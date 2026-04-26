# -*- coding: utf-8 -*-
"""OCR 结果展示控件模块"""

from typing import Dict, Optional, List, Callable, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, QPushButton,
    QGroupBox, QScrollArea, QFrame, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QClipboard
from PySide6.QtWidgets import QApplication

from src.core.ocr.document_parser import RecognitionResult, FieldConfidence, DocumentType, DocumentParser
from src.core.ocr.field_matcher import FieldMatcher
from src.gui.styles import (
    APP_COLORS as COLORS,
    button_style,
    input_style,
    hint_banner_style,
)


class ConfidenceIndicator(QLabel):
    """置信度指示器"""
    
    def __init__(self, confidence: float, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.set_confidence(confidence)
    
    def set_confidence(self, confidence: float):
        """设置置信度"""
        self._confidence = confidence
        
        # 根据置信度设置颜色和样式
        if confidence >= 0.9:
            color = "#4caf50"  # 绿色
            level = "高"
        elif confidence >= 0.8:
            color = "#ff9800"  # 橙色
            level = "中"
        else:
            color = "#f44336"  # 红色
            level = "低"
        
        percentage = int(confidence * 100)
        
        self.setText(f"{percentage}%")
        self.setToolTip(f"置信度: {percentage}% ({level})")
        self.setStyleSheet(f"""
            color: {color};
            font-weight: 700;
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 999px;
            background-color: {color}20;
        """)


class FieldEditWidget(QWidget):
    """字段编辑控件 - 支持单行和多行文本"""
    
    value_changed = Signal(str, str)  # (field_name, new_value)
    
    # 长文本字段列表（使用 QTextEdit 显示）
    LONG_TEXT_FIELDS = [
        '原告诉请', '被告答辩', '法院查明', '法院认为', '判决结果',
        '诉讼请求', '答辩意见', '经审理查明', '本院认为', '判决如下',
        '事实与理由', '争议焦点', '法律依据',
    ]
    
    def __init__(self, field_name: str, field_conf: FieldConfidence,
                 label_text: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._field_name = field_name
        self._field_conf = field_conf
        self._label_text = label_text
        self._is_long_text = self._check_is_long_text(field_name)
        
        self._setup_ui()
    
    def _check_is_long_text(self, field_name: str) -> bool:
        """检查是否为长文本字段"""
        for long_field in self.LONG_TEXT_FIELDS:
            if long_field in field_name:
                return True
        # 内容超过50字符也认为是长文本
        if len(self._field_conf.value) > 50:
            return True
        return False
    
    def _setup_ui(self):
        """设置界面"""
        # 长文本使用垂直布局，短文本使用水平布局
        if self._is_long_text:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 8, 0, 8)
            layout.setSpacing(6)
        else:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 4, 0, 4)
            layout.setSpacing(8)
        
        # 标签
        label = QLabel(self._label_text)
        label.setStyleSheet(f"font-weight: 700; color: {COLORS['text_primary']};")
        
        if self._is_long_text:
            label.setMinimumWidth(100)
            layout.addWidget(label)
        else:
            label.setMinimumWidth(80)
            layout.addWidget(label)
        
        # 输入框容器（用于放置输入框和置信度）
        input_container = QWidget()
        if self._is_long_text:
            input_layout = QHBoxLayout(input_container)
            input_layout.setContentsMargins(0, 0, 0, 0)
        else:
            input_layout = QHBoxLayout(input_container)
            input_layout.setContentsMargins(0, 0, 0, 0)
        
        # 根据类型选择输入控件
        if self._is_long_text:
            self._input = QTextEdit()
            self._input.setPlainText(self._field_conf.value)
            self._input.setMinimumHeight(80)
            self._input.setMaximumHeight(200)
            self._input.setStyleSheet(input_style(multiline=True))
            
            # 低置信度样式
            if self._field_conf.is_low_confidence:
                self._input.setStyleSheet(f"""
                    {input_style(multiline=True)}
                    QTextEdit {{
                        border: 1px solid {COLORS['danger']};
                        background-color: #fff1f2;
                    }}
                """)
                self._input.setToolTip("低置信度，请核对")
            
            self._input.textChanged.connect(self._on_text_changed)
        else:
            self._input = QLineEdit()
            self._input.setText(self._field_conf.value)
            self._input.setStyleSheet(input_style())
            
            # 低置信度样式
            if self._field_conf.is_low_confidence:
                self._input.setStyleSheet(f"""
                    {input_style()}
                    QLineEdit {{
                        border: 1px solid {COLORS['danger']};
                        background-color: #fff1f2;
                    }}
                """)
                self._input.setToolTip("低置信度，请核对")
            
            self._input.textChanged.connect(self._on_value_changed)
        
        input_layout.addWidget(self._input, 1)
        
        # 置信度指示器
        self._confidence_indicator = ConfidenceIndicator(self._field_conf.confidence)
        input_layout.addWidget(self._confidence_indicator)
        
        layout.addWidget(input_container)
    
    def _on_value_changed(self, text: str):
        """单行文本值改变事件"""
        self.value_changed.emit(self._field_name, text)
    
    def _on_text_changed(self):
        """多行文本值改变事件"""
        text = self._input.toPlainText()
        self.value_changed.emit(self._field_name, text)
    
    def get_value(self) -> str:
        """获取当前值"""
        if isinstance(self._input, QTextEdit):
            return self._input.toPlainText()
        else:
            return self._input.text()
    
    def set_value(self, value: str):
        """设置值"""
        if isinstance(self._input, QTextEdit):
            self._input.setPlainText(value)
        else:
            self._input.setText(value)
    
    def is_long_text(self) -> bool:
        """是否为长文本字段"""
        return self._is_long_text


