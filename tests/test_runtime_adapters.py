# -*- coding: utf-8 -*-
"""运行时适配器测试"""

from datetime import datetime

from src.utils.runtime_adapters import FixedTimeProvider, LocalFileSystem


def test_fixed_time_provider_returns_stable_today():
    """固定时间提供器应返回稳定日期。"""
    provider = FixedTimeProvider(datetime(2026, 4, 24, 10, 30))

    assert provider.now() == datetime(2026, 4, 24, 10, 30)
    assert provider.today().isoformat() == "2026-04-24"


def test_local_file_system_walk(tmp_path):
    """文件系统适配器应能遍历目录。"""
    folder = tmp_path / "案件"
    folder.mkdir()
    (folder / "材料.txt").write_text("demo", encoding="utf-8")

    fs = LocalFileSystem()

    assert fs.exists(folder)
    assert fs.is_dir(folder)
    assert any("材料.txt" in files for _, _, files in fs.walk(folder))
