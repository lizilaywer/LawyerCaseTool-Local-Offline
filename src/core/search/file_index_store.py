# -*- coding: utf-8 -*-
"""SQLite 文件索引存储。"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Union

from src.config.path_manager import get_path_manager
from src.core.search.models import FileIndexEntry, FileSearchResult


def _default_db_path() -> Path:
    path_manager = get_path_manager()
    return path_manager.cache_dir / "search" / "file_index.sqlite3"


def _escape_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


class FileIndexStore:
    """本地文件索引 SQLite 存储。"""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = Path(db_path) if db_path else _default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @property
    def db_path(self) -> Path:
        """索引数据库路径。"""
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    case_name TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    absolute_path TEXT NOT NULL,
                    parent_relative_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    stem TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    modified_at TEXT NOT NULL,
                    exists_flag INTEGER NOT NULL DEFAULT 1,
                    indexed_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_file_entries_case_rel
                ON file_entries(case_id, relative_path)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_file_entries_search
                ON file_entries(filename, relative_path, case_name, extension)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_file_entries_case
                ON file_entries(case_id)
                """
            )

    def replace_case_entries(self, case_id: str, entries: Iterable[FileIndexEntry]) -> int:
        """替换单个案件的全部文件索引。"""
        indexed_at = datetime.now().isoformat(timespec="seconds")
        entry_list = list(entries)
        with self._connect() as conn:
            conn.execute("DELETE FROM file_entries WHERE case_id = ?", (case_id,))
            conn.executemany(
                """
                INSERT INTO file_entries (
                    case_id, case_name, root_path, relative_path, absolute_path,
                    parent_relative_path, filename, stem, extension, file_type,
                    size_bytes, modified_at, exists_flag, indexed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                [
                    (
                        entry.case_id,
                        entry.case_name,
                        entry.root_path,
                        entry.relative_path,
                        entry.absolute_path,
                        entry.parent_relative_path,
                        entry.filename,
                        entry.stem,
                        entry.extension,
                        entry.file_type,
                        entry.size_bytes,
                        entry.modified_at,
                        indexed_at,
                    )
                    for entry in entry_list
                ],
            )
        return len(entry_list)

    def remove_case_entries(self, case_id: str) -> None:
        """删除单个案件的文件索引。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM file_entries WHERE case_id = ?", (case_id,))

    def clear(self) -> None:
        """清空索引。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM file_entries")

    def count_entries(self) -> int:
        """返回索引文件数量。"""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM file_entries").fetchone()
        return int(row["total"] if row else 0)

    def search(
        self,
        query: str,
        *,
        limit: int = 50,
        case_id: str = "",
    ) -> List[FileSearchResult]:
        """按文件名、相对路径、案件名进行文件级检索。"""
        tokens = [token for token in query.strip().lower().split() if token]
        if not tokens:
            return []

        where_parts = ["exists_flag = 1"]
        params: List[Union[str, int]] = []

        if case_id:
            where_parts.append("case_id = ?")
            params.append(case_id)

        for token in tokens:
            like = f"%{_escape_like(token)}%"
            where_parts.append(
                """
                (
                    lower(filename) LIKE ? ESCAPE '\\'
                    OR lower(relative_path) LIKE ? ESCAPE '\\'
                    OR lower(case_name) LIKE ? ESCAPE '\\'
                    OR lower(extension) LIKE ? ESCAPE '\\'
                )
                """
            )
            params.extend([like, like, like, like])

        params.append(max(1, min(int(limit), 200)))
        sql = f"""
            SELECT
                case_id, case_name, relative_path, absolute_path, filename,
                extension, file_type, size_bytes, modified_at
            FROM file_entries
            WHERE {' AND '.join(where_parts)}
            ORDER BY modified_at DESC, filename COLLATE NOCASE ASC
            LIMIT ?
        """

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            FileSearchResult(
                case_id=str(row["case_id"]),
                case_name=str(row["case_name"]),
                relative_path=str(row["relative_path"]),
                absolute_path=str(row["absolute_path"]),
                filename=str(row["filename"]),
                extension=str(row["extension"]),
                file_type=str(row["file_type"]),
                size_bytes=int(row["size_bytes"]),
                modified_at=str(row["modified_at"]),
            )
            for row in rows
        ]
