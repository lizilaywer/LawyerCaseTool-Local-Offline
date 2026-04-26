# -*- coding: utf-8 -*-
"""文件级索引数据模型。"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class FileIndexEntry:
    """单个文件的索引记录。"""

    case_id: str
    case_name: str
    root_path: str
    relative_path: str
    absolute_path: str
    parent_relative_path: str
    filename: str
    stem: str
    extension: str
    file_type: str
    size_bytes: int
    modified_at: str


@dataclass(frozen=True)
class FileSearchResult:
    """文件搜索结果。"""

    case_id: str
    case_name: str
    relative_path: str
    absolute_path: str
    filename: str
    extension: str
    file_type: str
    size_bytes: int
    modified_at: str


@dataclass(frozen=True)
class IndexSummary:
    """索引刷新摘要。"""

    cases_seen: int
    cases_indexed: int
    files_indexed: int
    missing_cases: int
    errors: Tuple[str, ...] = ()
