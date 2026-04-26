# -*- coding: utf-8 -*-
"""右键菜单命令构造测试"""

from src.integration.context_menu import ContextMenuManager
import src.integration.context_menu as context_menu_module


class TestContextMenu:
    """ContextMenuManager 测试类"""

    def test_get_executable_path_quotes_frozen_executable(self, monkeypatch):
        """打包态可执行路径应始终带引号，避免空格路径解析错误。"""
        monkeypatch.setattr(context_menu_module.sys, "frozen", True, raising=False)
        monkeypatch.setattr(
            context_menu_module.sys,
            "executable",
            r"C:\Program Files\LawyerCaseTool\lawyer-case-tool.exe",
            raising=False,
        )

        manager = ContextMenuManager()
        path = manager.get_executable_path()
        assert path == r'"C:\Program Files\LawyerCaseTool\lawyer-case-tool.exe"'

    def test_get_executable_path_quotes_interpreter_and_main_in_dev(self, monkeypatch):
        """开发态命令应同时引用解释器和 main.py 路径。"""
        monkeypatch.setattr(context_menu_module.sys, "frozen", False, raising=False)
        monkeypatch.setattr(
            context_menu_module.sys,
            "executable",
            r"C:\Program Files\Python313\python.exe",
            raising=False,
        )

        manager = ContextMenuManager()
        path = manager.get_executable_path()
        assert path.startswith(r'"C:\Program Files\Python313')
        assert "main.py" in path

    def test_get_backup_import_command_uses_file_association_placeholder(self, monkeypatch):
        """备份文件关联命令应复用主入口并传入 %1。"""
        monkeypatch.setattr(context_menu_module.sys, "frozen", True, raising=False)
        monkeypatch.setattr(
            context_menu_module.sys,
            "executable",
            r"C:\Program Files\LawyerCaseTool\lexora.exe",
            raising=False,
        )

        manager = ContextMenuManager()
        command = manager.get_backup_import_command()
        assert command == (
            r'"C:\Program Files\LawyerCaseTool\lexora.exe" '
            r'--import-backup "%1"'
        )
