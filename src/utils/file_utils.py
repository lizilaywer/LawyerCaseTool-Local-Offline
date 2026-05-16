# -*- coding: utf-8 -*-
"""文件工具函数模块"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterator, List, Optional

from src.utils.logger import get_logger


logger = get_logger()


def ensure_dir(path: Path) -> Path:
    """
    确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        目录路径
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_file(src: Path, dst: Path) -> Path:
    """
    复制文件

    Args:
        src: 源文件路径
        dst: 目标文件路径

    Returns:
        目标文件路径
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def copy_dir(src: Path, dst: Path) -> Path:
    """
    复制目录

    Args:
        src: 源目录路径
        dst: 目标目录路径

    Returns:
        目标目录路径
    """
    shutil.copytree(src, dst)
    return dst


def delete_file(path: Path) -> bool:
    """
    删除文件

    Args:
        path: 文件路径

    Returns:
        是否成功
    """
    try:
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False
    except Exception as exc:
        logger.warning(f"删除文件失败: {path} ({exc})")
        return False


def delete_dir(path: Path) -> bool:
    """
    删除目录

    Args:
        path: 目录路径

    Returns:
        是否成功
    """
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            return True
        return False
    except Exception as exc:
        logger.warning(f"删除目录失败: {path} ({exc})")
        return False


def list_files(
    directory: Path,
    pattern: str = "*",
    recursive: bool = False,
    limit: Optional[int] = None
) -> Iterator[Path]:
    """
    列出目录中的文件

    Args:
        directory: 目录路径
        pattern: 文件模式
        recursive: 是否递归
        limit: 最大返回数量，None 表示不限

    Returns:
        文件路径迭代器
    """
    count = 0
    if recursive:
        for path in directory.rglob(pattern):
            yield path
            count += 1
            if limit and count >= limit:
                return
    else:
        for path in directory.glob(pattern):
            yield path
            count += 1
            if limit and count >= limit:
                return


def get_file_size(path: Path) -> int:
    """
    获取文件大小（字节）

    Args:
        path: 文件路径

    Returns:
        文件大小
    """
    if path.exists() and path.is_file():
        return path.stat().st_size
    return 0


def get_unique_path(path: Path) -> Path:
    """
    获取唯一路径（避免重名）

    Args:
        path: 原始路径

    Returns:
        唯一路径
    """
    if not path.exists():
        return path

    counter = 1
    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def read_text_file(path: Path, encoding: str = 'utf-8') -> Optional[str]:
    """
    读取文本文件

    Args:
        path: 文件路径
        encoding: 编码

    Returns:
        文件内容，失败返回 None
    """
    try:
        return path.read_text(encoding=encoding)
    except Exception as exc:
        logger.warning(f"读取文本文件失败: {path} ({exc})")
        return None


def write_text_file(
    path: Path,
    content: str,
    encoding: str = 'utf-8'
) -> bool:
    """
    原子写入文本文件（临时文件 + 替换）

    Args:
        path: 文件路径
        content: 内容
        encoding: 编码

    Returns:
        是否成功
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            suffix='.tmp', prefix='.txt_', dir=path.parent
        )
        try:
            with os.fdopen(fd, 'w', encoding=encoding) as f:
                f.write(content)
            os.replace(temp_path, path)
            return True
        except BaseException:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except Exception as exc:
        logger.warning(f"写入文本文件失败: {path} ({exc})")
        return False


def read_json_file(path: Path) -> Optional[dict]:
    """
    读取 JSON 文件

    Args:
        path: 文件路径

    Returns:
        JSON 数据，失败返回 None
    """
    import json
    try:
        content = path.read_text(encoding='utf-8')
        return json.loads(content)
    except Exception as exc:
        logger.warning(f"读取JSON失败: {path} ({exc})")
        return None


def write_json_file(
    path: Path,
    data: dict,
    indent: int = 2,
    ensure_ascii: bool = False
) -> bool:
    """
    原子写入 JSON 文件（临时文件 + 替换）

    Args:
        path: 文件路径
        data: 数据
        indent: 缩进
        ensure_ascii: 是否确保 ASCII

    Returns:
        是否成功
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)

        fd, temp_path = tempfile.mkstemp(
            suffix='.tmp', prefix='.json_', dir=path.parent
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(temp_path, path)
            return True
        except BaseException:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except Exception as exc:
        logger.warning(f"写入JSON失败: {path} ({exc})")
        return False
