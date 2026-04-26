# -*- coding: utf-8 -*-
"""图片列表控件模块"""

import os
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QMenu, QStackedWidget,
    QSplitter, QScrollArea, QFrame, QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QKeyEvent, QWheelEvent, QDragEnterEvent, QDropEvent

from src.core.ocr.document_parser import DocumentType, DocumentParser
from src.utils.pdf_utils import get_pdf_processor


@dataclass
class ImageItem:
    """图片项数据"""
    file_path: str
    file_name: str
    doc_type: DocumentType = DocumentType.UNKNOWN
    thumbnail: Optional[QPixmap] = None


class ImageListWidget(QWidget):
    """图片列表控件 - 带图片预览功能"""
    
    # 信号
    image_added = Signal(str)           # 图片添加信号（文件路径）
    image_removed = Signal(str)         # 图片移除信号（文件路径）
    image_selected = Signal(str)        # 图片选中信号（文件路径）
    images_changed = Signal(list)       # 图片列表变化信号（文件路径列表）
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._images: List[ImageItem] = []
        self._supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
        self._current_preview_path: Optional[str] = None
        self._original_pixmap: Optional[QPixmap] = None  # 原始图片
        self._zoom_scale: float = 1.0  # 当前缩放比例
        self._min_zoom: float = 0.1  # 最小缩放
        self._max_zoom: float = 5.0  # 最大缩放
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题
        title_layout = QHBoxLayout()
        self._title_label = QLabel("待识别文件")
        self._title_label.setStyleSheet("font-weight: bold;")
        title_layout.addWidget(self._title_label)
        
        self._count_label = QLabel("(0)")
        self._count_label.setStyleSheet("color: gray;")
        title_layout.addWidget(self._count_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # ===== 创建垂直分割器：上方预览区域 + 下方文件列表 =====
        self._left_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 图片预览区域（带缩放功能）
        self._preview_container = QWidget()
        preview_layout = QVBoxLayout(self._preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(4)
        
        # 缩放控制工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(4)
        
        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setToolTip("缩小 (Ctrl+-)")
        self._zoom_out_btn.setFixedSize(28, 28)
        self._zoom_out_btn.setStyleSheet("QPushButton { font-weight: bold; font-size: 14px; }")
        self._zoom_out_btn.clicked.connect(self._zoom_out)
        toolbar_layout.addWidget(self._zoom_out_btn)
        
        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(50)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet("font-size: 11px; color: #666;")
        toolbar_layout.addWidget(self._zoom_label)
        
        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setToolTip("放大 (Ctrl++)")
        self._zoom_in_btn.setFixedSize(28, 28)
        self._zoom_in_btn.setStyleSheet("QPushButton { font-weight: bold; font-size: 14px; }")
        self._zoom_in_btn.clicked.connect(self._zoom_in)
        toolbar_layout.addWidget(self._zoom_in_btn)
        
        self._zoom_reset_btn = QPushButton("重置")
        self._zoom_reset_btn.setToolTip("重置缩放 (Ctrl+0)")
        self._zoom_reset_btn.setFixedHeight(28)
        self._zoom_reset_btn.clicked.connect(self._zoom_reset)
        toolbar_layout.addWidget(self._zoom_reset_btn)
        
        self._zoom_fit_btn = QPushButton("适应")
        self._zoom_fit_btn.setToolTip("适应窗口")
        self._zoom_fit_btn.setFixedHeight(28)
        self._zoom_fit_btn.clicked.connect(self._zoom_fit)
        toolbar_layout.addWidget(self._zoom_fit_btn)
        
        toolbar_layout.addStretch()
        preview_layout.addLayout(toolbar_layout)
        
        # 图片显示区域（使用滚动区域支持大图）
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
        """)
        
        # 预览标签（显示图片）
        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet("background-color: transparent;")
        self._preview_label.setText("选择文件查看预览")
        
        # 安装事件过滤器以支持鼠标滚轮缩放
        self._scroll_area.viewport().installEventFilter(self)
        
        self._scroll_area.setWidget(self._preview_label)
        preview_layout.addWidget(self._scroll_area, 1)
        
        # 占位符（没有预览时）
        self._no_preview_label = QLabel("暂无预览\n\n添加单个图片或PDF\n可在此查看预览")
        self._no_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_preview_label.setStyleSheet("""
            QLabel {
                color: #999;
                background-color: #f5f5f5;
                border: 1px dashed #ccc;
                border-radius: 4px;
                padding: 20px;
            }
        """)
        
        # 堆叠控件切换有无预览状态
        self._preview_widget = QStackedWidget()
        self._preview_widget.addWidget(self._no_preview_label)
        self._preview_widget.addWidget(self._preview_container)
        self._preview_widget.setCurrentIndex(0)  # 默认显示无预览
        self._preview_widget.setMinimumHeight(200)
        self._preview_widget.setMaximumHeight(600)
        
        self._left_splitter.addWidget(self._preview_widget)
        
        # 列表控件
        self._list_widget = QListWidget()
        self._list_widget.setIconSize(QSize(48, 48))
        self._list_widget.setMinimumHeight(100)
        self._list_widget.setMaximumHeight(300)
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self._list_widget.itemClicked.connect(self._on_item_clicked)
        self._list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list_widget.keyPressEvent = self._on_key_press
        
        # 启用拖拽功能
        self._list_widget.setAcceptDrops(True)
        self._list_widget.dragEnterEvent = self._drag_enter_event
        self._list_widget.dragMoveEvent = self._drag_move_event
        self._list_widget.dropEvent = self._drop_event
        
        # 设置样式
        self._list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #fafafa;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border-left: 3px solid #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        self._left_splitter.addWidget(self._list_widget)
        
        # 设置分割器默认比例（预览区域占更多空间）
        self._left_splitter.setSizes([300, 30, 150])
        self._left_splitter.setStretchFactor(0, 3)  # 预览区域拉伸因子
        self._left_splitter.setStretchFactor(1, 0)  # 提示标签不拉伸
        self._left_splitter.setStretchFactor(2, 1)  # 列表区域拉伸因子
        
        layout.addWidget(self._left_splitter, 1)  # 添加 stretch factor 让其占据主要空间
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self._add_btn = QPushButton("+ 添加图片/PDF")
        self._add_btn.setToolTip("支持 JPG、PNG、BMP、TIFF、PDF 格式")
        self._add_btn.clicked.connect(self._on_add_files)
        btn_layout.addWidget(self._add_btn)
        
        self._clear_btn = QPushButton("清空")
        self._clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self._clear_btn)
        
        layout.addLayout(btn_layout)
        
        # 粘贴输入框
        self._paste_edit = QLineEdit()
        self._paste_edit.setPlaceholderText("截图贴入，输入文字无效")
        self._paste_edit.setStyleSheet("""
            QLineEdit {
                border: 1px dashed #aaa;
                border-radius: 4px;
                padding: 8px 12px;
                background-color: #f8f8f8;
                color: #666;
            }
            QLineEdit:focus {
                border: 1px dashed #1976d2;
                background-color: #e3f2fd;
            }
        """)
        self._paste_edit.setToolTip("在此按 Ctrl+V 粘贴截图")
        # 安装事件过滤器以捕获粘贴事件
        self._paste_edit.installEventFilter(self)
        layout.addWidget(self._paste_edit)
        
        # 提示标签（显示在列表下方）
        self._hint_label = QLabel("拖拽文件到此处或点击添加")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet("color: gray; font-size: 12px; padding: 10px;")
        layout.addWidget(self._hint_label)
    
    def _update_preview(self, file_path: Optional[str] = None):
        """
        更新图片预览
        
        Args:
            file_path: 要预览的文件路径，None 表示清除预览
        """
        if file_path is None or not os.path.exists(file_path):
            self._preview_widget.setCurrentIndex(0)  # 显示无预览
            self._current_preview_path = None
            self._reset_zoom()
            return
        
        ext = Path(file_path).suffix.lower()
        
        try:
            if ext == '.pdf':
                # PDF 转换为图片预览
                pdf_processor = get_pdf_processor()
                if pdf_processor.is_available():
                    import tempfile
                    with tempfile.TemporaryDirectory() as temp_dir:
                        images = pdf_processor.convert_to_images(file_path, temp_dir, (1, 1))
                        if images:
                            pixmap = QPixmap(images[0])
                            self._show_pixmap(pixmap)
                        else:
                            self._preview_label.setText("PDF 预览失败")
                            self._preview_widget.setCurrentIndex(1)
                else:
                    self._preview_label.setText("PDF 预览不可用")
                    self._preview_widget.setCurrentIndex(1)
            else:
                # 直接显示图片
                pixmap = QPixmap(file_path)
                self._show_pixmap(pixmap)
            
            self._current_preview_path = file_path
            
        except Exception as e:
            self._preview_label.setText(f"预览加载失败:\n{str(e)}")
            self._preview_widget.setCurrentIndex(1)
    
    def _show_pixmap(self, pixmap: QPixmap):
        """显示缩放后的图片"""
        if pixmap.isNull():
            self._preview_label.setText("无法加载图片")
            self._preview_widget.setCurrentIndex(1)
            return
        
        # 保存原始图片
        self._original_pixmap = pixmap
        
        # 计算适应窗口的缩放比例
        margin = 40
        available_width = max(self._scroll_area.viewport().width() - margin, 100)
        available_height = max(self._scroll_area.viewport().height() - margin, 100)
        
        fit_scale = min(
            available_width / pixmap.width(),
            available_height / pixmap.height(),
            1.0  # 不超过原始大小
        )
        
        # 如果当前缩放为 1.0（首次加载），使用适应窗口的比例
        if self._zoom_scale == 1.0:
            self._zoom_scale = max(fit_scale, 0.1)
        
        # 应用缩放
        self._apply_zoom()
        self._preview_widget.setCurrentIndex(1)
    
    def _apply_zoom(self):
        """应用当前缩放比例"""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        
        # 计算缩放后的尺寸
        new_width = int(self._original_pixmap.width() * self._zoom_scale)
        new_height = int(self._original_pixmap.height() * self._zoom_scale)
        
        # 缩放图片
        scaled_pixmap = self._original_pixmap.scaled(
            new_width, new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self._preview_label.setPixmap(scaled_pixmap)
        self._preview_label.setFixedSize(scaled_pixmap.size())
        
        # 更新缩放比例显示
        self._zoom_label.setText(f"{int(self._zoom_scale * 100)}%")
        
        # 更新按钮状态
        self._zoom_out_btn.setEnabled(self._zoom_scale > self._min_zoom)
        self._zoom_in_btn.setEnabled(self._zoom_scale < self._max_zoom)
    
    def _zoom_in(self):
        """放大"""
        if self._zoom_scale < self._max_zoom:
            self._zoom_scale = min(self._zoom_scale * 1.25, self._max_zoom)
            self._apply_zoom()
    
    def _zoom_out(self):
        """缩小"""
        if self._zoom_scale > self._min_zoom:
            self._zoom_scale = max(self._zoom_scale / 1.25, self._min_zoom)
            self._apply_zoom()
    
    def _zoom_reset(self):
        """重置缩放为原始大小"""
        self._zoom_scale = 1.0
        self._apply_zoom()
    
    def _zoom_fit(self):
        """适应窗口"""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        
        margin = 40
        available_width = max(self._scroll_area.viewport().width() - margin, 100)
        available_height = max(self._scroll_area.viewport().height() - margin, 100)
        
        fit_scale = min(
            available_width / self._original_pixmap.width(),
            available_height / self._original_pixmap.height()
        )
        
        self._zoom_scale = max(fit_scale, 0.1)
        self._apply_zoom()
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 支持鼠标滚轮缩放和粘贴"""
        # 处理粘贴输入框的粘贴事件（先检查，因为_scroll_area也可能触发）
        if hasattr(self, '_paste_edit') and obj == self._paste_edit:
            if event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self._handle_paste()
                    return True
            # 对于粘贴输入框的其他事件，不处理，让默认行为生效
            return False
        
        # 处理滚动区域滚轮缩放
        if obj == self._scroll_area.viewport() and isinstance(event, QWheelEvent):
            # Ctrl + 滚轮缩放
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self._zoom_in()
                else:
                    self._zoom_out()
                return True
        
        return super().eventFilter(obj, event)
    
    def _drag_enter_event(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def _drag_move_event(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def _drop_event(self, event: QDropEvent):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        if urls:
            file_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if file_paths:
                self.add_files(file_paths)
            event.acceptProposedAction()
    
    def _handle_paste(self):
        """处理粘贴事件"""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QImage
        import tempfile
        
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        # 检查是否有图片数据
        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                # 保存为临时文件
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, f"pasted_image_{id(image)}.png")
                
                if image.save(temp_path, "PNG"):
                    self.add_files([temp_path])
                    # 清空输入框
                    self._paste_edit.clear()
                    QMessageBox.information(self, "粘贴成功", "图片已添加到识别列表")
                else:
                    QMessageBox.warning(self, "粘贴失败", "无法保存粘贴的图片")
            else:
                QMessageBox.warning(self, "粘贴失败", "剪贴板中没有图片")
        elif mime_data.hasText():
            # 如果是文本，尝试作为文件路径处理
            text = mime_data.text()
            if os.path.isfile(text):
                self.add_files([text])
                self._paste_edit.clear()
            else:
                QMessageBox.warning(self, "粘贴失败", "剪贴板中是文字，不是图片\n请使用截图工具（如QQ/微信截图）后按Ctrl+V粘贴")
        else:
            QMessageBox.warning(self, "粘贴失败", "剪贴板中没有图片数据")
    
    def _on_add_files(self):
        """添加文件按钮点击"""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("选择图片或 PDF 文件")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        
        # 设置过滤器
        filters = [
            "图片和 PDF (*.jpg *.jpeg *.png *.bmp *.tiff *.pdf)",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff)",
            "PDF 文件 (*.pdf)",
            "所有文件 (*.*)"
        ]
        file_dialog.setNameFilters(filters)
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            self.add_files(selected_files)
    
    def add_files(self, file_paths: List[str]):
        """
        添加文件到列表
        
        Args:
            file_paths: 文件路径列表
        """
        added_count = 0
        
        for file_path in file_paths:
            # 检查格式
            ext = Path(file_path).suffix.lower()
            if ext not in self._supported_formats:
                continue
            
            # 检查是否已存在
            if any(img.file_path == file_path for img in self._images):
                continue
            
            # 创建图片项
            item = ImageItem(
                file_path=file_path,
                file_name=Path(file_path).name
            )
            self._images.append(item)
            
            # 添加到列表控件
            list_item = QListWidgetItem()
            list_item.setText(item.file_name)
            list_item.setData(Qt.ItemDataRole.UserRole, file_path)
            
            # 设置图标
            if ext == '.pdf':
                list_item.setIcon(self._get_file_icon("pdf"))
            else:
                list_item.setIcon(self._get_file_icon("image"))
            
            self._list_widget.addItem(list_item)
            
            self.image_added.emit(file_path)
            added_count += 1
        
        if added_count > 0:
            self._update_count()
            self.images_changed.emit([img.file_path for img in self._images])
            
            # 如果只有单个文件，自动显示预览
            if len(self._images) == 1:
                self._update_preview(self._images[0].file_path)
                self._list_widget.setCurrentRow(0)
        
        return added_count
    
    def _get_file_icon(self, icon_type: str) -> QIcon:
        """获取文件图标（简化版）"""
        return QIcon()
    
    def remove_file(self, file_path: str):
        """
        移除指定文件
        
        Args:
            file_path: 文件路径
        """
        # 从数据列表中移除
        self._images = [img for img in self._images if img.file_path != file_path]
        
        # 从列表控件中移除
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                self._list_widget.takeItem(i)
                break
        
        self._update_count()
        self.image_removed.emit(file_path)
        self.images_changed.emit([img.file_path for img in self._images])
        
        # 更新预览
        if self._current_preview_path == file_path:
            if len(self._images) == 1:
                self._update_preview(self._images[0].file_path)
            else:
                self._update_preview(None)
    
    def _clear_all(self):
        """清空所有文件"""
        if not self._images:
            return
        
        reply = QMessageBox.question(
            self,
            "确认清空",
            f"确定要清空所有 {len(self._images)} 个文件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear()
    
    def clear(self):
        """清空列表"""
        self._images.clear()
        self._list_widget.clear()
        self._update_count()
        self._update_preview(None)
        self._reset_zoom()
        self.images_changed.emit([])
    
    def _reset_zoom(self):
        """重置缩放状态"""
        self._zoom_scale = 1.0
        self._original_pixmap = None
        self._zoom_label.setText("100%")
    
    def _update_count(self):
        """更新计数显示"""
        self._count_label.setText(f"({len(self._images)})")
        
        # 更新提示文字
        if len(self._images) == 0:
            self._hint_label.setText("拖拽文件到此处或点击添加")
        elif len(self._images) == 1:
            self._hint_label.setText("✓ 已添加 1 个文件，左侧显示预览")
        else:
            self._hint_label.setText(f"✓ 已添加 {len(self._images)} 个文件")
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """列表项点击"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        self._current_preview_path = file_path
        self._update_preview(file_path)
        self.image_selected.emit(file_path)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """列表项双击 - 预览图片"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        self._update_preview(file_path)
    
    def _on_key_press(self, event: QKeyEvent):
        """键盘事件处理"""
        if event.key() == Qt.Key.Key_Delete:
            # 删除键删除选中项
            current_item = self._list_widget.currentItem()
            if current_item:
                file_path = current_item.data(Qt.ItemDataRole.UserRole)
                self.remove_file(file_path)
        else:
            # 调用父类方法
            QListWidget.keyPressEvent(self._list_widget, event)
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        item = self._list_widget.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # 预览
        preview_action = menu.addAction("查看预览")
        preview_action.triggered.connect(lambda: self._on_item_double_clicked(item))
        
        menu.addSeparator()
        
        # 删除
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.remove_file(
            item.data(Qt.ItemDataRole.UserRole)
        ))
        
        menu.exec(self._list_widget.mapToGlobal(position))
    
    def get_all_files(self) -> List[str]:
        """获取所有文件路径"""
        return [img.file_path for img in self._images]
    
    def get_selected_file(self) -> Optional[str]:
        """获取当前选中的文件路径"""
        item = self._list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
    
    def set_document_type(self, file_path: str, doc_type: DocumentType):
        """
        设置文件的文档类型
        
        Args:
            file_path: 文件路径
            doc_type: 文档类型
        """
        for img in self._images:
            if img.file_path == file_path:
                img.doc_type = doc_type
                # 更新列表项显示
                for i in range(self._list_widget.count()):
                    item = self._list_widget.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == file_path:
                        type_name = DocumentParser.DOCUMENT_TYPE_NAMES.get(doc_type, '未知')
                        item.setText(f"{img.file_name}\n[{type_name}]")
                        break
                break
    
    def setCurrentItemByPath(self, file_path: str):
        """根据路径设置当前选中项"""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                self._list_widget.setCurrentItem(item)
                self._update_preview(file_path)
                break
    
    def resizeEvent(self, event):
        """窗口大小改变时重新调整预览图"""
        super().resizeEvent(event)
        if self._current_preview_path and self._original_pixmap:
            # 保持当前缩放比例，只需重新应用
            self._apply_zoom()
    
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls]
        self.add_files(file_paths)
