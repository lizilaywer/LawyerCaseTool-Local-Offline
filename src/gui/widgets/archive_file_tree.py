# -*- coding: utf-8 -*-
"""电子化归档 - 文件夹结构树控件

显示选择的案卷文件夹的完整目录结构。
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QAbstractItemView,
    QApplication,
    QMenu,
    QMessageBox,
    QInputDialog,
    QProgressDialog,
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QObject, QThread
from PySide6.QtGui import QAction, QKeyEvent

from src.utils.logger import get_logger
from src.utils.platform_utils import is_windows, is_macos, open_path
from src.gui.styles import APP_COLORS as COLORS
from src.gui.icon_utils import get_standard_icon


class _FileMoveWorker(QObject):
    """后台执行文件移动，避免大文件操作阻塞界面。"""

    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(self, source_path: Path, target_path: Path):
        super().__init__()
        self._source_path = source_path
        self._target_path = target_path

    def run(self) -> None:
        """在线程中执行真实移动。"""
        try:
            shutil.move(str(self._source_path), str(self._target_path))
        except Exception as e:
            self.failed.emit(str(e))
            return

        self.finished.emit(self._source_path, self._target_path)


class ArchiveFileTree(QTreeWidget):
    """文件夹结构树控件

    功能：
    - 显示文件夹的完整目录结构
    - 支持展开/收缩文件夹
    - 单击选中，双击打开文件
    - 支持拖拽移动文件
    - 文件和文件夹图标区分
    """

    # 信号
    file_double_clicked = Signal(Path)  # 双击文件
    file_clicked = Signal(Path)         # 单击文件
    folder_clicked = Signal(Path)       # 单击文件夹
    folder_double_clicked = Signal(Path)  # 双击文件夹
    file_moved = Signal(Path, Path)     # 文件移动 (源路径, 目标路径)
    structure_changed = Signal()        # 结构改变

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._root_path: Optional[Path] = None
        self._is_expanded = False
        self._lazy_mode: bool = False
        self._loaded_dirs: Optional[set] = None

        # 单击/双击区分定时器
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_click_timeout)
        self._pending_item: Optional[QTreeWidgetItem] = None
        self._pending_column: int = 0
        self._drag_source_data: Optional[Dict[str, Any]] = None
        self._active_move_thread: Optional[QThread] = None
        self._active_move_worker: Optional[_FileMoveWorker] = None
        self._move_progress_dialog: Optional[QProgressDialog] = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS

        self.setHeaderHidden(True)
        self.setIndentation(18)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setIconSize(QSize(16, 16))

        self.setStyleSheet(f"""
            QTreeWidget {{
                border: none;
                background: #ffffff;
                font-size: 13px;
                outline: none;
                alternate-background-color: #ffffff;
            }}
            QTreeWidget::viewport {{
                background: #ffffff;
            }}
            QTreeWidget::item {{
                padding: 5px 8px;
                border-radius: 4px;
                margin: 1px 6px;
                color: #475569;
                background: transparent;
            }}
            QTreeWidget::item:hover {{
                background: #f8fafc;
            }}
            QTreeWidget::item:selected {{
                background: transparent;
                color: #0f172a;
                font-weight: 500;
            }}
            QTreeWidget::item:selected:active {{
                background: transparent;
                color: #0f172a;
            }}
            QTreeWidget::item:selected:!active {{
                background: transparent;
                color: #0f172a;
            }}
        """)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemChanged.connect(self._on_item_renamed)
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)
        self.currentItemChanged.connect(self._on_current_item_changed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_lazy_mode(self, enabled: bool = True) -> None:
        """设置懒加载模式。启用后仅展开时加载子目录，提升大目录性能。"""
        self._lazy_mode = enabled
        self._loaded_dirs = set() if enabled else None

    def load_folder(self, folder_path: Path) -> None:
        """加载文件夹结构

        Args:
            folder_path: 文件夹路径
        """
        self._root_path = Path(folder_path)
        if not self._root_path.exists() or not self._root_path.is_dir():
            self._logger.error(f"文件夹不存在或不是目录: {folder_path}")
            return

        if self._lazy_mode:
            self._loaded_dirs = set()

        self.setUpdatesEnabled(False)
        self.clear()
        self._add_folder_items(self._root_path, self)
        self.setUpdatesEnabled(True)

        if not self._lazy_mode:
            self.expandAll()
            self._is_expanded = True

    def _add_folder_items(self, path: Path, parent) -> None:
        """添加文件夹内容（支持懒加载模式）

        Args:
            path: 当前路径
            parent: 父级（QTreeWidget 或 QTreeWidgetItem）
        """
        try:
            # 获取目录内容并排序（文件夹在前，文件在后）
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            for item in items:
                # 跳过隐藏文件和系统文件
                if item.name.startswith('.') or item.name == '__pycache__':
                    continue

                if item.is_dir():
                    # 文件夹
                    folder_item = QTreeWidgetItem([item.name])
                    folder_item.setIcon(0, get_standard_icon("folder"))
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "folder",
                        "path": str(item),
                        "name": item.name
                    })
                    folder_item.setExpanded(False)
                    folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsEditable)

                    if isinstance(parent, QTreeWidget):
                        parent.addTopLevelItem(folder_item)
                    else:
                        parent.addChild(folder_item)

                    if self._lazy_mode:
                        # 懒加载：添加占位子项使 Qt 显示展开箭头
                        placeholder = QTreeWidgetItem(["  ..."])
                        placeholder.setFlags(
                            placeholder.flags() & ~Qt.ItemFlag.ItemIsEditable
                        )
                        folder_item.addChild(placeholder)
                    else:
                        # 全量加载：递归
                        self._add_folder_items(item, folder_item)

                else:
                    # 文件
                    file_item = QTreeWidgetItem([item.name])
                    file_item.setIcon(0, get_standard_icon(self._get_file_icon_kind(item.name)))
                    file_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "file",
                        "path": str(item),
                        "name": item.name
                    })
                    file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsEditable)

                    if isinstance(parent, QTreeWidget):
                        parent.addTopLevelItem(file_item)
                    else:
                        parent.addChild(file_item)

        except PermissionError:
            self._logger.warning(f"权限不足: {path}")
        except Exception as e:
            self._logger.error(f"读取目录失败 {path}: {e}")

    def _get_file_icon_kind(self, filename: str) -> str:
        """根据文件名获取图标类型。"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''

        icon_map = {
            'docx': 'file',
            'doc': 'file',
            'pdf': 'file',
            'jpg': 'file',
            'jpeg': 'file',
            'png': 'file',
            'bmp': 'file',
            'gif': 'file',
            'txt': 'file',
            'md': 'file',
        }

        return icon_map.get(ext, 'file')

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """单击事件 - 延迟处理以区分双击"""
        self._pending_item = item
        self._pending_column = column
        self._click_timer.start(300)

    def _on_click_timeout(self) -> None:
        """单击定时器超时 - 触发预览/选中事件"""
        if not self._pending_item:
            return

        user_data = self._pending_item.data(0, Qt.ItemDataRole.UserRole)
        self._pending_item = None

        if not user_data:
            return

        item_type = user_data.get("type", "")
        item_path = user_data.get("path", "")
        if not item_path:
            return

        path_obj = Path(item_path)
        if item_type == "file":
            self.file_clicked.emit(path_obj)
        elif item_type == "folder":
            self.folder_clicked.emit(path_obj)

    def _on_current_item_changed(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
        """当前项变化时同步预览，保证嵌套目录中的文件切换也能即时生效。"""
        if current is None:
            return

        user_data = current.data(0, Qt.ItemDataRole.UserRole)
        if not user_data:
            return

        item_path = str(user_data.get("path", "")).strip()
        if not item_path:
            return

        path_obj = Path(item_path)
        if user_data.get("type") == "file":
            self.file_clicked.emit(path_obj)
        elif user_data.get("type") == "folder":
            self.folder_clicked.emit(path_obj)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """双击事件 - 文件直接打开，文件夹交给系统打开。"""
        # 取消待处理的单击
        self._click_timer.stop()
        self._pending_item = None

        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not user_data:
            return

        item_type = user_data.get("type", "")
        file_path = user_data.get("path", "")

        if item_type == "file" and file_path:
            self.file_double_clicked.emit(Path(file_path))
        elif item_type == "folder" and file_path:
            self.folder_double_clicked.emit(Path(file_path))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """键盘交互：F2 重命名，Enter 打开文件或文件夹。"""
        current_item = self.currentItem()

        if event.key() == Qt.Key.Key_F2 and current_item is not None:
            self._click_timer.stop()
            self._pending_item = None
            self.editItem(current_item, 0)
            event.accept()
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and current_item is not None:
            user_data = current_item.data(0, Qt.ItemDataRole.UserRole)
            if user_data and user_data.get("type") == "file":
                file_path = user_data.get("path", "")
                if file_path:
                    self.file_double_clicked.emit(Path(file_path))
                    event.accept()
                    return
            if user_data and user_data.get("type") == "folder":
                folder_path = user_data.get("path", "")
                if folder_path:
                    self.folder_double_clicked.emit(Path(folder_path))
                    event.accept()
                    return

        super().keyPressEvent(event)

    def startDrag(self, supportedActions) -> None:
        """记录拖拽源，供 drop 约束和实际移动使用。"""
        current_item = self.currentItem()
        user_data = current_item.data(0, Qt.ItemDataRole.UserRole) if current_item else None
        self._drag_source_data = dict(user_data) if user_data else None
        super().startDrag(supportedActions)

    def dragEnterEvent(self, event) -> None:
        """仅接受本树内部拖拽。"""
        if event.source() is self and self._drag_source_data:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        """限制拖拽目标：只允许拖到文件夹或根目录，不允许拖到文件项下。"""
        if event.source() is not self or not self._drag_source_data:
            event.ignore()
            return

        source_path = Path(self._drag_source_data.get("path", ""))
        source_type = str(self._drag_source_data.get("type", "")).strip()
        target_item = self.itemAt(self._event_point(event))
        destination_dir, _ = self._resolve_drop_directory(
            source_path,
            source_type,
            target_item,
            self.dropIndicatorPosition(),
        )
        if destination_dir is None:
            event.ignore()
            return
        event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """执行真实文件移动，并阻止文件拖到文件项下。"""
        if event.source() is not self or not self._drag_source_data:
            event.ignore()
            return

        source_data = dict(self._drag_source_data)
        self._drag_source_data = None

        source_path = Path(source_data.get("path", ""))
        source_type = str(source_data.get("type", "")).strip()
        if not source_path.exists():
            event.ignore()
            return

        target_item = self.itemAt(self._event_point(event))
        destination_dir, error_message = self._resolve_drop_directory(
            source_path,
            source_type,
            target_item,
            self.dropIndicatorPosition(),
        )
        if destination_dir is None:
            if error_message:
                self._logger.info(f"忽略无效拖拽目标: {error_message}")
            event.ignore()
            return

        target_path = destination_dir / source_path.name
        if target_path == source_path:
            event.ignore()
            return

        if not self._start_async_move(source_path, target_path):
            event.ignore()
            return

        event.acceptProposedAction()

    def _start_async_move(self, source_path: Path, target_path: Path) -> bool:
        """启动后台移动任务。"""
        if self._active_move_thread is not None and self._active_move_thread.isRunning():
            QMessageBox.information(self, "正在移动", "已有文件移动任务正在进行，请稍后再试。")
            return False

        worker = _FileMoveWorker(source_path, target_path)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_move_finished)
        worker.failed.connect(self._on_move_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_active_move)

        self._active_move_worker = worker
        self._active_move_thread = thread
        self._show_move_progress(source_path, target_path)
        thread.start()
        return True

    def _show_move_progress(self, source_path: Path, target_path: Path) -> None:
        """显示文件移动进度提示。"""
        dialog = QProgressDialog(
            f"正在移动：{source_path.name}\n目标：{target_path.parent}",
            "后台继续",
            0,
            0,
            self,
        )
        dialog.setWindowTitle("移动文件")
        dialog.setMinimumDuration(250)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.canceled.connect(
            lambda: self._logger.info("用户隐藏了移动进度窗口，文件移动仍在后台继续。")
        )
        self._move_progress_dialog = dialog
        dialog.show()

    def _on_move_finished(self, source_path: Path, target_path: Path) -> None:
        """移动完成后刷新结构并发送通知。"""
        if self._move_progress_dialog is not None:
            self._move_progress_dialog.close()
        self._logger.info(f"移动文件结构: {source_path} -> {target_path}")
        self.refresh()
        self._select_path(target_path)
        self.file_moved.emit(source_path, target_path)
        self.structure_changed.emit()

    def _on_move_failed(self, error_message: str) -> None:
        """移动失败提示。"""
        if self._move_progress_dialog is not None:
            self._move_progress_dialog.close()
        self._logger.error(f"移动文件失败: {error_message}")
        QMessageBox.warning(
            self,
            "移动失败",
            f"{error_message}\n\n原始文件结构已保留；如文件系统已部分移动，请刷新案卷结构后核对。",
        )

    def _clear_active_move(self) -> None:
        """清理后台移动任务引用。"""
        self._active_move_worker = None
        self._active_move_thread = None
        self._move_progress_dialog = None

    def _event_point(self, event) -> Any:
        """兼容 Qt6/QDropEvent 的坐标读取。"""
        if hasattr(event, "position"):
            return event.position().toPoint()
        return event.pos()

    def _resolve_drop_directory(
        self,
        source_path: Path,
        source_type: str,
        target_item: Optional[QTreeWidgetItem],
        drop_position,
    ) -> tuple[Optional[Path], str]:
        """计算允许的拖放目标目录。"""
        if not self._root_path:
            return None, "根目录未就绪"

        if target_item is None:
            destination_dir = self._root_path
        else:
            target_data = target_item.data(0, Qt.ItemDataRole.UserRole) or {}
            target_type = str(target_data.get("type", "")).strip()
            target_path_text = str(target_data.get("path", "")).strip()
            if not target_type or not target_path_text:
                return None, "目标项无效"

            target_path = Path(target_path_text)
            if drop_position == QAbstractItemView.DropIndicatorPosition.OnItem:
                if target_type != "folder":
                    return None, "文件不能作为子级容器"
                destination_dir = target_path
            else:
                destination_dir = target_path.parent

        if not destination_dir.exists() or not destination_dir.is_dir():
            return None, "目标目录不存在"

        if destination_dir == source_path.parent:
            return None, "同级位置调整不改变真实文件结构"

        if source_type == "folder":
            try:
                destination_dir.relative_to(source_path)
                return None, "文件夹不能拖入自己的子目录"
            except ValueError:
                pass

        target_path = destination_dir / source_path.name
        if target_path.exists():
            return None, f"目标已存在同名项: {target_path.name}"

        return destination_dir, ""

    def _select_path(self, path: Path) -> None:
        """刷新后重新选中目标路径。"""
        item = self._find_item_by_path(self.invisibleRootItem(), str(path))
        if item is not None:
            self.setCurrentItem(item)
            item.setSelected(True)

    def _find_item_by_path(self, parent_item: QTreeWidgetItem, path_text: str) -> Optional[QTreeWidgetItem]:
        for index in range(parent_item.childCount()):
            child = parent_item.child(index)
            user_data = child.data(0, Qt.ItemDataRole.UserRole) or {}
            if str(user_data.get("path", "")).strip() == path_text:
                return child
            matched = self._find_item_by_path(child, path_text)
            if matched is not None:
                return matched
        return None

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """节点展开 - 更新文件夹图标 + 懒加载子目录"""
        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if user_data and user_data.get("type") == "folder":
            item.setIcon(0, get_standard_icon("folder_open"))

            # 懒加载：展开时才加载子目录内容
            if self._lazy_mode and self._loaded_dirs is not None:
                dir_path = user_data.get("path", "")
                if dir_path and dir_path not in self._loaded_dirs:
                    self._loaded_dirs.add(dir_path)
                    # 移除占位子项
                    while item.childCount() > 0:
                        item.takeChild(0)
                    # 加载直接子项（不递归）
                    self._add_folder_items(Path(dir_path), item)

    def _on_item_collapsed(self, item: QTreeWidgetItem) -> None:
        """节点收缩 - 更新文件夹图标"""
        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if user_data and user_data.get("type") == "folder":
            item.setIcon(0, get_standard_icon("folder"))

    def _on_item_renamed(self, item: QTreeWidgetItem, column: int) -> None:
        """重命名完成事件"""
        # 断开信号防止递归
        self.itemChanged.disconnect(self._on_item_renamed)

        try:
            user_data = item.data(0, Qt.ItemDataRole.UserRole)
            if not user_data:
                return

            item_type = user_data.get("type", "")
            old_path = user_data.get("path", "")

            if item_type not in ("file", "folder") or not old_path:
                return

            new_name = item.text(0)

            if not new_name or new_name.strip() == "":
                self.refresh()
                return

            new_name = new_name.strip()
            old_path_obj = Path(old_path)

            # 检查名称是否变化
            if new_name == old_path_obj.name:
                return

            # 构建新路径
            new_path = old_path_obj.parent / new_name

            # 检查目标是否已存在
            if new_path.exists():
                QMessageBox.warning(self, "重命名失败", f"'{new_name}' 已存在")
                self.refresh()
                return

            # 执行重命名
            try:
                old_path_obj.rename(new_path)

                # 更新数据
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": item_type,
                    "path": str(new_path),
                    "name": new_name
                })

                self._logger.info(f"重命名: {old_path} -> {new_path}")
                self.structure_changed.emit()

            except Exception as e:
                self._logger.error(f"重命名失败: {e}")
                QMessageBox.warning(self, "重命名失败", str(e))
                self.refresh()

        finally:
            # 恢复信号连接
            self.itemChanged.connect(self._on_item_renamed)

    def _show_context_menu(self, position) -> None:
        """右键菜单：打开、打开所在位置、重命名、删除、复制路径。"""
        item = self.itemAt(position)
        if not item:
            return

        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not user_data:
            return

        item_type = user_data.get("type", "")
        path_str = user_data.get("path", "")
        if not path_str or item_type not in ("file", "folder"):
            return

        path_obj = Path(path_str)
        if not path_obj.exists():
            return

        menu = QMenu(self)
        c = COLORS
        menu.setStyleSheet(f"""
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
        """)

        # 1. 打开
        action_open = QAction("打开", self)
        action_open.triggered.connect(lambda: self._open_item(path_obj, item_type))
        menu.addAction(action_open)

        # 2. 打开文件所在的位置（仅文件）
        if item_type == "file":
            action_open_parent = QAction("打开文件所在的位置", self)
            action_open_parent.triggered.connect(lambda: self._open_parent_folder(path_obj))
            menu.addAction(action_open_parent)

        menu.addSeparator()

        # 3. 重命名
        action_rename = QAction("重命名", self)
        action_rename.triggered.connect(lambda: self.editItem(item, 0))
        menu.addAction(action_rename)

        # 4. 删除
        action_delete = QAction("删除", self)
        action_delete.triggered.connect(lambda: self._delete_item(path_obj, item_type))
        menu.addAction(action_delete)

        menu.addSeparator()

        # 5. 获取绝对路径（自动复制）
        action_copy_path = QAction("获取绝对路径", self)
        action_copy_path.triggered.connect(lambda: self._copy_item_path(path_obj))
        menu.addAction(action_copy_path)

        menu.exec_(self.viewport().mapToGlobal(position))

    def _open_item(self, path_obj: Path, item_type: str) -> None:
        """打开文件或文件夹。"""
        if item_type == "file":
            self.file_double_clicked.emit(path_obj)
        else:
            self.folder_double_clicked.emit(path_obj)

    def _open_parent_folder(self, path_obj: Path) -> None:
        """在系统文件管理器中打开父文件夹并选中该文件。"""
        try:
            if is_macos():
                subprocess.Popen(["open", "-R", str(path_obj)])
            elif is_windows():
                subprocess.Popen(["explorer", "/select,", str(path_obj)])
            else:
                # Linux 退化为打开父文件夹
                open_path(path_obj.parent)
        except Exception as e:
            self._logger.error(f"打开所在位置失败: {e}")
            QMessageBox.warning(self, "打开失败", str(e))

    def _delete_item(self, path_obj: Path, item_type: str) -> None:
        """删除文件或文件夹（真实删除）。"""
        name = path_obj.name
        if item_type == "file":
            msg = f"确定要删除文件『{name}』吗？\n此操作不可恢复。"
        else:
            msg = f"确定要删除文件夹『{name}』及其所有内容吗？\n此操作不可恢复。"

        reply = QMessageBox.question(
            self,
            "确认删除",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            if item_type == "file":
                path_obj.unlink()
            else:
                shutil.rmtree(str(path_obj))
            self._logger.info(f"删除: {path_obj}")
            self.refresh()
            self.structure_changed.emit()
        except Exception as e:
            self._logger.error(f"删除失败: {e}")
            QMessageBox.warning(self, "删除失败", str(e))

    def _copy_item_path(self, path_obj: Path) -> None:
        """复制绝对路径到剪贴板。"""
        QApplication.clipboard().setText(str(path_obj))

    def refresh(self) -> None:
        """刷新当前结构"""
        if self._root_path:
            if self._lazy_mode:
                self._loaded_dirs = set()
            self.load_folder(self._root_path)

    def expand_all(self) -> None:
        """展开所有项"""
        if self._lazy_mode:
            self._ensure_lazy_children_loaded(self.invisibleRootItem())
        self.expandAll()
        self._is_expanded = True
        self._update_folder_icons(self.invisibleRootItem(), True)

    def collapse_all(self) -> None:
        """收缩所有项"""
        self.collapseAll()
        self._is_expanded = False
        self._update_folder_icons(self.invisibleRootItem(), False)

    def _update_folder_icons(self, parent_item: QTreeWidgetItem, expanded: bool) -> None:
        """更新文件夹图标"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            user_data = child.data(0, Qt.ItemDataRole.UserRole)
            if user_data and user_data.get("type") == "folder":
                child.setIcon(0, get_standard_icon("folder_open" if expanded else "folder"))
            # 递归处理子项
            self._update_folder_icons(child, expanded)

    def _ensure_lazy_children_loaded(self, parent_item: QTreeWidgetItem) -> None:
        """在用户主动展开整棵树时，补齐懒加载目录内容。"""
        if self._loaded_dirs is None:
            return

        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            user_data = child.data(0, Qt.ItemDataRole.UserRole)
            if not user_data or user_data.get("type") != "folder":
                continue

            dir_path = str(user_data.get("path", "")).strip()
            if dir_path and dir_path not in self._loaded_dirs:
                self._loaded_dirs.add(dir_path)
                while child.childCount() > 0:
                    child.removeChild(child.child(0))
                self._add_folder_items(Path(dir_path), child)
            self._ensure_lazy_children_loaded(child)

    def get_selected_path(self) -> Optional[Path]:
        """获取当前选中的路径

        Returns:
            选中的文件或文件夹路径，无选中返回 None
        """
        items = self.selectedItems()
        if not items:
            return None

        user_data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if user_data:
            return Path(user_data.get("path", ""))
        return None

    def get_root_path(self) -> Optional[Path]:
        """获取根目录路径

        Returns:
            根目录路径
        """
        return self._root_path

    def get_all_files(self) -> List[Path]:
        """获取所有文件路径

        Returns:
            所有文件的路径列表
        """
        files = []
        self._collect_files(self.invisibleRootItem(), files)
        return files

    def _collect_files(self, parent_item: QTreeWidgetItem, files: List[Path]) -> None:
        """递归收集文件"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            user_data = child.data(0, Qt.ItemDataRole.UserRole)
            if user_data:
                if user_data.get("type") == "file":
                    path = Path(user_data.get("path", ""))
                    if path.exists():
                        files.append(path)
                # 递归处理子项
                self._collect_files(child, files)
