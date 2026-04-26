# -*- coding: utf-8 -*-
"""注册表管理模块"""

import sys
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger
from src.utils.exceptions import RegistryError, PermissionDeniedError


class RegistryManager:
    """Windows 注册表管理器"""

    def __init__(self):
        self._logger = get_logger()

    def _check_windows(self) -> bool:
        """检查是否为 Windows 系统"""
        if sys.platform != "win32":
            self._logger.warning("注册表操作仅支持 Windows 系统")
            return False
        return True

    def add_context_menu(
        self,
        key_path: str,
        display_name: str,
        command: str,
        icon: Optional[str] = None
    ) -> bool:
        """
        添加右键菜单项

        Args:
            key_path: 注册表键路径
            display_name: 显示名称
            command: 执行命令
            icon: 图标路径

        Returns:
            是否成功
        """
        if not self._check_windows():
            return False

        try:
            import winreg

            # 创建或打开注册表键
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
                # 设置默认值（显示名称）
                winreg.SetValue(key, None, winreg.REG_SZ, display_name)

                # 设置图标
                if icon:
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon)

            # 创建 command 子键
            with winreg.CreateKey(
                winreg.HKEY_CLASSES_ROOT,
                f"{key_path}\\command"
            ) as command_key:
                winreg.SetValue(command_key, None, winreg.REG_SZ, command)

            self._logger.info(f"注册表项已添加: {key_path}")
            return True

        except PermissionError:
            raise PermissionDeniedError("写入注册表")
        except Exception as e:
            self._logger.error(f"添加注册表项失败: {e}")
            raise RegistryError(f"添加注册表项失败: {e}")

    def remove_context_menu(self, key_path: str) -> bool:
        """
        删除右键菜单项

        Args:
            key_path: 注册表键路径

        Returns:
            是否成功
        """
        if not self._check_windows():
            return False

        try:
            import winreg

            # 删除 command 子键
            try:
                command_key = f"{key_path}\\command"
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, command_key)
            except OSError:
                pass

            # 删除主键
            try:
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
            except OSError:
                pass

            self._logger.info(f"注册表项已删除: {key_path}")
            return True

        except PermissionError:
            raise PermissionDeniedError("删除注册表项")
        except Exception as e:
            self._logger.error(f"删除注册表项失败: {e}")
            raise RegistryError(f"删除注册表项失败: {e}")

    def check_context_menu_exists(self, key_path: str) -> bool:
        """
        检查右键菜单项是否存在

        Args:
            key_path: 注册表键路径

        Returns:
            是否存在
        """
        if not self._check_windows():
            return False

        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                key_path,
                0,
                winreg.KEY_READ
            ) as key:
                return True

        except OSError:
            return False

    def get_context_menu_command(self, key_path: str) -> Optional[str]:
        """
        获取右键菜单命令

        Args:
            key_path: 注册表键路径

        Returns:
            命令字符串，不存在返回 None
        """
        if not self._check_windows():
            return None

        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                f"{key_path}\\command",
                0,
                winreg.KEY_READ
            ) as command_key:
                value, _ = winreg.QueryValueEx(command_key, None)
                return value

        except OSError:
            return None

    def add_file_association(
        self,
        extension: str,
        prog_id: str,
        display_name: str,
        command: str,
        icon: Optional[str] = None,
    ) -> bool:
        """
        添加当前用户级文件关联。

        使用 HKCU\\Software\\Classes，避免为备份文件关联要求管理员权限。
        """
        if not self._check_windows():
            return False

        if not extension.startswith("."):
            raise RegistryError(f"文件扩展名必须以点开头: {extension}")

        try:
            import winreg

            classes_root = r"Software\Classes"
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                fr"{classes_root}\{extension}",
            ) as ext_key:
                winreg.SetValue(ext_key, None, winreg.REG_SZ, prog_id)

            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                fr"{classes_root}\{prog_id}",
            ) as prog_key:
                winreg.SetValue(prog_key, None, winreg.REG_SZ, display_name)

            if icon:
                with winreg.CreateKey(
                    winreg.HKEY_CURRENT_USER,
                    fr"{classes_root}\{prog_id}\DefaultIcon",
                ) as icon_key:
                    winreg.SetValue(icon_key, None, winreg.REG_SZ, icon)

            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                fr"{classes_root}\{prog_id}\shell\open\command",
            ) as command_key:
                winreg.SetValue(command_key, None, winreg.REG_SZ, command)

            self._notify_shell_change()
            self._logger.info(f"文件关联已添加: {extension} -> {prog_id}")
            return True

        except PermissionError:
            raise PermissionDeniedError("写入文件关联注册表")
        except Exception as e:
            self._logger.error(f"添加文件关联失败: {e}")
            raise RegistryError(f"添加文件关联失败: {e}")

    def remove_file_association(self, extension: str, prog_id: str) -> bool:
        """
        删除当前用户级文件关联。
        """
        if not self._check_windows():
            return False

        try:
            import winreg

            classes_root = r"Software\Classes"
            self._delete_tree(winreg.HKEY_CURRENT_USER, fr"{classes_root}\{prog_id}")
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    fr"{classes_root}\{extension}",
                    0,
                    winreg.KEY_READ | winreg.KEY_WRITE,
                ) as ext_key:
                    try:
                        current_value, _ = winreg.QueryValueEx(ext_key, None)
                    except OSError:
                        current_value = None

                if current_value == prog_id:
                    winreg.DeleteKey(
                        winreg.HKEY_CURRENT_USER,
                        fr"{classes_root}\{extension}",
                    )
            except OSError:
                pass

            self._notify_shell_change()
            self._logger.info(f"文件关联已删除: {extension} -> {prog_id}")
            return True

        except PermissionError:
            raise PermissionDeniedError("删除文件关联注册表")
        except Exception as e:
            self._logger.error(f"删除文件关联失败: {e}")
            raise RegistryError(f"删除文件关联失败: {e}")

    def check_file_association_exists(self, extension: str, prog_id: str) -> bool:
        """
        检查当前用户级文件关联是否存在。
        """
        if not self._check_windows():
            return False

        try:
            import winreg

            classes_root = r"Software\Classes"
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                fr"{classes_root}\{extension}",
                0,
                winreg.KEY_READ,
            ) as ext_key:
                ext_value, _ = winreg.QueryValueEx(ext_key, None)

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                fr"{classes_root}\{prog_id}\shell\open\command",
                0,
                winreg.KEY_READ,
            ):
                pass

            return ext_value == prog_id

        except OSError:
            return False

    def _delete_tree(self, root, key_path: str) -> None:
        """递归删除注册表键，兼容旧版 Python/Windows。"""
        if not self._check_windows():
            return

        import winreg

        try:
            with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                while True:
                    try:
                        child_name = winreg.EnumKey(key, 0)
                    except OSError:
                        break
                    self._delete_tree(root, fr"{key_path}\{child_name}")
            winreg.DeleteKey(root, key_path)
        except OSError:
            pass

    def _notify_shell_change(self) -> None:
        """通知 Windows Explorer 刷新文件关联缓存。"""
        if not self._check_windows():
            return

        try:
            import ctypes

            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
        except Exception:
            pass
