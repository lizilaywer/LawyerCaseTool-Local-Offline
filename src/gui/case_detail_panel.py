# -*- coding: utf-8 -*-
"""案件详情面板"""

from copy import deepcopy
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStyle,
    QStyleOptionTab,
    QStylePainter,
    QTabBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.case_manager import (
    CORE_INFO_FIELD_DEFINITIONS,
    DEFAULT_INFO_SECTION_TITLES,
    FOLDER_STATUS_AVAILABLE,
    FOLDER_STATUS_MISSING,
    FOLDER_STATUS_UNLINKED,
    get_case_manager,
)
from src.core.ocr import format_ocr_setup_message, get_ocr_dependency_status
from src.gui.case_aux_dialogs import DeadlineEditorDialog
from src.gui.styles import APP_COLORS as COLORS, CHECK_ICON_PATH
from src.gui.widgets.archive_file_tree import ArchiveFileTree
from src.gui.widgets.ocr_worker import OcrWorker
from src.gui.widgets.archive_preview import ArchivePreview
from src.gui.widgets.screenshot_tool import ScreenshotTool
from src.utils.logger import get_logger


CATEGORY_STYLE = {
    "civil": ("民事", COLORS["accent"]),
    "civil2": ("民事", COLORS["accent"]),
    "criminal": ("刑事", COLORS["danger"]),
    "administrative": ("行政", "#f59e0b"),
    "non_litigation": ("非诉", "#10b981"),
    "arbitration": ("仲裁", "#8b5cf6"),
    "labor_arbitration": ("劳动仲裁", "#8b5cf6"),
    "commercial_arbitration": ("商事仲裁", "#06b6d4"),
}

STATUS_STYLE = {
    "active": ("推进中", COLORS["accent"]),
    "pending": ("未完结", COLORS["warning"]),
    "closed": ("待归档", COLORS["text_muted"]),
}

FOLDER_STATUS_LABELS = {
    FOLDER_STATUS_AVAILABLE: ("目录正常", COLORS["success"]),
    FOLDER_STATUS_MISSING: ("目录缺失", COLORS["danger"]),
    FOLDER_STATUS_UNLINKED: ("未关联目录", COLORS["warning"]),
}

DEADLINE_TYPE_STYLE = {
    "deadline": ("普通期限", COLORS["danger"]),
    "hearing": ("开庭/庭前", COLORS["accent"]),
    "custom": ("自定义提醒", COLORS["warning"]),
}

PRIORITY_STYLE = {
    "high": ("高优先级", COLORS["danger"]),
    "medium": ("中优先级", COLORS["warning"]),
    "low": ("低优先级", COLORS["success"]),
}

INFO_TYPE_LABELS = {
    "text": "文本",
    "date": "日期",
    "datetime": "日期时间",
    "money": "金额",
    "single_select": "单选",
    "multi_select": "多选",
    "phone": "电话",
    "long_text": "备注",
}

INFO_FIELD_TYPES = [
    ("文本", "text"),
    ("日期", "date"),
    ("日期时间", "datetime"),
    ("金额", "money"),
    ("单选", "single_select"),
    ("多选", "multi_select"),
    ("电话", "phone"),
    ("备注", "long_text"),
]

INFO_SECTION_ORDER = ("basic", "parties", "business", "custom")

INFO_SECTION_BY_KEY = {
    "engagement_date": "basic",
    "fee_status": "business",
    "case_number": "basic",
    "cause_of_action": "basic",
    "party_name": "parties",
    "opponent_name": "parties",
    "entrusted_role": "parties",
    "litigation_role": "parties",
    "handling_lawyer": "business",
    "forum": "business",
    "filing_date": "business",
}

INFO_FIELD_HINTS = {
    "case_number": "已写入案件索引，可直接参与搜索和导出。",
    "cause_of_action": "适合作为筛选和统计维度。",
    "entrusted_role": "委托角色可直接进入统一筛选。",
    "litigation_role": "诉讼地位后续可参与统计和列表筛选。",
    "fee_status": "收费状态建议保持简短，便于统一检索。",
}

INFO_FIELD_VALUE_OPTIONS = {
    "entrusted_role": [
        "原告",
        "被告",
        "第三人",
        "申请人",
        "被申请人",
        "上诉人",
        "被上诉人",
        "犯罪嫌疑人",
        "被告人",
        "被害人",
        "申请执行人",
        "被执行人",
        "债权人",
        "债务人",
        "管理人",
        "其他",
    ],
    "litigation_role": [
        "原告",
        "被告",
        "第三人",
        "申请人",
        "被申请人",
        "上诉人",
        "被上诉人",
        "犯罪嫌疑人",
        "被告人",
        "被害人",
        "申请执行人",
        "被执行人",
        "债权人",
        "债务人",
        "管理人",
        "其他",
    ],
}


