# -*- coding: utf-8 -*-
"""模板路径管理器模块"""

import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from src.config.path_manager import get_path_manager
from src.utils.logger import get_logger


class TemplatePathManager:
    """模板路径管理器"""

    # 缓存有效期（秒）
    CACHE_TTL: int = 30

    def __init__(self):
        self._logger = get_logger()
        self._user_template_dir: Optional[Path] = None
        self._system_template_dir: Optional[Path] = None
        # 模板缓存: {category: (templates_list, timestamp)}
        self._templates_cache: Dict[str, tuple] = {}
        self._cache_lock: threading.Lock = threading.Lock()

    def get_user_template_dir(self) -> Path:
        """
        获取用户自定义模板目录

        Returns:
            用户模板目录路径
        """
        if self._user_template_dir is None:
            path_manager = get_path_manager()
            self._user_template_dir = path_manager.app_data_dir / "templates"
            self._user_template_dir.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"用户模板目录: {self._user_template_dir}")

        return self._user_template_dir

    def get_system_template_dir(self) -> Path:
        """
        获取系统模板目录

        Returns:
            系统模板目录路径
        """
        if self._system_template_dir is None:
            # 从项目根目录的 templates 文件夹
            project_root = Path(__file__).parent.parent.parent
            self._system_template_dir = project_root / "templates"
            self._logger.info(f"系统模板目录: {self._system_template_dir}")

        return self._system_template_dir

    def resolve_template_path(self, relative_path: str) -> Optional[Path]:
        """
        解析模板路径（优先用户模板）

        支持以下格式：
        1. 相对于系统模板目录的相对路径（推荐）: civil/plaintiff/起诉状.docx
        2. 旧版格式（相对于项目根目录）: templates/civil/plaintiff/起诉状.docx
        3. 绝对路径（必须在允许目录内）

        Args:
            relative_path: 相对路径或绝对路径

        Returns:
            解析后的完整路径，如果不存在则返回 None
        """
        if not relative_path:
            return None

        raw_path = str(relative_path).strip()
        path = Path(raw_path)

        # 如果是绝对路径，检查是否在允许的目录内
        if path.is_absolute():
            # 只允许访问系统模板目录和用户模板目录
            system_dir = self.get_system_template_dir()
            user_dir = self.get_user_template_dir()
            try:
                resolved_path = path.resolve(strict=True)
            except OSError:
                self._logger.warning(f"绝对路径不存在或不可访问: {relative_path}")
                return None
            try:
                resolved_path.relative_to(system_dir.resolve())
                return resolved_path
            except ValueError:
                pass
            try:
                resolved_path.relative_to(user_dir.resolve())
                return resolved_path
            except ValueError:
                pass
            self._logger.warning(f"绝对路径不在允许的目录内: {relative_path}")
            return None

        # 安全检查：防止路径遍历攻击
        normalized = raw_path.replace('\\', '/')
        relative_parts = Path(normalized).parts
        if ".." in relative_parts or normalized.startswith('\\') or normalized.startswith('//'):
            self._logger.warning(f"检测到可疑的模板路径: {relative_path}")
            return None
        relative_path = normalized

        # 兼容旧格式：路径以 templates/ 开头时，先尝试相对于项目根目录解析
        if normalized.startswith('templates/'):
            from src.config.path_manager import get_path_manager
            app_dir = get_path_manager().app_dir
            legacy_path = app_dir / relative_path
            if legacy_path.exists():
                try:
                    legacy_path.resolve().relative_to(app_dir.resolve())
                    return legacy_path
                except ValueError:
                    pass
            # 旧格式路径不存在时，去掉 templates/ 前缀按新格式继续解析
            relative_path = normalized[len('templates/'):]

        # 先查找用户模板目录
        user_path = self.get_user_template_dir() / relative_path
        if user_path.exists():
            # 再次验证解析后的路径是否仍在目录内
            try:
                user_path.resolve().relative_to(self.get_user_template_dir().resolve())
            except ValueError:
                self._logger.warning(f"路径遍历攻击检测: {relative_path}")
                return None
            return user_path

        # 再查找系统模板目录
        system_path = self.get_system_template_dir() / relative_path
        if system_path.exists():
            # 再次验证解析后的路径是否仍在目录内
            try:
                system_path.resolve().relative_to(self.get_system_template_dir().resolve())
            except ValueError:
                self._logger.warning(f"路径遍历攻击检测: {relative_path}")
                return None
            return system_path

        self._logger.warning(f"模板文件不存在: {relative_path}")
        return None

    def validate_template_path(self, template_path: str) -> tuple[bool, str]:
        """
        验证模板路径

        Args:
            template_path: 模板路径

        Returns:
            (是否有效, 错误消息)
        """
        if not template_path:
            return False, "模板路径不能为空"

        path = Path(template_path)

        # 检查文件扩展名
        if path.suffix.lower() not in ['.docx', '.doc']:
            return False, "模板文件必须是 .docx 或 .doc 格式"

        # 解析路径
        resolved_path = self.resolve_template_path(template_path)
        if resolved_path is None:
            return False, f"模板文件不存在: {template_path}"

        return True, ""

    def get_available_templates(self, category: str = "", use_cache: bool = True) -> List[Dict]:
        """
        获取可用的模板列表

        Args:
            category: 模板类别（civil, criminal, non_litigation），为空则返回所有
            use_cache: 是否使用缓存

        Returns:
            模板列表，每个模板包含 name, path, category, variables
        """
        cache_key = category or "__all__"

        # 检查缓存
        if use_cache:
            with self._cache_lock:
                if cache_key in self._templates_cache:
                    cached_data, timestamp = self._templates_cache[cache_key]
                    if time.time() - timestamp < self.CACHE_TTL:
                        self._logger.debug(f"使用缓存的模板列表: {cache_key}")
                        return cached_data.copy()

        templates = self._scan_templates(category)

        # 更新缓存
        with self._cache_lock:
            self._templates_cache[cache_key] = (templates.copy(), time.time())

        return templates

    def _scan_templates(self, category: str = "") -> List[Dict]:
        """
        扫描模板文件系统

        Args:
            category: 模板类别

        Returns:
            模板列表
        """
        templates = []

        # 扫描系统模板目录
        system_dir = self.get_system_template_dir()

        if category:
            # 扫描指定类别
            scan_dirs = [system_dir / category]
        else:
            # 扫描所有子目录（civil, criminal, non_litigation等）
            scan_dirs = []
            if system_dir.exists():
                for sub_dir in system_dir.iterdir():
                    if sub_dir.is_dir():
                        scan_dirs.append(sub_dir)
            # 同时也扫描根目录
            scan_dirs.append(system_dir)

        for scan_dir in scan_dirs:
            if scan_dir.exists():
                # 扫描 .docx 和 .doc 文件
                for pattern in ["*.docx", "*.doc"]:
                    for template_file in scan_dir.glob(pattern):
                        template_info = {
                            "name": template_file.stem,
                            "path": str(template_file.relative_to(system_dir)),
                            "category": category or template_file.parent.name,
                            "is_system": True
                        }
                        templates.append(template_info)

        # 扫描用户模板目录
        user_dir = self.get_user_template_dir()

        if category:
            # 扫描指定类别
            scan_user_dirs = [user_dir / category]
        else:
            # 扫描所有子目录
            scan_user_dirs = []
            if user_dir.exists():
                for sub_dir in user_dir.iterdir():
                    if sub_dir.is_dir():
                        scan_user_dirs.append(sub_dir)
            # 同时也扫描根目录
            scan_user_dirs.append(user_dir)

        for scan_dir in scan_user_dirs:
            if scan_dir.exists():
                # 扫描 .docx 和 .doc 文件
                for pattern in ["*.docx", "*.doc"]:
                    for template_file in scan_dir.glob(pattern):
                        template_category = category or template_file.parent.name
                        # 避免重复（用户模板优先）
                        existing = next(
                            (
                                t for t in templates
                                if t["name"] == template_file.stem and t["category"] == template_category
                            ),
                            None,
                        )
                        if existing:
                            existing["is_system"] = False
                            existing["path"] = str(template_file.relative_to(user_dir))
                            existing["category"] = template_category
                        else:
                            template_info = {
                                "name": template_file.stem,
                                "path": str(template_file.relative_to(user_dir)),
                                "category": template_category,
                                "is_system": False
                            }
                            templates.append(template_info)

        self._logger.info(f"扫描完成，共找到 {len(templates)} 个模板")
        return templates

    def to_relative_template_path(self, absolute_path: Path) -> str:
        """
        将绝对路径转换为相对模板路径

        如果路径位于系统模板目录内，返回相对于 templates 目录的路径；
        如果路径位于项目根目录内（如 templates/ 子目录），返回相对于项目根目录的路径；
        否则返回原始绝对路径。

        Args:
            absolute_path: 绝对路径

        Returns:
            相对路径字符串（使用正斜杠）
        """
        if not absolute_path.is_absolute():
            return str(absolute_path).replace('\\', '/')

        try:
            system_dir = self.get_system_template_dir()
            rel = absolute_path.resolve().relative_to(system_dir.resolve())
            return str(rel).replace('\\', '/')
        except ValueError:
            pass

        try:
            from src.config.path_manager import get_path_manager
            app_dir = get_path_manager().app_dir
            rel = absolute_path.resolve().relative_to(app_dir.resolve())
            return str(rel).replace('\\', '/')
        except ValueError:
            pass

        return str(absolute_path).replace('\\', '/')

    def clear_cache(self) -> None:
        """清除模板缓存"""
        with self._cache_lock:
            self._templates_cache.clear()
        self._logger.info("模板缓存已清除")

    def copy_template_to_user_dir(self, source_path: Path, category: str = "") -> Path:
        """
        复制模板到用户模板目录

        Args:
            source_path: 源模板文件路径
            category: 目标类别

        Returns:
            目标文件路径
        """
        import shutil

        user_dir = self.get_user_template_dir()
        if category:
            target_dir = user_dir / category
        else:
            target_dir = user_dir

        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / source_path.name
        shutil.copy2(source_path, target_path)

        # 清除缓存以确保下次获取最新模板列表
        self.clear_cache()

        self._logger.info(f"模板已复制到用户目录: {target_path}")
        return target_path


# 全局单例
_template_path_manager: Optional[TemplatePathManager] = None
_template_path_lock: threading.Lock = threading.Lock()


def get_template_path_manager() -> TemplatePathManager:
    """
    获取模板路径管理器单例

    Returns:
        TemplatePathManager 实例
    """
    global _template_path_manager
    if _template_path_manager is None:
        with _template_path_lock:
            if _template_path_manager is None:
                _template_path_manager = TemplatePathManager()
    return _template_path_manager