class OCRResultWidget(QWidget):
    """OCR 结果展示控件"""
    
    # 信号
    field_edited = Signal(str, str)           # 字段编辑信号 (field_name, new_value)
    apply_to_template = Signal(dict)          # 应用到模板信号 {var_key: value}
    export_requested = Signal(str)            # 导出请求信号 (export_type: 'excel'|'word'|'json')
    re_recognize_requested = Signal()         # 重新识别请求信号
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._current_result: Optional[RecognitionResult] = None
        self._field_widgets: Dict[str, FieldEditWidget] = {}
        self._field_matcher = FieldMatcher()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置界面"""
        c = COLORS
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 文档类型标题
        self._type_label = QLabel("未识别")
        self._type_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {c['accent']};
            padding-bottom: 8px;
            border-bottom: 1px solid {c['border']};
        """)
        layout.addWidget(self._type_label)
        
        # 整体置信度
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("整体识别置信度:"))
        self._overall_confidence = ConfidenceIndicator(0.0)
        confidence_layout.addWidget(self._overall_confidence)
        confidence_layout.addStretch()
        layout.addLayout(confidence_layout)
        
        # 字段编辑区域（带滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._fields_container = QWidget()
        self._fields_layout = QVBoxLayout(self._fields_container)
        self._fields_layout.setSpacing(8)
        self._fields_layout.setContentsMargins(0, 0, 0, 0)
        self._fields_layout.addStretch()
        
        scroll.setWidget(self._fields_container)
        layout.addWidget(scroll, 1)
        
        # 汇总信息区域
        self._setup_summary_section(layout)
        
        # 低置信度警告
        self._warning_label = QLabel("存在低置信度字段，请仔细核对")
        self._warning_label.setStyleSheet(hint_banner_style("warning"))
        self._warning_label.setVisible(False)
        layout.addWidget(self._warning_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        btn_layout.addStretch()
        
        # 导出按钮
        export_menu_btn = QPushButton("导出 ▼")
        export_menu_btn.setStyleSheet(button_style(compact=True))
        export_menu_btn.setMenu(self._create_export_menu())
        btn_layout.addWidget(export_menu_btn)
        
        self._apply_btn = QPushButton("应用到案卷变量")
        self._apply_btn.setStyleSheet(button_style(success=True))
        self._apply_btn.clicked.connect(self._on_apply_to_template)
        btn_layout.addWidget(self._apply_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_export_menu(self) -> QMenu:
        """创建导出菜单"""
        menu = QMenu(self)
        
        json_action = menu.addAction("导出为 JSON")
        json_action.triggered.connect(lambda: self.export_requested.emit('json'))
        
        excel_action = menu.addAction("导出为 Excel")
        excel_action.triggered.connect(lambda: self.export_requested.emit('excel'))
        
        word_action = menu.addAction("导出为 Word")
        word_action.triggered.connect(lambda: self.export_requested.emit('word'))
        
        return menu
    
    def set_result(self, result: RecognitionResult, 
                   template_vars: Optional[List[Dict[str, Any]]] = None):
        """
        设置识别结果
        
        Args:
            result: 识别结果
            template_vars: 模板变量定义列表（用于显示映射关系）
        """
        self._current_result = result
        
        # 更新文档类型标题
        type_name = DocumentParser.DOCUMENT_TYPE_NAMES.get(result.document_type, '未知类型')
        self._type_label.setText(type_name)
        
        # 更新整体置信度
        self._overall_confidence.set_confidence(result.overall_confidence)
        
        # 清空现有字段控件
        self._clear_fields()
        
        # 检查是否有低置信度字段
        has_low_confidence = False
        
        # 创建字段编辑控件
        for field_name, field_conf in result.fields.items():
            label = self._field_matcher.get_recognized_field_label(
                field_name, result.document_type
            )
            
            widget = FieldEditWidget(field_name, field_conf, label)
            widget.value_changed.connect(self._on_field_edited)
            
            # 插入到 stretch 之前
            self._fields_layout.insertWidget(
                self._fields_layout.count() - 1,
                widget
            )
            self._field_widgets[field_name] = widget
            
            if field_conf.is_low_confidence:
                has_low_confidence = True
        
        # 显示/隐藏警告
        self._warning_label.setVisible(has_low_confidence)
        
        # 更新汇总文本
        self._update_summary()
    
    def _clear_fields(self):
        """清空字段控件"""
        for widget in self._field_widgets.values():
            widget.deleteLater()
        self._field_widgets.clear()
    
    def _on_field_edited(self, field_name: str, new_value: str):
        """字段编辑事件"""
        self.field_edited.emit(field_name, new_value)
        
        # 更新结果对象
        if self._current_result and field_name in self._current_result.fields:
            field_conf = self._current_result.fields[field_name]
            field_conf.value = new_value
        
        # 更新汇总文本
        self._update_summary()
    
    def _setup_summary_section(self, parent_layout):
        """设置汇总信息区域"""
        # 标题
        summary_title = QLabel("信息汇总")
        summary_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {COLORS['text_primary']};
            margin-top: 8px;
        """)
        parent_layout.addWidget(summary_title)
        
        # 汇总文本框和复制按钮
        summary_layout = QHBoxLayout()
        
        # 汇总文本框
        self._summary_text = QTextEdit()
        self._summary_text.setPlaceholderText("识别信息将自动汇总显示在这里...")
        self._summary_text.setMaximumHeight(80)
        self._summary_text.setStyleSheet(input_style(multiline=True))
        summary_layout.addWidget(self._summary_text, 1)
        
        # 一键复制按钮
        self._copy_btn = QPushButton("一键复制")
        self._copy_btn.setStyleSheet(button_style(primary=True, compact=True))
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._on_copy_summary)
        summary_layout.addWidget(self._copy_btn)
        summary_layout.setAlignment(self._copy_btn, Qt.AlignmentFlag.AlignTop)
        
        parent_layout.addLayout(summary_layout)
    
    def _update_summary(self):
        """更新汇总文本"""
        if not self._current_result:
            return
        
        # 获取字段值
        fields = self._current_result.fields
        
        # 构建汇总文本（按照指定格式）
        parts = []
        
        # 1. 姓名
        if 'name' in fields:
            parts.append(fields['name'].value)
        
        # 2. 性别
        if 'gender' in fields:
            parts.append(f"，{fields['gender'].value}")
        
        # 3. 出生日期
        if 'birth_date' in fields:
            birth_date = fields['birth_date'].value
            parts.append(f"，{birth_date}出生")
        
        # 4. 民族
        if 'ethnicity' in fields:
            parts.append(f"，{fields['ethnicity'].value}")
        
        # 5. 住址
        if 'address' in fields:
            parts.append(f"，住{fields['address'].value}")
        
        # 6. 身份证号
        if 'id_number' in fields:
            parts.append(f"，公民身份号码：{fields['id_number'].value}。")
        
        # 如果没有识别到标准字段，显示所有字段
        if not parts:
            for field_name, field_conf in fields.items():
                if field_conf.value:
                    label = self._field_matcher.get_recognized_field_label(
                        field_name, self._current_result.document_type
                    )
                    parts.append(f"{label}：{field_conf.value}")
        
        summary = "".join(parts)
        self._summary_text.setText(summary)
    
    def _on_copy_summary(self):
        """一键复制汇总文本"""
        text = self._summary_text.toPlainText()
        if not text:
            QMessageBox.information(self, "提示", "没有可复制的内容")
            return
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # 显示提示
        QMessageBox.information(self, "复制成功", "汇总信息已复制到剪贴板！")
    
    def _on_re_recognize(self):
        """重新识别"""
        self.re_recognize_requested.emit()
    
    def _on_apply_to_template(self):
        """应用到模板变量"""
        if not self._current_result:
            return
        
        # 获取所有字段的当前值
        values = {}
        for field_name, widget in self._field_widgets.items():
            values[field_name] = widget.get_value()
        
        self.apply_to_template.emit(values)
    
    def get_all_values(self) -> Dict[str, str]:
        """获取所有字段的当前值"""
        values = {}
        for field_name, widget in self._field_widgets.items():
            values[field_name] = widget.get_value()
        return values
    
    def clear(self):
        """清空显示"""
        self._current_result = None
        self._type_label.setText("未识别")
        self._overall_confidence.set_confidence(0.0)
        self._clear_fields()
        self._warning_label.setVisible(False)
        if hasattr(self, '_summary_text'):
            self._summary_text.clear()
    
    def highlight_field(self, field_name: str):
        """高亮显示指定字段"""
        if field_name in self._field_widgets:
            widget = self._field_widgets[field_name]
            widget._input.setFocus()
            widget._input.selectAll()

