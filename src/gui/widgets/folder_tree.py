# -*- coding: utf-8 -*-
"""文件夹树预览控件模块 - Modern UI v3"""

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLabel,
    QFrame,
    QInputDialog,
    QFileDialog,
    QMenu,
    QHBoxLayout,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction, QColor

from src.core.folder_generator import FolderGenerator
from src.gui.styles import APP_COLORS as COLORS
from src.gui.icon_utils import get_standard_icon


class FolderTreePreview(QWidget):
    """文件夹树预览控件（纯预览模式）- Modern UI v3
    
    仅用于预览文件夹结构，不支持编辑。
    所有文件夹结构操作请在模板管理中完成。
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._generator = FolderGenerator()
        self._original_structure: Dict[str, Any] = {}
        self._values: Dict[str, Any] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 树形控件 - 纯预览模式（不可编辑、不可拖拽）
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(18)
        
        # 禁用编辑和拖拽（纯预览模式）
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.setDragEnabled(False)
        self._tree.setAcceptDrops(False)
        self._tree.setDropIndicatorShown(False)
        
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                border: none;
                background-color: {c['surface_1']};
                outline: none;
                border-radius: 14px;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
            QTreeWidget::item {{
                padding: 4px 6px;
                border-radius: 8px;
                margin: 1px 4px;
                color: {c['text_secondary']};
            }}
            QTreeWidget::item:hover {{
                background-color: {c['surface_2']};
            }}
            QTreeWidget::item:selected {{
                background-color: transparent;
                color: {c['text_primary']};
                font-weight: 600;
            }}
        """)
        layout.addWidget(self._tree, 1)

        # 统计信息 - 完全扁平自然样式，无痕迹
        stats_widget = QWidget()
        stats_widget.setStyleSheet("border: none; outline: none; background: transparent;")
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(14, 12, 14, 12)
        stats_layout.setSpacing(12)

        self._stats_folders = QLabel("0")
        self._stats_folders.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {c['text_primary']};")
        
        self._stats_files = QLabel("0")
        self._stats_files.setStyleSheet(self._stats_folders.styleSheet())

        stats_layout.addStretch()
        
        folder_label = QVBoxLayout()
        folder_label.addWidget(self._stats_folders)
        folder_text = QLabel("文件夹")
        folder_text.setStyleSheet(f"font-size: 11px; color: {c['text_muted']}; text-align: center;")
        folder_label.addWidget(folder_text)
        stats_layout.addLayout(folder_label)

        stats_layout.addSpacing(20)

        file_label = QVBoxLayout()
        file_label.addWidget(self._stats_files)
        file_text = QLabel("文件")
        file_text.setStyleSheet(folder_text.styleSheet())
        file_label.addWidget(file_text)
        stats_layout.addLayout(file_label)
        
        stats_layout.addStretch()

        layout.addWidget(stats_widget)

    def _set_item_icon(self, item: QTreeWidgetItem, item_type: str, name: str, user_data: dict) -> None:
        """设置项目图标"""
        if item_type == "file":
            # 检查是否有模板
            has_template = bool(user_data.get("template_path", ""))
            if has_template:
                item.setText(0, name)
                item.setIcon(0, get_standard_icon("file_link"))
                item.setForeground(0, QColor(COLORS['accent']))
            else:
                item.setText(0, name)
                item.setIcon(0, get_standard_icon("file"))
                item.setForeground(0, QColor(COLORS['text_secondary']))
        else:
            item.setText(0, name)
            item.setIcon(0, get_standard_icon("folder"))
            item.setForeground(0, QColor(COLORS['text_primary']))

    def set_structure(
        self,
        structure: Dict[str, Any],
        values: Dict[str, Any]
    ) -> None:
        """
        设置文件夹结构

        Args:
            structure: 文件夹结构配置
            values: 变量值字典
        """
        # 保存原始数据
        self._original_structure = structure.copy() if structure else {}
        self._values = values.copy() if values else {}
        
        self._tree.clear()

        # 获取预览数据
        preview = self._generator.preview(structure, values)

        # 构建树
        parent_stack: List[QTreeWidgetItem] = []

        folder_count = 0
        file_count = 0

        for item_data in preview:
            level = item_data["level"]
            name = item_data["name"]
            item_type = item_data.get("type", "folder")

            tree_item = QTreeWidgetItem([name])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)

            # 设置图标和颜色
            self._set_item_icon(tree_item, item_type, name, item_data)
            
            if item_type == "file":
                file_count += 1
            else:
                folder_count += 1

            if level == 0:
                # 根目录
                self._tree.addTopLevelItem(tree_item)
                parent_stack = [tree_item]
            else:
                # 确保父级栈正确
                while len(parent_stack) > level:
                    parent_stack.pop()

                if parent_stack:
                    parent_stack[-1].addChild(tree_item)

                parent_stack.append(tree_item)

        # 展开所有
        self._tree.expandAll()

        # 更新统计
        self._stats_folders.setText(str(folder_count))
        self._stats_files.setText(str(file_count))

    def clear(self) -> None:
        """清空预览"""
        self._tree.clear()
        self._stats_folders.setText("0")
        self._stats_files.setText("0")


