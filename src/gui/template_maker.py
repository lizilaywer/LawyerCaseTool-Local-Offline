# -*- coding: utf-8 -*-
"""Word 模板制作器主窗口

提供 Word 模板的制作、编辑和变量替换功能。
"""

from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QWidget,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QStatusBar,
    QDialogButtonBox,
    QFrame,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

from src.core.word_editor import WordEditor, upload_to_template_category
from src.utils.template_path_manager import get_template_path_manager
from src.config.default_templates import DEFAULT_TEMPLATES
from src.utils.logger import get_logger
from src.utils.platform_utils import get_default_monospace_font_family, open_path
from src.gui.icon_utils import get_standard_icon
from src.gui.styles import (
    APP_COLORS as COLORS,
    CATEGORY_FULL_NAMES,
    button_style,
    combo_style,
    input_style,
    hint_banner_style,
)
from src.gui.window_metrics import APP_SURFACE_DEFAULT_SIZE, APP_SURFACE_MIN_SIZE


class AddVariableDialog(QDialog):
    """添加变量对话框 - 与模板管理器变量定义界面一致"""

    def __init__(self, parent=None, default_template_id: str = None):
        super().__init__(parent)
        self._default_template_id = default_template_id
        self._result = None
        
        self.setWindowTitle("添加变量")
        self.setMinimumWidth(450)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        from src.gui.widgets.transparent_form_layout import TransparentFormLayout
        
        layout = TransparentFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)
        self.setStyleSheet(f"QDialog {{ background: {c['surface_1']}; }}")
        
        # 键名
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("变量键名（英文，如 client_name）")
        self._key_edit.setStyleSheet(input_style())
        layout.addRow("键名*:", self._key_edit)
        
        # 标签
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("显示名称（如 委托人姓名）")
        self._label_edit.setStyleSheet(input_style())
        layout.addRow("标签*:", self._label_edit)
        
        # 类型
        self._type_combo = QComboBox()
        self._type_combo.addItem("文本", "text")
        self._type_combo.addItem("日期", "date")
        self._type_combo.addItem("下拉选择", "select")
        self._type_combo.addItem("数字", "number")
        self._type_combo.setStyleSheet(combo_style())
        layout.addRow("类型:", self._type_combo)
        
        # 必填
        self._required_check = QCheckBox("是")
        self._required_check.setChecked(False)
        layout.addRow("必填:", self._required_check)
        
        # 归属模板
        self._template_combo = QComboBox()
        self._template_combo.addItem("-- 选择模板 --", "")
        self._template_combo.setStyleSheet(combo_style())
        
        # 加载所有模板
        from src.config.config_manager import get_config_manager
        config_manager = get_config_manager()
        templates = config_manager.get_templates()
        
        # 如果没有用户模板，使用默认模板
        if not templates:
            templates = DEFAULT_TEMPLATES
        
        # 分类显示模板
        category_names = {
            "civil": "民事",
            "civil2": "民事(被告)",
            "criminal": "刑事",
            "administrative": "行政",
            "non_litigation": "非诉",
            "labor_arbitration": "劳动仲裁",
            "commercial_arbitration": "商事仲裁",
            "arbitration": "仲裁",
            "civil_simple": "民事简易",
            "civil_simple_plaintiff": "民事简易(原告)",
            "civil_simple_defendant": "民事简易(被告)",
            "criminal_simple": "刑事简易",
            "admin_simple": "行政简易",
            "admin_simple_plaintiff": "行政简易(原告)",
            "admin_simple_defendant": "行政简易(被告)",
            "labor_simple": "劳动仲裁简易",
            "labor_simple_applicant": "劳动仲裁简易(申请人)",
            "labor_simple_respondent": "劳动仲裁简易(被申请人)",
            "commercial_simple": "商事仲裁简易",
            "commercial_simple_applicant": "商事仲裁简易(申请人)",
            "commercial_simple_respondent": "商事仲裁简易(被申请人)",
        }
        
        for template in templates:
            template_id = template.get("id", "")
            template_name = template.get("name", "未命名")
            category = template.get("category", "other")
            
            # 构建显示文本
            cat_name = category_names.get(category, category)
            display_text = f"[{cat_name}] {template_name}"
            
            self._template_combo.addItem(display_text, template_id)
            
            # 如果是指定的默认模板，选中它
            if self._default_template_id and template_id == self._default_template_id:
                self._template_combo.setCurrentIndex(self._template_combo.count() - 1)
        
        layout.addRow("归属模板*:", self._template_combo)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet(button_style(primary=True, compact=True))
        ok_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(button_style(compact=True))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
    
    def _on_accept(self) -> None:
        """确认添加"""
        key = self._key_edit.text().strip()
        label = self._label_edit.text().strip()
        template_id = self._template_combo.currentData()
        
        # 验证必填项
        if not key:
            QMessageBox.warning(self, "验证失败", "请输入键名")
            return
        
        if not label:
            QMessageBox.warning(self, "验证失败", "请输入标签")
            return
        
        if not template_id:
            QMessageBox.warning(self, "验证失败", "请选择归属模板")
            return
        
        # 验证键名格式（只允许英文字母、数字、下划线）
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
            QMessageBox.warning(self, "验证失败", "键名只能包含英文字母、数字和下划线，且不能以数字开头")
            return
        
        self._result = {
            "key": key,
            "label": label,
            "type": self._type_combo.currentData(),
            "required": self._required_check.isChecked(),
            "template_id": template_id
        }
        
        self.accept()
    
    def get_result(self) -> Optional[Dict[str, Any]]:
        """获取添加的变量信息"""
        return self._result


