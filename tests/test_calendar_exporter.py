# -*- coding: utf-8 -*-
"""期限导出服务测试。"""

from pathlib import Path

import pytest

from src.core.calendar_exporter import CalendarExportService


def _sample_deadlines():
    return [
        {
            "title": "开庭安排",
            "date": "2026-04-22",
            "time": "09:30",
            "all_day": False,
            "type": "hearing",
            "priority": "high",
            "status": "pending",
            "case_name": "张三买卖合同纠纷",
            "case_tags": ["合同", "民事"],
            "description": "携带证据原件并提前 20 分钟到庭。",
        },
        {
            "title": "提交补充材料",
            "date": "2026-04-24",
            "all_day": True,
            "type": "deadline",
            "priority": "medium",
            "status": "pending",
            "case_name": "李四劳动争议",
            "case_tags": ["劳动"],
            "description": "补交工资流水和仲裁申请副本。",
        },
    ]


def test_calendar_export_service_writes_html(temp_dir):
    service = CalendarExportService()
    output_path = temp_dir / "calendar_export.html"

    service.export(
        _sample_deadlines(),
        output_path,
        export_format="html",
        theme="stream",
        title="期限事项导出",
        period_label="2026年 4月",
        summary_label="全部事项 · 2项",
        filter_notes=["风险：未来全部", "仅开庭"],
    )

    content = output_path.read_text(encoding="utf-8")
    assert "期限事项导出" in content
    assert "开庭安排" in content
    assert "风险：未来全部" in content
    assert "brand-mark" in content
    assert "data:image/png;base64," in content


@pytest.mark.parametrize(
    ("theme", "marker"),
    [
        ("stream", "stream-list"),
        ("calendar", "calendar-grid"),
        ("compact", "compact-table"),
        ("timeline", "timeline-row"),
        ("board", "board-column"),
        ("briefing", "briefing-card"),
        ("agenda", "agenda-group"),
    ],
)
def test_calendar_export_service_renders_theme_specific_layout(theme, marker):
    service = CalendarExportService()
    html = service.render_html(
        service._build_payload(  # type: ignore[attr-defined]
            deadlines=_sample_deadlines(),
            title="期限事项导出",
            period_label="2026年 4月",
            summary_label="全部事项 · 2项",
            filter_notes=["全部案件"],
        ),
        theme=theme,
    )

    assert marker in html


def test_calendar_export_service_print_html_uses_small_logo_and_theme_layout():
    service = CalendarExportService()
    html = service.render_print_html(
        service._build_payload(  # type: ignore[attr-defined]
            deadlines=_sample_deadlines(),
            title="期限事项导出",
            period_label="2026年 4月",
            summary_label="全部事项 · 2项",
            filter_notes=["全部案件"],
        ),
        theme="board",
    )

    assert 'width="92"' in html
    assert "待处理（" in html


@pytest.mark.parametrize(
    ("export_format", "theme", "suffix"),
    [
        ("pdf", "calendar", ".pdf"),
        ("docx", "compact", ".docx"),
        ("png", "stream", ".png"),
    ],
)
def test_calendar_export_service_writes_supported_binary_formats(qapp, temp_dir, export_format, theme, suffix):
    service = CalendarExportService()
    output_path = temp_dir / f"calendar_export{suffix}"

    service.export(
        _sample_deadlines(),
        output_path,
        export_format=export_format,
        theme=theme,
        title="期限事项导出",
        period_label="2026年 4月",
        summary_label="全部事项 · 2项",
        filter_notes=["全部案件"],
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
