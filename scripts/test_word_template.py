# -*- coding: utf-8 -*-
"""Word 模板功能测试脚本"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.folder_generator import FolderGenerator
from src.core.variable_parser import VariableParser
from src.utils.template_path_manager import get_template_path_manager


def test_template_path_manager():
    """测试模板路径管理器"""
    print("=" * 60)
    print("测试 1: 模板路径管理器")
    print("=" * 60)

    manager = get_template_path_manager()

    print(f"系统模板目录: {manager.get_system_template_dir()}")
    print(f"用户模板目录: {manager.get_user_template_dir()}")

    # 测试路径解析
    test_path = "civil/委托合同.docx"
    resolved = manager.resolve_template_path(test_path)
    print(f"\n解析路径: {test_path}")
    print(f"解析结果: {resolved}")

    # 验证模板路径
    is_valid, error_msg = manager.validate_template_path(test_path)
    print(f"路径验证: {'有效' if is_valid else '无效'}")
    if not is_valid:
        print(f"错误: {error_msg}")

    # 获取可用模板
    templates = manager.get_available_templates("civil")
    print(f"\n可用模板数量: {len(templates)}")
    for template in templates:
        print(f"  - {template['name']}: {template['path']}")

    print()


def test_template_generation():
    """测试模板生成"""
    print("=" * 60)
    print("测试 2: Word 模板生成（模拟）")
    print("=" * 60)

    # 模拟变量值
    values = {
        "client_name": "张三",
        "case_number": "(2024)京01民初123号",
        "case_cause": "合同纠纷",
        "opposing_party": "李四有限公司",
        "court": "北京市第一中级人民法院",
        "lawyer_name": "王律师",
        "receive_date": "2024-01-15"
    }

    print("变量值:")
    for key, value in values.items():
        print(f"  {key}: {value}")

    # 测试变量替换
    parser = VariableParser()
    test_text = '0"{{client_name}}"委托合同.docx'
    result = parser.replace_variables(test_text, values, sanitize=True)
    print(f"\n变量替换测试:")
    print(f"  原始: {test_text}")
    print(f"  结果: {result}")

    print()


def test_folder_generation_structure():
    """测试文件夹生成结构"""
    print("=" * 60)
    print("测试 3: 文件夹结构解析")
    print("=" * 60)

    # 导入默认模板
    from src.config.default_templates import CIVIL_TEMPLATE

    structure = CIVIL_TEMPLATE["folder_structure"]

    print(f"根目录: {structure.get('root_name')}")

    parser = VariableParser()
    values = {
        "case_number": "2024-001",
        "client_name": "张三"
    }

    root_name = parser.replace_variables(structure.get('root_name', ''), values)
    print(f"解析后根目录: {root_name}")

    print("\n文件列表（含模板关联状态）:")
    for folder in structure.get("folders", []):
        print(f"\n[文件夹] {folder.get('name')}")

        for subfolder in folder.get("subfolders", []):
            if isinstance(subfolder, dict) and subfolder.get("type") == "file":
                has_template = subfolder.get("use_template", False)
                template_path = subfolder.get("template_path", "")
                status = "[已关联]" if has_template else "[未关联]"
                print(f"  [文件] {subfolder.get('name')} {status}")
                if has_template:
                    print(f"      模板: {template_path}")

    print()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("律师案卷工具 - Word 模板功能测试")
    print("=" * 60 + "\n")

    try:
        test_template_path_manager()
        test_template_generation()
        test_folder_generation_structure()

        print("=" * 60)
        print("[成功] 所有测试完成！")
        print("=" * 60)

        print("\n[提示]:")
        print("1. 确保已安装 docxtpl: pip install docxtpl")
        print("2. 系统模板目录中需要包含实际的 .docx 文件")
        print("3. 运行主程序测试完整功能: python src/main.py")

    except Exception as e:
        print(f"\n[错误] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
