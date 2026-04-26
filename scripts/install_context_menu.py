# -*- coding: utf-8 -*-
"""安装右键菜单脚本"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.integration.context_menu import (
    install_backup_file_association,
    install_context_menu,
    is_context_menu_installed,
)
from src.config.path_manager import get_path_manager


def main():
    """主函数"""
    print("=" * 50)
    print("案件文件夹管理系统 - 右键菜单安装程序")
    print("=" * 50)

    # 检查管理员权限
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        print("\n错误: 需要管理员权限来安装右键菜单")
        print('请右键点击此脚本，选择"以管理员身份运行"')
        input("\n按回车键退出...")
        return 1

    # 检查是否已安装
    if is_context_menu_installed():
        print("\n右键菜单已安装")
        choice = input("是否重新安装？(y/n): ").strip().lower()
        if choice != 'y':
            print("已取消")
            return 0

    # 获取图标路径
    path_manager = get_path_manager()
    icon_path = path_manager.icons_dir / "app.ico"
    icon_str = str(icon_path) if icon_path.exists() else None

    # 安装
    print("\n正在安装右键菜单...")
    if install_context_menu(icon_str):
        print("\n安装成功!")
        print('现在您可以在任意文件夹右键菜单中看到"在此处新建案件目录"选项')
    else:
        print("\n安装失败!")
        return 1

    print("\n正在安装 .lexora-backup 文件关联...")
    if install_backup_file_association(icon_str):
        print("备份文件关联安装成功，可双击 .lexora-backup 文件导入。")
    else:
        print("备份文件关联安装失败，但右键菜单已安装。")

    input("\n按回车键退出...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
