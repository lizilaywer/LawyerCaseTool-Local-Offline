# -*- coding: utf-8 -*-
"""电子化归档 - 变量定义面板

显示和管理归档变量，支持添加、删除、导入、导出变量。
支持拖拽排序，卡片化设计。
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QMessageBox,
    QFileDialog,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint, QRect
from PySide6.QtGui import QDrag, QColor, QFont, QMouseEvent, QPixmap, QPainter, QPen

from src.utils.logger import get_logger
from src.config.config_manager import get_config_manager
from src.gui.widgets.screenshot_tool import ScreenshotTool
from src.gui.widgets.ocr_worker import OcrWorker
from src.gui.styles import APP_COLORS, button_style, input_style
from src.utils.platform_utils import get_default_monospace_font_family, is_windows
COLORS = {**APP_COLORS, 'border_hover': '#cbd5e1'}


class VariableItem(QFrame):
    """单个变量项控件 - 卡片化设计，支持拖拽排序

    结构：
    ┌─────────────────────────────────┐
    │ ≡  委托人姓名               [×] │  ← 拖拽指示器 + 变量名称 + 删除
    │     {{client_name}}             │  ← 变量名（蓝色标签）
    │ ┌───────────────────────────┐   │
    │ │ 张三                 [📷] │   │  ← 值输入框 + OCR按钮
    │ └───────────────────────────┘   │
    └─────────────────────────────────┘
    
    拖拽方式：按住卡片任意位置（除按钮外）拖动
    """

    # 信号
    value_changed = Signal(str, str)  # (变量key, 新值)
    delete_requested = Signal(str)     # 变量key
    ocr_requested = Signal(str)        # 变量key - 请求OCR识别

    def __init__(self, var_key: str, var_name: str, value: str = "", parent=None):
        super().__init__(parent)
        self._var_key = var_key
        self._var_name = var_name
        
        # 拖拽相关
        self._drag_start_pos = None
        self._is_dragging = False
        
        # 设置接受鼠标移动事件
        self.setMouseTracking(True)

        self._setup_ui(value)

    def _setup_ui(self, value: str) -> None:
        """设置界面 - 卡片化设计"""
        c = COLORS
        
        # 设置卡片基础样式
        self.setProperty("archiveVariableItem", True)
        self.setStyleSheet(f"""
            QFrame[archiveVariableItem="true"] {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
            QFrame[archiveVariableItem="true"]:hover {{
                border-color: {c['border_hover']};
            }}
        """)
        
        # 添加轻量阴影效果
        self._create_shadow()
        
        # 设置尺寸策略
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 6, 6, 6)
        layout.setSpacing(5)

        # 左侧：拖拽指示器（三道杠图标）
        drag_indicator = QLabel("≡")
        drag_indicator.setFixedSize(16, 24)
        drag_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drag_indicator.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #94a3b8;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
        """)
        drag_indicator.setToolTip("按住卡片任意位置拖动可调整顺序")
        layout.addWidget(drag_indicator)

        # 右侧：内容区域
        content_layout = QVBoxLayout()
        content_layout.setSpacing(5)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部：变量名称 + 删除按钮
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        # 变量名称
        name_label = QLabel(self._var_name)
        name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        name_label.setMinimumWidth(0)
        name_label.setStyleSheet(f"""
            background: transparent;
            border: none;
            font-weight: 600;
            font-size: 13px;
            color: {c['text_primary']};
        """)
        top_layout.addWidget(name_label, 1)

        key_label = QLabel(self._var_key)
        key_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        key_label.setMinimumWidth(0)
        key_label.setStyleSheet(f"""
            background: transparent;
            border: none;
            font-family: '{get_default_monospace_font_family()}';
            font-size: 10px;
            color: {c['text_muted']};
        """)
        key_label.setToolTip(f"{{{{{self._var_key}}}}}")
        key_label.setMaximumWidth(82)
        top_layout.addWidget(key_label)

        # 删除按钮
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(22, 22)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_muted']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 0;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: #fef2f2;
                color: {c['danger']};
                border-color: #fecaca;
            }}
            QPushButton:pressed {{
                background: #ffe4e6;
                color: {c['danger']};
                border-color: #fca5a5;
            }}
        """)
        delete_btn.setToolTip("删除变量")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._var_key))
        top_layout.addWidget(delete_btn)

        content_layout.addLayout(top_layout)

        # 值输入框 + OCR按钮
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self._value_input = QLineEdit()
        self._value_input.setText(value)
        self._value_input.setPlaceholderText("输入变量值...")
        self._value_input.setStyleSheet(input_style())
        self._value_input.setFixedHeight(30 if is_windows() else 28)
        self._value_input.setMinimumWidth(0)
        self._value_input.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._value_input.textChanged.connect(self._on_value_changed)
        input_layout.addWidget(self._value_input, 1)

        # OCR截图按钮
        self._ocr_btn = QPushButton("识别")
        self._ocr_btn.setFixedSize(46 if is_windows() else 44, 30 if is_windows() else 28)
        self._ocr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ocr_btn.setToolTip("截图识别")
        self._ocr_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['accent_subtle']};
                color: {c['accent']};
                border: 1px solid {c['accent_light']};
                border-radius: 8px;
                padding: 0;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['accent_light']};
                border-color: {c['accent']};
            }}
            QPushButton:pressed {{
                background: {c['accent']};
                color: white;
            }}
        """)
        self._ocr_btn.clicked.connect(self._on_ocr_clicked)
        input_layout.addWidget(self._ocr_btn)

        content_layout.addLayout(input_layout)
        layout.addLayout(content_layout, 1)

    def _create_shadow(self):
        """创建阴影效果"""
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(5)
        shadow.setColor(QColor(15, 23, 42, 18))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)

    def _on_value_changed(self, text: str) -> None:
        """值改变事件"""
        self.value_changed.emit(self._var_key, text)

    def get_key(self) -> str:
        """获取变量键"""
        return self._var_key

    def get_name(self) -> str:
        """获取变量名称"""
        return self._var_name

    def get_value(self) -> str:
        """获取变量值"""
        return self._value_input.text()

    def set_value(self, value: str) -> None:
        """设置变量值"""
        self._value_input.setText(value)
        self.value_changed.emit(self._var_key, value)

    def _on_ocr_clicked(self) -> None:
        """OCR截图按钮点击"""
        self.ocr_requested.emit(self._var_key)

    # ==================== 拖拽支持 ====================
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下 - 记录起始位置"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击了按钮（按钮会自己处理事件，这里不会收到）
            self._drag_start_pos = event.pos()
            self._is_dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动 - 处理拖拽"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if self._drag_start_pos is None:
            return
            
        # 计算移动距离
        distance = (event.pos() - self._drag_start_pos).manhattanLength()
        if distance < 15:  # 最小拖拽距离，避免误触
            return
        
        # 如果已经开始拖拽，不再重复启动
        if self._is_dragging:
            return

        self._is_dragging = True

        # 创建拖拽对象
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self._var_key)
        drag.setMimeData(mime_data)
        
        # 创建拖拽时的缩略图（整个卡片）
        pixmap = self.grab()
        # 添加半透明效果
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 180))
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        
        # 执行拖拽
        result = drag.exec(Qt.DropAction.MoveAction)
        
        # 拖拽结束，重置状态
        self._is_dragging = False
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        self._drag_start_pos = None
        self._is_dragging = False
        super().mouseReleaseEvent(event)


