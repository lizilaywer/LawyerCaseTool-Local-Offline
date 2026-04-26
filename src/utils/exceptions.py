# -*- coding: utf-8 -*-
"""自定义异常模块"""


class LawyerToolError(Exception):
    """律师工具基础异常"""

    def __init__(self, message: str = "发生错误"):
        super().__init__(message)


class TemplateError(LawyerToolError):
    """模板相关异常"""

    def __init__(self, message: str = "模板处理错误"):
        super().__init__(message)


class TemplateNotFoundError(TemplateError):
    """模板未找到异常"""

    def __init__(self, template_id: str = ""):
        message = f"模板未找到: {template_id}" if template_id else "模板未找到"
        super().__init__(message)


class TemplateFileError(TemplateError):
    """模板文件错误异常"""

    def __init__(self, file_path: str = "", reason: str = ""):
        message = f"模板文件错误: {file_path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class VariableError(LawyerToolError):
    """变量相关异常"""

    def __init__(self, message: str = "变量处理错误"):
        super().__init__(message)


class VariableValidationError(VariableError):
    """变量验证失败异常"""

    def __init__(self, variable_key: str, reason: str = ""):
        message = f"变量验证失败: {variable_key}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class VariableMissingError(VariableError):
    """必填变量缺失异常"""

    def __init__(self, variable_key: str = ""):
        message = f"必填变量缺失: {variable_key}" if variable_key else "必填变量缺失"
        super().__init__(message)


class FolderGenerationError(LawyerToolError):
    """文件夹生成异常"""

    def __init__(self, folder_path: str = "", reason: str = ""):
        message = f"文件夹生成失败: {folder_path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class ConfigError(LawyerToolError):
    """配置相关异常"""

    def __init__(self, message: str = "配置错误"):
        super().__init__(message)


class ConfigNotFoundError(ConfigError):
    """配置未找到异常"""

    def __init__(self, config_name: str = ""):
        message = f"配置未找到: {config_name}" if config_name else "配置未找到"
        super().__init__(message)


class RegistryError(LawyerToolError):
    """注册表操作异常"""

    def __init__(self, message: str = "注册表操作错误"):
        super().__init__(message)


class PermissionDeniedError(LawyerToolError):
    """权限不足异常"""

    def __init__(self, operation: str = ""):
        message = f"权限不足: {operation}" if operation else "权限不足"
        super().__init__(message)
