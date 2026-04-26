# -*- coding: utf-8 -*-
"""运行时适配器。

为日期、平台和文件系统访问提供可注入入口，减少测试对真实环境的依赖。
"""

from __future__ import annotations

import os
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Iterator, Protocol

from src.utils import platform_utils


class TimeProvider:
    """时间提供器。"""

    def now(self) -> datetime:
        """返回当前日期时间。"""
        return datetime.now()

    def today(self) -> date:
        """返回当前日期。"""
        return self.now().date()


class FixedTimeProvider(TimeProvider):
    """固定时间提供器，供测试使用。"""

    def __init__(self, fixed_now: datetime):
        self._fixed_now = fixed_now

    def now(self) -> datetime:
        return self._fixed_now


class PlatformAdapter:
    """平台路径适配器。"""

    def app_data_dir(self, app_name: str = "LawyerCaseTool") -> Path:
        return platform_utils.get_app_data_dir(app_name)

    def desktop_dir(self) -> Path:
        return platform_utils.get_desktop_dir()

    def documents_dir(self) -> Path:
        return platform_utils.get_documents_dir()

    def default_output_dir(self, folder_name: str = "案卷") -> Path:
        return platform_utils.get_default_output_dir(folder_name)

    def is_windows(self) -> bool:
        return platform_utils.is_windows()


class FileSystemProtocol(Protocol):
    """文件系统访问协议。"""

    def exists(self, path: Path) -> bool:
        ...

    def is_dir(self, path: Path) -> bool:
        ...

    def iterdir(self, path: Path) -> Iterable[Path]:
        ...

    def walk(self, path: Path) -> Iterator[tuple[str, list[str], list[str]]]:
        ...


class LocalFileSystem:
    """真实本地文件系统适配器。"""

    def exists(self, path: Path) -> bool:
        return Path(path).exists()

    def is_dir(self, path: Path) -> bool:
        return Path(path).is_dir()

    def iterdir(self, path: Path) -> Iterable[Path]:
        return Path(path).iterdir()

    def walk(self, path: Path) -> Iterator[tuple[str, list[str], list[str]]]:
        return os.walk(path)

    def move(self, source: Path, target: Path) -> Path:
        return Path(shutil.move(str(source), str(target)))

    def rmtree(self, path: Path) -> None:
        shutil.rmtree(path)


__all__ = [
    "FileSystemProtocol",
    "FixedTimeProvider",
    "LocalFileSystem",
    "PlatformAdapter",
    "TimeProvider",
]
