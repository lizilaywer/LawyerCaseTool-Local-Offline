# -*- coding: utf-8 -*-
"""法院短信文书读取服务。"""

from __future__ import annotations

import functools
import json
import re
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.path_manager import get_path_manager
from src.utils.logger import get_logger
from src.utils.validators import sanitize_filename

# 下载文件最大大小限制（100MB）
_MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import fitz  # type: ignore
except ImportError:
    fitz = None


_CASE_NUMBER_PATTERN = re.compile(r"[（(]\s*\d{4}\s*[)）][^，。；;、\\s]{2,40}?号")
_COURT_BRACKET_PATTERN = re.compile(r"【([^】]{2,40})】")
_URL_PATTERN = re.compile(r"https?://[^\s]+")
_RECIPIENT_PATTERN = re.compile(r"】\s*([^，。,；;]{1,30})[，,]")
_HEARING_DOC_KEYWORDS = ("传票", "出庭通知书", "开庭通知书")

_DATETIME_PATTERN = re.compile(
    r"(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日"
    r"(?:(?P<ampm>上午|下午|晚上|中午)?(?P<hour>\d{1,2})(?:[:：时点](?P<minute>\d{1,2})|[时点]半)?)?"
)
_CHINESE_DATETIME_PATTERN = re.compile(
    r"(?P<year>[二〇零一二三四五六七八九]{4})年(?P<month>[〇零一二三四五六七八九十]{1,3})月(?P<day>[〇零一二三四五六七八九十]{1,3})日"
)
_ISSUE_DATE_PATTERN = re.compile(
    r"(二[〇零一二三四五六七八九]{3}年[〇零一二三四五六七八九十]{1,3}月[〇零一二三四五六七八九十]{1,3}日)"
)
_WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"^[A-Za-z]:/")
_SAFE_DOCUMENT_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "jpg",
    "jpeg",
    "png",
    "txt",
}

_CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(r"\s+", "", text)


def _normalize_case_number(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    return (
        text.replace("(", "（")
        .replace(")", "）")
        .replace("〔", "（")
        .replace("〕", "）")
        .replace("[", "（")
        .replace("]", "）")
    )


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _sanitize_relative_path(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if (
        text.startswith("/")
        or text.startswith("//")
        or _WINDOWS_ABSOLUTE_PATH_PATTERN.match(text)
    ):
        raise ValueError("保存子目录不能是绝对路径。")

    text = re.sub(r"[<>:\"|?*]", "_", text)
    parts = []
    for raw_part in text.split("/"):
        stripped_part = raw_part.strip()
        if not stripped_part:
            continue
        if stripped_part in {".", ".."}:
            raise ValueError("保存子目录不能包含 . 或 ..。")
        safe_part = stripped_part.rstrip(".")
        if not safe_part or safe_part in {".", ".."}:
            raise ValueError("保存子目录包含无效路径片段。")
        parts.append(safe_part)
    return "/".join(parts)


def _sanitize_document_extension(value: str) -> str:
    ext = str(value or "").strip().lower().lstrip(".")
    ext = re.sub(r"[^a-z0-9]", "", ext)
    if ext not in _SAFE_DOCUMENT_EXTENSIONS:
        return "pdf"
    return ext


def _sanitize_document_filename(name: str, extname: str, fallback: str = "法院文书") -> str:
    safe_ext = _sanitize_document_extension(extname)
    raw_name = str(name or "").strip().replace("\\", "/")
    basename = Path(raw_name).name if raw_name else ""
    if not basename:
        basename = str(fallback or "").strip().replace("\\", "/")
        basename = Path(basename).name if basename else ""
    basename = sanitize_filename(basename or "法院文书").strip(" .")
    if not basename:
        basename = "法院文书"

    suffix = f".{safe_ext}"
    if not basename.lower().endswith(suffix):
        basename = f"{basename}{suffix}"
    return basename


def _resolve_child_path(base_dir: Path, child_path: Path) -> Path:
    base_resolved = base_dir.resolve()
    child_resolved = child_path.resolve()
    try:
        child_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError("目标路径超出允许目录。") from exc
    return child_resolved


def _ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem} ({counter}){suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _extract_fragment_query(url: str) -> Dict[str, str]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if parsed.fragment and "?" in parsed.fragment:
        _, fragment_query = parsed.fragment.split("?", 1)
        query.update(parse_qs(fragment_query))
    return {
        key: values[0].strip()
        for key, values in query.items()
        if values and str(values[0]).strip()
    }


def _extract_case_field(case: Dict[str, Any], key: str) -> str:
    variables = case.get("variables", {}) or {}
    if key in variables and str(variables.get(key, "")).strip():
        return str(variables.get(key, "")).strip()

    for field in case.get("info_fields", []) or []:
        if str(field.get("key", "")).strip() == key:
            return str(field.get("value", "")).strip()
    return ""


@functools.lru_cache(maxsize=128)
def _build_labeled_regex(label_tuple: tuple, end_tuple: tuple) -> Optional[re.Pattern]:
    label_pattern = "|".join(re.escape(label) for label in label_tuple)
    end_pattern = "|".join(re.escape(label) for label in end_tuple)
    if not label_pattern:
        return None
    return re.compile(
        rf"(?:{label_pattern})[:：]?(?P<value>.*?)(?=(?:{end_pattern})[:：]?|$)"
    )


def _extract_labeled_value(text: str, labels: Iterable[str], end_labels: Iterable[str], max_chars: int = 80) -> str:
    compact = _compact_text(text)
    if not compact:
        return ""

    pattern = _build_labeled_regex(tuple(labels), tuple(end_labels))
    if pattern is None:
        return ""

    match = pattern.search(compact)
    if not match:
        return ""
    return match.group("value").strip("：:，,。；;、 ")[:max_chars]


def _convert_chinese_numeral_segment(text: str) -> int:
    compact = str(text or "").strip()
    if not compact:
        return 0
    if compact.isdigit():
        return int(compact)
    if compact == "十":
        return 10
    if compact.startswith("十"):
        return 10 + _CHINESE_DIGITS.get(compact[1], 0)
    if compact.endswith("十"):
        return _CHINESE_DIGITS.get(compact[0], 0) * 10
    if "十" in compact:
        left, right = compact.split("十", 1)
        return _CHINESE_DIGITS.get(left, 0) * 10 + _CHINESE_DIGITS.get(right, 0)
    return _CHINESE_DIGITS.get(compact, 0)


def _parse_notice_datetime(value: str) -> tuple[str, str]:
    compact = _compact_text(value)
    if not compact:
        return "", ""

    match = _DATETIME_PATTERN.search(compact)
    if match:
        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))
        hour_text = match.group("hour")
        minute_text = match.group("minute")
        ampm = match.group("ampm") or ""
        date_text = f"{year:04d}-{month:02d}-{day:02d}"
        if not hour_text:
            return date_text, ""
        hour = int(hour_text)
        minute = 30 if "半" in compact[match.start():match.end()] and not minute_text else int(minute_text or 0)
        if ampm in {"下午", "晚上", "中午"} and hour < 12:
            hour += 12
        return date_text, f"{hour:02d}:{minute:02d}"

    chinese_match = _CHINESE_DATETIME_PATTERN.search(compact)
    if not chinese_match:
        return "", ""

    year = int("".join(str(_CHINESE_DIGITS.get(ch, 0)) for ch in chinese_match.group("year")))
    month = _convert_chinese_numeral_segment(chinese_match.group("month"))
    day = _convert_chinese_numeral_segment(chinese_match.group("day"))
    return f"{year:04d}-{month:02d}-{day:02d}", ""


