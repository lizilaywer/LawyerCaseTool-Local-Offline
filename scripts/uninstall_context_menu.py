# -*- coding: utf-8 -*-
"""卸载右键菜单脚本"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.integration.context_menu import (
    uninstall_backup_file_association,
    uninstall_context_menu,
    is_context_menu_installed,
)


def main():
    """主函数"""
    print("=" * 50)
    print("案件文件夹管理系统 - 右键菜单卸载程序")
    print("=" * 50)

    # 检查管理员权限
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        print("\n错误: 需要管理员权限来卸载右键菜单")
        print('请右键点击此脚本，选择"以管理员身份运行"')
        input("\n按回车键退出...")
        return 1

    # 检查是否已安装
    if not is_context_menu_installed():
        print("\n右键菜单未安装")
        input("\n按回车键退出...")
        return 0

    # 确认卸载
    choice = input("\n确定要卸载右键菜单吗？(y/n): ").strip().lower()
    if choice != 'y':
        print("已取消")
        return 0

    # 卸载
    print("\n正在卸载右键菜单...")
    if uninstall_context_menu():
        print("\n卸载成功!")
    else:
        print("\n卸载失败!")
        return 1

    print("\n正在卸载 .lexora-backup 文件关联...")
    if uninstall_backup_file_association():
        print("备份文件关联卸载成功。")
    else:
        print("备份文件关联卸载失败，或当前系统不支持。")

    input("\n按回车键退出...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
