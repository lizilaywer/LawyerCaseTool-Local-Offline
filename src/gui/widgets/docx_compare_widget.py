# -*- coding: utf-8 -*-
"""Word 文档对比界面组件

左右双栏布局：左边原文档，右边修改后文档。
支持拖拽、文件选择、案件文件搜索，对比后在同一窗口中高亮差异。
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QCompleter,
    QSplitter,
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from src.gui.styles import APP_COLORS as COLORS
from src.core.docx_compare import compare_docx, render_diff_html, extract_docx_text
from src.utils.logger import get_logger


class _DocDropZone(QTextEdit):
    """支持拖放 docx 文件的预览区。"""

    file_loaded = Signal(str)

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setReadOnly(True)
        self.setPlaceholderText(placeholder)
        c = COLORS
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {c['surface_0']};
                color: {c['text_primary']};
                border: 1px dashed {c['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {c['accent']};
                border-style: solid;
            }}
        """)
        self._current_file: Optional[Path] = None
        self._original_html: str = ""

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() == ".docx":
                self.load_file(path)
                self.file_loaded.emit(str(path))
            else:
                QMessageBox.warning(self, "格式不支持", "仅支持 .docx 格式的 Word 文档。")

    def load_file(self, path: Path) -> None:
        """加载并预览 docx 文件。"""
        self._current_file = path
        try:
            text = extract_docx_text(path)
            escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            self._original_html = f"<body style='margin:0;'><span style='color:#334155;'>{escaped}</span></body>"
            self.setHtml(self._original_html)
        except Exception as e:
            self.setPlainText(f"无法读取文件: {e}")

    def show_diff(self, html: str) -> None:
        """显示差异高亮结果。"""
        self.setHtml(f"<body style='margin:0;'>{html}</body>")

    def reset_to_original(self) -> None:
        """恢复显示原文。"""
        if self._original_html:
            self.setHtml(self._original_html)

    def get_file(self) -> Optional[Path]:
        return self._current_file

    def clear_all(self) -> None:
        """清空当前文件和预览内容，恢复为初始状态。"""
        self._current_file = None
        self._original_html = ""
        self.clear()
        self.setPlaceholderText("拖拽 Word 文件到此处…")