class CaseDetailTabBar(QTabBar):
    """案件详情页签栏，支持稳定的期限页签文字高亮。"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._deadline_tab_index = -1
        self._deadline_highlight = False

    def set_deadline_highlight(self, tab_index: int, highlight: bool) -> None:
        self._deadline_tab_index = tab_index
        self._deadline_highlight = bool(highlight)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QStylePainter(self)
        option = QStyleOptionTab()

        for index in range(self.count()):
            self.initStyleOption(option, index)
            text = option.text
            option.text = ""
            painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, option)

            color = QColor(COLORS["text_primary"] if index == self.currentIndex() else COLORS["text_secondary"])
            font = QFont(painter.font())
            font.setPixelSize(11)
            font.setWeight(QFont.Weight.DemiBold if index == self.currentIndex() else QFont.Weight.Medium)

            if index == self._deadline_tab_index and self._deadline_highlight:
                color = QColor(COLORS["danger"])
                font.setWeight(QFont.Weight.Bold)

            text_rect = self.style().subElementRect(QStyle.SubElement.SE_TabBarTabText, option, self)
            painter.save()
            painter.setPen(color)
            painter.setFont(font)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()

        painter.end()


class NotesPreviewTextEdit(QTextEdit):
    """只读笔记预览，支持双击进入编辑。"""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class FloatingNotesDialog(QDialog):
    """悬浮案件笔记窗口。"""

    text_changed = Signal(str)
    return_requested = Signal()
    dialog_closed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._syncing = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        c = COLORS
        self.setWindowTitle("悬浮笔记")
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.resize(500, 620)
        self.setMinimumSize(420, 420)
        self.setStyleSheet(f"QDialog {{ background: {c['surface_0']}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)

        title_wrap = QVBoxLayout()
        title_wrap.setContentsMargins(0, 0, 0, 0)
        title_wrap.setSpacing(2)

        self._case_label = QLabel("悬浮笔记")
        self._case_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 14px;
            font-weight: 800;
        """)
        title_wrap.addWidget(self._case_label)

        self._status_label = QLabel("可边看文件边记录，内容会自动保存到本地记忆。")
        self._status_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
        """)
        title_wrap.addWidget(self._status_label)
        header.addLayout(title_wrap, 1)

        self._btn_return = QPushButton("回归")
        self._btn_return.setFixedHeight(30)
        self._btn_return.clicked.connect(self.return_requested.emit)
        self._btn_return.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_1']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """)
        header.addWidget(self._btn_return)

        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(30)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_1']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
            }}
        """)
        header.addWidget(close_btn)
        layout.addLayout(header)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText("记录案件进展、证据线索、沟通纪要和下一步动作...")
        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.setStyleSheet(f"""
            QTextEdit {{
                background: {c['surface_0']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 14px;
                padding: 16px 18px;
                font-size: 13px;
                line-height: 1.65;
            }}
            QTextEdit:focus {{
                border-color: {c['accent']};
            }}
        """)
        layout.addWidget(self._editor, 1)

    def set_case_name(self, case_name: str) -> None:
        self._case_label.setText(f"悬浮笔记 · {case_name or '未命名案件'}")
        self.setWindowTitle(f"悬浮笔记 - {case_name or '未命名案件'}")

    def set_status_text(self, text: str) -> None:
        self._status_label.setText(text)

    def set_notes_text(self, text: str) -> None:
        next_text = text or ""
        if self._editor.toPlainText() == next_text:
            return
        self._syncing = True
        cursor = self._editor.textCursor()
        self._editor.setPlainText(next_text)
        self._editor.setTextCursor(cursor)
        self._syncing = False

    def focus_editor(self) -> None:
        self._editor.setFocus()

    def _on_text_changed(self) -> None:
        if self._syncing:
            return
        self.text_changed.emit(self._editor.toPlainText())

    def closeEvent(self, event) -> None:
        self.dialog_closed.emit()
        super().closeEvent(event)


class SplitNotesPane(QFrame):
    """双栏模式下的单个笔记面板。"""

    def __init__(
        self,
        pane_title: str,
        export_suffix: str,
        save_callback: Callable[[str], bool],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._pane_title = pane_title
        self._export_suffix = export_suffix
        self._save_callback = save_callback
        self._case_name = ""
        self._dirty = False
        self._editing = False
        self._floating_dialog: Optional[FloatingNotesDialog] = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_now)
        self._setup_ui()
        self.set_notes_text("", mark_saved=True)
        self._set_editing(False)

    def _setup_ui(self) -> None:
        c = COLORS
        self.setObjectName("splitNotesPane")
        self.setStyleSheet(f"""
            QFrame#splitNotesPane {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel(self._pane_title)
        title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 700;
        """)
        header.addWidget(title)

        self._state_label = QLabel("双击正文进入编辑。")
        self._state_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
        """)
        header.addWidget(self._state_label)
        header.addStretch()

        self._hint_chip = QLabel("双击正文进入编辑")
        self._hint_chip.setStyleSheet(f"""
            background: {c['surface_1']};
            color: {c['text_secondary']};
            border: 1px solid {c['border']};
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        header.addWidget(self._hint_chip)

        self._btn_edit = QPushButton("编辑")
        self._btn_edit.setFixedHeight(28)
        self._style_small_button(self._btn_edit)
        self._btn_edit.clicked.connect(self.enter_edit_mode)
        header.addWidget(self._btn_edit)

        self._btn_float = QPushButton("悬浮")
        self._btn_float.setFixedHeight(28)
        self._style_small_button(self._btn_float)
        self._btn_float.clicked.connect(self._toggle_floating)
        header.addWidget(self._btn_float)

        self._btn_export = QPushButton("导出")
        self._btn_export.setFixedHeight(28)
        self._style_small_button(self._btn_export)
        self._btn_export.clicked.connect(self._export_notes)
        header.addWidget(self._btn_export)

        self._btn_finish = QPushButton("完成")
        self._btn_finish.setFixedHeight(28)
        self._style_small_button(self._btn_finish, accent=True)
        self._btn_finish.clicked.connect(self.exit_edit_mode)
        header.addWidget(self._btn_finish)
        layout.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self._toolbar_buttons: List[QPushButton] = []
        for label, fmt in [
            ("B", "bold"),
            ("I", "italic"),
            ("H1", "h1"),
            ("H2", "h2"),
            ("•", "list"),
            (">", "quote"),
            ("日期", "timestamp"),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked=False, value=fmt: self._insert_markdown(value))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c['surface_1']};
                    color: {c['text_secondary']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {c['surface_2']};
                    color: {c['text_primary']};
                }}
            """)
            toolbar.addWidget(btn)
            btn.setVisible(False)
            self._toolbar_buttons.append(btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText(f"记录{self._pane_title}内容…")
        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.setStyleSheet(f"""
            QTextEdit {{
                background: {c['surface_0']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 14px 16px;
                font-size: 13px;
                line-height: 1.6;
            }}
            QTextEdit:focus {{
                border-color: {c['accent']};
            }}
        """)
        layout.addWidget(self._editor, 1)

        self._preview = NotesPreviewTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText(f"双击这里开始记录{self._pane_title}…")
        self._preview.double_clicked.connect(self.enter_edit_mode)
        self._preview.setStyleSheet(f"""
            QTextEdit {{
                background: {c['surface_0']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 16px 18px;
                font-size: 13px;
                line-height: 1.6;
            }}
        """)
        layout.addWidget(self._preview, 1)

    def _style_small_button(self, button: QPushButton, accent: bool = False) -> None:
        c = COLORS
        if accent:
            button.setStyleSheet(f"""
                QPushButton {{
                    background: linear-gradient({c['surface_0']}, {c['accent_subtle']});
                    color: {c['accent']};
                    border: 1px solid {c['accent_light']};
                    border-radius: 10px;
                    padding: 0 12px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {c['accent_subtle']};
                    color: {c['accent_hover']};
                    border-color: {c['accent_light']};
                }}
            """)
            return
        button.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_1']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """)

    def set_case_name(self, case_name: str) -> None:
        self._case_name = case_name or "未命名案件"
        if self._floating_dialog:
            self._floating_dialog.set_case_name(f"{self._case_name} · {self._pane_title}")

    def set_notes_text(self, text: str, *, mark_saved: bool = True) -> None:
        next_text = text or ""
        self._editor.blockSignals(True)
        self._editor.setPlainText(next_text)
        self._editor.blockSignals(False)
        self._refresh_preview()
        if mark_saved:
            self._dirty = False
            self._state_label.setText("双击正文进入编辑。")
        self._sync_floating_dialog(force_text=True)

    def get_notes_text(self) -> str:
        return self._editor.toPlainText()

    def is_editing(self) -> bool:
        return self._editing

    def _set_editing(self, editing: bool) -> None:
        self._editing = editing
        self._editor.setVisible(editing)
        self._preview.setVisible(not editing)
        self._btn_edit.setVisible(not editing)
        self._btn_finish.setVisible(editing)
        self._hint_chip.setVisible(not editing)
        for button in self._toolbar_buttons:
            button.setVisible(editing)
        if editing:
            self._editor.setFocus()

    def enter_edit_mode(self) -> None:
        self._set_editing(True)

    def exit_edit_mode(self) -> None:
        if self._dirty:
            self._save_now()
        self._refresh_preview()
        self._set_editing(False)

    def _refresh_preview(self) -> None:
        content = self._editor.toPlainText()
        if content.strip():
            if hasattr(self._preview, "setMarkdown"):
                self._preview.setMarkdown(content)
            else:
                self._preview.setPlainText(content)
        else:
            self._preview.setHtml(
                f"<div style='color:#94a3b8; line-height:1.8;'>"
                f"双击这里开始记录{self._pane_title}。"
                f"</div>"
            )
        self._sync_floating_dialog()

    def _on_text_changed(self) -> None:
        self._dirty = True
        self._state_label.setText("正在编辑，内容会自动保存。")
        self._refresh_preview()
        self._save_timer.start(800)

    def _save_now(self) -> None:
        if not self._dirty:
            return
        success = self._save_callback(self._editor.toPlainText())
        if success:
            self._dirty = False
            self._state_label.setText("已自动保存到本地记忆。")
            if self._floating_dialog and self._floating_dialog.isVisible():
                self._floating_dialog.set_status_text("已自动保存到本地记忆。")

    def _insert_markdown(self, fmt: str) -> None:
        cursor = self._editor.textCursor()
        selected = cursor.selectedText()
        mappings = {
            "bold": ("**", "**", "粗体文本"),
            "italic": ("*", "*", "斜体文本"),
            "h1": ("# ", "", "一级标题"),
            "h2": ("## ", "", "二级标题"),
            "list": ("- ", "", "列表项"),
            "quote": ("> ", "", "引用文本"),
            "timestamp": ("- ", "", datetime.now().strftime("%Y-%m-%d %H:%M") + " "),
        }
        prefix, suffix, placeholder = mappings.get(fmt, ("", "", ""))
        cursor.insertText(f"{prefix}{selected or placeholder}{suffix}")
        self._editor.setTextCursor(cursor)
        self._editor.setFocus()
        self._dirty = True
        self._refresh_preview()
        self._save_timer.start(800)

    def _export_notes(self) -> None:
        default_name = f"{self._case_name}_{self._export_suffix}.md"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"导出{self._pane_title}",
            default_name,
            "Markdown (*.md);;Text (*.txt)",
        )
        if not file_path:
            return
        try:
            Path(file_path).write_text(self._editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", f"导出{self._pane_title}时出现问题：{exc}")
            return
        QMessageBox.information(self, "导出成功", f"已导出到：{file_path}")

    def _ensure_floating_dialog(self) -> None:
        if self._floating_dialog is not None:
            return
        dialog = FloatingNotesDialog(self)
        dialog.text_changed.connect(self._on_floating_text_changed)
        dialog.return_requested.connect(self._on_return_from_floating)
        dialog.dialog_closed.connect(self._on_floating_dialog_closed)
        self._floating_dialog = dialog

    def _sync_floating_dialog(self, force_text: bool = False) -> None:
        if not self._floating_dialog:
            return
        self._floating_dialog.set_case_name(f"{self._case_name} · {self._pane_title}")
        self._floating_dialog.set_status_text(
            "正在编辑，修改会自动同步保存。" if self._dirty else "可边看文件边记录。"
        )
        if force_text or self._floating_dialog.isVisible():
            self._floating_dialog.set_notes_text(self._editor.toPlainText())

    def _toggle_floating(self) -> None:
        self._ensure_floating_dialog()
        if not self._floating_dialog:
            return
        self._sync_floating_dialog(force_text=True)
        self._floating_dialog.show()
        self._floating_dialog.raise_()
        self._floating_dialog.activateWindow()
        self._floating_dialog.focus_editor()
        self._btn_float.setText("悬浮中")

    def _on_floating_text_changed(self, text: str) -> None:
        if self._editor.toPlainText() == text:
            return
        self._editor.blockSignals(True)
        self._editor.setPlainText(text)
        self._editor.blockSignals(False)
        self._dirty = True
        self._state_label.setText("悬浮笔记已更新，正在同步保存。")
        self._refresh_preview()
        self._save_timer.start(800)

    def _on_return_from_floating(self) -> None:
        if self._floating_dialog:
            self._floating_dialog.close()
        self.enter_edit_mode()

    def _on_floating_dialog_closed(self) -> None:
        self._btn_float.setText("悬浮")
        if self._dirty:
            self._save_now()

    def contains_floating_dialog(self, global_pos: Optional[QPoint]) -> bool:
        if not self._floating_dialog or not self._floating_dialog.isVisible() or global_pos is None:
            return False
        top_left = self._floating_dialog.mapToGlobal(QPoint(0, 0))
        rect = QRect(top_left, self._floating_dialog.size())
        return rect.contains(global_pos)

    def close_floating(self) -> None:
        if self._floating_dialog and self._floating_dialog.isVisible():
            self._floating_dialog.close()
        self._btn_float.setText("悬浮")

    def clear(self) -> None:
        self._save_timer.stop()
        self._editor.blockSignals(True)
        self._editor.clear()
        self._editor.blockSignals(False)
        self._preview.clear()
        self._dirty = False
        self._state_label.setText("双击正文进入编辑。")
        self._set_editing(False)
        self.close_floating()


class SectionTitleLabel(QLabel):
    """分组标题标签，双击后触发改名。"""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class InfoInteractiveFrame(QFrame):
    """信息页可双击进入编辑的容器。"""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class CaseDetailPanel(QWidget):
    """案件详情面板"""

    open_folder_requested = Signal(str)
    archive_requested = Signal(str)
    edit_tags_requested = Signal(str)
    open_file_requested = Signal(Path)
    relink_folder_requested = Signal(str)
    case_refreshed = Signal(str)
    preview_fullscreen_toggled = Signal(bool)
    view_calendar_requested = Signal()
    tool_center_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._logger = get_logger()
        self._case: Optional[Dict[str, Any]] = None
        self._case_id = ""
        self._case_path: Optional[Path] = None
        self._notes_dirty = False
        self._file_tree_expanded = False
        self._notes_editing = False
        self._notes_split_mode = False
        self._floating_notes_dialog: Optional[FloatingNotesDialog] = None
        self._notes_tab_index = -1
        self._info_editing = False
        self._editable_info_fields: List[Dict[str, Any]] = []
        self._info_editor_widgets: Dict[str, Dict[str, Any]] = {}
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._auto_save_notes)
        self._screenshot_tool = ScreenshotTool(self)
        self._screenshot_tool.screenshot_captured.connect(self._on_case_ocr_screenshot_captured)
        self._screenshot_tool.screenshot_cancelled.connect(self._on_case_ocr_cancelled)
        self._case_ocr_worker: Optional[OcrWorker] = None
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._is_preview_fullscreen = False
        self._setup_ui()
        self.clear()

    def _setup_ui(self) -> None:
        c = COLORS
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        container = QWidget()
        container.setStyleSheet(f"background: {c['surface_1']};")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 12, 8, 16)
        container_layout.setSpacing(7)

        self._header = QFrame()
        self._header.setObjectName("detailHeader")
        self._header.setStyleSheet(f"""
            QFrame#detailHeader {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}
        """)
        header_layout = QVBoxLayout(self._header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._name_label = QLabel("选择一个案件查看详情")
        self._name_label.setWordWrap(True)
        self._name_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 16px;
            font-weight: 700;
        """)
        top_row.addWidget(self._name_label, 1)

        self._category_label = QLabel("")
        self._category_label.setVisible(False)
        top_row.addWidget(self._category_label)

        self._date_label = QLabel("")
        self._date_label.setVisible(False)
        self._date_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
        """)
        top_row.addWidget(self._date_label)
        header_layout.addLayout(top_row)

        self._summary_label = QLabel("")
        self._summary_label.setVisible(False)
        self._summary_label.setWordWrap(True)
        self._summary_label.setTextFormat(Qt.TextFormat.RichText)
        self._summary_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_secondary']};
            font-size: 12px;
        """)
        header_layout.addWidget(self._summary_label)

        self._tags_container = QWidget()
        self._tags_layout = QHBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(6)
        header_layout.addWidget(self._tags_container)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self._btn_open_folder = self._make_btn("打开文件夹")
        self._btn_open_folder.clicked.connect(self._on_open_folder)
        button_row.addWidget(self._btn_open_folder)

        self._btn_relink_folder = self._make_btn("重新关联目录")
        self._btn_relink_folder.clicked.connect(self._on_relink_folder)
        button_row.addWidget(self._btn_relink_folder)

        self._btn_archive = self._make_btn("电子化归档")
        self._btn_archive.clicked.connect(self._on_archive)
        button_row.addWidget(self._btn_archive)

        self._btn_edit_tags = self._make_btn("🏷 标签/分类")
        self._btn_edit_tags.clicked.connect(self._on_edit_tags)
        button_row.addWidget(self._btn_edit_tags)

        self._btn_view_calendar = self._make_btn("📅 查看全部期限")
        self._btn_view_calendar.clicked.connect(self._on_view_calendar)
        button_row.addWidget(self._btn_view_calendar)
        button_row.addStretch()

        self._btn_case_ocr = self._make_btn("OCR识别")
        self._btn_case_ocr.clicked.connect(self._on_case_ocr)
        button_row.addWidget(self._btn_case_ocr)

        self._btn_tool_center = self._make_btn("工具中心")
        self._btn_tool_center.clicked.connect(self._on_tool_center)
        button_row.addWidget(self._btn_tool_center)
        header_layout.addLayout(button_row)
        container_layout.addWidget(self._header)

        self._tabs = QTabWidget()
        self._detail_tab_bar = CaseDetailTabBar(self._tabs)
        self._tabs.setTabBar(self._detail_tab_bar)
        self._tabs.setDocumentMode(True)
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {c['border']};
                background: {c['surface_0']};
                border-radius: 10px;
                top: -1px;
            }}
            QTabBar::tab {{
                background: {c['surface_1']};
                border: 1px solid {c['border']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 7px 13px 6px 13px;
                margin-right: 5px;
                margin-top: 2px;
            }}
            QTabBar::tab:hover {{
                background: {c['surface_2']};
                border-color: {c['border_strong']};
            }}
            QTabBar::tab:selected {{
                background: {c['surface_0']};
                font-weight: 600;
            }}
        """)

        self._files_tab = self._create_files_tab()
        self._deadlines_tab = self._create_deadlines_tab()
        self._notes_tab = self._create_notes_tab()
        self._info_tab = self._create_info_tab()

        self._tabs.addTab(self._files_tab, "文件")
        self._tabs.addTab(self._deadlines_tab, "期限")
        self._tabs.addTab(self._notes_tab, "笔记")
        self._tabs.addTab(self._info_tab, "信息")
        self._deadline_tab_index = self._tabs.indexOf(self._deadlines_tab)
        self._deadline_tab_has_pending = False
        self._notes_tab_index = self._tabs.indexOf(self._notes_tab)
        self._tabs.currentChanged.connect(self._refresh_tab_text_colors)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._refresh_tab_text_colors()
        container_layout.addWidget(self._tabs, 1)

        main_layout.addWidget(container)

    def _toggle_preview_fullscreen(self) -> None:
        """切换文件预览全屏模式。"""
        self._is_preview_fullscreen = not self._is_preview_fullscreen

        if self._is_preview_fullscreen:
            self._header.setVisible(False)
            self._tabs.tabBar().setVisible(False)
        else:
            self._header.setVisible(True)
            self._tabs.tabBar().setVisible(True)

        if hasattr(self, "_btn_fullscreen"):
            self._btn_fullscreen.setText("↘↙" if self._is_preview_fullscreen else "⛶")
            self._btn_fullscreen.setToolTip("退出全屏" if self._is_preview_fullscreen else "全屏预览")

        self.preview_fullscreen_toggled.emit(self._is_preview_fullscreen)

    def _on_tab_changed(self, index: int) -> None:
        """切换 Tab 时，若离开文件页且处于全屏，自动退出。"""
        if self._is_preview_fullscreen and index != self._tabs.indexOf(self._files_tab):
            self._toggle_preview_fullscreen()

    def _on_add_to_notes(self, text: str) -> None:
        """将选中的 Word 文档文字追加到案件笔记末尾。"""
        if not text.strip() or self._notes_tab_index < 0:
            return

        # 切换到笔记 Tab
        self._tabs.setCurrentIndex(self._notes_tab_index)

        # 进入编辑模式（如果不在编辑模式）
        if not self._notes_editing:
            self._enter_notes_edit_mode()

        # 根据单栏/双栏模式选择编辑器
        if self._notes_split_mode:
            editor = self._primary_split_notes._editor
        else:
            editor = self._notes_editor

        # 移动光标到末尾
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)

        # 如果已有内容且末尾没有换行，先插入换行
        current_text = editor.toPlainText()
        if current_text and not current_text.endswith("\n"):
            editor.insertPlainText("\n")

        # 插入选中的文本（另起一行）
        editor.insertPlainText(text.strip())
        editor.insertPlainText("\n")
        editor.ensureCursorVisible()

    def _create_files_tab(self) -> QWidget:
        c = COLORS
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("案卷文件与预览")
        title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        header.addWidget(title)

        self._file_summary_label = QLabel("")
        self._file_summary_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
        """)
        header.addWidget(self._file_summary_label)

        self._file_focus_chip = QLabel("工作区")
        self._set_file_focus_chip("工作区")
        header.addWidget(self._file_focus_chip)
        header.addStretch()

        self._btn_toggle_tree = QPushButton("展开树")
        self._btn_toggle_tree.setFixedHeight(28)
        self._style_small_button(self._btn_toggle_tree)
        self._btn_toggle_tree.clicked.connect(self._toggle_file_tree_expansion)

        self._file_actions_group, file_actions_layout = self._create_toolbar_group("fileActionsGroup")
        file_actions_layout.addWidget(self._btn_toggle_tree)
        header.addWidget(self._file_actions_group, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_fullscreen = QPushButton("⛶")
        self._btn_fullscreen.setFixedSize(28, 28)
        self._btn_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_fullscreen.setToolTip("全屏预览")
        self._btn_fullscreen.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['text_muted']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                font-size: 12px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """)
        self._btn_fullscreen.clicked.connect(self._toggle_preview_fullscreen)
        header.addWidget(self._btn_fullscreen)

        layout.addLayout(header)

        self._file_warning_label = QLabel("")
        self._file_warning_label.setWordWrap(True)
        self._file_warning_label.setVisible(False)
        self._file_warning_label.setStyleSheet(f"""
            background: rgba(245, 158, 11, 0.06);
            color: {c['warning']};
            border: 1px solid rgba(245, 158, 11, 0.18);
            border-radius: 10px;
            padding: 9px 11px;
            font-size: 12px;
        """)
        layout.addWidget(self._file_warning_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {c['border']};
                width: 1px;
            }}
        """)

        self._file_tree = ArchiveFileTree()
        # Windows 上大案卷目录递归扫描非常容易卡 UI；案件管理默认按需加载，
        # 用户需要完整树时再点“展开树”主动展开。
        self._file_tree.set_lazy_mode(True)
        self._file_tree.file_clicked.connect(self._on_file_clicked)
        self._file_tree.file_double_clicked.connect(self.open_file_requested.emit)
        self._file_tree.folder_double_clicked.connect(self._on_folder_double_clicked)
        self._file_tree.folder_clicked.connect(self._on_folder_clicked)
        self._file_tree.file_moved.connect(self._on_file_moved)
        self._file_tree.structure_changed.connect(self._on_file_structure_changed)
        splitter.addWidget(self._file_tree)

        self._preview = ArchivePreview()
        self._preview.set_save_actions_enabled(False)
        self._preview.set_empty_hint_text("单击左侧文件立即预览，双击或回车用系统程序打开。")
        self._preview.add_to_notes_requested.connect(self._on_add_to_notes)
        splitter.addWidget(self._preview)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 860])
        layout.addWidget(splitter, 1)
        return tab

    def _create_deadlines_tab(self) -> QWidget:
        c = COLORS
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)

        self._deadline_title = QLabel("期限提醒")
        self._deadline_title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        header.addWidget(self._deadline_title)

        self._deadline_hint_label = QLabel("")
        self._deadline_hint_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
        """)
        header.addWidget(self._deadline_hint_label)
        header.addStretch()

        self._deadline_actions_group, deadline_actions_layout = self._create_toolbar_group("deadlineActionsGroup")
        deadline_actions_layout.setContentsMargins(0, 3, 0, 3)

        self._btn_add_deadline = QPushButton("+ 添加期限")
        self._style_deadline_header_button(self._btn_add_deadline, accent=True)
        self._btn_add_deadline.clicked.connect(self._on_add_deadline)
        deadline_actions_layout.addWidget(self._btn_add_deadline)

        self._btn_export_deadline_log = QPushButton("导出工作日志")
        self._style_deadline_header_button(self._btn_export_deadline_log)
        self._btn_export_deadline_log.clicked.connect(self._on_export_deadline_log)
        deadline_actions_layout.addWidget(self._btn_export_deadline_log)
        header.addWidget(self._deadline_actions_group, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("border: none; background: transparent;")
        self._info_scroll = scroll

        self._deadline_list = QWidget()
        self._deadline_list_layout = QVBoxLayout(self._deadline_list)
        self._deadline_list_layout.setContentsMargins(0, 0, 0, 0)
        self._deadline_list_layout.setSpacing(8)
        self._deadline_list_layout.addStretch()
        scroll.setWidget(self._deadline_list)
        layout.addWidget(scroll, 1)

        self._no_deadline_label = QLabel("暂无期限，点击右上角“添加期限”创建提醒。")
        self._no_deadline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_deadline_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 12px;
            padding: 20px 0;
        """)
        layout.addWidget(self._no_deadline_label)
        return tab

    def _create_notes_tab(self) -> QWidget:
        c = COLORS
        tab = QWidget()
        self._notes_tab = tab
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("案件速记")
        title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        header.addWidget(title)

        self._notes_state_label = QLabel("双击正文进入编辑，Markdown 本地存储。")
        self._notes_state_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
        """)
        header.addWidget(self._notes_state_label)

        self._notes_hint_chip = QLabel("双击正文进入编辑")
        self._style_hint_chip(self._notes_hint_chip)
        header.addWidget(self._notes_hint_chip)
        header.addStretch()

        self._notes_action_group, notes_action_layout = self._create_toolbar_group("notesActionGroup")

        self._btn_edit_notes = QPushButton("编辑")
        self._btn_edit_notes.setFixedHeight(28)
        self._style_small_button(self._btn_edit_notes)
        self._btn_edit_notes.clicked.connect(self._enter_notes_edit_mode)
        notes_action_layout.addWidget(self._btn_edit_notes)

        self._btn_float_notes = QPushButton("悬浮")
        self._btn_float_notes.setFixedHeight(28)
        self._style_small_button(self._btn_float_notes)
        self._btn_float_notes.clicked.connect(self._toggle_floating_notes)
        notes_action_layout.addWidget(self._btn_float_notes)

        self._btn_export_notes = QPushButton("导出")
        self._btn_export_notes.setFixedHeight(28)
        self._style_small_button(self._btn_export_notes)
        self._btn_export_notes.clicked.connect(self._on_export_notes)
        notes_action_layout.addWidget(self._btn_export_notes)

        self._btn_toggle_split_notes = QPushButton("双栏")
        self._btn_toggle_split_notes.setCheckable(True)
        self._btn_toggle_split_notes.setFixedHeight(28)
        self._style_small_button(self._btn_toggle_split_notes)
        self._btn_toggle_split_notes.clicked.connect(self._on_toggle_split_notes)
        notes_action_layout.addWidget(self._btn_toggle_split_notes)

        self._btn_finish_notes = QPushButton("完成")
        self._btn_finish_notes.setFixedHeight(28)
        self._style_small_button(self._btn_finish_notes, accent=True)
        self._btn_finish_notes.clicked.connect(self._exit_notes_edit_mode)
        notes_action_layout.addWidget(self._btn_finish_notes)
        header.addWidget(self._notes_action_group)

        self._notes_format_group, notes_format_layout = self._create_toolbar_group("notesFormatGroup")
        self._notes_toolbar_buttons = []

        for label, fmt in [
            ("B", "bold"),
            ("I", "italic"),
            ("H1", "h1"),
            ("H2", "h2"),
            ("•", "list"),
            (">", "quote"),
            ("日期", "timestamp"),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked=False, value=fmt: self._insert_markdown(value))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c['surface_1']};
                    color: {c['text_secondary']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {c['surface_2']};
                    color: {c['text_primary']};
                }}
            """)
            notes_format_layout.addWidget(btn)
            btn.setVisible(False)
            self._notes_toolbar_buttons.append(btn)
        self._notes_format_group.setVisible(False)
        header.addWidget(self._notes_format_group)
        layout.addLayout(header)

        self._single_notes_container = QWidget()
        single_layout = QVBoxLayout(self._single_notes_container)
        single_layout.setContentsMargins(0, 0, 0, 0)
        single_layout.setSpacing(0)

        self._notes_editor = QTextEdit()
        self._notes_editor.setPlaceholderText("记录案件进展、沟通纪要、证据线索、关键风险与下一步动作...")
        self._notes_editor.textChanged.connect(self._on_notes_changed)
        self._notes_editor.setStyleSheet(f"""
            QTextEdit {{
                background: #ffffff;
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 16px 18px;
                font-size: 13px;
                line-height: 1.6;
            }}
            QTextEdit:focus {{
                border-color: {c['accent']};
            }}
        """)
        self._notes_editor.hide()
        single_layout.addWidget(self._notes_editor, 1)

        self._notes_preview = NotesPreviewTextEdit()
        self._notes_preview.setReadOnly(True)
        self._notes_preview.setPlaceholderText("双击这里开始记录案件笔记…")
        self._notes_preview.double_clicked.connect(self._enter_notes_edit_mode)
        self._notes_preview.setStyleSheet(f"""
            QTextEdit {{
                background: {c['surface_0']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 18px 20px;
                font-size: 13px;
                line-height: 1.6;
            }}
        """)
        single_layout.addWidget(self._notes_preview, 1)
        layout.addWidget(self._single_notes_container, 1)

        self._split_notes_container = QSplitter(Qt.Orientation.Horizontal)
        self._split_notes_container.setChildrenCollapsible(False)
        self._split_notes_container.setStyleSheet(f"""
            QSplitter::handle {{
                background: {c['border']};
                width: 1px;
            }}
        """)
        self._primary_split_notes = SplitNotesPane(
            "主笔记",
            "主笔记",
            lambda text: self._save_split_notes_slot("primary", text),
            self,
        )
        self._secondary_split_notes = SplitNotesPane(
            "副笔记",
            "副笔记",
            lambda text: self._save_split_notes_slot("secondary", text),
            self,
        )
        self._split_notes_container.addWidget(self._primary_split_notes)
        self._split_notes_container.addWidget(self._secondary_split_notes)
        self._split_notes_container.setSizes([1, 1])
        self._split_notes_container.hide()
        layout.addWidget(self._split_notes_container, 1)
        return tab

    def _create_info_tab(self) -> QWidget:
        c = COLORS
        tab = QWidget()
        self._info_tab = tab
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("案件信息")
        title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        header.addWidget(title)

        self._info_summary_label = QLabel("核心字段 + 自定义字段，支持导出与筛选映射。")
        self._info_summary_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
        """)
        header.addWidget(self._info_summary_label)

        self._info_mode_chip = QLabel("双击小卡片即可进入编辑")
        self._style_hint_chip(self._info_mode_chip)
        header.addWidget(self._info_mode_chip)
        header.addStretch()

        self._info_actions_group, info_actions_layout = self._create_toolbar_group("infoActionsGroup")

        self._btn_add_info_field = QPushButton("+ 添加字段")
        self._style_small_button(self._btn_add_info_field)
        self._btn_add_info_field.clicked.connect(self._on_add_info_field)
        self._btn_add_info_field.setVisible(False)
        info_actions_layout.addWidget(self._btn_add_info_field)

        self._btn_cancel_info_edit = QPushButton("取消")
        self._style_small_button(self._btn_cancel_info_edit)
        self._btn_cancel_info_edit.clicked.connect(self._on_cancel_info_edit)
        self._btn_cancel_info_edit.setVisible(False)
        info_actions_layout.addWidget(self._btn_cancel_info_edit)

        self._btn_save_info = QPushButton("保存信息")
        self._style_small_button(self._btn_save_info, accent=True)
        self._btn_save_info.clicked.connect(self._on_save_info_fields)
        self._btn_save_info.setVisible(False)
        info_actions_layout.addWidget(self._btn_save_info)

        self._btn_edit_info = QPushButton("编辑信息")
        self._style_small_button(self._btn_edit_info)
        self._btn_edit_info.clicked.connect(self._on_start_info_edit)
        info_actions_layout.addWidget(self._btn_edit_info)

        self._btn_export_info = QPushButton("导出")
        self._style_small_button(self._btn_export_info)
        self._btn_export_info.clicked.connect(self._on_export_info)
        info_actions_layout.addWidget(self._btn_export_info)
        header.addWidget(self._info_actions_group)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("border: none; background: transparent;")

        self._info_container = QWidget()
        self._info_layout = QVBoxLayout(self._info_container)
        self._info_layout.setContentsMargins(0, 0, 0, 0)
        self._info_layout.setSpacing(12)
        self._info_layout.addStretch()
        scroll.setWidget(self._info_container)
        layout.addWidget(scroll, 1)
        return tab

    def _make_btn(self, text: str) -> QPushButton:
        c = COLORS
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_1']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """)
        return btn

    def _style_small_button(self, button: QPushButton, accent: bool = False) -> None:
        c = COLORS
        if accent:
            button.setStyleSheet(f"""
                QPushButton {{
                    background: linear-gradient({c['surface_0']}, {c['accent_subtle']});
                    color: {c['accent']};
                    border: 1px solid {c['accent_light']};
                    border-radius: 10px;
                    padding: 0 12px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {c['accent_subtle']};
                    color: {c['accent_hover']};
                    border-color: {c['accent_light']};
                }}
                QPushButton:disabled {{
                    background: {c['surface_0']};
                    color: {c['text_muted']};
                    border-color: {c['border']};
                }}
            """)
            return

        button.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_1']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
            QPushButton:disabled {{
                background: {c['surface_0']};
                color: {c['text_muted']};
                border-color: {c['border']};
            }}
        """)

    def _style_deadline_header_button(self, button: QPushButton, accent: bool = False) -> None:
        """期限页头部按钮，优先保证双平台边框完整显示。"""
        c = COLORS
        button.setFixedHeight(30)
        if accent:
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {c['surface_0']};
                    color: {c['accent']};
                    border: 1px solid {c['accent_light']};
                    border-radius: 10px;
                    padding: 0 12px;
                    min-height: 30px;
                    max-height: 30px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {c['accent_subtle']};
                    color: {c['accent_hover']};
                    border-color: {c['accent_light']};
                }}
                QPushButton:disabled {{
                    background: {c['surface_0']};
                    color: {c['text_muted']};
                    border-color: {c['border']};
                }}
            """)
            return

        button.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 12px;
                min-height: 30px;
                max-height: 30px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_1']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
            QPushButton:disabled {{
                background: {c['surface_0']};
                color: {c['text_muted']};
                border-color: {c['border']};
            }}
        """)

    def _create_toolbar_group(self, object_name: str = "detailToolbarGroup") -> Tuple[QFrame, QHBoxLayout]:
        """创建轻量工具条分组容器。"""
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setStyleSheet(f"""
            QFrame#{object_name} {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(6)
        return frame, layout

    def _style_hint_chip(self, label: QLabel, *, accent: bool = False, subtle: bool = False) -> None:
        """统一顶部提示胶囊样式。"""
        if subtle:
            bg = "rgba(248, 250, 252, 0.72)" if not accent else "rgba(219, 234, 254, 0.55)"
            fg = COLORS["accent"] if accent else COLORS["text_muted"]
            border = "rgba(191, 219, 254, 0.8)" if accent else "rgba(226, 232, 240, 0.72)"
            padding_v = "0px"
            padding_h = "8px"
            font_size = "10px"
            font_weight = "500"
        else:
            bg = COLORS["accent_subtle"] if accent else COLORS["surface_1"]
            fg = COLORS["accent"] if accent else COLORS["text_secondary"]
            border = COLORS["accent_light"] if accent else COLORS["border"]
            padding_v = "0px"
            padding_h = "8px"
            font_size = "11px"
            font_weight = "600"
        label.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 999px;
                padding: {padding_v} {padding_h};
                margin: 0px;
                min-height: 0px;
                max-height: 18px;
                font-size: {font_size};
                font-weight: {font_weight};
            }}
        """)

    def _set_file_focus_chip(self, text: str, detail: str = "", *, accent: bool = False) -> None:
        """设置文件页的弱提示胶囊，正文尽量短，详细信息放 tooltip。"""
        self._file_focus_chip.setText(text)
        self._file_focus_chip.setToolTip(f"{text} · {detail}" if detail else text)
        self._style_hint_chip(self._file_focus_chip, accent=accent, subtle=True)

    def load_case(self, case: Dict[str, Any]) -> None:
        if self._notes_dirty:
            self._save_notes_now()
        if self._info_editing:
            self._set_info_editing(False)

        self._case = case
        self._case_id = case.get("id", "")
        case_path = str(case.get("path", "")).strip()
        self._case_path = Path(case_path) if case_path else None
        self._notes_dirty = False
        self._save_timer.stop()

        # 批量更新期间禁用重绘，减少闪烁并提升性能
        self.setUpdatesEnabled(False)
        try:
            self._name_label.setText(case.get("name", "未命名案件"))
            self._update_header_meta()
            self._load_tags()
            self._load_files()
            self._load_deadlines()
            self._load_notes()
            self._load_info_fields()
            self._sync_floating_notes_dialog(force_text=True)
            self._set_controls_enabled(True)
        finally:
            self.setUpdatesEnabled(True)
            # 强制一次刷新，避免 Qt 延迟更新造成视觉残留
            self.repaint()

    def clear(self) -> None:
        if self._notes_dirty:
            self._save_notes_now()
        self._primary_split_notes.exit_edit_mode()
        self._secondary_split_notes.exit_edit_mode()

        self._case = None
        self._case_id = ""
        self._case_path = None
        self._notes_dirty = False
        self._save_timer.stop()

        self._name_label.setText("选择一个案件查看详情")
        self._summary_label.clear()
        self._summary_label.setVisible(False)
        self._category_label.clear()
        self._category_label.setVisible(False)
        self._date_label.clear()
        self._date_label.setVisible(False)
        self._clear_layout(self._tags_layout)
        self._tags_container.setVisible(False)
        self._preview.clear()
        self._file_tree.clear()
        self._file_summary_label.clear()
        self._set_file_focus_chip("工作区")
        self._file_warning_label.clear()
        self._file_warning_label.setVisible(False)
        self._deadline_title.setText("期限提醒")
        self._deadline_hint_label.clear()
        self._clear_layout(self._deadline_list_layout)
        self._deadline_list_layout.addStretch()
        self._no_deadline_label.setVisible(True)
        self._update_deadline_tab_state(0, 0)
        self._notes_editor.blockSignals(True)
        self._notes_editor.clear()
        self._notes_preview.clear()
        self._notes_editor.blockSignals(False)
        self._notes_split_mode = False
        self._primary_split_notes.clear()
        self._secondary_split_notes.clear()
        self._set_notes_editing(False)
        self._sync_notes_mode_ui()
        self._close_floating_notes_dialog()
        self._set_info_editing(False)
        self._clear_layout(self._info_layout)
        self._info_layout.addStretch()
        self._set_controls_enabled(False)

    def _set_controls_enabled(self, enabled: bool) -> None:
        has_case = enabled and bool(self._case_id)
        has_path = has_case and bool(self._case_path and self._case_path.exists())

        self._btn_open_folder.setVisible(has_path)
        folder_status = self._case.get("folder_status", FOLDER_STATUS_UNLINKED) if has_case and self._case else FOLDER_STATUS_UNLINKED
        self._btn_relink_folder.setVisible(has_case and folder_status != FOLDER_STATUS_AVAILABLE)
        self._btn_archive.setVisible(has_path)
        self._btn_edit_tags.setVisible(has_case)
        self._btn_case_ocr.setVisible(has_case)
        self._btn_tool_center.setVisible(has_case)
        self._btn_view_calendar.setVisible(has_case)
        self._btn_add_deadline.setEnabled(has_case)
        self._btn_export_deadline_log.setEnabled(has_case)
        self._btn_toggle_tree.setEnabled(has_path)
        self._btn_edit_info.setEnabled(has_case)
        self._btn_export_info.setEnabled(has_case)
        self._btn_add_info_field.setEnabled(has_case)
        self._btn_cancel_info_edit.setEnabled(has_case)
        self._btn_save_info.setEnabled(has_case)
        self._btn_edit_notes.setEnabled(has_case)
        self._btn_float_notes.setEnabled(has_case)
        self._btn_export_notes.setEnabled(has_case)
        self._btn_toggle_split_notes.setEnabled(has_case)
        self._btn_finish_notes.setEnabled(has_case)
        self._notes_preview.setEnabled(has_case)
        self._notes_editor.setEnabled(has_case)
        self._primary_split_notes.setEnabled(has_case)
        self._secondary_split_notes.setEnabled(has_case)
        self._set_case_ocr_button_enabled(has_case)

        for index in range(self._tabs.count()):
            self._tabs.setTabEnabled(index, has_case)

    def _update_header_meta(self) -> None:
        if not self._case:
            return

        category = self._case.get("category", "")
        cat_text, cat_color = CATEGORY_STYLE.get(category, ("其他", COLORS["text_muted"]))
        self._category_label.setText(cat_text)
        self._category_label.setStyleSheet(f"""
            background: {COLORS['surface_2']};
            color: {cat_color};
            border: none;
            border-radius: 5px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 600;
        """)
        self._category_label.setVisible(True)

        created_text = self._format_datetime(self._case.get("created_at", ""))
        updated_text = self._format_datetime(self._case.get("updated_at", ""))
        if created_text:
            text = f"创建: {created_text}"
            if updated_text and updated_text != created_text:
                text += f"  |  更新: {updated_text}"
            self._date_label.setText(text)
            self._date_label.setVisible(True)
        else:
            self._date_label.clear()
            self._date_label.setVisible(False)

        status_text, _ = STATUS_STYLE.get(self._case.get("status", "active"), ("推进中", COLORS["accent"]))
        folder_status_key = self._case.get("folder_status", FOLDER_STATUS_UNLINKED)
        folder_status_text, _ = FOLDER_STATUS_LABELS.get(folder_status_key, ("未知状态", COLORS["text_muted"]))

        summary_parts = [
            self._format_summary_meta_item(f"状态：{status_text}"),
            self._format_summary_meta_item(f"目录：{folder_status_text}"),
        ]
        if self._case_path:
            summary_parts.append(self._format_summary_meta_item(f"路径：{self._case_path}"))
        if self._case.get("path_history"):
            summary_parts.append(
                self._format_summary_meta_item(f"历史路径：{len(self._case.get('path_history', []))} 条")
            )
        deadlines = self._case.get("deadlines", [])
        pending_deadlines = [
            item for item in deadlines
            if str(item.get("status", "pending")).strip().lower() != "completed"
        ]
        summary_parts.append(
            self._format_deadline_meta_item(
                len(deadlines),
                highlight=bool(pending_deadlines),
            )
        )
        self._summary_label.setText(
            f"""<span style="color:{COLORS['text_secondary']};">{"  |  ".join(summary_parts)}</span>"""
        )
        self._summary_label.setVisible(True)

    def _format_summary_meta_item(self, text: str) -> str:
        """格式化头部摘要普通项。"""
        return escape(str(text or ""))

    def _format_deadline_meta_item(self, count: int, *, highlight: bool) -> str:
        """格式化头部摘要中的期限数量，仅未完成期限存在时高亮。"""
        text = escape(f"期限数量：{count}")
        if count >= 1 and highlight:
            return (
                f"""<span style="color:{COLORS['danger']}; font-weight:700; """
                f"""background-color:#fee2e2;">{text}</span>"""
            )
        return text

    def _refresh_tab_text_colors(self) -> None:
        """刷新页签文字颜色，保持原生页签尺寸。"""
        if not hasattr(self, "_detail_tab_bar"):
            return
        self._detail_tab_bar.set_deadline_highlight(
            self._deadline_tab_index,
            self._deadline_tab_has_pending,
        )

    def _update_deadline_tab_state(self, total_count: int, pending_count: int) -> None:
        """更新期限页签的高亮状态。"""
        if not hasattr(self, "_tabs"):
            return
        self._deadline_tab_has_pending = pending_count >= 1
        self._refresh_tab_text_colors()

    def _load_tags(self) -> None:
        self._clear_layout(self._tags_layout)
        if not self._case:
            self._tags_container.setVisible(False)
            return

        tags = self._case.get("tags", [])
        if not tags:
            empty = QLabel("暂无标签，点击“标签”添加")
            empty.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['text_muted']};
                font-size: 12px;
            """)
            self._tags_layout.addWidget(empty)
            self._tags_layout.addStretch()
            self._tags_container.setVisible(True)
            return

        for tag in tags:
            chip = QLabel(f"#{tag}")
            chip.setStyleSheet(f"""
                background: {COLORS['accent_light']};
                color: {COLORS['accent']};
                border: none;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            """)
            self._tags_layout.addWidget(chip)

        self._tags_layout.addStretch()
        self._tags_container.setVisible(True)

    def _load_files(self) -> None:
        self._file_tree_expanded = False
        self._btn_toggle_tree.setText("展开树")

        current_path = self._case_path if (self._case_path and self._case_path.exists()) else None
        if current_path:
            # 缓存：路径与上次相同时跳过重建，只清理预览和更新摘要
            if getattr(self, "_last_loaded_file_path", None) == current_path:
                self._preview.clear()
                self._file_warning_label.clear()
                self._file_warning_label.setVisible(False)
                self._update_file_summary_default()
                return
            self._last_loaded_file_path = current_path
            self._file_tree.load_folder(current_path)
            self._preview.clear()
            self._file_warning_label.clear()
            self._file_warning_label.setVisible(False)
            self._update_file_summary_default()
        else:
            self._last_loaded_file_path = None
            self._file_tree.clear()
            self._preview.clear()
            self._set_file_focus_chip("目录异常", "当前案件目录不可用")
            self._file_summary_label.setText("当前案件目录不可用，但软件仍保留了案件记录。")
            self._file_warning_label.setText('目录缺失或尚未关联。案件信息、标签、期限和笔记仍保留在本地记忆中，可点击上方"重新关联目录"恢复文件工作区。')
            self._file_warning_label.setVisible(True)
    def _update_file_summary_default(self) -> None:
        if not self._case_path or not self._case_path.exists():
            return
        self._set_file_focus_chip("工作区", self._case_path.name)
        self._file_summary_label.setText(
            "文件按需加载，展开文件夹后可继续浏览；单击预览，双击文件用系统程序打开。"
        )

    def _toggle_file_tree_expansion(self) -> None:
        if self._file_tree_expanded:
            self._file_tree.collapse_all()
            self._btn_toggle_tree.setText("展开树")
            self._file_tree_expanded = False
        else:
            self._file_tree.expand_all()
            self._btn_toggle_tree.setText("收起树")
            self._file_tree_expanded = True

    def _on_file_clicked(self, file_path: Path) -> None:
        if not file_path.exists():
            QMessageBox.warning(self, "文件不存在", f"找不到文件：{file_path}")
            return
        self._set_file_focus_chip("预览中", file_path.name, accent=True)
        self._preview.preview_file(file_path)

    def _on_folder_clicked(self, folder_path: Path) -> None:
        self._set_file_focus_chip("文件夹", folder_path.name)
        self._file_summary_label.setText(f"已选中文件夹：{folder_path.name}")

    def _on_folder_double_clicked(self, folder_path: Path) -> None:
        if not folder_path.exists():
            QMessageBox.warning(self, "目录不存在", f"找不到目录：{folder_path}")
            return
        self.open_folder_requested.emit(str(folder_path))

    def _on_file_moved(self, source_path: Path, target_path: Path) -> None:
        current_preview = self._preview.get_current_file_path()
        if current_preview and current_preview == source_path and target_path.is_file():
            self._preview.preview_file(target_path)
        self._update_file_summary_default()

    def _on_file_structure_changed(self) -> None:
        self._update_file_summary_default()

    def _deadline_target_datetime(self, deadline: Dict[str, Any]) -> Optional[datetime]:
        date_text = str(deadline.get("date", "")).strip()
        if not date_text:
            return None
        try:
            if deadline.get("all_day", True):
                return datetime.strptime(date_text, "%Y-%m-%d")
            time_text = str(deadline.get("time", "")).strip() or "09:00"
            return datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
        except ValueError:
            return None

    def _format_deadline_timestamp(self, deadline: Dict[str, Any]) -> str:
        date_text = str(deadline.get("date", "")).strip()
        if not date_text:
            return "未设置日期"
        if deadline.get("all_day", True):
            return f"{date_text} 全天"
        time_text = str(deadline.get("time", "")).strip() or "09:00"
        return f"{date_text} {time_text}"

    def _load_deadlines(self) -> None:
        self._deadline_list.setUpdatesEnabled(False)
        try:
            self._clear_layout(self._deadline_list_layout)
            self._deadline_list_layout.addStretch()

            if not self._case:
                self._no_deadline_label.setVisible(True)
                self._deadline_title.setText("期限提醒")
                self._deadline_hint_label.clear()
                self._update_deadline_tab_state(0, 0)
                return

            deadlines = self._case.get("deadlines", [])
            if not deadlines:
                self._no_deadline_label.setVisible(True)
                self._deadline_title.setText("期限提醒")
                self._deadline_hint_label.setText("支持时分、全天任务、自然输入和多档提前提醒。")
                self._update_deadline_tab_state(0, 0)
                return

            self._no_deadline_label.setVisible(False)
            pending = [item for item in deadlines if item.get("status", "pending") != "completed"]
            now = datetime.now()
            overdue_count = 0
            for item in pending:
                target = self._deadline_target_datetime(item)
                if target and target < now:
                    overdue_count += 1
            self._deadline_title.setText(f"期限提醒 ({len(deadlines)})")
            self._deadline_hint_label.setText(f"待处理 {len(pending)} 项，已逾期 {overdue_count} 项")
            self._update_deadline_tab_state(len(deadlines), len(pending))

            sorted_deadlines = sorted(deadlines, key=self._deadline_sort_key)
            stretch_item = self._deadline_list_layout.takeAt(self._deadline_list_layout.count() - 1)
            for deadline in sorted_deadlines:
                self._deadline_list_layout.addWidget(self._create_deadline_row(deadline))
            if stretch_item:
                self._deadline_list_layout.addItem(stretch_item)
        finally:
            self._deadline_list.setUpdatesEnabled(True)

    def _deadline_sort_key(self, deadline: Dict[str, Any]) -> Tuple[int, float]:
        if deadline.get("status", "pending") == "completed":
            return (2, float("inf"))
        target = self._deadline_target_datetime(deadline)
        if target is None:
            return (1, float("inf"))
        return (0, target.timestamp())

    def _create_deadline_row(self, deadline: Dict[str, Any]) -> QWidget:
        row = QFrame()
        row.setProperty("caseDeadlineRow", True)
        days_text, accent_color, bg_color = self._get_deadline_badge(deadline)
        row.setStyleSheet(f"""
            QFrame[caseDeadlineRow="true"] {{
                background: {bg_color};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        title = QLabel(deadline.get("title", "未命名期限"))
        title.setStyleSheet(f"""
            background: transparent;
            color: {COLORS['text_primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        top_row.addWidget(title, 1)

        badge = QLabel(days_text)
        badge.setStyleSheet(f"""
            background: transparent;
            color: {accent_color};
            font-size: 12px;
            font-weight: 700;
        """)
        top_row.addWidget(badge)
        layout.addLayout(top_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        for text, color in self._get_deadline_meta(deadline):
            chip = QLabel(text)
            chip.setStyleSheet(f"""
                background: {COLORS['surface_0']};
                color: {color};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 11px;
            """)
            meta_row.addWidget(chip)
        meta_row.addStretch()

        edit_btn = QPushButton("编辑")
        edit_btn.setFixedSize(48, 24)
        self._style_small_button(edit_btn)
        edit_btn.clicked.connect(
            lambda checked=False, deadline_id=deadline.get("id", ""): self._on_edit_deadline(deadline_id)
        )
        meta_row.addWidget(edit_btn)

        status = deadline.get("status", "pending")
        toggle_btn = QPushButton("恢复" if status == "completed" else "完成")
        toggle_btn.setFixedSize(48, 24)
        self._style_small_button(toggle_btn, accent=status != "completed")
        toggle_btn.clicked.connect(
            lambda checked=False, deadline_id=deadline.get("id", ""), completed=status != "completed": self._on_toggle_deadline(deadline_id, completed)
        )
        meta_row.addWidget(toggle_btn)

        del_btn = QPushButton("删除")
        del_btn.setFixedSize(48, 24)
        self._style_small_button(del_btn)
        del_btn.clicked.connect(
            lambda checked=False, deadline_id=deadline.get("id", ""): self._on_remove_deadline(deadline_id)
        )
        meta_row.addWidget(del_btn)
        layout.addLayout(meta_row)

        description = str(deadline.get("description", "")).strip()
        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            desc.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['text_secondary']};
                font-size: 12px;
            """)
            layout.addWidget(desc)

        return row

    def _get_deadline_meta(self, deadline: Dict[str, Any]) -> List[Tuple[str, str]]:
        type_text, type_color = DEADLINE_TYPE_STYLE.get(
            deadline.get("type", "deadline"),
            DEADLINE_TYPE_STYLE["deadline"],
        )
        priority_text, priority_color = PRIORITY_STYLE.get(
            deadline.get("priority", "medium"),
            PRIORITY_STYLE["medium"],
        )
        remind_before = deadline.get("remind_before", [])
        remind_text = "未设置提醒"
        if isinstance(remind_before, list) and remind_before:
            remind_text = "提前 " + "/".join(str(item) for item in remind_before) + " 天"
        status = deadline.get("status", "pending")
        status_text = "已完成" if status == "completed" else "待处理"
        status_color = COLORS["success"] if status == "completed" else COLORS["text_secondary"]

        return [
            (self._format_deadline_timestamp(deadline), COLORS["text_secondary"]),
            (type_text, type_color),
            (priority_text, priority_color),
            (remind_text, COLORS["text_muted"]),
            (status_text, status_color),
        ]

    def _get_deadline_badge(self, deadline: Dict[str, Any]) -> Tuple[str, str, str]:
        if deadline.get("status", "pending") == "completed":
            return ("已完成", COLORS["success"], "rgba(16, 185, 129, 0.08)")

        target = self._deadline_target_datetime(deadline)
        if target is None:
            return ("日期未识别", COLORS["text_muted"], COLORS["surface_1"])

        now = datetime.now()
        if deadline.get("all_day", True):
            delta_days = (target.date() - now.date()).days
            if delta_days < 0:
                return (f"已逾期 {abs(delta_days)} 天", COLORS["danger"], "rgba(239, 68, 68, 0.08)")
            if delta_days == 0:
                return ("今天到期", COLORS["danger"], "rgba(239, 68, 68, 0.08)")
            if delta_days <= 7:
                return (f"{delta_days} 天后到期", COLORS["danger"], "rgba(239, 68, 68, 0.08)")
            if delta_days <= 30:
                return (f"{delta_days} 天后到期", COLORS["warning"], "rgba(245, 158, 11, 0.08)")
            return (f"{delta_days} 天后到期", COLORS["success"], "rgba(16, 185, 129, 0.06)")

        delta_seconds = int((target - now).total_seconds())
        if delta_seconds < 0:
            hours = max(1, abs(delta_seconds) // 3600)
            return (f"已过 {hours} 小时", COLORS["danger"], "rgba(239, 68, 68, 0.08)")
        if delta_seconds < 3600:
            minutes = max(1, delta_seconds // 60)
            return (f"{minutes} 分钟后", COLORS["danger"], "rgba(239, 68, 68, 0.08)")
        if target.date() == now.date():
            return (f"今天 {target.strftime('%H:%M')}", COLORS["danger"], "rgba(239, 68, 68, 0.08)")
        delta_days = (target.date() - now.date()).days
        if delta_days <= 7:
            return (f"{delta_days} 天后 {target.strftime('%H:%M')}", COLORS["danger"], "rgba(239, 68, 68, 0.08)")
        if delta_days <= 30:
            return (f"{delta_days} 天后 {target.strftime('%H:%M')}", COLORS["warning"], "rgba(245, 158, 11, 0.08)")
        return (target.strftime("%m-%d %H:%M"), COLORS["success"], "rgba(16, 185, 129, 0.06)")

    def _on_add_deadline(self) -> None:
        if not self._case_id:
            return

        dialog = DeadlineEditorDialog(parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        data = dialog.get_deadline_data()
        if not data:
            return

        get_case_manager().add_deadline(self._case_id, data)
        self._refresh_case_from_store()

    def _on_export_deadline_log(self) -> None:
        if not self._case_id or not self._case:
            return

        default_name = f"{self._case.get('name', '案件')}_工作日志.md"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出工作日志",
            default_name,
            "Markdown (*.md);;Text (*.txt)",
        )
        if not file_path:
            return

        success = get_case_manager().export_case_work_log(self._case_id, Path(file_path))
        if success:
            QMessageBox.information(self, "导出成功", f"已导出到：{file_path}")
        else:
            QMessageBox.warning(self, "导出失败", "导出工作日志时出现问题。")

    def _on_edit_deadline(self, deadline_id: str) -> None:
        if not self._case_id or not self._case:
            return

        deadline = next(
            (item for item in self._case.get("deadlines", []) if item.get("id") == deadline_id),
            None,
        )
        if not deadline:
            return

        dialog = DeadlineEditorDialog(deadline, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        data = dialog.get_deadline_data()
        if not data:
            return

        if data.get("deleted"):
            get_case_manager().remove_deadline(self._case_id, deadline_id)
            self._refresh_case_from_store()
            return

        get_case_manager().update_deadline(self._case_id, deadline_id, data)
        self._refresh_case_from_store()

    def _on_toggle_deadline(self, deadline_id: str, completed: bool) -> None:
        if not self._case_id:
            return
        updates = {
            "status": "completed" if completed else "pending",
            "completed_at": datetime.now().isoformat() if completed else "",
        }
        get_case_manager().update_deadline(self._case_id, deadline_id, updates)
        self._refresh_case_from_store()

    def _on_remove_deadline(self, deadline_id: str) -> None:
        if not self._case_id:
            return
        get_case_manager().remove_deadline(self._case_id, deadline_id)
        self._refresh_case_from_store()

    def _load_notes(self) -> None:
        if not self._case:
            return

        self._notes_editor.blockSignals(True)
        notes = str(self._case.get("notes", ""))
        self._notes_editor.setPlainText(notes)
        self._notes_editor.blockSignals(False)
        self._notes_dirty = False
        self._refresh_notes_preview()
        self._sync_floating_notes_dialog(force_text=True)
        self._primary_split_notes.set_case_name(self._case.get("name", ""))
        self._secondary_split_notes.set_case_name(self._case.get("name", ""))
        self._primary_split_notes.set_notes_text(notes, mark_saved=True)
        self._secondary_split_notes.set_notes_text(str(self._case.get("notes_secondary", "")), mark_saved=True)
        self._set_notes_editing(False)
        self._set_notes_split_mode(bool(self._case.get("notes_split", False)), persist=False)

    def _refresh_notes_preview(self) -> None:
        content = self._notes_editor.toPlainText()
        if content.strip():
            if hasattr(self._notes_preview, "setMarkdown"):
                self._notes_preview.setMarkdown(content)
            else:
                self._notes_preview.setPlainText(content)
        else:
            self._notes_preview.setHtml(
                "<div style='color:#94a3b8; line-height:1.8;'>"
                "双击这里开始记录案件进展、沟通纪要、证据线索和后续动作。"
                "</div>"
            )
        self._sync_floating_notes_dialog()

    def _save_split_notes_slot(self, slot: str, text: str) -> bool:
        if not self._case_id:
            return False
        success = get_case_manager().update_case_notes(self._case_id, text, slot=slot)
        if success and self._case is not None:
            key = "notes_secondary" if slot == "secondary" else "notes"
            self._case[key] = text
        return success

    def _sync_notes_mode_ui(self) -> None:
        split = self._notes_split_mode
        self._single_notes_container.setVisible(not split)
        self._split_notes_container.setVisible(split)

        self._btn_edit_notes.setVisible(not split and not self._notes_editing)
        self._btn_float_notes.setVisible(not split)
        self._btn_export_notes.setVisible(not split)
        self._btn_finish_notes.setVisible(not split and self._notes_editing)
        self._notes_hint_chip.setVisible(not split and not self._notes_editing)
        self._notes_format_group.setVisible(not split and self._notes_editing)
        for button in getattr(self, "_notes_toolbar_buttons", []):
            button.setVisible(not split and self._notes_editing)

        self._btn_toggle_split_notes.blockSignals(True)
        self._btn_toggle_split_notes.setChecked(split)
        self._btn_toggle_split_notes.blockSignals(False)
        self._style_small_button(self._btn_toggle_split_notes, accent=split)
        self._notes_state_label.setText(
            "双栏模式：左右两栏互不干扰，可分别编辑、导出和悬浮。"
            if split else
            "双击正文进入编辑，Markdown 本地存储。"
        )

    def _set_notes_split_mode(self, enabled: bool, *, persist: bool = True) -> None:
        enabled = bool(enabled)
        if enabled == self._notes_split_mode and persist:
            return

        if enabled:
            if self._notes_dirty:
                self._save_notes_now()
            self._close_floating_notes_dialog()
            primary_text = self._notes_editor.toPlainText()
            secondary_text = str(self._case.get("notes_secondary", "")) if self._case else ""
            self._primary_split_notes.set_notes_text(primary_text, mark_saved=True)
            self._secondary_split_notes.set_notes_text(secondary_text, mark_saved=True)
            self._set_notes_editing(False)
        else:
            self._primary_split_notes.exit_edit_mode()
            self._secondary_split_notes.exit_edit_mode()
            self._primary_split_notes.close_floating()
            self._secondary_split_notes.close_floating()
            self._notes_editor.blockSignals(True)
            self._notes_editor.setPlainText(self._primary_split_notes.get_notes_text())
            self._notes_editor.blockSignals(False)
            self._refresh_notes_preview()

        self._notes_split_mode = enabled
        if self._case is not None:
            self._case["notes_split"] = enabled
        self._sync_notes_mode_ui()

        if persist and self._case_id:
            get_case_manager().update_case(self._case_id, {"notes_split": enabled})

    def _on_toggle_split_notes(self) -> None:
        self._set_notes_split_mode(self._btn_toggle_split_notes.isChecked(), persist=True)

    def _set_notes_editing(self, editing: bool) -> None:
        self._notes_editing = editing
        self._notes_editor.setVisible(editing)
        self._notes_preview.setVisible(not editing)
        if not self._notes_split_mode:
            self._btn_edit_notes.setVisible(not editing)
            self._btn_finish_notes.setVisible(editing)
            self._notes_hint_chip.setVisible(not editing)
            self._btn_float_notes.setVisible(True)
            self._btn_export_notes.setVisible(True)
            for button in getattr(self, "_notes_toolbar_buttons", []):
                button.setVisible(editing)
        if editing:
            self._notes_editor.setFocus()

    def _set_info_editing(self, editing: bool) -> None:
        self._info_editing = editing
        self._editable_info_fields = [] if not editing else self._editable_info_fields
        self._info_editor_widgets = {}
        self._btn_add_info_field.setVisible(editing)
        self._btn_cancel_info_edit.setVisible(editing)
        self._btn_save_info.setVisible(editing)
        self._btn_edit_info.setVisible(not editing)
        self._info_mode_chip.setText("正在页内编辑，点击外部区域会自动保存" if editing else "双击小卡片即可进入编辑")
        self._style_hint_chip(self._info_mode_chip, accent=editing)
        if self._case:
            self._load_info_fields()

    def _on_start_info_edit(self, focus_field_id: str = "") -> None:
        if not self._case_id or not self._case:
            return
        self._editable_info_fields = deepcopy(self._case.get("info_fields", []))
        self._set_info_editing(True)
        if focus_field_id:
            QTimer.singleShot(0, lambda field_id=focus_field_id: self._focus_info_field(field_id))

    def _on_cancel_info_edit(self) -> None:
        if not self._case:
            return
        self._set_info_editing(False)

    def _on_add_info_field(self) -> None:
        if not self._case_id:
            return
        if not self._info_editing:
            self._on_start_info_edit()
        custom_count = sum(1 for field in self._editable_info_fields if not field.get("builtin", False))
        self._editable_info_fields.append({
            "id": f"draft_{datetime.now().strftime('%H%M%S%f')}",
            "key": "",
            "label": f"自定义字段{custom_count + 1}",
            "value": "",
            "type": "text",
            "builtin": False,
            "map_to_tag": False,
        })
        self._load_info_fields()

    def _on_remove_info_field(self, field_id: str) -> None:
        if not field_id:
            return
        self._editable_info_fields = [
            field for field in self._editable_info_fields
            if field.get("id") != field_id or field.get("builtin", False)
        ]
        self._load_info_fields()

    def _make_info_input(self, placeholder: str = "") -> QLineEdit:
        input_widget = QLineEdit()
        input_widget.setPlaceholderText(placeholder)
        input_widget.setMinimumHeight(34)
        input_widget.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['surface_0']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 0 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent']};
                background: #ffffff;
            }}
        """)
        return input_widget

    def _make_info_textarea(self, placeholder: str = "") -> QTextEdit:
        input_widget = QTextEdit()
        input_widget.setPlaceholderText(placeholder)
        input_widget.setMinimumHeight(84)
        input_widget.setMaximumHeight(120)
        input_widget.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['surface_0']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 12px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {COLORS['accent']};
                background: #ffffff;
            }}
        """)
        return input_widget

    def _make_info_combo(self, items: List[str]) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setMinimumHeight(34)
        if items:
            combo.addItems(items)
        combo.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['surface_0']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 0 10px;
                font-size: 12px;
            }}
            QComboBox:focus {{
                border-color: {COLORS['accent']};
                background: #ffffff;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        return combo

    def _make_info_checkbox(self, text: str) -> QCheckBox:
        checkbox = QCheckBox(text)
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                background: transparent;
                color: {COLORS['text_secondary']};
                font-size: 11px;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {COLORS['border_strong']};
                border-radius: 5px;
                background: {COLORS['surface_0']};
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['accent']};
                border-color: {COLORS['accent']};
                image: url({CHECK_ICON_PATH});
            }}
        """)
        return checkbox

    def _get_info_field_placeholder(self, field: Dict[str, Any]) -> str:
        field_type = str(field.get("type", "text")).strip() or "text"
        placeholder_map = {
            "date": "例如：2026-04-04",
            "datetime": "例如：2026-04-04 09:30",
            "money": "例如：5000 元 / 已支付一半",
            "phone": "例如：13800000000",
            "single_select": "可直接输入或选择",
            "multi_select": "多个值可用 / 或 、 分隔",
            "long_text": "补充更完整的说明、备注或补充事实…",
        }
        return placeholder_map.get(field_type, "请输入字段内容")

    def _read_info_value_widget(self, widget: QWidget) -> str:
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        return ""

    def _collect_inline_info_fields(self) -> Optional[List[Dict[str, Any]]]:
        collected_fields: List[Dict[str, Any]] = []

        for field in self._editable_info_fields:
            field_id = str(field.get("id", "")).strip()
            widgets = self._info_editor_widgets.get(field_id, {})
            if not widgets:
                collected_fields.append(dict(field))
                continue

            label_widget = widgets.get("label")
            value_widget = widgets.get("value")
            type_widget = widgets.get("type")
            tag_widget = widgets.get("map_to_tag")

            label = field.get("label", "")
            if isinstance(label_widget, QLineEdit):
                label = label_widget.text().strip()
            label = str(label or "").strip()

            value = self._read_info_value_widget(value_widget) if isinstance(value_widget, QWidget) else ""
            field_type = field.get("type", "text")
            if isinstance(type_widget, QComboBox):
                field_type = type_widget.currentData() or type_widget.currentText().strip() or field_type
            field_type = str(field_type or "text").strip() or "text"
            map_to_tag = bool(tag_widget.isChecked()) if isinstance(tag_widget, QCheckBox) else bool(field.get("map_to_tag", False))

            if field.get("builtin", False):
                label = field.get("label", "")
            elif not label and not value:
                continue
            elif not label:
                QMessageBox.information(self, "字段名称不能为空", "请先填写自定义字段名称，再保存信息。")
                if isinstance(label_widget, QLineEdit):
                    label_widget.setFocus()
                return None

            updated_field = dict(field)
            updated_field["label"] = label
            updated_field["value"] = value
            updated_field["type"] = field_type
            updated_field["map_to_tag"] = map_to_tag
            collected_fields.append(updated_field)

        return collected_fields

    def _on_save_info_fields(self) -> None:
        if not self._case_id:
            return

        fields = self._collect_inline_info_fields()
        if fields is None:
            return

        if not get_case_manager().update_info_fields(self._case_id, fields):
            QMessageBox.warning(self, "保存失败", "保存案件信息时出现问题。")
            return

        self._set_info_editing(False)
        self._refresh_case_from_store()

    def _create_info_field_editor_row(self, field: Dict[str, Any]) -> QWidget:
        row = QFrame()
        row.setObjectName("infoFieldEditorRow")
        row.setStyleSheet(f"""
            QFrame#infoFieldEditorRow {{
                background: rgba(248, 250, 252, 0.96);
                border: none;
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(row)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        label_widget: Optional[QLineEdit] = None
        if field.get("builtin", False):
            title = QLabel(field.get("label", "未命名字段"))
            title.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['text_primary']};
                font-size: 13px;
                font-weight: 700;
            """)
            top_row.addWidget(title, 1)
        else:
            label_widget = self._make_info_input("字段名称")
            label_widget.setText(str(field.get("label", "")))
            top_row.addWidget(label_widget, 1)

        type_widget: Optional[QComboBox] = None
        if field.get("builtin", False):
            type_chip = QLabel(INFO_TYPE_LABELS.get(field.get("type", "text"), "文本"))
            type_chip.setStyleSheet(f"""
                background: {COLORS['surface_1']};
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            """)
            top_row.addWidget(type_chip)
        else:
            type_widget = self._make_info_combo([])
            type_widget.clear()
            for label, value in INFO_FIELD_TYPES:
                type_widget.addItem(label, value)
            current_type = str(field.get("type", "text")).strip() or "text"
            index = type_widget.findData(current_type)
            type_widget.setCurrentIndex(index if index >= 0 else 0)
            top_row.addWidget(type_widget)

            remove_btn = QPushButton("删除")
            self._style_small_button(remove_btn)
            remove_btn.clicked.connect(
                lambda checked=False, field_id=field.get("id", ""): self._on_remove_info_field(field_id)
            )
            top_row.addWidget(remove_btn)

        layout.addLayout(top_row)

        field_key = str(field.get("key", "")).strip()
        field_type = str(field.get("type", "text")).strip() or "text"
        value_options = INFO_FIELD_VALUE_OPTIONS.get(field_key, [])
        if field_type == "long_text":
            value_widget: QWidget = self._make_info_textarea(self._get_info_field_placeholder(field))
            value_widget.setPlainText(str(field.get("value", "")))
        elif value_options:
            combo = self._make_info_combo(value_options)
            combo.setCurrentText(str(field.get("value", "")))
            value_widget = combo
        else:
            value_widget = self._make_info_input(self._get_info_field_placeholder(field))
            value_widget.setText(str(field.get("value", "")))
        layout.addWidget(value_widget)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        map_checkbox = self._make_info_checkbox("映射为筛选标签")
        map_checkbox.setChecked(bool(field.get("map_to_tag", False)))
        bottom_row.addWidget(map_checkbox)

        hint_text = self._get_info_field_hint(field)
        if hint_text:
            hint = QLabel(hint_text)
            hint.setWordWrap(True)
            hint.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['text_muted']};
                font-size: 11px;
            """)
            bottom_row.addWidget(hint, 1)
        else:
            bottom_row.addStretch()
        layout.addLayout(bottom_row)

        self._info_editor_widgets[str(field.get("id", ""))] = {
            "label": label_widget,
            "value": value_widget,
            "type": type_widget,
            "map_to_tag": map_checkbox,
        }
        return row

    def _enter_notes_edit_mode(self) -> None:
        if not self._case_id:
            return
        if self._notes_split_mode:
            self._primary_split_notes.enter_edit_mode()
            return
        self._set_notes_editing(True)

    def _exit_notes_edit_mode(self) -> None:
        if self._notes_split_mode:
            self._primary_split_notes.exit_edit_mode()
            self._secondary_split_notes.exit_edit_mode()
            return
        if self._notes_dirty:
            self._save_notes_now()
        self._refresh_notes_preview()
        self._set_notes_editing(False)

    def _on_notes_changed(self) -> None:
        self._notes_dirty = True
        self._refresh_notes_preview()
        self._save_timer.start(800)

    def _auto_save_notes(self) -> None:
        self._save_notes_now()

    def _save_notes_now(self) -> None:
        if not self._notes_dirty or not self._case_id:
            return
        success = get_case_manager().update_case_notes(self._case_id, self._notes_editor.toPlainText(), slot="primary")
        if success:
            self._notes_dirty = False
            if self._case is not None:
                self._case["notes"] = self._notes_editor.toPlainText()
            self._notes_state_label.setText("已自动保存到本地记忆与案件侧边文件。")
            if self._floating_notes_dialog and self._floating_notes_dialog.isVisible():
                self._floating_notes_dialog.set_status_text("已自动保存到本地记忆与案件侧边文件。")

    def _on_export_notes(self) -> None:
        if not self._case_id or not self._case:
            return
        if self._notes_split_mode:
            self._primary_split_notes._export_notes()
            return

        default_name = f"{self._case.get('name', '案件笔记')}_笔记.md"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出案件笔记",
            default_name,
            "Markdown (*.md);;Text (*.txt)",
        )
        if not file_path:
            return

        try:
            Path(file_path).write_text(self._notes_editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", f"导出案件笔记时出现问题：{exc}")
            return

        QMessageBox.information(self, "导出成功", f"已导出到：{file_path}")

    def _insert_markdown(self, fmt: str) -> None:
        if self._notes_split_mode:
            self._primary_split_notes._insert_markdown(fmt)
            return
        cursor = self._notes_editor.textCursor()
        selected = cursor.selectedText()
        mappings = {
            "bold": ("**", "**", "粗体文本"),
            "italic": ("*", "*", "斜体文本"),
            "h1": ("# ", "", "一级标题"),
            "h2": ("## ", "", "二级标题"),
            "list": ("- ", "", "列表项"),
            "quote": ("> ", "", "引用文本"),
            "timestamp": ("- ", "", datetime.now().strftime("%Y-%m-%d %H:%M") + " "),
        }
        prefix, suffix, placeholder = mappings.get(fmt, ("", "", ""))
        insert_text = f"{prefix}{selected or placeholder}{suffix}"
        cursor.insertText(insert_text)
        self._notes_editor.setTextCursor(cursor)
        self._notes_editor.setFocus()
        self._notes_dirty = True
        self._refresh_notes_preview()
        self._save_timer.start(800)

    def _toggle_floating_notes(self) -> None:
        if not self._case_id:
            return
        if self._notes_split_mode:
            self._primary_split_notes._toggle_floating()
            return

        if self._floating_notes_dialog and self._floating_notes_dialog.isVisible():
            self._floating_notes_dialog.raise_()
            self._floating_notes_dialog.activateWindow()
            self._floating_notes_dialog.focus_editor()
            return

        self._ensure_floating_notes_dialog()
        if not self._floating_notes_dialog:
            return

        self._sync_floating_notes_dialog(force_text=True)
        self._floating_notes_dialog.show()
        self._floating_notes_dialog.raise_()
        self._floating_notes_dialog.activateWindow()
        self._floating_notes_dialog.focus_editor()
        self._btn_float_notes.setText("悬浮中")

    def _ensure_floating_notes_dialog(self) -> None:
        if self._floating_notes_dialog is not None:
            return

        dialog = FloatingNotesDialog(self)
        dialog.text_changed.connect(self._on_floating_notes_text_changed)
        dialog.return_requested.connect(self._on_return_from_floating_notes)
        dialog.dialog_closed.connect(self._on_floating_notes_dialog_closed)
        self._floating_notes_dialog = dialog

    def _sync_floating_notes_dialog(self, force_text: bool = False) -> None:
        if not self._floating_notes_dialog:
            return

        case_name = self._case.get("name", "") if self._case else ""
        self._floating_notes_dialog.set_case_name(case_name)
        if self._notes_dirty:
            status_text = "正在编辑，修改会自动同步回主笔记并保存。"
        else:
            status_text = "可边看文件边记录，内容会自动保存到本地记忆。"
        self._floating_notes_dialog.set_status_text(status_text)
        if force_text or self._floating_notes_dialog.isVisible():
            self._floating_notes_dialog.set_notes_text(self._notes_editor.toPlainText())

    def _on_floating_notes_text_changed(self, text: str) -> None:
        if not self._case_id:
            return
        if self._notes_editor.toPlainText() == text:
            return

        self._notes_editor.blockSignals(True)
        self._notes_editor.setPlainText(text)
        self._notes_editor.blockSignals(False)
        self._notes_dirty = True
        self._notes_state_label.setText("悬浮笔记已更新，正在同步保存到本地记忆。")
        self._refresh_notes_preview()
        self._save_timer.start(800)

    def _on_return_from_floating_notes(self) -> None:
        if self._floating_notes_dialog:
            self._floating_notes_dialog.close()
        if self._notes_tab_index >= 0:
            self._tabs.setCurrentIndex(self._notes_tab_index)
        self._enter_notes_edit_mode()

    def _on_floating_notes_dialog_closed(self) -> None:
        self._btn_float_notes.setText("悬浮")
        if self._notes_dirty:
            self._save_notes_now()

    def _close_floating_notes_dialog(self) -> None:
        if self._floating_notes_dialog and self._floating_notes_dialog.isVisible():
            self._floating_notes_dialog.close()
        self._btn_float_notes.setText("悬浮")

    def _extract_global_pos(self, event) -> Optional[QPoint]:
        if hasattr(event, "globalPosition"):
            try:
                return event.globalPosition().toPoint()
            except Exception:
                pass
        if hasattr(event, "globalPos"):
            try:
                return event.globalPos()
            except Exception:
                pass
        return None

    def _widget_contains_global_pos(self, widget: Optional[QWidget], global_pos: Optional[QPoint]) -> bool:
        if widget is None or global_pos is None or not widget.isVisible():
            return False
        top_left = widget.mapToGlobal(QPoint(0, 0))
        rect = QRect(top_left, widget.size())
        return rect.contains(global_pos)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            global_pos = self._extract_global_pos(event)
            if global_pos is None:
                return super().eventFilter(watched, event)

            if self._notes_split_mode:
                in_notes_tab = self._widget_contains_global_pos(getattr(self, "_notes_tab", None), global_pos)
                in_split_floating = (
                    self._primary_split_notes.contains_floating_dialog(global_pos)
                    or self._secondary_split_notes.contains_floating_dialog(global_pos)
                )
                if not in_notes_tab and not in_split_floating:
                    self._exit_notes_edit_mode()
            elif self._notes_editing:
                in_notes_tab = self._widget_contains_global_pos(getattr(self, "_notes_tab", None), global_pos)
                in_floating_dialog = self._widget_contains_global_pos(self._floating_notes_dialog, global_pos)
                if not in_notes_tab and not in_floating_dialog:
                    self._exit_notes_edit_mode()

            if self._info_editing:
                in_info_tab = self._widget_contains_global_pos(getattr(self, "_info_tab", None), global_pos)
                if not in_info_tab:
                    self._on_save_info_fields()

        return super().eventFilter(watched, event)

    def _load_info_fields(self) -> None:
        if hasattr(self, "_info_scroll"):
            self._info_scroll.setUpdatesEnabled(False)
        try:
            self._clear_layout(self._info_layout)
            if not self._case:
                self._info_layout.addStretch()
                return

            self._info_editor_widgets = {}
            info_fields = self._editable_info_fields if self._info_editing else self._case.get("info_fields", [])
            section_titles = self._case.get("info_section_titles", DEFAULT_INFO_SECTION_TITLES)
            if self._info_editing:
                self._info_summary_label.setText(
                    f"正在页内编辑 {len(info_fields)} 个字段，可直接修改、添加自定义字段并保存。"
                )
                self._info_mode_chip.setText("正在页内编辑，点击外部区域会自动保存")
                self._style_hint_chip(self._info_mode_chip, accent=True)
            else:
                self._info_summary_label.setText(
                    f"共 {len(info_fields)} 个字段，支持分类标题改名、逐项转标签与本地导出。"
                )
                self._info_mode_chip.setText("双击小卡片即可进入编辑")
                self._style_hint_chip(self._info_mode_chip)

            grouped_fields = {key: [] for key in INFO_SECTION_ORDER}
            for field in info_fields:
                section_key = INFO_SECTION_BY_KEY.get(field.get("key", ""), "custom")
                if not field.get("builtin", False):
                    section_key = "custom"
                grouped_fields.setdefault(section_key, []).append(field)

            columns_widget = QWidget()
            columns_layout = QHBoxLayout(columns_widget)
            columns_layout.setContentsMargins(0, 0, 0, 0)
            columns_layout.setSpacing(12)

            left_column = QWidget()
            left_layout = QVBoxLayout(left_column)
            left_layout.setContentsMargins(0, 0, 0, 0)
            left_layout.setSpacing(12)

            right_column = QWidget()
            right_layout = QVBoxLayout(right_column)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(12)

            for section_key in ("basic", "business"):
                left_layout.addWidget(
                    self._create_info_section_card(
                        section_key,
                        section_titles.get(section_key, DEFAULT_INFO_SECTION_TITLES[section_key]),
                        grouped_fields.get(section_key, []),
                    )
                )
            left_layout.addStretch()

            for section_key in ("parties", "custom"):
                right_layout.addWidget(
                    self._create_info_section_card(
                        section_key,
                        section_titles.get(section_key, DEFAULT_INFO_SECTION_TITLES[section_key]),
                        grouped_fields.get(section_key, []),
                    )
                )
            right_layout.addStretch()

            columns_layout.addWidget(left_column, 1)
            columns_layout.addWidget(right_column, 1)

            self._info_layout.addWidget(columns_widget)
            self._info_layout.addWidget(self._create_system_info_card())
            self._info_layout.addStretch()
        finally:
            if hasattr(self, "_info_scroll"):
                self._info_scroll.setUpdatesEnabled(True)

    def _focus_info_field(self, field_id: str) -> None:
        """在页内编辑状态下聚焦到指定字段。"""
        widgets = self._info_editor_widgets.get(field_id, {})
        target = widgets.get("value") or widgets.get("label")
        if not isinstance(target, QWidget):
            return
        target.setFocus()
        if hasattr(self, "_info_scroll"):
            self._info_scroll.ensureWidgetVisible(target, 0, 36)

    def _create_info_section_card(
        self,
        section_key: str,
        title_text: str,
        fields: List[Dict[str, Any]],
    ) -> QWidget:
        card = InfoInteractiveFrame()
        card.setObjectName("infoSectionCard")
        card.setStyleSheet(f"""
            QFrame#infoSectionCard {{
                background: {COLORS['surface_0']};
                border: 1px solid rgba(226, 232, 240, 0.78);
                border-radius: 16px;
            }}
        """)
        if not self._info_editing:
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.double_clicked.connect(self._on_start_info_edit)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        title = SectionTitleLabel(title_text)
        title.double_clicked.connect(
            lambda current_key=section_key, current_title=title_text: self._on_rename_info_section(
                current_key,
                current_title,
            )
        )
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setStyleSheet(f"""
            background: transparent;
            color: {COLORS['text_primary']};
            font-size: 13px;
            font-weight: 800;
            padding: 0;
        """)
        top_row.addWidget(title)

        top_row.addStretch()

        tip_text = "双击标题可改名" if section_key == "basic" else "每项都能映射标签"
        if section_key == "parties":
            tip_text = "支持自定义分类名称"
        elif section_key == "custom":
            tip_text = "可继续增减内容"
        tip = QLabel(tip_text)
        self._style_hint_chip(tip)
        top_row.addWidget(tip)
        layout.addLayout(top_row)

        if fields:
            for field in fields:
                if self._info_editing:
                    layout.addWidget(self._create_info_field_editor_row(field))
                else:
                    layout.addWidget(self._create_info_field_row(field))
        else:
            empty = QLabel("当前分组暂无字段，可在当前页面直接补充。")
            empty.setStyleSheet(f"""
                background: {COLORS['surface_1']};
                color: {COLORS['text_muted']};
                border: none;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 12px;
                line-height: 1.55;
            """)
            layout.addWidget(empty)

        return card

    def _create_info_field_row(self, field: Dict[str, Any]) -> QWidget:
        row = InfoInteractiveFrame()
        row.setObjectName("infoFieldRow")
        row.setStyleSheet(f"""
            QFrame#infoFieldRow {{
                background: rgba(248, 250, 252, 0.94);
                border: none;
                border-radius: 12px;
            }}
            QFrame#infoFieldRow:hover {{
                background: rgba(241, 245, 249, 0.98);
            }}
        """)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.double_clicked.connect(
            lambda field_id=str(field.get("id", "")).strip(): self._on_start_info_edit(field_id)
        )

        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 13, 14, 13)
        layout.setSpacing(12)

        main = QWidget()
        main.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        title = QLabel(field.get("label", "未命名字段"))
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        title.setStyleSheet(f"""
            background: transparent;
            color: {COLORS['text_muted']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """)
        main_layout.addWidget(title)

        value = str(field.get("value", "")).strip() or "未填写"
        value_label = QLabel(value)
        value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value_label.setStyleSheet(f"""
            background: transparent;
            color: {COLORS['text_secondary'] if value == '未填写' else COLORS['text_primary']};
            font-size: 14px;
            font-weight: 700;
            line-height: 1.45;
        """)
        main_layout.addWidget(value_label)

        hint_text = self._get_info_field_hint(field)
        if hint_text:
            hint = QLabel(hint_text)
            hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            hint.setWordWrap(True)
            hint.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['text_muted']};
                font-size: 11px;
                line-height: 1.45;
            """)
            main_layout.addWidget(hint)

        toggle_btn = QPushButton("取消标签" if field.get("map_to_tag") else "转为标签")
        toggle_btn.setEnabled(bool(str(field.get("value", "")).strip()))
        toggle_btn.clicked.connect(
            lambda checked=False, field_id=field.get("id", ""): self._on_toggle_info_field_tag(field_id)
        )
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface_0']};
                color: {COLORS['accent'] if field.get('map_to_tag') else COLORS['text_secondary']};
                border: 1px solid {COLORS['accent_light'] if field.get('map_to_tag') else '#dbe3ef'};
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_subtle'] if field.get('map_to_tag') else COLORS['surface_2']};
                color: {COLORS['accent'] if field.get('map_to_tag') else COLORS['text_primary']};
            }}
            QPushButton:disabled {{
                background: {COLORS['surface_0']};
                color: {COLORS['text_muted']};
                border-color: {COLORS['border']};
            }}
        """)

        layout.addWidget(main, 1)
        layout.addWidget(toggle_btn, 0, Qt.AlignmentFlag.AlignTop)
        return row

    def _create_system_info_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("memoryCard")
        card.setStyleSheet(f"""
            QFrame#memoryCard {{
                background: {COLORS['surface_0']};
                border: 1px solid rgba(226, 232, 240, 0.78);
                border-radius: 16px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("本地记忆状态")
        title.setStyleSheet(f"""
            background: transparent;
            color: {COLORS['text_primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        layout.addWidget(title)

        if not self._case:
            return card

        folder_status_key = self._case.get("folder_status", FOLDER_STATUS_UNLINKED)
        folder_status_text, _ = FOLDER_STATUS_LABELS.get(folder_status_key, ("未知状态", COLORS["text_muted"]))
        lines = [
            f"目录状态：{folder_status_text}",
            f"当前路径：{self._case.get('path', '') or '未关联'}",
            f"历史路径数量：{len(self._case.get('path_history', []))}",
            f"最后记录时间：{self._format_datetime(self._case.get('last_seen_at', '')) or '暂无'}",
        ]
        if folder_status_key != FOLDER_STATUS_AVAILABLE:
            lines.append("提示：重新关联目录后，软件会继续沿用同一个案件记忆与历史路径。")
        for line in lines:
            if "：" in line:
                label_text, value_text = line.split("：", 1)
            else:
                label_text, value_text = "说明", line

            item = QFrame()
            item.setObjectName("memoryRow")
            item.setStyleSheet(f"""
                QFrame#memoryRow {{
                    background: {COLORS['surface_1']};
                    border: none;
                    border-radius: 12px;
                }}
            """)
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(12, 10, 12, 10)
            item_layout.setSpacing(4)

            label = QLabel(label_text)
            label.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['text_muted']};
                font-size: 11px;
                font-weight: 700;
            """)
            item_layout.addWidget(label)

            value = QLabel(value_text)
            value.setWordWrap(True)
            value.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['text_secondary']};
                font-size: 13px;
                line-height: 1.55;
            """)
            item_layout.addWidget(value)
            layout.addWidget(item)

        tip = QLabel("文件夹仍是内容本体，软件负责本地索引、路径历史、字段、期限、笔记与筛选记忆，两者并存而不是互相替代。")
        tip.setWordWrap(True)
        tip.setStyleSheet(f"""
            background: rgba(16, 185, 129, 0.10);
            color: {COLORS['success']};
            border-radius: 12px;
            padding: 11px 12px;
            font-size: 12px;
            font-weight: 700;
            line-height: 1.6;
        """)
        layout.addWidget(tip)
        return card

    def _get_info_field_hint(self, field: Dict[str, Any]) -> str:
        if field.get("map_to_tag", False):
            return "已写入统一标签筛选，可直接参与列表过滤。"
        return INFO_FIELD_HINTS.get(field.get("key", ""), "")

    def _on_rename_info_section(self, section_key: str, current_title: str) -> None:
        if not self._case_id:
            return

        new_title, accepted = QInputDialog.getText(
            self,
            "修改分类标题",
            "请输入新的分类标题：",
            text=current_title,
        )
        if not accepted:
            return

        title = str(new_title or "").strip()
        if not title:
            QMessageBox.information(self, "标题未修改", "分类标题不能为空。")
            return

        if get_case_manager().update_info_section_titles(self._case_id, {section_key: title}):
            self._refresh_case_from_store()

    def _on_export_info(self) -> None:
        if not self._case_id or not self._case:
            return

        default_name = f"{self._case.get('name', '案件信息')}_信息.md"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出案件信息",
            default_name,
            "Markdown (*.md);;JSON (*.json)",
        )
        if not file_path:
            return

        success = get_case_manager().export_case_info(self._case_id, Path(file_path))
        if success:
            QMessageBox.information(self, "导出成功", f"已导出到：{file_path}")
        else:
            QMessageBox.warning(self, "导出失败", "导出案件信息时出现问题。")

    def _on_toggle_info_field_tag(self, field_id: str) -> None:
        if not self._case_id or not field_id:
            return
        get_case_manager().toggle_info_field_tag(self._case_id, field_id)
        self._refresh_case_from_store()

    def show_deadline_tab(self, deadline_id: str = "") -> bool:
        """切换到当前案件的期限签页（不打开编辑弹窗）。"""
        if not self._case_id:
            return False
        self._tabs.setCurrentIndex(self._deadline_tab_index)
        if deadline_id:
            deadline_exists = any(
                item.get("id") == deadline_id
                for item in (self._case or {}).get("deadlines", [])
            )
            if not deadline_exists:
                self._refresh_case_from_store()
        return True

    def open_deadline_editor_from_calendar(self, deadline_id: str) -> bool:
        """从期限日历跳转到当前案件的期限编辑。"""
        if not self._case_id or not deadline_id:
            return False
        self.show_deadline_tab(deadline_id)
        deadline_exists = any(
            item.get("id") == deadline_id
            for item in (self._case or {}).get("deadlines", [])
        )
        if not deadline_exists:
            return False
        self._on_edit_deadline(deadline_id)
        return True

    def _find_case_manager_dialog(self):
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "open_case_deadline_from_calendar") and hasattr(parent, "refresh_cases"):
                return parent
            parent = parent.parentWidget()
        return None

    def _refresh_case_from_store(self) -> None:
        if not self._case_id:
            return
        case = get_case_manager().get_case(self._case_id)
        if case:
            self.load_case(case)
            self.case_refreshed.emit(self._case_id)

    def _on_open_folder(self) -> None:
        if self._case_path:
            self.open_folder_requested.emit(str(self._case_path))

    def _on_relink_folder(self) -> None:
        if self._case_id:
            self.relink_folder_requested.emit(self._case_id)

    def _on_archive(self) -> None:
        if self._case_id:
            self.archive_requested.emit(self._case_id)

    def _on_edit_tags(self) -> None:
        if self._case_id:
            self.edit_tags_requested.emit(self._case_id)

    def _show_case_ocr_setup_guide(self) -> None:
        """显示 OCR 安装说明。"""
        status = get_ocr_dependency_status()
        QMessageBox.information(
            self,
            "OCR 增强能力说明",
            format_ocr_setup_message(status)
        )

    def _set_case_ocr_button_enabled(self, enabled: bool, text: str = "OCR识别") -> None:
        """统一控制案件详情头部 OCR 按钮状态。"""
        if not hasattr(self, "_btn_case_ocr"):
            return
        self._btn_case_ocr.setEnabled(enabled)
        self._btn_case_ocr.setText(text)

    def _on_case_ocr(self) -> None:
        """头部 OCR 截图识别入口。"""
        status = get_ocr_dependency_status()
        if not status.available:
            self._show_case_ocr_setup_guide()
            return

        self._set_case_ocr_button_enabled(False, "截图中...")
        self._screenshot_tool.start_screenshot()

    def _on_case_ocr_screenshot_captured(self, pixmap) -> None:
        """截图完成后启动 OCR。"""
        if pixmap.isNull():
            self._on_case_ocr_cancelled()
            return

        self._set_case_ocr_button_enabled(False, "识别中...")
        self._case_ocr_worker = OcrWorker(pixmap, self)
        self._case_ocr_worker.ocr_completed.connect(self._on_case_ocr_completed)
        self._case_ocr_worker.ocr_failed.connect(self._on_case_ocr_failed)
        self._case_ocr_worker.start()

    def _on_case_ocr_cancelled(self) -> None:
        """用户取消截图。"""
        self._set_case_ocr_button_enabled(bool(self._case_id))

    def _on_case_ocr_completed(self, text: str, text_blocks: List[Any]) -> None:
        """OCR 识别完成。"""
        self._set_case_ocr_button_enabled(bool(self._case_id))
        if self._case_ocr_worker is not None:
            self._case_ocr_worker.deleteLater()
            self._case_ocr_worker = None

        text = text.strip()
        if not text:
            QMessageBox.information(self, "OCR识别", "未能识别到文字，请尝试截取更清晰的区域。")
            return

        QApplication.clipboard().setText(text)
        preview = text.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:80] + "..."
        QMessageBox.information(
            self,
            "OCR识别完成",
            f"识别结果已复制到剪贴板，可直接粘贴到笔记或案件信息中。\n\n{preview}"
        )

    def _on_case_ocr_failed(self, error: str) -> None:
        """OCR 识别失败。"""
        self._logger.error(f"案件详情 OCR 识别失败: {error}")
        self._set_case_ocr_button_enabled(bool(self._case_id))
        if self._case_ocr_worker is not None:
            self._case_ocr_worker.deleteLater()
            self._case_ocr_worker = None
        QMessageBox.warning(self, "OCR识别失败", f"无法识别截图内容：\n{error}")

    def _on_tool_center(self) -> None:
        self.tool_center_requested.emit()

    def _on_view_calendar(self) -> None:
        self.view_calendar_requested.emit()

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget:
                widget.deleteLater()
            elif child_layout:
                self._clear_layout(child_layout)

    def _format_datetime(self, value: str) -> str:
        try:
            return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            return ""
