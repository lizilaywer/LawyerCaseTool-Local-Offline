# -*- coding: utf-8 -*-
"""模板卡片控件模块 - Modern UI v3"""

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.gui.styles import APP_COLORS as COLORS, CATEGORY_COLORS
from src.utils.platform_utils import get_default_ui_font_family


class TemplateCard(QFrame):
    """模板卡片控件 - Modern UI v3"""

    clicked = Signal(str)  # template_id
    edit_clicked = Signal(str)  # template_id
    delete_clicked = Signal(str)  # template_id

    def __init__(
        self,
        template: Dict[str, Any],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._template = template
        self._is_selected = False
        self._setup_ui()
        self._update_style()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        
        self.setFixedHeight(130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 顶部：类别标签和操作按钮
        top_layout = QHBoxLayout()
        top_layout.setSpacing(0)

        category = self._template.get("category", "unknown")
        cat_text, cat_color, chip_bg = CATEGORY_COLORS.get(
            category,
            ("其他", c['text_tertiary'], c['surface_2'])
        )

        # 类别标签（按钮样式，与卡片统一）
        self._category_label = QLabel(cat_text)
        self._category_label.setStyleSheet(f"""
            background-color: {chip_bg};
            color: {cat_color};
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        top_layout.addWidget(self._category_label)
        top_layout.addStretch()

        # 操作按钮容器（默认隐藏，hover时显示）
        self._actions_widget = QWidget()
        self._actions_widget.setStyleSheet("background: transparent; border: none;")
        self._actions_widget.setMinimumHeight(28)
        actions_layout = QHBoxLayout(self._actions_widget)
        actions_layout.setContentsMargins(2, 2, 2, 2)
        actions_layout.setSpacing(2)

        edit_frame = QFrame()
        edit_frame.setFixedSize(24, 24)
        edit_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 6px;
            }}
        """)
        edit_label = QLabel("✎")
        edit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        edit_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 10px; font-weight: bold;")
        ef_layout = QVBoxLayout(edit_frame)
        ef_layout.setContentsMargins(0, 0, 0, 0)
        ef_layout.addWidget(edit_label)
        edit_frame.mousePressEvent = lambda event: self.edit_clicked.emit(self._template["id"])
        actions_layout.addWidget(edit_frame)

        top_layout.addWidget(self._actions_widget)
        layout.addLayout(top_layout)

        # 标题行（包含置顶标记）
        title_layout = QHBoxLayout()
        title_layout.setSpacing(6)
        
        # 置顶标记（默认隐藏，通过 set_pinned 显示）
        self._pin_label = QLabel("📌")
        self._pin_label.setStyleSheet(f"background: transparent; font-size: 12px;")
        self._pin_label.setVisible(False)
        title_layout.addWidget(self._pin_label)
        
        # 标题
        title = QLabel(self._template.get("name", "未命名模板"))
        title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        title.setWordWrap(True)
        title_layout.addWidget(title, 1)
        
        layout.addLayout(title_layout)

        # 描述
        description = self._template.get("description", "")
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"""
                background: transparent;
                color: {c['text_tertiary']};
                font-size: 11px;
                line-height: 1.4;
            """)
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(40)
            layout.addWidget(desc_label)

        layout.addStretch()

        # 底部：统计信息
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(12)

        # 获取文件夹和文件数量
        folder_count = self._count_folders(self._template)
        file_count = self._count_files(self._template)

        meta_text = QLabel(f"{folder_count} 个文件夹 · {file_count} 个文件")
        meta_text.setStyleSheet(f"background: transparent; color: {c['text_muted']}; font-size: 11px;")
        meta_layout.addWidget(meta_text)

        meta_layout.addStretch()
        layout.addLayout(meta_layout)

    def _count_folders(self, template: Dict[str, Any]) -> int:
        """统计文件夹数量"""
        structure = template.get("folder_structure", {})
        folders = structure.get("folders", [])
        return len(folders)

    def _count_files(self, template: Dict[str, Any]) -> int:
        """统计文件数量"""
        structure = template.get("folder_structure", {})
        folders = structure.get("folders", [])
        file_count = 0
        for folder in folders:
            subfolders = folder.get("subfolders", [])
            for item in subfolders:
                if isinstance(item, dict) and item.get("type") == "file":
                    file_count += 1
                elif isinstance(item, str) and "." in item:
                    file_count += 1
        return file_count

    def _update_style(self) -> None:
        """更新样式"""
        c = COLORS
        if self._is_selected:
            self.setStyleSheet(f"""
                TemplateCard {{
                    background-color: {c['accent_subtle']};
                    border: 1px solid {c['accent']};
                    border-radius: 12px;
                }}
            """)
            # 选中时显示操作按钮
            self._actions_widget.setVisible(True)
        else:
            self.setStyleSheet(f"""
                TemplateCard {{
                    background-color: {c['surface_0']};
                    border: 1px solid {c['border']};
                    border-radius: 12px;
                }}
                TemplateCard:hover {{
                    border-color: {c['border_strong']};
                    background-color: {c['surface_0']};
                }}
            """)
            # 未选中时隐藏操作按钮（通过样式控制或父控件控制）
            self._actions_widget.setVisible(False)

    def set_selected(self, selected: bool) -> None:
        """设置选中状态"""
        self._is_selected = selected
        self._update_style()

    def is_selected(self) -> bool:
        """是否选中"""
        return self._is_selected

    def get_template(self) -> Dict[str, Any]:
        """获取模板数据"""
        return self._template

    def get_template_id(self) -> str:
        """获取模板ID"""
        return self._template["id"]

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._template["id"])
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        """鼠标进入事件"""
        self._actions_widget.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """鼠标离开事件"""
        if not self._is_selected:
            self._actions_widget.setVisible(False)
        super().leaveEvent(event)

    def set_pinned(self, pinned: bool) -> None:
        """设置置顶状态
        
        Args:
            pinned: 是否置顶
        """
        if hasattr(self, '_pin_label'):
            self._pin_label.setVisible(pinned)
