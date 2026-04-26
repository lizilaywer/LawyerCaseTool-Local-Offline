# -*- coding: utf-8 -*-
"""文件搜索门面服务。"""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.core.search.file_index_store import FileIndexStore
from src.core.search.file_indexer import FileIndexer
from src.core.search.models import FileSearchResult, IndexSummary


class FileSearchService:
    """文件级索引与搜索统一入口。"""

    def __init__(self, db_path: Optional[Path] = None):
        self._store = FileIndexStore(db_path)
        self._indexer = FileIndexer(self._store)

    @property
    def db_path(self) -> Path:
        """索引数据库路径。"""
        return self._store.db_path

    def count_entries(self) -> int:
        """返回当前索引文件数。"""
        return self._store.count_entries()

    def reindex_case(self, case: Dict[str, Any]) -> IndexSummary:
        """重建单个案件索引。"""
        return self._indexer.reindex_case(case)

    def reindex_cases(self, cases: Iterable[Dict[str, Any]]) -> IndexSummary:
        """重建多个案件索引。"""
        return self._indexer.reindex_cases(cases)

    def clear(self) -> None:
        """清空索引。"""
        self._store.clear()

    def search(self, query: str, *, limit: int = 50, case_id: str = "") -> List[FileSearchResult]:
        """搜索文件。"""
        return self._store.search(query, limit=limit, case_id=case_id)
