# -*- coding: utf-8 -*-
"""透明标签 QFormLayout — 避免 macOS 给 buddy label 绘制高亮底色。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from src.gui.styles import APP_COLORS as COLORS


class TransparentFormLayout(QFormLayout):
    """QFormLayout 子类，自动为字符串标签创建与卡片背景一致的 QLabel，且不设置 buddy。"""

    def addRow(self, label, field=None):
        if field is not None and isinstance(label, str) and label and isinstance(field, QWidget):
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"background: transparent; color: {COLORS['text_primary']}; border: none;"
            )
            lbl.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
            lbl.setAutoFillBackground(False)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            row = self.rowCount()
            self.setWidget(row, QFormLayout.ItemRole.LabelRole, lbl)
            self.setWidget(row, QFormLayout.ItemRole.FieldRole, field)
        else:
            super().addRow(label, field)
