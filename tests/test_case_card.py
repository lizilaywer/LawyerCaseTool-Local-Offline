# -*- coding: utf-8 -*-
"""案件卡片显示逻辑测试"""

from datetime import datetime, timedelta

from src.gui.widgets.case_card import CaseCard


class TestCaseCard:
    """案件卡片测试。"""

    def test_completed_deadline_hint_is_not_displayed(self, qapp):
        card = CaseCard({
            "id": "case_done",
            "name": "已完成期限案件",
            "status": "active",
            "tags": ["仲裁", "保全"],
            "deadlines": [
                {
                    "title": "斗争斗斗",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": "completed",
                }
            ],
        })
        card.resize(280, 96)
        card.show()
        qapp.processEvents()

        assert card._deadline_label is not None
        assert card._deadline_label.text() == ""
        assert card._deadline_label.isVisible() is False

    def test_compact_card_prefers_tags_over_non_urgent_deadline(self, qapp):
        future_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        card = CaseCard({
            "id": "case_future",
            "name": "普通期限案件",
            "status": "active",
            "tags": ["立案", "开庭", "执行"],
            "deadlines": [
                {
                    "title": "普通期限",
                    "date": future_date,
                    "status": "pending",
                }
            ],
        })
        card.resize(220, 96)
        card.show()
        qapp.processEvents()

        assert card._deadline_label is not None
        assert card._deadline_label.isVisible() is False
        assert any(chip.isVisible() for chip in card._tag_chips)
