# -*- coding: utf-8 -*-
"""共享 UI 样式定义 - Cherry-inspired light workbench."""

from pathlib import Path

from src.utils.platform_utils import is_windows

# 勾选图标路径（供 QCheckBox::indicator:checked 使用）
CHECK_ICON_PATH = str(Path(__file__).parent.parent.parent / "resources" / "icons" / "check.svg")

APP_COLORS = {
    # Surface backgrounds
    'surface_0': '#ffffff',
    'surface_1': '#f6f8fb',
    'surface_2': '#eef2f7',
    'surface_3': '#e4eaf3',
    'surface_4': '#d7e0ec',
    # Text
    'text_primary': '#111827',
    'text_secondary': '#4b5563',
    'text_tertiary': '#667085',
    'text_muted': '#94a3b8',
    # Accent
    'accent': '#2563eb',
    'accent_hover': '#1d4ed8',
    'accent_light': '#dbeafe',
    'accent_subtle': '#eff6ff',
    # Semantic
    'success': '#10b981',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    # Category accents
    'category_administrative': '#f59e0b',
    'category_non_litigation': '#10b981',
    'category_arbitration': '#8b5cf6',
    'category_labor_arbitration': '#8b5cf6',
    'category_commercial_arbitration': '#06b6d4',
    # Borders
    'border': '#e5eaf2',
    'border_strong': '#cdd6e3',
}

CATEGORY_NAMES = {
    "civil": "民事",
    "civil2": "民事",
    "criminal": "刑事",
    "administrative": "行政",
    "non_litigation": "非诉",
    "labor_arbitration": "劳动仲裁",
    "commercial_arbitration": "商事仲裁",
}

CATEGORY_FULL_NAMES = {
    "civil": "民事案件",
    "civil2": "民事案件",
    "criminal": "刑事案件",
    "administrative": "行政案件",
    "non_litigation": "非诉案件",
    "labor_arbitration": "劳动仲裁",
    "commercial_arbitration": "商事仲裁",
    "arbitration": "仲裁",
}

CATEGORY_COLORS = {
    "civil": ("民事", '#2563eb', '#eff6ff'),
    "civil2": ("民事", '#2563eb', '#eff6ff'),
    "criminal": ("刑事", '#ef4444', '#fef2f2'),
    "administrative": ("行政", '#d97706', '#fff7ed'),
    "non_litigation": ("非诉", '#059669', '#ecfdf5'),
    "labor_arbitration": ("劳动", '#7c3aed', '#f5f3ff'),
    "commercial_arbitration": ("商仲", '#0891b2', '#ecfeff'),
}

CONTROL_HEIGHT = 34 if is_windows() else 32
COMPACT_CONTROL_HEIGHT = 30 if is_windows() else 28
MULTILINE_MIN_HEIGHT = 88 if is_windows() else 84
TAB_V_PADDING = 8 if is_windows() else 7
TAB_H_PADDING = 14 if is_windows() else 14


def button_style(
    *,
    primary: bool = False,
    success: bool = False,
    warning: bool = False,
    compact: bool = False,
) -> str:
    """统一按钮样式。"""
    c = APP_COLORS
    radius = "10px" if compact else "12px"
    padding = "0 12px" if compact else "0 16px"
    height_weight = "700"

    if success:
        bg = c["success"]
        hover = "#059669"
        fg = "#ffffff"
        border = c["success"]
    elif warning:
        bg = c["warning"]
        hover = "#d97706"
        fg = "#ffffff"
        border = c["warning"]
    elif primary:
        bg = c["accent"]
        hover = c["accent_hover"]
        fg = "#ffffff"
        border = c["accent"]
    else:
        bg = c["surface_0"]
        hover = c["surface_1"]
        fg = c["text_secondary"]
        border = c["border"]

    return f"""
        QPushButton {{
            background: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: {radius};
            padding: {padding};
            font-size: 12px;
            font-weight: {height_weight};
            min-height: {f"{COMPACT_CONTROL_HEIGHT}px" if compact else f"{CONTROL_HEIGHT}px"};
        }}
        QPushButton:hover {{
            background: {hover};
            color: {fg if (primary or success or warning) else c['text_primary']};
            border-color: {border if (primary or success or warning) else c['border_strong']};
        }}
        QPushButton:disabled {{
            background: {c['surface_1']};
            color: {c['text_muted']};
            border-color: {c['border']};
        }}
    """


