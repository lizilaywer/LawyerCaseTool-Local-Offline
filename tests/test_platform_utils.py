# -*- coding: utf-8 -*-
"""平台工具测试"""

from pathlib import Path

from src.utils import platform_utils


class TestPlatformUtils:
    """平台工具测试类"""

    def test_get_app_data_dir_on_windows(self, monkeypatch):
        """测试 Windows 应用数据目录"""
        monkeypatch.setattr(platform_utils.sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", r"C:\Users\Test\AppData\Roaming")

        result = platform_utils.get_app_data_dir("LawyerCaseTool")

        assert result == Path(r"C:\Users\Test\AppData\Roaming") / "LawyerCaseTool"

    def test_get_app_data_dir_on_macos(self, monkeypatch):
        """测试 macOS 应用数据目录"""
        monkeypatch.setattr(platform_utils.sys, "platform", "darwin")
        monkeypatch.setattr(platform_utils.Path, "home", lambda: Path("/Users/tester"))

        result = platform_utils.get_app_data_dir("LawyerCaseTool")

        assert result == Path("/Users/tester/Library/Application Support/LawyerCaseTool")

    def test_get_app_data_dir_on_linux(self, monkeypatch):
        """测试 Linux 应用数据目录"""
        monkeypatch.setattr(platform_utils.sys, "platform", "linux")
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setattr(platform_utils.Path, "home", lambda: Path("/home/tester"))

        result = platform_utils.get_app_data_dir("LawyerCaseTool")

        assert result == Path("/home/tester/.local/share/LawyerCaseTool")

    def test_get_default_output_dir_on_macos(self, monkeypatch):
        """测试 macOS 默认案卷输出目录为桌面"""
        monkeypatch.setattr(platform_utils.sys, "platform", "darwin")
        monkeypatch.setattr(platform_utils.Path, "home", lambda: Path("/Users/tester"))

        result = platform_utils.get_default_output_dir()

        assert result == Path("/Users/tester/Desktop/案卷")

    def test_get_default_output_dir_on_windows(self, monkeypatch):
        """测试 Windows 默认案卷输出目录为桌面"""
        monkeypatch.setattr(platform_utils.sys, "platform", "win32")
        monkeypatch.setenv("USERPROFILE", r"C:\Users\Tester")

        result = platform_utils.get_default_output_dir()

        assert result == Path(r"C:\Users\Tester\Desktop\案卷")

    def test_get_default_ui_font_family_on_windows(self, monkeypatch):
        """Windows 使用更贴近系统控件的 UI 字体。"""
        monkeypatch.setattr(platform_utils.sys, "platform", "win32")

        assert platform_utils.get_default_ui_font_family() == "Microsoft YaHei UI"

    def test_get_documents_dir_falls_back_when_documents_missing(self, monkeypatch):
        """测试文稿目录不存在时回退到候选目录"""
        monkeypatch.setattr(platform_utils.sys, "platform", "darwin")
        monkeypatch.setattr(platform_utils.Path, "home", lambda: Path("/Users/tester"))
        monkeypatch.setattr(platform_utils.Path, "exists", lambda self: False)

        result = platform_utils.get_documents_dir()

        assert result == Path("/Users/tester/Documents")

    def test_open_path_returns_error_for_missing_target(self):
        """测试打开不存在路径时返回错误"""
        ok, error = platform_utils.open_path("/path/that/does/not/exist")

        assert ok is False
        assert "不存在" in error
