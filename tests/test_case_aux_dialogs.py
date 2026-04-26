# -*- coding: utf-8 -*-
"""案件辅助对话框逻辑测试"""

from datetime import datetime

from PySide6.QtWidgets import QDialogButtonBox, QFrame, QSplitter, QWidget

from src.gui.case_aux_dialogs import (
    DeadlineEditorDialog,
    parse_deadline_input_text,
    parse_deadline_smart_input_text,
)


class TestCaseAuxDialogs:
    """辅助对话框纯逻辑测试。"""

    def test_parse_deadline_input_text_supports_compact_digits(self):
        """支持紧凑数字日期时间。"""
        result = parse_deadline_input_text("202404031620")
        assert result["date"] == "2024-04-03"
        assert result["time"] == "16:20"
        assert result["all_day"] is False

    def test_parse_deadline_input_text_supports_chinese_pm_text(self):
        """支持中文下午时间表达。"""
        result = parse_deadline_input_text("2024年4月3日下午4点20")
        assert result["date"] == "2024-04-03"
        assert result["time"] == "16:20"
        assert result["all_day"] is False

    def test_parse_deadline_input_text_supports_compact_date_only(self):
        """支持纯 8 位日期。"""
        result = parse_deadline_input_text("20240203")
        assert result["date"] == "2024-02-03"
        assert result["time"] == ""
        assert result["all_day"] is True

    def test_parse_deadline_input_text_supports_missing_day_suffix(self):
        """支持不带“日”的中文日期。"""
        result = parse_deadline_input_text("2024年2月2")
        assert result["date"] == "2024-02-02"
        assert result["time"] == ""
        assert result["all_day"] is True

    def test_parse_deadline_input_text_supports_two_digit_year(self):
        """支持两位年份。"""
        result = parse_deadline_input_text("23年2月17")
        assert result["date"] == "2023-02-17"
        assert result["time"] == ""
        assert result["all_day"] is True

    def test_parse_deadline_input_text_supports_time_only_morning(self):
        """仅输入上午几点时默认使用今天日期。"""
        result = parse_deadline_input_text("上午9点")
        assert result["date"] == datetime.now().strftime("%Y-%m-%d")
        assert result["time"] == "09:00"
        assert result["all_day"] is False

    def test_parse_deadline_input_text_supports_time_only_half_hour(self):
        """支持“八点半”这类口语时间。"""
        result = parse_deadline_input_text("上午8点半")
        assert result["date"] == datetime.now().strftime("%Y-%m-%d")
        assert result["time"] == "08:30"
        assert result["all_day"] is False

    def test_parse_deadline_input_text_supports_time_only_without_ampm(self):
        """支持仅输入 16 点 20。"""
        result = parse_deadline_input_text("16点20")
        assert result["date"] == datetime.now().strftime("%Y-%m-%d")
        assert result["time"] == "16:20"
        assert result["all_day"] is False

    def test_parse_deadline_input_text_defaults_to_hearing_morning_time(self):
        """开庭事项仅输入日期时默认上午 9 点。"""
        result = parse_deadline_input_text(
            "2024-04-03",
            default_time="09:00",
            default_all_day=False,
        )
        assert result["date"] == "2024-04-03"
        assert result["time"] == "09:00"
        assert result["all_day"] is False

    def test_parse_deadline_input_text_defaults_to_all_day_for_normal_deadline(self):
        """普通期限仅输入日期时默认全天。"""
        result = parse_deadline_input_text(
            "2024/4/3",
            default_time="",
            default_all_day=True,
        )
        assert result["date"] == "2024-04-03"
        assert result["time"] == ""
        assert result["all_day"] is True

    def test_parse_deadline_smart_input_text_extracts_hearing_sentence(self):
        """整句开庭事项可拆出标题、类型、时间和说明。"""
        result = parse_deadline_smart_input_text(
            "2024年3月14日上午9时30分在池州市贵池区人民法院开庭审理牛先生民间借贷纠纷案件"
        )
        assert result["date"] == "2024-03-14"
        assert result["time"] == "09:30"
        assert result["all_day"] is False
        assert result["type"] == "hearing"
        assert result["priority"] == "high"
        assert result["title"].startswith("开庭安排")
        assert "池州市贵池区人民法院" in result["description"]

    def test_parse_deadline_smart_input_text_extracts_deadline_sentence(self):
        """整句期限事项可识别普通期限语义。"""
        result = parse_deadline_smart_input_text(
            "2024年4月20日前提交证据材料并补充银行流水说明"
        )
        assert result["date"] == "2024-04-20"
        assert result["time"] == ""
        assert result["all_day"] is True
        assert result["type"] == "deadline"
        assert result["title"] in {"提交证据期限", "提交材料期限", "材料提交提醒"}

    def test_deadline_editor_dialog_allows_empty_case_selection(self, qapp):
        dialog = DeadlineEditorDialog(
            cases=[
                {"id": "case_1", "name": "张三合同纠纷", "tags": ["合同"]},
            ]
        )
        dialog._title_edit.setText("临时提醒")
        if dialog._case_combo is not None:
            dialog._case_combo.setCurrentIndex(0)

        dialog._on_accept()

        assert dialog.get_deadline_data() is not None
        assert dialog.get_selected_case_id() == ""

    def test_deadline_editor_dialog_search_text_can_auto_match_case(self, qapp):
        dialog = DeadlineEditorDialog(
            cases=[
                {"id": "case_1", "name": "张三合同纠纷", "tags": ["合同"]},
                {"id": "case_2", "name": "李四劳动争议", "tags": ["劳动"]},
            ]
        )

        assert dialog._case_combo is not None
        dialog._select_case_from_text("劳动")

        assert dialog.get_selected_case_id() == "case_2"

    def test_deadline_editor_dialog_default_layout_keeps_fields_visible(self, qapp):
        dialog = DeadlineEditorDialog(
            cases=[
                {"id": "case_1", "name": "张三合同纠纷", "tags": ["合同"]},
            ]
        )
        dialog.show()
        qapp.processEvents()

        assert 680 <= dialog.width() <= 740
        assert 500 <= dialog.height() <= 540

        buttons = dialog.findChild(QDialogButtonBox)
        smart_card = next(
            widget
            for widget in dialog.findChildren(QFrame)
            if widget.objectName() == "deadlineSmartCard"
        )
        form_card = next(
            widget
            for widget in dialog.findChildren(QFrame)
            if widget.objectName() == "deadlineFormCard"
        )
        inline_fields = [
            widget
            for widget in dialog.findChildren(QFrame)
            if widget.objectName() == "deadlineInlineField"
        ]

        assert buttons is not None and buttons.isVisible()
        assert smart_card.width() <= 280
        assert form_card.width() > smart_card.width()
        assert inline_fields == []
        assert dialog._smart_input.height() >= 88
        assert dialog._smart_result_label.height() >= 118

        smart_bottom = smart_card.mapTo(dialog, smart_card.rect().bottomLeft()).y()
        form_bottom = form_card.mapTo(dialog, form_card.rect().bottomLeft()).y()
        gap_to_buttons = buttons.geometry().top() - max(smart_bottom, form_bottom)

        assert 0 <= gap_to_buttons <= 10
        assert buttons.geometry().bottom() <= dialog.rect().bottom()
        assert dialog._title_edit.width() >= 280
        assert dialog._case_combo is not None
        assert dialog._case_combo.objectName() == "deadlineCaseCombo"
        assert dialog._date_edit.width() >= 220
        assert dialog._btn_pick_date.width() >= 48
        assert dialog._time_edit.width() >= 84
        assert dialog._all_day_checkbox.width() >= 74
        assert dialog._type_combo.width() >= 200
        assert dialog._priority_combo.width() >= 68
        assert dialog._type_combo.y() == dialog._priority_combo.y()
        assert dialog._remind_edit.width() >= 280
        assert dialog._description_edit.height() >= 88
        assert dialog.findChild(QWidget, "deadlineDateTimeField") is not None
        assert dialog.findChild(QWidget, "deadlineTypePriorityField") is not None
        assert dialog.findChild(QWidget, "deadlineRemindBlock") is not None

        dialog.resize(1200, 900)
        qapp.processEvents()
        qapp.processEvents()
        dialog.resize(700, 500)
        qapp.processEvents()
        qapp.processEvents()
        restored_smart_sizes = (
            dialog._smart_input.height(),
            dialog._smart_result_label.height(),
        )

        dialog.resize(1200, 900)
        qapp.processEvents()
        qapp.processEvents()
        dialog.resize(700, 500)
        qapp.processEvents()
        qapp.processEvents()

        assert (
            dialog._smart_input.height(),
            dialog._smart_result_label.height(),
        ) == restored_smart_sizes
        assert dialog._smart_input.height() >= 88
        assert dialog._smart_result_label.height() >= 118
        assert dialog._description_edit.height() >= 88
        assert dialog._date_edit.width() >= 220

    def test_deadline_editor_dialog_splitter_allows_resizing_panels(self, qapp):
        dialog = DeadlineEditorDialog(
            cases=[
                {"id": "case_1", "name": "张三合同纠纷", "tags": ["合同"]},
            ]
        )
        dialog.show()
        qapp.processEvents()

        splitter = dialog.findChild(QSplitter, "deadlineCardsSplitter")
        smart_card = next(
            widget
            for widget in dialog.findChildren(QFrame)
            if widget.objectName() == "deadlineSmartCard"
        )
        form_card = next(
            widget
            for widget in dialog.findChildren(QFrame)
            if widget.objectName() == "deadlineFormCard"
        )

        assert splitter is not None
        dialog.resize(900, 650)
        qapp.processEvents()
        original_sizes = splitter.sizes()
        splitter.setSizes([420, 520])
        qapp.processEvents()

        resized_sizes = splitter.sizes()
        assert len(resized_sizes) == 2
        assert resized_sizes[0] > original_sizes[0]
        assert smart_card.width() >= 280
        assert form_card.width() > 0
