# -*- coding: utf-8 -*-
"""期限日历绘制回归测试"""

import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QEvent, QRect, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from src.core.case_manager import CaseManager
from src.gui.calendar_dialog import CalendarDialog, DeadlineCalendarWidget, DeadlineDetailRow
from src.utils.runtime_adapters import FixedTimeProvider


class TestCalendarDialog:
    """日历界面最小回归测试。"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.case_folder = self.temp_dir / "日历案件"
        self.case_folder.mkdir()
        CaseManager._instance = None
        self.manager = CaseManager()
        self.manager._cases_file = self.temp_dir / "cases.json"
        self.manager._cases = {}
        self.manager._global_deadlines = []

    def teardown_method(self):
        CaseManager._instance = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_is_selected_day_without_selected_date_returns_false(self, qapp):
        """未选中日期时应返回 False，而不是 None。"""
        widget = DeadlineCalendarWidget()
        assert widget.get_selected_date() is None
        assert widget._is_selected_day(5) is False

    def test_deadline_calendar_widget_renders_without_selected_date(self, qapp):
        widget = DeadlineCalendarWidget()
        widget.resize(760, 560)
        widget.set_month(2026, 4)
        widget.set_deadlines([
            {"date": "2026-04-05", "type": "deadline", "title": "举证期限"},
            {"date": "2026-04-15", "type": "hearing", "title": "开庭安排"},
        ])
        widget.show()
        qapp.processEvents()

        pixmap = QPixmap(widget.size())
        widget.render(pixmap)
        qapp.processEvents()

        assert not pixmap.isNull()
        assert widget.get_selected_date() is None

    def test_deadline_calendar_widget_renders_with_selected_date(self, qapp):
        widget = DeadlineCalendarWidget()
        widget.resize(760, 560)
        widget.set_month(2026, 4)
        widget._selected_date = date(2026, 4, 15)
        widget.set_deadlines([
            {"date": "2026-04-15", "type": "hearing", "title": "开庭安排"},
        ])
        widget.show()
        qapp.processEvents()

        pixmap = QPixmap(widget.size())
        widget.render(pixmap)
        qapp.processEvents()

        assert not pixmap.isNull()

    def test_month_view_uses_actual_week_rows_for_taller_cards(self, qapp):
        """月视图应按当月实际周数布局，而不是固定 6 行。"""
        widget = DeadlineCalendarWidget()
        widget.set_month(2026, 4)

        assert widget._row_count() == 5

    def test_deadline_preview_items_include_overflow_count(self, qapp):
        """日期卡预览应保留文本，并返回额外事项数量。"""
        widget = DeadlineCalendarWidget()
        widget.set_deadlines([
            {"date": "2026-04-18", "type": "hearing", "title": "牛先生民间借贷纠纷开庭", "time": "09:30", "all_day": False},
            {"date": "2026-04-18", "type": "deadline", "title": "补正材料截止", "all_day": True},
            {"date": "2026-04-18", "type": "custom", "title": "与当事人沟通", "time": "16:20", "all_day": False},
        ])

        previews, extra_count = widget._get_preview_items("2026-04-18", max_items=2)

        assert len(previews) == 2
        assert "09:30" in previews[0]["text"]
        assert "牛先生民间借贷纠纷开庭" in previews[0]["text"]
        assert previews[0]["deadline"]["date"] == "2026-04-18"
        assert extra_count == 1

    def test_day_visual_state_marks_overdue_and_nearby_deadlines(self, qapp):
        """有期限的日期卡应能区分逾期与近 7 天状态。"""
        widget = DeadlineCalendarWidget()

        overdue_day = date.today() - timedelta(days=1)
        upcoming_day = date.today()
        if upcoming_day.day <= 21:
            upcoming_day = upcoming_day.replace(day=upcoming_day.day + 3)

        overdue_state, overdue_badge = widget._day_visual_state(
            overdue_day,
            [{"date": overdue_day.strftime("%Y-%m-%d"), "title": "补正期限", "all_day": True, "status": "pending"}],
        )
        upcoming_state, upcoming_badge = widget._day_visual_state(
            upcoming_day,
            [{"date": upcoming_day.strftime("%Y-%m-%d"), "title": "开庭安排", "time": "09:30", "all_day": False, "status": "pending", "type": "hearing"}],
        )

        assert overdue_state == "overdue"
        assert overdue_badge == "已过期"
        assert upcoming_state == "hearing"
        assert upcoming_badge == "开庭"

    def test_day_visual_state_uses_injected_time_provider(self, qapp):
        """日期状态判定应支持注入固定时间，避免测试受真实日期影响。"""
        provider = FixedTimeProvider(datetime(2026, 4, 24, 10, 0))
        widget = DeadlineCalendarWidget(time_provider=provider)

        state, badge = widget._day_visual_state(
            date(2026, 4, 23),
            [{"date": "2026-04-23", "title": "举证期限", "all_day": True, "status": "pending"}],
        )

        assert state == "overdue"
        assert badge == "已过期"

    def test_hearing_deadline_preview_style_uses_prominent_red(self, qapp):
        """开庭事项在月视图中应使用最醒目的红色。"""
        widget = DeadlineCalendarWidget()
        target_day = date.today() + timedelta(days=1)

        style = widget._deadline_visual_style({
            "date": target_day.strftime("%Y-%m-%d"),
            "title": "开庭安排",
            "time": "09:30",
            "all_day": False,
            "status": "pending",
            "type": "hearing",
        })

        assert style["state"] == "normal"
        assert style["indicator_color"].name() == "#dc2626"

    def test_overdue_deadline_preview_style_turns_gray(self, qapp):
        """过期事项在月视图中应切换为灰色样式。"""
        widget = DeadlineCalendarWidget()
        overdue_day = date.today() - timedelta(days=1)

        style = widget._deadline_visual_style({
            "date": overdue_day.strftime("%Y-%m-%d"),
            "title": "补正期限",
            "all_day": True,
            "status": "pending",
            "type": "deadline",
        })

        assert style["state"] == "overdue"
        assert style["strike_out"] is False
        assert style["indicator_color"].name() == "#9ca3af"

    def test_completed_deadline_preview_style_uses_strikeout(self, qapp):
        """已完成事项在月视图中应使用删除线样式。"""
        widget = DeadlineCalendarWidget()

        style = widget._deadline_visual_style({
            "date": "2026-04-18",
            "title": "补证期限",
            "all_day": True,
            "status": "completed",
            "type": "deadline",
        })

        assert style["state"] == "completed"
        assert style["strike_out"] is True
        assert style["indicator_color"].name() == "#94a3b8"

    def test_compact_calendar_card_still_allows_single_preview(self, qapp):
        """窄日期卡也应至少能显示 1 条事项预览。"""
        widget = DeadlineCalendarWidget()
        assert widget._preview_capacity(QRect(0, 0, 82, 80)) == 1

    def test_taller_month_card_can_show_more_preview_items(self, qapp):
        """更高的月卡片应允许展示 3-4 条以上事项。"""
        widget = DeadlineCalendarWidget()

        assert widget._preview_capacity(QRect(0, 0, 126, 132)) >= 4

    def test_compact_calendar_card_hides_top_badge(self, qapp):
        """窄日期卡不应再绘制顶部"1项"徽标挡住日期。"""
        widget = DeadlineCalendarWidget()
        assert widget._show_top_badge(QRect(0, 0, 82, 80), "normal", 1) is False
        assert widget._show_top_badge(QRect(0, 0, 140, 96), "normal", 2) is True

    def test_calendar_extra_indicator_uses_more_label(self, qapp):
        """超出显示容量时应使用更明确的“更多 n 项”。"""
        widget = DeadlineCalendarWidget()
        assert widget._extra_indicator_text(1) == "更多 1 项"
        assert widget._extra_indicator_text(3) == "更多 3 项"

    def test_click_more_indicator_temporarily_expands_month_card(self, qapp):
        """点击“更多 n 项”后应临时展开该日卡片，鼠标移开后恢复。"""
        widget = DeadlineCalendarWidget()
        widget.resize(560, 420)
        widget.set_month(2026, 4)
        widget.set_deadlines([
            {"date": "2026-04-25", "type": "hearing", "title": "开庭安排", "time": "09:00", "all_day": False},
            {"date": "2026-04-25", "type": "deadline", "title": "举证期限", "all_day": True},
            {"date": "2026-04-25", "type": "custom", "title": "提交代理意见", "time": "16:00", "all_day": False},
        ])
        widget.show()
        qapp.processEvents()

        pixmap = QPixmap(widget.size())
        widget.render(pixmap)
        qapp.processEvents()

        target_day = date(2026, 4, 25)
        more_region = next(
            rect for rect, day_value in widget._more_hit_regions if day_value == target_day
        )
        base_row = (target_day.day + widget._first_day_weekday - 1) // 7
        base_col = (target_day.day + widget._first_day_weekday - 1) % 7
        base_height = widget._card_rect(base_row, base_col).height()

        QTest.mouseClick(
            widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            more_region.center(),
        )
        assert widget._expanded_more_date == target_day

        widget.render(QPixmap(widget.size()))
        qapp.processEvents()
        assert widget._expanded_card_region is not None
        assert widget._expanded_card_region.height() > base_height

        widget.leaveEvent(QEvent(QEvent.Type.Leave))
        assert widget._expanded_more_date is None

    def test_deadline_calendar_widget_renders_week_view(self, qapp):
        """周视图应能正常渲染，并展示更大的单周卡片。"""
        widget = DeadlineCalendarWidget()
        widget.resize(980, 560)
        widget.set_view_mode("week", date(2026, 4, 15))
        widget.set_selected_date(date(2026, 4, 15))
        widget.set_deadlines([
            {"date": "2026-04-13", "type": "deadline", "title": "举证期限"},
            {"date": "2026-04-15", "type": "hearing", "title": "开庭安排", "time": "09:30", "all_day": False},
            {"date": "2026-04-18", "type": "custom", "title": "与当事人沟通", "time": "16:00", "all_day": False},
        ])
        widget.show()
        qapp.processEvents()

        pixmap = QPixmap(widget.size())
        widget.render(pixmap)
        qapp.processEvents()

        assert not pixmap.isNull()
        assert widget.get_view_mode() == "week"

    def test_week_time_scale_snaps_to_five_minutes(self, qapp):
        """周视图时间拖拽应吸附到 5 分钟刻度。"""
        widget = DeadlineCalendarWidget()

        assert widget._week_snap_minutes(526) == 525
        assert widget._week_minutes_to_time_text(525) == "08:45"
        assert widget._week_snap_minutes(528) == 530
        assert widget._week_minutes_to_time_text(530) == "08:50"

    def test_week_preview_lines_prioritize_hearing_time_and_case(self, qapp):
        """周视图应优先突出开庭时间和案件名。"""
        widget = DeadlineCalendarWidget()

        primary, secondary = widget._week_preview_lines(
            {
                "date": (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "title": "开庭安排",
                "type": "hearing",
                "time": "09:30",
                "all_day": False,
                "case_name": "张三买卖合同纠纷案",
                "status": "pending",
            },
            220,
        )

        assert primary == "09:30 · 开庭"
        assert "张三买卖合同纠纷案" in secondary

    def test_hearing_compact_preview_includes_case_name_when_space_allows(self, qapp):
        """月视图宽卡片中，开庭预览应带出案件简称。"""
        widget = DeadlineCalendarWidget()
        target_day = date.today() + timedelta(days=2)

        preview = widget._format_compact_deadline_preview(
            {
                "date": target_day.strftime("%Y-%m-%d"),
                "title": "开庭安排",
                "type": "hearing",
                "time": "09:30",
                "all_day": False,
                "case_name": "王某某劳动争议纠纷",
                "status": "pending",
            },
            148,
        )

        assert "09:30" in preview
        assert "开庭" in preview
        assert "王某某" in preview

    def test_calendar_open_case_navigation_emits_case_and_deadline(self, qapp):
        case_id = self.manager.register_case({
            "name": "日历跳转案件",
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
        dialog = CalendarDialog()
        received = {}
        dialog.navigate_to_deadline_requested.connect(
            lambda target_case_id, deadline_id: received.update({
                "case_id": target_case_id,
                "deadline_id": deadline_id,
            })
        )

        dialog._on_open_case_from_detail({"case_id": case_id, "id": "dl_nav"})

        assert received == {"case_id": case_id, "deadline_id": ""}

    def test_calendar_case_manager_button_opens_case_manager_dialog(self, qapp, monkeypatch):
        captured = {}

        class DummyCaseManagerDialog:
            def __init__(self, parent=None):
                captured["parent"] = parent

            def exec(self):
                captured["executed"] = True

        monkeypatch.setattr("src.gui.case_manager_dialog.CaseManagerDialog", DummyCaseManagerDialog)

        dialog = CalendarDialog()
        dialog.show()
        qapp.processEvents()

        assert dialog._btn_case_manager.text() == "案件管理"

        dialog._on_case_manager()
        qapp.processEvents()

        assert captured.get("executed") is True

    def test_calendar_filter_combos_use_visible_dropdown_style(self, qapp):
        """右侧筛选框应保留清晰的下拉按钮入口。"""
        dialog = CalendarDialog()

        for combo in (
            dialog._tag_filter_combo,
            dialog._case_filter_combo,
            dialog._status_filter_combo,
            dialog._type_filter_combo,
        ):
            assert combo.objectName() == "calendarFilterCombo"
            style = combo.styleSheet()
            assert "QComboBox#calendarFilterCombo::drop-down" in style
            assert "QComboBox#calendarFilterCombo::down-arrow" in style
            assert "dropdown_arrow.svg" in style

    def test_calendar_edit_deadline_stays_inside_calendar_dialog(self, qapp, monkeypatch):
        dialog = CalendarDialog()
        called = {}
        monkeypatch.setattr(
            dialog,
            "_open_deadline_dialog",
            lambda **kwargs: called.update({"deadline_id": kwargs.get("deadline", {}).get("id")}) or True,
        )

        dialog._on_edit_deadline_from_detail({"case_id": "case_x", "id": "dl_local"})

        assert called == {"deadline_id": "dl_local"}

    def test_calendar_toggle_deadline_updates_case_manager(self, qapp):
        case_id = self.manager.register_case({
            "name": "日历完成案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_toggle",
                    "title": "补证期限",
                    "date": "2026-04-18",
                    "status": "pending",
                }
            ],
        })
        dialog = CalendarDialog()
        dialog._calendar.set_selected_date(date(2026, 4, 18))

        dialog._on_toggle_deadline_from_detail({
            "case_id": case_id,
            "id": "dl_toggle",
            "status": "pending",
        })

        updated_case = self.manager.get_case(case_id)
        assert updated_case is not None
        updated_deadline = updated_case["deadlines"][0]
        assert updated_deadline["status"] == "completed"
        assert updated_deadline["completed_at"]

    def test_calendar_all_mode_supports_tag_filter(self, qapp):
        contract_case_id = self.manager.register_case({
            "name": "合同纠纷案件",
            "path": str(self.case_folder),
            "tags": ["合同", "民事"],
            "deadlines": [
                {
                    "id": "dl_contract",
                    "title": "举证期限",
                    "date": "2026-04-22",
                    "status": "pending",
                    "type": "deadline",
                }
            ],
        })
        self.manager.register_case({
            "name": "劳动争议案件",
            "path": str(self.case_folder),
            "tags": ["劳动"],
            "deadlines": [
                {
                    "id": "dl_labor",
                    "title": "开庭安排",
                    "date": "2026-04-23",
                    "status": "pending",
                    "type": "hearing",
                }
            ],
        })

        dialog = CalendarDialog()
        dialog._set_detail_mode("all")

        tag_index = dialog._tag_filter_combo.findData("合同")
        assert tag_index >= 0
        dialog._tag_filter_combo.setCurrentIndex(tag_index)
        qapp.processEvents()

        filtered = dialog._filtered_deadlines_for_current_view()

        assert len(filtered) == 1
        assert filtered[0]["case_id"] == contract_case_id
        assert filtered[0]["case_tags"] == ["合同", "民事"]

    def test_empty_filtered_detail_panel_removes_old_deadline_cards(self, qapp):
        case_id = self.manager.register_case({
            "name": "筛选清空案件",
            "path": str(self.case_folder),
            "tags": ["合同"],
            "deadlines": [
                {
                    "id": "dl_visible",
                    "title": "举证期限",
                    "date": "2026-04-22",
                    "status": "pending",
                    "type": "deadline",
                }
            ],
        })

        dialog = CalendarDialog()
        dialog.show()
        dialog._set_detail_mode("all")
        qapp.processEvents()

        case_index = dialog._case_filter_combo.findData(case_id)
        dialog._case_filter_combo.setCurrentIndex(case_index)
        qapp.processEvents()
        assert len(dialog._detail_container.findChildren(DeadlineDetailRow)) >= 1

        dialog._type_filter_combo.setCurrentIndex(dialog._type_filter_combo.findData("hearing"))
        qapp.processEvents()

        assert dialog._detail_container.findChildren(DeadlineDetailRow) == []
        labels = [label.text() for label in dialog._detail_container.findChildren(type(dialog._detail_title))]
        assert "当前筛选下暂无事项" in labels

    def test_calendar_all_mode_supports_case_filter_and_risk_queue(self, qapp):
        case_a = self.manager.register_case({
            "name": "买卖合同纠纷",
            "path": str(self.case_folder),
            "tags": ["合同"],
            "deadlines": [
                {
                    "id": "dl_a",
                    "title": "举证期限",
                    "date": (date.today() + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "status": "pending",
                    "type": "deadline",
                }
            ],
        })
        self.manager.register_case({
            "name": "劳动仲裁案件",
            "path": str(self.case_folder),
            "tags": ["劳动"],
            "deadlines": [
                {
                    "id": "dl_b",
                    "title": "开庭安排",
                    "date": (date.today() + timedelta(days=5)).strftime("%Y-%m-%d"),
                    "status": "pending",
                    "type": "hearing",
                }
            ],
        })

        dialog = CalendarDialog()
        dialog._set_detail_mode("all")

        case_index = dialog._case_filter_combo.findData(case_a)
        assert case_index >= 0
        dialog._case_filter_combo.setCurrentIndex(case_index)
        qapp.processEvents()

        filtered = dialog._filtered_deadlines_for_current_view()
        assert len(filtered) == 1
        assert filtered[0]["case_id"] == case_a

        dialog._apply_risk_filter("hearing_week")
        qapp.processEvents()
        filtered = dialog._filtered_deadlines_for_current_view()
        assert len(filtered) == 0

        dialog._case_filter_combo.setCurrentIndex(0)
        qapp.processEvents()
        filtered = dialog._filtered_deadlines_for_current_view()
        assert len(filtered) == 1
        assert filtered[0]["type"] == "hearing"

    def test_calendar_detail_expand_toggle_collapses_rows_but_keeps_actions(self, qapp):
        self.manager.register_case({
            "name": "折叠测试案件",
            "path": str(self.case_folder),
            "tags": ["合同"],
            "deadlines": [
                {
                    "id": "dl_expand",
                    "title": "开庭安排 - 离婚纠纷",
                    "date": "2026-04-13",
                    "time": "09:30",
                    "status": "pending",
                    "type": "hearing",
                    "description": "补充说明",
                }
            ],
        })

        dialog = CalendarDialog()
        dialog.show()
        dialog._set_detail_mode("all")
        qapp.processEvents()

        rows = dialog._detail_container.findChildren(DeadlineDetailRow)
        assert rows
        assert dialog._detail_expand_toggle_btn.text() == "收缩"

        dialog._set_detail_rows_expanded(False)
        qapp.processEvents()

        row = dialog._detail_container.findChildren(DeadlineDetailRow)[0]
        assert dialog._detail_expand_toggle_btn.text() == "展开"
        assert row._meta_label.wordWrap() is False
        assert row._chips_widget.isHidden()
        assert row._action_widget.isVisible()

    def test_calendar_quick_template_defaults_match_lawyer_workflow(self, qapp):
        dialog = CalendarDialog()

        evidence = dialog._quick_template_defaults("evidence")
        appeal = dialog._quick_template_defaults("appeal")
        payment = dialog._quick_template_defaults("payment")

        assert evidence["title"] == "举证期限"
        assert evidence["priority"] == "high"
        assert evidence["remind_before"] == [7, 3, 1, 0]
        assert appeal["title"] == "上诉期限"
        assert payment["title"] == "缴费期限"
        assert payment["remind_before"] == [3, 1, 0]

    def test_calendar_quick_add_supports_top_level_deadline_entries(self, qapp, monkeypatch):
        dialog = CalendarDialog()
        captured = {}

        monkeypatch.setattr(dialog, "_on_add_deadline", lambda deadline_type: captured.update({"type": deadline_type}))

        dialog._on_quick_add_template("add_hearing")
        assert captured == {"type": "hearing"}

        dialog._on_quick_add_template("add_deadline")
        assert captured == {"type": "deadline"}

    def test_calendar_postpone_deadline_moves_it_to_next_day(self, qapp):
        case_id = self.manager.register_case({
            "name": "顺延案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_postpone",
                    "title": "补证期限",
                    "date": "2026-04-18",
                    "status": "pending",
                    "type": "deadline",
                }
            ],
        })

        dialog = CalendarDialog()
        dialog._on_postpone_deadline_from_detail({
            "case_id": case_id,
            "id": "dl_postpone",
            "date": "2026-04-18",
            "status": "pending",
        })

        updated_case = self.manager.get_case(case_id)
        assert updated_case is not None
        updated_deadline = updated_case["deadlines"][0]
        assert updated_deadline["date"] == "2026-04-19"
        assert updated_deadline["status"] == "pending"

    def test_calendar_week_view_only_loads_current_week_deadlines(self, qapp):
        """切换到周视图后，日历只应绘制当前周事项。"""
        self.manager.register_case({
            "name": "周视图案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_week_1",
                    "title": "本周开庭",
                    "date": "2026-04-15",
                    "status": "pending",
                    "type": "hearing",
                },
                {
                    "id": "dl_week_2",
                    "title": "下周补证",
                    "date": "2026-04-22",
                    "status": "pending",
                    "type": "deadline",
                },
            ],
        })

        dialog = CalendarDialog()
        dialog._jump_to_date(date(2026, 4, 15))
        dialog._set_calendar_view_mode("week")
        qapp.processEvents()

        visible_dates = sorted(dialog._calendar._deadlines.keys())

        assert dialog._calendar.get_view_mode() == "week"
        assert visible_dates == ["2026-04-15"]
        assert "13日 - 19日" in dialog._month_label.text()

    def test_calendar_week_view_navigation_moves_by_full_week(self, qapp):
        """周视图翻页时应按整周切换，而不是按月份。"""
        dialog = CalendarDialog()
        dialog._jump_to_date(date(2026, 4, 15))
        dialog._set_calendar_view_mode("week")

        dialog._on_next_month()
        assert dialog._calendar.get_selected_date() == date(2026, 4, 22)
        assert "20日 - 26日" in dialog._month_label.text()

        dialog._on_prev_month()
        assert dialog._calendar.get_selected_date() == date(2026, 4, 15)

    def test_drag_deadline_from_week_view_updates_date_and_time(self, qapp):
        case_id = self.manager.register_case({
            "name": "周拖拽案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_drag",
                    "title": "开庭安排",
                    "date": "2026-04-15",
                    "time": "09:00",
                    "all_day": False,
                    "status": "pending",
                    "type": "hearing",
                }
            ],
        })

        dialog = CalendarDialog()
        dialog._on_drag_deadline_from_week_view(
            {
                "case_id": case_id,
                "id": "dl_drag",
            },
            date(2026, 4, 16),
            "08:45",
        )

        updated_case = self.manager.get_case(case_id)
        assert updated_case is not None
        updated_deadline = updated_case["deadlines"][0]
        assert updated_deadline["date"] == "2026-04-16"
        assert updated_deadline["time"] == "08:45"
        assert updated_deadline["all_day"] is False

    def test_drag_deadline_from_month_view_updates_date_and_preserves_time(self, qapp):
        case_id = self.manager.register_case({
            "name": "月拖拽案件",
            "path": str(self.case_folder),
            "deadlines": [
                {
                    "id": "dl_month_drag",
                    "title": "补证期限",
                    "date": "2026-04-13",
                    "time": "10:30",
                    "all_day": False,
                    "status": "pending",
                    "type": "deadline",
                }
            ],
        })

        dialog = CalendarDialog()
        dialog._on_drag_deadline_from_calendar(
            {
                "case_id": case_id,
                "id": "dl_month_drag",
                "date": "2026-04-13",
                "time": "10:30",
                "all_day": False,
            },
            date(2026, 4, 12),
            None,
        )

        updated_case = self.manager.get_case(case_id)
        assert updated_case is not None
        updated_deadline = updated_case["deadlines"][0]
        assert updated_deadline["date"] == "2026-04-12"
        assert updated_deadline["time"] == "10:30"
        assert updated_deadline["all_day"] is False

    def test_global_deadline_toggle_updates_without_case(self, qapp):
        deadline_id = self.manager.add_global_deadline({
            "id": "dl_global_toggle",
            "title": "日历临时任务",
            "date": "2026-04-18",
            "status": "pending",
            "all_day": True,
        })

        dialog = CalendarDialog()
        dialog._on_toggle_deadline_from_detail({
            "case_id": "",
            "id": deadline_id,
            "status": "pending",
        })

        global_deadlines = self.manager.get_global_deadlines()
        updated = next(item for item in global_deadlines if item["id"] == deadline_id)
        assert updated["status"] == "completed"

    def test_completed_deadline_detail_row_shows_strikeout(self, qapp):
        """右侧详情中的已完成事项应显示删除线。"""
        row = DeadlineDetailRow(
            {
                "title": "补证期限",
                "date": "2026-04-18",
                "status": "completed",
                "all_day": True,
                "case_name": "日历案件",
            },
            edit_callback=None,
            toggle_callback=None,
            remove_callback=None,
        )

        assert row._title_label.font().strikeOut() is True
        assert row._meta_label.font().strikeOut() is True

    def test_deadline_detail_row_meta_includes_countdown_hint(self, qapp):
        """右侧事项卡应直接显示倒计时提示。"""
        target_day = date.today() + timedelta(days=2)
        row = DeadlineDetailRow(
            {
                "title": "举证期限",
                "date": target_day.strftime("%Y-%m-%d"),
                "status": "pending",
                "all_day": True,
                "case_name": "示例案件",
            },
            edit_callback=None,
            toggle_callback=None,
            remove_callback=None,
        )

        assert "D-2" in row._meta_label.text()

    def test_deadline_detail_row_collapsed_meta_uses_single_line_elide(self, qapp):
        """收缩态下，标题下方信息应单行完整展示，并以省略号收尾，而不是被裁切。"""
        row = DeadlineDetailRow(
            {
                "title": "开庭安排 - 离婚纠纷",
                "date": "2026-04-13",
                "time": "09:30",
                "status": "pending",
                "all_day": False,
                "case_name": "2025民123new2023-01-06章云云--吴江生 离婚一审",
                "description": "补充说明",
            },
            edit_callback=None,
            toggle_callback=None,
            remove_callback=None,
            show_date=True,
            expanded=False,
        )
        row.resize(360, 120)
        row.show()
        qapp.processEvents()

        assert row._meta_label.wordWrap() is False
        assert row._chips_widget.isHidden()
        assert row._action_widget.isVisible()
        assert "…" in row._meta_label.text() or "..." in row._meta_label.text()