class DropIndicator(QFrame):
    """拖拽时的放置位置指示器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(4)
        self.setStyleSheet("""
            background: #3b82f6;
            border-radius: 2px;
        """)
        self.hide()


class ArchiveVariablePanel(QWidget):
    """变量定义面板 - 支持拖拽排序

    功能：
    - 显示所有已定义的变量（卡片化设计）
    - 支持添加/删除变量
    - 支持拖拽排序（拖动整个卡片改变顺序）
    - 支持导入/导出 JSON
    - 与主界面模板变量系统同步（只增不减）
    """

    # 信号
    variables_changed = Signal()  # 变量列表改变
    variable_order_changed = Signal(list)  # 变量顺序改变，参数为新的key列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._config_manager = get_config_manager()
        self._variables: Dict[str, Dict[str, Any]] = {}  # key -> {name, value, ...}
        self._variable_order: List[str] = []  # 变量顺序列表

        # 截图OCR相关
        self._screenshot_tool = ScreenshotTool(self)
        self._screenshot_tool.screenshot_captured.connect(self._on_screenshot_captured)
        self._screenshot_tool.screenshot_cancelled.connect(self._on_screenshot_cancelled)
        self._ocr_worker: OcrWorker = None
        self._current_ocr_key: str = None

        # 拖拽相关
        self._drop_indicator = None
        self._drag_over_item = None

        self._setup_ui()
        self._sync_from_main()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS

        self.setProperty("archiveVariablePanel", True)
        self.setStyleSheet(f"""
            QWidget[archiveVariablePanel="true"] {{
                background: {c['surface_0']};
                border-right: 1px solid {c['border']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setProperty("archiveVariableHeader", True)
        header.setStyleSheet(f"""
            QWidget[archiveVariableHeader="true"] {{
                background: {c['surface_0']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("变量定义")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['text_primary']};")
        header_layout.addWidget(title)

        # 导入/导出按钮
        import_btn = QPushButton("导入")
        import_btn.setFixedHeight(28)
        import_btn.setStyleSheet(button_style(compact=True))
        import_btn.clicked.connect(self._on_import)
        header_layout.addWidget(import_btn)

        export_btn = QPushButton("导出")
        export_btn.setFixedHeight(28)
        export_btn.setStyleSheet(import_btn.styleSheet())
        export_btn.clicked.connect(self._on_export)
        header_layout.addWidget(export_btn)

        layout.addWidget(header)

        # 搜索框
        search_widget = QWidget()
        search_widget.setProperty("archiveVariableSearchBar", True)
        search_widget.setStyleSheet(f"""
            QWidget[archiveVariableSearchBar="true"] {{
                background: {c['surface_0']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(10, 8, 10, 8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索变量...")
        self._search_input.setStyleSheet(input_style())
        self._search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self._search_input)
        layout.addWidget(search_widget)

        # 变量列表容器（使用QWidget作为拖拽接受区域）
        self._list_container = QWidget()
        self._list_container.setStyleSheet(f"background: {c['surface_1']};")
        self._list_container.setMinimumWidth(0)
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(7)
        self._list_layout.setContentsMargins(5, 7, 9, 7)
        self._list_layout.addStretch()
        
        # 启用拖拽接受
        self._list_container.setAcceptDrops(True)
        self._list_container.dragEnterEvent = self._on_drag_enter
        self._list_container.dragMoveEvent = self._on_drag_move
        self._list_container.dragLeaveEvent = self._on_drag_leave
        self._list_container.dropEvent = self._on_drop

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
        """)
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, 1)

        # 添加变量按钮
        add_footer = QWidget()
        add_footer.setStyleSheet(f"background: {c['surface_0']}; border-top: 1px solid {c['border']};")
        add_footer_layout = QHBoxLayout(add_footer)
        add_footer_layout.setContentsMargins(8, 8, 8, 8)
        add_footer_layout.setSpacing(0)

        add_btn = QPushButton("+ 添加变量")
        add_btn.setFixedHeight(32)
        add_btn.setStyleSheet(button_style(compact=True))
        add_btn.clicked.connect(self._on_add_variable)
        add_footer_layout.addWidget(add_btn)
        layout.addWidget(add_footer)

        # 变量项字典
        self._var_items: Dict[str, VariableItem] = {}
        
        # 放置指示器
        self._drop_indicator = DropIndicator(self._list_container)

    def _sync_from_main(self) -> None:
        """从主界面模板系统同步变量（只增不减）"""
        templates = self._config_manager.get_templates()

        for template in templates:
            for var in template.get("variables", []):
                key = var.get("key", "")
                name = var.get("label", key)
                if key and key not in self._variables:
                    self._variables[key] = {
                        "name": name,
                        "value": "",
                        "source": "main",
                    }
                    self._variable_order.append(key)

        self._refresh_list()

    def _refresh_list(self, filter_text: str = "") -> None:
        """刷新变量列表"""
        # 清除现有项（保留stretch）
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._var_items.clear()

        # 按顺序添加变量项
        filter_lower = filter_text.lower() if filter_text else ""
        
        for key in self._variable_order:
            if key not in self._variables:
                continue
                
            var_data = self._variables[key]
            name = var_data.get("name", key)
            value = var_data.get("value", "")

            # 应用过滤
            if filter_text:
                if filter_lower not in key.lower() and filter_lower not in name.lower():
                    continue

            # 创建变量项卡片
            var_item = VariableItem(key, name, value)
            var_item.value_changed.connect(self._on_value_changed)
            var_item.delete_requested.connect(self._on_delete_variable)
            var_item.ocr_requested.connect(self._on_ocr_requested)

            # 插入到stretch之前
            self._list_layout.insertWidget(self._list_layout.count() - 1, var_item)
            self._var_items[key] = var_item

    def _on_search(self, text: str) -> None:
        """搜索变量"""
        self._refresh_list(text)

    def _on_value_changed(self, key: str, value: str) -> None:
        """变量值改变"""
        if key in self._variables:
            self._variables[key]["value"] = value

    def _on_delete_variable(self, key: str) -> None:
        """删除变量"""
        if key in self._variables:
            del self._variables[key]
            if key in self._variable_order:
                self._variable_order.remove(key)
            self.variables_changed.emit()
            self._refresh_list()

    def _on_ocr_requested(self, key: str) -> None:
        """OCR截图请求"""
        self._current_ocr_key = key
        self._screenshot_tool.start_screenshot()

    def _on_screenshot_captured(self, pixmap) -> None:
        """截图完成，启动OCR识别"""
        if not self._current_ocr_key:
            return

        self._set_ocr_buttons_enabled(False)
        self._ocr_worker = OcrWorker(pixmap)
        self._ocr_worker.ocr_completed.connect(self._on_ocr_completed)
        self._ocr_worker.ocr_failed.connect(self._on_ocr_failed)
        self._ocr_worker.start()

    def _on_screenshot_cancelled(self) -> None:
        """用户取消截图"""
        self._current_ocr_key = None

    def _on_ocr_completed(self, text: str, text_blocks: list) -> None:
        """OCR识别完成"""
        key = self._current_ocr_key

        # 复制识别结果到系统剪贴板
        if text.strip():
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

        # 填充到对应变量
        if key and key in self._var_items:
            self._var_items[key].set_value(text)
            
            if text.strip():
                from PySide6.QtWidgets import QToolTip
                QToolTip.showText(self.mapToGlobal(self.pos()), f"识别成功: {text[:30]}...", self)
            else:
                QMessageBox.information(self, "OCR识别", "未能识别到文字，请尝试截取更清晰的区域。")

        self._current_ocr_key = None
        self._set_ocr_buttons_enabled(True)

    def _on_ocr_failed(self, error: str) -> None:
        """OCR识别失败"""
        self._logger.error(f"OCR识别失败: {error}")
        self._current_ocr_key = None
        self._set_ocr_buttons_enabled(True)
        QMessageBox.warning(self, "OCR识别失败", f"无法识别截图内容:\n{error}")

    def _set_ocr_buttons_enabled(self, enabled: bool) -> None:
        """设置所有OCR按钮的启用状态"""
        for item in self._var_items.values():
            if hasattr(item, '_ocr_btn'):
                item._ocr_btn.setEnabled(enabled)

    def _on_add_variable(self) -> None:
        """添加新变量"""
        from PySide6.QtWidgets import QInputDialog

        key, ok = QInputDialog.getText(self, "添加变量", "变量名（英文，如 client_address）：")
        if not ok or not key:
            return

        key = key.strip()

        if key in self._variables:
            QMessageBox.warning(self, "警告", f"变量 '{key}' 已存在")
            return

        name, ok = QInputDialog.getText(self, "添加变量", "变量显示名（如 委托人地址）：", text=key)
        if not ok:
            name = key

        self._variables[key] = {
            "name": name.strip(),
            "value": "",
            "source": "custom",
        }
        self._variable_order.append(key)

        self._refresh_list()
        self.variables_changed.emit()

    def add_variable(self, key: str, name: str, value: str = "") -> None:
        """添加变量（程序调用）"""
        if key not in self._variables:
            self._variables[key] = {
                "name": name,
                "value": value,
                "source": "custom",
            }
            self._variable_order.append(key)
            self._refresh_list()
            self.variables_changed.emit()
        else:
            self.set_value(key, value)

    def set_value(self, key: str, value: str) -> None:
        """设置变量值"""
        if key in self._variables:
            self._variables[key]["value"] = value
            if key in self._var_items:
                self._var_items[key].set_value(value)

    def get_value(self, key: str) -> str:
        """获取变量值"""
        return self._variables.get(key, {}).get("value", "")

    def get_all_values(self) -> Dict[str, str]:
        """获取所有变量值"""
        return {key: data.get("value", "") for key, data in self._variables.items()}

    def get_all_variables(self) -> Dict[str, Dict[str, Any]]:
        """获取所有变量信息"""
        return self._variables.copy()

    def has_variable(self, key: str) -> bool:
        """检查变量是否存在"""
        return key in self._variables

    def get_variable_list(self) -> List[Dict[str, str]]:
        """获取变量列表（用于下拉菜单）"""
        return [
            {"key": key, "name": self._variables[key].get("name", key)}
            for key in self._variable_order
            if key in self._variables
        ]

    def _on_import(self) -> None:
        """导入 JSON 文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入变量", "", "JSON 文件 (*.json);;所有文件 (*.*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            variables = data.get("variables", [])
            count = 0

            for var in variables:
                key = var.get("key", "")
                name = var.get("name", key)
                value = var.get("value", "")

                if key and key not in self._variables:
                    self._variables[key] = {
                        "name": name,
                        "value": value,
                        "source": "import",
                    }
                    self._variable_order.append(key)
                    count += 1
                elif key:
                    self._variables[key]["value"] = value
                    count += 1

            self._refresh_list()
            self.variables_changed.emit()
            QMessageBox.information(self, "导入成功", f"已导入 {count} 个变量")

        except Exception as e:
            self._logger.error(f"导入变量失败: {e}")
            QMessageBox.warning(self, "导入失败", str(e))

    def _on_export(self) -> None:
        """导出到 JSON 文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出变量",
            f"variables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON 文件 (*.json)"
        )

        if not file_path:
            return

        try:
            data = {
                "variables": [
                    {
                        "key": key,
                        "name": self._variables[key].get("name", key),
                        "value": self._variables[key].get("value", ""),
                        "exported_at": datetime.now().isoformat()
                    }
                    for key in self._variable_order
                    if key in self._variables
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "导出成功", f"已导出到:\n{file_path}")

        except Exception as e:
            self._logger.error(f"导出变量失败: {e}")
            QMessageBox.warning(self, "导出失败", str(e))

    # ==================== 拖拽排序支持 ====================
    
    def _on_drag_enter(self, event):
        """拖拽进入"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self._drop_indicator.show()

    def _on_drag_move(self, event):
        """拖拽移动 - 显示放置位置指示器"""
        if not event.mimeData().hasText():
            return
            
        # 找到最近的插入位置
        pos = event.position().toPoint()
        insert_y = self._calculate_drop_position(pos.y())
        
        # 移动指示器到该位置
        self._drop_indicator.move(12, insert_y - 2)
        self._drop_indicator.resize(self._list_container.width() - 24, 4)
        self._drop_indicator.show()
        
        event.acceptProposedAction()

    def _on_drag_leave(self, event):
        """拖拽离开"""
        self._drop_indicator.hide()

    def _on_drop(self, event):
        """放置事件 - 处理变量重新排序"""
        if not event.mimeData().hasText():
            return
            
        source_key = event.mimeData().text()
        if source_key not in self._variable_order:
            return
        
        # 计算放置位置对应的索引
        pos = event.position().toPoint()
        insert_y = pos.y()
        insert_index = self._calculate_insert_index(insert_y)
        
        # 获取当前索引
        old_index = self._variable_order.index(source_key)
        
        # 如果放回原位置，不做操作
        if old_index == insert_index or old_index == insert_index - 1:
            self._drop_indicator.hide()
            event.acceptProposedAction()
            return
        
        # 调整插入位置（考虑移除后的变化）
        if old_index < insert_index:
            insert_index -= 1
        
        # 执行移动
        self._variable_order.pop(old_index)
        self._variable_order.insert(insert_index, source_key)
        
        self._logger.debug(f"变量排序: {source_key} 从位置 {old_index} 移动到 {insert_index}")
        
        # 隐藏指示器
        self._drop_indicator.hide()
        
        # 刷新列表
        self._refresh_list()
        
        # 发送信号
        self.variable_order_changed.emit(self._variable_order.copy())
        
        event.acceptProposedAction()

    def _calculate_drop_position(self, y_pos: int) -> int:
        """计算放置指示器的Y坐标位置"""
        if not self._var_items:
            return 12  # 默认顶部位置
        
        # 获取所有可见项的位置
        for i, key in enumerate(self._variable_order):
            if key not in self._var_items:
                continue
            item = self._var_items[key]
            item_geo = item.geometry()
            item_center = item_geo.y() + item_geo.height() // 2
            
            if y_pos < item_center:
                return item_geo.y()
        
        # 默认放在最后一个后面
        last_key = None
        for key in reversed(self._variable_order):
            if key in self._var_items:
                last_key = key
                break
        
        if last_key:
            last_geo = self._var_items[last_key].geometry()
            return last_geo.y() + last_geo.height() + 10  # 10是间距
        
        return 12

    def _calculate_insert_index(self, y_pos: int) -> int:
        """计算插入索引"""
        if not self._var_items:
            return 0
        
        for i, key in enumerate(self._variable_order):
            if key not in self._var_items:
                continue
            item = self._var_items[key]
            item_geo = item.geometry()
            item_center = item_geo.y() + item_geo.height() // 2
            
            if y_pos < item_center:
                return i
        
        return len(self._variable_order)
