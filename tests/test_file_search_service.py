# -*- coding: utf-8 -*-
"""文件级索引与搜索测试。"""

from pathlib import Path

from src.core.search import FileSearchService


def test_file_index_searches_filename_and_relative_path(tmp_path: Path):
    case_root = tmp_path / "案件A"
    (case_root / "证据").mkdir(parents=True)
    (case_root / "证据" / "聊天记录.pdf").write_text("pdf", encoding="utf-8")
    (case_root / "代理词.docx").write_text("docx", encoding="utf-8")
    (case_root / ".case").mkdir()
    (case_root / ".case" / "metadata.json").write_text("{}", encoding="utf-8")
    (case_root / "~$临时.docx").write_text("tmp", encoding="utf-8")

    service = FileSearchService(tmp_path / "index.sqlite3")
    summary = service.reindex_cases([
        {"id": "case_1", "name": "案件A", "path": str(case_root)}
    ])

    assert summary.cases_indexed == 1
    assert summary.files_indexed == 2

    by_name = service.search("聊天", limit=10)
    assert [item.filename for item in by_name] == ["聊天记录.pdf"]

    by_folder = service.search("证据", limit=10)
    assert [item.relative_path for item in by_folder] == ["证据/聊天记录.pdf"]


def test_file_index_removes_missing_case_entries(tmp_path: Path):
    case_root = tmp_path / "案件B"
    case_root.mkdir()
    (case_root / "起诉状.docx").write_text("docx", encoding="utf-8")

    service = FileSearchService(tmp_path / "index.sqlite3")
    service.reindex_case({"id": "case_2", "name": "案件B", "path": str(case_root)})
    assert service.count_entries() == 1

    missing_root = tmp_path / "missing"
    summary = service.reindex_case({"id": "case_2", "name": "案件B", "path": str(missing_root)})

    assert summary.missing_cases == 1
    assert service.count_entries() == 0
