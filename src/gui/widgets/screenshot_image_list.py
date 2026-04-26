# -*- coding: utf-8 -*-
"""截图合并功能的图片列表控件"""

from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QUrl
from PySide6.QtGui import QPixmap, QIcon, QDesktopServices

from src.gui.styles import APP_COLORS


class ScreenshotImageList(QListWidget):
    """截图合并功能的图片列表控件

    支持缩略图/列表视图切换、内部拖拽排序、外部文件拖放和右键菜单。
    """

    images_changed = Signal(list)

    # 支持的图片格式
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

    # 视图模式
    THUMB_SIZE = 120
    LIST_ROW_HEIGHT = 28
    THUMB_ROW_HEIGHT = 128

    def __init__(self, parent=None):
        super().__init__(parent)

        self._icon_mode = True  # True=缩略图, False=列表
        self._setup_ui()
        self._setup_signals()

    def _setup_ui(self):
        """设置界面"""
        c = APP_COLORS

        # 启用内部拖拽排序
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)

        # 启用外部拖放
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        # 设置右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # 设置图标大小
        self.setIconSize(QSize(self.THUMB_SIZE, self.THUMB_SIZE))

        # 设置样式
        self._apply_style()

        # 设置选择模式
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

    def _apply_style(self):
        """应用当前视图模式的样式"""
        c = APP_COLORS
        if self._icon_mode:
            item_height = self.THUMB_ROW_HEIGHT
        else:
            item_height = self.LIST_ROW_HEIGHT

        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                height: {item_height}px;
                padding: 4px 8px;
                border-radius: 8px;
                margin: 2px 0px;
            }}
            QListWidget::item:selected {{
                background-color: rgba(219, 234, 254, 0.5);
            }}
            QListWidget::item:hover {{
                background-color: {c['surface_2']};
            }}
            QListWidget::item:selected:hover {{
                background-color: rgba(219, 234, 254, 0.7);
            }}
        """)

    def toggle_view_mode(self):
        """切换缩略图/列表视图"""
        self._icon_mode = not self._icon_mode
        self.setIconSize(QSize(
            self.THUMB_SIZE if self._icon_mode else 0,
            self.THUMB_SIZE if self._icon_mode else 0
        ))
        self._apply_style()

        # 刷新所有 item 的图标
        for i in range(self.count()):
            item = self.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path is not None:
                self._refresh_item_icon(item, Path(path))

    def _refresh_item_icon(self, item: QListWidgetItem, path: Path):
        """刷新单个 item 的图标"""
        if self._icon_mode:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(
                    self.THUMB_SIZE, self.THUMB_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                item.setIcon(QIcon(thumbnail))
            item.setSizeHint(QSize(0, self.THUMB_ROW_HEIGHT))
        else:
            item.setIcon(QIcon())
            item.setSizeHint(QSize(0, self.LIST_ROW_HEIGHT))

    def _setup_signals(self):
        """连接信号"""
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def _is_image_file(self, path: Path) -> bool:
        """检查是否为支持的图片文件"""
        return path.suffix.lower() in self.SUPPORTED_FORMATS

    def _collect_images_from_path(self, path: Path) -> List[Path]:
        """从路径收集图片文件

        如果是文件夹，递归收集其中的图片文件。
        """
        images = []

        if path.is_file() and self._is_image_file(path):
            images.append(path)
        elif path.is_dir():
            for item in path.rglob('*'):
                if item.is_file() and self._is_image_file(item):
                    images.append(item)

        return images

    def _create_list_item(self, path: Path) -> QListWidgetItem:
        """创建列表项"""
        item = QListWidgetItem()
        item.setText(path.name)
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(str(path))
        self._refresh_item_icon(item, path)
        return item

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击打开图片"""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def add_images(self, paths: List[Path]) -> None:
        """添加图片（去重）"""
        if not paths:
            return

        existing_paths = set(self.get_ordered_paths())
        added = False

        for path in paths:
            path = Path(path)
            if not path.exists():
                continue

            # 收集图片文件（文件夹会递归展开）
            images = self._collect_images_from_path(path)

            for img_path in images:
                if img_path in existing_paths:
                    continue

                existing_paths.add(img_path)
                item = self._create_list_item(img_path)
                self.addItem(item)
                added = True

        if added:
            self.images_changed.emit(self.get_ordered_paths())

    def remove_selected(self) -> None:
        """移除选中项"""
        rows_to_remove = []
        for item in self.selectedItems():
            rows_to_remove.append(self.row(item))

        if not rows_to_remove:
            return

        # 从后往前删除，避免索引变化
        for row in sorted(rows_to_remove, reverse=True):
            self.takeItem(row)

        self.images_changed.emit(self.get_ordered_paths())

    def clear_all(self) -> None:
        """清空全部"""
        if self.count() == 0:
            return

        reply = QMessageBox.question(
            self,
            "确认清空",
            f"确定要清空全部 {self.count()} 张图片吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.clear()
            self.images_changed.emit([])

    def get_ordered_paths(self) -> List[Path]:
        """获取当前排序后的路径列表"""
        paths = []
        for i in range(self.count()):
            item = self.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path is not None:
                paths.append(path)
        return paths

    def set_images(self, paths: List[Path]) -> None:
        """重置列表"""
        self.clear()
        if paths:
            self.add_images(paths)
        else:
            self.images_changed.emit([])

    def _show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)

        # 移除选中
        remove_action = menu.addAction("移除选中")
        remove_action.setEnabled(bool(self.selectedItems()))
        remove_action.triggered.connect(self.remove_selected)

        menu.addSeparator()

        # 清空全部
        clear_action = menu.addAction("清空全部")
        clear_action.setEnabled(self.count() > 0)
        clear_action.triggered.connect(self.clear_all)

        menu.exec(self.mapToGlobal(position))

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """拖拽放下事件"""
        if event.mimeData().hasUrls():
            # 外部文件拖放
            urls = event.mimeData().urls()
            paths = [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
            if paths:
                self.add_images(paths)
            event.acceptProposedAction()
        else:
            # 内部拖拽排序
            old_paths = self.get_ordered_paths()
            super().dropEvent(event)
            new_paths = self.get_ordered_paths()
            if new_paths != old_paths:
                self.images_changed.emit(new_paths)

    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Delete:
            self.remove_selected()
        else:
            super().keyPressEvent(event)
