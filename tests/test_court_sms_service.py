# -*- coding: utf-8 -*-
"""法院短信服务测试。"""

from __future__ import annotations

import json
from pathlib import Path

from src.core.court_sms_service import CourtSmsDocument, CourtSmsService


class _FakeResponse:
    def __init__(self, data: bytes, status_code: int = 200):
        self._data = data
        self.status_code = status_code

    def read(self) -> bytes:
        return self._data

    def json(self):
        import json
        return json.loads(self._data)

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=8192):
        yield self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestCourtSmsService:
    """法院短信服务测试。"""

    def setup_method(self):
        self.service = CourtSmsService()

    def test_parse_sms_extracts_link_and_case_fields(self):
        sms = (
            "【石台县人民法院】曹忠发，石台县人民法院向您发送了（2026）皖1722民初273号案件相关文书，"
            "请及时签收。点击链接查阅："
            "https://zxfw.court.gov.cn/zxfw/#/pagesAjkj/app/wssd/index?"
            "qdbh=4554ad9528bf4101b8969691a1ab0145&sdbh=36151b97e5be4e7daff4c338ebf78573&"
            "sdsin=dbd022c9ab28544ab1f1e454da63d25d"
        )

        result = self.service.parse_sms(sms)

        assert result.court_name == "石台县人民法院"
        assert result.recipient_name == "曹忠发"
        assert result.case_number == "（2026）皖1722民初273号"
        assert result.qdbh == "4554ad9528bf4101b8969691a1ab0145"
        assert result.sdbh == "36151b97e5be4e7daff4c338ebf78573"
        assert result.sdsin == "dbd022c9ab28544ab1f1e454da63d25d"

    def test_fetch_documents_posts_json_and_parses_response(self, monkeypatch):
        sms = (
            "【石台县人民法院】曹忠发，石台县人民法院向您发送了（2026）皖1722民初273号案件相关文书。"
            "https://zxfw.court.gov.cn/zxfw/#/pagesAjkj/app/wssd/index?"
            "qdbh=q1&sdbh=s1&sdsin=sin1"
        )
        parsed = self.service.parse_sms(sms)
        captured = {}

        payload = {
            "code": 200,
            "msg": "成功！",
            "data": [
                {
                    "c_wsmc": "受理通知书（曹忠发）",
                    "c_wjgs": "pdf",
                    "c_wsbh": "doc1",
                    "c_fymc": "石台县人民法院",
                    "wjlj": "https://example.com/doc1.pdf",
                }
            ],
        }

        def fake_post(url, **kwargs):
            captured["url"] = url
            captured["json"] = kwargs.get("json")
            captured["headers"] = kwargs.get("headers", {})
            return _FakeResponse(json.dumps(payload).encode("utf-8"))

        monkeypatch.setattr(self.service._session, "post", fake_post)

        documents = self.service.fetch_documents(parsed)

        assert captured["url"].endswith("/api/v1/sdfw/getWsListBySdbhNew")
        assert captured["json"] == {
            "sdbh": "s1",
            "qdbh": "q1",
            "sdsin": "sin1",
            "mm": "",
        }
        assert "application/json" in str(captured["headers"].get("Content-Type", ""))
        assert len(documents) == 1
        assert documents[0].name == "受理通知书（曹忠发）.pdf"

    def test_fetch_documents_sanitizes_remote_filename(self, monkeypatch):
        """法院接口返回的文件名不能携带路径或危险扩展名。"""
        parsed = self.service.parse_sms(
            "【石台县人民法院】曹忠发，石台县人民法院向您发送了案件文书。"
            "https://zxfw.court.gov.cn/zxfw/#/pagesAjkj/app/wssd/index?qdbh=q1&sdbh=s1&sdsin=sin1"
        )
        payload = {
            "code": 200,
            "data": [
                {
                    "c_wsmc": "../危险/文书",
                    "c_wjgs": "../../exe",
                    "c_wsbh": "doc1",
                    "wjlj": "https://example.com/doc1",
                }
            ],
        }

        def fake_post(url, **kwargs):
            return _FakeResponse(json.dumps(payload).encode("utf-8"))

        monkeypatch.setattr(self.service._session, "post", fake_post)

        documents = self.service.fetch_documents(parsed)

        assert documents[0].name == "文书.pdf"
        assert documents[0].extname == "pdf"

    def test_match_cases_prefers_case_number_then_party_and_court(self):
        sms = (
            "【石台县人民法院】曹忠发，石台县人民法院向您发送了（2026）皖1722民初273号案件相关文书。"
            "https://zxfw.court.gov.cn/zxfw/#/pagesAjkj/app/wssd/index?"
            "qdbh=q1&sdbh=s1&sdsin=sin1"
        )
        parsed = self.service.parse_sms(sms)

        matches = self.service.match_cases(
            parsed,
            [
                {
                    "id": "case_a",
                    "name": "石台法院民事案件",
                    "path": "/tmp/case_a",
                    "info_fields": [
                        {"key": "case_number", "value": "（2026）皖1722民初273号"},
                        {"key": "party_name", "value": "曹忠发"},
                        {"key": "forum", "value": "石台县人民法院"},
                    ],
                    "variables": {},
                },
                {
                    "id": "case_b",
                    "name": "其他案件",
                    "path": "/tmp/case_b",
                    "info_fields": [
                        {"key": "case_number", "value": "（2026）皖0000民初1号"},
                        {"key": "party_name", "value": "李四"},
                    ],
                    "variables": {},
                },
            ],
        )

        assert matches
        assert matches[0].case_id == "case_a"
        assert "案号完全匹配" in matches[0].reasons

    def test_save_documents_to_case_copies_files_into_relative_folder(self, tmp_path):
        case_dir = tmp_path / "案件目录"
        case_dir.mkdir()
        temp_file = tmp_path / "受理通知书.pdf"
        temp_file.write_bytes(b"pdf-bytes")

        saved = self.service.save_documents_to_case(
            {"path": str(case_dir)},
            [
                CourtSmsDocument(
                    name="受理通知书.pdf",
                    extname="pdf",
                    download_url="",
                    local_path=str(temp_file),
                )
            ],
            "法院送达文书/（2026）皖1722民初273号",
        )

        assert len(saved) == 1
        assert saved[0].exists()
        assert saved[0].read_bytes() == b"pdf-bytes"
        assert "法院送达文书" in str(saved[0].parent)

    def test_save_documents_to_directory_supports_custom_folder(self, tmp_path):
        custom_dir = tmp_path / "自定义保存"
        source = tmp_path / "举证通知书.pdf"
        source.write_bytes(b"custom-bytes")

        saved = self.service.save_documents_to_directory(
            custom_dir,
            [
                CourtSmsDocument(
                    name="举证通知书.pdf",
                    extname="pdf",
                    download_url="",
                    local_path=str(source),
                )
            ],
            "法院送达文书/石台法院",
        )

        assert len(saved) == 1
        assert saved[0].exists()
        assert saved[0].read_bytes() == b"custom-bytes"
        assert saved[0].parent == custom_dir / "法院送达文书" / "石台法院"

    def test_save_documents_to_directory_rejects_path_traversal(self, tmp_path):
        """保存子目录不能跳出用户选择的目标目录。"""
        custom_dir = tmp_path / "自定义保存"
        source = tmp_path / "举证通知书.pdf"
        source.write_bytes(b"custom-bytes")

        try:
            self.service.save_documents_to_directory(
                custom_dir,
                [
                    CourtSmsDocument(
                        name="举证通知书.pdf",
                        extname="pdf",
                        download_url="",
                        local_path=str(source),
                    )
                ],
                "../外部目录",
            )
        except ValueError as exc:
            assert "保存子目录" in str(exc)
        else:
            raise AssertionError("路径穿越应被拒绝")

    def test_download_documents_keeps_remote_name_inside_session_dir(self, tmp_path, monkeypatch):
        """下载落盘前再次清洗文件名，确保不会写出暂存目录。"""
        parsed = self.service.parse_sms(
            "【石台县人民法院】曹忠发，石台县人民法院向您发送了案件文书。"
            "https://zxfw.court.gov.cn/zxfw/#/pagesAjkj/app/wssd/index?qdbh=q1&sdbh=s1&sdsin=sin1"
        )
        monkeypatch.setattr(self.service._path_manager, "_app_data_dir", tmp_path)
        captured = {}

        def fake_get(url, **kwargs):
            return _FakeResponse(b"pdf-bytes")

        monkeypatch.setattr(self.service._session, "get", fake_get)

        document = CourtSmsDocument(
            name="../危险/文书.pdf",
            extname="pdf",
            download_url="https://example.com/doc1.pdf",
        )
        session_dir = self.service.download_documents([document], parsed)

        saved_path = Path(document.local_path)
        captured["relative"] = saved_path.relative_to(session_dir)
        assert captured["relative"] == Path("文书.pdf")
        assert saved_path.read_bytes() == b"pdf-bytes"

    def test_parse_hearing_notice_text_extracts_hearing_fields_from_summons(self):
        text = (
            "池 州 市 贵 池 区 人 民 法 院\n"
            "传 票\n"
            "案 号：（2026）皖 1702 民初 3435 号\n"
            "案 由：离婚纠纷\n"
            "被传事由 开庭审理\n"
            "应到时间 2026 年 04 月13 日 09:30\n"
            "应到处所 杏花村第三法庭\n"
            "签发人 方圆圆 送达人 高伟松 金玮玮\n"
            "联系人 孙慧敏\n"
            "二〇二六年三月十六日"
        )

        notice = self.service.parse_hearing_notice_text(
            CourtSmsDocument(
                name="传票（章云云）.pdf",
                extname="pdf",
                download_url="",
                local_path="/tmp/传票（章云云）.pdf",
                court_name="池州市贵池区人民法院",
            ),
            text,
            fallback_case_number="（2026）皖1702民初3435号",
            fallback_court_name="池州市贵池区人民法院",
        )

        assert notice is not None
        assert notice.notice_type == "传票"
        assert notice.case_number == "（2026）皖1702民初3435号"
        assert notice.cause == "离婚纠纷"
        assert notice.hearing_date == "2026-04-13"
        assert notice.hearing_time == "09:30"
        assert notice.hearing_place == "杏花村第三法庭"
        assert notice.signer == "方圆圆"
        assert notice.contact_person == "孙慧敏"

    def test_build_deadline_from_hearing_notice_marks_hearing_priority_and_reminders(self):
        notice = self.service.parse_hearing_notice_text(
            CourtSmsDocument(
                name="传票（章云云）.pdf",
                extname="pdf",
                download_url="",
                local_path="/tmp/传票（章云云）.pdf",
                court_name="池州市贵池区人民法院",
            ),
            (
                "池州市贵池区人民法院传票案号：（2026）皖1702民初3435号案由：离婚纠纷"
                "应到时间2026年04月13日09:30应到处所杏花村第三法庭签发人方圆圆联系人孙慧敏"
            ),
            fallback_case_number="（2026）皖1702民初3435号",
            fallback_court_name="池州市贵池区人民法院",
        )

        assert notice is not None
        deadline = self.service.build_deadline_from_hearing_notice(notice)

        assert deadline["type"] == "hearing"
        assert deadline["priority"] == "high"
        assert deadline["date"] == "2026-04-13"
        assert deadline["time"] == "09:30"
        assert deadline["all_day"] is False
        assert deadline["remind_before"] == [7, 3, 1, 0]
        assert "杏花村第三法庭" in deadline["description"]