def input_style(*, multiline: bool = False) -> str:
    """统一输入框样式。"""
    c = APP_COLORS
    widget = "QTextEdit" if multiline else "QLineEdit"
    padding = "10px 12px" if multiline else "0 12px"
    return f"""
        {widget} {{
            background: {c['surface_0']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 12px;
            padding: {padding};
            font-size: 12px;
            min-height: {f"{MULTILINE_MIN_HEIGHT}px" if multiline else f"{CONTROL_HEIGHT}px"};
        }}
        {widget}:hover {{
            border-color: {c['border_strong']};
        }}
        {widget}:focus {{
            border-color: {c['accent']};
            background: #ffffff;
        }}
    """


def hint_banner_style(kind: str = "info") -> str:
    """统一提示条样式。"""
    c = APP_COLORS
    mapping = {
        "info": (c["accent_subtle"], c["accent"], c["accent_light"]),
        "warning": ("#fff7ed", "#c2410c", "#fdba74"),
        "success": ("#ecfdf5", c["success"], "#a7f3d0"),
    }
    bg, fg, border = mapping.get(kind, mapping["info"])
    return f"""
        background: {bg};
        color: {fg};
        border: 1px solid {border};
        border-radius: 14px;
        padding: 10px 12px;
        font-size: 12px;
        font-weight: 600;
    """


def card_style() -> str:
    """统一卡片容器样式。"""
    c = APP_COLORS
    return f"""
        background: {c['surface_0']};
        border: 1px solid {c['border']};
        border-radius: 16px;
    """


def combo_style() -> str:
    """统一下拉框样式。"""
    c = APP_COLORS
    return f"""
        QComboBox {{
            background: {c['surface_0']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 12px;
            padding: 0 12px;
            min-height: {CONTROL_HEIGHT}px;
            font-size: 12px;
        }}
        QComboBox:hover {{
            border-color: {c['border_strong']};
        }}
        QComboBox:focus {{
            border-color: {c['accent']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
    """


