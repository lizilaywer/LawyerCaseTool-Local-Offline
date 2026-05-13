# -*- coding: utf-8 -*-
"""工具中心对话框测试"""

from src.core.court_sms_service import CourtSmsCaseMatch, CourtSmsHearingNotice, CourtSmsParseResult
from src.gui.tool_center_dialog import ToolCenterDialog


class TestToolCenterDialog:
    """工具中心最小回归。"""

    class _RunningWorker:
        def isRunning(self):
            return True

    def test_dialog_instantiates_and_calculates_litigation_fee(self, qapp):
        dialog = ToolCenterDialog()
        dialog.show()
        qapp.processEvents()

        assert dialog._tabs.count() == 9

        dialog._litigation_amount.setValue(100000)
        dialog._litigation_type.setCurrentIndex(0)
        dialog._calculate_litigation_fee()
        qapp.processEvents()

        html = dialog._litigation_result.toHtml()
        assert "2300.00" in html or "2300" in html

    def test_fee_amount_inputs_start_blank_and_results_are_compact(self, qapp):
        dialog = ToolCenterDialog()
        dialog.show()
        qapp.processEvents()

        assert dialog._litigation_amount.lineEdit().text() == ""
        assert dialog._apply_amount.lineEdit().text() == ""
        assert dialog._bankruptcy_assets.lineEdit().text() == ""

        assert dialog._litigation_result.minimumHeight() <= 60
        assert dialog._apply_result.maximumHeight() <= 80
        assert dialog._bankruptcy_result.maximumHeight() <= 80

    def test_court_sms_case_combo_remains_searchable_after_parse(self, qapp, monkeypatch):
        dialog = ToolCenterDialog()
        dialog.show()
        qapp.processEvents()

        cases = [
            {
                "id": "case-a",
                "name": "石台借贷纠纷",
                "path": "/tmp/case-a",
                "category": "civil",
                "tags": ["借贷"],
                "info_fields": [],
                "variables": {"case_number": "（2026）皖1722民初273号"},
            },
            {
                "id": "case-b",
                "name": "张三执行案件",
                "path": "/tmp/case-b",
                "category": "execution",
                "tags": ["执行"],
                "info_fields": [],
                "variables": {},
            },
        ]

        monkeypatch.setattr(dialog._case_manager, "get_all_cases", lambda: cases)
        monkeypatch.setattr(
            dialog._court_sms_service,
            "match_cases",
            lambda parsed, case_records, preferred_case_id="": [
                CourtSmsCaseMatch(
                    case_id="case-a",
                    case_name="石台借贷纠纷",
                    case_path="/tmp/case-a",
                    score=96,
                    reasons=["案号匹配"],
                )
            ],
        )

        dialog._sms_parse_result = CourtSmsParseResult(
            raw_text="短信",
            link="https://example.com",
            court_name="石台县人民法院",
            recipient_name="曹忠发",
            case_number="（2026）皖1722民初273号",
            qdbh="q",
            sdbh="s",
            sdsin="sin",
        )
        dialog._refresh_case_matches()
        qapp.processEvents()

        line_edit = dialog._court_sms_case_combo.lineEdit()
        assert line_edit is not None
        assert dialog._court_sms_case_combo.isEditable()
        assert dialog._court_sms_case_combo.currentData() == "case-a"
        assert dialog._get_active_court_sms_case_id() == "case-a"
        assert dialog._get_court_sms_case_search_text() == ""

        dialog._begin_court_sms_case_search()
        qapp.processEvents()

        assert line_edit.text() == ""
        assert dialog._court_sms_case_combo.currentIndex() == -1
        assert dialog._get_active_court_sms_case_id() == "case-a"

        line_edit.setText("张三")
        dialog._handle_court_sms_case_search_input("张三")
        qapp.processEvents()

        assert line_edit.text() == "张三"
        assert dialog._court_sms_case_combo.currentIndex() == -1
        assert dialog._get_active_court_sms_case_id() == ""

        dialog._select_court_sms_case_from_text("张三执行案件  ·  案件项目")
        qapp.processEvents()

        assert dialog._court_sms_case_combo.currentData() == "case-b"

    def test_add_selected_hearing_notice_creates_case_deadline(self, qapp, monkeypatch):
        dialog = ToolCenterDialog()
        dialog.show()
        qapp.processEvents()

        cases = [
            {
                "id": "case-a",
                "name": "贵池离婚纠纷",
                "path": "/tmp/case-a",
                "deadlines": [],
            }
        ]
        monkeypatch.setattr(dialog._case_manager, "get_case", lambda case_id: cases[0] if case_id == "case-a" else None)
        monkeypatch.setattr(dialog._case_manager, "add_deadline", lambda case_id, data: "dl_auto_1")
        monkeypatch.setattr(
            dialog,
            "_notify_case_deadline_updated",
            lambda case_id: None,
        )
        monkeypatch.setattr(
            "src.gui.tool_center_dialog.QMessageBox.information",
            lambda *args, **kwargs: 0,
        )

        dialog._court_sms_case_options = [{"case_id": "case-a", "display": "贵池离婚纠纷", "search": "贵池 离婚", "kind": "suggested", "score": "90"}]
        dialog._populate_court_sms_case_combo(selected_case_id="case-a")
        dialog._sms_hearing_notices = [
            CourtSmsHearingNotice(
                document_name="传票（章云云）.pdf",
                document_path="/tmp/传票（章云云）.pdf",
                notice_type="传票",
                case_number="（2026）皖1702民初3435号",
                cause="离婚纠纷",
                hearing_date="2026-04-13",
                hearing_time="09:30",
                hearing_place="杏花村第三法庭",
                signer="方圆圆",
                contact_person="孙慧敏",
                court_name="池州市贵池区人民法院",
            )
        ]
        dialog._populate_court_sms_hearing_notices()
        qapp.processEvents()

        dialog._add_selected_court_sms_hearing_deadline()
        qapp.processEvents()

        assert dialog._sms_hearing_notices[0].added_case_id == "case-a"
        assert dialog._sms_hearing_notices[0].added_deadline_id == "dl_auto_1"

    def test_added_hearing_notice_enables_case_and_calendar_navigation(self, qapp, monkeypatch):
        dialog = ToolCenterDialog()
        dialog.show()
        qapp.processEvents()

        cases = [
            {
                "id": "case-a",
                "name": "贵池离婚纠纷",
                "path": "/tmp/case-a",
                "deadlines": [],
            }
        ]
        monkeypatch.setattr(dialog._case_manager, "get_case", lambda case_id: cases[0] if case_id == "case-a" else None)
        monkeypatch.setattr(dialog._case_manager, "add_deadline", lambda case_id, data: "dl_auto_1")
        monkeypatch.setattr(dialog, "_notify_case_deadline_updated", lambda case_id: None)
        monkeypatch.setattr("src.gui.tool_center_dialog.QMessageBox.information", lambda *args, **kwargs: 0)
        monkeypatch.setattr(dialog, "accept", lambda: None)

        dialog._court_sms_case_options = [
            {
                "case_id": "case-a",
                "display": "贵池离婚纠纷",
                "search": "贵池 离婚",
                "kind": "suggested",
                "score": "90",
            }
        ]
        dialog._populate_court_sms_case_combo(selected_case_id="case-a")
        dialog._sms_hearing_notices = [
            CourtSmsHearingNotice(
                document_name="传票（章云云）.pdf",
                document_path="/tmp/传票（章云云）.pdf",
                notice_type="传票",
                case_number="（2026）皖1702民初3435号",
                cause="离婚纠纷",
                hearing_date="2026-04-13",
                hearing_time="09:30",
                hearing_place="杏花村第三法庭",
                signer="方圆圆",
                contact_person="孙慧敏",
                court_name="池州市贵池区人民法院",
            )
        ]
        dialog._populate_court_sms_hearing_notices()
        qapp.processEvents()

        dialog._add_selected_court_sms_hearing_deadline()
        qapp.processEvents()

        captured = {}
        dialog.navigate_to_case_requested.connect(lambda case_id: captured.update({"case_id": case_id}))
        dialog.navigate_to_calendar_requested.connect(lambda date_text: captured.update({"date": date_text}))

        assert dialog._btn_open_court_sms_case.isEnabled()
        assert dialog._btn_open_court_sms_calendar.isEnabled()

        dialog._open_court_sms_case_from_hearing()
        dialog._open_court_sms_calendar_from_hearing()
        qapp.processEvents()

        assert captured.get("case_id") == "case-a"
        assert captured.get("date") == "2026-04-13"

    def test_read_and_stage_is_guarded_while_background_worker_is_running(self, qapp, monkeypatch):
        dialog = ToolCenterDialog()
        dialog.show()
        qapp.processEvents()

        dialog._court_sms_input.setPlainText("测试短信")
        dialog._court_sms_read_worker = self._RunningWorker()
        captured = {}
        monkeypatch.setattr(
            "src.gui.tool_center_dialog.QMessageBox.information",
            lambda *args, **kwargs: captured.update({"shown": True}),
        )

        dialog._read_and_stage_court_documents()
        qapp.processEvents()

        assert captured.get("shown") is True
        assert dialog._court_sms_read_worker is not None

    def test_parse_court_sms_auto_starts_read_and_stage(self, qapp, monkeypatch):
        dialog = ToolCenterDialog()
        dialog.show()
        qapp.processEvents()

        parsed = CourtSmsParseResult(
            raw_text="短信",
            link="https://example.com",
            court_name="石台县人民法院",
            recipient_name="曹忠发",
            case_number="（2026）皖1722民初273号",
            qdbh="q",
            sdbh="s",
            sdsin="sin",
        )
        captured = {}

        monkeypatch.setattr(dialog._court_sms_service, "parse_sms", lambda text: parsed)
        monkeypatch.setattr(dialog._court_sms_service, "suggest_relative_folder", lambda parsed_result: "法院送达文书")
        monkeypatch.setattr(
            dialog,
            "_read_and_stage_court_documents",
            lambda pre_parsed=None: captured.update({"parsed": pre_parsed}),
        )

        dialog._court_sms_input.setPlainText("测试短信")
        dialog._parse_court_sms_only()
        qapp.processEvents()

        assert captured.get("parsed") is parsed
        assert dialog._court_sms_target_folder.text() == "法院送达文书"
        assert "自动读取网页文书" in dialog._court_sms_summary.toHtml()
