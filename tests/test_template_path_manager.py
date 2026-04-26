# -*- coding: utf-8 -*-
"""模板路径管理器测试"""

import shutil
import tempfile
from pathlib import Path

from src.utils.template_path_manager import TemplatePathManager


class TestTemplatePathManager:
    """模板路径管理器测试类"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.system_dir = self.temp_dir / "system_templates"
        self.user_dir = self.temp_dir / "user_templates"
        self.system_dir.mkdir()
        self.user_dir.mkdir()

    def teardown_method(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _build_manager(self) -> TemplatePathManager:
        manager = TemplatePathManager()
        manager._system_template_dir = self.system_dir
        manager._user_template_dir = self.user_dir
        return manager

    def test_resolve_template_path_accepts_allowed_absolute_path(self):
        """允许目录内的绝对路径应能被正确解析。"""
        template_path = self.system_dir / "civil" / "起诉状.docx"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.touch()

        manager = self._build_manager()
        resolved = manager.resolve_template_path(str(template_path))

        assert resolved == template_path.resolve()

    def test_resolve_template_path_normalizes_windows_style_relative_path(self):
        """相对路径中的反斜杠应被统一处理，兼容跨平台配置。"""
        template_path = self.user_dir / "civil" / "答辩状.docx"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.touch()

        manager = self._build_manager()
        resolved = manager.resolve_template_path(r"civil\答辩状.docx")

        assert resolved == template_path

    def test_get_available_templates_keeps_category_when_user_override_exists(self):
        """同名模板跨分类共存时，用户覆盖只应作用于同分类项。"""
        civil_system = self.system_dir / "civil" / "委托合同.docx"
        criminal_system = self.system_dir / "criminal" / "委托合同.docx"
        criminal_user = self.user_dir / "criminal" / "委托合同.docx"

        for path in [civil_system, criminal_system, criminal_user]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

        manager = self._build_manager()
        templates = manager.get_available_templates(use_cache=False)
        by_category = {item["category"]: item for item in templates if item["name"] == "委托合同"}

        assert len(by_category) == 2
        assert by_category["civil"]["path"] == "civil/委托合同.docx"
        assert by_category["civil"]["is_system"] is True
        assert by_category["criminal"]["path"] == "criminal/委托合同.docx"
        assert by_category["criminal"]["is_system"] is False
