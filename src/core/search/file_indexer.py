# -*- coding: utf-8 -*-
"""案件文件夹文件级索引构建器。"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.core.search.file_index_store import FileIndexStore
from src.core.search.models import FileIndexEntry, IndexSummary


SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".case",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
}

SKIP_FILE_PREFIXES = ("~$", ".~", ".DS_")
SKIP_FILE_SUFFIXES = (".tmp", ".temp", ".crdownload", ".part")

DOCUMENT_EXTENSIONS = {".doc", ".docx", ".pdf", ".txt", ".md", ".rtf", ".wps"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
SHEET_EXTENSIONS = {".xls", ".xlsx", ".csv", ".et"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz"}


def _file_type_for_extension(extension: str) -> str:
    ext = extension.lower()
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in SHEET_EXTENSIONS:
        return "spreadsheet"
    if ext in ARCHIVE_EXTENSIONS:
        return "archive"
    return "file"


def _should_skip_file(name: str) -> bool:
    lower_name = name.lower()
    return (
        name.startswith(SKIP_FILE_PREFIXES)
        or lower_name.endswith(SKIP_FILE_SUFFIXES)
    )


def _iter_files(root: Path) -> Iterable[Path]:
    """以 scandir 递归遍历文件，避免跟随符号链接。"""
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as iterator:
                entries = list(iterator)
        except OSError:
            continue

        for entry in sorted(entries, key=lambda item: item.name.lower(), reverse=True):
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in SKIP_DIR_NAMES or entry.name.startswith("."):
                        continue
                    stack.append(Path(entry.path))
                    continue
                if entry.is_file(follow_symlinks=False) and not _should_skip_file(entry.name):
                    yield Path(entry.path)
            except OSError:
                continue


class FileIndexer:
    """为案件文件夹建立文件级索引。"""

    def __init__(self, store: Optional[FileIndexStore] = None):
        self._store = store or FileIndexStore()

    def build_entries_for_case(self, case: Dict[str, Any]) -> Tuple[List[FileIndexEntry], bool]:
        """构建单个案件的文件索引记录。

        Returns:
            (entries, case_path_exists)
        """
        case_id = str(case.get("id", "")).strip()
        case_name = str(case.get("name", "")).strip() or "未命名案件"
        root = Path(str(case.get("path", "")).strip())
        if not case_id or not root.exists() or not root.is_dir():
            return [], False

        entries: List[FileIndexEntry] = []
        root_text = str(root)
        for file_path in _iter_files(root):
            try:
                stat = file_path.stat()
                relative_path = file_path.relative_to(root).as_posix()
            except OSError:
                continue

            parent_relative = file_path.parent.relative_to(root).as_posix()
            if parent_relative == ".":
                parent_relative = ""

            extension = file_path.suffix.lower()
            entries.append(
                FileIndexEntry(
                    case_id=case_id,
                    case_name=case_name,
                    root_path=root_text,
                    relative_path=relative_path,
                    absolute_path=str(file_path),
                    parent_relative_path=parent_relative,
                    filename=file_path.name,
                    stem=file_path.stem,
                    extension=extension,
                    file_type=_file_type_for_extension(extension),
                    size_bytes=int(stat.st_size),
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                )
            )

        return entries, True

    def reindex_case(self, case: Dict[str, Any]) -> IndexSummary:
        """重建单个案件文件索引。"""
        case_id = str(case.get("id", "")).strip()
        if not case_id:
            return IndexSummary(1, 0, 0, 1, ("案件缺少 id",))

        entries, exists = self.build_entries_for_case(case)
        if not exists:
            self._store.remove_case_entries(case_id)
            return IndexSummary(1, 0, 0, 1)

        count = self._store.replace_case_entries(case_id, entries)
        return IndexSummary(1, 1, count, 0)

    def reindex_cases(self, cases: Iterable[Dict[str, Any]]) -> IndexSummary:
        """重建多个案件文件索引。"""
        cases_seen = 0
        cases_indexed = 0
        files_indexed = 0
        missing_cases = 0
        errors: List[str] = []

        for case in cases:
            cases_seen += 1
            try:
                summary = self.reindex_case(case)
            except Exception as exc:
                errors.append(f"{case.get('name') or case.get('id')}: {exc}")
                continue
            cases_indexed += summary.cases_indexed
            files_indexed += summary.files_indexed
            missing_cases += summary.missing_cases
            errors.extend(summary.errors)

        return IndexSummary(
            cases_seen=cases_seen,
            cases_indexed=cases_indexed,
            files_indexed=files_indexed,
            missing_cases=missing_cases,
            errors=tuple(errors),
        )
