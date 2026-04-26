# -*- coding: utf-8 -*-
"""右键菜单集成模块"""

import sys
from pathlib import Path
from typing import Optional

from src.integration.registry_manager import RegistryManager
from src.utils.logger import get_logger
from src.utils.exceptions import RegistryError, PermissionDeniedError


class ContextMenuManager:
    """Windows 右键菜单管理器"""

    # 注册表键路径
    # 键名继续保留 LawyerCaseTool，避免覆盖或丢失已安装的旧菜单项。
    DIRECTORY_BACKGROUND_KEY = r"Directory\Background\shell\LawyerCaseTool"
    DIRECTORY_KEY = r"Directory\shell\LawyerCaseTool"
    BACKUP_EXTENSION = ".lexora-backup"
    BACKUP_PROG_ID = "CaseFolderManager.LEXORABackup"

    def __init__(self):
        self._registry = RegistryManager()
        self._logger = get_logger()

    def get_executable_path(self) -> str:
        """获取可执行文件路径"""
        if getattr(sys, 'frozen', False):
            # 打包后的 exe
            return f'"{sys.executable}"'
        else:
            # 开发环境：优先 pythonw（Windows 下无控制台），并确保路径加引号
            main_py = Path(__file__).parent.parent / "main.py"
            interpreter = Path(sys.executable)
            pythonw = interpreter.with_name("pythonw.exe")
            if pythonw.exists():
                interpreter = pythonw
            return f'"{interpreter}" "{main_py}"'

    def install(self, icon_path: Optional[str] = None) -> bool:
        """
        安装右键菜单

        Args:
            icon_path: 图标路径

        Returns:
            是否成功
        """
        try:
            exe_path = self.get_executable_path()
            command = f'{exe_path} "%V"'

            # 在文件夹背景右键菜单中添加
            self._registry.add_context_menu(
                self.DIRECTORY_BACKGROUND_KEY,
                "在此处新建案件目录",
                command,
                icon_path
            )

            # 在文件夹右键菜单中添加
            self._registry.add_context_menu(
                self.DIRECTORY_KEY,
                "在此文件夹新建案件目录",
                command,
                icon_path
            )

            self._logger.info("右键菜单安装成功")
            return True

        except (RegistryError, PermissionDeniedError) as e:
            self._logger.error(f"右键菜单安装失败: {e}")
            return False

    def get_backup_import_command(self) -> str:
        """获取备份文件双击导入命令。"""
        return f'{self.get_executable_path()} --import-backup "%1"'

    def install_backup_file_association(self, icon_path: Optional[str] = None) -> bool:
        """
        安装 LEXORA 备份文件关联。

        文件关联写入当前用户注册表，不需要管理员权限。
        """
        try:
            return self._registry.add_file_association(
                self.BACKUP_EXTENSION,
                self.BACKUP_PROG_ID,
                "LEXORA 本地备份",
                self.get_backup_import_command(),
                icon_path,
            )
        except (RegistryError, PermissionDeniedError) as e:
            self._logger.error(f"备份文件关联安装失败: {e}")
            return False

    def uninstall_backup_file_association(self) -> bool:
        """
        卸载 LEXORA 备份文件关联。
        """
        try:
            return self._registry.remove_file_association(
                self.BACKUP_EXTENSION,
                self.BACKUP_PROG_ID,
            )
        except (RegistryError, PermissionDeniedError) as e:
            self._logger.error(f"备份文件关联卸载失败: {e}")
            return False

    def is_backup_file_association_installed(self) -> bool:
        """
        检查 LEXORA 备份文件关联是否已安装。
        """
        return self._registry.check_file_association_exists(
            self.BACKUP_EXTENSION,
            self.BACKUP_PROG_ID,
        )

    def uninstall(self) -> bool:
        """
        卸载右键菜单

        Returns:
            是否成功
        """
        try:
            # 删除文件夹背景菜单项
            self._registry.remove_context_menu(self.DIRECTORY_BACKGROUND_KEY)

            # 删除文件夹菜单项
            self._registry.remove_context_menu(self.DIRECTORY_KEY)

            self._logger.info("右键菜单卸载成功")
            return True

        except (RegistryError, PermissionDeniedError) as e:
            self._logger.error(f"右键菜单卸载失败: {e}")
            return False

    def is_installed(self) -> bool:
        """
        检查右键菜单是否已安装

        Returns:
            是否已安装
        """
        return self._registry.check_context_menu_exists(
            self.DIRECTORY_BACKGROUND_KEY
        )

    def get_install_status(self) -> dict:
        """
        获取安装状态

        Returns:
            状态信息字典
        """
        return {
            "background_menu": self._registry.check_context_menu_exists(
                self.DIRECTORY_BACKGROUND_KEY
            ),
            "directory_menu": self._registry.check_context_menu_exists(
                self.DIRECTORY_KEY
            ),
            "backup_file_association": self.is_backup_file_association_installed(),
            "background_command": self._registry.get_context_menu_command(
                self.DIRECTORY_BACKGROUND_KEY
            ),
            "directory_command": self._registry.get_context_menu_command(
                self.DIRECTORY_KEY
            ),
            "backup_import_command": self.get_backup_import_command(),
        }


def install_context_menu(icon_path: Optional[str] = None) -> bool:
    """
    安装右键菜单的便捷函数

    Args:
        icon_path: 图标路径

    Returns:
        是否成功
    """
    manager = ContextMenuManager()
    return manager.install(icon_path)


def uninstall_context_menu() -> bool:
    """
    卸载右键菜单的便捷函数

    Returns:
        是否成功
    """
    manager = ContextMenuManager()
    return manager.uninstall()


def is_context_menu_installed() -> bool:
    """
    检查右键菜单是否已安装

    Returns:
        是否已安装
    """
    manager = ContextMenuManager()
    return manager.is_installed()


def install_backup_file_association(icon_path: Optional[str] = None) -> bool:
    """
    安装备份文件关联的便捷函数。
    """
    manager = ContextMenuManager()
    return manager.install_backup_file_association(icon_path)


def uninstall_backup_file_association() -> bool:
    """
    卸载备份文件关联的便捷函数。
    """
    manager = ContextMenuManager()
    return manager.uninstall_backup_file_association()


def is_backup_file_association_installed() -> bool:
    """
    检查备份文件关联是否已安装。
    """
    manager = ContextMenuManager()
    return manager.is_backup_file_association_installed()