def _extract_issue_date_text(text: str) -> str:
    compact = _compact_text(text)
    match = _ISSUE_DATE_PATTERN.search(compact)
    return match.group(1) if match else ""


@dataclass
class CourtSmsParseResult:
    raw_text: str
    link: str
    court_name: str = ""
    recipient_name: str = ""
    case_number: str = ""
    qdbh: str = ""
    sdbh: str = ""
    sdsin: str = ""
    password: str = ""
    host: str = "https://zxfw.court.gov.cn"

    @property
    def is_complete(self) -> bool:
        return bool(self.link and self.qdbh and self.sdbh and self.sdsin)


@dataclass
class CourtSmsDocument:
    name: str
    extname: str
    download_url: str
    document_id: str = ""
    created_at: str = ""
    court_name: str = ""
    court_id: str = ""
    storage_key: str = ""
    local_path: str = ""
    size_bytes: int = 0


@dataclass
class CourtSmsHearingNotice:
    document_name: str
    document_path: str
    notice_type: str = ""
    case_number: str = ""
    cause: str = ""
    summoned_person: str = ""
    hearing_date: str = ""
    hearing_time: str = ""
    hearing_place: str = ""
    signer: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    court_name: str = ""
    issue_date_text: str = ""
    raw_text: str = ""
    added_case_id: str = ""
    added_deadline_id: str = ""

    @property
    def display_time(self) -> str:
        if self.hearing_date and self.hearing_time:
            return f"{self.hearing_date} {self.hearing_time}"
        return self.hearing_date or "未识别"


@dataclass
class CourtSmsCaseMatch:
    case_id: str
    case_name: str
    case_path: str
    score: int
    reasons: List[str] = field(default_factory=list)


