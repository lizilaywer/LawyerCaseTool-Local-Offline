# -*- coding: utf-8 -*-
"""数据验证模块"""

import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


class Validator:
    """数据验证器基类"""

    @staticmethod
    def validate(value: Any, rules: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证数据

        Args:
            value: 待验证的值
            rules: 验证规则

        Returns:
            (是否有效, 错误消息)
        """
        raise NotImplementedError


class TextValidator(Validator):
    """文本验证器"""

    @staticmethod
    def validate(value: Any, rules: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(value, str):
            return False, "值必须是文本类型"

        min_length = rules.get('min_length', 0)
        max_length = rules.get('max_length', float('inf'))
        pattern = rules.get('pattern')

        if len(value) < min_length:
            return False, f"长度不能少于 {min_length} 个字符"

        if len(value) > max_length:
            return False, f"长度不能超过 {max_length} 个字符"

        if pattern and not re.match(pattern, value):
            return False, f"格式不正确"

        return True, ""


class NumberValidator(Validator):
    """数字验证器"""

    @staticmethod
    def validate(value: Any, rules: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, "值必须是数字"

        min_val = rules.get('min_value')
        max_val = rules.get('max_value')

        if min_val is not None and num_value < min_val:
            return False, f"值不能小于 {min_val}"

        if max_val is not None and num_value > max_val:
            return False, f"值不能大于 {max_val}"

        return True, ""


class DateValidator(Validator):
    """日期验证器"""

    @staticmethod
    def validate(value: Any, rules: Dict[str, Any]) -> Tuple[bool, str]:
        if isinstance(value, datetime):
            return True, ""

        if not isinstance(value, str):
            return False, "值必须是日期类型"

        date_format = rules.get('format', '%Y-%m-%d')

        try:
            datetime.strptime(value, date_format)
            return True, ""
        except ValueError:
            return False, f"日期格式不正确，应为 {date_format}"


class SelectValidator(Validator):
    """选择验证器"""

    @staticmethod
    def validate(value: Any, rules: Dict[str, Any]) -> Tuple[bool, str]:
        options = rules.get('options', [])
        if value not in options:
            return False, f"值必须是以下选项之一: {', '.join(map(str, options))}"
        return True, ""


def validate_variable(
    value: Any,
    var_type: str,
    required: bool,
    rules: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    验证变量值

    Args:
        value: 变量值
        var_type: 变量类型 (text, number, date, select)
        required: 是否必填
        rules: 验证规则

    Returns:
        (是否有效, 错误消息)
    """
    rules = rules or {}

    # 检查必填
    if required and (value is None or value == ''):
        return False, "此字段为必填项"

    # 空值且非必填，直接通过
    if value is None or value == '':
        return True, ""

    # 根据类型选择验证器
    validators = {
        'text': TextValidator,
        'number': NumberValidator,
        'date': DateValidator,
        'select': SelectValidator
    }

    validator = validators.get(var_type, TextValidator)
    return validator.validate(value, rules)


def sanitize_filename(filename: str, strip_ui_markers: bool = True) -> str:
    """
    清理文件名中的非法字符

    Args:
        filename: 原始文件名
        strip_ui_markers: 是否移除 UI 显示标记符号

    Returns:
        清理后的文件名
    """
    if strip_ui_markers:
        filename = filename.replace(" ✓", "").replace(" 📎", "")

    # Windows 文件名非法字符 + 中文引号
    illegal_chars = r'[<>:"/\\|?*""]'  # 添加了中文引号 " 和 "
    return re.sub(illegal_chars, '_', filename)


def validate_folder_name(name: str) -> Tuple[bool, str]:
    """
    验证文件夹名称

    Args:
        name: 文件夹名称

    Returns:
        (是否有效, 错误消息)
    """
    if not name:
        return False, "文件夹名称不能为空"

    if len(name) > 255:
        return False, "文件夹名称不能超过255个字符"

    # 检查非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    if re.search(illegal_chars, name):
        return False, "文件夹名称包含非法字符"

    # 检查保留名称
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    if name.upper() in reserved_names:
        return False, f"'{name}' 是系统保留名称"

    # 检查尾部点号或空格（Windows 不允许）
    if name.rstrip('. ') != name:
        return False, "文件夹名称不能以点号或空格结尾"

    # 检查控制字符
    if re.search(r'[\x00-\x1f\x7f]', name):
        return False, "文件夹名称不能包含控制字符"

    return True, ""
