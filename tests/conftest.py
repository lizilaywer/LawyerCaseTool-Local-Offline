# -*- coding: utf-8 -*-
"""测试共享 fixtures"""

import shutil
import tempfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """提供全局唯一的 QApplication 实例。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_dir():
    """为每个测试提供独立临时目录，测试结束后自动清理。"""
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(autouse=False)
def reset_case_manager():
    """在每个测试前后重置 CaseManager 单例。

    用法：在测试类或测试函数的参数列表中声明此 fixture。
    """
    from src.core.case_manager import CaseManager
    CaseManager._instance = None
    yield
    CaseManager._instance = None
