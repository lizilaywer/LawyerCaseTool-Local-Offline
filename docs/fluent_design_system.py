# -*- coding: utf-8 -*-
"""
律师案卷工具 - Fluent Design 设计系统
基于 PySide-Fluent-Widgets
"""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import QApplication

# 尝试导入 Fluent Widgets
try:
    from qfluentwidgets import (
        setTheme, Theme, setFont, FluentTranslator,
        PrimaryPushButton, PushButton, LineEdit, SearchLineEdit,
        ComboBox, CheckBox, Slider, ProgressBar,
        CardWidget, ListWidget, TreeWidget,
        MessageBox, Dialog, RoundMenu, ToolTip,
        InfoBar, InfoBarPosition,
        NavigationInterface, NavigationItemPosition,
        SegmentedWidget, Pivot, BreadcrumbBar,
        FluentWindow, SplashScreen,
        isDarkTheme, setThemeColor
    )
    FLUENT_AVAILABLE = True
except ImportError:
    FLUENT_AVAILABLE = False
    print("警告: 未安装 PySide-Fluent-Widgets，请先安装: pip install PySide6-Fluent-Widgets")


class DesignTokens:
    """设计令牌 - 统一的设计规范"""
    
    # 颜色系统
    COLORS = {
        # 主色调 - 法律蓝
        "primary": "#1e3a5f",
        "primary_light": "#2d5a87",
        "primary_dark": "#152942",
        "primary_50": "#f0f4f8",
        
        # 强调色 - 金色
        "accent": "#d4a853",
        "accent_light": "#e5c47a",
        "accent_dark": "#b8923f",
        
        # 功能色
        "success": "#22c55e",
        "success_light": "#dcfce7",
        "warning": "#f59e0b",
        "warning_light": "#fef3c7",
        "error": "#ef4444",
        "error_light": "#fee2e2",
        "info": "#3b82f6",
        "info_light": "#dbeafe",
        
        # 中性色
        "gray_50": "#f8fafc",
        "gray_100": "#f1f5f9",
        "gray_200": "#e2e8f0",
        "gray_300": "#cbd5e1",
        "gray_400": "#94a3b8",
        "gray_500": "#64748b",
        "gray_600": "#475569",
        "gray_700": "#334155",
        "gray_800": "#1e293b",
        "gray_900": "#0f172a",
    }
    
    # 字体规范
    FONTS = {
        "family": "Microsoft YaHei UI",  # Windows 默认中文字体
        "family_en": "Segoe UI",
        
        # 字号
        "size_xs": 11,      # 辅助文字
        "size_sm": 12,      # 正文小
        "size_base": 14,    # 正文
        "size_lg": 16,      # 小标题
        "size_xl": 18,      # 标题
        "size_2xl": 20,     # 大标题
        "size_3xl": 24,     # 显示标题
    }
    
    # 间距规范
    SPACING = {
        "xs": 4,
        "sm": 8,
        "md": 12,
        "lg": 16,
        "xl": 24,
        "2xl": 32,
        "3xl": 48,
    }
    
    # 圆角
    RADIUS = {
        "sm": 4,
        "md": 6,
        "lg": 8,
        "xl": 12,
        "full": 9999,
    }


class LawyerTheme:
    """律师工具主题配置"""
    
    @staticmethod
    def setup_theme(app: QApplication, dark_mode: bool = False):
        """配置应用主题"""
        if not FLUENT_AVAILABLE:
            return
            
        # 设置主题模式
        theme = Theme.DARK if dark_mode else Theme.LIGHT
        setTheme(theme, save=False)
        
        # 设置主题色（法律蓝）
        setThemeColor(DesignTokens.COLORS["primary"])
        
        # 设置全局字体
        font = QFont(DesignTokens.FONTS["family"], DesignTokens.FONTS["size_base"])
        setFont(font)
        app.setFont(font)
        
    @staticmethod
    def get_stylesheet() -> str:
        """获取自定义样式表（补充 Fluent 样式）"""
        return """
        /* 自定义法律行业样式 */
        
        /* 标题栏样式 */
        .TitleBar {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1e3a5f, stop:0.5 #2d5a87, stop:1 #1e3a5f);
            color: white;
        }
        
        /* 金色强调按钮 */
        .GoldButton {
            background-color: #d4a853;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
        }
        
        .GoldButton:hover {
            background-color: #e5c47a;
        }
        
        /* 卡片样式 */
        .LawyerCard {
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
        }
        
        .LawyerCard:hover {
            border-color: #1e3a5f;
            box-shadow: 0 4px 12px rgba(30, 58, 95, 0.1);
        }
        
        /* 模板卡片选中状态 */
        .TemplateCard[selected="true"] {
            border: 2px solid #1e3a5f;
            background-color: #f0f4f8;
        }
        
        /* 文件夹树样式 */
        QTreeWidget::item {
            padding: 6px 8px;
            border-radius: 4px;
        }
        
        QTreeWidget::item:selected {
            background-color: #f0f4f8;
            color: #1e3a5f;
        }
        
        QTreeWidget::item:hover {
            background-color: #f8fafc;
        }
        
        /* 输入框焦点样式 */
        QLineEdit:focus, QTextEdit:focus {
            border-color: #1e3a5f;
        }
        
        /* 侧边栏样式 */
        .Sidebar {
            background-color: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }
        
        /* 统计数字样式 */
        .StatNumber {
            font-size: 24px;
            font-weight: bold;
            color: #1e3a5f;
        }
        
        /* 标签样式 */
        .Tag {
            background-color: #f0f4f8;
            color: #1e3a5f;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
        }
        
        .TagOCR {
            background-color: #fef3c7;
            color: #d97706;
        }
        """


