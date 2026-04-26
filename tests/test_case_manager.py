# -*- coding: utf-8 -*-
"""案件管理器测试"""

import shutil
import tempfile
import json
from pathlib import Path

import pytest

import src.core.case_manager as case_manager_module
from src.core.case_manager import CaseManager


class TestCaseManager:
    """案件管理器测试类"""

    def setup_method(self):
        """每个测试前创建独立实例和数据目录。"""
        self.temp_dir = Path(tempfile.mkdtemp())
        CaseManager._instance = None
        self.manager = CaseManager()
        self.manager._cases_file = self.temp_dir / "cases.json"
        self.manager._cases = {}
        self.manager._common_tags = []

    def teardown_method(self):
        """测试结束后清理临时目录。"""
        CaseManager._instance = None
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_import_existing_folders_reports_statuses(self):
        """批量导入会区分新增、已存在和无效目录。"""
        folder_a = self.temp_dir / "案件A"
        folder_b = self.temp_dir / "案件B"
        invalid = self.temp_dir / "不存在"
        folder_a.mkdir()
        folder_b.mkdir()

        first_case_id = self.manager.import_existing_folder(folder_a)
        result = self.manager.import_existing_folders([folder_a, folder_b, invalid])

        assert result["existing_ids"] == [first_case_id]
        assert len(result["imported_ids"]) == 1
        assert result["invalid_paths"] == [str(invalid)]

        imported_case = self.manager.get_case(result["imported_ids"][0])
        assert imported_case is not None
        assert imported_case["name"] == "案件B"

    def test_update_case_tags_normalizes_duplicates(self):
        """更新标签时会去重、去井号并保留顺序。"""
        case_id = self.manager.register_case({
            "name": "测试案件",
            "path": str(self.temp_dir / "案件标签"),
            "tags": [],
        })

        assert self.manager.update_case_tags(case_id, ["紧急", "#合同", "紧急", " 证据 "]) is True

        case = self.manager.get_case(case_id)
        assert case is not None
        assert case["tags"] == ["紧急", "合同", "证据"]

    def test_common_tags_persist_in_cases_store(self):
        """常用标签会单独持久化，并在重新加载后恢复。"""
        assert self.manager.set_common_tags(["仲裁", "#保全", "仲裁", " 紧急 "]) is True

        payload = json.loads(self.manager._cases_file.read_text(encoding="utf-8"))
        assert payload["common_tags"] == ["仲裁", "保全", "紧急"]

        CaseManager._instance = None
        reloaded = CaseManager()
        reloaded._cases_file = self.manager._cases_file
        reloaded._load()

        assert reloaded.get_common_tags() == ["仲裁", "保全", "紧急"]

    def test_update_deadline_updates_single_deadline(self):
        """更新期限只应修改目标期限。"""
        case_id = self.manager.register_case({
            "name": "测试案件",
            "path": str(self.temp_dir / "案件期限"),
            "tags": [],
        })
        first_deadline_id = self.manager.add_deadline(case_id, {
            "title": "举证期限",
            "date": "2026-04-20",
            "type": "deadline",
            "priority": "medium",
        })
        second_deadline_id = self.manager.add_deadline(case_id, {
            "title": "开庭",
            "date": "2026-05-01",
            "type": "hearing",
            "priority": "high",
        })

        assert self.manager.update_deadline(case_id, first_deadline_id, {
            "title": "补正期限",
            "priority": "high",
            "status": "completed",
        }) is True

        case = self.manager.get_case(case_id)
        assert case is not None
        deadlines = {item["id"]: item for item in case["deadlines"]}
        assert deadlines[first_deadline_id]["title"] == "补正期限"
        assert deadlines[first_deadline_id]["priority"] == "high"
        assert deadlines[first_deadline_id]["status"] == "completed"
        assert deadlines[second_deadline_id]["title"] == "开庭"

    def test_export_case_work_log_groups_pending_and_completed_deadlines(self):
        """工作日志导出会按待处理/已完成分组输出。"""
        case_id = self.manager.register_case({
            "name": "工作日志案件",
            "path": str(self.temp_dir / "案件日志"),
            "deadlines": [
                {
                    "id": "dl_pending",
                    "title": "提交证据",
                    "date": "2026-04-20",
                    "status": "pending",
                    "all_day": True,
                    "type": "deadline",
                    "description": "整理证据目录",
                },
                {
                    "id": "dl_done",
                    "title": "开庭",
                    "date": "2026-04-10",
                    "time": "09:30",
                    "status": "completed",
                    "all_day": False,
                    "type": "hearing",
                    "description": "一审开庭",
                },
            ],
        })
        output_path = self.temp_dir / "工作日志.md"

        assert self.manager.export_case_work_log(case_id, output_path) is True

        text = output_path.read_text(encoding="utf-8")
        assert "# 工作日志案件 工作日志" in text
        assert "## 一、待处理事项" in text
        assert "## 二、已完成事项" in text
        assert "事项：提交证据" in text
        assert "事项：开庭" in text
        assert "状态：待处理" in text
        assert "状态：已完成" in text

    def test_get_all_cases_does_not_refresh_disk_status_by_default(self):
        """列表读取默认不做磁盘核验，避免打开案件管理时卡顿。"""
        case_folder = self.temp_dir / "性能案件"
        case_folder.mkdir()
        case_id = self.manager.register_case({
            "name": "性能案件",
            "path": str(case_folder),
        })
        shutil.rmtree(case_folder)

        cases = self.manager.get_all_cases()
        case_by_id = {case["id"]: case for case in cases}

        assert case_by_id[case_id]["folder_status"] == "available"

        refreshed_cases = self.manager.get_all_cases(refresh_runtime=True)
        refreshed_by_id = {case["id"]: case for case in refreshed_cases}

        assert refreshed_by_id[case_id]["folder_status"] == "missing"

    def test_register_case_writes_sidecar_metadata_and_notes(self):
        """注册案件后会同步写入案件目录侧边数据。"""
        case_folder = self.temp_dir / "案件侧边数据"
        case_folder.mkdir()

        case_id = self.manager.register_case({
            "name": "案件侧边数据",
            "path": str(case_folder),
            "notes": "这里是案件笔记",
            "info_fields": [
                {
                    "id": "builtin_case_number",
                    "key": "case_number",
                    "label": "案号",
                    "value": "(2026)测试001",
                    "type": "text",
                    "builtin": True,
                    "map_to_tag": False,
                }
            ],
        })

        metadata_path = case_folder / ".case" / "metadata.json"
        notes_path = case_folder / ".case" / "notes.md"
        secondary_notes_path = case_folder / ".case" / "notes_secondary.md"

        assert metadata_path.exists()
        assert notes_path.exists()
        assert secondary_notes_path.exists()

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["case_id"] == case_id
        assert metadata["name"] == "案件侧边数据"
        assert notes_path.read_text(encoding="utf-8") == "这里是案件笔记"
        assert secondary_notes_path.read_text(encoding="utf-8") == ""

    def test_import_existing_folder_relinks_case_by_sidecar_metadata(self):
        """目录移动后重新导入会按 sidecar metadata 重新关联旧案件。"""
        original_folder = self.temp_dir / "原始案件"
        original_folder.mkdir()

        case_id = self.manager.register_case({
            "name": "原始案件",
            "path": str(original_folder),
            "notes": "迁移前笔记",
        })

        moved_folder = self.temp_dir / "迁移后的案件"
        original_folder.rename(moved_folder)

        imported_case_id = self.manager.import_existing_folder(moved_folder)
        assert imported_case_id == case_id

        case = self.manager.get_case(case_id)
        assert case is not None
        assert case["path"] == str(moved_folder)
        assert case["folder_status"] == "available"
        assert "迁移前笔记" == case["notes"]

    def test_update_case_path_preserves_history(self):
        """手动更新案件目录时应保留历史路径。"""
        original_folder = self.temp_dir / "原始目录"
        moved_folder = self.temp_dir / "新目录"
        original_folder.mkdir()
        moved_folder.mkdir()

        case_id = self.manager.register_case({
            "name": "路径迁移案件",
            "path": str(original_folder),
        })

        assert self.manager.update_case_path(case_id, moved_folder) is True

        case = self.manager.get_case(case_id)
        assert case is not None
        assert case["path"] == str(moved_folder)
        assert case["folder_status"] == "available"
        assert str(original_folder) in case["path_history"]
        assert str(moved_folder) in case["path_history"]

    def test_update_case_notes_keeps_memory_after_folder_removed(self):
        """案件目录缺失后，本地记忆中的笔记仍然保留。"""
        case_folder = self.temp_dir / "案件记忆"
        case_folder.mkdir()

        case_id = self.manager.register_case({
            "name": "案件记忆",
            "path": str(case_folder),
        })
        assert self.manager.update_case_notes(case_id, "本地记忆仍要保留")

        shutil.rmtree(case_folder)
        case = self.manager.get_case(case_id)

        assert case is not None
        assert case["folder_status"] == "missing"
        assert case["notes"] == "本地记忆仍要保留"

    def test_update_secondary_notes_persists_to_sidecar(self):
        """副笔记应写入本地记忆和案件 sidecar。"""
        case_folder = self.temp_dir / "副笔记案件"
        case_folder.mkdir()

        case_id = self.manager.register_case({
            "name": "副笔记案件",
            "path": str(case_folder),
            "notes_split": True,
        })

        assert self.manager.update_case_notes(case_id, "右栏独立笔记", slot="secondary") is True

        case = self.manager.get_case(case_id)
        assert case is not None
        assert case["notes_secondary"] == "右栏独立笔记"

        metadata_path = case_folder / ".case" / "metadata.json"
        secondary_notes_path = case_folder / ".case" / "notes_secondary.md"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["notes_split"] is True
        assert secondary_notes_path.read_text(encoding="utf-8") == "右栏独立笔记"

    def test_remove_case_rolls_back_index_when_folder_delete_fails(self, monkeypatch):
        """删除目录失败时，应回滚案件索引，避免“目录在/索引无”的不一致。"""
        case_folder = self.temp_dir / "删除失败案件"
        case_folder.mkdir()
        case_id = self.manager.register_case({
            "name": "删除失败案件",
            "path": str(case_folder),
        })

        def _raise_os_error(*_args, **_kwargs):
            raise OSError("mock delete error")

        monkeypatch.setattr(case_manager_module.shutil, "rmtree", _raise_os_error)

        with pytest.raises(OSError):
            self.manager.remove_case(case_id, delete_folder=True)

        case = self.manager.get_case(case_id)
        assert case is not None
        assert self.manager.get_case_by_path(str(case_folder)) is not None
        assert case_id in {item["id"] for item in self.manager.search_cases("删除失败")}
        assert case_folder.exists()

    def test_remove_case_aborts_when_delete_target_is_unsafe(self, monkeypatch):
        """安全校验失败时，不应删除目录，也不应移除案件索引。"""
        case_folder = self.temp_dir / "不安全删除目标"
        case_folder.mkdir()
        case_id = self.manager.register_case({
            "name": "不安全删除目标",
            "path": str(case_folder),
        })

        monkeypatch.setattr(self.manager, "_resolve_safe_delete_target", lambda *_args, **_kwargs: None)

        assert self.manager.remove_case(case_id, delete_folder=True) is False
        assert self.manager.get_case(case_id) is not None
        assert case_folder.exists()

    def test_get_case_light_refresh_does_not_read_sidecar_notes(self, monkeypatch):
        """get_case 应走轻量刷新，不触发 sidecar 笔记读取。"""
        case_folder = self.temp_dir / "轻量刷新案件"
        case_folder.mkdir()
        case_id = self.manager.register_case({
            "name": "轻量刷新案件",
            "path": str(case_folder),
        })

        def _raise_if_called(*_args, **_kwargs):
            raise AssertionError("get_case 不应读取 sidecar 笔记文件")

        monkeypatch.setattr(self.manager, "_get_case_notes_file", _raise_if_called)
        monkeypatch.setattr(self.manager, "_get_case_secondary_notes_file", _raise_if_called)

        case = self.manager.get_case(case_id)
        assert case is not None
        assert case["id"] == case_id

    def test_toggle_info_field_tag_creates_and_removes_filter_tag(self):
        """字段映射标签开启和关闭后，应同步生成和移除筛选标签。"""
        case_id = self.manager.register_case({
            "name": "字段标签案件",
            "path": str(self.temp_dir / "字段标签案件"),
            "info_fields": [
                {
                    "id": "builtin_case_number",
                    "key": "case_number",
                    "label": "案号",
                    "value": "(2026)测试001",
                    "type": "text",
                    "builtin": True,
                    "map_to_tag": False,
                }
            ],
        })

        assert self.manager.toggle_info_field_tag(case_id, "builtin_case_number", True) is True
        case = self.manager.get_case(case_id)
        assert case is not None
        assert "案号:(2026)测试001" in case["tags"]

        assert self.manager.toggle_info_field_tag(case_id, "builtin_case_number", False) is True
        case = self.manager.get_case(case_id)
        assert case is not None
        assert "案号:(2026)测试001" not in case["tags"]

    def test_update_info_section_titles_persists_to_memory_and_sidecar(self):
        """信息分组标题更新后，应保存到本地索引和案件 sidecar。"""
        case_folder = self.temp_dir / "分组标题案件"
        case_folder.mkdir()

        case_id = self.manager.register_case({
            "name": "分组标题案件",
            "path": str(case_folder),
        })

        assert self.manager.update_info_section_titles(case_id, {
            "basic": "案件总览",
            "business": "办理信息",
        }) is True

        case = self.manager.get_case(case_id)
        assert case is not None
        assert case["info_section_titles"]["basic"] == "案件总览"
        assert case["info_section_titles"]["business"] == "办理信息"
        assert case["info_section_titles"]["parties"] == "委托关系"

        metadata_path = case_folder / ".case" / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["info_section_titles"]["basic"] == "案件总览"
        assert metadata["info_section_titles"]["business"] == "办理信息"

    def test_manual_arbitration_category_is_returned_by_arbitration_filter(self):
        """手动分类为仲裁后，应能被仲裁筛选命中。"""
        case_id = self.manager.register_case({
            "name": "仲裁案件",
            "path": str(self.temp_dir / "仲裁案件"),
            "category": "arbitration",
            "status": "closed",
        })

        arbitration_cases = self.manager.get_cases_by_category("arbitration")
        matched_ids = {case["id"] for case in arbitration_cases}

        assert case_id in matched_ids
        case = self.manager.get_case(case_id)
        assert case is not None
        assert case["status"] == "closed"

    def test_rename_case_renames_real_folder_and_updates_history(self):
        """重命名案件时，应同步更新真实目录和历史路径。"""
        case_folder = self.temp_dir / "原案件目录"
        case_folder.mkdir()

        case_id = self.manager.register_case({
            "name": "原案件目录",
            "path": str(case_folder),
        })

        assert self.manager.rename_case(case_id, "新的案件目录") is True

        renamed_folder = self.temp_dir / "新的案件目录"
        assert renamed_folder.exists()
        assert not case_folder.exists()

        case = self.manager.get_case(case_id)
        assert case is not None
        assert case["name"] == "新的案件目录"
        assert case["path"] == str(renamed_folder)
        assert str(case_folder) in case["path_history"]
        assert str(renamed_folder) in case["path_history"]

    def test_remove_case_with_folder_deletes_record_and_directory(self):
        """物理删除模式应同时移除案件记录与实际目录。"""
        case_folder = self.temp_dir / "待删除案件"
        case_folder.mkdir()

        case_id = self.manager.register_case({
            "name": "待删除案件",
            "path": str(case_folder),
        })

        assert self.manager.remove_case(case_id, delete_folder=True) is True
        assert self.manager.get_case(case_id) is None
        assert not case_folder.exists()