def build_app_stylesheet() -> str:
    """应用级基础样式，统一全局控件气质。"""
    c = APP_COLORS
    return f"""
        QWidget {{
            color: {c['text_primary']};
            selection-background-color: {c['accent_light']};
            selection-color: {c['text_primary']};
        }}

        QMainWindow, QDialog {{
            background: {c['surface_1']};
        }}

        QFrame[card="true"], QWidget[card="true"] {{
            background: {c['surface_0']};
            border: 1px solid {c['border']};
            border-radius: 16px;
        }}

        QGroupBox {{
            background: {c['surface_0']};
            border: 1px solid {c['border']};
            border-radius: 16px;
            margin-top: 14px;
            padding: 12px 14px 14px 14px;
            font-size: 12px;
            font-weight: 700;
            color: {c['text_primary']};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 6px;
            color: {c['text_primary']};
            background: {c['surface_0']};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background: {c['surface_0']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 12px;
            padding: 0 12px;
            min-height: {CONTROL_HEIGHT}px;
            font-size: 12px;
        }}

        QTextEdit, QPlainTextEdit {{
            padding: 10px 12px;
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border-color: {c['accent']};
            background: #ffffff;
        }}

        QPushButton, QToolButton {{
            background: {c['surface_0']};
            color: {c['text_secondary']};
            border: 1px solid {c['border']};
            border-radius: 12px;
            padding: 0 14px;
            min-height: {CONTROL_HEIGHT}px;
            font-size: 12px;
            font-weight: 700;
        }}

        QPushButton:hover, QToolButton:hover {{
            background: {c['surface_2']};
            color: {c['text_primary']};
            border-color: {c['border_strong']};
        }}

        QPushButton:disabled, QToolButton:disabled {{
            background: {c['surface_1']};
            color: {c['text_muted']};
            border-color: {c['border']};
        }}

        QTabWidget::pane {{
            border: none;
            background: transparent;
            top: 0;
        }}

        QTabBar::tab {{
            background: {c['surface_1']};
            color: {c['text_secondary']};
            border: 1px solid {c['border']};
            border-radius: 11px;
            padding: {TAB_V_PADDING}px {TAB_H_PADDING}px;
            margin-right: 8px;
            font-size: 12px;
            font-weight: 600;
        }}

        QTabBar::tab:selected {{
            background: {c['surface_0']};
            color: {c['text_primary']};
            border-color: {c['border_strong']};
        }}

        QTabBar::tab:hover:!selected {{
            background: {c['surface_2']};
        }}

        QScrollArea {{
            border: none;
            background: transparent;
        }}

        QListWidget, QTreeWidget, QTableWidget, QListView, QTreeView {{
            background: {c['surface_0']};
            border: 1px solid {c['border']};
            border-radius: 14px;
            outline: none;
            font-size: 12px;
        }}

        QListWidget::item, QTreeWidget::item, QTableWidget::item {{
            padding: 4px 6px;
        }}

        QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {{
            background: {c['surface_2']};
        }}

        QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {{
            background: {c['accent_subtle']};
            color: {c['text_primary']};
        }}

        QHeaderView::section {{
            background: {c['surface_1']};
            color: {c['text_secondary']};
            border: none;
            border-bottom: 1px solid {c['border']};
            padding: 7px 10px;
            font-size: 11px;
            font-weight: 700;
        }}

        QProgressBar {{
            background: {c['surface_2']};
            border: none;
            border-radius: 999px;
            min-height: 10px;
            text-align: center;
            color: {c['text_muted']};
        }}

        QProgressBar::chunk {{
            background: {c['accent']};
            border-radius: 999px;
        }}

        QCheckBox {{
            spacing: 6px;
            font-size: 12px;
            color: {c['text_secondary']};
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {c['border_strong']};
            border-radius: 5px;
            background: {c['surface_0']};
        }}

        QCheckBox::indicator:checked {{
            background: {c['accent']};
            border-color: {c['accent']};
            image: url({CHECK_ICON_PATH});
        }}

        QMenu {{
            background: {c['surface_0']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 6px;
        }}

        QMenu::item {{
            padding: 7px 24px 7px 12px;
            border-radius: 8px;
            color: {c['text_secondary']};
        }}

        QMenu::item:selected {{
            background: {c['accent_subtle']};
            color: {c['accent']};
        }}

        QStatusBar {{
            background: {c['surface_0']};
            color: {c['text_tertiary']};
            border-top: 1px solid {c['border']};
        }}

        QToolTip {{
            background-color: #1e293b;
            color: #ffffff;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 6px 8px;
            font-size: 12px;
            outline: none;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px 2px 2px 0;
        }}

        QScrollBar::handle:vertical {{
            background: {c['surface_3']};
            min-height: 36px;
            border-radius: 5px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {c['border_strong']};
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 0 2px 2px 2px;
        }}

        QScrollBar::handle:horizontal {{
            background: {c['surface_3']};
            min-width: 36px;
            border-radius: 5px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: {c['border_strong']};
        }}

        QScrollBar::add-line, QScrollBar::sub-line,
        QScrollBar::add-page, QScrollBar::sub-page {{
            border: none;
            background: transparent;
            width: 0;
            height: 0;
        }}
    """
