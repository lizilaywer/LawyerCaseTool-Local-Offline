# -*- coding: utf-8 -*-
"""validators 模块单元测试"""

from datetime import datetime

import pytest

from src.utils.validators import (
    TextValidator,
    NumberValidator,
    DateValidator,
    SelectValidator,
    validate_variable,
    sanitize_filename,
    validate_folder_name,
)


class TestTextValidator:
    """文本验证器测试"""

    def test_valid_text(self):
        ok, msg = TextValidator.validate("hello", {})
        assert ok is True
        assert msg == ""

    def test_non_string_fails(self):
        ok, msg = TextValidator.validate(123, {})
        assert ok is False

    def test_min_length(self):
        ok, msg = TextValidator.validate("ab", {"min_length": 5})
        assert ok is False
        assert "5" in msg

    def test_max_length(self):
        ok, msg = TextValidator.validate("abcdef", {"max_length": 3})
        assert ok is False
        assert "3" in msg

    def test_pattern_match(self):
        ok, msg = TextValidator.validate("2026-04-26", {"pattern": r"\d{4}-\d{2}-\d{2}"})
        assert ok is True

    def test_pattern_no_match(self):
        ok, msg = TextValidator.validate("not-a-date", {"pattern": r"\d{4}-\d{2}-\d{2}"})
        assert ok is False


class TestNumberValidator:
    """数字验证器测试"""

    def test_valid_integer(self):
        assert NumberValidator.validate(42, {})[0] is True

    def test_valid_float_string(self):
        assert NumberValidator.validate("3.14", {})[0] is True

    def test_non_number(self):
        assert NumberValidator.validate("abc", {})[0] is False

    def test_min_value(self):
        assert NumberValidator.validate(1, {"min_value": 5})[0] is False

    def test_max_value(self):
        assert NumberValidator.validate(100, {"max_value": 50})[0] is False

    def test_in_range(self):
        assert NumberValidator.validate(50, {"min_value": 0, "max_value": 100})[0] is True


class TestDateValidator:
    """日期验证器测试"""

    def test_valid_date_string(self):
        assert DateValidator.validate("2026-04-26", {})[0] is True

    def test_invalid_format(self):
        assert DateValidator.validate("26/04/2026", {})[0] is False

    def test_datetime_object(self):
        assert DateValidator.validate(datetime.now(), {})[0] is True

    def test_non_date(self):
        assert DateValidator.validate(12345, {})[0] is False


class TestSelectValidator:
    """选择验证器测试"""

    def test_valid_option(self):
        assert SelectValidator.validate("a", {"options": ["a", "b", "c"]})[0] is True

    def test_invalid_option(self):
        assert SelectValidator.validate("d", {"options": ["a", "b", "c"]})[0] is False


class TestValidateVariable:
    """统一验证入口测试"""

    def test_required_empty(self):
        ok, msg = validate_variable("", "text", required=True)
        assert ok is False
        assert "必填" in msg

    def test_required_none(self):
        assert validate_variable(None, "text", required=True)[0] is False

    def test_optional_empty_passes(self):
        assert validate_variable("", "text", required=False)[0] is True

    def test_optional_none_passes(self):
        assert validate_variable(None, "text", required=False)[0] is True

    def test_unknown_type_falls_back_to_text(self):
        ok, _ = validate_variable("hello", "unknown_type", required=False)
        assert ok is True


class TestSanitizeFilename:
    """文件名清理测试"""

    def test_removes_illegal_chars(self):
        result = sanitize_filename('test<>:"/\\|?*file')
        assert "<" not in result
        assert ">" not in result

    def test_strips_ui_markers(self):
        assert sanitize_filename("case_name ✓ 📎") == "case_name"

    def test_keeps_normal_name(self):
        assert sanitize_filename("正常文件名.txt") == "正常文件名.txt"

    def test_replaces_special_quotes(self):
        result = sanitize_filename('test"file"')
        assert '"' not in result


class TestValidateFolderName:
    """文件夹名称验证测试"""

    def test_empty_name(self):
        assert validate_folder_name("")[0] is False

    def test_valid_name(self):
        assert validate_folder_name("张三案件")[0] is True

    def test_illegal_chars(self):
        assert validate_folder_name("test<>file")[0] is False

    def test_reserved_name(self):
        assert validate_folder_name("CON")[0] is False
        assert validate_folder_name("aux")[0] is False

    def test_trailing_dot(self):
        assert validate_folder_name("test.")[0] is False

    def test_trailing_space(self):
        assert validate_folder_name("test ")[0] is False

    def test_too_long(self):
        assert validate_folder_name("x" * 256)[0] is False

    def test_control_chars(self):
        assert validate_folder_name("test\x00name")[0] is False
