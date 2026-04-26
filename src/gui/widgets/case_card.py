# -*- coding: utf-8 -*-
"""案件卡片控件 - Modern UI v3

紧凑型案件列表项，包含分类色条、名称、标签 chips、日期。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QWidget,
)
from PySide6.QtCore import QPoint, QSize, Qt, Signal
from src.gui.styles import APP_COLORS as COLORS

# 分类 → (名称, 颜色) 映射
CATEGORY_STYLE = {
    "civil": ("民事", COLORS['accent']),
    "civil2": ("民事", COLORS['accent']),
    "criminal": ("刑事", COLORS['danger']),
    "administrative": ("行政", COLORS['category_administrative']),
    "non_litigation": ("非诉", COLORS['category_non_litigation']),
    "arbitration": ("仲裁", COLORS['category_arbitration']),
    "labor_arbitration": ("劳动仲裁", COLORS['category_labor_arbitration']),
    "commercial_arbitration": ("商事仲裁", COLORS['category_commercial_arbitration']),
}

# 案件状态 → (显示名, 颜色)
STATUS_STYLE = {
    "active": ("推进中", COLORS['accent']),
    "pending": ("未完结", COLORS['warning']),
    "closed": ("待归档", COLORS['text_muted']),
}


class CaseCard(QFrame):
    """案件卡片控件

    布局（紧凑双行）：
    ┌──┬──────────────────────────────────┐
    │色│  案件名称                          │
    │条│  [标签1] [标签2]        MM-DD更新  │
    └──┴──────────────────────────────────┘
    """

    clicked = Signal(str)  # case_id (legacy)
    selection_requested = Signal(str, int)  # case_id, modifiers
    context_menu_requested = Signal(str, QPoint)

    def __init__(self, case: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._case = case
        self._case_id = case.get("id", "")
        self._is_selected = False
        self._tag_chips: list[QLabel] = []
        self._tag_more_label: Optional[QLabel] = None
        self._deadline_label: Optional[QLabel] = None
        self._deadline_spacer: Optional[QLabel] = None
        self._setup_ui()
        self._update_style()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        self.setMinimumHeight(88)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 6, 10, 6)
        main_layout.setSpacing(8)

        # 左侧分类色条（3px 宽圆角条）
        category = self._case.get("category", "")
        _, cat_color = CATEGORY_STYLE.get(category, ("其他", c['text_muted']))
        self._color_bar = QFrame()
        self._color_bar.setFixedWidth(3)
        self._color_bar.setStyleSheet(f"""
            QFrame {{
                background: {cat_color};
                border: none;
                border-radius: 1px;
            }}
        """)
        main_layout.addWidget(self._color_bar)

        # 右侧内容
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 3, 0, 3)
        self._content_layout.setSpacing(5)

        # 第一行：案件名称
        name = self._case.get("name", "未命名案件")
        name_row = QHBoxLayout()
        name_row.setSpacing(5)
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 状态小标签
        status = self._case.get("status", "active")
        status_text, status_color = STATUS_STYLE.get(status, ("推进中", c['accent']))
        self._status_chip = QLabel(status_text)
        self._status_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_chip.setFixedHeight(18)
        self._status_chip.setStyleSheet(f"""
            background: transparent;
            color: {status_color};
            border: 1px solid {status_color};
            border-radius: 3px;
            padding: 0px 5px;
            font-size: 10px;
            font-weight: 500;
        """)
        self._status_chip.setContentsMargins(0, 0, 0, 0)
        name_row.addWidget(self._status_chip)

        self._name_label = QLabel(name)
        self._name_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 12px;
            font-weight: 600;
        """)
        self._name_label.setWordWrap(True)
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._name_label.setMaximumHeight(54)
        name_row.addWidget(self._name_label, 1)

        self._content_layout.addLayout(name_row)

        # 第二行：标签 chips + 日期
        self._rebuild_bottom_row()

        self._content_layout.addLayout(self._bottom_row)
        main_layout.addWidget(self._content_widget, 1)
        self._apply_compact_layout(max(self.width(), 220))

    def _rebuild_bottom_row(self) -> None:
        """重建底部行（标签、期限提示、日期）。"""
        c = COLORS
        self._tag_chips.clear()
        self._tag_more_label = None
        self._date_label = None

        self._bottom_row = QHBoxLayout()
        self._bottom_row.setSpacing(0)
        self._bottom_row.setContentsMargins(0, 0, 0, 0)

        folder_status = str(self._case.get("folder_status", "available")).strip()
        if folder_status in {"missing", "unlinked"}:
            status_text = "目录缺失" if folder_status == "missing" else "未关联"
            status_color = c['danger'] if folder_status == "missing" else c['warning']
            status_chip = QLabel(status_text)
            status_chip.setStyleSheet(f"""
                background: {c['surface_2']};
                color: {status_color};
                border: 1px solid {status_color};
                border-radius: 3px;
                padding: 1px 6px;
                font-size: 10px;
            """)
            self._bottom_row.addWidget(status_chip)

            spacer = QLabel()
            spacer.setFixedWidth(4)
            spacer.setStyleSheet("background: transparent;")
            self._bottom_row.addWidget(spacer)

        # 标签 chips
        tags = self._case.get("tags", [])
        for tag in tags[:3]:  # 最多显示 3 个
            chip = QLabel(tag)
            chip.setStyleSheet(f"""
                background: {c['surface_2']};
                color: {c['text_secondary']};
                border: none;
                border-radius: 3px;
                padding: 1px 6px;
                font-size: 10px;
            """)
            self._bottom_row.addWidget(chip)
            self._tag_chips.append(chip)
            spacer = QLabel()
            spacer.setFixedWidth(4)
            spacer.setStyleSheet("background: transparent;")
            self._bottom_row.addWidget(spacer)

        if len(tags) > 3:
            more = QLabel(f"+{len(tags) - 3}")
            more.setStyleSheet(f"""
                background: transparent;
                color: {c['text_muted']};
                font-size: 10px;
            """)
            self._tag_more_label = more
            self._bottom_row.addWidget(more)

        self._deadline_spacer = QLabel()
        self._deadline_spacer.setFixedWidth(8)
        self._deadline_spacer.setStyleSheet("background: transparent;")
        self._bottom_row.addWidget(self._deadline_spacer)

        self._deadline_label = QLabel("")
        self._deadline_label.setStyleSheet(f"""
            background: transparent;
            color: {c['danger']};
            font-size: 10px;
            font-weight: 600;
        """)
        self._deadline_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._bottom_row.addWidget(self._deadline_label)

        self._bottom_row.addStretch()

        # 更新日期
        updated = self._case.get("updated_at", "")
        if updated:
            try:
                dt = datetime.fromisoformat(updated)
                date_text = dt.strftime("%m-%d更新")
            except (ValueError, TypeError):
                date_text = ""
        else:
            date_text = ""
        if date_text:
            self._date_label = QLabel(date_text)
            self._date_label.setStyleSheet(f"""
                background: transparent;
                color: {c['text_muted']};
                font-size: 10px;
            """)
            self._bottom_row.addWidget(self._date_label)

    def refresh(self, case: Dict[str, Any]) -> None:
        """刷新卡片内容而不重建整个控件。"""
        self._case = case
        self._case_id = case.get("id", "")

        name = self._case.get("name", "未命名案件")
        self._name_label.setText(name)

        # 更新状态 chip
        status = self._case.get("status", "active")
        status_text, status_color = STATUS_STYLE.get(status, ("推进中", COLORS['accent']))
        self._status_chip.setText(status_text)
        self._status_chip.setStyleSheet(f"""
            background: transparent;
            color: {status_color};
            border: 1px solid {status_color};
            border-radius: 3px;
            padding: 0px 5px;
            font-size: 10px;
            font-weight: 500;
        """)

        # 更新颜色条
        category = self._case.get("category", "")
        _, cat_color = CATEGORY_STYLE.get(category, ("其他", COLORS['text_muted']))
        self._color_bar.setStyleSheet(f"""
            QFrame {{
                background: {cat_color};
                border: none;
                border-radius: 1px;
            }}
        """)

        # 重建底部行
        # 先移除旧的 bottom_row 中的所有 widgets（通过从 content_layout 中移除并重建）
        # 实际上最简单的方式是移除 content_layout 的最后一项（bottom_row），然后重新添加
        # content_layout 目前是 [name_row, bottom_row]
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(1)
            if item.layout():
                # 清理 layout 中的 widgets
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
        self._rebuild_bottom_row()
        self._content_layout.addLayout(self._bottom_row)
        self._apply_compact_layout(max(self.width(), 220))

    def _calculate_card_height(self, width: int) -> int:
        text_width = max(120, width - 84)
        metrics = self._name_label.fontMetrics()
        title_rect = metrics.boundingRect(
            0,
            0,
            text_width,
            200,
            int(Qt.TextFlag.TextWordWrap),
            self._name_label.text(),
        )
        title_height = min(max(title_rect.height(), 34), 54)
        return max(88, min(118, 42 + title_height))

    def _apply_compact_layout(self, width: int) -> None:
        card_height = self._calculate_card_height(width)
        self.setFixedHeight(card_height)
        self._name_label.setMaximumHeight(max(38, card_height - 44))
        self._sync_bottom_row_visibility(width)

    def sizeHint(self) -> QSize:
        return QSize(240, self._calculate_card_height(max(self.width(), 240)))

    def minimumSizeHint(self) -> QSize:
        return QSize(180, self._calculate_card_height(max(self.width(), 180)))

    def _get_deadline_hint(self) -> tuple[str, Optional[int]]:
        """获取最近未完成期限的简短提示和剩余天数。"""
        deadlines = [
            item for item in self._case.get("deadlines", [])
            if item.get("status", "pending") != "completed"
        ]
        if not deadlines:
            return "", None

        today = datetime.now().date()
        best = None
        best_days = None
        for item in deadlines:
            try:
                current_date = datetime.strptime(item.get("date", ""), "%Y-%m-%d").date()
            except (TypeError, ValueError):
                continue
            days = (current_date - today).days
            if best is None or days < best_days:
                best = item
                best_days = days

        if best is None or best_days is None:
            return "", None

        title = str(best.get("title", "期限")).strip() or "期限"
        if best_days < 0:
            return f"逾期{abs(best_days)}天 · {title}", best_days
        if best_days == 0:
            return f"今天到期 · {title}", best_days
        return f"{best_days}天后 · {title}", best_days

    def _sync_bottom_row_visibility(self, width: int) -> None:
        """根据宽度与期限紧急程度协调标签/期限显示优先级。"""
        if not self._deadline_label or not self._deadline_spacer:
            return

        deadline_hint, deadline_days = self._get_deadline_hint()
        show_deadline = bool(deadline_hint)
        compact = width < 250
        urgent_deadline = deadline_days is not None and deadline_days <= 7

        if compact and not urgent_deadline:
            show_deadline = False

        self._deadline_label.setText(deadline_hint if show_deadline else "")
        self._deadline_label.setVisible(show_deadline)

        has_visible_tags = any(chip.isVisible() for chip in self._tag_chips) or (
            self._tag_more_label is not None and self._tag_more_label.isVisible()
        )
        self._deadline_spacer.setVisible(show_deadline and has_visible_tags)

    def _update_style(self) -> None:
        """更新选中样式"""
        c = COLORS
        if self._is_selected:
            self.setStyleSheet(f"""
                CaseCard {{
                    background-color: {c['accent_subtle']};
                    border: 2px solid {c['accent']};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                CaseCard {{
                    background-color: {c['surface_0']};
                    border: 1px solid {c['border']};
                    border-radius: 8px;
                }}
                CaseCard:hover {{
                    border-color: {c['accent']};
                }}
            """)

    def set_selected(self, selected: bool) -> None:
        """设置选中状态"""
        self._is_selected = selected
        self._update_style()

    def is_selected(self) -> bool:
        return self._is_selected

    def get_case_id(self) -> str:
        return self._case_id

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selection_requested.emit(self._case_id, int(event.modifiers().value))
        super().mousePressEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.context_menu_requested.emit(self._case_id, event.globalPos())
        event.accept()

    def resizeEvent(self, event) -> None:
        self._apply_compact_layout(event.size().width())
        super().resizeEvent(event)
