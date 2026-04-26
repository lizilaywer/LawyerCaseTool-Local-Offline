# -*- coding: utf-8 -*-
"""电子化归档 - 文件预览控件

支持预览 Word、PDF、图片文件，并提供右键菜单功能。
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import OrderedDict
import re

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QScrollArea,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QPushButton,
    QLineEdit,
)
from PySide6.QtCore import Qt, Signal, QPoint, QByteArray, QTimer
from PySide6.QtGui import QPixmap, QImage, QTextCursor, QColor, QFont, QTextCharFormat

from src.utils.logger import get_logger
from src.gui.styles import APP_COLORS as COLORS, button_style, input_style
from src.utils.platform_utils import get_default_monospace_font_family, get_default_ui_font_family
from src.gui.icon_utils import get_standard_icon

# 尝试导入 PyMuPDF (fitz)
try:
    import fitz
except ImportError:
    fitz = None


class ArchivePreview(QWidget):
    """文件预览控件

    功能：
    - 预览 Word(.docx)、PDF、图片文件
    - Word 文档变量高亮
    - 右键菜单：设置为变量、定义为变量字段
    - 支持文件拖拽
    """

    # 信号
    variable_set = Signal(str, str, dict)  # 设置为变量 (变量key, 选中文本, 选区信息)
    field_defined = Signal(str, str)      # 定义为字段 (变量key, 选中文本)
    variables_detected = Signal(list)     # 检测到新变量
    save_requested = Signal()             # 保存请求
    save_as_requested = Signal()          # 另存为请求

    # 变量匹配正则
    VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()

        self._current_file: Optional[Path] = None
        self._current_type: str = ""  # word, pdf, image, empty
        self._variables: List[Dict[str, str]] = []  # 变量列表 [{key, name}, ...]
        self._original_text: str = ""  # 原始文本（用于高亮）
        self._save_actions_enabled = True
        self._empty_hint_text = "拖拽文件到此处或双击右侧文件树中的文件进行预览"

        # PDF 阅读器状态
        self._pdf_doc = None  # PDF 文档对象
        self._pdf_current_page = 0  # 当前页码（从0开始）
        self._pdf_total_pages = 0  # 总页数
        self._pdf_zoom = 1.0  # 用户缩放比例（用于放大/缩小按钮）
        self._actual_zoom = 1.0  # 实际显示缩放比例
        self._pdf_fit_mode = "width"  # 适应模式: width, original, fit

        # 图片预览状态
        self._original_pixmap: Optional[QPixmap] = None  # 原始图片（用于缩放）
        self._render_cache: OrderedDict[tuple, QPixmap] = OrderedDict()
        self._render_cache_limit = 16

        # 渲染防抖定时器
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(100)
        self._refresh_timer.timeout.connect(self._do_visual_refresh)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setProperty("archivePreviewHeader", True)
        header.setStyleSheet(f"background: {c['surface_0']}; border-bottom: 1px solid {c['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        self._title_label = QLabel("文件预览")
        self._title_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['text_primary']};")
        header_layout.addWidget(self._title_label)

        self._type_label = QLabel("")
        self._type_label.setStyleSheet(f"font-size: 11px; color: {c['text_tertiary']};")
        header_layout.addWidget(self._type_label)
        header_layout.addStretch()

        # 保存按钮
        self._save_btn = QPushButton("保存")
        self._save_btn.setFixedHeight(28)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet(button_style(compact=True))
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._save_btn.setVisible(False)  # 默认隐藏，打开文件后显示
        header_layout.addWidget(self._save_btn)

        # 另存为按钮
        self._save_as_btn = QPushButton("另存为")
        self._save_as_btn.setFixedHeight(28)
        self._save_as_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_as_btn.setStyleSheet(button_style(primary=True, compact=True))
        self._save_as_btn.clicked.connect(self._on_save_as_clicked)
        self._save_as_btn.setVisible(False)  # 默认隐藏，打开文件后显示
        header_layout.addWidget(self._save_as_btn)

        layout.addWidget(header)

        # 预览区域
        self._stack_widget = QWidget()
        self._stack_layout = QVBoxLayout(self._stack_widget)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)

        # 空白提示
        self._empty_widget = QWidget()
        self._empty_layout = QVBoxLayout(self._empty_widget)
        self._empty_layout.setContentsMargins(20, 20, 20, 20)
        self._empty_layout.addStretch()

        self._empty_icon = QLabel()
        self._empty_icon.setPixmap(get_standard_icon("file").pixmap(42, 42))
        self._empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_layout.addWidget(self._empty_icon)

        self._empty_hint = QLabel(self._empty_hint_text)
        self._empty_hint.setStyleSheet(f"""
            font-size: 13px;
            color: {c['text_tertiary']};
        """)
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_layout.addWidget(self._empty_hint)
        self._empty_layout.addStretch()

        self._stack_layout.addWidget(self._empty_widget)

        # 文本预览 (Word)
        self._text_preview = QTextEdit()
        self._text_preview.setReadOnly(True)
        self._text_preview.setAcceptDrops(True)
        self._text_preview.setAcceptRichText(True)
        self._text_preview.setStyleSheet(f"""
            QTextEdit {{
                border: none;
                background: {c['surface_0']};
                font-size: 13px;
                color: {c['text_primary']};
                padding: 12px;
            }}
        """)
        self._text_preview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._text_preview.customContextMenuRequested.connect(self._show_context_menu)
        self._text_preview.setHidden(True)
        self._stack_layout.addWidget(self._text_preview)

        # 图片预览容器（包含图片和PDF工具栏）
        self._image_container = QWidget()
        image_layout = QVBoxLayout(self._image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)

        # 图片滚动区域
        self._image_scroll = QScrollArea()
        self._image_scroll.setWidgetResizable(True)
        self._image_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {c['surface_0']};
            }}
        """)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setScaledContents(True)
        self._image_scroll.setWidget(self._image_label)
        image_layout.addWidget(self._image_scroll, 1)

        # PDF 工具栏
        self._pdf_toolbar = self._create_pdf_toolbar()
        image_layout.addWidget(self._pdf_toolbar)

        self._image_container.setHidden(True)
        self._stack_layout.addWidget(self._image_container)

        layout.addWidget(self._stack_widget, 1)

        # 启用拖拽
        self.setAcceptDrops(True)

    def _create_pdf_toolbar(self) -> QWidget:
        """创建 PDF 阅读器工具栏"""
        c = COLORS
        toolbar = QWidget()
        toolbar.setFixedHeight(42)
        toolbar.setProperty("archivePdfToolbar", True)
        toolbar.setStyleSheet(f"""
            QWidget[archivePdfToolbar="true"] {{
                background: {c['surface_1']};
                border-top: 1px solid {c['border']};
            }}
        """)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(6)

        icon_button_style = f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 0;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                border-color: {c['border_strong']};
                color: {c['text_primary']};
            }}
            QPushButton:checked {{
                background: {c['accent_subtle']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
            QPushButton:disabled {{
                background: {c['surface_1']};
                color: {c['text_muted']};
                border-color: {c['border']};
            }}
        """

        fit_button_style = f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 0;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
            QPushButton:checked {{
                background: {c['accent_subtle']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
        """

        # 翻页控制组（包装到一个 widget 中，方便图片预览时整体隐藏）
        self._page_nav_widget = QWidget()
        page_nav_layout = QHBoxLayout(self._page_nav_widget)
        page_nav_layout.setContentsMargins(0, 0, 0, 0)
        page_nav_layout.setSpacing(4)

        self._prev_btn = QPushButton("‹")
        self._prev_btn.setFixedSize(30, 30)
        self._prev_btn.setToolTip("上一页")
        self._prev_btn.clicked.connect(self._on_pdf_prev_page)
        page_nav_layout.addWidget(self._prev_btn)

        # 页码显示和跳转
        page_widget = QWidget()
        page_layout = QHBoxLayout(page_widget)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(3)

        self._page_input = QLineEdit()
        self._page_input.setFixedSize(36, 28)
        self._page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_input.setStyleSheet(input_style())
        self._page_input.returnPressed.connect(self._on_pdf_page_jump)
        page_layout.addWidget(self._page_input)

        self._page_label = QLabel("/ 0")
        self._page_label.setFixedWidth(30)
        self._page_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
        page_layout.addWidget(self._page_label)

        page_nav_layout.addWidget(page_widget)

        self._next_btn = QPushButton("›")
        self._next_btn.setFixedSize(30, 30)
        self._next_btn.setToolTip("下一页")
        self._next_btn.clicked.connect(self._on_pdf_next_page)
        page_nav_layout.addWidget(self._next_btn)

        layout.addWidget(self._page_nav_widget)

        layout.addSpacing(8)

        # 缩放控制组
        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setFixedSize(30, 30)
        self._zoom_out_btn.setToolTip("缩小")
        self._zoom_out_btn.clicked.connect(self._on_pdf_zoom_out)
        layout.addWidget(self._zoom_out_btn)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(46)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
        layout.addWidget(self._zoom_label)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedSize(30, 30)
        self._zoom_in_btn.setToolTip("放大")
        self._zoom_in_btn.clicked.connect(self._on_pdf_zoom_in)
        layout.addWidget(self._zoom_in_btn)

        layout.addSpacing(6)

        # 适应模式按钮
        self._fit_width_btn = QPushButton("↔")
        self._fit_width_btn.setFixedSize(34, 30)
        self._fit_width_btn.setCheckable(True)
        self._fit_width_btn.setToolTip("适应窗口宽度")
        self._fit_width_btn.clicked.connect(lambda: self._on_pdf_fit_mode("width"))
        layout.addWidget(self._fit_width_btn)

        self._fit_page_btn = QPushButton("▣")
        self._fit_page_btn.setFixedSize(34, 30)
        self._fit_page_btn.setCheckable(True)
        self._fit_page_btn.setToolTip("适应窗口大小")
        self._fit_page_btn.clicked.connect(lambda: self._on_pdf_fit_mode("fit"))
        layout.addWidget(self._fit_page_btn)

        self._original_size_btn = QPushButton("1:1")
        self._original_size_btn.setFixedSize(42, 30)
        self._original_size_btn.setCheckable(True)
        self._original_size_btn.setToolTip("原始大小")
        self._original_size_btn.clicked.connect(lambda: self._on_pdf_fit_mode("original"))
        layout.addWidget(self._original_size_btn)

        layout.addStretch()

        # 设置按钮样式
        for btn in [self._prev_btn, self._next_btn, self._zoom_out_btn, self._zoom_in_btn]:
            btn.setStyleSheet(icon_button_style)

        for btn in [self._fit_width_btn, self._fit_page_btn, self._original_size_btn]:
            btn.setStyleSheet(fit_button_style)

        return toolbar

    def set_variables(self, variables: List[Dict[str, str]]) -> None:
        """设置变量列表

        Args:
            variables: 变量列表 [{key, name}, ...]
        """
        self._variables = variables

    def set_save_actions_enabled(self, enabled: bool) -> None:
        """设置保存按钮是否允许显示。"""
        self._save_actions_enabled = enabled
        if not enabled:
            self._save_btn.setVisible(False)
            self._save_as_btn.setVisible(False)

    def set_empty_hint_text(self, text: str) -> None:
        """设置空白提示文案。"""
        self._empty_hint_text = text
        if self._current_type == "empty":
            self._empty_hint.setText(text)

    def preview_file(self, file_path: Path) -> None:
        """预览文件

        Args:
            file_path: 文件路径
        """
        self._current_file = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == '.docx':
            self._preview_word(file_path)
        elif suffix == '.doc':
            self._show_empty("暂不支持 .doc 格式\n请将文件转换为 .docx 格式后预览")
        elif suffix == '.pdf':
            self._preview_pdf(file_path)
        elif suffix in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            self._preview_image(file_path)
        elif suffix in ['.txt', '.md']:
            self._preview_text_file(file_path)
        else:
            self._show_empty(f"不支持的文件格式: {suffix}")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._schedule_visual_refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_visual_refresh()

    def _preview_word(self, file_path: Path) -> None:
        """预览 Word 文档"""
        try:
            from docx import Document
            from zipfile import BadZipFile
            
            # 关闭PDF文档（如果打开）
            if self._pdf_doc:
                self._pdf_doc.close()
                self._pdf_doc = None

            doc = Document(str(file_path))
            text = "\n".join([p.text for p in doc.paragraphs])

            self._original_text = text
            self._current_type = "word"
            self._title_label.setText(file_path.name)
            self._type_label.setText("Word 文档")

            # 高亮变量
            self._highlight_text_with_variables(text)

            # 显示文本预览，隐藏图片容器
            self._empty_widget.setHidden(True)
            self._text_preview.setHidden(False)
            self._image_container.setHidden(True)

            # 显示保存按钮（仅Word文档）
            self._update_save_buttons_visibility(True)

        except BadZipFile:
            # 文件可能损坏或不是有效的 docx 文件
            self._logger.warning(f"文件格式不正确或已损坏: {file_path}")
            self._show_empty(f"无法打开文件: 文件格式不正确或已损坏")
        except Exception as e:
            self._logger.error(f"预览 Word 文档失败: {e}")
            self._show_empty(f"无法打开文件: {e}")

    def _preview_pdf(self, file_path: Path) -> None:
        """预览 PDF 文件 - 始终以图片形式渲染"""
        if fitz is None:
            self._show_empty("PDF 预览需要安装 PyMuPDF: pip install PyMuPDF")
            return
            
        try:
            # 关闭之前的PDF文档
            if self._pdf_doc:
                self._pdf_doc.close()
            
            # 打开新PDF文档
            self._pdf_doc = fitz.open(str(file_path))
            self._pdf_total_pages = len(self._pdf_doc)
            self._pdf_current_page = 0
            self._pdf_zoom = 1.0
            self._pdf_fit_mode = "width"
            
            # 更新界面
            self._current_type = "pdf"
            self._title_label.setText(file_path.name)
            self._type_label.setText(f"PDF 文档 ({self._pdf_total_pages} 页)")
            
            # 显示PDF工具栏和翻页控件
            self._pdf_toolbar.setVisible(True)
            self._page_nav_widget.setVisible(True)
            
            # 显示图片预览区域
            self._empty_widget.setHidden(True)
            self._text_preview.setHidden(True)
            self._image_container.setHidden(False)
            self._update_pdf_toolbar()
            self._do_visual_refresh()

            # PDF不支持保存，隐藏保存按钮
            self._update_save_buttons_visibility(False)

        except Exception as e:
            self._logger.error(f"预览 PDF 失败: {e}")
            self._show_empty(f"无法打开文件: {e}")

    def _render_pdf_page(self) -> None:
        """渲染当前PDF页面"""
        if not self._pdf_doc or self._pdf_total_pages == 0:
            return
        
        try:
            page = self._pdf_doc[self._pdf_current_page]
            rect = page.rect
            scroll_width = max(160, self._image_scroll.viewport().width() - 20)
            scroll_height = max(200, self._image_scroll.viewport().height() - 20)
            
            # 根据适应模式计算基础缩放比例
            if self._pdf_fit_mode == "original":
                base_zoom = 1.0
            elif self._pdf_fit_mode == "fit":
                # 适应窗口（考虑滚动条边距）
                zoom_x = scroll_width / rect.width
                zoom_y = scroll_height / rect.height
                base_zoom = min(zoom_x, zoom_y, 3.0)  # 最大3倍
            else:  # width 或 custom
                # 适应宽度
                base_zoom = min(scroll_width / rect.width, 3.0)
            
            # 应用用户缩放（仅在custom模式下）
            if self._pdf_fit_mode == "custom":
                zoom = base_zoom * self._pdf_zoom
            else:
                zoom = base_zoom
            
            # 保存实际显示比例用于显示
            self._actual_zoom = zoom

            mtime_ns = self._current_file.stat().st_mtime_ns if self._current_file and self._current_file.exists() else 0
            cache_key = (
                str(self._current_file),
                mtime_ns,
                self._pdf_current_page,
                self._pdf_fit_mode,
                round(zoom, 3),
                scroll_width,
                scroll_height,
            )
            cached = self._render_cache.get(cache_key)
            if cached is not None:
                self._render_cache.move_to_end(cache_key)
                self._image_label.setScaledContents(False)
                self._image_label.setPixmap(cached)
                self._image_label.resize(cached.size())
                self._update_pdf_toolbar()
                return
            
            # 渲染页面
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # 转换为 QImage
            img_data = pix.tobytes("png")
            qimg = QImage.fromData(QByteArray(img_data))
            
            if qimg.isNull():
                raise ValueError("无法渲染PDF页面")
            
            # 显示图片
            pixmap = QPixmap.fromImage(qimg)
            self._render_cache[cache_key] = pixmap
            self._render_cache.move_to_end(cache_key)
            while len(self._render_cache) > self._render_cache_limit:
                self._render_cache.popitem(last=False)
            self._image_label.setScaledContents(False)
            self._image_label.setPixmap(pixmap)
            self._image_label.resize(pixmap.size())
            
            # 更新工具栏
            self._update_pdf_toolbar()
            
        except Exception as e:
            self._logger.error(f"渲染PDF页面失败: {e}")

    def _update_pdf_toolbar(self) -> None:
        """更新PDF工具栏状态"""
        # 更新页码显示
        self._page_input.setText(str(self._pdf_current_page + 1))
        self._page_label.setText(f"/ {self._pdf_total_pages}")
        
        # 更新翻页按钮状态
        self._prev_btn.setEnabled(self._pdf_current_page > 0)
        self._next_btn.setEnabled(self._pdf_current_page < self._pdf_total_pages - 1)
        
        # 更新缩放显示（显示实际缩放比例）
        actual_zoom = getattr(self, '_actual_zoom', self._pdf_zoom)
        zoom_percent = int(actual_zoom * 100)
        self._zoom_label.setText(f"{zoom_percent}%")
        self._update_fit_buttons_state()

    def _on_pdf_prev_page(self) -> None:
        """上一页"""
        if self._pdf_current_page > 0:
            self._pdf_current_page -= 1
            self._render_pdf_page()

    def _on_pdf_next_page(self) -> None:
        """下一页"""
        if self._pdf_current_page < self._pdf_total_pages - 1:
            self._pdf_current_page += 1
            self._render_pdf_page()

    def _on_pdf_page_jump(self) -> None:
        """跳转到指定页"""
        try:
            page_num = int(self._page_input.text()) - 1  # 转换为0-based
            page_num = max(0, min(page_num, self._pdf_total_pages - 1))
            self._pdf_current_page = page_num
            self._render_pdf_page()
        except ValueError:
            pass  # 输入无效，忽略

    def _on_pdf_zoom_in(self) -> None:
        """放大"""
        if self._pdf_zoom < 5.0:  # 最大500%
            self._pdf_zoom = min(5.0, self._pdf_zoom * 1.25)
            self._pdf_fit_mode = "custom"
            if self._current_type == "image":
                self._render_image()
            else:
                self._render_pdf_page()

    def _on_pdf_zoom_out(self) -> None:
        """缩小"""
        if self._pdf_zoom > 0.1:  # 最小10%
            self._pdf_zoom = max(0.1, self._pdf_zoom / 1.25)
            self._pdf_fit_mode = "custom"
            if self._current_type == "image":
                self._render_image()
            else:
                self._render_pdf_page()

    def _on_pdf_fit_mode(self, mode: str) -> None:
        """设置适应模式"""
        self._pdf_fit_mode = mode
        self._pdf_zoom = 1.0  # 重置用户缩放
        if self._current_type == "image":
            self._render_image()
        else:
            self._render_pdf_page()

    def _render_image(self) -> None:
        """根据当前适应模式渲染图片"""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return

        try:
            scroll = self._image_scroll
            scroll_w = scroll.viewport().width() - 20
            scroll_h = scroll.viewport().height() - 20
            orig_w = self._original_pixmap.width()
            orig_h = self._original_pixmap.height()

            if orig_w == 0 or orig_h == 0:
                return

            # 计算缩放比例
            if self._pdf_fit_mode == "original":
                zoom = 1.0
            elif self._pdf_fit_mode == "fit":
                zoom = min(scroll_w / orig_w, scroll_h / orig_h, 3.0)
            elif self._pdf_fit_mode == "width":
                zoom = min(scroll_w / orig_w, 3.0)
            elif self._pdf_fit_mode == "custom":
                base_zoom = min(scroll_w / orig_w, 3.0)
                zoom = base_zoom * self._pdf_zoom
            else:
                zoom = 1.0

            zoom = max(0.1, min(zoom, 5.0))
            self._actual_zoom = zoom

            new_w = int(orig_w * zoom)
            new_h = int(orig_h * zoom)
            scaled = self._original_pixmap.scaled(
                new_w, new_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self._image_label.setScaledContents(False)
            self._image_label.setPixmap(scaled)
            self._image_label.resize(scaled.size())

            # 更新工具栏
            self._zoom_label.setText(f"{int(zoom * 100)}%")
            self._update_fit_buttons_state()

        except Exception as e:
            self._logger.error(f"渲染图片失败: {e}")

    def _update_fit_buttons_state(self) -> None:
        """更新适应模式按钮的选中状态"""
        self._fit_width_btn.setChecked(self._pdf_fit_mode == "width")
        self._fit_page_btn.setChecked(self._pdf_fit_mode == "fit")
        self._original_size_btn.setChecked(self._pdf_fit_mode == "original")

    def _preview_image(self, file_path: Path) -> None:
        """预览图片文件"""
        try:
            # 关闭PDF文档（如果打开）
            if self._pdf_doc:
                self._pdf_doc.close()
                self._pdf_doc = None

            pixmap = QPixmap(str(file_path))
            if pixmap.isNull():
                raise ValueError("无法加载图片")

            # 保存原始图片用于缩放
            self._original_pixmap = pixmap
            self._pdf_zoom = 1.0
            self._pdf_fit_mode = "width"

            self._current_type = "image"
            self._title_label.setText(file_path.name)
            self._type_label.setText("图片文件")

            # 显示图片预览和工具栏
            self._empty_widget.setHidden(True)
            self._text_preview.setHidden(True)
            self._pdf_toolbar.setVisible(True)
            self._image_container.setHidden(False)

            # 隐藏翻页控件（图片无翻页），显示缩放控件
            self._page_nav_widget.setVisible(False)

            # 渲染适应宽度
            self._do_visual_refresh()

            # 图片不支持保存，隐藏保存按钮
            self._update_save_buttons_visibility(False)

        except Exception as e:
            self._logger.error(f"预览图片失败: {e}")
            self._show_empty(f"无法打开文件: {e}")

    def _highlight_text_with_variables(self, text: str) -> None:
        """高亮文本中的变量（使用与Word模板制作器一致的绿色）"""
        cursor = self._text_preview.textCursor()

        # 设置高亮格式 - 使用绿色（与word_preview.py一致）
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor(212, 237, 218))  # 浅绿色背景
        highlight_format.setForeground(QColor(21, 87, 36))     # 深绿色文字
        highlight_format.setFont(QFont(get_default_monospace_font_family(), 12, QFont.Weight.Bold))

        # 设置默认格式
        default_format = QTextCharFormat()
        default_format.setFont(QFont(get_default_ui_font_family(), 12))

        # 清除现有内容
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.removeSelectedText()

        # 分割文本并高亮变量
        last_end = 0
        for match in self.VARIABLE_PATTERN.finditer(text):
            # 插入变量前的普通文本
            if match.start() > last_end:
                normal_text = text[last_end:match.start()]
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(normal_text, default_format)

            # 插入变量（高亮）
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(match.group(0), highlight_format)

            last_end = match.end()

        # 插入最后的普通文本
        if last_end < len(text):
            remaining_text = text[last_end:]
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(remaining_text, default_format)

    def _preview_text_file(self, file_path: Path) -> None:
        """预览文本文件（.txt / .md）"""
        try:
            content = file_path.read_text(encoding='utf-8')
            self._current_type = 'text'

            if file_path.suffix.lower() == '.md':
                self._type_label.setText("Markdown")
                self._render_markdown(content)
            else:
                self._type_label.setText("文本文件")
                self._text_preview.setPlainText(content)

            self._title_label.setText(f"  {file_path.name}")
            self._pdf_toolbar.setVisible(False)
            self._empty_widget.setVisible(False)
            self._image_container.setVisible(False)
            self._text_preview.setVisible(True)
        except Exception as e:
            self._show_empty(f"无法打开文件: {e}")

    def _render_markdown(self, text: str) -> None:
        """简易 Markdown 渲染到 QTextEdit（标题加粗加大、列表缩进）"""
        self._text_preview.clear()

        body_format = QTextCharFormat()
        body_format.setFont(QFont(get_default_ui_font_family(), 11))

        heading1 = QTextCharFormat()
        heading1.setFontWeight(QFont.Weight.Bold)
        heading1.setFontPointSize(16)

        heading2 = QTextCharFormat()
        heading2.setFontWeight(QFont.Weight.Bold)
        heading2.setFontPointSize(14)

        heading3 = QTextCharFormat()
        heading3.setFontWeight(QFont.Weight.Bold)
        heading3.setFontPointSize(12)

        cursor = self._text_preview.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        for line in text.split('\n'):
            if line.startswith('### '):
                cursor.insertText(line[4:] + '\n', heading3)
            elif line.startswith('## '):
                cursor.insertText(line[3:] + '\n', heading2)
            elif line.startswith('# '):
                cursor.insertText(line[2:] + '\n', heading1)
            elif line.startswith('- ') or line.startswith('* '):
                cursor.insertText('  • ' + line[2:] + '\n', body_format)
            elif line.startswith('> '):
                italic = QTextCharFormat(body_format)
                italic.setFontItalic(True)
                italic.setForeground(QColor(COLORS['text_muted']))
                cursor.insertText('  ' + line[2:] + '\n', italic)
            else:
                cursor.insertText(line + '\n', body_format)

        cursor.movePosition(QTextCursor.MoveOperation.Start)

    def _show_empty(self, message: str = "") -> None:
        """显示空白提示"""
        # 关闭PDF文档（如果打开）
        if self._pdf_doc:
            self._pdf_doc.close()
            self._pdf_doc = None
        
        self._current_type = "empty"
        self._title_label.setText("文件预览")
        self._type_label.setText("")

        self._empty_widget.setHidden(False)
        self._text_preview.setHidden(True)
        self._image_container.setHidden(True)

        # 隐藏保存按钮
        self._update_save_buttons_visibility(False)

        if message:
            self._empty_hint.setText(message)

        else:
            self._empty_hint.setText(self._empty_hint_text)

    def _schedule_visual_refresh(self) -> None:
        """防抖：尺寸稳定 100ms 后才刷新 PDF/图片预览。"""
        if self._current_type in ("pdf", "image"):
            self._refresh_timer.start()

    def _do_visual_refresh(self) -> None:
        """执行实际的渲染刷新。"""
        if self._current_type == "pdf":
            self._render_pdf_page()
        elif self._current_type == "image":
            self._render_image()

    def _show_context_menu(self, position: QPoint) -> None:
        """显示右键菜单"""
        if self._current_type not in ("word", "pdf"):
            return

        # 获取选中的文本
        cursor = self._text_preview.textCursor()
        if not cursor.hasSelection():
            return

        selected_text = self._get_selected_text_from_cursor(cursor)

        if not selected_text.strip():
            return

        # 创建菜单
        menu = QMenu(self)
        menu.setStyleSheet(self._get_menu_style())

        # 设置为变量
        set_var_menu = menu.addMenu("设置为变量")
        for var in self._variables:
                action = set_var_menu.addAction(f"{var['name']} ({{{{{var['key']}}}}})")
                action.triggered.connect(
                    lambda checked, k=var['key']: self._on_set_variable(k)
                )

        menu.addSeparator()

        # 定义为变量字段
        def_var_menu = menu.addMenu("定义为变量字段")
        for var in self._variables:
                action = def_var_menu.addAction(f"{var['name']} ({{{{{var['key']}}}}})")
                action.triggered.connect(
                    lambda checked, k=var['key']: self._on_define_field(k)
                )

        menu.exec_(self._text_preview.mapToGlobal(position))

    def _get_menu_style(self) -> str:
        """获取菜单样式"""
        c = COLORS
        return f"""
            QMenu {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
                color: {c['text_secondary']};
            }}
            QMenu::item:selected {{
                background-color: {c['accent_light']};
                color: {c['accent']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {c['border']};
                margin: 4px 8px;
            }}
        """

    def _get_selected_text_from_cursor(self, cursor: QTextCursor) -> str:
        """获取光标选中的原始文本。"""
        plain_text = self._text_preview.toPlainText()
        return plain_text[cursor.selectionStart():cursor.selectionEnd()]

    def _on_set_variable(self, var_key: str) -> None:
        """设置为变量 - 替换选中文本为变量占位符并高亮"""
        cursor = self._text_preview.textCursor()
        if not cursor.hasSelection():
            return

        text = self._get_selected_text_from_cursor(cursor)
        selection_info = {
            "selection_start": cursor.selectionStart(),
            "selection_end": cursor.selectionEnd(),
        }

        # 替换选中的文本为变量占位符
        cursor.insertText(f"{{{{{var_key}}}}}")

        # 更新原始文本
        self._original_text = self._text_preview.toPlainText()

        # 重新高亮所有变量
        self._highlight_text_with_variables(self._original_text)

        # 发送信号
        self.variable_set.emit(var_key, text, selection_info)

    def _on_define_field(self, var_key: str) -> None:
        """定义为变量字段"""
        cursor = self._text_preview.textCursor()
        if not cursor.hasSelection():
            return
        text = self._get_selected_text_from_cursor(cursor)
        self.field_defined.emit(var_key, text)

    def get_selected_text(self) -> str:
        """获取当前选中的文本"""
        if self._current_type in ("word", "pdf"):
            cursor = self._text_preview.textCursor()
            return cursor.selectedText().strip().replace('\u2029', '\n')
        return ""

    def clear(self) -> None:
        """清空预览"""
        # 关闭PDF文档（如果打开）
        if self._pdf_doc:
            self._pdf_doc.close()
            self._pdf_doc = None
        
        self._current_file = None
        self._current_type = "empty"
        self._original_text = ""
        self._text_preview.clear()
        self._image_label.clear()
        self._show_empty()

    def get_current_content(self) -> str:
        """获取当前预览的文本内容
        
        Returns:
            当前显示的文本内容（包含变量占位符）
        """
        if self._current_type in ("word", "pdf"):
            return self._text_preview.toPlainText()
        return ""

    def get_current_file_path(self) -> Optional[Path]:
        """获取当前预览的文件路径
        
        Returns:
            当前文件路径，如果没有则返回None
        """
        return self._current_file

    def _on_save_clicked(self) -> None:
        """保存按钮点击"""
        if self._current_file and self._current_type == "word":
            self.save_requested.emit()

    def _on_save_as_clicked(self) -> None:
        """另存为按钮点击"""
        if self._current_type == "word":
            self.save_as_requested.emit()

    def _update_save_buttons_visibility(self, visible: bool) -> None:
        """更新保存按钮的可见性
        
        Args:
            visible: 是否显示按钮
        """
        actual_visible = visible and self._save_actions_enabled
        self._save_btn.setVisible(actual_visible)
        self._save_as_btn.setVisible(actual_visible)

    # 拖拽支持
    def dragEnterEvent(self, event) -> None:
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        if urls:
            file_path = Path(urls[0].toLocalFile())
            self.preview_file(file_path)
