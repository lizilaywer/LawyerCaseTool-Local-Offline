# -*- coding: utf-8 -*-
"""配置管理器测试"""

import pytest
from pathlib import Path
import tempfile
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.config.config_manager import ConfigManager
from src.config.default_templates import DEFAULT_PINNED_CONFIG, DEFAULT_TEMPLATES


class TestConfigManager:
    """配置管理器测试类"""

    def test_get_default_config(self):
        """测试获取默认配置"""
        # 这个测试需要模拟单例
        manager = ConfigManager()
        config = manager._get_default_config()

        assert "app" in config
        assert "generation" in config
        assert "ui" in config

    def test_get_set_config_value(self):
        """测试获取和设置配置值"""
        manager = ConfigManager()

        # 设置值
        manager.set("test.key", "value", save=False)
        assert manager.get("test.key") == "value"

        # 获取不存在的键
        assert manager.get("nonexistent", "default") == "default"

    def test_nested_config_access(self):
        """测试嵌套配置访问"""
        manager = ConfigManager()

        # 设置嵌套值
        manager.set("nested.deep.key", "nested_value", save=False)
        assert manager.get("nested.deep.key") == "nested_value"

    def test_get_templates(self):
        """测试获取模板列表"""
        manager = ConfigManager()
        templates = manager.get_templates()

        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_get_template_by_id(self):
        """测试根据 ID 获取模板"""
        manager = ConfigManager()

        # 获取存在的模板
        template = manager.get_template("civil_simple_001")
        assert template is not None
        assert template["name"] == "民事案件简易模板(原告)"

        # 获取不存在的模板
        template = manager.get_template("nonexistent")
        assert template is None

    def test_get_all_config_returns_deep_copy(self):
        """读取配置时应返回深拷贝，避免调用方污染内部状态。"""
        manager = object.__new__(ConfigManager)
        manager._config = {
            "pinned": {"global": ["civil_simple_001"]},
            "app": {"theme": "default"},
        }

        config = manager.get_all_config()
        config["pinned"]["global"].append("criminal_001")

        assert manager._config["pinned"]["global"] == ["civil_simple_001"]

    def test_get_template_returns_deep_copy(self):
        """读取单个模板时应返回深拷贝，避免嵌套结构被外部修改。"""
        manager = object.__new__(ConfigManager)
        manager._templates = [
            {
                "id": "demo",
                "variables": [{"key": "client_name"}],
                "folder_structure": {"folders": [{"name": "材料"}]},
            }
        ]

        template = manager.get_template("demo")
        assert template is not None

        template["variables"][0]["key"] = "changed"
        template["folder_structure"]["folders"][0]["name"] = "已修改"

        stored_template = manager._templates[0]
        assert stored_template["variables"][0]["key"] == "client_name"
        assert stored_template["folder_structure"]["folders"][0]["name"] == "材料"

    def test_reset_templates_deep_copies_default_pinned_config(self):
        """重置模板时不应复用默认置顶配置中的可变嵌套对象。"""
        manager = object.__new__(ConfigManager)
        manager._config = {"app": {}, "generation": {}, "ui": {}, "pinned": {}}
        manager._templates = []
        manager._logger = Mock()
        manager._save_templates = Mock(return_value=True)
        manager._save_config = Mock(return_value=True)

        manager.reset_templates(include_settings=True)

        assert manager._config["pinned"] == DEFAULT_PINNED_CONFIG
        assert manager._config["pinned"] is not DEFAULT_PINNED_CONFIG
        assert manager._config["pinned"]["global"] is not DEFAULT_PINNED_CONFIG["global"]

    def test_corrupt_config_is_backed_up_before_default_recreate(self, tmp_path):
        """配置 JSON 损坏时应备份原文件，再创建新的默认配置。"""
        config_file = tmp_path / "config.json"
        templates_file = tmp_path / "templates.json"
        config_file.write_text("{broken", encoding="utf-8")

        manager = object.__new__(ConfigManager)
        manager._path_manager = SimpleNamespace(
            config_file=config_file,
            templates_config_file=templates_file,
        )
        manager._logger = Mock()

        manager._load_or_create_config()

        backups = list(tmp_path.glob("config.json.corrupt-*.bak"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == "{broken"
        assert manager._validate_config(json.loads(config_file.read_text(encoding="utf-8")))

    def test_invalid_templates_are_backed_up_before_default_recreate(self, tmp_path):
        """模板结构无效时应备份原文件，再写入默认模板。"""
        config_file = tmp_path / "config.json"
        templates_file = tmp_path / "templates.json"
        templates_file.write_text(json.dumps([{"id": "bad"}]), encoding="utf-8")

        manager = object.__new__(ConfigManager)
        manager._path_manager = SimpleNamespace(
            config_file=config_file,
            templates_config_file=templates_file,
        )
        manager._logger = Mock()

        manager._load_or_create_templates()

        backups = list(tmp_path.glob("templates.json.corrupt-*.bak"))
        assert len(backups) == 1
        assert json.loads(backups[0].read_text(encoding="utf-8")) == [{"id": "bad"}]
        assert json.loads(templates_file.read_text(encoding="utf-8")) == DEFAULT_TEMPLATES
