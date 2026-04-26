# -*- coding: utf-8 -*-
"""文件模板关联对话框模块"""

from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QScrollArea,
    QWidget,
    QFrame
)
from PySide6.QtGui import QFont

from src.utils.template_path_manager import get_template_path_manager
from src.utils.logger import get_logger
from src.gui.styles import (
    APP_COLORS as COLORS,
    button_style,
    input_style,
    hint_banner_style,
    card_style,
)
from src.gui.icon_utils import get_standard_icon


class TemplateFileDialog(QDialog):
    """文件模板关联对话框"""

    def __init__(self, file_item: Dict[str, Any], parent: Optional[QWidget] = None):
        """
        初始化对话框

        Args:
            file_item: 文件项配置字典
            parent: 父窗口
        """
        super().__init__(parent)
        self._file_item = file_item
        self._template_manager = get_template_path_manager()
        self._logger = get_logger()
        self._setup_ui()
        self._load_current_config()

    def _setup_ui(self):
        """设置界面"""
        c = COLORS
        self.setWindowTitle("关联 Word 模板")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setStyleSheet(f"QDialog {{ background: {c['surface_1']}; }}")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # 标题
        title_label = QLabel("Word 模板关联配置")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {c['text_primary']};")
        layout.addWidget(title_label)

        # 说明
        desc_label = QLabel("为选中的文件关联 Word 模板，生成案卷时将自动填充变量值")
        desc_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
        layout.addWidget(desc_label)

        # 使用说明区域
        usage_info = QLabel(
            "<b>使用说明</b><br>"
            "• 在模板中使用 <code>{{变量名}}</code> 格式定义变量（支持中文）<br>"
            "• 系统会自动从模板中提取变量，生成时需填写变量值<br>"
            "• 支持 .docx 格式（推荐）和 .doc 格式模板<br>"
            "• 可从系统模板库选择，或点击浏览选择本地文件"
        )
        usage_info.setWordWrap(True)
        usage_info.setStyleSheet(hint_banner_style("warning"))
        layout.addWidget(usage_info)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet(f"color: {c['border']};")
        layout.addWidget(line)

        # 当前文件名
        file_group = self._create_form_group("当前选中文件")
        self.file_name_edit = QLineEdit()
        self.file_name_edit.setReadOnly(True)
        self.file_name_edit.setStyleSheet(f"""
            {input_style()}
            QLineEdit {{
                background: {c['surface_2']};
                color: {c['text_secondary']};
            }}
        """)
        file_group_layout = file_group.layout()
        file_group_layout.addWidget(self.file_name_edit)
        layout.addWidget(file_group)

        # 是否使用模板
        self.use_template_cb = QCheckBox("启用 Word 模板生成文档")
        self.use_template_cb.setStyleSheet(f"font-size: 13px; color: {c['text_primary']};")
        layout.addWidget(self.use_template_cb)

        hint_label = QLabel("💡 取消勾选则生成空白的 .docx 文件")
        hint_label.setStyleSheet(f"color: {c['text_tertiary']}; font-size: 12px; margin-left: 24px;")
        layout.addWidget(hint_label)

        # 模板路径输入
        path_group = self._create_form_group("Word 模板路径 *")
        path_layout = QHBoxLayout()

        self.template_path_edit = QLineEdit()
        self.template_path_edit.setPlaceholderText("选择或输入模板文件路径...")
        self.template_path_edit.setStyleSheet(input_style())
        path_layout.addWidget(self.template_path_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(100)
        browse_btn.setStyleSheet(button_style(compact=True))
        browse_btn.clicked.connect(self._browse_template)
        path_layout.addWidget(browse_btn)

        path_group_layout = path_group.layout()
        path_group_layout.addLayout(path_layout)

        # 路径验证提示
        self.path_hint_label = QLabel()
        self.path_hint_label.setStyleSheet(f"font-size: 12px; color: {c['text_tertiary']};")
        path_group_layout.addWidget(self.path_hint_label)

        layout.addWidget(path_group)

        # 模板库
        library_group = self._create_form_group("从系统模板库选择")
        library_scroll = QScrollArea()
        library_scroll.setWidgetResizable(True)
        library_scroll.setMaximumHeight(200)
        library_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        library_widget = QWidget()
        library_widget.setStyleSheet("background: transparent;")
        self.library_layout = QVBoxLayout(library_widget)
        self.library_layout.setSpacing(8)
        self.library_layout.setContentsMargins(0, 0, 0, 0)
        library_scroll.setWidget(library_widget)

        library_group_layout = library_group.layout()
        library_group_layout.addWidget(library_scroll)

        layout.addWidget(library_group)

        # 模板变量预览
        self.preview_group = self._create_form_group("模板中包含的变量")
        self.preview_group.setVisible(False)

        self.variable_label = QLabel()
        self.variable_label.setWordWrap(True)
        self.variable_label.setStyleSheet(f"font-size: 12px; color: {c['text_secondary']};")

        preview_layout = self.preview_group.layout()
        preview_layout.addWidget(self.variable_label)

        layout.addWidget(self.preview_group)

        # 弹性空间
        layout.addStretch()

        # 按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet(button_style(compact=True))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存配置")
        save_btn.setFixedWidth(120)
        save_btn.setStyleSheet(button_style(primary=True, compact=True))
        save_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 连接信号
        self.template_path_edit.textChanged.connect(self._on_path_changed)
        self.use_template_cb.toggled.connect(self._on_use_template_toggled)

    def _create_form_group(self, title: str) -> QFrame:
        """
        创建表单组

        Args:
            title: 组标题

        Returns:
            表单组框架
        """
        c = COLORS
        frame = QFrame()
        frame.setStyleSheet(card_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {c['text_primary']};")
        layout.addWidget(label)

        return frame

    def _load_current_config(self):
        """加载当前配置"""
        # 显示文件名
        file_name = self._file_item.get("name", "")
        self.file_name_edit.setText(file_name)

        # 加载模板路径
        template_path = self._file_item.get("template_path", "")
        self.template_path_edit.setText(template_path)

        # 加载启用状态
        use_template = self._file_item.get("use_template", False)
        self.use_template_cb.setChecked(use_template)

        # 加载模板库
        self._load_template_library()

        # 更新界面状态
        self._on_path_changed(template_path)
        self._on_use_template_toggled(use_template)

    def _load_template_library(self):
        """加载模板库"""
        # 清空现有项
        while self.library_layout.count():
            item = self.library_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 获取可用模板
        templates = self._template_manager.get_available_templates()

        if not templates:
            no_template_label = QLabel("📭 暂无可用模板")
            no_template_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; padding: 16px;")
            self.library_layout.addWidget(no_template_label)
            return

        # 添加模板项
        for template in templates:
            template_item = self._create_template_item(template)
            self.library_layout.addWidget(template_item)

        self.library_layout.addStretch()

    def _create_template_item(self, template: Dict[str, Any]) -> QWidget:
        """
        创建模板项

        Args:
            template: 模板信息字典

        Returns:
            模板项控件
        """
        from PySide6.QtCore import Signal

        item = QFrame()
        item.setProperty("templateLibraryItem", True)
        c = COLORS
        item.setStyleSheet(f"""
            QFrame[templateLibraryItem="true"] {{
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 8px;
                background: {c['surface_0']};
            }}
            QFrame[templateLibraryItem="true"]:hover {{
                background: {c['surface_1']};
                border-color: {c['accent']};
            }}
        """)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(12, 8, 12, 8)

        # 图标
        icon_label = QLabel()
        icon_label.setPixmap(get_standard_icon("file").pixmap(20, 20))
        layout.addWidget(icon_label)

        # 信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        name_label = QLabel(template["name"])
        name_label.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {c['text_primary']};")
        info_layout.addWidget(name_label)

        path_label = QLabel(template["path"])
        path_label.setStyleSheet(f"color: {c['text_tertiary']}; font-size: 11px;")
        info_layout.addWidget(path_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 选择按钮
        select_btn = QPushButton("选择")
        select_btn.setFixedWidth(60)
        select_btn.setStyleSheet(button_style(compact=True))
        select_btn.clicked.connect(lambda: self._select_template(template["path"]))
        layout.addWidget(select_btn)

        return item

    def _select_template(self, template_path: str):
        """
        选择模板

        Args:
            template_path: 模板路径
        """
        self.template_path_edit.setText(template_path)
        self.use_template_cb.setChecked(True)

    def _browse_template(self):
        """浏览模板文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Word 模板",
            "",
            "Word 文档 (*.docx)"
        )

        if file_path:
            # 转换为相对路径（如果位于项目目录内），避免项目迁移后路径失效
            relative_path = self._template_manager.to_relative_template_path(Path(file_path))
            self.template_path_edit.setText(relative_path)
            self.use_template_cb.setChecked(True)

    def _on_path_changed(self, path: str):
        """
        路径变化时的处理

        Args:
            path: 模板路径
        """
        if not path:
            self.path_hint_label.setText("未关联模板，将生成空白文档")
            self.path_hint_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
            self.preview_group.setVisible(False)
            return

        # 验证路径
        is_valid, error_msg = self._template_manager.validate_template_path(path)

        if is_valid:
            self.path_hint_label.setText("✓ 模板文件有效")
            self.path_hint_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")

            # 提取变量（简化版本，实际可以调用 TemplateEngine）
            self._show_template_variables(path)
        else:
            self.path_hint_label.setText(error_msg)
            self.path_hint_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
            self.preview_group.setVisible(False)

    def _show_template_variables(self, template_path: str):
        """
        显示模板变量

        Args:
            template_path: 模板路径
        """
        # 解析模板路径
        resolved_path = self._template_manager.resolve_template_path(template_path)

        if not resolved_path or not resolved_path.exists():
            self.variable_label.setText("无法找到模板文件")
            self.variable_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
            self.preview_group.setVisible(True)
            return

        # 使用 TemplateEngine 提取变量
        from src.core.template_engine import TemplateEngine
        engine = TemplateEngine()
        variables = engine.extract_variables(resolved_path)

        if variables:
            # 显示实际提取的变量
            variable_html = " ".join([
                f'<span style="background: {COLORS["accent_subtle"]}; color: {COLORS["accent"]}; padding: 4px 10px; border-radius: 999px; margin-right: 6px; margin-bottom: 6px; display: inline-block;">{{{{{v}}}}}</span>'
                for v in variables
            ])
            self.variable_label.setText(variable_html)
            self.variable_label.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
            self.preview_group.setVisible(True)
        else:
            self.variable_label.setText("该模板中未找到变量（可能是 .doc 格式或模板不包含变量）")
            self.variable_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
            self.preview_group.setVisible(True)

    def _on_use_template_toggled(self, checked: bool):
        """
        启用复选框切换

        Args:
            checked: 是否选中
        """
        if checked:
            self.template_path_edit.setEnabled(True)
        else:
            self.template_path_edit.setEnabled(False)

    def _save_and_accept(self):
        """保存配置并接受对话框"""
        # 验证
        if self.use_template_cb.isChecked():
            template_path = self.template_path_edit.text()
            if not template_path:
                self.path_hint_label.setText("请选择模板文件")
                self.path_hint_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
                return

            is_valid, error_msg = self._template_manager.validate_template_path(template_path)
            if not is_valid:
                self.path_hint_label.setText(error_msg)
                self.path_hint_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
                return

        self.accept()

    def get_result(self) -> Dict[str, Any]:
        """
        获取配置结果

        Returns:
            配置结果字典
        """
        return {
            "template_path": self.template_path_edit.text(),
            "use_template": self.use_template_cb.isChecked()
        }
