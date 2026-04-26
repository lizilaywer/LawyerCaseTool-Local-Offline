# -*- coding: utf-8 -*-
"""变量输入控件模块 - Modern UI v3"""

from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QComboBox,
    QFrame,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QPalette, QColor

from src.gui.styles import APP_COLORS as COLORS, combo_style, input_style


class VariableInput(QWidget):
    """单个变量输入控件 - Modern UI v3"""

    value_changed = Signal(str, object)  # (key, value)

    def __init__(self, var_def: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_def = var_def
        self._key = var_def["key"]
        self._input_widget = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(4)

        # 标签行
        label_layout = QHBoxLayout()
        label_layout.setSpacing(4)

        label = QLabel(self._var_def.get("label", self._key))
        label.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 12px;
            font-weight: 600;
        """)
        label_layout.addWidget(label)

        # 必填标记
        if self._var_def.get("required", False):
            required_label = QLabel("*")
            required_label.setStyleSheet(f"color: {c['danger']}; font-weight: bold;")
            label_layout.addWidget(required_label)

        label_layout.addStretch()
        layout.addLayout(label_layout)

        # 根据类型创建输入控件
        var_type = self._var_def.get("type", "text")
        self._input_widget = self._create_input_widget(var_type)
        layout.addWidget(self._input_widget)

        # 描述
        description = self._var_def.get("description")
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"color: {c['text_tertiary']}; font-size: 11px;")
            layout.addWidget(desc_label)

    def _create_input_widget(self, var_type: str) -> QWidget:
        """根据类型创建输入控件"""
        c = COLORS
        
        if var_type == "text":
            widget = QLineEdit()
            widget.setPlaceholderText("请输入...")
            widget.setStyleSheet(input_style())
            
            default = self._var_def.get("default_value", "")
            if default:
                widget.setText(str(default))
            widget.textChanged.connect(self._on_text_changed)

            # 设置最大长度
            max_length = self._var_def.get("validation", {}).get("max_length")
            if max_length:
                widget.setMaxLength(max_length)

            return widget

        elif var_type == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setStyleSheet(f"""
                QDateEdit {{
                    background: {c['surface_0']};
                    color: {c['text_primary']};
                    border: 1px solid {c['border']};
                    border-radius: 12px;
                    padding: 0 12px;
                    min-height: 32px;
                    font-size: 12px;
                }}
                QDateEdit:hover {{
                    border-color: {c['border_strong']};
                }}
                QDateEdit:focus {{
                    border-color: {c['accent']};
                }}
                QDateEdit::drop-down {{
                    border: none;
                    width: 24px;
                }}
            """)

            default = self._var_def.get("default_value")
            if default:
                try:
                    if isinstance(default, str):
                        date = datetime.strptime(default, "%Y-%m-%d")
                        widget.setDate(QDate(date.year, date.month, date.day))
                except ValueError:
                    pass

            widget.dateChanged.connect(self._on_date_changed)
            return widget

        elif var_type == "select":
            widget = QComboBox()
            widget.setEditable(False)
            widget.setStyleSheet(combo_style())

            options = self._var_def.get("validation", {}).get("options", [])
            widget.addItems(options)

            default = self._var_def.get("default_value", "")
            if default and default in options:
                widget.setCurrentText(default)

            widget.currentTextChanged.connect(self._on_select_changed)
            return widget

        else:
            # 默认文本输入
            widget = QLineEdit()
            widget.setStyleSheet(input_style())
            widget.textChanged.connect(self._on_text_changed)
            return widget

    def _on_text_changed(self, text: str) -> None:
        """文本改变事件"""
        self.value_changed.emit(self._key, text)

    def _on_date_changed(self, date: QDate) -> None:
        """日期改变事件"""
        self.value_changed.emit(self._key, date.toString("yyyy-MM-dd"))

    def _on_select_changed(self, text: str) -> None:
        """选择改变事件"""
        self.value_changed.emit(self._key, text)

    def get_value(self) -> Any:
        """获取当前值"""
        var_type = self._var_def.get("type", "text")

        if var_type == "text":
            return self._input_widget.text()
        elif var_type == "date":
            return self._input_widget.date().toString("yyyy-MM-dd")
        elif var_type == "select":
            return self._input_widget.currentText()

        return self._input_widget.text() if hasattr(self._input_widget, 'text') else None

    def set_value(self, value: Any) -> None:
        """设置值"""
        var_type = self._var_def.get("type", "text")

        if var_type == "text":
            self._input_widget.setText(str(value) if value else "")
        elif var_type == "date":
            if value:
                if isinstance(value, str):
                    try:
                        date = datetime.strptime(value, "%Y-%m-%d")
                        self._input_widget.setDate(
                            QDate(date.year, date.month, date.day)
                        )
                    except ValueError:
                        pass
                elif isinstance(value, datetime):
                    self._input_widget.setDate(
                        QDate(value.year, value.month, value.day)
                    )
        elif var_type == "select":
            if value:
                self._input_widget.setCurrentText(str(value))

    def clear(self) -> None:
        """清空值"""
        var_type = self._var_def.get("type", "text")

        if var_type == "text":
            self._input_widget.clear()
        elif var_type == "date":
            self._input_widget.setDate(QDate.currentDate())
        elif var_type == "select":
            self._input_widget.setCurrentIndex(0)

    def validate(self) -> tuple:
        """
        验证当前值

        Returns:
            (是否有效, 错误消息)
        """
        from src.utils.validators import validate_variable

        value = self.get_value()
        var_type = self._var_def.get("type", "text")
        required = self._var_def.get("required", False)
        validation = self._var_def.get("validation", {})

        return validate_variable(value, var_type, required, validation)


class VariablesForm(QWidget):
    """变量表单 - Modern UI v3"""

    values_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._inputs: Dict[str, VariableInput] = {}
        self._values: Dict[str, Any] = {}
        self._bulk_update = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # 添加弹性空间
        self._layout.addStretch()

    def set_variables(self, var_defs: list) -> None:
        """
        设置变量定义

        Args:
            var_defs: 变量定义列表
        """
        # 清除现有输入
        self.clear_inputs()

        # 创建新的输入控件
        for var_def in var_defs:
            input_widget = VariableInput(var_def)
            input_widget.value_changed.connect(self._on_value_changed)
            self._layout.insertWidget(
                self._layout.count() - 1,  # 在 stretch 之前插入
                input_widget
            )
            self._inputs[var_def["key"]] = input_widget

    def clear_inputs(self) -> None:
        """安全清除所有输入控件

        断开所有信号连接，释放资源
        """
        for key, widget in list(self._inputs.items()):
            try:
                # 断开信号连接
                widget.value_changed.disconnect()
            except RuntimeError:
                pass  # 从布局移除
            self._layout.removeWidget(widget)
            widget.setParent(None)
        self._inputs.clear()
        self._values.clear()

    def _on_value_changed(self, key: str, value: Any) -> None:
        """值改变事件"""
        self._values[key] = value
        if self._bulk_update:
            return
        self.values_changed.emit(self._values.copy())

    def get_values(self) -> Dict[str, Any]:
        """获取所有值"""
        values = {}
        for key, widget in self._inputs.items():
            values[key] = widget.get_value()
        return values

    def set_values(self, values: Dict[str, Any]) -> None:
        """设置所有值"""
        self._bulk_update = True
        try:
            for key, value in values.items():
                if key in self._inputs:
                    self._inputs[key].set_value(value)
                    self._values[key] = self._inputs[key].get_value()
        finally:
            self._bulk_update = False
        self.values_changed.emit(self._values.copy())
    
    def add_variable(self, var_def: Dict[str, Any]) -> None:
        """
        动态添加一个新变量输入控件
        
        Args:
            var_def: 变量定义字典
        """
        key = var_def.get('key')
        if not key:
            return
        
        # 如果变量已存在，不重复添加
        if key in self._inputs:
            return
        
        # 创建新的输入控件
        input_widget = VariableInput(var_def)
        input_widget.value_changed.connect(self._on_value_changed)
        self._layout.insertWidget(
            self._layout.count() - 1,  # 在 stretch 之前插入
            input_widget
        )
        self._inputs[key] = input_widget
    
    def has_variable(self, key: str) -> bool:
        """
        检查变量是否已存在
        
        Args:
            key: 变量 key
            
        Returns:
            是否存在
        """
        return key in self._inputs

    def clear_all(self) -> None:
        """清空所有值"""
        self._bulk_update = True
        try:
            for widget in self._inputs.values():
                widget.clear()
            self._values.clear()
        finally:
            self._bulk_update = False
        self.values_changed.emit(self._values.copy())

    def validate(self) -> tuple:
        """
        验证所有值

        Returns:
            (是否全部有效, 错误消息列表)
        """
        errors = []
        for key, widget in self._inputs.items():
            is_valid, error_msg = widget.validate()
            if not is_valid:
                label = widget._var_def.get("label", key)
                errors.append(f"{label}: {error_msg}")

        return len(errors) == 0, errors
