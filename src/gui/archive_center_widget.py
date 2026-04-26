# -*- coding: utf-8 -*-
"""归档中心 Widget - 作为 App Shell 内嵌页面"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QFileDialog,
    QFrame,
)

from src.gui.icon_utils import get_standard_icon
from src.gui.styles import APP_COLORS as COLORS, button_style


class ArchiveCenterWidget(QWidget):
    """归档中心：先显示文件夹选择界面，选择后内嵌显示归档内容。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._archive_page: Optional[QWidget] = None
        self._setup_ui()

    def _setup_ui(self):
        c = COLORS
        self.setStyleSheet(f"background: {c['surface_1']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { border: none; background: transparent; }")

        # 页面 0: 选择界面
        select_page = self._create_select_page()
        self._stack.addWidget(select_page)

        layout.addWidget(self._stack)

    def _create_select_page(self) -> QWidget:
        c = COLORS
        page = QWidget()
        page.setStyleSheet(f"background: {c['surface_1']};")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)

        # Icon
        icon = QLabel()
        icon.setPixmap(get_standard_icon("folder").pixmap(48, 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        # Title
        title = QLabel("电子化归档")
        title.setStyleSheet(f"color: {c['text_primary']}; font-size: 20px; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("请选择要归档的案卷文件夹")
        subtitle.setStyleSheet(f"color: {c['text_secondary']}; font-size: 14px; font-weight: 500;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Hint
        hint = QLabel("支持对已有案卷文件夹进行归档整理、变量替换和 PDF 预览")
        hint.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px; font-weight: 500;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addSpacing(4)

        # Select button
        btn = QPushButton("选择案卷文件夹")
        btn.setFixedHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(button_style(primary=True))
        btn.clicked.connect(self._on_select_folder)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return page

    def _on_select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择案卷文件夹",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder_path:
            return

        from src.gui.archive_dialog import ArchiveDialog

        dialog = ArchiveDialog(Path(folder_path), self._stack, embed_mode=True)
        dialog.change_folder_requested.connect(self.reset)

        if self._archive_page is not None:
            self._stack.removeWidget(self._archive_page)
            self._archive_page.deleteLater()

        self._archive_page = dialog
        self._stack.addWidget(dialog)
        self._stack.setCurrentIndex(1)

    def reset(self):
        """重置到选择界面"""
        self._stack.setCurrentIndex(0)
