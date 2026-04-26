# -*- coding: utf-8 -*-
"""路径管理器模块"""

import threading
from pathlib import Path
from typing import Optional

from src.utils.platform_utils import get_app_data_dir


class PathManager:
    """路径管理器

    使用双重检查锁定模式确保线程安全的单例实现。
    """

    _instance: Optional['PathManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        # 双重检查锁定模式
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 应用数据目录
        self._app_data_dir = self._get_app_data_dir()
        # 应用程序目录
        self._app_dir = Path(__file__).parent.parent.parent
        # 资源目录
        self._resources_dir = self._app_dir / "resources"
        # 模板目录
        self._templates_dir = self._app_dir / "templates"

    def _get_app_data_dir(self) -> Path:
        """获取应用数据目录"""
        # 兼容既有用户配置与索引数据，运行时目录暂保留旧标识。
        return get_app_data_dir("LawyerCaseTool")

    @property
    def app_data_dir(self) -> Path:
        """应用数据目录"""
        return self._app_data_dir

    @property
    def config_dir(self) -> Path:
        """配置目录"""
        return self._app_data_dir / "config"

    @property
    def logs_dir(self) -> Path:
        """日志目录"""
        return self._app_data_dir / "logs"

    @property
    def cache_dir(self) -> Path:
        """缓存目录"""
        return self._app_data_dir / "cache"

    @property
    def app_dir(self) -> Path:
        """应用程序目录"""
        return self._app_dir

    @property
    def resources_dir(self) -> Path:
        """资源目录"""
        return self._resources_dir

    @property
    def templates_dir(self) -> Path:
        """模板目录"""
        return self._templates_dir

    @property
    def icons_dir(self) -> Path:
        """图标目录"""
        return self._resources_dir / "icons"

    @property
    def config_file(self) -> Path:
        """配置文件路径"""
        return self.config_dir / "config.json"

    @property
    def templates_config_file(self) -> Path:
        """模板配置文件路径"""
        return self.config_dir / "templates.json"

    @property
    def cases_file(self) -> Path:
        """案件索引文件路径"""
        return self.config_dir / "cases.json"

    def get_template_path(self, category: str, filename: str = "template.docx") -> Path:
        """
        获取模板文件路径

        Args:
            category: 模板类别
            filename: 文件名

        Returns:
            模板文件路径
        """
        return self._templates_dir / category / filename

    def ensure_directories(self) -> None:
        """确保所有必要目录存在"""
        self._app_data_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


def get_path_manager() -> PathManager:
    """获取路径管理器实例"""
    return PathManager()
