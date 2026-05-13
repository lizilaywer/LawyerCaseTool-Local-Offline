# -*- coding: utf-8 -*-
"""案件索引管理器

管理 cases.json，提供案件 CRUD、搜索、标签、期限、信息字段与本地记忆能力。
"""

import contextlib
import json
import shutil
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from src.config.config_manager import safe_write_json
from src.config.path_manager import get_path_manager
from src.utils.logger import get_logger


FOLDER_STATUS_AVAILABLE = "available"
FOLDER_STATUS_MISSING = "missing"
FOLDER_STATUS_UNLINKED = "unlinked"

CORE_INFO_FIELD_DEFINITIONS = [
    {"key": "engagement_date", "label": "委托时间", "type": "datetime"},
    {"key": "fee_status", "label": "收费情况", "type": "text"},
    {"key": "case_number", "label": "案号", "type": "text"},
    {"key": "cause_of_action", "label": "案由", "type": "text"},
    {"key": "party_name", "label": "当事人", "type": "text"},
    {"key": "opponent_name", "label": "对方当事人", "type": "text"},
    {"key": "entrusted_role", "label": "委托角色", "type": "single_select"},
    {"key": "litigation_role", "label": "诉讼地位", "type": "single_select"},
    {"key": "handling_lawyer", "label": "承办律师", "type": "text"},
    {"key": "forum", "label": "法院/仲裁委", "type": "text"},
    {"key": "filing_date", "label": "立案时间", "type": "date"},
]

DEFAULT_INFO_SECTION_TITLES = {
    "basic": "基础信息",
    "parties": "委托关系",
    "business": "业务信息",
    "custom": "自定义字段",
}

_CORE_INFO_KEYS = {item["key"] for item in CORE_INFO_FIELD_DEFINITIONS}
_CORE_INFO_BY_KEY = {item["key"]: item for item in CORE_INFO_FIELD_DEFINITIONS}
_VARIABLE_TO_INFO_KEY = {
    # 案号
    "case_number": "case_number",
    # 案由
    "Cause_of_Action": "cause_of_action",
    "crime_name": "cause_of_action",
    # 当事人（我方委托人）
    "client_name": "party_name",
    # 对方当事人（不同模板用不同变量名）
    "opponent_client_name": "opponent_name",
    "opposing_party": "opponent_name",
    "plaintiff_name": "opponent_name",
    "defendant_agency": "opponent_name",
    "employer_name": "opponent_name",
    "respondent_name": "opponent_name",
    "applicant_name": "opponent_name",
    # 法院 / 仲裁委
    "court_name": "forum",
    "court": "forum",
    "arbitration_committee": "forum",
    "arbitration_institution": "forum",
    # 立案时间
    "filing_date": "filing_date",
    # 承办律师
    "lawyer_name": "handling_lawyer",
    # 委托时间
    "receive_date": "engagement_date",
    # 律师费支付 → 收费情况
    "payment": "fee_status",
}

_TEMPLATE_LITIGATION_ROLE = {
    "civil_simple_001": "原告",
    "civil_simple_002": "被告",
    "criminal_simple_001": "__criminal__",  # 需要根据阶段判断
    "admin_simple_001": "原告",
    "admin_simple_002": "被告",
    "labor_simple_001": "申请人",
    "labor_simple_002": "被申请人",
    "commercial_simple_001": "申请人",
    "commercial_simple_002": "被申请人",
}


def _derive_litigation_role(
    template_id: str, template_name: str, variables: Dict[str, Any]
) -> str:
    """根据模板 ID / 名称 / 变量推导诉讼地位。"""
    role = _TEMPLATE_LITIGATION_ROLE.get(template_id, "")
    if role == "__criminal__":
        stage = str(variables.get("Case_adjudication_stage", "")).strip()
        if any(kw in stage for kw in ("一审", "二审", "审判", "法院")):
            return "被告人"
        if any(kw in stage for kw in ("侦查", "审查起诉", "检")):
            return "犯罪嫌疑人"
        return "犯罪嫌疑人/被告人"
    if role:
        return role
    # 名称关键词回退（用户自定义模板）
    name = template_name or ""
    if "被申请" in name:
        return "被申请人"
    if "申请" in name:
        return "申请人"
    if "被告" in name:
        return "被告"
    if "原告" in name:
        return "原告"
    if "刑事" in name or "辩护" in name:
        return "犯罪嫌疑人/被告人"
    return ""


_INFO_SECTION_BY_KEY = {
    "engagement_date": "basic",
    "fee_status": "business",
    "case_number": "basic",
    "cause_of_action": "basic",
    "party_name": "parties",
    "opponent_name": "parties",
    "entrusted_role": "parties",
    "litigation_role": "parties",
    "handling_lawyer": "business",
    "forum": "business",
    "filing_date": "business",
}


def _normalize_tags(tags: Iterable[str]) -> List[str]:
    """规范化标签，去重并保留原顺序。"""
    result: List[str] = []
    seen = set()

    for tag in tags:
        value = str(tag or "").strip().lstrip("#")
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)

    return result


def _ensure_datetime_string(value: str) -> str:
    """标准化 ISO 时间字符串。"""
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return ""


def _normalize_path_history(path_history: Iterable[str], current_path: str) -> List[str]:
    """规范化路径历史。"""
    result: List[str] = []
    seen = set()

    for item in list(path_history or []) + ([current_path] if current_path else []):
        value = str(item or "").strip()
        if not value:
            continue
        normalized = value.replace("\\", "/").rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)

    return result


def _normalize_deadline(deadline: Dict[str, Any]) -> Dict[str, Any]:
    """规范化期限数据。"""
    result = dict(deadline or {})
    result.setdefault("id", f"dl_{uuid.uuid4().hex[:6]}")
    result["title"] = str(result.get("title", "")).strip()
    result["date"] = str(result.get("date", "")).strip()
    result["time"] = str(result.get("time", "")).strip()
    result["all_day"] = bool(result.get("all_day", not bool(result["time"])))
    result["type"] = str(result.get("type", "deadline")).strip() or "deadline"
    result["priority"] = str(result.get("priority", "medium")).strip() or "medium"
    result["description"] = str(result.get("description", "")).strip()
    result["status"] = str(result.get("status", "pending")).strip() or "pending"
    result["completed_at"] = _ensure_datetime_string(result.get("completed_at", ""))

    remind_before = result.get("remind_before", [])
    normalized_remind = []
    seen = set()
    if isinstance(remind_before, list):
        for item in remind_before:
            try:
                value = int(item)
            except (TypeError, ValueError):
                continue
            if value < 0 or value in seen:
                continue
            seen.add(value)
            normalized_remind.append(value)
    normalized_remind.sort(reverse=True)
    result["remind_before"] = normalized_remind
    return result


