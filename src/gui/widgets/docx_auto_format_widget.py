# -*- coding: utf-8 -*-
"""自动排版界面组件

简洁卡片式布局：拖拽/导入 Word 文档 → 预览识别结果 → 一键排版。
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QButtonGroup,
    QProgressBar,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from src.gui.styles import APP_COLORS
from src.core.docx_auto_format import DocxAutoFormatter, ParagraphType
from src.utils.logger import get_logger

c = APP_COLORS

# ── 段落类型中文名 ──
_PTYPE_LABELS = {
    ParagraphType.MAIN_TITLE: "大标题",
    ParagraphType.LEVEL1_TITLE: "一级标题",
    ParagraphType.LEVEL2_TITLE: "二级标题",
    ParagraphType.LEVEL3_TITLE: "三级标题",
    ParagraphType.BODY: "正文",
    ParagraphType.SIGNATURE: "落款",
    ParagraphType.EMPTY: "空行",
}

_PTYPE_COLORS = {
    ParagraphType.MAIN_TITLE: "#dc2626",
    ParagraphType.LEVEL1_TITLE: "#2563eb",
    ParagraphType.LEVEL2_TITLE: "#7c3aed",
    ParagraphType.LEVEL3_TITLE: "#059669",
    ParagraphType.BODY: c["text_secondary"],
    ParagraphType.SIGNATURE: "#d97706",
}

# ── 卡片样式帮助函数 ──

def _card_style() -> str:
    return f"""
        background: {c['surface_0']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    """


def _primary_btn_style(height: int = 38) -> str:
    return f"""
        QPushButton {{
            background: {c['accent']};
            color: #fff;
            border: none;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 700;
            padding: 0 24px;
            min-height: {height}px;
            max-height: {height}px;
        }}
        QPushButton:hover {{
            background: {c['accent_hover']};
        }}
        QPushButton:disabled {{
            background: {c['surface_3']};
            color: {c['text_muted']};
        }}
    """


def _secondary_btn_style() -> str:
    return f"""
        QPushButton {{
            background: {c['surface_0']};
            color: {c['text_secondary']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            padding: 0 14px;
            min-height: 30px;
            max-height: 30px;
        }}
        QPushButton:hover {{
            background: {c['surface_1']};
            border-color: {c['border_strong']};
            color: {c['text_primary']};
        }}
    """


# ═══════════════════════════════════════════════════════════════════
# 拖放区域
# ═══════════════════════════════════════════════════════════════════

class _DropZone(QWidget):
    """支持拖放 .docx 文件的区域，同时也是文件列表容器。"""

    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._hover = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self._hint = QLabel("将 Word 文档拖拽到此处\n或点击下方按钮选择文件")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        # 文件 chips 可滚动容器
        self._chip_scroll = QScrollArea()
        self._chip_scroll.setWidgetResizable(True)
        self._chip_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._chip_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['border_strong']};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self._chip_container = QWidget()
        self._chip_container.setStyleSheet("background: transparent;")
        self._chip_layout = QVBoxLayout(self._chip_container)
        self._chip_layout.setContentsMargins(0, 0, 0, 0)
        self._chip_layout.setSpacing(4)
        self._chip_layout.addStretch()

        self._chip_scroll.setWidget(self._chip_container)
        self._chip_scroll.hide()
        layout.addWidget(self._chip_scroll, 1)

        self._update_style()

    @property
    def chip_layout(self):
        return self._chip_layout

    def _update_style(self) -> None:
        if self._hover:
            bg, border_color, text_color = c["accent_subtle"], c["accent"], c["accent"]
            border_style = "solid"
        else:
            bg, border_color, text_color = c["surface_0"], c["border"], c["text_muted"]
            border_style = "dashed"

        self.setStyleSheet(f"""
            QWidget {{
                background: {bg};
                border: 2px {border_style} {border_color};
                border-radius: 12px;
            }}
        """)
        self._hint.setStyleSheet(f"""
            color: {text_color};
            font-size: 13px;
            background: transparent;
            border: none;
        """)

    def set_has_files(self, has: bool) -> None:
        self._hint.setVisible(not has)
        self._chip_scroll.setVisible(has)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._hover = True
            self._update_style()

    def dragLeaveEvent(self, event) -> None:
        self._hover = False
        self._update_style()

    def dropEvent(self, event: QDropEvent) -> None:
        self._hover = False
        self._update_style()
        paths = [
            Path(u.toLocalFile()) for u in event.mimeData().urls()
            if u.toLocalFile().lower().endswith(".docx")
        ]
        if paths:
            self.files_dropped.emit([str(p) for p in paths])
        else:
            QMessageBox.warning(self, "格式不支持", "仅支持 .docx 格式的 Word 文档。")


# ═══════════════════════════════════════════════════════════════════
# 后台排版线程
# ═══════════════════════════════════════════════════════════════════

class _FormatWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(list, int, int)

    def __init__(self, files: List[Path], save_as: bool,
                 output_dir: Optional[Path], backup: bool):
        super().__init__()
        self._files = files
        self._save_as = save_as
        self._output_dir = output_dir
        self._backup = backup

    def run(self):
        results = []
        success = 0
        fail = 0
        total = len(self._files)

        for i, file_path in enumerate(self._files):
            pct = int((i / total) * 100)
            self.progress.emit(pct, file_path.name)

            try:
                if self._backup and not self._save_as:
                    DocxAutoFormatter.backup_original(file_path)

                formatter = DocxAutoFormatter()
                formatter.load(file_path)
                formatter.apply_format()

                if self._save_as and self._output_dir:
                    out_path = self._output_dir / f"{file_path.stem}_排版后{file_path.suffix}"
                else:
                    out_path = file_path

                formatter.save(out_path)
                success += 1
                results.append((True, file_path.name, ""))
            except Exception as e:
                fail += 1
                results.append((False, file_path.name, str(e)))

        self.progress.emit(100, "")
        self.finished.emit(results, success, fail)


# ═══════════════════════════════════════════════════════════════════
# 文件条目 chip
# ═══════════════════════════════════════════════════════════════════

class _FileChip(QFrame):
    removed = Signal(object)

    def __init__(self, file_path: Path, parent=None):
        super().__init__(parent)
        self._path = file_path

        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QFrame {{
                background: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 8, 4)
        layout.setSpacing(8)

        icon = QLabel("DOC")
        icon.setFixedWidth(34)
        icon.setFixedHeight(24)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"""
            background: {c['accent_subtle']};
            color: {c['accent']};
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
        """)
        layout.addWidget(icon)

        name = QLabel(file_path.name)
        name.setMinimumWidth(60)
        name.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        name.setStyleSheet(f"""
            color: {c['text_primary']};
            font-size: 12px;
            font-weight: 500;
            background: transparent;
            border: none;
        """)
        name.setToolTip(str(file_path))
        layout.addWidget(name, 1)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(26, 26)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['text_muted']};
                border: 1px solid transparent;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 700;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['danger']};
                border-color: {c['border']};
            }}
        """)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(remove_btn)

    @property
    def path(self) -> Path:
        return self._path


# ═══════════════════════════════════════════════════════════════════
# 主组件
# ═══════════════════════════════════════════════════════════════════

class DocxAutoFormatWidget(QWidget):
    """自动排版主组件 —— 简洁卡片式布局。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._files: List[Path] = []
        self._chips: List[_FileChip] = []
        self._worker: Optional[_FormatWorker] = None
        self._preview_data: List[tuple] = []  # (ptype, preview, align)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(12)

        # ── 说明 ──
        desc = QLabel("智能识别标题层级，参照 GB/T 9704-2012 应用法律文书标准排版格式")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        root.addWidget(desc)

        # ── 拖放区 + 文件列表 合并为一个区域 ──
        drop_card = QFrame()
        drop_card.setStyleSheet(_card_style())
        drop_card_layout = QVBoxLayout(drop_card)
        drop_card_layout.setContentsMargins(16, 12, 16, 12)
        drop_card_layout.setSpacing(0)

        self._drop_zone = _DropZone()
        self._drop_zone.setMinimumHeight(88)
        self._drop_zone.setMaximumHeight(280)
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        drop_card_layout.addWidget(self._drop_zone)

        root.addWidget(drop_card)

        # ── 预览结果区 ──
        self._preview_card = QFrame()
        self._preview_card.setStyleSheet(_card_style())
        self._preview_card.hide()
        preview_layout = QVBoxLayout(self._preview_card)
        preview_layout.setContentsMargins(14, 10, 14, 10)
        preview_layout.setSpacing(6)

        self._preview_title = QLabel("识别预览")
        self._preview_title.setStyleSheet(f"""
            color: {c['text_primary']};
            font-size: 12px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        preview_layout.addWidget(self._preview_title)

        self._preview_stats = QLabel("")
        self._preview_stats.setWordWrap(True)
        self._preview_stats.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 11px;
            background: transparent;
            border: none;
            padding: 2px 0;
        """)
        preview_layout.addWidget(self._preview_stats)

        # 滚动详情
        self._preview_scroll = QScrollArea()
        self._preview_scroll.setWidgetResizable(True)
        self._preview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._preview_scroll.setMaximumHeight(200)
        self._preview_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._preview_list = QWidget()
        self._preview_list.setStyleSheet(f"background: transparent;")
        self._preview_list_layout = QVBoxLayout(self._preview_list)
        self._preview_list_layout.setContentsMargins(0, 0, 0, 0)
        self._preview_list_layout.setSpacing(2)
        self._preview_scroll.setWidget(self._preview_list)

        preview_layout.addWidget(self._preview_scroll)
        root.addWidget(self._preview_card)

        # ── 操作按钮 + 保存选项 合并为一行 ──
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self._btn_select = QPushButton("选择文件")
        self._btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_select.setStyleSheet(_secondary_btn_style())
        self._btn_select.clicked.connect(self._on_select_files)
        bottom_row.addWidget(self._btn_select)

        self._btn_preview = QPushButton("预览识别结果")
        self._btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_preview.setStyleSheet(_secondary_btn_style())
        self._btn_preview.clicked.connect(self._on_preview)
        self._btn_preview.setEnabled(False)
        bottom_row.addWidget(self._btn_preview)

        self._btn_clear = QPushButton("清空所有")
        self._btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['text_muted']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 14px;
                min-height: 30px;
                max-height: 30px;
            }}
            QPushButton:hover {{
                color: {c['danger']};
                border-color: {c['danger']};
                background: {c['surface_1']};
            }}
        """)
        self._btn_clear.clicked.connect(self._on_clear_files)
        self._btn_clear.setEnabled(False)
        bottom_row.addWidget(self._btn_clear)

        bottom_row.addSpacing(16)

        self._save_mode_group = QButtonGroup(self)
        self._cb_overwrite = QCheckBox("覆盖原文档（自动备份）")
        self._cb_overwrite.setChecked(True)
        self._cb_save_as = QCheckBox("另存为新文件")
        self._save_mode_group.addButton(self._cb_overwrite)
        self._save_mode_group.addButton(self._cb_save_as)

        for cb in (self._cb_overwrite, self._cb_save_as):
            bottom_row.addWidget(cb)

        bottom_row.addStretch()
        root.addLayout(bottom_row)

        # ── 进度 ──
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: {c['surface_2']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {c['accent']};
                border-radius: 3px;
            }}
        """)
        self._progress.hide()
        root.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"""
            color: {c['text_muted']};
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        self._status_label.hide()
        root.addWidget(self._status_label)

        # ── 执行按钮 ──
        self._btn_format = QPushButton("▶ 自动排版")
        self._btn_format.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_format.setStyleSheet(_primary_btn_style(40))
        self._btn_format.clicked.connect(self._on_format)
        self._btn_format.setEnabled(False)
        root.addWidget(self._btn_format, 0, Qt.AlignmentFlag.AlignHCenter)

        root.addStretch()

    # ------------------------------------------------------------------
    # 文件管理
    # ------------------------------------------------------------------

    def _on_select_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择 Word 文档", "", "Word 文档 (*.docx)"
        )
        if paths:
            self._add_files([Path(p) for p in paths])

    def _on_files_dropped(self, paths: List[str]) -> None:
        self._add_files([Path(p) for p in paths])

    def _on_clear_files(self) -> None:
        self._files.clear()
        self._refresh_file_list()
        self._hide_preview()

    def _add_files(self, paths: List[Path]) -> None:
        added = 0
        for p in paths:
            if p.suffix.lower() == ".docx" and p not in self._files:
                self._files.append(p)
                added += 1
        if added:
            self._refresh_file_list()
            self._hide_preview()

    def _remove_file(self, chip: _FileChip) -> None:
        if chip.path in self._files:
            self._files.remove(chip.path)
        self._refresh_file_list()
        if not self._files:
            self._hide_preview()

    def _refresh_file_list(self) -> None:
        # 清除旧 chips
        for chip in self._chips:
            chip.deleteLater()
        self._chips.clear()

        layout = self._drop_zone.chip_layout

        for fp in self._files:
            chip = _FileChip(fp)
            chip.removed.connect(self._remove_file)
            self._chips.append(chip)
            layout.addWidget(chip)

        self._drop_zone.set_has_files(bool(self._files))

        if not self._files:
            self._btn_preview.setEnabled(False)
            self._btn_clear.setEnabled(False)
            self._btn_format.setEnabled(False)
        else:
            self._btn_preview.setEnabled(True)
            self._btn_clear.setEnabled(True)
            self._btn_format.setEnabled(True)

    def _hide_preview(self) -> None:
        self._preview_data.clear()
        self._preview_card.hide()
        self._clear_preview_items()

    def _clear_preview_items(self) -> None:
        while self._preview_list_layout.count():
            item = self._preview_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ------------------------------------------------------------------
    # 预览
    # ------------------------------------------------------------------

    def _on_preview(self) -> None:
        if not self._files:
            return

        file_path = self._files[0]
        try:
            formatter = DocxAutoFormatter()
            formatter.load(file_path)
            info = formatter.get_paragraph_info()
        except Exception as e:
            QMessageBox.critical(self, "预览失败", f"无法读取文档：\n{e}")
            return

        self._preview_data = info
        self._clear_preview_items()

        # 统计
        type_counts = {}
        for ptype, preview, align in info:
            if ptype != ParagraphType.EMPTY:
                type_counts[ptype] = type_counts.get(ptype, 0) + 1

        stats_parts = []
        for pt in [ParagraphType.MAIN_TITLE, ParagraphType.LEVEL1_TITLE,
                   ParagraphType.LEVEL2_TITLE, ParagraphType.LEVEL3_TITLE,
                   ParagraphType.BODY, ParagraphType.SIGNATURE]:
            cnt = type_counts.get(pt, 0)
            if cnt > 0:
                color = _PTYPE_COLORS.get(pt, c["text_secondary"])
                stats_parts.append(
                    f'<span style="color:{color};font-weight:600;">{_PTYPE_LABELS[pt]}</span>'
                    f' <span style="color:{c["text_tertiary"]};">{cnt}段</span>'
                )

        if stats_parts:
            self._preview_stats.setText(" · ".join(stats_parts))
        else:
            self._preview_stats.setText("未识别到内容段落")

        if len(self._files) > 1:
            self._preview_stats.setText(
                self._preview_stats.text() +
                f'  <span style="color:{c["text_muted"]};">（仅预览 {file_path.name}）</span>'
            )

        # 添加每段的预览条目
        for ptype, preview, align in info:
            if ptype == ParagraphType.EMPTY:
                continue

            row = QWidget()
            row.setStyleSheet(f"""
                QWidget {{
                    background: transparent;
                    border-radius: 4px;
                }}
                QWidget:hover {{
                    background: {c['surface_1']};
                }}
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(8)

            # 类型标签
            type_label = QLabel(_PTYPE_LABELS.get(ptype, str(ptype)))
            type_color = _PTYPE_COLORS.get(ptype, c["text_secondary"])
            type_label.setFixedWidth(56)
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_label.setStyleSheet(f"""
                background: {type_color}18;
                color: {type_color};
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                padding: 1px 4px;
            """)
            row_layout.addWidget(type_label)

            # 内容预览
            content = QLabel(preview)
            content.setStyleSheet(f"""
                color: {c['text_primary']};
                font-size: 11px;
                background: transparent;
                border: none;
            """)
            content.setWordWrap(False)
            row_layout.addWidget(content, 1)

            self._preview_list_layout.addWidget(row)

        self._preview_card.show()

    # ------------------------------------------------------------------
    # 排版执行
    # ------------------------------------------------------------------

    def _on_format(self) -> None:
        if not self._files:
            return

        save_as = self._cb_save_as.isChecked()
        output_dir: Optional[Path] = None
        if save_as:
            dir_path = QFileDialog.getExistingDirectory(self, "选择保存目录")
            if not dir_path:
                return
            output_dir = Path(dir_path)

        backup = not save_as

        if not save_as:
            ret = QMessageBox.question(
                self, "确认排版",
                f"将在原文档上直接修改（已自动备份）。\n\n"
                f"确定对 {len(self._files)} 个文件执行排版？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return

        # 禁用控件
        self._btn_format.setEnabled(False)
        self._btn_select.setEnabled(False)
        self._btn_preview.setEnabled(False)
        self._btn_clear.setEnabled(False)
        self._progress.show()
        self._progress.setValue(0)
        self._status_label.show()
        self._status_label.setText("正在准备…")

        self._worker = _FormatWorker(self._files, save_as, output_dir, backup)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, pct: int, name: str):
        self._progress.setValue(pct)
        if name:
            self._status_label.setText(f"正在处理：{name}…")

    def _on_finished(self, results: list, success: int, fail: int):
        self._progress.setValue(100)
        self._btn_format.setEnabled(True)
        self._btn_select.setEnabled(True)
        self._btn_preview.setEnabled(True)
        self._btn_clear.setEnabled(True)

        if fail == 0:
            self._status_label.setText(f"完成 — 成功处理 {success} 个文件")
            QMessageBox.information(self, "排版完成", f"成功处理 {success} 个文件。")
        else:
            self._status_label.setText(f"完成 — 成功 {success} 个，失败 {fail} 个")
            lines = []
            for ok, name, err in results:
                if not ok:
                    lines.append(f"✗ {name} — {err}")
            detail = "\n".join(lines[:10])
            QMessageBox.warning(
                self, "排版完成",
                f"成功 {success} 个，失败 {fail} 个。\n\n{detail}"
            )

        self._worker = None

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """清空所有文件和状态。"""
        self._files.clear()
        self._refresh_file_list()
        self._hide_preview()
        self._progress.hide()
        self._status_label.hide()
        self._status_label.setText("")
