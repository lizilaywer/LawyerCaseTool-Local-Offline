# -*- coding: utf-8 -*-
"""日志记录模块"""

import logging
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional


class LoggerManager:
    """日志管理器

    使用双重检查锁定模式确保线程安全的单例实现。
    """

    _instance: Optional['LoggerManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        # 双重检查锁定模式
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized_flag = False
        return cls._instance

    def __init__(self):
        # 使用实例变量 _initialized_flag 避免重复初始化
        if getattr(self, '_initialized_flag', False):
            return
        self._initialized_flag = True

        self._logger = logging.getLogger("LawyerCaseTool")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()

    def setup_file_handler(self, log_dir: Path) -> None:
        """设置文件日志处理器"""
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"lawyer_tool_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)

    def setup_console_handler(self) -> None:
        """设置控制台日志处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)

    @property
    def logger(self) -> logging.Logger:
        return self._logger


def get_logger() -> logging.Logger:
    """获取日志记录器"""
    return LoggerManager().logger


def setup_logging(log_dir: Path, console: bool = True) -> logging.Logger:
    """设置日志系统"""
    manager = LoggerManager()
    manager.setup_file_handler(log_dir)
    if console:
        manager.setup_console_handler()
    return manager.logger