class AnimationPresets:
    """动画预设"""
    
    @staticmethod
    def fade_in(widget, duration: int = 300):
        """淡入动画"""
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        return animation
    
    @staticmethod
    def slide_in(widget, direction: str = "left", duration: int = 300):
        """滑入动画"""
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        
        current_pos = widget.pos()
        if direction == "left":
            animation.setStartValue(QPoint(-widget.width(), current_pos.y()))
        elif direction == "right":
            animation.setStartValue(QPoint(widget.parent().width(), current_pos.y()))
        elif direction == "top":
            animation.setStartValue(QPoint(current_pos.x(), -widget.height()))
        elif direction == "bottom":
            animation.setStartValue(QPoint(current_pos.x(), widget.parent().height()))
        
        animation.setEndValue(current_pos)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        return animation


# 组件使用示例代码
USAGE_EXAMPLES = '''
# ============================================
# Fluent Widgets 使用示例
# ============================================

# 1. 主窗口
from qfluentwidgets import FluentWindow

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("律师案卷自动化生成工具")
        self.resize(1200, 800)
        
        # 添加导航项
        self.addSubInterface(
            CreateCaseInterface(), 
            FluentIcon.FOLDER_ADD, 
            "创建案卷",
            NavigationItemPosition.TOP
        )
        self.addSubInterface(
            OCRInterface(), 
            FluentIcon.SCAN, 
            "信息识别",
            NavigationItemPosition.TOP
        )
        self.addSubInterface(
            TemplateInterface(), 
            FluentIcon.LAYOUT, 
            "模板管理",
            NavigationItemPosition.TOP
        )

# 2. 主要按钮
from qfluentwidgets import PrimaryPushButton, PushButton

# 主要操作按钮（蓝色）
generate_btn = PrimaryPushButton("生成案卷")
generate_btn.setIcon(FluentIcon.ACCEPT)

# 次要按钮（白色背景）
preview_btn = PushButton("预览")
preview_btn.setIcon(FluentIcon.VIEW)

# 3. 输入框
from qfluentwidgets import LineEdit, SearchLineEdit

# 普通输入框
case_number_input = LineEdit()
case_number_input.setPlaceholderText("请输入案号")
case_number_input.setText("(2024)浙01民初123号")

# 搜索框
search_input = SearchLineEdit()
search_input.setPlaceholderText("搜索模板或案卷...")

# 4. 卡片
from qfluentwidgets import CardWidget, ElevatedCardWidget

# 基础卡片
card = CardWidget()
card_layout = QVBoxLayout(card)
card_layout.addWidget(QLabel("民事案件模板"))

# 5. 消息提示
from qfluentwidgets import InfoBar, InfoBarPosition

# 成功提示
InfoBar.success(
    title="生成成功",
    content="案卷文件夹已创建完成",
    orient=Qt.Horizontal,
    isClosable=True,
    position=InfoBarPosition.TOP,
    duration=2000,
    parent=self
)

# 错误提示
InfoBar.error(
    title="生成失败",
    content="目标目录不存在",
    parent=self
)

# 6. 对话框
from qfluentwidgets import MessageBox

msg_box = MessageBox(
    "确认删除",
    "确定要删除这个模板吗？此操作不可撤销。",
    self
)
if msg_box.exec():
    # 用户点击了确认
    pass

# 7. 进度条
from qfluentwidgets import IndeterminateProgressBar, ProgressBar

# 不确定进度（正在处理）
progress = IndeterminateProgressBar()

# 确定进度
progress = ProgressBar()
progress.setValue(65)

# 8. 分段控件（替代 Tab）
from qfluentwidgets import SegmentedWidget

segmented = SegmentedWidget()
segmented.addItem("基本信息", "basic", lambda: print("基本信息"))
segmented.addItem("当事人", "party", lambda: print("当事人"))
segmented.addItem("诉讼请求", "claims", lambda: print("诉讼请求"))

# 9. 菜单
from qfluentwidgets import RoundMenu, Action, FluentIcon

menu = RoundMenu()
menu.addAction(Action(FluentIcon.FOLDER, "打开文件夹"))
menu.addAction(Action(FluentIcon.EDIT, "重命名"))
menu.addSeparator()
menu.addAction(Action(FluentIcon.DELETE, "删除"))

# 在按钮位置显示菜单
menu.exec(pos)

# 10. 树形控件
from qfluentwidgets import TreeWidget

tree = TreeWidget()
tree.setHeaderLabels(["名称", "类型", "大小"])

# 添加节点
root = QTreeWidgetItem(tree)
root.setText(0, "(2024)浙01民初123号_张三")
root.setIcon(0, FluentIcon.FOLDER.icon())

child = QTreeWidgetItem(root)
child.setText(0, "0委托手续")
child.setIcon(0, FluentIcon.FOLDER.icon())
'''

if __name__ == "__main__":
    print(USAGE_EXAMPLES)
