# -*- coding: utf-8 -*-
"""案件详情面板测试"""

import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

from src.core.case_manager import CaseManager
from src.gui.case_detail_panel import CaseDetailPanel


def _mouse_press_at(widget: QWidget, global_pos: QPoint) -> QMouseEvent:
    local_pos = widget.mapFromGlobal(global_pos)
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(local_pos),
        QPointF(global_pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


class TestCaseDetailPanel:
    """案件详情面板回归测试。"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.case_folder = self.temp_dir / "浮窗案件"
        self.case_folder.mkdir()
        CaseManager._instance = None
        self.manager = CaseManager()
        self.manager._cases_file = self.temp_dir / "cases.json"
        self.manager._cases = {}

    def teardown_method(self):
        CaseManager._instance = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_floating_notes_syncs_back_to_main_editor(self, qapp):
        case_id = self.manager.register_case({
            "name": "浮窗案件",
            "path": str(self.case_folder),
            "notes": "初始笔记",
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.load_case(case)
        panel._toggle_floating_notes()
        qapp.processEvents()

        dialog = panel._floating_notes_dialog
        assert dialog is not None
        assert "浮窗案件" in dialog.windowTitle()

        dialog._editor.setPlainText("新的悬浮笔记")
        qapp.processEvents()

        assert panel._notes_editor.toPlainText() == "新的悬浮笔记"

        dialog._btn_return.click()
        qapp.processEvents()

        assert panel._tabs.currentIndex() == panel._notes_tab_index

    def test_case_detail_tabs_area_is_compact(self, qapp):
        """头部卡片与页签内容之间保持紧凑。"""
        panel = CaseDetailPanel()
        panel.resize(1200, 760)
        panel.show()
        qapp.processEvents()

        header_bottom = panel._header.geometry().bottom()
        tabs_top = panel._tabs.geometry().top()
        gap = tabs_top - header_bottom - 1
        files_margins = panel._files_tab.layout().contentsMargins()

        assert gap <= 8
        assert panel._tabs.tabBar().height() <= 36
        assert files_margins.top() <= 8
        assert panel._files_tab.layout().spacing() <= 6

    def test_export_notes_writes_markdown_file(self, qapp, monkeypatch):
        case_id = self.manager.register_case({
            "name": "导出笔记案件",
            "path": str(self.case_folder),
            "notes": "初始内容",
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.load_case(case)
        panel._notes_editor.setPlainText("导出的 Markdown 笔记")
        output_path = self.temp_dir / "案件笔记.md"

        monkeypatch.setattr(
            "src.gui.case_detail_panel.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (str(output_path), "Markdown (*.md)"),
        )
        monkeypatch.setattr(
            "src.gui.case_detail_panel.QMessageBox.information",
            lambda *args, **kwargs: None,
        )

        panel._on_export_notes()
        qapp.processEvents()

        assert output_path.read_text(encoding="utf-8") == "导出的 Markdown 笔记"

    def test_clicking_outside_editors_auto_saves_and_exits(self, qapp):
        case_id = self.manager.register_case({
            "name": "自动保存案件",
            "path": str(self.case_folder),
            "notes": "旧笔记",
            "info_fields": [
                {
                    "id": "builtin_case_number",
                    "key": "case_number",
                    "label": "案号",
                    "value": "（2026）旧001",
                    "type": "text",
                    "builtin": True,
                    "map_to_tag": False,
                }
            ],
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.resize(1200, 800)
        panel.show()
        panel.load_case(case)
        qapp.processEvents()

        panel._enter_notes_edit_mode()
        panel._notes_editor.setPlainText("新的自动保存笔记")
        outside_pos = panel.mapToGlobal(QPoint(panel.width() + 24, panel.height() + 24))
        panel.eventFilter(panel, _mouse_press_at(panel, outside_pos))
        qapp.processEvents()

        refreshed = self.manager.get_case(case_id)
        assert refreshed is not None
        assert panel._notes_editing is False
        assert refreshed["notes"] == "新的自动保存笔记"

        panel._tabs.setCurrentIndex(panel._tabs.indexOf(panel._info_tab))
        panel._on_start_info_edit("builtin_case_number")
        editor_widgets = panel._info_editor_widgets["builtin_case_number"]
        editor_widgets["value"].setText("（2026）新002")
        panel.eventFilter(panel, _mouse_press_at(panel, outside_pos))
        qapp.processEvents()

        refreshed = self.manager.get_case(case_id)
        assert refreshed is not None
        assert panel._info_editing is False
        info_by_id = {field["id"]: field for field in refreshed["info_fields"]}
        assert info_by_id["builtin_case_number"]["value"] == "（2026）新002"

    def test_clicking_toolbar_buttons_does_not_force_exit_edit_mode(self, qapp):
        case_id = self.manager.register_case({
            "name": "按钮交互案件",
            "path": str(self.case_folder),
            "notes": "旧笔记",
            "info_fields": [
                {
                    "id": "builtin_case_number",
                    "key": "case_number",
                    "label": "案号",
                    "value": "（2026）旧001",
                    "type": "text",
                    "builtin": True,
                    "map_to_tag": False,
                }
            ],
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.resize(1200, 800)
        panel.show()
        panel.load_case(case)
        qapp.processEvents()

        panel._tabs.setCurrentIndex(panel._notes_tab_index)
        panel._enter_notes_edit_mode()
        notes_button_pos = panel._btn_export_notes.mapToGlobal(panel._btn_export_notes.rect().center())
        panel.eventFilter(panel._btn_export_notes, _mouse_press_at(panel._btn_export_notes, notes_button_pos))
        notes_editor_pos = panel._notes_editor.viewport().mapToGlobal(QPoint(20, 20))
        panel.eventFilter(panel._notes_editor.viewport(), _mouse_press_at(panel._notes_editor.viewport(), notes_editor_pos))
        qapp.processEvents()
        assert panel._notes_editing is True

        panel._tabs.setCurrentIndex(panel._tabs.indexOf(panel._info_tab))
        panel._on_start_info_edit("builtin_case_number")
        info_button_pos = panel._btn_save_info.mapToGlobal(panel._btn_save_info.rect().center())
        panel.eventFilter(panel._btn_save_info, _mouse_press_at(panel._btn_save_info, info_button_pos))
        qapp.processEvents()
        assert panel._info_editing is True

    def test_split_notes_mode_saves_secondary_notes(self, qapp):
        case_id = self.manager.register_case({
            "name": "双栏笔记案件",
            "path": str(self.case_folder),
            "notes": "主笔记",
            "notes_secondary": "",
            "notes_split": False,
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.resize(1200, 800)
        panel.show()
        panel.load_case(case)
        qapp.processEvents()

        panel._tabs.setCurrentIndex(panel._notes_tab_index)
        panel._btn_toggle_split_notes.click()
        qapp.processEvents()
        assert panel._notes_split_mode is True
        assert panel._split_notes_container.isHidden() is False

        panel._secondary_split_notes.enter_edit_mode()
        panel._secondary_split_notes._editor.setPlainText("副栏记录")
        panel._secondary_split_notes.exit_edit_mode()
        qapp.processEvents()

        refreshed = self.manager.get_case(case_id)
        assert refreshed is not None
        assert refreshed["notes_secondary"] == "副栏记录"
        assert refreshed["notes_split"] is True

    def test_header_deadline_summary_highlights_when_case_has_deadlines(self, qapp):
        case_id = self.manager.register_case({
            "name": "期限高亮案件",
            "path": str(self.case_folder),
            "deadlines": [],
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.load_case(case)
        qapp.processEvents()
        assert "background-color:#fee2e2" not in panel._summary_label.text()
        assert "期限数量：0" in panel._summary_label.text()

        self.manager.add_deadline(case_id, {
            "title": "开庭",
            "date": "2026-04-20",
            "type": "hearing",
            "priority": "high",
        })
        refreshed = self.manager.get_case(case_id)
        assert refreshed is not None

        panel.load_case(refreshed)
        qapp.processEvents()

        assert "期限数量：1" in panel._summary_label.text()
        assert "background-color:#fee2e2" in panel._summary_label.text()

    def test_header_deadline_summary_does_not_highlight_completed_deadlines(self, qapp):
        case_id = self.manager.register_case({
            "name": "期限已完成案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_done",
                    "title": "已完成开庭",
                    "date": "2026-04-20",
                    "type": "hearing",
                    "priority": "high",
                    "status": "completed",
                }
            ],
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.load_case(case)
        qapp.processEvents()

        assert "期限数量：1" in panel._summary_label.text()
        assert "background-color:#fee2e2" not in panel._summary_label.text()

    def test_open_deadline_editor_from_calendar_switches_to_deadline_tab(self, qapp):
        case_id = self.manager.register_case({
            "name": "跳转编辑案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_jump",
                    "title": "开庭安排",
                    "date": "2026-04-18",
                    "status": "pending",
                }
            ],
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.load_case(case)
        panel._tabs.setCurrentIndex(panel._tabs.indexOf(panel._files_tab))
        captured = {}
        panel._on_edit_deadline = lambda deadline_id: captured.setdefault("deadline_id", deadline_id)

        result = panel.open_deadline_editor_from_calendar("dl_jump")

        assert result is True
        assert panel._tabs.currentIndex() == panel._deadline_tab_index
        assert captured["deadline_id"] == "dl_jump"

    def test_deadline_tab_highlights_only_for_pending_deadlines(self, qapp):
        case_id = self.manager.register_case({
            "name": "期限页签案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_pending",
                    "title": "待处理开庭",
                    "date": "2026-04-20",
                    "type": "hearing",
                    "priority": "high",
                    "status": "pending",
                }
            ],
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.load_case(case)
        qapp.processEvents()

        assert panel._detail_tab_bar._deadline_highlight is True

        self.manager.update_deadline(case_id, "dl_pending", {"status": "completed"})
        refreshed = self.manager.get_case(case_id)
        assert refreshed is not None
        panel.load_case(refreshed)
        qapp.processEvents()

        assert panel._detail_tab_bar._deadline_highlight is False

    def test_case_ocr_button_shows_setup_guide_when_dependency_unavailable(self, qapp, monkeypatch):
        # qapp provided by fixture
        case_id = self.manager.register_case({
            "name": "OCR说明案件",
            "path": str(self.case_folder),
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.load_case(case)
        qapp.processEvents()

        recorded = {}
        monkeypatch.setattr(
            "src.gui.case_detail_panel.get_ocr_dependency_status",
            lambda: SimpleNamespace(available=False),
        )
        monkeypatch.setattr(
            "src.gui.case_detail_panel.format_ocr_setup_message",
            lambda status: "请安装 OCR 依赖",
        )
        monkeypatch.setattr(
            "src.gui.case_detail_panel.QMessageBox.information",
            lambda parent, title, message: recorded.update({"title": title, "message": message}),
        )

        panel._on_case_ocr()

        assert recorded["title"] == "OCR 增强能力说明"
        assert "请安装 OCR 依赖" in recorded["message"]

    def test_case_ocr_button_starts_screenshot_when_dependency_available(self, qapp, monkeypatch):
        # qapp provided by fixture
        case_id = self.manager.register_case({
            "name": "OCR截图案件",
            "path": str(self.case_folder),
        })
        case = self.manager.get_case(case_id)
        assert case is not None

        panel = CaseDetailPanel()
        panel.load_case(case)
        qapp.processEvents()

        started = {"value": False}
        monkeypatch.setattr(
            "src.gui.case_detail_panel.get_ocr_dependency_status",
            lambda: SimpleNamespace(available=True),
        )
        monkeypatch.setattr(
            panel._screenshot_tool,
            "start_screenshot",
            lambda: started.update({"value": True}),
        )

        panel._on_case_ocr()

        assert started["value"] is True
        assert panel._btn_case_ocr.text() == "截图中..."
