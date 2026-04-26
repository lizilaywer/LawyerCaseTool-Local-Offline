# -*- coding: utf-8 -*-
"""file_utils 模块单元测试"""

import json
from pathlib import Path

import pytest

from src.utils.file_utils import (
    ensure_dir,
    copy_file,
    delete_file,
    delete_dir,
    list_files,
    get_file_size,
    get_unique_path,
    read_text_file,
    write_text_file,
    read_json_file,
    write_json_file,
)


class TestEnsureDir:
    """确保目录存在测试"""

    def test_creates_dir(self, temp_dir):
        target = temp_dir / "new_dir"
        result = ensure_dir(target)
        assert target.is_dir()
        assert result == target

    def test_existing_dir_ok(self, temp_dir):
        result = ensure_dir(temp_dir)
        assert result == temp_dir

    def test_nested_dirs(self, temp_dir):
        target = temp_dir / "a" / "b" / "c"
        ensure_dir(target)
        assert target.is_dir()


class TestReadWriteText:
    """文本文件读写测试"""

    def test_write_and_read(self, temp_dir):
        f = temp_dir / "test.txt"
        assert write_text_file(f, "hello world") is True
        assert read_text_file(f) == "hello world"

    def test_write_chinese(self, temp_dir):
        f = temp_dir / "中文.txt"
        assert write_text_file(f, "你好世界") is True
        assert read_text_file(f) == "你好世界"

    def test_write_creates_parent(self, temp_dir):
        f = temp_dir / "sub" / "dir" / "file.txt"
        assert write_text_file(f, "deep") is True
        assert read_text_file(f) == "deep"

    def test_read_nonexistent(self, temp_dir):
        assert read_text_file(temp_dir / "nope.txt") is None

    def test_write_empty_content(self, temp_dir):
        f = temp_dir / "empty.txt"
        assert write_text_file(f, "") is True
        assert read_text_file(f) == ""


class TestReadWriteJson:
    """JSON 文件读写测试"""

    def test_write_and_read(self, temp_dir):
        f = temp_dir / "data.json"
        data = {"name": "测试", "count": 42}
        assert write_json_file(f, data) is True
        result = read_json_file(f)
        assert result == data

    def test_preserves_unicode(self, temp_dir):
        f = temp_dir / "unicode.json"
        data = {"中文键": "中文值"}
        assert write_json_file(f, data) is True
        assert read_json_file(f) == data

    def test_read_nonexistent(self, temp_dir):
        assert read_json_file(temp_dir / "nope.json") is None

    def test_read_corrupt_json(self, temp_dir):
        f = temp_dir / "bad.json"
        f.write_text("{invalid json", encoding="utf-8")
        assert read_json_file(f) is None


class TestCopyDelete:
    """文件复制与删除测试"""

    def test_copy_file(self, temp_dir):
        src = temp_dir / "src.txt"
        dst = temp_dir / "dst.txt"
        src.write_text("content", encoding="utf-8")
        result = copy_file(src, dst)
        assert dst.read_text(encoding="utf-8") == "content"
        assert result == dst

    def test_delete_file(self, temp_dir):
        f = temp_dir / "del.txt"
        f.write_text("bye", encoding="utf-8")
        assert delete_file(f) is True
        assert not f.exists()

    def test_delete_nonexistent_file(self, temp_dir):
        assert delete_file(temp_dir / "nope.txt") is False

    def test_delete_dir(self, temp_dir):
        d = temp_dir / "subdir"
        d.mkdir()
        (d / "file.txt").write_text("x", encoding="utf-8")
        assert delete_dir(d) is True
        assert not d.exists()

    def test_delete_nonexistent_dir(self, temp_dir):
        assert delete_dir(temp_dir / "nope") is False


class TestListFiles:
    """文件列表测试"""

    def test_list_txt(self, temp_dir):
        (temp_dir / "a.txt").write_text("a", encoding="utf-8")
        (temp_dir / "b.txt").write_text("b", encoding="utf-8")
        (temp_dir / "c.py").write_text("c", encoding="utf-8")
        files = list_files(temp_dir, "*.txt")
        assert len(files) == 2

    def test_list_recursive(self, temp_dir):
        sub = temp_dir / "sub"
        sub.mkdir()
        (sub / "deep.txt").write_text("d", encoding="utf-8")
        files = list_files(temp_dir, "*.txt", recursive=True)
        assert len(files) == 1


class TestGetFileSize:
    """文件大小测试"""

    def test_existing_file(self, temp_dir):
        f = temp_dir / "size.txt"
        f.write_text("12345", encoding="utf-8")
        assert get_file_size(f) == 5

    def test_nonexistent_file(self, temp_dir):
        assert get_file_size(temp_dir / "nope") == 0


class TestGetUniquePath:
    """唯一路径测试"""

    def test_nonexistent(self, temp_dir):
        p = temp_dir / "new.txt"
        assert get_unique_path(p) == p

    def test_exists_increments(self, temp_dir):
        p = temp_dir / "file.txt"
        p.write_text("1", encoding="utf-8")
        result = get_unique_path(p)
        assert result.name == "file_1.txt"
