# -*- coding: utf-8 -*-
"""跨平台图标工具。"""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle


def get_standard_icon(name: str) -> QIcon:
    """返回系统标准图标，优先保证 Windows/macOS 都稳定显示。"""
    app = QApplication.instance()
    if app is None:
        return QIcon()

    style = app.style()
    file_link_icon = getattr(QStyle.StandardPixmap, "SP_FileLinkIcon", QStyle.StandardPixmap.SP_FileIcon)

    mapping = {
        "folder": QStyle.StandardPixmap.SP_DirIcon,
        "folder_open": QStyle.StandardPixmap.SP_DirOpenIcon,
        "file": QStyle.StandardPixmap.SP_FileIcon,
        "file_link": file_link_icon,
        "trash": QStyle.StandardPixmap.SP_TrashIcon,
        "warning": QStyle.StandardPixmap.SP_MessageBoxWarning,
        "info": QStyle.StandardPixmap.SP_MessageBoxInformation,
    }
    pixmap = mapping.get(name, QStyle.StandardPixmap.SP_FileIcon)
    return style.standardIcon(pixmap)
