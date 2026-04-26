# -*- coding: utf-8 -*-
"""模板管理界面模块 - Modern UI v3"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QWidget,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QGroupBox,
    QScrollArea,
    QMessageBox,
    QFileDialog,
    QAbstractItemView,
    QFrame,
)
from PySide6.QtCore import Qt

from src.config.config_manager import get_config_manager
from src.config.default_templates import DEFAULT_TEMPLATES
from src.core.template_diagnostics import diagnose_templates
from src.utils.logger import get_logger
from src.gui.template_file_dialog import TemplateFileDialog
from src.gui.icon_utils import get_standard_icon
from src.gui.styles import (
    APP_COLORS as COLORS,
    button_style,
    combo_style,
    input_style,
    hint_banner_style,
)



class TemplateEditor(QWidget):
    """模板编辑器 - Modern UI v3"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_manager = get_config_manager()
        self._logger = get_logger()
        self._current_template: Optional[Dict[str, Any]] = None
        self._setup_ui()

    def _create_section(self, title: str) -> tuple:
        """创建分组区域 - 简洁设计，无边框"""
        c = COLORS
        section = QWidget()
        section.setProperty("templateSectionCard", True)
        section.setStyleSheet(f"""
            QWidget[templateSectionCard="true"] {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
        """)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 标题 - 简洁文字，无下划线
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 700;
            color: {c['text_primary']};
        """)
        layout.addWidget(title_label)

        return section, layout

    def _create_input_field(self, label: str, placeholder: str = "") -> tuple:
        """创建输入字段 - 紧凑设计"""
        c = COLORS
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 标签 - 黑色加粗
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 600;
            color: {c['text_primary']};
        """)
        layout.addWidget(label_widget)

        # 输入框 - 简洁边框设计
        input_widget = QLineEdit()
        input_widget.setPlaceholderText(placeholder)
        input_widget.setStyleSheet(input_style())
        layout.addWidget(input_widget)

        return container, input_widget

    def _create_btn(self, text: str, primary: bool = False) -> QPushButton:
        """创建统一风格的按钮"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(30)
        btn.setStyleSheet(button_style(primary=primary, compact=True))
        return btn

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # 内容容器 - 浅灰背景
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(10)

        # 基本信息分组
        basic_section, basic_layout = self._create_section("基本信息")

        # 名称
        name_field, self._name_edit = self._create_input_field("模板名称", "输入模板名称")
        basic_layout.addWidget(name_field)

        # 类别
        category_container = QWidget()
        category_layout = QVBoxLayout(category_container)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(2)

        category_label = QLabel("类别")
        category_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {c['text_secondary']};")
        category_layout.addWidget(category_label)

        self._category_combo = QComboBox()
        self._category_combo.addItems(["civil", "criminal", "non_litigation"])
        self._category_combo.setStyleSheet(combo_style())
        category_layout.addWidget(self._category_combo)
        basic_layout.addWidget(category_container)

        # 描述
        desc_container = QWidget()
        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.setSpacing(2)

        desc_label = QLabel("描述")
        desc_label.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {c['text_secondary']};")
        desc_layout.addWidget(desc_label)

        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(80)
        self._desc_edit.setPlaceholderText("输入模板描述")
        self._desc_edit.setStyleSheet(input_style(multiline=True))
        desc_layout.addWidget(self._desc_edit)
        basic_layout.addWidget(desc_container)

        # 模板文件
        file_container = QWidget()
        file_layout = QHBoxLayout(file_container)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)

        file_field, self._file_edit = self._create_input_field("模板文件", "选择 Word 模板文件")
        file_layout.addWidget(file_field, 1)

        file_btn = self._create_btn("浏览...")
        file_btn.clicked.connect(self._on_browse_template)
        file_layout.addWidget(file_btn)
        file_layout.setAlignment(file_btn, Qt.AlignmentFlag.AlignBottom)

        basic_layout.addWidget(file_container)
        container_layout.addWidget(basic_section)

        # 文件夹结构分组
        structure_section, structure_layout = self._create_section("文件夹结构")

        # 根目录名称
        root_field, self._root_edit = self._create_input_field("根目录名称", "使用 {{变量名}} 插入变量")
        structure_layout.addWidget(root_field)

        # 文件夹树 - 白色背景突出
        tree_container = QFrame()
        tree_container.setProperty("templateEditorListBox", True)
        tree_container.setStyleSheet(f"""
            QFrame[templateEditorListBox="true"] {{
                border: 1px solid {c['border']};
                border-radius: 12px;
                background-color: {c['surface_0']};
            }}
        """)
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(8, 8, 8, 8)

        self._folder_tree = QTreeWidget()
        self._folder_tree.setHeaderHidden(True)
        self._folder_tree.setMinimumHeight(250)
        self._folder_tree.setStyleSheet(f"""
            QTreeWidget {{
                border: none;
                border-radius: 8px;
                background-color: {c['surface_0']};
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {c['border']};
                color: {c['text_secondary']};
            }}
            QTreeWidget::item:last {{
                border-bottom: none;
            }}
            QTreeWidget::item:hover {{
                background-color: {c['surface_2']};
            }}
            QTreeWidget::item:selected {{
                background-color: {c['accent_subtle']};
                color: {c['text_primary']};
            }}
        """)
        self._folder_tree.setEditTriggers(
            QAbstractItemView.EditTrigger.EditKeyPressed |
            QAbstractItemView.EditTrigger.DoubleClicked
        )
        self._folder_tree.itemChanged.connect(self._on_item_changed)
        tree_layout.addWidget(self._folder_tree)
        structure_layout.addWidget(tree_container)

        # 操作按钮
        folder_btn_layout = QHBoxLayout()
        folder_btn_layout.setSpacing(8)

        add_folder_btn = self._create_btn("添加文件夹")
        add_folder_btn.clicked.connect(self._on_add_folder)
        folder_btn_layout.addWidget(add_folder_btn)

        add_subfolder_btn = self._create_btn("添加子文件夹")
        add_subfolder_btn.clicked.connect(self._on_add_subfolder)
        folder_btn_layout.addWidget(add_subfolder_btn)

        add_file_btn = self._create_btn("添加文件")
        add_file_btn.clicked.connect(self._on_add_file)
        folder_btn_layout.addWidget(add_file_btn)

        set_template_btn = self._create_btn("设置模板")
        set_template_btn.clicked.connect(self._on_set_template)
        folder_btn_layout.addWidget(set_template_btn)

        rename_folder_btn = self._create_btn("重命名")
        rename_folder_btn.clicked.connect(self._on_rename_folder)
        folder_btn_layout.addWidget(rename_folder_btn)

        remove_folder_btn = self._create_btn("删除")
        remove_folder_btn.clicked.connect(self._on_remove_folder)
        folder_btn_layout.addWidget(remove_folder_btn)

        folder_btn_layout.addStretch()
        structure_layout.addLayout(folder_btn_layout)

        container_layout.addWidget(structure_section)

        # 变量定义分组
        variables_section, variables_layout = self._create_section("变量定义")

        # 变量列表 - 白色背景突出
        list_container = QFrame()
        list_container.setProperty("templateEditorListBox", True)
        list_container.setStyleSheet(f"""
            QFrame[templateEditorListBox="true"] {{
                border: 1px solid {c['border']};
                border-radius: 12px;
                background-color: {c['surface_0']};
            }}
        """)
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(8, 8, 8, 8)

        self._variables_list = QListWidget()
        self._variables_list.setMinimumHeight(200)
        # 启用拖拽排序
        self._variables_list.setDragEnabled(True)
        self._variables_list.setAcceptDrops(True)
        self._variables_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._variables_list.setStyleSheet(f"""
            QListWidget {{
                border: none;
                border-radius: 8px;
                background-color: {c['surface_0']};
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-bottom: 1px solid {c['border']};
                color: {c['text_secondary']};
            }}
            QListWidget::item:last {{
                border-bottom: none;
            }}
            QListWidget::item:hover {{
                background-color: {c['surface_1']};
            }}
            QListWidget::item:selected {{
                background-color: {c['accent']};
                color: white;
            }}
        """)
        list_layout.addWidget(self._variables_list)
        variables_layout.addWidget(list_container)

        # 变量操作按钮
        var_btn_layout = QHBoxLayout()
        var_btn_layout.setSpacing(8)

        add_var_btn = self._create_btn("添加变量")
        add_var_btn.clicked.connect(self._on_add_variable)
        var_btn_layout.addWidget(add_var_btn)

        edit_var_btn = self._create_btn("编辑变量")
        edit_var_btn.clicked.connect(self._on_edit_variable)
        var_btn_layout.addWidget(edit_var_btn)

        remove_var_btn = self._create_btn("删除变量")
        remove_var_btn.clicked.connect(self._on_remove_variable)
        var_btn_layout.addWidget(remove_var_btn)

        # 上移/下移按钮
        move_up_btn = self._create_btn("↑ 上移")
        move_up_btn.clicked.connect(self._on_move_variable_up)
        var_btn_layout.addWidget(move_up_btn)

        move_down_btn = self._create_btn("↓ 下移")
        move_down_btn.clicked.connect(self._on_move_variable_down)
        var_btn_layout.addWidget(move_down_btn)

        var_btn_layout.addStretch()
        variables_layout.addLayout(var_btn_layout)

        container_layout.addWidget(variables_section)
        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

    def load_template(self, template: Dict[str, Any]) -> None:
        """加载模板"""
        self._current_template = template.copy()

        # 基本信息
        self._name_edit.setText(template.get("name", ""))
        self._category_combo.setCurrentText(template.get("category", "civil"))
        self._desc_edit.setPlainText(template.get("description", ""))
        self._file_edit.setText(template.get("template_file", ""))

        # 文件夹结构
        structure = template.get("folder_structure", {})
        self._root_edit.setText(structure.get("root_name", ""))
        self._load_folder_structure(structure.get("folders", []))

        # 变量
        self._load_variables(template.get("variables", []))

    def get_template(self) -> Dict[str, Any]:
        """获取模板数据"""
        template = {
            "id": self._current_template.get("id") if self._current_template else "",
            "name": self._name_edit.text(),
            "description": self._desc_edit.toPlainText(),
            "category": self._category_combo.currentText(),
            "template_file": self._file_edit.text(),
            "folder_structure": {
                "root_name": self._root_edit.text(),
                "folders": self._get_folder_structure()
            },
            "variables": self._get_variables()
        }
        return template

    def _load_folder_structure(self, folders: List[Dict[str, Any]]) -> None:
        """加载文件夹结构，带图标"""
        self._folder_tree.clear()

        for folder in folders:
            folder_name = folder.get("name", "")
            item = QTreeWidgetItem([folder_name])
            item.setIcon(0, get_standard_icon("folder"))
            item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "folder",
                "name": folder_name,
                "subfolders": []
            })
            self._folder_tree.addTopLevelItem(item)

            for subfolder in folder.get("subfolders", []):
                if isinstance(subfolder, str):
                    # 简单字符串 - 判断是文件还是文件夹
                    clean_name = subfolder
                    is_file = "." in clean_name and not clean_name.endswith("/")
                    sub_item = QTreeWidgetItem([clean_name])
                    sub_item.setIcon(0, get_standard_icon("file" if is_file else "folder"))
                    sub_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "file" if is_file else "folder",
                        "name": clean_name
                    })
                    item.addChild(sub_item)
                elif isinstance(subfolder, dict):
                    name = subfolder.get("name", "")
                    item_type = subfolder.get("type", "file")
                    sub_item = QTreeWidgetItem([name])
                    if item_type == "folder":
                        sub_item.setIcon(0, get_standard_icon("folder"))
                    elif subfolder.get("use_template", False) and subfolder.get("template_path"):
                        sub_item.setIcon(0, get_standard_icon("file_link"))
                    else:
                        sub_item.setIcon(0, get_standard_icon("file"))
                    # 确保 user_data 中的 name 是干净的（无图标）
                    user_data = subfolder.copy()
                    user_data["name"] = name
                    sub_item.setData(0, Qt.ItemDataRole.UserRole, user_data)
                    item.addChild(sub_item)

        self._folder_tree.expandAll()

    def _get_folder_structure(self) -> List[Dict[str, Any]]:
        """获取文件夹结构"""
        folders = []

        for i in range(self._folder_tree.topLevelItemCount()):
            item = self._folder_tree.topLevelItem(i)
            folder_name = item.text(0)
            folder = {
                "name": folder_name,
                "subfolders": []
            }

            for j in range(item.childCount()):
                child = item.child(j)
                user_data = child.data(0, Qt.ItemDataRole.UserRole)

                if isinstance(user_data, dict):
                    # 清理 user_data 中的 name 字段的图标前缀
                    user_data_copy = user_data.copy()
                    folder["subfolders"].append(user_data_copy)
                else:
                    folder["subfolders"].append(child.text(0))

            folders.append(folder)

        return folders

    def _load_variables(self, variables: List[Dict[str, Any]]) -> None:
        """加载变量列表"""
        self._variables_list.clear()

        for var in variables:
            key = var.get("key", "")
            label = var.get("label", "")
            var_type = var.get("type", "text")

            display_text = f"{label} ({key}) - {var_type}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, var)
            self._variables_list.addItem(item)

    def _get_variables(self) -> List[Dict[str, Any]]:
        """获取变量列表"""
        variables = []

        for i in range(self._variables_list.count()):
            item = self._variables_list.item(i)
            var_data = item.data(Qt.ItemDataRole.UserRole)
            if var_data:
                variables.append(var_data)

        return variables

    def _on_browse_template(self) -> None:
        """浏览模板文件"""
        from src.utils.template_path_manager import get_template_path_manager

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模板文件",
            "",
            "Word 文件 (*.docx)"
        )

        if file_path:
            # 转换为相对路径（如果位于项目目录内），避免项目迁移后路径失效
            manager = get_template_path_manager()
            relative_path = manager.to_relative_template_path(Path(file_path))
            self._file_edit.setText(relative_path)

    def _on_item_changed(self, item: QTreeWidgetItem) -> None:
        """处理项目变化事件（重命名后）"""
        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(user_data, dict):
            user_data["name"] = item.text(0)
            item.setData(0, Qt.ItemDataRole.UserRole, user_data)

    def _on_add_folder(self) -> None:
        """添加文件夹"""
        item = QTreeWidgetItem(["新文件夹"])
        item.setIcon(0, get_standard_icon("folder"))
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "folder",
            "name": "新文件夹",
            "subfolders": []
        })
        self._folder_tree.addTopLevelItem(item)
        self._folder_tree.editItem(item)

    def _on_add_subfolder(self) -> None:
        """添加子文件夹"""
        current = self._folder_tree.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择一个父文件夹")
            return

        # 判断选中项的类型
        user_data = current.data(0, Qt.ItemDataRole.UserRole)
        is_file = isinstance(user_data, dict) and user_data.get("type") == "file"

        if is_file:
            # 如果选中的是文件，找到其父文件夹，在父文件夹下添加（平级）
            parent = current.parent()
            if parent:
                target_parent = parent
            else:
                QMessageBox.warning(self, "提示", "无法在文件同级位置添加文件夹")
                return
        else:
            # 如果选中的是文件夹，直接在该文件夹下添加
            target_parent = current

        # 创建新文件夹项
        item = QTreeWidgetItem(["新子文件夹"])
        item.setIcon(0, get_standard_icon("folder"))
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "folder",
            "name": "新子文件夹",
            "subfolders": []
        })
        target_parent.addChild(item)
        self._folder_tree.expandItem(target_parent)
        self._folder_tree.editItem(item)

    def _on_remove_folder(self) -> None:
        """删除文件夹或文件"""
        current = self._folder_tree.currentItem()
        if current:
            parent = current.parent()
            if parent:
                parent.removeChild(current)
            else:
                index = self._folder_tree.indexOfTopLevelItem(current)
                self._folder_tree.takeTopLevelItem(index)

    def _on_add_file(self) -> None:
        """添加文件"""
        current = self._folder_tree.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择一个父文件夹")
            return

        # 判断选中项的类型
        user_data = current.data(0, Qt.ItemDataRole.UserRole)
        is_file = isinstance(user_data, dict) and user_data.get("type") == "file"

        if is_file:
            # 如果选中的是文件，找到其父文件夹，在父文件夹下添加新文件（平级）
            parent = current.parent()
            if parent:
                target_parent = parent
            else:
                # 文件是顶级项，添加到顶级
                target_parent = None
        else:
            # 如果选中的是文件夹，直接在该文件夹下添加
            target_parent = current

        # 创建新文件项
        item = QTreeWidgetItem(["新文件.docx"])
        item.setIcon(0, get_standard_icon("file"))
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "file",
            "name": "新文件.docx",
            "template_path": "",
            "use_template": False
        })

        # 添加到目标父项
        if target_parent:
            target_parent.addChild(item)
            self._folder_tree.expandItem(target_parent)
        else:
            # 添加到顶级
            self._folder_tree.addTopLevelItem(item)

        self._folder_tree.editItem(item)

    def _on_set_template(self) -> None:
        """为文件设置模板路径"""
        current = self._folder_tree.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择一个文件")
            return

        user_data = current.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(user_data, dict) or user_data.get("type") != "file":
            QMessageBox.warning(self, "提示", "请选择一个文件")
            return

        dialog = TemplateFileDialog(user_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            user_data["template_path"] = result.get("template_path", "")
            user_data["use_template"] = result.get("use_template", False)
            current.setData(0, Qt.ItemDataRole.UserRole, user_data)
            self._update_item_display(current)

            QMessageBox.information(
                self,
                "成功",
                f"模板关联配置已保存\n模板: {result.get('template_path', '')}"
            )

    def _update_item_display(self, item: QTreeWidgetItem) -> None:
        """更新文件项的显示"""
        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(user_data, dict):
            return

        # 获取基础名称（去除图标前缀）
        base_name = user_data.get("name", item.text(0))
        user_data["name"] = base_name

        # 根据类型和模板状态选择图标
        item_type = user_data.get("type", "file")
        if item_type == "folder":
            item.setIcon(0, get_standard_icon("folder"))
        elif user_data.get("use_template", False) and user_data.get("template_path"):
            item.setIcon(0, get_standard_icon("file_link"))
        else:
            item.setIcon(0, get_standard_icon("file"))

        item.setText(0, base_name)
        item.setData(0, Qt.ItemDataRole.UserRole, user_data)

    def _on_rename_folder(self) -> None:
        """重命名选中的文件夹或文件"""
        current = self._folder_tree.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择要重命名的文件夹")
            return

        if not (current.flags() & Qt.ItemFlag.ItemIsEditable):
            current.setFlags(current.flags() | Qt.ItemFlag.ItemIsEditable)

        self._folder_tree.setFocus()
        self._folder_tree.editItem(current)

    def _on_add_variable(self) -> None:
        """添加变量"""
        from PySide6.QtWidgets import QDialog
        from src.gui.widgets.transparent_form_layout import TransparentFormLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("添加变量")
        dialog.setMinimumWidth(400)

        layout = TransparentFormLayout(dialog)

        key_edit = QLineEdit()
        key_edit.setPlaceholderText("变量键名（英文）")
        layout.addRow("键名:", key_edit)

        label_edit = QLineEdit()
        label_edit.setPlaceholderText("显示名称")
        layout.addRow("标签:", label_edit)

        type_combo = QComboBox()
        type_combo.addItems(["text", "date", "select", "number"])
        layout.addRow("类型:", type_combo)

        required_combo = QComboBox()
        required_combo.addItems(["否", "是"])
        layout.addRow("必填:", required_combo)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            var_data = {
                "key": key_edit.text(),
                "label": label_edit.text(),
                "type": type_combo.currentText(),
                "required": required_combo.currentText() == "是"
            }

            display_text = f"{var_data['label']} ({var_data['key']}) - {var_data['type']}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, var_data)
            self._variables_list.addItem(item)

    def _on_edit_variable(self) -> None:
        """编辑变量"""
        from PySide6.QtWidgets import QDialog
        from src.gui.widgets.transparent_form_layout import TransparentFormLayout

        current = self._variables_list.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择一个变量")
            return

        var_data = current.data(Qt.ItemDataRole.UserRole)
        if not var_data:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("编辑变量")
        dialog.setMinimumWidth(400)

        layout = TransparentFormLayout(dialog)

        key_edit = QLineEdit(var_data.get("key", ""))
        layout.addRow("键名:", key_edit)

        label_edit = QLineEdit(var_data.get("label", ""))
        layout.addRow("标签:", label_edit)

        type_combo = QComboBox()
        type_combo.addItems(["text", "date", "select", "number"])
        type_combo.setCurrentText(var_data.get("type", "text"))
        layout.addRow("类型:", type_combo)

        required_combo = QComboBox()
        required_combo.addItems(["否", "是"])
        required_combo.setCurrentText("是" if var_data.get("required", False) else "否")
        layout.addRow("必填:", required_combo)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            var_data = {
                "key": key_edit.text(),
                "label": label_edit.text(),
                "type": type_combo.currentText(),
                "required": required_combo.currentText() == "是"
            }

            display_text = f"{var_data['label']} ({var_data['key']}) - {var_data['type']}"
            current.setText(display_text)
            current.setData(Qt.ItemDataRole.UserRole, var_data)

    def _on_remove_variable(self) -> None:
        """删除变量"""
        current = self._variables_list.currentRow()
        if current >= 0:
            self._variables_list.takeItem(current)

    def _on_move_variable_up(self) -> None:
        """上移变量"""
        current_row = self._variables_list.currentRow()
        if current_row > 0:
            # 获取当前项和上一项
            current_item = self._variables_list.takeItem(current_row)
            # 在上一位置插入
            self._variables_list.insertItem(current_row - 1, current_item)
            # 保持选中状态
            self._variables_list.setCurrentItem(current_item)

    def _on_move_variable_down(self) -> None:
        """下移变量"""
        current_row = self._variables_list.currentRow()
        if current_row >= 0 and current_row < self._variables_list.count() - 1:
            # 获取当前项
            current_item = self._variables_list.takeItem(current_row)
            # 在下一位置插入
            self._variables_list.insertItem(current_row + 1, current_item)
            # 保持选中状态
            self._variables_list.setCurrentItem(current_item)


class TemplateManagerDialog(QDialog):
    """模板管理对话框 - Modern UI v3"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_manager = get_config_manager()
        self._logger = get_logger()
        self._templates: List[Dict[str, Any]] = []
        self._setup_ui()
        self._load_templates()

    def _create_btn(self, text: str, primary: bool = False) -> QPushButton:
        """创建统一风格的按钮"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(30)
        btn.setStyleSheet(button_style(primary=primary, compact=True))
        return btn

    def _setup_ui(self) -> None:
        """设置界面 - 增强视觉层次"""
        c = COLORS
        self.setWindowTitle("模板管理")
        self.setMinimumSize(1000, 700)
        # 对话框背景与表面色一致
        self.setStyleSheet(f"QDialog {{ background-color: {c['surface_1']}; }}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        intro_label = QLabel("统一维护模板的基础信息、文件夹结构、变量定义和关联 Word 文件。")
        intro_label.setWordWrap(True)
        intro_label.setStyleSheet(hint_banner_style("info"))
        main_layout.addWidget(intro_label)

        # 内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # === 左侧模板列表 - 简洁设计 ===
        left_panel = QWidget()
        left_panel.setProperty("templateManagerPanel", True)
        left_panel.setStyleSheet(f"""
            QWidget[templateManagerPanel="true"] {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(12)

        left_title = QLabel("模板列表")
        left_title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {c['text_primary']};")
        left_layout.addWidget(left_title)

        # 模板列表 - 白色背景突出
        self._template_list = QListWidget()
        self._template_list.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {c['border']};
                border-radius: 12px;
                background-color: {c['surface_0']};
                outline: none;
            }}
            QListWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {c['border']};
                color: {c['text_secondary']};
                font-size: 13px;
            }}
            QListWidget::item:last {{
                border-bottom: none;
            }}
            QListWidget::item:hover {{
                background-color: {c['surface_1']};
            }}
            QListWidget::item:selected {{
                background-color: {c['accent']};
                color: white;
                font-weight: 600;
            }}
        """)
        self._template_list.currentRowChanged.connect(self._on_template_selected)
        left_layout.addWidget(self._template_list, 1)

        # 左侧按钮组
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        add_btn = self._create_btn("新建", primary=True)
        add_btn.clicked.connect(self._on_add_template)
        btn_layout.addWidget(add_btn)

        copy_btn = self._create_btn("复制")
        copy_btn.clicked.connect(self._on_copy_template)
        btn_layout.addWidget(copy_btn)

        delete_btn = self._create_btn("删除")
        delete_btn.clicked.connect(self._on_delete_template)
        btn_layout.addWidget(delete_btn)

        reset_btn = self._create_btn("重置默认")
        reset_btn.clicked.connect(self._on_reset_templates)
        btn_layout.addWidget(reset_btn)

        diagnose_btn = self._create_btn("诊断")
        diagnose_btn.clicked.connect(self._on_template_diagnostics)
        btn_layout.addWidget(diagnose_btn)

        left_layout.addLayout(btn_layout)
        content_layout.addWidget(left_panel, 1)

        # === 右侧编辑器 - 简洁设计，无边框 ===
        right_panel = QWidget()
        right_panel.setProperty("templateManagerPanel", True)
        right_panel.setStyleSheet(f"""
            QWidget[templateManagerPanel="true"] {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(12)

        right_title = QLabel("模板编辑")
        right_title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {c['text_primary']};")
        right_layout.addWidget(right_title)

        self._editor = TemplateEditor()
        right_layout.addWidget(self._editor, 1)

        content_layout.addWidget(right_panel, 2)
        main_layout.addLayout(content_layout, 1)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        save_btn = self._create_btn("保存", primary=True)
        save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(save_btn)

        close_btn = self._create_btn("关闭")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        main_layout.addLayout(bottom_layout)

    def _load_templates(self) -> None:
        """加载模板列表"""
        self._templates = self._config_manager.get_templates()
        self._template_list.clear()

        for template in self._templates:
            item = QListWidgetItem(template.get("name", ""))
            item.setData(Qt.ItemDataRole.UserRole, template.get("id"))
            self._template_list.addItem(item)

        if self._templates:
            self._template_list.setCurrentRow(0)

    def _on_template_selected(self, row: int) -> None:
        """模板选中"""
        if 0 <= row < len(self._templates):
            self._editor.load_template(self._templates[row])

    def select_template(self, template_id: str) -> None:
        """选择指定模板"""
        for i, template in enumerate(self._templates):
            if template.get("id") == template_id:
                self._template_list.setCurrentRow(i)
                break

    def _on_add_template(self) -> None:
        """添加新模板"""
        # 生成唯一ID
        base_id = f"template_{len(self._templates) + 1}"
        new_id = base_id
        counter = 1
        existing_ids = {t["id"] for t in self._templates}
        while new_id in existing_ids:
            new_id = f"{base_id}_{counter}"
            counter += 1

        new_template = {
            "id": new_id,
            "name": "新模板",
            "category": "civil",
            "description": "",
            "template_file": "",
            "folder_structure": {
                "root_name": "{{case_number}}_{{client_name}}",
                "folders": []
            },
            "variables": []
        }

        # 添加到 config_manager 并保存
        if self._config_manager.add_template(new_template):
            self._templates.append(new_template)

            item = QListWidgetItem(new_template["name"])
            item.setData(Qt.ItemDataRole.UserRole, new_template["id"])
            self._template_list.addItem(item)
            self._template_list.setCurrentRow(self._template_list.count() - 1)

            self._logger.info(f"新建模板: {new_id}")
        else:
            QMessageBox.warning(self, "提示", "创建模板失败")

    def _on_copy_template(self) -> None:
        """复制当前模板"""
        current_row = self._template_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return

        source_template = self._templates[current_row]
        new_template = source_template.copy()

        # 生成唯一ID
        base_id = f"{source_template['id']}_copy"
        new_id = base_id
        counter = 1
        existing_ids = {t["id"] for t in self._templates}
        while new_id in existing_ids:
            new_id = f"{base_id}_{counter}"
            counter += 1

        new_template["id"] = new_id
        new_template["name"] = f"{source_template['name']} (复制)"

        # 添加到 config_manager 并保存
        if self._config_manager.add_template(new_template):
            self._templates.append(new_template)

            item = QListWidgetItem(new_template["name"])
            item.setData(Qt.ItemDataRole.UserRole, new_template["id"])
            self._template_list.addItem(item)
            self._template_list.setCurrentRow(self._template_list.count() - 1)

            self._logger.info(f"复制模板: {new_id}")
        else:
            QMessageBox.warning(self, "提示", "复制模板失败")

    def _on_delete_template(self) -> None:
        """删除当前模板"""
        current_row = self._template_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return

        # 获取要删除的模板ID
        template_id = self._templates[current_row].get("id")
        if not template_id:
            QMessageBox.warning(self, "提示", "无法获取模板ID")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除这个模板吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 使用 config_manager 删除并保存
            if self._config_manager.delete_template(template_id):
                del self._templates[current_row]
                self._template_list.takeItem(current_row)

                if self._templates:
                    self._template_list.setCurrentRow(0)

                self._logger.info(f"模板已删除: {template_id}")
            else:
                QMessageBox.warning(self, "提示", "删除模板失败")

    def _on_reset_templates(self) -> None:
        """重置为默认模板"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置为默认模板吗？这将丢失所有自定义模板。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 正确的顺序：先保存到配置，再重新加载
            self._config_manager.reset_templates()
            self._templates = self._config_manager.get_templates()
            self._load_templates()

    def _on_template_diagnostics(self) -> None:
        """显示模板路径与变量诊断结果。"""
        summary = diagnose_templates(self._config_manager.get_templates())
        dialog = QDialog(self)
        dialog.setWindowTitle("模板诊断")
        dialog.setMinimumSize(720, 520)
        c = COLORS
        dialog.setStyleSheet(f"QDialog {{ background-color: {c['surface_1']}; }}")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        overview = QLabel(
            "模板数：{template_count}    失效路径：{invalid_paths}    "
            "重复 ID：{duplicate_ids}    缺失变量：{missing_variables}    "
            "Word 占位符：{placeholder_count}".format(**summary.__dict__)
        )
        overview.setStyleSheet(hint_banner_style("info" if not summary.issues else "warning"))
        layout.addWidget(overview)

        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setStyleSheet(input_style())
        if summary.issues:
            lines = []
            for index, issue in enumerate(summary.issues, start=1):
                location = f"路径：{issue.path}" if issue.path else "路径：-"
                lines.append(
                    f"{index}. [{issue.level}] {issue.template_name or issue.template_id}\n"
                    f"   ID：{issue.template_id or '-'}\n"
                    f"   {location}\n"
                    f"   问题：{issue.message}"
                )
            detail.setPlainText("\n\n".join(lines))
        else:
            detail.setPlainText("未发现失效路径、重复 ID 或变量缺失。")
        layout.addWidget(detail, 1)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = self._create_btn("关闭", primary=True)
        close_btn.clicked.connect(dialog.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        dialog.exec()

    def _on_save(self) -> None:
        """保存模板"""
        current_row = self._template_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return

        template = self._editor.get_template()
        self._templates[current_row] = template

        self._template_list.item(current_row).setText(template["name"])
        self._config_manager.update_template(template["id"], template)

        QMessageBox.information(self, "成功", "模板已保存")