class CourtSmsService:
    """解析法院短信、读取文书并匹配案件。"""

    def __init__(self) -> None:
        self._logger = get_logger()
        self._path_manager = get_path_manager()
        self._path_manager.ensure_directories()
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=5, pool_maxsize=10)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def parse_sms(self, sms_text: str) -> CourtSmsParseResult:
        """解析法院短信文本。"""
        text = str(sms_text or "").strip()
        if not text:
            raise ValueError("请先粘贴法院短信内容。")

        link_match = _URL_PATTERN.search(text)
        if not link_match:
            raise ValueError("短信中未识别到可访问链接。")
        link = link_match.group(0).strip().rstrip("。；;，,")

        query = _extract_fragment_query(link)
        result = CourtSmsParseResult(
            raw_text=text,
            link=link,
            court_name="",
            recipient_name="",
            case_number="",
            qdbh=query.get("qdbh", ""),
            sdbh=query.get("sdbh", ""),
            sdsin=query.get("sdsin", ""),
            password=query.get("mm", ""),
            host=f"{urlparse(link).scheme}://{urlparse(link).netloc}" if urlparse(link).scheme else "https://zxfw.court.gov.cn",
        )

        court_match = _COURT_BRACKET_PATTERN.search(text)
        if court_match:
            result.court_name = court_match.group(1).strip()

        if result.court_name:
            recipient_match = _RECIPIENT_PATTERN.search(text)
            if recipient_match:
                result.recipient_name = recipient_match.group(1).strip()

        if not result.recipient_name:
            generic_recipient = _RECIPIENT_PATTERN.search(text)
            if generic_recipient:
                result.recipient_name = generic_recipient.group(1).strip()

        case_match = _CASE_NUMBER_PATTERN.search(text)
        if case_match:
            result.case_number = _normalize_case_number(case_match.group(0))

        if not result.is_complete:
            raise ValueError("短信链接缺少必要参数，无法读取法院文书。")
        return result

    def fetch_documents(self, parsed: CourtSmsParseResult, timeout: int = 30) -> List[CourtSmsDocument]:
        """读取法院短信链接对应的文书列表。"""
        url = f"{parsed.host}/yzw/yzw-zxfw-sdfw/api/v1/sdfw/getWsListBySdbhNew"
        payload = {
            "sdbh": parsed.sdbh,
            "qdbh": parsed.qdbh,
            "sdsin": parsed.sdsin,
            "mm": parsed.password,
        }
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Referer": f"{parsed.host}/zxfw/",
            "User-Agent": "LEXORA/1.0",
        }

        response = self._session.post(url, json=payload, headers=headers, timeout=timeout, verify=True)
        response.raise_for_status()

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ValueError("法院服务返回内容无法解析。") from exc

        if int(data.get("code", 0)) != 200:
            raise ValueError(str(data.get("msg") or data.get("message") or "法院服务返回失败。"))

        documents: List[CourtSmsDocument] = []
        for item in data.get("data", []) or []:
            name = str(item.get("c_wsmc", "")).strip()
            extname = _sanitize_document_extension(str(item.get("c_wjgs", "")).strip())
            filename = _sanitize_document_filename(
                name,
                extname,
                str(item.get("c_wsbh", "")).strip() or "法院文书",
            )
            documents.append(
                CourtSmsDocument(
                    name=filename,
                    extname=extname,
                    download_url=str(item.get("wjlj", "")).strip(),
                    document_id=str(item.get("c_wsbh", "")).strip(),
                    created_at=str(item.get("dt_cjsj", "")).strip(),
                    court_name=str(item.get("c_fymc", "")).strip() or parsed.court_name,
                    court_id=str(item.get("c_fybh", "")).strip(),
                    storage_key=str(item.get("c_stbh", "")).strip(),
                )
            )

        if not documents:
            raise ValueError("未读取到任何法院文书。")
        return documents

    def download_documents(
        self,
        documents: Iterable[CourtSmsDocument],
        parsed: CourtSmsParseResult,
        timeout: int = 60,
        max_workers: int = 4,
    ) -> Path:
        """把法院文书下载到本地暂存目录（支持并发下载）。"""
        session_name = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:6]}"
        session_dir = self._path_manager.cache_dir / "court_sms" / session_name
        session_dir.mkdir(parents=True, exist_ok=True)

        doc_list = list(documents)
        if len(doc_list) <= 1:
            # 单文件串行处理，避免线程池开销
            for document in doc_list:
                self._download_one_document(document, parsed, session_dir, timeout)
            return session_dir

        def _worker(document: CourtSmsDocument) -> None:
            self._download_one_document(document, parsed, session_dir, timeout)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(_worker, doc_list))

        return session_dir

    def _download_one_document(
        self,
        document: CourtSmsDocument,
        parsed: CourtSmsParseResult,
        session_dir: Path,
        timeout: int,
    ) -> None:
        if not document.download_url:
            return
        safe_name = _sanitize_document_filename(document.name, document.extname)
        target_path = _ensure_unique_path(_resolve_child_path(session_dir, session_dir / safe_name))
        headers = {
            "Referer": f"{parsed.host}/zxfw/",
            "User-Agent": "LEXORA/1.0",
        }
        with self._session.get(
            document.download_url, headers=headers, stream=True, timeout=timeout, verify=True
        ) as response:
            response.raise_for_status()
            total = 0
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        total += len(chunk)
                        if total > _MAX_DOWNLOAD_SIZE:
                            target_path.unlink(missing_ok=True)
                            raise ValueError(f"文件大小超出限制({_MAX_DOWNLOAD_SIZE // 1024 // 1024}MB)")
                        f.write(chunk)
        document.local_path = str(target_path)
        document.size_bytes = target_path.stat().st_size

    def suggest_relative_folder(self, parsed: CourtSmsParseResult) -> str:
        """生成默认保存相对目录。"""
        parts = ["法院送达文书"]
        title_parts = []
        if parsed.case_number:
            title_parts.append(parsed.case_number)
        if parsed.court_name:
            title_parts.append(parsed.court_name)
        if not title_parts:
            title_parts.append(datetime.now().strftime("%Y-%m-%d"))
        parts.append("_".join(title_parts))
        return _sanitize_relative_path("/".join(parts))

    def match_cases(
        self,
        parsed: CourtSmsParseResult,
        cases: Iterable[Dict[str, Any]],
        preferred_case_id: str = "",
    ) -> List[CourtSmsCaseMatch]:
        """根据案号、法院、当事人自动匹配案件。"""
        target_case_number = _normalize_case_number(parsed.case_number)
        target_recipient = _normalize_text(parsed.recipient_name).lower()
        target_court = _normalize_text(parsed.court_name).lower()
        suggestions: List[CourtSmsCaseMatch] = []

        for case in cases:
            case_id = str(case.get("id", "")).strip()
            case_name = str(case.get("name", "")).strip()
            case_path = str(case.get("path", "")).strip()
            score = 0
            reasons: List[str] = []

            case_number_values = [
                _extract_case_field(case, "case_number"),
                str(case.get("variables", {}).get("case_number", "")).strip(),
                case_name,
            ]
            normalized_numbers = {
                _normalize_case_number(value)
                for value in case_number_values
                if _normalize_case_number(value)
            }
            if target_case_number and target_case_number in normalized_numbers:
                score += 120
                reasons.append("案号完全匹配")

            party_values = [
                _extract_case_field(case, "party_name"),
                _extract_case_field(case, "opponent_name"),
                str(case.get("variables", {}).get("client_name", "")).strip(),
                str(case.get("variables", {}).get("opponent_client_name", "")).strip(),
                case_name,
            ]
            if target_recipient and any(target_recipient in _normalize_text(value).lower() for value in party_values if value):
                score += 35
                reasons.append("当事人姓名匹配")

            forum_values = [
                _extract_case_field(case, "forum"),
                str(case.get("variables", {}).get("court_name", "")).strip(),
                case_name,
            ]
            if target_court and any(target_court in _normalize_text(value).lower() for value in forum_values if value):
                score += 24
                reasons.append("法院名称匹配")

            if preferred_case_id and case_id == preferred_case_id:
                score += 12
                reasons.append("来自当前案件上下文")

            if score <= 0:
                continue

            suggestions.append(
                CourtSmsCaseMatch(
                    case_id=case_id,
                    case_name=case_name,
                    case_path=case_path,
                    score=score,
                    reasons=reasons,
                )
            )

        suggestions.sort(key=lambda item: (-item.score, item.case_name))
        return suggestions

    def save_documents_to_case(
        self,
        case_record: Dict[str, Any],
        documents: Iterable[CourtSmsDocument],
        relative_folder: str,
    ) -> List[Path]:
        """把暂存文书复制到案件目录。"""
        case_path = Path(str(case_record.get("path", "")).strip())
        if not case_path.exists() or not case_path.is_dir():
            raise ValueError("目标案件目录不存在，无法保存法院文书。")

        return self.save_documents_to_directory(case_path, documents, relative_folder)

    def save_documents_to_directory(
        self,
        base_dir: Path | str,
        documents: Iterable[CourtSmsDocument],
        relative_folder: str = "",
    ) -> List[Path]:
        """把暂存文书复制到任意目录。"""
        base_path = Path(str(base_dir).strip())
        if not str(base_path).strip():
            raise ValueError("目标保存目录不能为空。")
        if base_path.exists() and not base_path.is_dir():
            raise ValueError("目标保存位置不是文件夹。")

        safe_relative = _sanitize_relative_path(relative_folder)
        target_dir = base_path / Path(safe_relative) if safe_relative else base_path
        target_dir = _resolve_child_path(base_path, target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        saved_paths: List[Path] = []
        for document in documents:
            source_path = Path(str(document.local_path or "").strip())
            if not source_path.exists():
                raise FileNotFoundError(f"暂存文件不存在：{source_path}")
            destination = _ensure_unique_path(target_dir / source_path.name)
            shutil.copy2(source_path, destination)
            saved_paths.append(destination)
        return saved_paths

    def extract_pdf_text(self, pdf_path: str, *, allow_pymupdf_fallback: bool = False) -> str:
        """提取 PDF 文本，优先使用 pypdf；默认不回退到 PyMuPDF 以避免原生库偶发闪退。"""
        path = Path(str(pdf_path or "").strip())
        if not path.exists() or not path.is_file():
            return ""

        if PdfReader is not None:
            try:
                reader = PdfReader(str(path))
                return "\n".join((page.extract_text() or "") for page in reader.pages)
            except Exception as exc:
                self._logger.warning(f"pypdf 提取 PDF 文本失败，尝试回退到 PyMuPDF: {path} | {exc}")

        if fitz is not None and allow_pymupdf_fallback:
            try:
                doc = fitz.open(str(path))
                try:
                    text = "\n".join(page.get_text() or "" for page in doc)
                finally:
                    doc.close()
                return text
            except Exception as exc:
                self._logger.warning(f"PyMuPDF 提取 PDF 文本失败: {path} | {exc}")

        if fitz is not None and not allow_pymupdf_fallback:
            self._logger.info(f"已跳过 PyMuPDF 回退以提升法院文书识别稳定性: {path}")
        if PdfReader is None and fitz is None:
            self._logger.warning(f"当前环境未安装可用的 PDF 文本提取依赖，无法识别: {path}")
        else:
            self._logger.warning(f"PDF 文本提取未成功，已跳过不稳定的回退路径: {path}")
        return ""

    def extract_text_from_file(self, file_path: str) -> str:
        """从 PDF 或图片文件提取文本。

        - PDF：优先 pypdf 文本提取，失败后尝试 OCR 回退
        - 图片 (jpg/png/bmp)：使用 RapidOCR 识别
        """
        path = Path(str(file_path or "").strip())
        if not path.exists() or not path.is_file():
            return ""

        ext = path.suffix.lower()

        # PDF：先尝试文本提取
        if ext == ".pdf":
            text = self.extract_pdf_text(str(path), allow_pymupdf_fallback=True)
            if text.strip():
                return text
            # 文本提取为空（扫描件），尝试 OCR 回退
            return self._ocr_pdf_pages(path)

        # 图片：直接 OCR
        if ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"):
            return self._ocr_image(str(path))

        return ""

    def _ocr_image(self, image_path: str) -> str:
        """使用 RapidOCR 识别单张图片。"""
        try:
            from src.core.ocr.paddle_engine import get_ocr_engine
            engine = get_ocr_engine()
            if not engine.is_ready():
                self._logger.warning(f"OCR 引擎未就绪，无法识别图片: {image_path}")
                return ""
            results = engine.recognize(image_path)
            return "\n".join(block.text for block in results if block.text)
        except Exception as exc:
            self._logger.warning(f"OCR 识别图片失败: {image_path} | {exc}")
            return ""

    def _ocr_pdf_pages(self, pdf_path: Path) -> str:
        """将 PDF 页面渲染为图片后逐页 OCR。"""
        if fitz is None:
            return ""
        try:
            from src.core.ocr.paddle_engine import get_ocr_engine
            engine = get_ocr_engine()
            if not engine.is_ready():
                return ""
            import tempfile
            texts = []
            doc = fitz.open(str(pdf_path))
            try:
                for page in doc:
                    pix = page.get_pixmap(dpi=200)
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                        tmp = f.name
                    pix.save(tmp)
                    try:
                        results = engine.recognize(tmp)
                        page_text = "\n".join(block.text for block in results if block.text)
                        if page_text:
                            texts.append(page_text)
                    finally:
                        Path(tmp).unlink(missing_ok=True)
            finally:
                doc.close()
            return "\n".join(texts)
        except Exception as exc:
            self._logger.warning(f"PDF OCR 回退失败: {pdf_path} | {exc}")
            return ""

    def _fallback_extract_datetime_from_ocr(self, compact: str) -> tuple[str, str]:
        """OCR 分散文本回退：将分散的年月和日时拼合。

        OCR 传票常见格式：
        "2026年05月...09日09:00" 或 "2026年5月9日9时0分"
        """
        # 模式1: "年XX月" 和 "XX日XX:XX" 分散
        m1 = re.search(r"(\d{4})年(\d{1,2})月", compact)
        m2 = re.search(r"(\d{1,2})日(\d{1,2}):(\d{2})", compact)
        if m1 and m2:
            y, mo = int(m1.group(1)), int(m1.group(2))
            d, h, mi = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            return f"{y:04d}-{mo:02d}-{d:02d}", f"{h:02d}:{mi:02d}"

        # 模式2: "年XX月XX日XX时XX分" 连续
        m3 = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2})[时:](\d{1,2})[分:]?", compact)
        if m3:
            y, mo, d = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
            h, mi = int(m3.group(4)), int(m3.group(5))
            return f"{y:04d}-{mo:02d}-{d:02d}", f"{h:02d}:{mi:02d}"

        # 模式3: 只有 "年XX月XX日"
        m4 = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", compact)
        if m4:
            y, mo, d = int(m4.group(1)), int(m4.group(2)), int(m4.group(3))
            return f"{y:04d}-{mo:02d}-{d:02d}", ""

        return "", ""

    def _extract_summoned_person(self, compact: str, raw_text: str) -> str:
        """提取被传唤人/被通知人姓名。

        PDF 文本格式：'被传唤人姓名王海生单位或住址...'
        OCR 图片格式：'被传唤人' '安徽象山文化' '单位或' '旅游发展有限' 分散多行
        """
        # 模式1: "姓名" 后跟姓名（PDF 紧凑格式）
        # compact 中 "姓名王海生单位或" → 提取 "王海生"
        m = re.search(r"姓名([\u4e00-\u9fff·]{2,10}?)(?:单位|住址|被传事由|应到)", compact)
        if m:
            val = m.group(1)
            # 排除把标签后面的内容误匹配（如 "姓名住址公司会象山小学被传事由"）
            _BAD_STARTS = ("住址", "单位", "公司", "被传")
            if not any(val.startswith(b) for b in _BAD_STARTS):
                return val

        # 模式3: OCR 场景 — 尝试拼合公司名称碎片
        # OCR 传票表格中，公司名碎片分散在多行，但公司后缀完整存在于某行
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        _COMPANY_SUFFIXES = ("有限公司", "有限责任公司", "股份有限公司", "合伙企业")
        _COMPANY_PARTS = ("有限公司", "有限", "股份", "合伙")
        _NOISE = {"被传唤人", "被通知人", "单位或", "姓名", "住址", "公司",
                   "被传事由", "应到时间", "应到处所", "注意事项", "签发人",
                   "1、", "2、", "3、", "4、"}

        # 策略A: 找包含公司后缀关键词的碎片，向前回溯拼合完整公司名
        for i, line in enumerate(lines):
            if line in _NOISE:
                continue
            has_company_hint = any(part in line for part in _COMPANY_PARTS) and len(line) >= 3
            if not has_company_hint:
                continue
            # 从此行向前收集碎片，跳过标签行不停
            parts = [line]
            _HARD_STOP = {"案号", "案由", "传票", "人民法院"}
            for j in range(i - 1, max(i - 10, -1), -1):
                prev = lines[j].strip()
                if any(prev.startswith(s) or prev == s for s in _HARD_STOP):
                    break
                # 地址碎片跳过（以省/市开头或以地址后缀结尾）
                if re.search(r"^[省市区县镇]|^[安徽北京天津上海重庆].*[市区县]$", prev):
                    continue
                if re.search(r"[省市区县镇路街号幢室栋座里村]$", prev) and len(prev) > 3:
                    continue
                # 标签行跳过不停
                if prev in _NOISE:
                    continue
                parts.insert(0, prev)
            combined = "".join(parts)
            for s in ("有限公司", "有限责任公司", "股份有限公司"):
                if s in combined:
                    idx = combined.index(s) + len(s)
                    return combined[:idx]
            if "公司" in combined:
                idx = combined.index("公司") + 2
                return combined[:idx]
            # "有限" 但没有 "公司" → 拼合 + "公司"
            if "有限" in combined:
                return combined + "公司"

        # 策略B: 没有公司后缀时，从 "案由" 到 "被传事由" 之间取第一个纯中文碎片
        cause_idx = -1
        stop_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("案由") or line == "案由":
                cause_idx = i
            if line in _NOISE or any(line.startswith(w) for w in _NOISE):
                if cause_idx >= 0 and stop_idx < 0:
                    stop_idx = i
                    break

        if cause_idx >= 0 and stop_idx > cause_idx:
            region = lines[cause_idx + 1:stop_idx]
            _LABELS = {"被传唤人", "被通知人", "单位或", "姓名", "住址"}
            fragments = [l for l in region if l not in _LABELS]
            # 自然人姓名：第一个纯中文 2-6 字碎片
            for frag in fragments:
                if 2 <= len(frag) <= 6 and all('\u4e00' <= c <= '\u9fff' or c == '·' for c in frag):
                    return frag

        # 模式4: 从传票标题中提取（如 "传票（王海生）"）
        m = re.search(r"传票[（(]([^)）]{2,20})[)）]", compact)
        if m:
            return m.group(1)

        return ""

    def parse_hearing_notice_text(
        self,
        document: CourtSmsDocument,
        text: str,
        *,
        fallback_case_number: str = "",
        fallback_court_name: str = "",
    ) -> Optional[CourtSmsHearingNotice]:
        """从传票/出庭通知书文本中提取开庭信息。"""
        compact = _compact_text(text)
        document_name = str(document.name or "").strip()
        if not compact:
            return None

        notice_type = ""
        if "传票" in compact or "传票" in document_name:
            notice_type = "传票"
        elif "出庭通知书" in compact or "出庭通知书" in document_name:
            notice_type = "出庭通知书"
        elif "开庭通知书" in compact or "开庭通知书" in document_name:
            notice_type = "开庭通知书"
        else:
            return None

        case_number = _normalize_case_number(
            _extract_labeled_value(compact, ("案号",), ("案由", "被传唤人", "被通知人", "案由", "事由"))
        ) or _normalize_case_number(fallback_case_number)

        cause = _extract_labeled_value(
            compact,
            ("案由", "事由"),
            ("被传唤人", "被通知人", "被传事由", "开庭时间", "出庭时间", "应到时间", "应到处所", "开庭地点"),
        )
        if cause:
            # OCR 场景：案由值可能夹带后面表格内容，截取到"XX纠纷"为止
            cause_cut = re.search(r"([\u4e00-\u9fff]{2,20}纠纷)", cause)
            if cause_cut:
                cause = cause_cut.group(1)
        if not cause:
            cause_match = re.search(r"([\u4e00-\u9fff]{2,20}纠纷)", compact)
            if cause_match:
                cause = cause_match.group(1)

        datetime_text = _extract_labeled_value(
            compact,
            ("应到时间", "开庭时间", "出庭时间", "庭审时间", "开庭日期"),
            ("应到处所", "应到地点", "开庭地点", "出庭地点", "庭审地点", "注意事项", "签发人", "承办人", "书记员", "联系人"),
            max_chars=48,
        )
        hearing_date, hearing_time = _parse_notice_datetime(datetime_text)

        # OCR 回退：标签和值分散时，直接从全文匹配日期时间
        if not hearing_date:
            hearing_date, hearing_time = self._fallback_extract_datetime_from_ocr(compact)
        if not hearing_date:
            return None

        hearing_place = _extract_labeled_value(
            compact,
            ("应到处所", "应到地点", "开庭地点", "出庭地点", "庭审地点", "审判法庭"),
            ("注意事项", "签发人", "承办人", "书记员", "联系人", "本院地址", "联系电话"),
            max_chars=60,
        )
        # OCR 场景：地点值可能夹带日期时间等，截取纯文字部分
        if hearing_place:
            hearing_place = re.sub(r"\d{1,4}年\d{1,2}月\d{1,2}日.*", "", hearing_place)
            hearing_place = re.sub(r"\d{1,2}日\d{1,2}[时:].*", "", hearing_place)
            hearing_place = re.sub(r"\d[、.].*", "", hearing_place)
            hearing_place = hearing_place.strip("：:，,。；;、 ")
        signer = _extract_labeled_value(
            compact,
            ("签发人", "承办人", "审判员", "审判长"),
            ("送达人", "联系人", "联系电话", "书记员", "zdqz", "二〇", "本院地址", "注"),
            max_chars=20,
        )
        contact_person = _extract_labeled_value(
            compact,
            ("联系人", "联系法官"),
            ("联系电话", "电话", "书记员", "zdqz", "二〇", "本院地址", "注"),
            max_chars=20,
        )
        phone_match = re.search(r"(?<!\d)(\d{3,4}-\d{7,8}|\d{11})(?!\d)", compact)
        court_name = document.court_name or fallback_court_name
        # OCR 回退：从全文匹配法院名
        if not court_name:
            court_match = re.search(r"([\u4e00-\u9fff]{2,15}人民法院)", compact)
            if court_match:
                court_name = court_match.group(1)

        # 提取被传唤人/被通知人姓名
        summoned_person = self._extract_summoned_person(compact, text)

        return CourtSmsHearingNotice(
            document_name=document_name,
            document_path=str(document.local_path or "").strip(),
            notice_type=notice_type,
            case_number=case_number,
            cause=cause,
            summoned_person=summoned_person,
            hearing_date=hearing_date,
            hearing_time=hearing_time,
            hearing_place=hearing_place,
            signer=signer,
            contact_person=contact_person,
            contact_phone=phone_match.group(1) if phone_match else "",
            court_name=court_name,
            issue_date_text=_extract_issue_date_text(compact),
            raw_text=text,
        )

    def extract_hearing_notice(
        self,
        document: CourtSmsDocument,
        parsed: Optional[CourtSmsParseResult] = None,
    ) -> Optional[CourtSmsHearingNotice]:
        """从单份法院文书（PDF 或图片）中识别庭审信息。"""
        ext = str(document.extname or "").lower()
        local_path = str(document.local_path or "").strip()

        # 支持的文件类型
        if ext == "pdf":
            source_text = self.extract_pdf_text(local_path, allow_pymupdf_fallback=True)
        elif ext in ("jpg", "jpeg", "png", "bmp", "tiff", "tif"):
            source_text = self.extract_text_from_file(local_path)
        else:
            return None

        # 如果文件名不含关键词，检查文本内容
        if not any(keyword in str(document.name or "") for keyword in _HEARING_DOC_KEYWORDS):
            if not any(keyword in _compact_text(source_text) for keyword in _HEARING_DOC_KEYWORDS):
                return None

        return self.parse_hearing_notice_text(
            document,
            source_text,
            fallback_case_number=parsed.case_number if parsed else "",
            fallback_court_name=parsed.court_name if parsed else "",
        )

    def extract_hearing_notices(
        self,
        documents: Iterable[CourtSmsDocument],
        parsed: Optional[CourtSmsParseResult] = None,
    ) -> List[CourtSmsHearingNotice]:
        """批量识别下载文书中的开庭/出庭提醒。"""
        notices: List[CourtSmsHearingNotice] = []
        seen = set()
        for document in documents:
            notice = self.extract_hearing_notice(document, parsed)
            if not notice:
                continue
            key = (
                notice.case_number,
                notice.hearing_date,
                notice.hearing_time,
                notice.hearing_place,
                notice.document_name,
            )
            if key in seen:
                continue
            seen.add(key)
            notices.append(notice)

        notices.sort(key=lambda item: (item.hearing_date, item.hearing_time or "99:99", item.document_name))
        return notices

    def extract_text_and_hearing_notices_from_files(
        self,
        file_paths: List[str],
    ) -> Tuple[List[CourtSmsDocument], List[CourtSmsHearingNotice]]:
        """从本地文件（PDF/图片）提取文本并识别庭审信息。

        Returns:
            (documents, hearing_notices) 元组
        """
        documents: List[CourtSmsDocument] = []
        hearing_notices: List[CourtSmsHearingNotice] = []

        for fp in file_paths:
            path = Path(fp)
            if not path.exists():
                continue

            ext = path.suffix.lstrip(".").lower()
            doc = CourtSmsDocument(
                name=path.name,
                extname=ext,
                download_url="",
                local_path=str(path),
                size_bytes=path.stat().st_size,
            )
            documents.append(doc)

            try:
                notice = self.extract_hearing_notice(doc)
                if notice:
                    hearing_notices.append(notice)
            except Exception as exc:
                self._logger.warning(f"识别庭审信息失败: {path.name} | {exc}")

        hearing_notices.sort(
            key=lambda item: (item.hearing_date, item.hearing_time or "99:99", item.document_name)
        )
        return documents, hearing_notices

    def build_deadline_from_hearing_notice(self, notice: CourtSmsHearingNotice) -> Dict[str, Any]:
        """把识别出的庭审文书转换为案件期限数据。"""
        title = "开庭安排"
        if notice.cause:
            title = f"开庭安排 - {notice.cause}"
        elif notice.notice_type:
            title = f"开庭安排 - {notice.notice_type}"

        description_lines = []
        if notice.notice_type:
            description_lines.append(f"来源文书：{notice.notice_type} / {notice.document_name}")
        else:
            description_lines.append(f"来源文书：{notice.document_name}")
        if notice.case_number:
            description_lines.append(f"案号：{notice.case_number}")
        if notice.summoned_person:
            description_lines.append(f"被传唤人：{notice.summoned_person}")
        if notice.court_name:
            description_lines.append(f"法院：{notice.court_name}")
        if notice.hearing_place:
            description_lines.append(f"地点：{notice.hearing_place}")
        if notice.signer:
            description_lines.append(f"签发人：{notice.signer}")
        if notice.contact_person:
            contact_text = notice.contact_person
            if notice.contact_phone:
                contact_text += f" / {notice.contact_phone}"
            description_lines.append(f"联系人：{contact_text}")
        elif notice.contact_phone:
            description_lines.append(f"联系电话：{notice.contact_phone}")
        if notice.issue_date_text:
            description_lines.append(f"文书日期：{notice.issue_date_text}")

        return {
            "title": title,
            "date": notice.hearing_date,
            "time": notice.hearing_time or "09:00",
            "all_day": False,
            "type": "hearing",
            "priority": "high",
            "description": "\n".join(description_lines),
            "status": "pending",
            "remind_before": [7, 3, 1, 0],
            "source": "court_sms",
            "source_document_path": notice.document_path,
            "source_document_name": notice.document_name,
            "source_notice_type": notice.notice_type,
            "source_case_number": notice.case_number,
        }
