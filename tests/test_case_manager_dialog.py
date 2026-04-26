# -*- coding: utf-8 -*-
"""案件管理对话框联动测试"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from src.core.case_manager import CaseManager
from src.gui.case_manager_dialog import CaseImportDropFrame, CaseManagerDialog


class TestCaseManagerDialog:
    """案件管理窗口联动测试。"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.case_folder = self.temp_dir / "联动案件"
        self.case_folder.mkdir()
        CaseManager._instance = None
        self.manager = CaseManager()
        self.manager._cases_file = self.temp_dir / "cases.json"
        self.manager._cases = {}
        self.manager._common_tags = []

    def teardown_method(self):
        CaseManager._instance = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_deadline_toggle_refreshes_case_card_immediately(self, qapp):
        case_id = self.manager.register_case({
            "name": "联动案件",
            "path": str(self.case_folder),
            "tags": ["执行"],
            "deadlines": [
                {
                    "id": "dl_live",
                    "title": "今天到期事项",
                    "date": "2099-01-01",
                    "status": "pending",
                }
            ],
        })
        self.manager.update_deadline(case_id, "dl_live", {"date": datetime.now().strftime("%Y-%m-%d")})

        dialog = CaseManagerDialog()
        dialog.show()
        dialog._select_single_case(case_id)
        qapp.processEvents()

        card = dialog._case_cards[case_id]
        assert card._deadline_label is not None
        assert card._deadline_label.isVisible() is True

        dialog._detail_panel._on_toggle_deadline("dl_live", True)
        qapp.processEvents()

        refreshed_card = dialog._case_cards[case_id]
        assert refreshed_card._deadline_label is not None
        assert refreshed_card._deadline_label.isVisible() is False

    def test_open_case_deadline_from_calendar_resets_filters_and_targets_case(self, qapp):
        other_case_folder = self.temp_dir / "其他案件"
        other_case_folder.mkdir()
        other_case_id = self.manager.register_case({
            "name": "其他案件",
            "path": str(other_case_folder),
        })
        target_case_id = self.manager.register_case({
            "name": "目标案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_nav",
                    "title": "开庭安排",
                    "date": "2026-04-18",
                    "status": "pending",
                }
            ],
        })
        dialog = CaseManagerDialog()
        dialog.show()
        qapp.processEvents()

        dialog._search_input.setText("不存在的案件")
        dialog._do_search()  # 手动触发防抖后的搜索
        qapp.processEvents()
        assert not dialog._case_cards

        captured = {}
        def _capture_deadline(deadline_id: str) -> bool:
            captured["deadline_id"] = deadline_id
            return True
        dialog._detail_panel.open_deadline_editor_from_calendar = _capture_deadline

        result = dialog.open_case_deadline_from_calendar(target_case_id, "dl_nav")
        qapp.processEvents()

        assert result is True
        assert dialog._selected_case_ids == {target_case_id}
        assert dialog._search_input.text() == ""
        assert dialog._current_filter == "all"
        assert dialog._current_status == "all"
        assert dialog._current_directory == "all"
        assert captured["deadline_id"] == "dl_nav"

    def test_import_actions_panel_is_above_search_filter_panel(self, qapp):
        dialog = CaseManagerDialog()
        dialog.show()
        qapp.processEvents()

        layout = dialog._list_panel.layout()
        first_widget = layout.itemAt(0).widget()
        second_widget = layout.itemAt(1).widget()

        assert isinstance(first_widget, CaseImportDropFrame)
        assert second_widget.objectName() == "searchFilterPanel"