def _build_default_info_fields(variables: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """构建默认核心字段。"""
    variables = variables or {}
    values_by_key = {}
    for variable_key, info_key in _VARIABLE_TO_INFO_KEY.items():
        value = str(variables.get(variable_key, "")).strip()
        if value:
            values_by_key[info_key] = value

    fields = []
    for item in CORE_INFO_FIELD_DEFINITIONS:
        fields.append({
            "id": f"builtin_{item['key']}",
            "key": item["key"],
            "label": item["label"],
            "value": values_by_key.get(item["key"], ""),
            "type": item["type"],
            "builtin": True,
            "map_to_tag": False,
        })
    return fields


def _normalize_info_fields(
    info_fields: Iterable[Dict[str, Any]],
    variables: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """规范化案件信息字段。"""
    defaults = {item["key"]: item for item in _build_default_info_fields(variables)}
    custom_fields: List[Dict[str, Any]] = []

    for raw_field in info_fields or []:
        if not isinstance(raw_field, dict):
            continue
        key = str(raw_field.get("key", "")).strip()
        label = str(raw_field.get("label", "")).strip()
        builtin = bool(raw_field.get("builtin", key in _CORE_INFO_KEYS))
        field_type = str(raw_field.get("type", "text")).strip() or "text"
        value = str(raw_field.get("value", "")).strip()
        map_to_tag = bool(raw_field.get("map_to_tag", False))

        if builtin and key in defaults:
            defaults[key].update({
                "id": str(raw_field.get("id", defaults[key]["id"])) or defaults[key]["id"],
                "label": label or defaults[key]["label"],
                "value": value,
                "type": field_type or defaults[key]["type"],
                "builtin": True,
                "map_to_tag": map_to_tag,
            })
            continue

        if not label:
            continue

        custom_fields.append({
            "id": str(raw_field.get("id", "")) or f"field_{uuid.uuid4().hex[:8]}",
            "key": key or f"custom_{uuid.uuid4().hex[:6]}",
            "label": label,
            "value": value,
            "type": field_type,
            "builtin": False,
            "map_to_tag": map_to_tag,
        })

    return list(defaults.values()) + custom_fields


def _build_info_field_tag(field: Dict[str, Any]) -> str:
    """根据字段构建筛选标签。"""
    label = str(field.get("label", "")).strip()
    value = str(field.get("value", "")).strip()
    if not label or not value:
        return ""
    return f"{label}:{value}"


def _normalize_info_section_titles(
    section_titles: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """规范化信息分组标题。"""
    normalized: Dict[str, str] = {}
    raw_titles = section_titles if isinstance(section_titles, dict) else {}
    for key, default_title in DEFAULT_INFO_SECTION_TITLES.items():
        value = str(raw_titles.get(key, "")).strip()
        normalized[key] = value or default_title
    return normalized


class CaseManager:
    """案件索引管理器 - 单例模式"""

    _instance: Optional["CaseManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        with self.__class__._lock:
            if self._initialized:
                return
            self._initialized = True
        self._logger = get_logger()
        self._cases_file = get_path_manager().cases_file
        self._cases: Dict[str, Dict[str, Any]] = {}
        self._global_deadlines: List[Dict[str, Any]] = []
        self._common_tags: List[str] = []
        self._last_refresh_time: float = 0.0  # 上次全量刷新时间戳
        self._lock = threading.RLock()
        # 批量更新模式
        self._batch_mode = False
        self._batch_changed: Set[str] = set()
        # 性能优化索引
        self._path_index: Dict[str, str] = {}  # normalized_path -> case_id
        self._history_index: Dict[str, str] = {}  # normalized_history_path -> case_id
        self._search_index: Dict[str, str] = {}  # case_id -> flattened search text
        self._sorted_case_ids: List[str] = []  # 按 updated_at 降序排序的 case_id 列表
        self._load()

    def _load(self) -> None:
        """从 cases.json 加载。"""
        if not self._cases_file.exists():
            self._cases = {}
            self._global_deadlines = []
            self._common_tags = []
            return

        try:
            data = json.loads(self._cases_file.read_text(encoding="utf-8"))
            raw_cases = data.get("cases", {})
            raw_global_deadlines = data.get("global_deadlines", [])
            raw_common_tags = data.get("common_tags", [])
        except Exception as exc:
            self._logger.error(f"加载案件索引失败: {exc}")
            self._cases = {}
            self._global_deadlines = []
            self._common_tags = []
            return

        normalized_cases: Dict[str, Dict[str, Any]] = {}
        changed = False
        for case_id, case in raw_cases.items():
            normalized = self._normalize_case_record(case_id, case)
            normalized_cases[case_id] = normalized
            if normalized != case:
                changed = True

        self._cases = normalized_cases
        self._global_deadlines = [
            _normalize_deadline(item) for item in raw_global_deadlines if isinstance(item, dict)
        ]
        self._common_tags = _normalize_tags(raw_common_tags)
        self._rebuild_indices()
        if changed or self._global_deadlines != list(raw_global_deadlines or []):
            self.save()

    def save(self) -> bool:
        """保存到 cases.json。"""
        try:
            safe_write_json(
                self._cases_file,
                {
                    "version": 2,
                    "cases": self._cases,
                    "global_deadlines": self._global_deadlines,
                    "common_tags": self._common_tags,
                },
            )
            return True
        except Exception as exc:
            self._logger.error(f"保存案件索引失败: {exc}")
            return False

    def _rebuild_indices(self) -> None:
        """重建所有性能优化索引。"""
        self._path_index.clear()
        self._history_index.clear()
        self._search_index.clear()
        for case_id, case in self._cases.items():
            path = str(case.get("path", "")).replace("\\", "/").rstrip("/")
            if path:
                self._path_index[path] = case_id
            for hist in case.get("path_history", []):
                hist_norm = str(hist).replace("\\", "/").rstrip("/")
                if hist_norm:
                    self._history_index[hist_norm] = case_id
            self._search_index[case_id] = self._build_search_text(case)
        self._rebuild_sorted_ids()

    def _rebuild_sorted_ids(self) -> None:
        """重建按 updated_at 降序排序的 case_id 列表。"""
        self._sorted_case_ids = sorted(
            self._cases.keys(),
            key=lambda cid: self._cases[cid].get("updated_at", ""),
            reverse=True,
        )

    @staticmethod
    def _build_search_text(case: Dict[str, Any]) -> str:
        """为案件构建扁平化的搜索文本。"""
        parts = [str(case.get("name", "")).lower()]
        parts.extend(str(tag).lower() for tag in case.get("tags", []))
        parts.extend(str(v).lower() for v in case.get("variables", {}).values())
        for field in case.get("info_fields", []):
            parts.append(str(field.get("label", "")).lower())
            parts.append(str(field.get("value", "")).lower())
        return " ".join(parts)

    def _update_case_index(self, case_id: str, old_case: Optional[Dict[str, Any]] = None) -> None:
        """增量更新单个案件的索引。"""
        case = self._cases.get(case_id)
        if not case:
            return
        # 路径索引
        if old_case:
            old_path = str(old_case.get("path", "")).replace("\\", "/").rstrip("/")
            if old_path and self._path_index.get(old_path) == case_id:
                del self._path_index[old_path]
            for hist in old_case.get("path_history", []):
                hist_norm = str(hist).replace("\\", "/").rstrip("/")
                if hist_norm and self._history_index.get(hist_norm) == case_id:
                    del self._history_index[hist_norm]
        new_path = str(case.get("path", "")).replace("\\", "/").rstrip("/")
        if new_path:
            self._path_index[new_path] = case_id
        for hist in case.get("path_history", []):
            hist_norm = str(hist).replace("\\", "/").rstrip("/")
            if hist_norm:
                self._history_index[hist_norm] = case_id
        # 搜索索引
        self._search_index[case_id] = self._build_search_text(case)
        # 排序缓存：移到队首（最新更新）
        if case_id in self._sorted_case_ids:
            self._sorted_case_ids.remove(case_id)
        self._sorted_case_ids.insert(0, case_id)

    @contextlib.contextmanager
    def batch_update(self):
        """批量更新上下文管理器。退出时统一保存一次。"""
        with self._lock:
            self._batch_mode = True
            self._batch_changed.clear()
        try:
            yield self
        finally:
            with self._lock:
                self._batch_mode = False
                changed = bool(self._batch_changed)
                self._batch_changed.clear()
            if changed:
                self.save()

    def _persist_case(self, case_id: str) -> bool:
        """保存单个案件相关数据。"""
        if self._batch_mode:
            self._batch_changed.add(case_id)
            self._sync_case_sidecar(case_id)
            return True
        saved = self.save()
        if saved:
            self._sync_case_sidecar(case_id)
        return saved

    def _normalize_case_record(self, case_id: str, case: Dict[str, Any]) -> Dict[str, Any]:
        """规范化案件记录。"""
        now = datetime.now().isoformat()
        normalized: Dict[str, Any] = dict(case or {})
        normalized["id"] = str(normalized.get("id", case_id) or case_id)
        normalized["name"] = str(normalized.get("name", "")).strip()
        normalized["path"] = str(normalized.get("path", "")).strip()
        normalized["category"] = str(normalized.get("category", "")).strip()
        normalized["template_id"] = str(normalized.get("template_id", "")).strip()
        normalized["template_name"] = str(normalized.get("template_name", "")).strip()
        normalized["variables"] = dict(normalized.get("variables", {}) or {})
        normalized["notes"] = str(normalized.get("notes", "") or "")
        normalized["notes_secondary"] = str(normalized.get("notes_secondary", "") or "")
        normalized["notes_split"] = bool(normalized.get("notes_split", False))
        normalized["created_at"] = _ensure_datetime_string(normalized.get("created_at", now)) or now
        normalized["updated_at"] = _ensure_datetime_string(normalized.get("updated_at", now)) or now
        normalized["last_seen_at"] = _ensure_datetime_string(normalized.get("last_seen_at", "")) or ""
        normalized["folder_status"] = str(normalized.get("folder_status", "")).strip()
        normalized["tags"] = _normalize_tags(normalized.get("tags", []))
        normalized["deadlines"] = [
            _normalize_deadline(item) for item in normalized.get("deadlines", []) if isinstance(item, dict)
        ]
        normalized["path_history"] = _normalize_path_history(
            normalized.get("path_history", []),
            normalized["path"],
        )
        normalized["info_fields"] = _normalize_info_fields(
            normalized.get("info_fields", []),
            normalized["variables"],
        )
        normalized["info_section_titles"] = _normalize_info_section_titles(
            normalized.get("info_section_titles"),
        )

        # 根据 template_id / template_name / variables 自动填充诉讼地位和委托角色
        litigation_role = _derive_litigation_role(
            normalized["template_id"],
            normalized["template_name"],
            normalized["variables"],
        )
        for field in normalized["info_fields"]:
            if field.get("key") == "litigation_role" and not field.get("value"):
                field["value"] = litigation_role
                break
        for field in normalized["info_fields"]:
            if field.get("key") == "entrusted_role" and not field.get("value"):
                field["value"] = "委托人"
                break

        if not normalized["folder_status"]:
            normalized["folder_status"] = self._detect_folder_status(normalized["path"])
        else:
            normalized["folder_status"] = self._detect_folder_status(
                normalized["path"],
                normalized["folder_status"],
            )

        return normalized

    def _detect_folder_status(self, path_text: str, preferred: str = "") -> str:
        """检测案件目录状态。"""
        if not path_text:
            return FOLDER_STATUS_UNLINKED
        path = Path(path_text)
        if path.exists():
            return FOLDER_STATUS_AVAILABLE
        if preferred == FOLDER_STATUS_UNLINKED:
            return preferred
        return FOLDER_STATUS_MISSING

    def _refresh_case_runtime_state(self, case_id: str) -> bool:
        """刷新案件的运行时状态。"""
        case = self._cases.get(case_id)
        if not case:
            return False

        changed = False
        current_status = case.get("folder_status", "")
        detected_status = self._detect_folder_status(case.get("path", ""), current_status)
        if detected_status != current_status:
            case["folder_status"] = detected_status
            changed = True

        if detected_status == FOLDER_STATUS_AVAILABLE:
            case["last_seen_at"] = datetime.now().isoformat()
            notes_path = self._get_case_notes_file(case.get("path", ""))
            if notes_path.exists():
                try:
                    notes_text = notes_path.read_text(encoding="utf-8")
                except Exception as exc:
                    self._logger.warning(f"读取案件速记失败: {exc}")
                else:
                    if notes_text != case.get("notes", ""):
                        case["notes"] = notes_text
                        changed = True

            secondary_notes_path = self._get_case_secondary_notes_file(case.get("path", ""))
            if secondary_notes_path.exists():
                try:
                    secondary_notes_text = secondary_notes_path.read_text(encoding="utf-8")
                except Exception as exc:
                    self._logger.warning(f"读取副笔记失败: {exc}")
                else:
                    if secondary_notes_text != case.get("notes_secondary", ""):
                        case["notes_secondary"] = secondary_notes_text
                        changed = True

        return changed

    def _refresh_case_runtime_state_light(self, case_id: str) -> bool:
        """轻量刷新：仅更新目录状态，不读取 sidecar 笔记。"""
        case = self._cases.get(case_id)
        if not case:
            return False

        changed = False
        current_status = case.get("folder_status", "")
        detected_status = self._detect_folder_status(case.get("path", ""), current_status)
        if detected_status != current_status:
            case["folder_status"] = detected_status
            changed = True

        if detected_status == FOLDER_STATUS_AVAILABLE:
            case["last_seen_at"] = datetime.now().isoformat()

        return changed

    def _resolve_safe_delete_target(self, case_id: str, folder_path: Path) -> Optional[Path]:
        """校验删除目标目录是否安全。"""
        if folder_path.is_symlink():
            self._logger.error(f"拒绝删除符号链接目录: {folder_path}")
            return None

        try:
            resolved = folder_path.resolve(strict=True)
        except OSError as exc:
            self._logger.error(f"解析删除路径失败: {folder_path} ({exc})")
            return None

        # 禁止删除文件系统根目录（/、C:\ 等）
        if resolved == Path(resolved.anchor):
            self._logger.error(f"拒绝删除根目录: {resolved}")
            return None

        # 禁止删除用户主目录
        try:
            if resolved == Path.home().resolve():
                self._logger.error(f"拒绝删除用户主目录: {resolved}")
                return None
        except Exception:
            pass

        metadata_file = self._get_case_metadata_file(str(resolved))
        if not metadata_file.exists():
            self._logger.error(f"删除目标缺少案件 metadata，拒绝删除: {resolved}")
            return None

        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception as exc:
            self._logger.error(f"案件 metadata 读取失败，拒绝删除: {metadata_file} ({exc})")
            return None

        meta_case_id = str(metadata.get("case_id", "")).strip()
        if meta_case_id != case_id:
            self._logger.error(
                f"删除目标与案件ID不一致，拒绝删除: case_id={case_id}, metadata_case_id={meta_case_id}, path={resolved}"
            )
            return None

        return resolved

    def _get_case_storage_dir(self, path_text: str) -> Path:
        """获取案件目录内的 sidecar 目录。"""
        return Path(path_text) / ".case"

    def _get_case_metadata_file(self, path_text: str) -> Path:
        return self._get_case_storage_dir(path_text) / "metadata.json"

    def _get_case_notes_file(self, path_text: str) -> Path:
        return self._get_case_storage_dir(path_text) / "notes.md"

    def _get_case_secondary_notes_file(self, path_text: str) -> Path:
        return self._get_case_storage_dir(path_text) / "notes_secondary.md"

    def _build_case_metadata_payload(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """构建 sidecar metadata 载荷。"""
        return {
            "case_id": case.get("id", ""),
            "name": case.get("name", ""),
            "category": case.get("category", ""),
            "status": case.get("status", "active"),
            "folder_status": case.get("folder_status", FOLDER_STATUS_UNLINKED),
            "tags": case.get("tags", []),
            "path_history": case.get("path_history", []),
            "info_fields": case.get("info_fields", []),
            "info_section_titles": case.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES),
            "deadlines": case.get("deadlines", []),
            "notes_split": bool(case.get("notes_split", False)),
            "updated_at": case.get("updated_at", ""),
            "created_at": case.get("created_at", ""),
        }

    def _sync_case_sidecar(self, case_id: str) -> None:
        """将案件摘要和笔记同步到文件夹 sidecar。"""
        case = self._cases.get(case_id)
        if not case:
            return

        path_text = case.get("path", "")
        if not path_text:
            return

        folder_path = Path(path_text)
        if not folder_path.exists() or not folder_path.is_dir():
            return

        storage_dir = self._get_case_storage_dir(path_text)
        storage_dir.mkdir(parents=True, exist_ok=True)

        try:
            safe_write_json(
                self._get_case_metadata_file(path_text),
                self._build_case_metadata_payload(case),
            )
        except Exception as exc:
            self._logger.warning(f"同步案件 metadata 失败: {exc}")

        try:
            self._get_case_notes_file(path_text).write_text(case.get("notes", ""), encoding="utf-8")
        except Exception as exc:
            self._logger.warning(f"同步案件笔记失败: {exc}")

        try:
            self._get_case_secondary_notes_file(path_text).write_text(case.get("notes_secondary", ""), encoding="utf-8")
        except Exception as exc:
            self._logger.warning(f"同步案件副笔记失败: {exc}")

    def _read_case_sidecar(self, folder_path: Path) -> Tuple[Dict[str, Any], str, str]:
        """读取案件目录中的 metadata 和主/副笔记。"""
        metadata: Dict[str, Any] = {}
        notes_text = ""
        secondary_notes_text = ""

        metadata_path = self._get_case_metadata_file(str(folder_path))
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception as exc:
                self._logger.warning(f"读取案件 metadata 失败: {exc}")

        notes_path = self._get_case_notes_file(str(folder_path))
        if notes_path.exists():
            try:
                notes_text = notes_path.read_text(encoding="utf-8")
            except Exception as exc:
                self._logger.warning(f"读取案件笔记失败: {exc}")

        secondary_notes_path = self._get_case_secondary_notes_file(str(folder_path))
        if secondary_notes_path.exists():
            try:
                secondary_notes_text = secondary_notes_path.read_text(encoding="utf-8")
            except Exception as exc:
                self._logger.warning(f"读取案件副笔记失败: {exc}")

        return metadata, notes_text, secondary_notes_text

    def _resolve_existing_case_id(self, folder_path: Path) -> Optional[str]:
        """通过当前路径、历史路径或 metadata 识别既有案件。"""
        existing = self.get_case_by_path(str(folder_path))
        if existing:
            return existing["id"]

        normalized_path = str(folder_path).replace("\\", "/").rstrip("/")
        case_id = self._history_index.get(normalized_path)
        if case_id and case_id in self._cases:
            self.update_case_path(case_id, folder_path)
            return case_id

        metadata, _, _ = self._read_case_sidecar(folder_path)
        sidecar_case_id = str(metadata.get("case_id", "")).strip()
        if sidecar_case_id and sidecar_case_id in self._cases:
            self.update_case_path(sidecar_case_id, folder_path)
            return sidecar_case_id

        return None

    # ── 案件 CRUD ──

    def register_case(self, info: Dict[str, Any], case_id: str = "") -> str:
        """注册新案件，返回 case_id。"""
        now = datetime.now().isoformat()
        resolved_case_id = case_id or f"case_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
        path_text = str(info.get("path", "")).strip()
        variables = dict(info.get("variables", {}) or {})

        case = self._normalize_case_record(resolved_case_id, {
            "id": resolved_case_id,
            "name": info.get("name", ""),
            "path": path_text,
            "category": info.get("category", ""),
            "template_id": info.get("template_id", ""),
            "variables": variables,
            "tags": info.get("tags", []),
            "status": info.get("status", "active"),
            "deadlines": info.get("deadlines", []),
            "path_history": info.get("path_history", [path_text] if path_text else []),
            "folder_status": info.get("folder_status", ""),
            "last_seen_at": info.get("last_seen_at", now if path_text else ""),
            "notes": info.get("notes", ""),
            "notes_secondary": info.get("notes_secondary", ""),
            "notes_split": info.get("notes_split", False),
            "info_fields": info.get("info_fields", []),
            "info_section_titles": info.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES),
            "created_at": info.get("created_at", now),
            "updated_at": info.get("updated_at", now),
        })
        self._cases[resolved_case_id] = case
        self._update_case_index(resolved_case_id)
        self._persist_case(resolved_case_id)
        return resolved_case_id

    def unregister_case(self, case_id: str) -> bool:
        """删除案件索引（不删除文件夹）。"""
        if case_id not in self._cases:
            return False
        old_case = self._cases[case_id]
        # 清理索引
        old_path = str(old_case.get("path", "")).replace("\\", "/").rstrip("/")
        if old_path and self._path_index.get(old_path) == case_id:
            del self._path_index[old_path]
        for hist in old_case.get("path_history", []):
            hist_norm = str(hist).replace("\\", "/").rstrip("/")
            if hist_norm and self._history_index.get(hist_norm) == case_id:
                del self._history_index[hist_norm]
        self._search_index.pop(case_id, None)
        if case_id in self._sorted_case_ids:
            self._sorted_case_ids.remove(case_id)
        del self._cases[case_id]
        return self.save()

    def remove_case(self, case_id: str, delete_folder: bool = False) -> bool:
        """移除案件；可选同步删除实际目录。"""
        case = self._cases.get(case_id)
        if not case:
            return False

        if not delete_folder:
            return self.unregister_case(case_id)

        path_text = str(case.get("path", "")).strip()
        safe_target: Optional[Path] = None
        if path_text:
            folder_path = Path(path_text)
            if folder_path.exists():
                safe_target = self._resolve_safe_delete_target(case_id, folder_path)
                if safe_target is None:
                    return False

        case_snapshot = deepcopy(case)
        if not self.unregister_case(case_id):
            return False

        if safe_target is None:
            return True

        try:
            shutil.rmtree(safe_target)
            return True
        except OSError as exc:
            self._cases[case_id] = case_snapshot
            self._rebuild_indices()
            if not self.save():
                self._logger.critical(
                    f"删除目录失败后回滚案件索引也失败，请人工检查 cases.json 与目录状态: {case_id}"
                )
            raise exc

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> bool:
        """部分更新案件信息。"""
        if case_id not in self._cases:
            return False

        case = self._cases[case_id]
        old_case = deepcopy(case)
        old_info_fields = deepcopy(case.get("info_fields", []))
        case.update(updates)
        case["updated_at"] = datetime.now().isoformat()
        case = self._normalize_case_record(case_id, case)
        case["tags"] = self._merge_manual_and_field_tags(
            case.get("tags", []),
            old_info_fields,
            case.get("info_fields", []),
        )
        self._cases[case_id] = case
        self._update_case_index(case_id, old_case=old_case)
        return self._persist_case(case_id)

    def update_case_path(self, case_id: str, new_path: Path) -> bool:
        """更新案件当前路径，并保留历史路径。"""
        if case_id not in self._cases:
            return False

        case = self._cases[case_id]
        case_before = deepcopy(case)
        current_path = str(case.get("path", "")).strip()
        resolved_path = str(Path(new_path))
        if current_path and current_path != resolved_path:
            case["path_history"] = _normalize_path_history(case.get("path_history", []), current_path)
        case["path"] = resolved_path
        case["path_history"] = _normalize_path_history(case.get("path_history", []), resolved_path)
        case["folder_status"] = self._detect_folder_status(resolved_path)
        case["last_seen_at"] = datetime.now().isoformat()
        case["updated_at"] = datetime.now().isoformat()
        self._cases[case_id] = case
        self._update_case_index(case_id, old_case=case_before)
        return self._persist_case(case_id)

    def rename_case(self, case_id: str, new_name: str) -> bool:
        """重命名案件；若实际目录存在则同步重命名文件夹。"""
        if case_id not in self._cases:
            return False

        target_name = str(new_name or "").strip()
        if not target_name:
            return False

        case = self._cases[case_id]
        current_path_text = str(case.get("path", "")).strip()
        current_path = Path(current_path_text) if current_path_text else None

        if current_path and current_path.exists() and current_path.is_dir():
            if current_path.name != target_name:
                target_path = current_path.with_name(target_name)
                if target_path.exists():
                    raise FileExistsError(f"目标目录已存在：{target_path}")
                current_path.rename(target_path)
                if not self.update_case_path(case_id, target_path):
                    return False

        return self.update_case(case_id, {"name": target_name})

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """获取单个案件。"""
        with self._lock:
            if case_id not in self._cases:
                return None
        self._refresh_case_runtime_state_light(case_id)
        with self._lock:
            return self._cases.get(case_id)

    def get_case_by_path(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """根据文件夹路径查找案件。"""
        normalized = str(folder_path).replace("\\", "/").rstrip("/")
        with self._lock:
            case_id = self._path_index.get(normalized)
            if case_id:
                return self._cases.get(case_id)
        return None

    def get_all_cases(self, refresh_runtime: bool = False) -> List[Dict[str, Any]]:
        """获取所有案件，按 updated_at 降序。

        默认只返回内存索引，避免打开案件管理、搜索和筛选时在主线程
        批量访问磁盘。需要显式核验目录/sidecar 状态的场景可传入
        refresh_runtime=True。
        """
        if refresh_runtime:
            now = time.monotonic()
            if now - self._last_refresh_time >= 30.0:
                self.refresh_all_runtime_states()
                self._last_refresh_time = now

        with self._lock:
            return [self._cases[cid] for cid in self._sorted_case_ids if cid in self._cases]

    def refresh_all_runtime_states(self, include_notes: bool = False) -> bool:
        """刷新全部案件运行时状态。

        这是相对昂贵的磁盘 I/O 操作，尤其在 Windows 上会受杀软、
        网络盘、机械盘影响；因此只在用户明确触发或后台维护场景调用。
        """
        changed = False
        with self.batch_update():
            for case_id in list(self._cases.keys()):
                case = self._cases[case_id]
                before = case.get("folder_status", "")
                if include_notes:
                    case_changed = self._refresh_case_runtime_state(case_id)
                else:
                    case_changed = self._refresh_case_runtime_state_light(case_id)
                if case_changed or self._cases[case_id].get("folder_status", "") != before:
                    self._batch_changed.add(case_id)
                    changed = True
        return changed

    def get_cases_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按分类筛选。"""
        cat_map = {
            "civil": ["civil"],
            "criminal": ["criminal"],
            "administrative": ["administrative"],
            "non_litigation": ["non_litigation"],
            "labor_arbitration": ["labor_arbitration"],
            "commercial_arbitration": ["commercial_arbitration"],
        }
        allowed = cat_map.get(category, [category])
        return [case for case in self.get_all_cases() if case.get("category", "") in allowed]

    def get_cases_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """按标签筛选。"""
        return [case for case in self.get_all_cases() if tag in case.get("tags", [])]

    def search_cases(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索（名称 + 标签 + 变量值 + 信息字段）。"""
        if not keyword:
            return self.get_all_cases()

        kw = keyword.lower()
        with self._lock:
            results = []
            for case_id in self._sorted_case_ids:
                case = self._cases.get(case_id)
                if not case:
                    continue
                search_text = self._search_index.get(case_id, "")
                if kw in search_text:
                    results.append(case)
        return results

    def get_all_tags(self) -> List[str]:
        """获取所有已使用的标签，去重排序。"""
        tags = set()
        for case in self.get_all_cases():
            for tag in case.get("tags", []):
                if tag:
                    tags.add(tag)
        return sorted(tags)

    def get_common_tags(self) -> List[str]:
        """获取常用标签。"""
        return list(self._common_tags)

    def set_common_tags(self, tags: Iterable[str]) -> bool:
        """设置常用标签。"""
        self._common_tags = _normalize_tags(tags)
        return self.save()

    def verify_case_path(self, case_id: str) -> bool:
        """验证案件文件夹是否存在。"""
        case = self.get_case(case_id)
        if not case:
            return False
        return case.get("folder_status") == FOLDER_STATUS_AVAILABLE

    def cleanup_missing(self) -> List[str]:
        """刷新目录缺失状态，返回当前缺失的 case_id 列表。"""
        missing_cases = []
        with self.batch_update():
            for case_id in list(self._cases.keys()):
                self._refresh_case_runtime_state(case_id)
                if self._cases[case_id].get("folder_status") == FOLDER_STATUS_MISSING:
                    missing_cases.append(case_id)
        return missing_cases

    def import_existing_folder(self, folder_path: Path, category: str = "") -> Optional[str]:
        """导入已有文件夹为新案件或重新关联已有案件。"""
        folder_path = Path(folder_path)
        if not folder_path.exists() or not folder_path.is_dir():
            return None

        resolved_case_id = self._resolve_existing_case_id(folder_path)
        if resolved_case_id:
            return resolved_case_id

        metadata, notes_text, secondary_notes_text = self._read_case_sidecar(folder_path)
        sidecar_case_id = str(metadata.get("case_id", "")).strip()
        record_info = {
            "name": metadata.get("name") or folder_path.name,
            "path": str(folder_path),
            "category": metadata.get("category") or category,
            "tags": metadata.get("tags", []),
            "status": metadata.get("status", "active"),
            "deadlines": metadata.get("deadlines", []),
            "path_history": metadata.get("path_history", [str(folder_path)]),
            "folder_status": metadata.get("folder_status", FOLDER_STATUS_AVAILABLE),
            "notes": notes_text,
            "notes_secondary": secondary_notes_text,
            "notes_split": metadata.get("notes_split", False),
            "info_fields": metadata.get("info_fields", []),
            "info_section_titles": metadata.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES),
            "created_at": metadata.get("created_at", ""),
            "updated_at": metadata.get("updated_at", ""),
        }
        return self.register_case(record_info, case_id=sidecar_case_id)

    def import_existing_folders(
        self,
        folder_paths: List[Path],
        category: str = "",
    ) -> Dict[str, List[str]]:
        """批量导入已有文件夹。"""
        result = {
            "imported_ids": [],
            "existing_ids": [],
            "invalid_paths": [],
        }
        seen_paths = set()

        with self.batch_update():
            for raw_path in folder_paths:
                folder_path = Path(raw_path)
                normalized = str(folder_path.resolve()) if folder_path.exists() else str(folder_path)
                if normalized in seen_paths:
                    continue
                seen_paths.add(normalized)

                if not folder_path.exists() or not folder_path.is_dir():
                    result["invalid_paths"].append(str(folder_path))
                    continue

                existing = self.get_case_by_path(str(folder_path))
                if existing:
                    result["existing_ids"].append(existing["id"])
                    continue

                relinked_id = self._resolve_existing_case_id(folder_path)
                if relinked_id:
                    result["existing_ids"].append(relinked_id)
                    continue

                case_id = self.import_existing_folder(folder_path, category=category)
                if case_id:
                    result["imported_ids"].append(case_id)

        return result

    def _compare_sidecar_with_case(
        self, case_id: str, folder_path: Path
    ) -> Tuple[Dict[str, Any], List[str]]:
        """对比新目录 sidecar 与现有案件记录，返回 sidecar 数据和冲突字段列表。

        Returns:
            (sidecar_metadata, conflict_fields)
        """
        case = self._cases.get(case_id)
        if not case:
            return {}, []

        metadata, notes_text, secondary_notes_text = self._read_case_sidecar(folder_path)
        # 把 sidecar 的 notes 也纳入 metadata 方便对比
        sidecar = dict(metadata)
        sidecar["notes"] = notes_text
        sidecar["notes_secondary"] = secondary_notes_text

        conflict_fields: List[str] = []

        def _diff(field: str, old: Any, new: Any) -> None:
            if old != new and str(new or "").strip():
                conflict_fields.append(field)

        _diff("name", case.get("name", ""), sidecar.get("name", ""))
        _diff("category", case.get("category", ""), sidecar.get("category", ""))

        # 标签差异
        existing_tags = set(case.get("tags", []))
        sidecar_tags = set(sidecar.get("tags", []))
        if existing_tags != sidecar_tags and sidecar_tags:
            conflict_fields.append("tags")

        # 期限差异（以 id 为 key 对比）
        existing_dl_ids = {str(d.get("id", "")) for d in case.get("deadlines", [])}
        sidecar_dl_ids = {str(d.get("id", "")) for d in sidecar.get("deadlines", [])}
        if existing_dl_ids != sidecar_dl_ids and sidecar.get("deadlines"):
            conflict_fields.append("deadlines")

        # 信息字段差异
        existing_if_keys = {str(f.get("key", "")) for f in case.get("info_fields", [])}
        sidecar_if_keys = {str(f.get("key", "")) for f in sidecar.get("info_fields", [])}
        if existing_if_keys != sidecar_if_keys and sidecar.get("info_fields"):
            conflict_fields.append("info_fields")

        # 笔记差异
        _diff("notes", case.get("notes", ""), sidecar.get("notes", ""))
        _diff("notes_secondary", case.get("notes_secondary", ""), sidecar.get("notes_secondary", ""))

        # 分组标题差异
        existing_titles = case.get("info_section_titles", {})
        sidecar_titles = sidecar.get("info_section_titles", {})
        if existing_titles != sidecar_titles and sidecar_titles:
            conflict_fields.append("info_section_titles")

        return sidecar, conflict_fields

    def _merge_case_data(self, case_id: str, sidecar: Dict[str, Any]) -> bool:
        """智能合并 sidecar 数据到现有案件记录。

        合并规则：
        - 名称：保留现有
        - 标签：合并去重
        - 期限：按 id 去重合并
        - 信息字段：key 冲突保留现有，新增字段追加
        - 笔记：现有 + 分隔线 + 目录笔记
        - 分组标题：key 冲突保留现有
        """
        case = self._cases.get(case_id)
        if not case:
            return False

        # 标签合并
        existing_tags = list(case.get("tags", []))
        sidecar_tags = list(sidecar.get("tags", []))
        merged_tags = _normalize_tags(existing_tags + sidecar_tags)

        # 期限合并（按 id 去重）
        existing_deadlines = list(case.get("deadlines", []))
        sidecar_deadlines = list(sidecar.get("deadlines", []))
        merged_dl_map: Dict[str, Dict[str, Any]] = {}
        for dl in existing_deadlines + sidecar_deadlines:
            dl_id = str(dl.get("id", ""))
            if dl_id and dl_id not in merged_dl_map:
                merged_dl_map[dl_id] = dl
        merged_deadlines = list(merged_dl_map.values())

        # 信息字段合并（key 冲突保留现有）
        existing_if_map = {str(f.get("key", "")): f for f in case.get("info_fields", [])}
        for f in sidecar.get("info_fields", []):
            key = str(f.get("key", ""))
            if key and key not in existing_if_map:
                existing_if_map[key] = f
        merged_info_fields = list(existing_if_map.values())

        # 笔记合并
        existing_notes = str(case.get("notes", "") or "").strip()
        sidecar_notes = str(sidecar.get("notes", "") or "").strip()
        if existing_notes and sidecar_notes:
            merged_notes = existing_notes + "\n\n--- 来自目录笔记 ---\n\n" + sidecar_notes
        elif sidecar_notes:
            merged_notes = sidecar_notes
        else:
            merged_notes = existing_notes

        existing_notes2 = str(case.get("notes_secondary", "") or "").strip()
        sidecar_notes2 = str(sidecar.get("notes_secondary", "") or "").strip()
        if existing_notes2 and sidecar_notes2:
            merged_notes2 = existing_notes2 + "\n\n--- 来自目录笔记 ---\n\n" + sidecar_notes2
        elif sidecar_notes2:
            merged_notes2 = sidecar_notes2
        else:
            merged_notes2 = existing_notes2

        # 分组标题合并（key 冲突保留现有）
        merged_titles = dict(case.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES))
        for key, value in (sidecar.get("info_section_titles") or {}).items():
            if key not in merged_titles:
                merged_titles[key] = value

        case["tags"] = merged_tags
        case["deadlines"] = merged_deadlines
        case["info_fields"] = merged_info_fields
        case["notes"] = merged_notes
        case["notes_secondary"] = merged_notes2
        case["info_section_titles"] = merged_titles
        case["updated_at"] = datetime.now().isoformat()
        self._cases[case_id] = case
        return True

    def redefine_case_path(
        self,
        case_id: str,
        new_folder_path: Path,
        mode: str = "preview",
    ) -> Any:
        """重新定义案件目录。

        Args:
            case_id: 案件 ID
            new_folder_path: 新目录路径
            mode: ``"preview"`` 仅返回对比结果；
                  ``"replace"`` 用 sidecar 替换现有记录；
                  ``"keep"`` 仅更新路径；
                  ``"merge"`` 智能合并

        Returns:
            preview 模式返回 ``(sidecar_dict, conflict_fields)``；
            其他模式返回 ``True/False``
        """
        folder_path = Path(new_folder_path)
        if not folder_path.exists() or not folder_path.is_dir():
            raise ValueError("选择的目录不存在或不是有效文件夹。")

        case = self._cases.get(case_id)
        if not case:
            raise ValueError("案件不存在。")

        sidecar, conflict_fields = self._compare_sidecar_with_case(case_id, folder_path)

        if mode == "preview":
            return sidecar, conflict_fields

        if mode == "keep":
            # 仅更新路径
            return self.update_case_path(case_id, folder_path)

        if mode == "replace":
            # 用 sidecar 替换现有记录（保留 id、created_at）
            old_case = deepcopy(case)
            preserved = {
                "id": case.get("id", ""),
                "created_at": case.get("created_at", ""),
                "updated_at": datetime.now().isoformat(),
            }
            for key in ["name", "category", "status", "tags", "deadlines",
                        "info_fields", "info_section_titles", "notes_split"]:
                if key in sidecar:
                    case[key] = sidecar[key]
            case["notes"] = sidecar.get("notes", "")
            case["notes_secondary"] = sidecar.get("notes_secondary", "")
            case.update(preserved)
            case["path"] = str(folder_path)
            case["path_history"] = _normalize_path_history(
                case.get("path_history", []), str(folder_path)
            )
            case["folder_status"] = self._detect_folder_status(str(folder_path))
            self._cases[case_id] = case
            self._update_case_index(case_id, old_case=old_case)
            self._sync_case_sidecar(case_id)
            return self._persist_case(case_id)

        if mode == "merge":
            # 智能合并
            old_case = deepcopy(case)
            self._merge_case_data(case_id, sidecar)
            case = self._cases[case_id]
            case["path"] = str(folder_path)
            case["path_history"] = _normalize_path_history(
                case.get("path_history", []), str(folder_path)
            )
            case["folder_status"] = self._detect_folder_status(str(folder_path))
            case["updated_at"] = datetime.now().isoformat()
            self._cases[case_id] = case
            self._update_case_index(case_id, old_case=old_case)
            self._sync_case_sidecar(case_id)
            return self._persist_case(case_id)

        raise ValueError(f"未知的 mode: {mode}")

    def migrate_case_folder(
        self,
        case_id: str,
        target_parent_path: Path,
        rename_if_exists: bool = True,
    ) -> Path:
        """迁移案件文件夹到新的父目录。

        Args:
            case_id: 案件 ID
            target_parent_path: 目标父目录
            rename_if_exists: 目标已存在同名文件夹时是否自动重命名

        Returns:
            迁移后的新路径

        Raises:
            ValueError: 参数非法
            OSError: 文件操作失败
        """
        case = self._cases.get(case_id)
        if not case:
            raise ValueError("案件不存在。")

        current_path_text = str(case.get("path", "")).strip()
        if not current_path_text:
            raise ValueError("案件当前未关联任何目录。")

        source_path = Path(current_path_text)
        if not source_path.exists():
            raise ValueError(f"案件当前目录不存在：{source_path}")
        if not source_path.is_dir():
            raise ValueError(f"案件当前路径不是目录：{source_path}")

        target_parent = Path(target_parent_path)
        if not target_parent.exists() or not target_parent.is_dir():
            raise ValueError("目标目录不存在或不是有效文件夹。")

        # 安全检查
        try:
            if target_parent.resolve() == Path(target_parent.anchor):
                raise ValueError("不能迁移到文件系统根目录。")
            if target_parent.resolve() == Path.home().resolve():
                raise ValueError("不能迁移到用户主目录。")
        except Exception as exc:
            raise ValueError(f"目标路径安全检查失败: {exc}")

        target_path = target_parent / source_path.name

        if target_path.exists():
            if not rename_if_exists:
                raise FileExistsError(f"目标位置已存在同名文件夹：{target_path}")
            # 自动重命名
            counter = 1
            original_target = target_path
            while target_path.exists():
                target_path = original_target.with_name(f"{original_target.name} ({counter})")
                counter += 1

        # 执行移动
        shutil.move(str(source_path), str(target_path))

        # 更新路径
        if not self.update_case_path(case_id, target_path):
            # 回滚：移回去
            try:
                shutil.move(str(target_path), str(source_path))
            except Exception as rollback_exc:
                self._logger.critical(
                    f"迁移后更新路径失败，回滚也失败。"
                    f"案件 {case_id} 当前在 {target_path}，"
                    f"但软件记录仍指向 {source_path}。错误: {rollback_exc}"
                )
            raise RuntimeError("更新案件路径记录失败，已回滚移动操作。")

        return target_path

    def update_case_tags(self, case_id: str, tags: Iterable[str]) -> bool:
        """更新案件标签。"""
        if case_id not in self._cases:
            return False

        case = self._cases[case_id]
        old_info_fields = deepcopy(case.get("info_fields", []))
        case["tags"] = _normalize_tags(tags)
        case["tags"] = self._merge_manual_and_field_tags(case["tags"], old_info_fields, case.get("info_fields", []))
        case["updated_at"] = datetime.now().isoformat()
        self._cases[case_id] = case
        return self._persist_case(case_id)

    def get_info_fields(self, case_id: str) -> List[Dict[str, Any]]:
        """获取案件信息字段。"""
        case = self.get_case(case_id)
        if not case:
            return []
        return deepcopy(case.get("info_fields", []))

    def get_info_section_titles(self, case_id: str) -> Dict[str, str]:
        """获取案件信息分组标题。"""
        case = self.get_case(case_id)
        if not case:
            return deepcopy(DEFAULT_INFO_SECTION_TITLES)
        return deepcopy(case.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES))

    def update_info_fields(self, case_id: str, info_fields: Iterable[Dict[str, Any]]) -> bool:
        """更新案件信息字段。"""
        if case_id not in self._cases:
            return False

        case = self._cases[case_id]
        old_info_fields = deepcopy(case.get("info_fields", []))
        new_info_fields = _normalize_info_fields(info_fields, case.get("variables", {}))
        case["info_fields"] = new_info_fields
        case["tags"] = self._merge_manual_and_field_tags(case.get("tags", []), old_info_fields, new_info_fields)
        case["updated_at"] = datetime.now().isoformat()
        self._cases[case_id] = case
        return self._persist_case(case_id)

    def update_info_section_titles(self, case_id: str, section_titles: Dict[str, Any]) -> bool:
        """更新案件信息分组标题。"""
        if case_id not in self._cases:
            return False

        case = self._cases[case_id]
        current_titles = case.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES)
        case["info_section_titles"] = _normalize_info_section_titles({
            **current_titles,
            **dict(section_titles or {}),
        })
        case["updated_at"] = datetime.now().isoformat()
        self._cases[case_id] = case
        return self._persist_case(case_id)

    def toggle_info_field_tag(self, case_id: str, field_id: str, enabled: Optional[bool] = None) -> bool:
        """切换案件信息字段的标签映射状态。"""
        if case_id not in self._cases:
            return False

        case = self._cases[case_id]
        old_info_fields = deepcopy(case.get("info_fields", []))
        changed = False
        for field in case.get("info_fields", []):
            if field.get("id") != field_id:
                continue
            target_enabled = not field.get("map_to_tag", False) if enabled is None else bool(enabled)
            field["map_to_tag"] = target_enabled
            changed = True
            break

        if not changed:
            return False

        case["tags"] = self._merge_manual_and_field_tags(
            case.get("tags", []),
            old_info_fields,
            case.get("info_fields", []),
        )
        case["updated_at"] = datetime.now().isoformat()
        self._cases[case_id] = case
        return self._persist_case(case_id)

    def update_case_notes(self, case_id: str, notes: str, slot: str = "primary") -> bool:
        """更新案件笔记，并同步到文件夹 sidecar。"""
        if case_id not in self._cases:
            return False

        case = self._cases[case_id]
        key = "notes_secondary" if slot == "secondary" else "notes"
        case[key] = str(notes or "")
        case["updated_at"] = datetime.now().isoformat()
        self._cases[case_id] = case
        return self._persist_case(case_id)

    def export_case_info(self, case_id: str, output_path: Path) -> bool:
        """导出案件信息到文件。"""
        case = self.get_case(case_id)
        if not case:
            return False

        output_path = Path(output_path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._logger.error(f"创建导出目录失败: {exc}")
            return False

        payload = {
            "id": case.get("id", ""),
            "name": case.get("name", ""),
            "category": case.get("category", ""),
            "status": case.get("status", ""),
            "folder_status": case.get("folder_status", ""),
            "path": case.get("path", ""),
            "path_history": case.get("path_history", []),
            "tags": case.get("tags", []),
            "variables": case.get("variables", {}),
            "info_fields": case.get("info_fields", []),
            "info_section_titles": case.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES),
            "deadlines": case.get("deadlines", []),
            "notes": case.get("notes", ""),
            "notes_secondary": case.get("notes_secondary", ""),
            "notes_split": bool(case.get("notes_split", False)),
            "created_at": case.get("created_at", ""),
            "updated_at": case.get("updated_at", ""),
        }

        try:
            if output_path.suffix.lower() == ".json":
                output_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                output_path.write_text(self._build_markdown_export(case), encoding="utf-8")
        except Exception as exc:
            self._logger.error(f"导出案件信息失败: {exc}")
            return False

        return True

    def export_case_work_log(self, case_id: str, output_path: Path) -> bool:
        """根据案件期限导出固定格式的工作日志。"""
        case = self.get_case(case_id)
        if not case:
            return False

        output_path = Path(output_path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._logger.error(f"创建工作日志导出目录失败: {exc}")
            return False

        try:
            output_path.write_text(self._build_deadline_work_log(case), encoding="utf-8")
        except Exception as exc:
            self._logger.error(f"导出案件工作日志失败: {exc}")
            return False

        return True

    def _build_markdown_export(self, case: Dict[str, Any]) -> str:
        """构建 Markdown 导出内容（统一日历导出风格）。"""
        section_titles = case.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES)
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            f"# 📁 {case.get('name', '未命名案件')}",
            "",
            f"> **案件信息导出** ｜ 生成于 {generated_at}",
            "",
            "## 📋 基本信息",
            "",
            f"- **案件类型**：{case.get('category', '') or '未填写'}",
            f"- **业务状态**：{case.get('status', '') or '未填写'}",
            f"- **目录状态**：{case.get('folder_status', '') or '未填写'}",
            f"- **当前路径**：{case.get('path', '') or '未关联'}",
            "",
        ]

        tags = case.get("tags", [])
        lines.append("## 🏷️ 标签")
        lines.append("")
        if tags:
            lines.append(" · ".join(f"`{tag}`" for tag in tags))
        else:
            lines.append("> 暂无标签")
        lines.append("")

        # 案件信息字段
        grouped_fields: Dict[str, List[Dict[str, Any]]] = {
            "basic": [],
            "parties": [],
            "business": [],
            "custom": [],
        }
        for field in case.get("info_fields", []):
            section_key = _INFO_SECTION_BY_KEY.get(field.get("key", ""), "custom")
            if field.get("builtin", False):
                grouped_fields.setdefault(section_key, []).append(field)
            else:
                grouped_fields["custom"].append(field)

        has_any_fields = any(grouped_fields.get(k, []) for k in ("basic", "parties", "business", "custom"))
        if has_any_fields:
            lines.append("## 📑 案件信息")
            lines.append("")
            for section_key in ("basic", "parties", "business", "custom"):
                fields = grouped_fields.get(section_key, [])
                if not fields:
                    continue
                section_title = section_titles.get(section_key, DEFAULT_INFO_SECTION_TITLES[section_key])
                lines.append(f"### {section_title}")
                lines.append("")
                for field in fields:
                    label = field.get("label", "未命名字段")
                    value = field.get("value", "") or "未填写"
                    lines.append(f"- **{label}**：{value}")
                lines.append("")

        # 期限提醒
        lines.append("## ⏰ 期限提醒")
        lines.append("")
        deadlines = case.get("deadlines", [])
        if deadlines:
            for deadline in deadlines:
                title = deadline.get("title", "未命名期限")
                date_text = deadline.get("date", "")
                time_text = "全天" if deadline.get("all_day", True) else (deadline.get("time", "") or "09:00")
                status = str(deadline.get("status", "pending")).strip()
                dl_type = str(deadline.get("type", "deadline")).strip()
                description = str(deadline.get("description", "")).strip()

                status_emoji = "✅" if status == "completed" else "⚠️" if status == "overdue" else "⏳"
                type_label = {"deadline": "普通期限", "hearing": "开庭/庭前", "custom": "自定义提醒"}.get(dl_type, "普通期限")

                lines.append(f"{status_emoji} **{title}** ｜ `{date_text} {time_text}`")
                lines.append("")
                lines.append(f"   类型：{type_label} ｜ 状态：{'已完成' if status == 'completed' else '已逾期' if status == 'overdue' else '待处理'}")
                if description:
                    lines.append(f"   > {description}")
                lines.append("")
        else:
            lines.append("> 暂无期限事项")
            lines.append("")

        # 笔记
        notes = str(case.get("notes", "") or "").strip()
        if notes:
            lines.append("## 📝 主笔记")
            lines.append("")
            lines.append(notes)
            lines.append("")

        secondary_notes = str(case.get("notes_secondary", "") or "").strip()
        if secondary_notes:
            lines.append("## 📝 副笔记")
            lines.append("")
            lines.append(secondary_notes)
            lines.append("")

        lines.append("---")
        lines.append(f"*由 案件文件夹管理系统 生成于 {generated_at}*")
        lines.append("")
        return "\n".join(lines)

    def _build_deadline_work_log(self, case: Dict[str, Any]) -> str:
        """根据期限事项构建统一风格的工作日志（Markdown）。"""
        deadlines = list(case.get("deadlines", []))
        pending = [item for item in deadlines if str(item.get("status", "pending")).strip() != "completed"]
        completed = [item for item in deadlines if str(item.get("status", "pending")).strip() == "completed"]

        def sort_key(item: Dict[str, Any]) -> Tuple[str, str]:
            date_text = str(item.get("date", "")).strip()
            time_text = "" if item.get("all_day", True) else (str(item.get("time", "")).strip() or "09:00")
            return (date_text, time_text)

        pending.sort(key=sort_key)
        completed.sort(key=sort_key)

        def status_emoji(status: str) -> str:
            return "✅" if status == "completed" else "⏳"

        def type_label(item: Dict[str, Any]) -> str:
            mapping = {"deadline": "普通期限", "hearing": "开庭/庭前", "custom": "自定义提醒"}
            return mapping.get(str(item.get("type", "deadline")).strip(), "普通期限")

        def format_time(item: Dict[str, Any]) -> str:
            if item.get("all_day", True):
                return "全天"
            return str(item.get("time", "")).strip() or "09:00"

        def remind_text(item: Dict[str, Any]) -> str:
            remind_before = item.get("remind_before", [])
            if isinstance(remind_before, list) and remind_before:
                return "提前 " + "/".join(str(day) for day in remind_before) + " 天"
            return "未设置"

        def append_items(lines: List[str], items: List[Dict[str, Any]]) -> None:
            if not items:
                lines.extend(["> 暂无记录", ""])
                return
            for item in items:
                title = item.get("title", "未命名事项") or "未命名事项"
                date_text = str(item.get("date", "")).strip() or "未填写"
                time_text = format_time(item)
                dl_type = type_label(item)
                status = str(item.get("status", "pending")).strip()
                description = str(item.get("description", "")).strip()

                lines.append(f"{status_emoji(status)} **{title}** ｜ `{date_text} {time_text}`")
                lines.append("")
                lines.append(f"   类型：{dl_type} ｜ 状态：{'已完成' if status == 'completed' else '待处理'} ｜ 提醒：{remind_text(item)}")
                if description:
                    lines.append(f"   > {description}")
                lines.append("")

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"# 📋 {case.get('name', '未命名案件')} — 工作日志",
            "",
            f"> **期限事项汇总** ｜ 生成于 {generated_at}",
            "",
            "## 📊 统计概览",
            "",
            f"- **期限总数**：{len(deadlines)}",
            f"- **待处理**：{len(pending)}",
            f"- **已完成**：{len(completed)}",
            f"- **办理状态**：{case.get('status', '') or '未填写'}",
            f"- **案件类型**：{case.get('category', '') or '未填写'}",
            f"- **当前路径**：{case.get('path', '') or '未关联'}",
            "",
            "## ⏳ 待处理事项",
            "",
        ]
        append_items(lines, pending)
        lines.extend(["## ✅ 已完成事项", ""])
        append_items(lines, completed)
        lines.extend([
            "## 💡 工作提示",
            "",
            "> 请结合案件实际进展，将本日志与笔记、案卷文件预览同步更新。",
            "> 已完成事项建议在案件期限页保持完成状态，以免左侧列表持续高亮提醒。",
            "",
            "---",
            f"*由 案件文件夹管理系统 生成于 {generated_at}*",
            "",
        ])
        return "\n".join(lines)

    def _merge_manual_and_field_tags(
        self,
        current_tags: List[str],
        old_info_fields: Iterable[Dict[str, Any]],
        new_info_fields: Iterable[Dict[str, Any]],
    ) -> List[str]:
        """合并手动标签与字段映射标签。"""
        old_derived = {
            _build_info_field_tag(field)
            for field in old_info_fields or []
            if field.get("map_to_tag") and _build_info_field_tag(field)
        }
        manual_tags = [tag for tag in current_tags if tag not in old_derived]

        new_derived = [
            _build_info_field_tag(field)
            for field in new_info_fields or []
            if field.get("map_to_tag") and _build_info_field_tag(field)
        ]
        return _normalize_tags(manual_tags + new_derived)

    # ── 期限管理 ──

    def add_deadline(self, case_id: str, deadline: Dict[str, Any]) -> str:
        """为案件添加期限。"""
        if case_id not in self._cases:
            return ""

        normalized = _normalize_deadline(deadline)
        self._cases[case_id].setdefault("deadlines", []).append(normalized)
        self._cases[case_id]["updated_at"] = datetime.now().isoformat()
        self._persist_case(case_id)
        return normalized["id"]

    def add_global_deadline(self, deadline: Dict[str, Any]) -> str:
        """添加未关联案件的全局期限。"""
        normalized = _normalize_deadline(deadline)
        self._global_deadlines.append(normalized)
        self.save()
        return normalized["id"]

    def remove_deadline(self, case_id: str, deadline_id: str) -> bool:
        """删除期限。"""
        if case_id not in self._cases:
            return False

        deadlines = self._cases[case_id].get("deadlines", [])
        new_deadlines = [item for item in deadlines if item.get("id") != deadline_id]
        if len(new_deadlines) == len(deadlines):
            return False

        self._cases[case_id]["deadlines"] = new_deadlines
        self._cases[case_id]["updated_at"] = datetime.now().isoformat()
        return self._persist_case(case_id)

    def remove_global_deadline(self, deadline_id: str) -> bool:
        """删除未关联案件的全局期限。"""
        new_deadlines = [item for item in self._global_deadlines if item.get("id") != deadline_id]
        if len(new_deadlines) == len(self._global_deadlines):
            return False
        self._global_deadlines = new_deadlines
        return self.save()

    def update_deadline(self, case_id: str, deadline_id: str, updates: Dict[str, Any]) -> bool:
        """更新指定期限。"""
        if case_id not in self._cases:
            return False

        deadlines = self._cases[case_id].get("deadlines", [])
        for index, deadline in enumerate(deadlines):
            if deadline.get("id") != deadline_id:
                continue

            cleaned_updates = dict(updates)
            cleaned_updates.pop("id", None)
            updated_deadline = _normalize_deadline({**deadline, **cleaned_updates, "id": deadline_id})
            deadlines[index] = updated_deadline
            self._cases[case_id]["updated_at"] = datetime.now().isoformat()
            return self._persist_case(case_id)

        return False

    def update_global_deadline(self, deadline_id: str, updates: Dict[str, Any]) -> bool:
        """更新未关联案件的全局期限。"""
        for index, deadline in enumerate(self._global_deadlines):
            if deadline.get("id") != deadline_id:
                continue

            cleaned_updates = dict(updates)
            cleaned_updates.pop("id", None)
            self._global_deadlines[index] = _normalize_deadline(
                {**deadline, **cleaned_updates, "id": deadline_id}
            )
            return self.save()
        return False

    def get_deadlines_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        """获取案件的所有期限。"""
        case = self.get_case(case_id)
        if not case:
            return []
        return deepcopy(case.get("deadlines", []))

    def get_global_deadlines(self) -> List[Dict[str, Any]]:
        """获取未关联案件的全局期限。"""
        return deepcopy(self._global_deadlines)

    def get_deadlines_by_date_range(self, start: str, end: str) -> List[Dict[str, Any]]:
        """获取日期范围内的所有期限，返回带案件信息的列表。"""
        results = []
        for case_id, case in self._cases.items():
            for deadline in case.get("deadlines", []):
                deadline_date = deadline.get("date", "")
                if start <= deadline_date <= end:
                    results.append({
                        **deadline,
                        "case_id": case_id,
                        "case_name": case.get("name", ""),
                    })
        for deadline in self._global_deadlines:
            deadline_date = deadline.get("date", "")
            if start <= deadline_date <= end:
                results.append({
                    **deadline,
                    "case_id": "",
                    "case_name": "未关联案件",
                })
        results.sort(key=lambda item: (item.get("date", ""), item.get("time", "")))
        return results

    def get_all_deadlines(self) -> List[Dict[str, Any]]:
        """获取所有期限。"""
        results = []
        for case_id, case in self._cases.items():
            for deadline in case.get("deadlines", []):
                results.append({
                    **deadline,
                    "case_id": case_id,
                    "case_name": case.get("name", ""),
                })
        for deadline in self._global_deadlines:
            results.append({
                **deadline,
                "case_id": "",
                "case_name": "未关联案件",
            })
        results.sort(key=lambda item: (item.get("date", ""), item.get("time", "")))
        return results


def get_case_manager() -> CaseManager:
    """获取路径管理器实例。"""
    return CaseManager()
