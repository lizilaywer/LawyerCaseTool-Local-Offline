# -*- coding: utf-8 -*-
"""版本管理模块"""

from pathlib import Path
from typing import Optional

__all__ = ['get_version']

_VERSION: Optional[str] = None


def get_version() -> str:
    """
    获取应用版本号

    从项目根目录的 VERSION 文件读取版本号，并缓存结果

    Returns:
        版本号字符串，格式为 "x.y.z"
    """
    global _VERSION

    if _VERSION is not None:
        return _VERSION

    try:
        # VERSION 文件位于项目根目录
        version_file = Path(__file__).parent.parent.parent / 'VERSION'
        _VERSION = version_file.read_text(encoding='utf-8').strip()
        return _VERSION
    except Exception:
        # 如果读取失败，返回默认版本号
        _VERSION = '2.0.0'
        return _VERSION