class DocxCompareWidget(QWidget):
    """文档对比主组件。"""

    def __init__(self, parent=None, case_path: Optional[Path] = None):
        super().__init__(parent)
        self._logger = get_logger()
        self._case_path = case_path
        self._setup_ui()
        self._build_file_list()

    def _setup_ui(self) -> None:
        c = COLORS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # 左右分栏：原文档 vs 修改后文档
        file_area = QHBoxLayout()
        file_area.setSpacing(8)

        # 文档 A
        zone_a, container_a, self._btn_select_a, self._search_a = self._build_drop_zone(
            "原文档", "拖拽 Word 文件到此处…"
        )
        self._zone_a = zone_a
        file_area.addWidget(container_a, 1)

        # 文档 B
        zone_b, container_b, self._btn_select_b, self._search_b = self._build_drop_zone(
            "修改后文档", "拖拽 Word 文件到此处…"
        )
        self._zone_b = zone_b
        file_area.addWidget(container_b, 1)

        layout.addLayout(file_area, 1)

        # 操作按钮栏：开始对比 + 清空全部
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)
        btn_bar.addStretch()

        self._btn_compare = QPushButton("▶ 开始对比")
        self._btn_compare.setFixedHeight(30)
        self._btn_compare.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_compare.setStyleSheet(f"""
            QPushButton {{
                background: {c['accent']};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background: {c['accent_hover']};
            }}
            QPushButton:disabled {{
                background: {c['surface_3']};
                color: {c['text_muted']};
            }}
        """)
        self._btn_compare.clicked.connect(self._on_compare)
        btn_bar.addWidget(self._btn_compare)

        self._btn_clear = QPushButton("✕ 清空全部")
        self._btn_clear.setFixedHeight(30)
        self._btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_1']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """)
        self._btn_clear.clicked.connect(self._on_clear_all)
        btn_bar.addWidget(self._btn_clear)
        btn_bar.addStretch()

        layout.addLayout(btn_bar)

    def _build_drop_zone(self, title_text: str, placeholder: str) -> tuple:
        """构建单个拖放区，返回 (drop_zone, 容器widget, 选择按钮, 搜索框)。"""
        c = COLORS
        container = QWidget()
        vlayout = QVBoxLayout(container)
        vlayout.setContentsMargins(0, 0, 0, 4)
        vlayout.setSpacing(6)

        title = QLabel(title_text)
        title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        vlayout.addWidget(title)

        zone = _DocDropZone(placeholder)
        zone.setMinimumHeight(160)
        vlayout.addWidget(zone, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_select = QPushButton("选择文件")
        btn_select.setFixedHeight(28)
        btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_1']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                font-size: 12px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """)
        btn_row.addWidget(btn_select)

        search_edit = QLineEdit()
        search_edit.setPlaceholderText("🔍 搜索 Word 文件…")
        search_edit.setFixedHeight(28)
        search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {c['surface_0']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 12px;
            }}
        """)
        btn_row.addWidget(search_edit, 1)

        vlayout.addLayout(btn_row)
        return zone, container, btn_select, search_edit

    def _build_file_list(self) -> None:
        """收集所有案件目录下的 docx 文件用于搜索补全。"""
        files: list[str] = []
        try:
            from src.core.case_manager import get_case_manager
            cm = get_case_manager()
            all_cases = cm.get_all_cases()
            for case in all_cases:
                case_path = Path(case.get("path", ""))
                if case_path.exists():
                    for p in case_path.rglob("*.docx"):
                        files.append(str(p))
        except Exception as e:
            self._logger.warning(f"扫描 docx 文件失败: {e}")

        # 为搜索框 A 设置 completer
        completer_a = QCompleter(files, self)
        completer_a.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer_a.setFilterMode(Qt.MatchFlag.MatchContains)
        self._search_a.setCompleter(completer_a)
        completer_a.activated.connect(lambda text: self._on_completer_activated(text, self._zone_a))
        self._search_a.returnPressed.connect(lambda: self._on_search_file(self._search_a, self._zone_a))
        self._btn_select_a.clicked.connect(lambda: self._on_select_file(self._zone_a))

        # 为搜索框 B 设置 completer
        completer_b = QCompleter(files, self)
        completer_b.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer_b.setFilterMode(Qt.MatchFlag.MatchContains)
        self._search_b.setCompleter(completer_b)
        completer_b.activated.connect(lambda text: self._on_completer_activated(text, self._zone_b))
        self._search_b.returnPressed.connect(lambda: self._on_search_file(self._search_b, self._zone_b))
        self._btn_select_b.clicked.connect(lambda: self._on_select_file(self._zone_b))

    def _on_select_file(self, zone: _DocDropZone) -> None:
        """通过文件对话框选择 docx 文件。"""
        path_str, _ = QFileDialog.getOpenFileName(
            self, "选择 Word 文档", "", "Word 文档 (*.docx)"
        )
        if path_str:
            zone.load_file(Path(path_str))

    def _on_completer_activated(self, text: str, zone: _DocDropZone) -> None:
        """从 QCompleter 下拉列表中选择文件后加载。"""
        path = Path(text.strip())
        if path.exists() and path.suffix.lower() == ".docx":
            zone.load_file(path)
        else:
            QMessageBox.warning(self, "文件不存在", f"找不到 Word 文档: {text}")

    def _on_search_file(self, edit: QLineEdit, zone: _DocDropZone) -> None:
        """通过搜索框路径加载文件。"""
        text = edit.text().strip()
        if not text:
            return
        path = Path(text)
        if not path.exists():
            # 尝试在案件目录下查找
            try:
                from src.core.case_manager import get_case_manager
                cm = get_case_manager()
                for case in cm.get_all_cases():
                    case_path = Path(case.get("path", ""))
                    if case_path.exists():
                        candidate = case_path / text
                        if candidate.exists():
                            path = candidate
                            break
                        # 也尝试递归查找匹配文件名的文件
                        for p in case_path.rglob("*.docx"):
                            if p.name == text or str(p).endswith(text):
                                path = p
                                break
            except Exception:
                pass
        if path.exists() and path.suffix.lower() == ".docx":
            zone.load_file(path)
            edit.clear()
        else:
            QMessageBox.warning(self, "文件不存在", f"找不到 Word 文档: {text}")

    def _on_compare(self) -> None:
        """执行对比，在同一窗口中高亮显示差异。"""
        path_a = self._zone_a.get_file()
        path_b = self._zone_b.get_file()

        if not path_a or not path_b:
            QMessageBox.information(self, "提示", "请先选择两份 Word 文档。")
            return

        try:
            segments_a, segments_b = compare_docx(path_a, path_b)
            html_a = render_diff_html(segments_a, side="left")
            html_b = render_diff_html(segments_b, side="right")
            self._zone_a.show_diff(html_a)
            self._zone_b.show_diff(html_b)
        except Exception as e:
            self._logger.error(f"文档对比失败: {e}")
            QMessageBox.warning(self, "对比失败", str(e))

    def _on_clear_all(self) -> None:
        """清空左右两侧的文件和预览内容。"""
        self._zone_a.clear_all()
        self._zone_b.clear_all()
        self._search_a.clear()
        self._search_b.clear()
