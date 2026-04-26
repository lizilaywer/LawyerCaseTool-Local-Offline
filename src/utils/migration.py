# -*- coding: utf-8 -*-
"""数据迁移工具模块"""

from typing import Any, Dict, List
from src.utils.logger import get_logger


def migrate_template_structure(template: Dict[str, Any]) -> Dict[str, Any]:
    """
    迁移旧版本模板数据结构到新版本

    旧格式 (v1.0):
        "subfolders": ["委托代理合同", "授权委托书"]

    新格式 (v2.0):
        "subfolders": [
            {
                "name": "委托代理合同.docx",
                "type": "file",
                "template_path": ""
            },
            {
                "name": "其他材料",
                "type": "folder",
                "template_path": None
            }
        ]

    Args:
        template: 旧版本模板配置

    Returns:
        新版本模板配置
    """
    logger = get_logger()
    template = template.copy()
    folder_structure = template.get("folder_structure", {})
    folders = folder_structure.get("folders", [])

    migrated = False
    new_folders = []

    for folder in folders:
        new_folder = folder.copy()
        subfolders = folder.get("subfolders", [])

        # 检查是否需要迁移
        needs_migration = False
        for item in subfolders:
            if isinstance(item, str):
                needs_migration = True
                break

        if needs_migration:
            migrated = True
            new_subfolders = []
            for item in subfolders:
                if isinstance(item, str):
                    # 将字符串迁移为文件对象
                    # 如果不包含.docx后缀，自动添加
                    name = item
                    if not name.lower().endswith(".docx"):
                        name = f"{name}.docx"

                    new_subfolders.append({
                        "name": name,
                        "type": "file",
                        "template_path": ""
                    })
                elif isinstance(item, dict):
                    # 已经是新的格式，保持不变
                    new_subfolders.append(item)

            new_folder["subfolders"] = new_subfolders

        new_folders.append(new_folder)

    if migrated:
        template["folder_structure"]["folders"] = new_folders
        logger.info(f"模板 {template.get('id', 'unknown')} 数据结构已迁移")

    return template


def migrate_templates(templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量迁移模板列表

    Args:
        templates: 旧版本模板列表

    Returns:
        新版本模板列表
    """
    return [migrate_template_structure(t) for t in templates]


def is_template_v1(template: Dict[str, Any]) -> bool:
    """
    检查模板是否为 v1.0 格式

    Args:
        template: 模板配置

    Returns:
        是否为 v1.0 格式
    """
    folders = template.get("folder_structure", {}).get("folders", [])
    for folder in folders:
        subfolders = folder.get("subfolders", [])
        for item in subfolders:
            if isinstance(item, str):
                return True
    return False


def has_legacy_template_paths(template: Dict[str, Any]) -> bool:
    """
    检查模板是否包含旧版路径格式（template_path 以 templates/ 开头）

    Args:
        template: 模板配置

    Returns:
        是否包含旧版路径
    """
    folders = template.get("folder_structure", {}).get("folders", [])
    for folder in folders:
        for item in folder.get("subfolders", []):
            if isinstance(item, dict):
                tp = item.get("template_path", "")
                if isinstance(tp, str) and tp.startswith("templates/"):
                    return True
    return False


def migrate_template_paths(template: Dict[str, Any]) -> Dict[str, Any]:
    """
    迁移旧版模板路径为新版格式

    旧版: template_path = "templates/civil/起诉状.docx"
    新版: template_path = "civil/起诉状.docx"

    Args:
        template: 模板配置

    Returns:
        迁移后的模板配置
    """
    logger = get_logger()
    template = template.copy()
    folders = template.get("folder_structure", {}).get("folders", [])

    migrated = False
    for folder in folders:
        for item in folder.get("subfolders", []):
            if isinstance(item, dict):
                tp = item.get("template_path", "")
                if isinstance(tp, str) and tp.startswith("templates/"):
                    item["template_path"] = tp[len("templates/"):]
                    migrated = True

    if migrated:
        logger.info(f"模板 {template.get('id', 'unknown')} 路径格式已迁移")

    return template