class EditableFolderTree(QWidget):
    """可编辑的文件夹树控件 - Modern UI v3"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标题
        title = QLabel("文件夹结构（右键编辑）")
        title.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: {c['text_primary']};
            padding: 0 4px;
        """)
        layout.addWidget(title)

        # 树形控件
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["名称"])
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.setIndentation(20)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {c['border']};
                border-radius: 12px;
                background-color: {c['surface_0']};
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 6px 8px;
                border-radius: 8px;
                margin: 2px 4px;
            }}
            QTreeWidget::item:hover {{
                background-color: {c['surface_2']};
            }}
            QTreeWidget::item:selected {{
                background-color: {c['accent_subtle']};
                color: {c['text_primary']};
            }}
        """)
        layout.addWidget(self._tree)

    def _connect_signals(self) -> None:
        """连接信号"""
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos) -> None:
        """显示右键菜单"""
        c = COLORS
        item = self._tree.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 7px 20px 7px 12px;
                border-radius: 8px;
            }}
            QMenu::item:selected {{
                background-color: {c['accent_subtle']};
                color: {c['accent']};
            }}
        """)

        if item is None:
            # 空白处
            add_folder_action = QAction("添加文件夹", self)
            add_folder_action.triggered.connect(lambda: self._add_folder(None))
            menu.addAction(add_folder_action)
        else:
            user_data = item.data(0, Qt.ItemDataRole.UserRole)
            item_type = user_data.get("type", "folder") if isinstance(user_data, dict) else "folder"

            if item_type == "folder":
                # 文件夹
                add_subfolder_action = QAction("添加子文件夹", self)
                add_subfolder_action.triggered.connect(lambda: self._add_folder(item))
                menu.addAction(add_subfolder_action)

                add_file_action = QAction("添加文件", self)
                add_file_action.triggered.connect(lambda: self._add_file(item))
                menu.addAction(add_file_action)

                menu.addSeparator()

                rename_action = QAction("重命名", self)
                rename_action.triggered.connect(lambda: self._rename_item(item))
                menu.addAction(rename_action)

                delete_action = QAction("删除", self)
                delete_action.triggered.connect(lambda: self._delete_item(item))
                menu.addAction(delete_action)
            else:
                # 文件
                if item.parent() is not None:
                    set_template_action = QAction("设置模板", self)
                    set_template_action.triggered.connect(lambda: self._set_template(item))
                    menu.addAction(set_template_action)

                    menu.addSeparator()

                rename_action = QAction("重命名", self)
                rename_action.triggered.connect(lambda: self._rename_item(item))
                menu.addAction(rename_action)

                delete_action = QAction("删除", self)
                delete_action.triggered.connect(lambda: self._delete_item(item))
                menu.addAction(delete_action)

        menu.exec(self._tree.mapToGlobal(pos))

    def _add_folder(self, parent_item: Optional[QTreeWidgetItem]) -> None:
        """添加文件夹"""
        item = QTreeWidgetItem(["新文件夹"])
        item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})

        if parent_item is None:
            self._tree.addTopLevelItem(item)
        else:
            parent_item.addChild(item)
            self._tree.expandItem(parent_item)

        self._tree.editItem(item)

    def _add_file(self, parent_item: QTreeWidgetItem) -> None:
        """添加文件"""
        item = QTreeWidgetItem(["新文件.docx"])
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "file",
            "template_path": ""
        })
        parent_item.addChild(item)
        self._tree.expandItem(parent_item)
        self._tree.editItem(item)

    def _rename_item(self, item: QTreeWidgetItem) -> None:
        """重命名项目"""
        self._tree.editItem(item)

    def _delete_item(self, item: QTreeWidgetItem) -> None:
        """删除项目"""
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self._tree.indexOfTopLevelItem(item)
            self._tree.takeTopLevelItem(index)

    def _set_template(self, item: QTreeWidgetItem) -> None:
        """设置文件模板"""
        from src.utils.template_path_manager import get_template_path_manager

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模板文件",
            "",
            "Word 文件 (*.docx)"
        )

        if file_path:
            user_data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(user_data, dict):
                # 转换为相对路径（如果位于项目目录内），避免项目迁移后路径失效
                manager = get_template_path_manager()
                relative_path = manager.to_relative_template_path(Path(file_path))
                user_data["template_path"] = relative_path
                item.setData(0, Qt.ItemDataRole.UserRole, user_data)
                # 更新显示
                name = item.text(0).strip()
                item.setText(0, name)
                item.setIcon(0, get_standard_icon("file_link"))

    def load_structure(self, folders: List[Dict[str, Any]]) -> None:
        """
        加载文件夹结构

        Args:
            folders: 文件夹列表
        """
        self._tree.clear()

        for folder in folders:
            item = QTreeWidgetItem([folder.get("name", "")])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})
            self._tree.addTopLevelItem(item)

            for subfolder in folder.get("subfolders", []):
                if isinstance(subfolder, str):
                    # 旧格式
                    sub_item = QTreeWidgetItem([subfolder])
                    sub_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})
                    item.addChild(sub_item)
                elif isinstance(subfolder, dict):
                    # 新格式
                    name = subfolder.get("name", "")
                    sub_item = QTreeWidgetItem([name])
                    sub_item.setData(0, Qt.ItemDataRole.UserRole, subfolder)

                    # 设置图标
                    if subfolder.get("type") == "file":
                        sub_item.setText(0, name)
                        sub_item.setIcon(0, get_standard_icon("file_link" if subfolder.get("template_path") else "file"))
                    else:
                        sub_item.setText(0, name)
                        sub_item.setIcon(0, get_standard_icon("folder"))

                    item.addChild(sub_item)

        self._tree.expandAll()

    def get_structure(self) -> List[Dict[str, Any]]:
        """
        获取文件夹结构

        Returns:
            文件夹列表
        """
        folders = []

        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            folder = {
                "name": item.text(0).strip(),
                "subfolders": []
            }

            for j in range(item.childCount()):
                child = item.child(j)
                user_data = child.data(0, Qt.ItemDataRole.UserRole)

                if isinstance(user_data, dict):
                    # 新格式
                    # 清理图标字符
                    user_data = user_data.copy()
                    user_data["name"] = user_data["name"].strip()
                    folder["subfolders"].append(user_data)
                else:
                    # 旧格式
                    folder["subfolders"].append(child.text(0))

            folders.append(folder)

        return folders

    def clear(self) -> None:
        """清空树"""
        self._tree.clear()
