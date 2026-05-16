# -*- coding: utf-8 -*-
"""变量解析器模块"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.utils.validators import validate_variable, sanitize_filename
from src.utils.exceptions import (
    VariableError,
    VariableValidationError,
    VariableMissingError
)
from src.utils.logger import get_logger


class VariableParser:
    """变量解析器"""

    # 变量模式: {{variable_name}}
    VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')

    def __init__(self):
        self._logger = get_logger()

    def extract_variables(self, text: str) -> List[str]:
        """
        从文本中提取变量名

        Args:
            text: 包含变量的文本

        Returns:
            变量名列表
        """
        return sorted(set(self.VARIABLE_PATTERN.findall(text)))

    def extract_from_structure(self, structure: Dict[str, Any]) -> List[str]:
        """
        从文件夹结构中提取变量名

        Args:
            structure: 文件夹结构配置

        Returns:
            变量名列表
        """
        variables = set()

        def extract_from_dict(d: Dict[str, Any]) -> None:
            for key, value in d.items():
                if isinstance(value, str):
                    variables.update(self.extract_variables(value))
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            variables.update(self.extract_variables(item))
                        elif isinstance(item, dict):
                            extract_from_dict(item)
                elif isinstance(value, dict):
                    extract_from_dict(value)

        extract_from_dict(structure)
        return sorted(variables)

    def replace_variables(
        self,
        text: str,
        values: Dict[str, Any],
        sanitize: bool = False
    ) -> str:
        """
        替换文本中的变量

        Args:
            text: 包含变量的文本
            values: 变量值字典
            sanitize: 是否清理文件名非法字符

        Returns:
            替换后的文本
        """
        def replace(match):
            var_name = match.group(1)
            value = values.get(var_name, match.group(0))  # 未找到则保留原样
            if value is None:
                value = ""
            str_value = str(value)
            if sanitize:
                str_value = sanitize_filename(str_value)
            return str_value

        result = self.VARIABLE_PATTERN.sub(replace, text)

        # 对整个结果进行清理，包括模板中的非法字符（如中文引号）
        if sanitize:
            result = sanitize_filename(result)

        return result

    def validate_values(
        self,
        values: Dict[str, Any],
        variable_definitions: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        验证变量值

        Args:
            values: 变量值字典
            variable_definitions: 变量定义列表

        Returns:
            (是否全部有效, 错误消息列表)
        """
        errors = []

        for var_def in variable_definitions:
            key = var_def["key"]
            value = values.get(key)
            var_type = var_def.get("type", "text")
            required = var_def.get("required", False)
            validation = var_def.get("validation", {})

            is_valid, error_msg = validate_variable(
                value, var_type, required, validation
            )

            if not is_valid:
                label = var_def.get("label", key)
                errors.append(f"{label}: {error_msg}")

        return len(errors) == 0, errors

    def check_required_variables(
        self,
        values: Dict[str, Any],
        variable_definitions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        检查必填变量是否都有值

        Args:
            values: 变量值字典
            variable_definitions: 变量定义列表

        Returns:
            缺失的必填变量键列表
        """
        missing = []

        for var_def in variable_definitions:
            if var_def.get("required", False):
                key = var_def["key"]
                value = values.get(key)
                if value is None or value == "":
                    missing.append(key)

        return missing

    def apply_defaults(
        self,
        values: Dict[str, Any],
        variable_definitions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        应用默认值

        Args:
            values: 变量值字典
            variable_definitions: 变量定义列表

        Returns:
        应用了默认值的变量值字典
        """
        result = values.copy()

        for var_def in variable_definitions:
            key = var_def["key"]
            if key not in result or result[key] is None or result[key] == "":
                default = var_def.get("default_value")
                if default is not None:
                    result[key] = default

        return result

    def format_value(self, value: Any, var_type: str) -> str:
        """
        格式化变量值

        Args:
            value: 变量值
            var_type: 变量类型

        Returns:
            格式化后的字符串
        """
        if value is None:
            return ""

        if var_type == "date":
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            return str(value)

        return str(value)

    def get_display_value(self, value: Any, var_def: Dict[str, Any]) -> str:
        """
        获取变量的显示值

        Args:
            value: 变量值
            var_def: 变量定义

        Returns:
            显示值字符串
        """
        var_type = var_def.get("type", "text")

        if var_type == "select":
            options = var_def.get("validation", {}).get("options", [])
            if value in options:
                return str(value)
            return ""

        if var_type == "date":
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            if isinstance(value, str):
                return value
            return ""

        return str(value) if value is not None else ""