class VariableItem(QWidget):
    """变量项控件 - Modern UI v3"""

    clicked = Signal(str)  # 变量键
    double_clicked = Signal(str)

    def __init__(self, var_key: str, var_label: str, var_type: str = "text", parent=None):
        super().__init__(parent)
        self._var_key = var_key
        self._var_label = var_label

        self._setup_ui(var_key, var_label, var_type)

    def _setup_ui(self, key: str, label: str, var_type: str) -> None:
        c = COLORS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 变量标签
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {c['text_primary']};")
        layout.addWidget(label_widget)

        # 变量键
        key_widget = QLabel(f"{{{{{key}}}}}")
        key_widget.setStyleSheet(f"""
            font-family: '{get_default_monospace_font_family()}';
            font-size: 12px;
            color: {c['accent']};
            background: {c['accent_subtle']};
            padding: 4px 8px;
            border-radius: 8px;
        """)
        layout.addWidget(key_widget)

        # 变量类型
        type_text = {
            "text": "文本",
            "date": "日期",
            "select": "选择",
        }.get(var_type, "文本")
        type_widget = QLabel(type_text)
        type_widget.setStyleSheet(f"font-size: 11px; color: {c['text_tertiary']};")
        layout.addWidget(type_widget)

        # 设置样式
        self.setStyleSheet(f"""
            VariableItem {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
            VariableItem:hover {{
                border-color: {c['border_strong']};
                background: {c['surface_1']};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._var_key)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self._var_key)
        super().mouseDoubleClickEvent(event)

    def get_variable_key(self) -> str:
        return self._var_key

    def get_variable_label(self) -> str:
        return self._var_label


class ReplaceDialog(QDialog):
    """替换对话框"""

    def __init__(self, selected_text: str = "", variables: List[Dict] = None, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._selected_text = selected_text
        self._variables = variables or []

        self._result_variable = None
        self._result_search_text = None
        self._result_replace_all = True

        self.setWindowTitle("替换为变量")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self) -> None:
        c = COLORS
        self.setStyleSheet(f"QDialog {{ background: {c['surface_1']}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # 替换方式
        mode_group = QGroupBox("替换方式")
        mode_layout = QVBoxLayout(mode_group)

        from PySide6.QtWidgets import QRadioButton
        self._selected_mode = QRadioButton("选中文字替换")
        self._input_mode = QRadioButton("手动输入替换")

        if self._selected_text:
            self._selected_mode.setChecked(True)
        else:
            self._input_mode.setChecked(True)

        self._selected_mode.toggled.connect(self._on_mode_changed)

        mode_layout.addWidget(self._selected_mode)
        mode_layout.addWidget(self._input_mode)
        layout.addWidget(mode_group)

        # 选中文字模式
        self._selected_group = QGroupBox("选中的文本")
        selected_layout = QVBoxLayout(self._selected_group)
        self._selected_text_edit = QLineEdit(self._selected_text)
        self._selected_text_edit.setReadOnly(True)
        self._selected_text_edit.setStyleSheet(f"""
            {input_style()}
            QLineEdit {{
                background: {c['surface_2']};
                color: {c['text_secondary']};
            }}
        """)
        selected_layout.addWidget(self._selected_text_edit)
        layout.addWidget(self._selected_group)

        # 手动输入模式
        self._input_group = QGroupBox("查找内容")
        input_layout = QVBoxLayout(self._input_group)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入要替换的文字...")
        self._search_input.setStyleSheet(input_style())
        input_layout.addWidget(self._search_input)

        # 提示
        tip_label = QLabel("提示：输入文字后，将查找文档中所有匹配的内容进行替换")
        tip_label.setStyleSheet(hint_banner_style("warning"))
        tip_label.setWordWrap(True)
        input_layout.addWidget(tip_label)
        layout.addWidget(self._input_group)

        # 变量选择
        var_group = QGroupBox("替换为变量")
        var_layout = QVBoxLayout(var_group)
        self._var_combo = QComboBox()
        self._var_combo.addItem("-- 选择变量 --", "")
        self._var_combo.setStyleSheet(combo_style())

        for var in self._variables:
            key = var.get("key", "")
            label = var.get("label", "")
            self._var_combo.addItem(f"{{{{{key}}}}} - {label}", key)

        self._var_combo.addItem("+ 添加自定义变量...", "__custom__")
        self._var_combo.currentIndexChanged.connect(self._on_variable_changed)
        var_layout.addWidget(self._var_combo)
        layout.addWidget(var_group)

        # 全部替换选项
        self._replace_all_check = QCheckBox("同时替换文档中所有相同内容")
        self._replace_all_check.setChecked(True)
        layout.addWidget(self._replace_all_check)

        # 格式保持提示
        format_tip = QLabel(
            "格式保持：替换操作将保持原文档的所有格式，包括：字体、字号、颜色、加粗、斜体、下划线、段落格式等。"
        )
        format_tip.setStyleSheet(hint_banner_style("success"))
        format_tip.setWordWrap(True)
        layout.addWidget(format_tip)

        # 预览
        self._preview_label = QLabel()
        self._preview_label.setStyleSheet(f"""
            background: {c['surface_0']};
            border: 1px solid {c['border']};
            color: {c['text_secondary']};
            padding: 12px;
            border-radius: 12px;
        """)
        self._update_preview()
        layout.addWidget(self._preview_label)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setStyleSheet(button_style(primary=True, compact=True))
        if cancel_btn:
            cancel_btn.setStyleSheet(button_style(compact=True))
        layout.addWidget(button_box)

        # 初始化状态
        self._on_mode_changed()

    def _on_mode_changed(self) -> None:
        """切换模式"""
        is_selected = self._selected_mode.isChecked()
        self._selected_group.setVisible(is_selected)
        self._input_group.setVisible(not is_selected)
        self._update_preview()

    def _on_variable_changed(self) -> None:
        """变量选择改变"""
        if self._var_combo.currentData() == "__custom__":
            # 立即重置下拉框选择，防止重复触发
            self._var_combo.setCurrentIndex(0)
            
            # 打开添加变量对话框
            dialog = AddVariableDialog(self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                result = dialog.get_result()
                if result:
                    var_key = result["key"]
                    var_label = result["label"]
                    
                    # 将变量保存到对应模板的配置中
                    self._save_variable_to_template(result)
                    
                    # 添加到下拉框（插入到 "+ 添加自定义变量..." 之前）
                    insert_index = self._var_combo.count() - 1
                    self._var_combo.insertItem(
                        insert_index,
                        f"{{{{{var_key}}}}} - {var_label}",
                        var_key
                    )
                    
                    # 选中新添加的变量
                    self._var_combo.setCurrentIndex(insert_index)
                    
                    # 获取模板名称用于显示
                    template_id = result.get("template_id", "")
                    template_name = self._get_template_name_by_id(template_id)
                    
                    # 显示成功提示
                    QMessageBox.information(
                        self, 
                        "添加成功", 
                        f"变量 {{{{{var_key}}}}} 已添加到模板 [{template_name}]"
                    )
                    
                    # 更新预览（使用新选中的变量）
                    self._update_preview()
                    return
        
        # 普通选择变化时更新预览
        self._update_preview()
    
    def _get_template_name_by_id(self, template_id: str) -> str:
        """根据模板ID获取模板名称"""
        from src.config.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        template = config_manager.get_template(template_id)
        
        if template:
            return template.get("name", template_id)
        
        # 如果在配置中找不到，在默认模板中查找
        for template in DEFAULT_TEMPLATES:
            if template.get("id") == template_id:
                return template.get("name", template_id)
        
        return template_id
    
    def _save_variable_to_template(self, var_data: Dict[str, Any]) -> bool:
        """将变量保存到指定模板的配置中
        
        Args:
            var_data: 变量数据，包含 key, label, type, required, template_id
            
        Returns:
            是否保存成功
        """
        from src.config.config_manager import get_config_manager
        
        try:
            config_manager = get_config_manager()
            template_id = var_data.get("template_id")
            
            # 获取模板
            template = config_manager.get_template(template_id)
            if not template:
                self._logger.warning(f"未找到模板: {template_id}")
                return False
            
            # 获取现有变量列表
            variables = template.get("variables", [])
            
            # 检查变量是否已存在
            existing_keys = {v.get("key") for v in variables}
            if var_data["key"] in existing_keys:
                self._logger.info(f"变量 {var_data['key']} 已存在，更新其定义")
                # 更新现有变量
                for i, v in enumerate(variables):
                    if v.get("key") == var_data["key"]:
                        variables[i] = {
                            "key": var_data["key"],
                            "label": var_data["label"],
                            "type": var_data.get("type", "text"),
                            "required": var_data.get("required", False)
                        }
                        break
            else:
                # 添加新变量
                variables.append({
                    "key": var_data["key"],
                    "label": var_data["label"],
                    "type": var_data.get("type", "text"),
                    "required": var_data.get("required", False)
                })
            
            # 更新模板
            template["variables"] = variables
            config_manager.update_template(template_id, template)
            
            self._logger.info(f"变量 {var_data['key']} 已保存到模板 {template_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"保存变量到模板失败: {e}")
            return False

    def _update_preview(self) -> None:
        """更新预览"""
        search_text = self._get_search_text()
        var_key = self._var_combo.currentData()

        if search_text and var_key:
            self._preview_label.setText(
                f"<b>预览：</b><br>"
                f"<span style='color: #dc3545; text-decoration: line-through;'>{search_text}</span> "
                f"→ <span style='color: #28a745; font-weight: bold;'>{{{{{var_key}}}}}</span>"
            )
        else:
            self._preview_label.setText("<b>预览：</b> 请选择变量")

    def _get_search_text(self) -> str:
        """获取搜索文本"""
        if self._selected_mode.isChecked():
            return self._selected_text
        else:
            return self._search_input.text()

    def _on_accept(self) -> None:
        """确认"""
        search_text = self._get_search_text()
        var_key = self._var_combo.currentData()

        if not search_text:
            QMessageBox.warning(self, "警告", "请输入要替换的文字")
            return

        if not var_key or var_key == "__custom__":
            QMessageBox.warning(self, "警告", "请选择变量")
            return

        self._result_search_text = search_text
        self._result_variable = var_key
        self._result_replace_all = self._replace_all_check.isChecked()

        self.accept()

    def get_result(self) -> tuple:
        """获取结果

        Returns:
            (搜索文本, 变量名, 是否全部替换)
        """
        return self._result_search_text, self._result_variable, self._result_replace_all


class TemplateMakerWidget(QWidget):
    """Word 模板制作器面板 - 可嵌入为标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._template_path_manager = get_template_path_manager()
        self._word_editor = WordEditor()

        self._current_template_path: Optional[Path] = None
        self._selected_text: str = ""
        self._variables: List[Dict] = []
        self._is_tree_expanded: bool = False  # 文件树展开状态

        # 单击/双击区分定时器
        from PySide6.QtCore import QTimer
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_click_timeout)
        self._pending_item: Optional[QTreeWidgetItem] = None
        self._pending_column: int = 0

        self._load_default_variables()
        self._setup_ui()
        self._refresh_file_tree()

    def _load_default_variables(self) -> None:
        """从配置管理器加载变量定义（与模板管理器保持同步）"""
        from src.config.config_manager import get_config_manager

        var_set = {}

        # 优先从用户配置的模板中读取变量
        config_manager = get_config_manager()
        templates = config_manager.get_templates()

        for template in templates:
            for var in template.get("variables", []):
                key = var.get("key", "")
                if key and key not in var_set:
                    var_set[key] = var

        # 如果用户配置中没有变量，则从默认模板加载
        if not var_set:
            for template in DEFAULT_TEMPLATES:
                for var in template.get("variables", []):
                    key = var.get("key", "")
                    if key and key not in var_set:
                        var_set[key] = var

        self._variables = list(var_set.values())

    def _reload_variables_from_config(self) -> None:
        """从配置管理器重新加载变量（保留从文档中提取的变量）"""
        from src.config.config_manager import get_config_manager

        # 记录从文档中提取的变量（这些是临时的，不在配置中的）
        doc_var_keys = set()
        for var in self._variables:
            # 检查是否是临时变量（没有在配置模板中定义的）
            key = var.get("key", "")
            if key:
                doc_var_keys.add(key)

        # 从配置管理器重新加载
        var_set = {}
        config_manager = get_config_manager()
        templates = config_manager.get_templates()

        for template in templates:
            for var in template.get("variables", []):
                key = var.get("key", "")
                if key and key not in var_set:
                    var_set[key] = var

        # 如果用户配置中没有变量，则从默认模板加载
        if not var_set:
            for template in DEFAULT_TEMPLATES:
                for var in template.get("variables", []):
                    key = var.get("key", "")
                    if key and key not in var_set:
                        var_set[key] = var

        # 保留从文档中提取的临时变量
        for var in self._variables:
            key = var.get("key", "")
            if key and key not in var_set:
                var_set[key] = var

        self._variables = list(var_set.values())

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        self.setStyleSheet(f"QDialog {{ background: {c['surface_1']}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # 主内容区
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {c['border']};
                width: 1px;
            }}
        """)

        # 左侧：模板库
        left_panel = self._create_template_library_panel()
        splitter.addWidget(left_panel)

        # 中间：Word 预览
        center_panel = self._create_preview_panel()
        splitter.addWidget(center_panel)

        # 右侧：变量面板
        right_panel = self._create_variable_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setSizes([220, 600, 280])

        layout.addWidget(splitter, 1)

        # 状态栏
        self._status_bar = QStatusBar()
        self._status_bar.showMessage("就绪")
        layout.addWidget(self._status_bar)

    def _create_toolbar(self) -> QWidget:
        """创建工具栏 - Modern UI v3"""
        c = COLORS
        toolbar = QWidget()
        toolbar.setProperty("templateMakerToolbar", True)
        toolbar.setStyleSheet(f"""
            QWidget[templateMakerToolbar="true"] {{
                background: {c['surface_0']};
                border-bottom: 1px solid {c['border']};
            }}
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 打开文件按钮
        open_btn = QPushButton("打开文件")
        open_btn.setFixedHeight(30)
        open_btn.setStyleSheet(button_style(compact=True))
        open_btn.clicked.connect(self._on_open_file)
        layout.addWidget(open_btn)

        layout.addWidget(self._create_separator())

        # 替换选中
        self._replace_selected_btn = QPushButton("替换选中")
        self._replace_selected_btn.setFixedHeight(30)
        self._replace_selected_btn.setStyleSheet(button_style(primary=True, compact=True))
        self._replace_selected_btn.clicked.connect(self._on_replace_selected)
        self._replace_selected_btn.setEnabled(False)
        layout.addWidget(self._replace_selected_btn)

        # 全部替换
        replace_all_btn = QPushButton("全部替换")
        replace_all_btn.setFixedHeight(30)
        replace_all_btn.setStyleSheet(button_style(compact=True))
        replace_all_btn.clicked.connect(self._on_replace_all)
        layout.addWidget(replace_all_btn)

        layout.addWidget(self._create_separator())

        # 撤销
        undo_btn = QPushButton("撤销")
        undo_btn.setFixedHeight(30)
        undo_btn.setStyleSheet(button_style(compact=True))
        undo_btn.clicked.connect(self._on_undo)
        layout.addWidget(undo_btn)

        layout.addWidget(self._create_separator())

        # 保存
        save_btn = QPushButton("保存")
        save_btn.setFixedHeight(30)
        save_btn.setStyleSheet(button_style(primary=True, compact=True))
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        # 另存为
        save_as_btn = QPushButton("另存为...")
        save_as_btn.setFixedHeight(30)
        save_as_btn.setStyleSheet(button_style(compact=True))
        save_as_btn.clicked.connect(self._on_save_as)
        layout.addWidget(save_as_btn)

        layout.addStretch()

        return toolbar

    def _create_separator(self) -> QWidget:
        """创建分隔符"""
        c = COLORS
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {c['border']};")
        return sep

    def _create_template_library_panel(self) -> QWidget:
        """创建模板文件浏览器面板 - 实时显示 templates 文件夹结构"""
        c = COLORS
        panel = QWidget()
        panel.setStyleSheet(f"""
            background: {c['surface_0']};
            border-right: 1px solid {c['border']};
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QWidget()
        header.setStyleSheet(f"background: {c['surface_0']}; border-bottom: 1px solid {c['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        
        title = QLabel("模板文件")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['text_primary']};")
        header_layout.addWidget(title)
        
        # 展开/收缩按钮
        self._expand_btn = QPushButton("▸")
        self._expand_btn.setFixedSize(28, 28)
        self._expand_btn.setCheckable(True)
        self._expand_btn.setStyleSheet(button_style(compact=True))
        self._expand_btn.setToolTip("展开/收缩所有文件夹")
        self._expand_btn.clicked.connect(self._toggle_expand_collapse)
        header_layout.addWidget(self._expand_btn)
        
        # 标记当前展开状态
        self._is_tree_expanded = False
        
        layout.addWidget(header)

        # 文件树 - 使用 QTreeWidget 显示文件系统
        self._file_tree = QTreeWidget()
        self._file_tree.setHeaderHidden(True)
        self._file_tree.setIndentation(18)
        self._file_tree.setIconSize(QSize(16, 16))
        # 禁用自动编辑，使用自定义逻辑
        self._file_tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._file_tree.setStyleSheet(f"""
            QTreeWidget {{
                border: none;
                background: {c['surface_0']};
                font-size: 12px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 6px 8px;
                border-radius: 10px;
                margin: 1px 6px;
                color: {c['text_secondary']};
            }}
            QTreeWidget::item:hover {{
                background: {c['surface_2']};
            }}
            QTreeWidget::item:selected {{
                background: {c['accent_subtle']};
                color: {c['text_primary']};
            }}
        """)
        # 连接信号
        self._file_tree.itemClicked.connect(self._on_file_item_clicked)
        self._file_tree.itemDoubleClicked.connect(self._on_file_item_double_clicked)
        self._file_tree.itemChanged.connect(self._on_file_item_renamed)
        layout.addWidget(self._file_tree, 1)

        # 底部状态栏区域（已移除打开文件按钮，功能合并到顶部工具栏）
        # footer 区域保留用于将来可能的状态信息展示
        layout.addStretch()

        return panel

    def _create_preview_panel(self) -> QWidget:
        """创建预览面板 - Modern UI v3"""
        c = COLORS
        panel = QWidget()
        panel.setStyleSheet(f"""
            background: {c['surface_0']};
            border-right: 1px solid {c['border']};
            border-left: 1px solid {c['border']};
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 导入 Word 预览控件
        try:
            from src.gui.widgets.word_preview import WordPreviewWidget
            self._word_preview = WordPreviewWidget()
            self._word_preview.text_selected.connect(self._on_text_selected)
            self._word_preview.document_loaded.connect(self._on_document_loaded)
            self._word_preview.replace_requested.connect(self._on_replace_selected)
            self._word_preview.undo_variable_requested.connect(self._on_undo_variable)
            layout.addWidget(self._word_preview)
        except Exception as e:
            self._logger.error(f"创建 Word 预览控件失败: {e}")
            # 回退到简单文本显示
            self._fallback_label = QLabel("Word 预览加载失败")
            self._fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._fallback_label)

        return panel

    def _create_variable_panel(self) -> QWidget:
        """创建变量面板 - Modern UI v3"""
        c = COLORS
        panel = QWidget()
        panel.setStyleSheet(f"background: {c['surface_0']}; border-left: 1px solid {c['border']};")
        panel.setMaximumWidth(320)
        panel.setMinimumWidth(240)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        header = QWidget()
        header.setStyleSheet(f"background: {c['surface_0']}; border-bottom: 1px solid {c['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        
        title = QLabel("变量定义")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['text_primary']};")
        header_layout.addWidget(title)
        layout.addWidget(header)

        # 搜索框
        search_widget = QWidget()
        search_widget.setStyleSheet(f"background: {c['surface_0']}; border-bottom: 1px solid {c['border']};")
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(10, 8, 10, 8)

        self._var_search = QLineEdit()
        self._var_search.setPlaceholderText("搜索变量...")
        self._var_search.setStyleSheet(input_style())
        self._var_search.textChanged.connect(self._on_search_variables)
        search_layout.addWidget(self._var_search)
        layout.addWidget(search_widget)

        # 智能推荐区域
        self._recommend_group = QGroupBox("智能推荐")
        self._recommend_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 12px;
                font-weight: 600;
                color: {c['warning']};
                background: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 16px;
                margin-top: 8px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
            }}
        """)
        recommend_layout = QVBoxLayout(self._recommend_group)
        self._recommend_label = QLabel("选中文字后显示推荐变量")
        self._recommend_label.setStyleSheet(f"font-size: 11px; color: {c['text_tertiary']}; padding: 5px;")
        self._recommend_label.setWordWrap(True)
        recommend_layout.addWidget(self._recommend_label)
        layout.addWidget(self._recommend_group)

        # 变量列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self._var_list_widget = QWidget()
        self._var_list_layout = QVBoxLayout(self._var_list_widget)
        self._var_list_layout.setSpacing(6)
        self._var_list_layout.setContentsMargins(10, 10, 10, 10)
        self._var_list_layout.addStretch()

        scroll.setWidget(self._var_list_widget)
        layout.addWidget(scroll, 1)

        # 添加变量按钮
        add_var_btn = QPushButton("+ 添加自定义变量")
        add_var_btn.setStyleSheet(button_style(compact=True))
        add_var_btn.clicked.connect(self._on_add_custom_variable)
        layout.addWidget(add_var_btn)

        # 加载变量列表
        self._refresh_variable_list()

        return panel

    def _load_template_tree(self) -> None:
        """加载模板树 - 从 ConfigManager 加载所有模板"""
        from src.config.config_manager import get_config_manager
        
        self._template_tree.clear()
        
        # 获取配置管理器中的所有模板
        config_manager = get_config_manager()
        templates = config_manager.get_templates()
        
        # 分类映射（与主界面保持一致）
        category_map = CATEGORY_FULL_NAMES

        # 按分类组织模板
        templates_by_category: Dict[str, List[Dict]] = {}
        for template in templates:
            cat = template.get("category", "other")
            if cat not in templates_by_category:
                templates_by_category[cat] = []
            templates_by_category[cat].append(template)
        
        # 按固定顺序显示分类
        category_order = [
            "civil", "civil2", "criminal", "administrative", 
            "non_litigation", "labor_arbitration", "commercial_arbitration", "arbitration"
        ]
        
        for cat_key in category_order:
            if cat_key not in templates_by_category:
                continue
                
            cat_templates = templates_by_category[cat_key]
            cat_name = category_map.get(cat_key, cat_key)
            
            # 创建分类节点
            cat_item = QTreeWidgetItem([cat_name])
            cat_item.setIcon(0, get_standard_icon("folder"))
            cat_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "category": cat_key})
            cat_item.setExpanded(True)
            self._template_tree.addTopLevelItem(cat_item)
            
            # 添加该分类下的所有模板
            for template in sorted(cat_templates, key=lambda x: x.get("name", "")):
                template_name = template.get("name", "未命名模板")
                template_id = template.get("id", "")
                
                # 获取模板文件路径
                folder_structure = template.get("folder_structure", {})
                template_files = self._extract_template_files(folder_structure)
                
                if template_files:
                    # 有模板文件的显示为可展开节点
                    template_item = QTreeWidgetItem([template_name])
                    template_item.setIcon(0, get_standard_icon("file"))
                    template_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "template",
                        "template_id": template_id,
                        "category": cat_key
                    })
                    cat_item.addChild(template_item)
                    
                    # 添加模板文件子项
                    for file_info in template_files:
                        file_item = QTreeWidgetItem([file_info['name']])
                        file_item.setIcon(0, get_standard_icon("file_link"))
                        file_item.setData(0, Qt.ItemDataRole.UserRole, {
                            "type": "file",
                            "path": file_info.get("template_path", ""),
                            "category": cat_key,
                            "template_id": template_id
                        })
                        template_item.addChild(file_item)
                else:
                    # 没有模板文件的显示为简单节点
                    template_item = QTreeWidgetItem([template_name])
                    template_item.setIcon(0, get_standard_icon("file"))
                    template_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "template",
                        "template_id": template_id,
                        "category": cat_key
                    })
                    cat_item.addChild(template_item)
        
        # 处理其他未分类的模板
        for cat_key, cat_templates in templates_by_category.items():
            if cat_key in category_order:
                continue
            
            cat_name = category_map.get(cat_key, cat_key)
            cat_item = QTreeWidgetItem([cat_name])
            cat_item.setIcon(0, get_standard_icon("folder"))
            cat_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "category": cat_key})
            cat_item.setExpanded(True)
            self._template_tree.addTopLevelItem(cat_item)
            
            for template in sorted(cat_templates, key=lambda x: x.get("name", "")):
                template_name = template.get("name", "未命名模板")
                template_id = template.get("id", "")
                template_item = QTreeWidgetItem([template_name])
                template_item.setIcon(0, get_standard_icon("file"))
                template_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "template",
                    "template_id": template_id,
                    "category": cat_key
                })
                cat_item.addChild(template_item)
    
    def _refresh_file_tree(self) -> None:
        """刷新文件树 - 从 templates 文件夹加载实际文件结构"""
        import os
        from pathlib import Path
        
        self._file_tree.clear()
        
        # 获取 templates 目录路径
        templates_dir = Path("templates")
        if not templates_dir.exists():
            templates_dir = Path(__file__).parent.parent.parent / "templates"
        
        if not templates_dir.exists():
            self._logger.warning(f"Templates directory not found: {templates_dir}")
            return
        
        self._templates_root_path = templates_dir
        
        # 递归添加文件和文件夹
        self._add_file_tree_item(templates_dir, self._file_tree)
        
        # 根据当前状态展开或收缩
        if self._is_tree_expanded:
            self._file_tree.expandAll()
        else:
            self._file_tree.collapseAll()
    
    def _toggle_expand_collapse(self) -> None:
        """切换展开/收缩所有文件夹"""
        self._is_tree_expanded = not self._is_tree_expanded
        
        if self._is_tree_expanded:
            # 展开所有
            self._file_tree.expandAll()
            self._expand_btn.setText("▾")
            self._expand_btn.setToolTip("收缩所有文件夹")
        else:
            # 收缩所有
            self._file_tree.collapseAll()
            self._expand_btn.setText("▸")
            self._expand_btn.setToolTip("展开所有文件夹")
    
    def _add_file_tree_item(self, path: Path, parent) -> None:
        """递归添加文件树项
        
        Args:
            path: 当前路径
            parent: 父级（QTreeWidget 或 QTreeWidgetItem）
        """
        try:
            # 获取目录内容并排序（文件夹在前，文件在后）
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for item in items:
                # 跳过隐藏文件和 __pycache__
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
                    # 文件夹可编辑（重命名）
                    folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    
                    if isinstance(parent, QTreeWidget):
                        parent.addTopLevelItem(folder_item)
                    else:
                        parent.addChild(folder_item)
                    
                    # 递归添加子项
                    self._add_file_tree_item(item, folder_item)
                    
                else:
                    # 文件
                    file_item = QTreeWidgetItem([item.name])
                    file_item.setIcon(0, get_standard_icon(self._get_file_icon(item.name)))
                    file_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "file",
                        "path": str(item),
                        "name": item.name
                    })
                    # 文件可编辑（重命名）
                    file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    
                    if isinstance(parent, QTreeWidget):
                        parent.addTopLevelItem(file_item)
                    else:
                        parent.addChild(file_item)
        
        except PermissionError:
            self._logger.warning(f"Permission denied: {path}")
        except Exception as e:
            self._logger.error(f"Error reading directory {path}: {e}")
    
    def _get_file_icon(self, filename: str) -> str:
        """根据文件名获取文件图标"""
        return "file"
    
    def _on_file_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """文件项单击事件 - 延迟处理以区分双击"""
        # 记录待处理的单击
        self._pending_item = item
        self._pending_column = column
        # 启动定时器（300ms），如果在此期间没有双击，则认为是单击
        self._click_timer.start(300)
    
    def _on_click_timeout(self) -> None:
        """单击定时器超时 - 进入编辑模式（重命名）"""
        if self._pending_item:
            # 进入编辑模式
            self._file_tree.editItem(self._pending_item, self._pending_column)
            self._pending_item = None
    
    def _on_file_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """文件项双击事件 - 打开文件进行编辑"""
        # 取消待处理的单击
        self._click_timer.stop()
        self._pending_item = None
        
        user_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not user_data:
            return
        
        item_type = user_data.get("type", "")
        file_path = user_data.get("path", "")
        
        if item_type == "file" and file_path:
            # 检查是否是 Word 文档
            if file_path.lower().endswith(('.docx', '.doc')):
                self._open_word_document(file_path)
            else:
                # 其他文件尝试用系统默认程序打开
                self._open_file_with_default_app(file_path)
    
    def _on_file_item_renamed(self, item: QTreeWidgetItem, column: int) -> None:
        """文件项重命名完成事件"""
        # 断开信号防止递归
        self._file_tree.itemChanged.disconnect(self._on_file_item_renamed)
        
        try:
            user_data = item.data(0, Qt.ItemDataRole.UserRole)
            if not user_data:
                return
            
            item_type = user_data.get("type", "")
            old_path = user_data.get("path", "")
            
            # 只有文件和文件夹可以重命名
            if item_type not in ("file", "folder") or not old_path:
                return
            
            new_name = item.text(0)
            
            if not new_name or new_name.strip() == "":
                # 名称为空，恢复原名
                self._refresh_file_tree()
                return
            
            new_name = new_name.strip()
            old_path_obj = Path(old_path)
            
            # 检查名称是否变化
            if new_name == old_path_obj.name:
                return  # 名称没变
            
            # 构建新路径
            new_path = old_path_obj.parent / new_name
            
            # 检查目标是否已存在
            if new_path.exists():
                QMessageBox.warning(self, "重命名失败", f"'{new_name}' 已存在")
                self._refresh_file_tree()
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
                
                self._status_bar.showMessage(f"已重命名为: {new_name}")
                self._logger.info(f"重命名: {old_path} -> {new_path}")
                
                # 更新当前打开的路径（如果正在编辑该文件）
                if self._current_template_path == old_path_obj:
                    self._current_template_path = new_path
                
            except Exception as e:
                self._logger.error(f"重命名失败: {e}")
                QMessageBox.warning(self, "重命名失败", str(e))
                self._refresh_file_tree()
        
        finally:
            # 恢复信号连接
            self._file_tree.itemChanged.connect(self._on_file_item_renamed)
    
    def _open_word_document(self, file_path: str) -> None:
        """打开 Word 文档进行编辑"""
        try:
            path = Path(file_path)
            if not path.exists():
                QMessageBox.warning(self, "文件不存在", f"文件不存在:\n{file_path}")
                return
            
            self._current_template_path = path
            
            # 加载文档到 Word 编辑器
            self._word_editor.load_document(path)
            
            # 加载文档到 Word 预览控件
            if hasattr(self, '_word_preview'):
                self._word_preview.load_file(path)
            
            self._status_bar.showMessage(f"已打开: {path.name}")
            
        except Exception as e:
            self._logger.error(f"打开 Word 文档失败: {e}")
            QMessageBox.critical(self, "打开失败", f"无法打开文件:\n{e}")
    
    def _open_file_with_default_app(self, file_path: str) -> None:
        """使用系统默认程序打开文件"""
        ok, error = open_path(file_path)
        if ok:
            self._status_bar.showMessage(f"已用默认程序打开: {Path(file_path).name}")
            return

        self._logger.error(f"打开文件失败: {error}")
        QMessageBox.warning(self, "打开失败", f"无法打开文件:\n{error}")

    def _refresh_variable_list(self, filter_text: str = "", force_rebuild: bool = False) -> None:
        """刷新变量列表

        Args:
            filter_text: 过滤文本
            force_rebuild: 是否强制重建（当变量列表发生变化时）
        """
        # 如果需要强制重建或变量数量与控件数量不匹配
        current_widget_count = self._var_list_layout.count() - 1  # 减去 stretch
        needs_rebuild = force_rebuild or current_widget_count != len(self._variables)

        if needs_rebuild:
            # 重新从配置管理器加载变量，确保与模板管理器同步
            self._reload_variables_from_config()

            # 清除现有项
            while self._var_list_layout.count() > 1:
                item = self._var_list_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 添加变量项
            for var in self._variables:
                key = var.get("key", "")
                label = var.get("label", "")
                var_type = var.get("type", "text")

                var_item = VariableItem(key, label, var_type)
                var_item.clicked.connect(self._on_variable_clicked)
                var_item.double_clicked.connect(self._on_variable_double_clicked)

                # 应用过滤
                if filter_text:
                    if filter_text.lower() not in key.lower() and filter_text.lower() not in label.lower():
                        var_item.setVisible(False)

                self._var_list_layout.insertWidget(self._var_list_layout.count() - 1, var_item)
        else:
            # 仅更新可见性（性能优化）
            filter_lower = filter_text.lower() if filter_text else ""
            for i in range(self._var_list_layout.count() - 1):
                item = self._var_list_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, VariableItem):
                        key = widget.get_variable_key().lower()
                        label = widget.get_variable_label().lower()
                        if filter_text:
                            visible = filter_lower in key or filter_lower in label
                        else:
                            visible = True
                        widget.setVisible(visible)

    def _on_template_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """模板项点击"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "file":
            path = Path(data.get("path", ""))
            if path.exists():
                self._load_template(path)

    def _load_template(self, path: Path) -> None:
        """加载模板文件"""
        self._logger.info(f"加载模板: {path}")

        # 检查是否有未保存的更改
        if self._word_editor.is_modified():
            reply = QMessageBox.question(
                self,
                "确认",
                "当前文档有未保存的更改，是否继续加载新文档？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # 加载到编辑器
        if self._word_editor.load_document(path):
            self._current_template_path = path
            self._status_bar.showMessage(f"已加载: {path.name}")

            # 加载到预览
            if hasattr(self, '_word_preview'):
                self._word_preview.load_file(path)

            # 更新变量列表（合并文档中的变量）
            self._update_variables_from_document()
        else:
            QMessageBox.warning(self, "错误", f"无法加载文件: {path}")

    def _update_variables_from_document(self) -> None:
        """从文档更新变量列表"""
        if not self._word_editor.is_loaded():
            return

        # 提取文档中的变量
        doc_vars = self._word_editor.extract_variables()

        # 合并到变量列表
        var_keys = {v.get("key") for v in self._variables}
        added_new = False
        for var_name in doc_vars:
            if var_name not in var_keys:
                self._variables.append({
                    "key": var_name,
                    "label": var_name,
                    "type": "text"
                })
                var_keys.add(var_name)
                added_new = True

        # 只有添加了新变量时才强制重建
        self._refresh_variable_list(force_rebuild=added_new)

    def _on_text_selected(self, text: str) -> None:
        """文本选中"""
        self._selected_text = text
        self._replace_selected_btn.setEnabled(bool(text))

        # 更新智能推荐
        self._update_recommendations(text)

    def _update_recommendations(self, text: str) -> None:
        """更新智能推荐"""
        if not text:
            self._recommend_label.setText("选中文字后显示推荐变量")
            return

        # 简单的匹配逻辑
        recommendations = []
        text_lower = text.lower()

        for var in self._variables:
            key = var.get("key", "")
            label = var.get("label", "")

            # 检查是否有匹配
            if any(kw in text_lower for kw in [key.lower(), label.lower()]):
                recommendations.append((key, label))

        if recommendations:
            rec_text = "<br>".join([f"'{text}' → <b>{{{{{k}}}}}</b> ({l})" for k, l in recommendations[:3]])
            self._recommend_label.setText(f"推荐：<br>{rec_text}")
        else:
            self._recommend_label.setText(f"选中文本: \"{text}\"<br>未找到匹配变量")

    def _on_document_loaded(self, success: bool) -> None:
        """文档加载完成"""
        if success:
            self._status_bar.showMessage(f"文档加载成功: {self._current_template_path.name if self._current_template_path else ''}")
        else:
            self._status_bar.showMessage("文档加载失败")

    def _on_open_file(self) -> None:
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开 Word 文档",
            "",
            "Word 文档 (*.docx *.doc);;所有文件 (*.*)"
        )
        if file_path:
            self._load_template(Path(file_path))

    def _on_upload_template(self) -> None:
        """上传模板"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要上传的 Word 文档",
            "",
            "Word 文档 (*.docx *.doc);;所有文件 (*.*)"
        )
        if not file_path:
            return

        # 选择分类
        from PySide6.QtWidgets import QInputDialog
        categories = ["civil", "criminal", "non_litigation"]
        category, ok = QInputDialog.getItem(
            self,
            "选择分类",
            "请选择模板分类:",
            categories,
            0,
            False
        )
        if not ok:
            return

        # 复制文件
        source_path = Path(file_path)
        system_dir = self._template_path_manager.get_system_template_dir()
        target_path = upload_to_template_category(source_path, category, system_dir)

        # 刷新文件树
        self._refresh_file_tree()

        # 加载新上传的模板
        self._load_template(target_path)

        QMessageBox.information(self, "成功", f"模板已上传到: {target_path}")

    def _on_undo_variable(self, variable_name: str, single: bool) -> None:
        """处理撤销变量请求

        Args:
            variable_name: 变量名（如 "client_name"）
            single: True=只撤销一个，False=撤销所有同名
        """
        if not self._word_editor.is_loaded():
            self._logger.warning("撤销变量失败：没有打开的文档")
            return

        self._logger.info(f"撤销变量请求: {variable_name}, single={single}")

        # 获取原始文字（用于显示）
        original_text = self._word_editor.get_variable_original_text(variable_name)
        if original_text:
            self._logger.info(f"找到原始文字: {original_text}")

        # 执行撤销
        count = self._word_editor.undo_variable(variable_name, single)

        if count > 0:
            msg = f"已撤销 {count} 处变量 {{{{{variable_name}}}}}"
            if original_text:
                msg += f" → {original_text}"
            self._status_bar.showMessage(msg)
            self._logger.info(f"撤销完成: {count} 处")

            # 刷新预览
            self._refresh_preview_from_editor()
        else:
            self._status_bar.showMessage(f"撤销失败：未找到变量 {{{{{variable_name}}}}} 的原始文字")
            self._logger.warning(f"撤销失败: {variable_name}")

    def _on_replace_selected(self) -> None:
        """替换选中"""
        if not self._word_editor.is_loaded():
            QMessageBox.warning(self, "警告", "请先打开文档")
            return

        # 直接从预览控件获取当前选中的文本（而不是使用缓存的 _selected_text）
        current_selected = self._word_preview.get_selected_text()
        # 替换 Unicode 段落分隔符为普通换行符
        current_selected = current_selected.replace('\u2029', '\n')

        self._logger.info(f"打开替换对话框，当前选中文本: '{current_selected}'")

        # 如果没有选中文字，提示用户
        if not current_selected:
            QMessageBox.information(
                self,
                "提示",
                '请先在预览区域选择要替换的文字，或使用"全部替换"功能手动输入文字。'
            )
            return

        dialog = ReplaceDialog(current_selected, self._variables, self)
        if dialog.exec():
            search_text, var_key, replace_all = dialog.get_result()
            self._logger.info(f"替换对话框返回: search='{search_text}', var='{var_key}', replace_all={replace_all}")

            if search_text and var_key:
                count, _ = self._word_editor.replace_text(search_text, f"{{{{{var_key}}}}}", replace_all)
                self._logger.info(f"替换完成，共替换 {count} 处")
                self._status_bar.showMessage(f"替换完成，共 {count} 处")

                # 刷新预览 - 从内存中的文档更新，而不是重新加载文件
                self._refresh_preview_from_editor()
            else:
                self._logger.warning(f"替换参数无效: search='{search_text}', var='{var_key}'")

    def _on_replace_all(self) -> None:
        """全部替换"""
        if not self._word_editor.is_loaded():
            QMessageBox.warning(self, "警告", "请先打开文档")
            return

        self._logger.info("打开全部替换对话框")
        dialog = ReplaceDialog("", self._variables, self)
        if dialog.exec():
            search_text, var_key, replace_all = dialog.get_result()
            self._logger.info(f"替换对话框返回: search='{search_text}', var='{var_key}', replace_all={replace_all}")

            if search_text and var_key:
                count, _ = self._word_editor.replace_text(search_text, f"{{{{{var_key}}}}}", True)
                self._logger.info(f"替换完成，共替换 {count} 处")
                self._status_bar.showMessage(f"替换完成，共 {count} 处")

                # 刷新预览 - 从内存中的文档更新
                self._refresh_preview_from_editor()
            else:
                self._logger.warning(f"替换参数无效: search='{search_text}', var='{var_key}'")

    def _refresh_preview_from_editor(self) -> None:
        """从编辑器刷新预览（不重新加载文件）"""
        if not self._word_editor.is_loaded():
            self._logger.warning("编辑器未加载文档，无法刷新预览")
            return

        # 从编辑器获取修改后的文本
        text = self._word_editor.extract_all_text()
        self._logger.info(f"从编辑器获取文本，长度: {len(text)}")

        # 直接更新预览控件的内容
        if hasattr(self, '_word_preview'):
            self._word_preview.set_preview_text(text)
            self._logger.info("预览已更新")
        else:
            self._logger.warning("预览控件不存在")

        # 更新变量列表
        self._update_variables_from_document()

    def _on_undo(self) -> None:
        """撤销"""
        if not self._word_editor.is_loaded():
            QMessageBox.warning(self, "警告", "请先打开文档")
            return

        if self._word_editor.can_undo():
            if self._word_editor.undo():
                self._status_bar.showMessage("已撤销")
                # 刷新预览区域
                self._refresh_preview_from_editor()
            else:
                self._status_bar.showMessage("撤销失败")
        else:
            self._status_bar.showMessage("没有可撤销的操作")

    def _on_save(self) -> None:
        """保存"""
        if not self._word_editor.is_loaded():
            QMessageBox.warning(self, "警告", "没有打开的文档")
            return

        if self._word_editor.save_document():
            self._status_bar.showMessage("保存成功")
        else:
            QMessageBox.warning(self, "错误", "保存失败")

    def _on_save_as(self) -> None:
        """另存为"""
        if not self._word_editor.is_loaded():
            QMessageBox.warning(self, "警告", "没有打开的文档")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            str(self._current_template_path.parent) if self._current_template_path else "",
            "Word 文档 (*.docx)"
        )
        if file_path:
            if self._word_editor.save_as(Path(file_path)):
                self._status_bar.showMessage(f"已保存到: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "保存失败")

    def _on_search_variables(self, text: str) -> None:
        """搜索变量"""
        self._refresh_variable_list(text)

    def _on_variable_clicked(self, var_key: str) -> None:
        """变量点击"""
        self._status_bar.showMessage(f"选中变量: {{{{{var_key}}}}}")

    def _on_variable_double_clicked(self, var_key: str) -> None:
        """变量双击 - 快速插入"""
        if self._selected_text and self._word_editor.is_loaded():
            # 直接替换选中文本
            count, _ = self._word_editor.replace_text(self._selected_text, f"{{{{{var_key}}}}}", False)
            self._status_bar.showMessage(f"已替换为 {{{{{var_key}}}}}")

            # 刷新预览
            if hasattr(self, '_word_preview') and self._current_template_path:
                self._word_preview.load_file(self._current_template_path)

    def _on_add_custom_variable(self) -> None:
        """添加自定义变量 - 使用与模板管理器一致的对话框"""
        dialog = AddVariableDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                # 将变量保存到对应模板的配置中
                success = self._save_variable_to_template(result)
                
                if success:
                    # 添加到当前变量列表（如果正在编辑对应模板）
                    var_key = result["key"]
                    existing_keys = {v.get("key") for v in self._variables}
                    
                    if var_key not in existing_keys:
                        self._variables.append({
                            "key": result["key"],
                            "label": result["label"],
                            "type": result.get("type", "text"),
                            "required": result.get("required", False)
                        })
                        self._refresh_variable_list()
                    
                    self._status_bar.showMessage(
                        f"已添加变量 {{{{{result['key']}}}}} 到模板"
                    )
                else:
                    QMessageBox.warning(self, "添加失败", "变量未能保存到模板配置中")
    
    def _save_variable_to_template(self, var_data: Dict[str, Any]) -> bool:
        """将变量保存到指定模板的配置中
        
        Args:
            var_data: 变量数据，包含 key, label, type, required, template_id
            
        Returns:
            是否保存成功
        """
        from src.config.config_manager import get_config_manager
        
        try:
            config_manager = get_config_manager()
            template_id = var_data.get("template_id")
            
            # 获取模板
            template = config_manager.get_template(template_id)
            if not template:
                self._logger.warning(f"未找到模板: {template_id}")
                return False
            
            # 获取现有变量列表
            variables = template.get("variables", [])
            
            # 检查变量是否已存在
            existing_keys = {v.get("key") for v in variables}
            if var_data["key"] in existing_keys:
                self._logger.info(f"变量 {var_data['key']} 已存在，更新其定义")
                # 更新现有变量
                for i, v in enumerate(variables):
                    if v.get("key") == var_data["key"]:
                        variables[i] = {
                            "key": var_data["key"],
                            "label": var_data["label"],
                            "type": var_data.get("type", "text"),
                            "required": var_data.get("required", False)
                        }
                        break
            else:
                # 添加新变量
                variables.append({
                    "key": var_data["key"],
                    "label": var_data["label"],
                    "type": var_data.get("type", "text"),
                    "required": var_data.get("required", False)
                })
            
            # 更新模板
            template["variables"] = variables
            config_manager.update_template(template_id, template)
            
            self._logger.info(f"变量 {var_data['key']} 已保存到模板 {template_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"保存变量到模板失败: {e}")
            return False

    def check_unsaved_changes(self) -> bool:
        """检查未保存的更改，返回 True 表示可以继续关闭。"""
        if self._word_editor.is_modified():
            reply = QMessageBox.question(
                self.window(),
                "确认",
                "文档有未保存的更改，是否保存？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        return True

    def cleanup(self) -> None:
        """清理资源"""
        if hasattr(self, '_word_preview'):
            self._word_preview.cleanup()
        self._word_editor.close()


class TemplateMakerDialog(QDialog):
    """Word 模板制作器对话框 - 兼容旧调用"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._maker = TemplateMakerWidget(self)

        self.setWindowTitle("Word 模板制作器 - 案件文件夹管理系统")
        self.setMinimumSize(*APP_SURFACE_MIN_SIZE)
        self.resize(*APP_SURFACE_DEFAULT_SIZE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._maker)

    def closeEvent(self, event) -> None:
        if not self._maker.check_unsaved_changes():
            event.ignore()
            return
        self._maker.cleanup()
        event.accept()
