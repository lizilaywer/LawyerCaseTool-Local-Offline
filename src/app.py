# -*- coding: utf-8 -*-
"""QApplication 配置模块"""

import sys
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.config.path_manager import get_path_manager
from src.gui.styles import build_app_stylesheet
from src.utils.logger import setup_logging
from src.utils.platform_utils import get_default_ui_font_family, is_windows
from src.utils.version import get_version
from src.utils.windows_runtime import (
    apply_windows_qt_tuning,
    configure_windows_process,
)


class Application:
    """应用程序类"""

    _instance: Optional['Application'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定模式
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        with self.__class__._lock:
            if self._initialized:
                return
            self._initialized = True

        self._path_manager = get_path_manager()
        self._qt_app: Optional[QApplication] = None

    def initialize(self, argv: list = None) -> QApplication:
        """
        初始化应用程序

        Args:
            argv: 命令行参数

        Returns:
            QApplication 实例
        """
        if argv is None:
            argv = sys.argv

        # 确保目录存在
        self._path_manager.ensure_directories()

        # 设置日志
        setup_logging(self._path_manager.logs_dir, console=not is_windows())

        # Windows 进程级优化必须在 QApplication 创建前执行
        configure_windows_process()

        # 创建 QApplication
        self._qt_app = QApplication(argv)
        self._qt_app.setApplicationName("案件文件夹管理系统 LEXORA")
        self._qt_app.setApplicationDisplayName("案件文件夹管理系统 LEXORA")
        self._qt_app.setApplicationVersion(get_version())
        self._qt_app.setOrganizationName("CaseFolderManager")

        # 设置默认字体
        font = QFont(get_default_ui_font_family(), 9)
        self._qt_app.setFont(font)

        # 设置样式
        self._qt_app.setStyle("Fusion")
        self._qt_app.setStyleSheet(build_app_stylesheet())
        apply_windows_qt_tuning(self._qt_app)

        return self._qt_app

    def get_qt_app(self) -> Optional[QApplication]:
        """获取 QApplication 实例"""
        return self._qt_app

    def run(self) -> int:
        """运行应用程序"""
        if self._qt_app is None:
            raise RuntimeError("Application not initialized")

        return self._qt_app.exec()


def get_application() -> Application:
    """获取应用程序实例"""
    return Application()
