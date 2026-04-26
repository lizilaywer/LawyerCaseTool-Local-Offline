# -*- coding: utf-8 -*-
"""模板引擎测试"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.template_engine import TemplateEngine


class TestTemplateEngine:
    """模板引擎测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.engine = TemplateEngine()

    def test_prepare_context_with_none(self):
        """测试 None 值处理 - None 值应显式保留模板占位符"""
        values = {"name": None, "title": "测试"}
        context = self.engine._prepare_context(values)
        assert context["name"] == "{{name}}"
        assert context["title"] == "测试"

    def test_prepare_context_with_blank_string(self):
        """测试空字符串处理 - 空字符串也应保留模板占位符。"""
        values = {"name": "   ", "title": "测试"}
        context = self.engine._prepare_context(values)

        assert context["name"] == "{{name}}"
        assert context["title"] == "测试"

    def test_prepare_context_with_string(self):
        """测试字符串处理"""
        values = {"client": "张三", "case": "民事纠纷"}
        context = self.engine._prepare_context(values)
        assert context["client"] == "张三"
        assert context["case"] == "民事纠纷"

    def test_validate_template_not_exists(self):
        """测试验证不存在的模板"""
        result, msg = self.engine.validate_template(Path("/nonexistent/path.docx"))
        assert result is False
        assert "不存在" in msg

    def test_validate_template_wrong_extension(self):
        """测试验证错误扩展名"""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = Path(f.name)

        try:
            result, msg = self.engine.validate_template(temp_path)
            assert result is False
            assert "docx" in msg.lower()
        finally:
            temp_path.unlink()
