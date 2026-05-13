# -*- coding: utf-8 -*-
"""主窗口模块 - Modern UI v3"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QStatusBar,
    QMenuBar,
    QMenu,
    QToolBar,
    QFrame,
    QSizePolicy,
    QLineEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, QSize, QTimer, QObject, QThread, Signal, QPoint, QEvent
from PySide6.QtGui import QAction, QIcon, QFont, QColor
from PySide6.QtSvgWidgets import QSvgWidget

from src.config.config_manager import ConfigManager, get_config_manager
from src.core.case_manager import get_case_manager
from src.core.search import FileSearchService
from src.core.ocr import format_ocr_setup_message, get_ocr_dependency_status
from src.gui.widgets.template_card import TemplateCard
from src.gui.widgets.variable_input import VariablesForm
from src.gui.widgets.folder_tree import FolderTreePreview
from src.gui.generation_dialog import GenerationDialog
from src.gui.template_manager import TemplateManagerDialog
# TemplateMakerDialog is now integrated as a tab inside TemplateManagerDialog
from src.gui.settings_dialog import SettingsDialog
# TemplateMakerDialog removed - now integrated into TemplateManagerDialog
from src.utils.logger import get_logger
from src.utils.platform_utils import open_path
from src.utils.version import get_version
from src.utils.windows_runtime import apply_windows_window_tuning
from src.gui.styles import APP_COLORS as COLORS, CATEGORY_NAMES
from src.gui.window_metrics import APP_SURFACE_DEFAULT_SIZE, APP_SURFACE_MIN_SIZE
from src.gui.dashboard_widget import DashboardWidget


APP_DISPLAY_NAME = "案件文件夹管理系统"
APP_BRAND_ENGLISH = "LEXORA"


class _FileIndexWorker(QObject):
    """后台刷新文件索引，避免在 UI 线程扫盘。"""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, cases: List[Dict[str, Any]]):
        super().__init__()
        self._cases = cases

    def run(self) -> None:
        try:
            summary = FileSearchService().reindex_cases(self._cases)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(summary)


class MainWindow(QMainWindow):
    """主窗口 - Modern UI v3"""

    def __init__(self):
        super().__init__()

        self._config_manager = get_config_manager()
        self._logger = get_logger()
        self._selected_template_id: Optional[str] = None
        self._template_cards: Dict[str, TemplateCard] = {}
        self._preview_update_timer = QTimer(self)
        self._preview_update_timer.setSingleShot(True)
        self._preview_update_timer.setInterval(180)
        self._preview_update_timer.timeout.connect(self._update_preview)
        
        # 筛选状态
        self._current_filter: str = 'all'
        self._search_text: str = ''
        self._search_mode: str = "case"
        self._file_search_service: Optional[FileSearchService] = None
        self._file_index_thread: Optional[QThread] = None
        self._file_index_worker: Optional[_FileIndexWorker] = None
        self._file_index_pending: bool = False
        self._search_popup_items: List[Dict[str, Any]] = []
        self._search_update_timer = QTimer(self)
        self._search_update_timer.setSingleShot(True)
        self._search_update_timer.setInterval(120)
        self._search_update_timer.timeout.connect(self._refresh_search_popup)

        # 设置窗口图标
        self._setup_window_icon()
        
        self._setup_styles()
        self._setup_ui()
        self._refresh_ocr_ui_state()
        self._load_templates()
        self._restore_geometry()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """处理顶部搜索结果面板的键盘交互。"""
        if event.type() == QEvent.Type.KeyPress and hasattr(self, "_search_table"):
            key = event.key()
            if watched is self._top_search:
                if key == Qt.Key.Key_Down and self._search_popup.isVisible():
                    self._search_table.setFocus()
                    if self._search_table.currentRow() < 0:
                        self._search_table.setCurrentCell(0, 0)
                    return True
                if key == Qt.Key.Key_Escape and self._search_popup.isVisible():
                    self._search_popup.hide()
                    return True
            elif watched is self._search_table:
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._activate_search_popup_selection()
                    return True
                if key == Qt.Key.Key_Escape:
                    self._search_popup.hide()
                    self._top_search.setFocus()
                    return True
                if key == Qt.Key.Key_Up and self._search_table.currentRow() <= 0:
                    self._top_search.setFocus()
                    return True
        return super().eventFilter(watched, event)

    def _setup_window_icon(self) -> None:
        """设置窗口图标"""
        from PySide6.QtGui import QIcon
        from pathlib import Path
        
        # 尝试多个路径查找图标
        possible_paths = [
            Path(__file__).parent.parent.parent / 'resources' / 'icons' / 'lexora_app_icon_flat.ico',
            Path(__file__).parent.parent.parent / 'resources' / 'icons' / 'lexora_app_icon_flat.png',
            Path(__file__).parent.parent.parent / 'resources' / 'icons' / 'lexora_app_icon.ico',
            Path(__file__).parent.parent.parent / 'resources' / 'icons' / 'lexora_app_icon.png',
            Path(__file__).parent.parent.parent / 'resources' / 'icons' / 'app_icon.ico',
            Path(__file__).parent.parent.parent / 'resources' / 'icons' / 'app_logo.png',
            Path('resources/icons/lexora_app_icon_flat.ico'),
            Path('resources/icons/lexora_app_icon_flat.png'),
            Path('resources/icons/lexora_app_icon.ico'),
            Path('resources/icons/lexora_app_icon.png'),
            Path('resources/icons/app_icon.ico'),
            Path('resources/icons/app_logo.png'),
        ]
        
        for icon_path in possible_paths:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break

    def _setup_styles(self) -> None:
        """设置全局样式"""
        c = COLORS
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {c['surface_1']};
            }}

            /* 全局控件底色统一 */
            QLabel {{
                background-color: {c['surface_0']} !important;
                border: none;
            }}
            QCheckBox {{
                background-color: {c['surface_0']} !important;
                border: none;
            }}

            /* 菜单栏样式 */
            QMenuBar {{
                background-color: {c['surface_1']};
                border-bottom: 1px solid {c['border']};
                padding: 4px 8px;
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 6px 12px;
                border-radius: 8px;
            }}
            QMenuBar::item:selected {{
                background-color: {c['surface_2']};
            }}
            QMenuBar::item:pressed {{
                background-color: {c['surface_3']};
            }}
            
            /* 菜单样式 */
            QMenu {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 7px 24px 7px 12px;
                border-radius: 8px;
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
            
            /* 工具栏样式 */
            QToolBar {{
                background-color: {c['surface_1']};
                border-bottom: 1px solid {c['border']};
                padding: 8px 14px;
                spacing: 8px;
            }}
            QToolButton {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 6px 12px;
                color: {c['text_secondary']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_2']};
                border-color: {c['border_strong']};
            }}
            QToolButton:pressed {{
                background-color: {c['surface_2']};
            }}
            
            /* 状态栏样式 */
            QStatusBar {{
                background-color: {c['surface_0']};
                border-top: 1px solid {c['border']};
                color: {c['text_tertiary']};
            }}
            
            /* 滚动条样式 */
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {c['surface_3']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['border_strong']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            
            /* 分割线 */
            QSplitter::handle {{
                background-color: {c['border']};
            }}
            QSplitter::handle:horizontal {{
                width: 1px;
            }}
        """)

    def _setup_ui(self) -> None:
        """设置界面 - App Shell 架构"""
        c = COLORS
        
        self.setWindowTitle(f"{APP_DISPLAY_NAME} {APP_BRAND_ENGLISH} v{get_version()}")
        self.setMinimumSize(960, 640)
        apply_windows_window_tuning(self)

        # 保留菜单栏（向后兼容）
        self._create_menu_bar()
        
        # 隐藏原生工具栏，使用自定义 TopBar
        self._create_tool_bar()
        for toolbar in self.findChildren(QToolBar):
            toolbar.setVisible(False)

        # === App Shell 中心部件 ===
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        shell_layout = QHBoxLayout(central_widget)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # 左侧导航栏
        self._nav_rail = self._create_nav_rail()
        shell_layout.addWidget(self._nav_rail)

        # 右侧主内容区
        main_content = QWidget()
        main_content.setStyleSheet(f"background: {c['surface_1']};")
        main_layout = QVBoxLayout(main_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部栏
        self._top_bar = self._create_top_bar()
        main_layout.addWidget(self._top_bar)

        # 页面堆叠
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { border: none; background: transparent; }")

        # 页面 0: 工作台（Dashboard）
        self._dashboard = DashboardWidget()
        self._dashboard.new_case_requested.connect(self._on_new_case)
        self._dashboard.navigate_to_documents_requested.connect(lambda: self._switch_page("documents"))
        self._dashboard.navigate_to_cases_requested.connect(lambda: self._switch_page("cases"))
        self._dashboard.navigate_to_calendar_requested.connect(self._on_navigate_to_calendar_from_dashboard)
        self._dashboard.open_case_deadline_requested.connect(self._on_open_case_deadline)
        self._dashboard.filter_cases_by_status_requested.connect(self._on_filter_by_status)
        self._dashboard.filter_cases_by_category_requested.connect(self._on_filter_by_category)
        self._dashboard.new_deadline_requested.connect(self._on_new_deadline)
        self._dashboard.open_tools_tab_requested.connect(self._on_open_tools_tab)
        self._dashboard.import_case_requested.connect(self._on_import_case)
        self._dashboard.open_ocr_requested.connect(self._on_open_ocr)
        self._dashboard.show_directory_abnormal_requested.connect(self._on_directory_abnormal)
        self._stack.addWidget(self._dashboard)

        # 页面 1: 文书中心（原三栏案卷生成）
        self._document_center = self._create_document_center()
        self._stack.addWidget(self._document_center)

        # 页面 2: 案件中心（内嵌模式，不显示为弹窗）
        from src.gui.case_manager_dialog import CaseManagerDialog
        self._case_center = CaseManagerDialog(parent=self._stack, embed_mode=True)
        self._case_center.setStyleSheet(f"QDialog {{ background: {c['surface_1']}; border: none; }}")
        self._stack.addWidget(self._case_center)

        # 页面 3: 期限日历（内嵌模式）
        from src.gui.calendar_dialog import CalendarDialog
        self._calendar_page = CalendarDialog(parent=self._stack, embed_mode=True)
        self._calendar_page.setStyleSheet(f"QDialog {{ background: {c['surface_1']}; border: none; }}")
        self._calendar_page.switch_page_requested.connect(self._switch_page)
        self._stack.addWidget(self._calendar_page)

        # 页面 4: 工具中心（内嵌模式）
        from src.gui.tool_center_dialog import ToolCenterDialog
        self._tool_center_page = ToolCenterDialog(parent=self._stack, embed_mode=True)
        self._tool_center_page.setStyleSheet(f"QDialog {{ background: {c['surface_1']}; border: none; }}")
        self._tool_center_page.navigate_to_calendar_requested.connect(self._on_navigate_to_calendar_from_tool)
        self._stack.addWidget(self._tool_center_page)

        # 页面 5: 归档中心（自带文件夹选择 → 归档界面流程）
        from src.gui.archive_center_widget import ArchiveCenterWidget
        self._archive_center = ArchiveCenterWidget(self._stack)
        self._stack.addWidget(self._archive_center)

        main_layout.addWidget(self._stack, 1)

        # 状态栏
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {c['surface_0']};
                border-top: 1px solid {c['border']};
                color: {c['text_tertiary']};
                font-size: 11px;
                font-weight: 500;
                padding: 0 16px;
            }}
        """)
        main_layout.addWidget(self._status_bar)
        self._update_status_bar()

        shell_layout.addWidget(main_content, 1)

        # 默认显示工作台
        self._switch_page("dashboard")

    def _create_nav_rail(self) -> QFrame:
        """创建左侧导航栏"""
        c = COLORS
        rail = QFrame()
        rail.setFixedWidth(64)
        rail.setStyleSheet(f"""
            QFrame {{
                background: {c['surface_0']};
                border-right: 1px solid {c['border']};
            }}
        """)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(8, 6, 8, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Logo
        logo_path = Path(__file__).parent.parent.parent / 'resources' / 'icons' / 'lexora_nav_logo.svg'
        if logo_path.exists():
            logo = QSvgWidget(str(logo_path))
            logo.setFixedSize(48, 48)
            logo.setToolTip(f"{APP_BRAND_ENGLISH} - {APP_DISPLAY_NAME}")
            logo.setStyleSheet("background: transparent; border: none;")
        else:
            logo = QLabel()
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setFixedSize(48, 48)
            logo.setToolTip(f"{APP_BRAND_ENGLISH} - {APP_DISPLAY_NAME}")
            logo.setText("案")
            logo.setStyleSheet(f"""
                background: {c['accent_subtle']};
                color: {c['accent']};
                border-radius: 8px;
                font-size: 16px;
                font-weight: 700;
            """)
        layout.addWidget(logo)
        layout.addSpacing(16)

        # Nav items
        self._nav_buttons = []
        nav_items = [
            ("dashboard", "工作台"),
            ("cases", "案件"),
            ("calendar", "日历"),
            ("documents", "创建"),
            ("archive", "归档"),
            ("tools", "工具"),
        ]

        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setProperty("navKey", key)
            btn.setCheckable(True)
            btn.setFixedSize(48, 48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['text_muted']};
                    border: none;
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {c['surface_1']};
                    color: {c['text_secondary']};
                }}
                QPushButton:checked {{
                    background: {c['accent_subtle']};
                    color: {c['accent']};
                }}
            """)
            btn.clicked.connect(lambda checked=False, k=key: self._on_nav_clicked(k))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Settings at bottom
        settings_btn = QPushButton("设置")
        settings_btn.setFixedSize(48, 48)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['text_muted']};
                border: none;
                border-radius: 8px;
                font-size: 10px;
                font-weight: 600;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {c['surface_1']};
                color: {c['text_secondary']};
            }}
        """)
        settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(settings_btn)

        return rail

    def _create_top_bar(self) -> QWidget:
        """创建顶部全局栏"""
        c = COLORS
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"""
            QWidget {{
                background: {c['surface_0']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        # Title
        self._page_title = QLabel("案件指挥台")
        self._page_title.setStyleSheet(f"""
            color: {c['text_primary']};
            font-size: 16px;
            font-weight: 700;
        """)
        layout.addWidget(self._page_title)

        # Search — 全局搜索框，输入时在下方面板展示案件/文件结果
        self._top_search = QLineEdit()
        self._top_search.setPlaceholderText("搜索案件...")
        self._top_search.setFixedHeight(36)
        self._top_search.setMaximumWidth(360)
        self._top_search.installEventFilter(self)
        self._top_search.setStyleSheet(f"""
            QLineEdit {{
                background: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                padding: 0 12px;
                color: {c['text_primary']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {c['accent']};
                background: {c['surface_0']};
            }}
        """)
        self._top_search.returnPressed.connect(self._on_global_search)
        self._top_search.textChanged.connect(self._on_top_search_text_changed)
        self._search_case_map: dict[str, str] = {}  # name -> case_id

        layout.addWidget(self._top_search)

        self._search_mode_btn = QPushButton("案件搜索")
        self._search_mode_btn.setFixedSize(104, 36)
        self._search_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_mode_btn.setToolTip("切换案件搜索 / 文件搜索")
        self._search_mode_btn.clicked.connect(self._toggle_search_mode)
        layout.addWidget(self._search_mode_btn)
        self._create_search_popup()
        self._update_search_mode_ui()

        layout.addStretch()

        # New case button — 移至最右侧，替代原头像位置
        new_btn = QPushButton("+ 新建案件")
        new_btn.setFixedHeight(36)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['accent']};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {c['accent_hover']};
            }}
        """)
        new_btn.clicked.connect(self._on_new_case)
        layout.addWidget(new_btn)

        return bar

    def _create_search_popup(self) -> None:
        """创建顶部搜索即时结果面板。"""
        c = COLORS
        self._search_popup = QFrame(self)
        self._search_popup.setObjectName("globalSearchPopup")
        self._search_popup.setFrameShape(QFrame.Shape.NoFrame)
        self._search_popup.setStyleSheet(f"""
            QFrame#globalSearchPopup {{
                background: {c['surface_0']};
                border: 1px solid {c['border_strong']};
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
            }}
        """)
        self._search_popup.hide()

        popup_layout = QVBoxLayout(self._search_popup)
        popup_layout.setContentsMargins(10, 8, 10, 10)
        popup_layout.setSpacing(6)

        self._search_popup_title = QLabel("输入关键词搜索")
        self._search_popup_title.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 12px;
            font-weight: 700;
            padding: 0 2px 2px 2px;
        """)
        popup_layout.addWidget(self._search_popup_title)

        self._search_table = QTableWidget(0, 3, self._search_popup)
        self._search_table.installEventFilter(self)
        self._search_table.setHorizontalHeaderLabels(["名称", "案件", "位置"])
        self._search_table.verticalHeader().hide()
        self._search_table.setShowGrid(False)
        self._search_table.setAlternatingRowColors(False)
        self._search_table.setWordWrap(False)
        self._search_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._search_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._search_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._search_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._search_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._search_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._search_table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._search_table.itemDoubleClicked.connect(lambda _item: self._activate_search_popup_selection())
        self._search_table.verticalHeader().setDefaultSectionSize(30)
        self._search_table.verticalHeader().setMinimumSectionSize(30)
        header = self._search_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsMovable(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._search_table.setStyleSheet(f"""
            QTableWidget {{
                background: {c['surface_0']};
                border: none;
                outline: none;
                color: {c['text_primary']};
                font-size: 12px;
                selection-background-color: {c['accent_subtle']};
                selection-color: {c['text_primary']};
            }}
            QHeaderView::section {{
                background: {c['surface_1']};
                color: {c['text_tertiary']};
                border: none;
                border-bottom: 1px solid {c['border']};
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 700;
            }}
            QTableWidget::item {{
                border: none;
                padding: 3px 8px;
            }}
            QTableWidget::item:selected {{
                background: {c['accent_subtle']};
                color: {c['text_primary']};
            }}
        """)
        popup_layout.addWidget(self._search_table)

    def _create_document_center(self) -> QWidget:
        """创建文书中心（原三栏案卷生成布局）"""
        c = COLORS
        widget = QWidget()
        widget.setStyleSheet(f"background: {c['surface_1']};")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        left_panel = self._create_template_panel()
        splitter.addWidget(left_panel)

        middle_panel = self._create_variables_panel()
        splitter.addWidget(middle_panel)

        right_panel = self._create_preview_panel()
        splitter.addWidget(right_panel)

        middle_panel.setMinimumWidth(300)
        right_panel.setMinimumWidth(200)
        splitter.setCollapsible(0, True)

        splitter.setSizes([280, 400, 320])
        splitter.setHandleWidth(1)

        return widget

    def _switch_page(self, page_key: str) -> None:
        """切换页面"""
        if hasattr(self, "_search_popup"):
            self._search_popup.hide()

        page_map = {
            "dashboard": (0, "案件指挥台"),
            "documents": (1, "创建中心"),
            "cases": (2, "案件中心"),
            "calendar": (3, "期限日历"),
            "tools": (4, "工具中心"),
            "archive": (5, "归档中心"),
        }

        if page_key in page_map:
            index, title = page_map[page_key]
            self._stack.setCurrentIndex(index)
            self._page_title.setText(title)

        # 回到工作台时刷新数据，确保显示最新状态
        if page_key == "dashboard" and hasattr(self, "_dashboard"):
            self._dashboard.refresh_data()

        # 案件中心、创建中心页面自带完整工具栏，整个 TopBar 隐藏以节省空间
        if hasattr(self, "_top_bar"):
            self._top_bar.setVisible(page_key not in ("cases", "documents"))

        # Update nav buttons
        for btn in self._nav_buttons:
            btn.setChecked(btn.property("navKey") == page_key)

    def _on_nav_clicked(self, key: str) -> None:
        """统一处理导航栏点击"""
        # 更新按钮状态
        for btn in self._nav_buttons:
            btn.setChecked(btn.property("navKey") == key)

        # 所有模块都已内嵌，直接切换页面
        if key in ("dashboard", "documents", "cases", "calendar", "tools", "archive"):
            self._switch_page(key)

    def _update_status_bar(self):
        """更新状态栏信息"""
        try:
            from src.config.path_manager import get_path_manager
            pm = get_path_manager()
            self._status_bar.showMessage(
                f"本地模式  |  模板目录: {pm.get_templates_dir()}  |  v{get_version()}"
            )
        except Exception:
            self._status_bar.showMessage(f"就绪  |  v{get_version()}")

    def _create_menu_bar(self) -> None:
        """创建菜单栏"""
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件(&F)")

        new_action = QAction("新建案卷(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_case)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 模板菜单
        template_menu = menu_bar.addMenu("模板(&T)")

        manage_action = QAction("管理模板(&M)...", self)
        manage_action.triggered.connect(self._on_manage_templates)
        template_menu.addAction(manage_action)

        maker_action = QAction("制作 Word 模板(&W)", self)
        maker_action.setShortcut("Ctrl+M")
        maker_action.triggered.connect(self._on_template_maker)
        template_menu.addAction(maker_action)

        # 设置菜单
        settings_menu = menu_bar.addMenu("设置(&S)")

        preferences_action = QAction("首选项(&P)", self)
        preferences_action.triggered.connect(self._on_settings)
        settings_menu.addAction(preferences_action)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _create_tool_bar(self) -> None:
        """创建工具栏 - 使用 QWidget 避免 QToolBar 样式覆盖"""
        c = COLORS
        
        # 创建自定义工具栏容器
        toolbar_widget = QWidget()
        toolbar_widget.setFixedHeight(48)
        toolbar_widget.setStyleSheet(f"background-color: {c['surface_0']}; border-bottom: 1px solid {c['border']};")
        
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(16, 8, 16, 8)  # 与下方内容区对齐
        toolbar_layout.setSpacing(8)

        # 模板管理按钮
        manage_btn = QPushButton("模板管理")
        manage_btn.setFixedHeight(32)
        manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        manage_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        manage_btn.clicked.connect(self._on_manage_templates)
        toolbar_layout.addWidget(manage_btn)

        # 制作模板按钮
        maker_btn = QPushButton("制作模板")
        maker_btn.setFixedHeight(32)
        maker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        maker_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                color: {c['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
            }}
        """)
        maker_btn.clicked.connect(self._on_template_maker)
        toolbar_layout.addWidget(maker_btn)

        # 电子化归档按钮
        archive_btn = QPushButton("电子化归档")
        archive_btn.setFixedHeight(32)
        archive_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        archive_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                color: {c['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
            }}
        """)
        archive_btn.clicked.connect(self._on_archive)
        toolbar_layout.addWidget(archive_btn)

        # 案件管理按钮
        case_btn = QPushButton("案件管理")
        case_btn.setFixedHeight(32)
        case_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        case_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                color: {c['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
            }}
        """)
        case_btn.clicked.connect(self._on_case_manager)
        toolbar_layout.addWidget(case_btn)

        # 期限日历按钮
        calendar_btn = QPushButton("期限日历")
        calendar_btn.setFixedHeight(32)
        calendar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        calendar_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                color: {c['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
            }}
        """)
        calendar_btn.clicked.connect(self._on_calendar)
        toolbar_layout.addWidget(calendar_btn)

        tool_center_btn = QPushButton("工具中心")
        tool_center_btn.setFixedHeight(32)
        tool_center_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tool_center_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                color: {c['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
            }}
        """)
        tool_center_btn.clicked.connect(self._on_tool_center)
        toolbar_layout.addWidget(tool_center_btn)

        toolbar_layout.addStretch()

        # 将工具栏添加到主窗口 - 移除 QToolBar 默认边距确保对齐
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setStyleSheet("border: none; padding: 0;")
        toolbar.addWidget(toolbar_widget)
        self.addToolBar(toolbar)

    def _create_template_panel(self) -> QWidget:
        """创建模板选择面板"""
        c = COLORS
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {c['surface_1']}; border-right: 1px solid {c['border']};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 面板头部
        header = QWidget()
        header.setStyleSheet("border: none;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 6)
        header_layout.setSpacing(6)

        # 搜索框 - 可输入
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索模板...")
        self._search_input.setFixedHeight(28)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 2px 10px;
                color: {c['text_primary']};
                font-size: 12px;
                min-height: 28px;
                max-height: 28px;
            }}
            QLineEdit:hover {{
                border-color: {c['border_strong']};
            }}
            QLineEdit:focus {{
                border: 1px solid {c['accent']};
            }}
        """)
        self._search_input.setMinimumHeight(28)
        self._search_input.setMaximumHeight(28)
        self._search_input.setFixedHeight(28)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        header_layout.addWidget(self._search_input)
        layout.addWidget(header)

        # 分类筛选标签 + 置顶按钮
        filter_widget = QWidget()
        filter_widget.setStyleSheet(f"border-bottom: 1px solid {c['border']}; background-color: {c['surface_2']};")
        filter_layout = QGridLayout(filter_widget)
        filter_layout.setContentsMargins(12, 6, 12, 6)
        filter_layout.setSpacing(6)
        filter_layout.setHorizontalSpacing(6)
        filter_layout.setVerticalSpacing(6)

        self._filter_buttons = []
        categories = ["全部", "民事", "刑事", "行政", "非诉", "仲裁"]
        category_map = {"民事": "civil", "刑事": "criminal", "行政": "administrative", "非诉": "non_litigation", "仲裁": "arbitration"}

        for i, cat in enumerate(categories):
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setProperty("category", category_map.get(cat, "all"))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, b=btn: self._on_filter_clicked(b))
            self._update_filter_btn_style(btn, i == 0)
            self._filter_buttons.append(btn)
            filter_layout.addWidget(btn, i // 4, i % 4)

        # 置顶按钮 - 默认隐藏，选择模板后显示
        self._pin_btn = QPushButton("📌 置顶")
        self._pin_btn.setCheckable(True)
        self._pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin_btn.setFixedSize(88, 26)
        self._pin_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 7px;
                color: {c['text_secondary']};
                font-size: 11px;
                font-weight: 600;
                padding: 0 8px;
                text-align: center;
                min-height: 26px;
                max-height: 26px;
            }}
            QPushButton:hover {{
                border-color: {c['accent']};
                background-color: {c['accent_subtle']};
                color: {c['accent']};
            }}
            QPushButton:checked {{
                border-color: {c['accent']};
                background-color: {c['accent_subtle']};
                color: {c['accent']};
            }}
        """)
        self._pin_btn.setToolTip("置顶当前模板（全部最多3个，分类最多1个）")
        self._pin_btn.clicked.connect(self._on_pin_button_clicked)
        self._pin_btn.setVisible(False)
        filter_layout.addWidget(self._pin_btn, 1, 3)
        
        layout.addWidget(filter_widget)

        # 滚动区域 - 模板列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._template_container = QWidget()
        self._template_container.setStyleSheet(f"background-color: {c['surface_1']};")
        self._template_layout = QVBoxLayout(self._template_container)
        self._template_layout.setSpacing(8)
        self._template_layout.setContentsMargins(10, 10, 10, 10)
        self._template_layout.addStretch()

        scroll.setWidget(self._template_container)
        layout.addWidget(scroll)

        # 底部按钮 — 新建模板 + 模板管理
        footer = QWidget()
        footer.setStyleSheet(f"border-top: 1px solid {c['border']}; background-color: {c['surface_2']};")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 10, 10, 10)
        footer_layout.setSpacing(8)

        add_btn = QPushButton("+ 新建模板")
        add_btn.setFixedHeight(30)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 0 8px;
                font-size: 11px;
                font-weight: 600;
                min-height: 30px;
                max-height: 30px;
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
                border-color: {c['border_strong']};
            }}
        """)
        add_btn.clicked.connect(self._on_add_template)
        footer_layout.addWidget(add_btn, 1)

        manage_btn = QPushButton("± 模板管理")
        manage_btn.setFixedHeight(30)
        manage_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 0 8px;
                font-size: 11px;
                font-weight: 600;
                min-height: 30px;
                max-height: 30px;
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
                border-color: {c['border_strong']};
            }}
        """)
        manage_btn.clicked.connect(self._on_manage_templates)
        footer_layout.addWidget(manage_btn, 1)

        layout.addWidget(footer)

        return panel

    def _create_variables_panel(self) -> QWidget:
        """创建变量输入面板"""
        c = COLORS
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {c['surface_0']};")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        toolbar = QWidget()
        toolbar.setStyleSheet(f"border-bottom: 1px solid {c['border']};")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 10, 16, 10)

        # 面包屑
        self._breadcrumb = QLabel(f"<span style='color: {c['text_tertiary']};'>案卷生成</span> / <span style='font-weight: 500;'>请选择模板</span>")
        self._breadcrumb.setStyleSheet(f"font-size: 13px; color: {c['text_secondary']};")
        toolbar_layout.addWidget(self._breadcrumb)
        toolbar_layout.addStretch()

        reset_btn = QPushButton("重置")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_secondary']};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
            }}
        """)
        reset_btn.clicked.connect(self._on_clear_values)
        toolbar_layout.addWidget(reset_btn)

        save_btn = QPushButton("保存草稿")
        save_btn.setStyleSheet(reset_btn.styleSheet())
        save_btn.setVisible(False)  # 功能尚未实现，暂时隐藏
        toolbar_layout.addWidget(save_btn)

        layout.addWidget(toolbar)

        # 滚动区域 - 表单
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        form_container = QWidget()
        form_container.setStyleSheet(f"background-color: {c['surface_0']};")
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(20, 8, 20, 16)
        form_layout.setSpacing(12)

        # 表单标题
        form_header_title = QLabel("填写案件信息")
        form_header_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['text_primary']}; margin-bottom: 2px;")
        form_layout.addWidget(form_header_title)
        


        # OCR 信息识别区域
        ocr_frame = QFrame()
        ocr_frame.setProperty("mainWindowOcrCard", True)
        ocr_frame.setMinimumHeight(92)
        ocr_frame.setStyleSheet(f"""
            QFrame[mainWindowOcrCard="true"] {{
                background-color: {c['accent_subtle']};
                border-radius: 10px;
            }}
        """)
        ocr_layout = QVBoxLayout(ocr_frame)
        ocr_layout.setContentsMargins(10, 8, 10, 8)
        ocr_layout.setSpacing(6)

        ocr_title = QLabel("智能信息识别")
        ocr_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['text_primary']}; background: transparent;")
        ocr_layout.addWidget(ocr_title)
        
        ocr_desc = QLabel("上传判决书、身份证等文件，自动提取案件信息填充表单")
        ocr_desc.setWordWrap(True)
        ocr_desc.setStyleSheet(f"font-size: 11px; color: {c['text_secondary']}; background: transparent;")
        ocr_layout.addWidget(ocr_desc)

        self._ocr_status_label = QLabel()
        self._ocr_status_label.setWordWrap(True)
        self._ocr_status_label.setStyleSheet(f"font-size: 11px; color: {c['text_tertiary']}; background: transparent;")
        ocr_layout.addWidget(self._ocr_status_label)

        ocr_actions = QHBoxLayout()
        ocr_actions.setSpacing(8)
        
        self._ocr_primary_btn = QPushButton("上传文件")
        self._ocr_primary_btn.setFixedHeight(28)
        self._ocr_primary_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
                min-height: 28px;
                max-height: 28px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
        """)
        self._ocr_primary_btn.clicked.connect(self._on_info_extraction)
        ocr_actions.addWidget(self._ocr_primary_btn)

        self._ocr_help_btn = QPushButton("安装说明")
        self._ocr_help_btn.setFixedHeight(28)
        self._ocr_help_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
                min-height: 28px;
                max-height: 28px;
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
            }}
        """)
        self._ocr_help_btn.clicked.connect(self._show_ocr_setup_guide)
        ocr_actions.addWidget(self._ocr_help_btn)

        self._ocr_paste_btn = QPushButton("粘贴截图")
        self._ocr_paste_btn.setFixedHeight(28)
        self._ocr_paste_btn.setStyleSheet(self._ocr_help_btn.styleSheet())
        ocr_actions.addWidget(self._ocr_paste_btn)
        ocr_actions.addStretch()
        ocr_layout.addLayout(ocr_actions)

        form_layout.addWidget(ocr_frame)

        # 变量表单
        self._variables_form = VariablesForm()
        self._variables_form.values_changed.connect(self._on_values_changed)
        form_layout.addWidget(self._variables_form)

        form_layout.addStretch()
        scroll.setWidget(form_container)
        layout.addWidget(scroll, 1)

        # 底部按钮栏
        footer = QWidget()
        footer.setStyleSheet(f"border-top: 1px solid {c['border']}; background-color: {c['surface_1']};")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 10, 16, 10)  # 统一边距

        # 状态
        status = QLabel("● 就绪")
        status.setStyleSheet(f"color: {c['success']}; font-size: 12px;")
        footer_layout.addWidget(status)

        last_saved = QLabel("上次保存：刚刚")
        last_saved.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px;")
        footer_layout.addWidget(last_saved)

        footer_layout.addStretch()

        preview_btn = QPushButton("预览")
        preview_btn.setFixedHeight(30)
        preview_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: 600;
                min-height: 30px;
                max-height: 30px;
            }}
            QPushButton:hover {{
                background-color: {c['surface_1']};
                border-color: {c['border_strong']};
            }}
        """)
        preview_btn.clicked.connect(self._on_preview)
        footer_layout.addWidget(preview_btn)

        generate_btn = QPushButton("生成案卷")
        generate_btn.setFixedHeight(30)
        generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #334155;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
                min-height: 30px;
                max-height: 30px;
            }}
            QPushButton:hover {{
                background-color: #1e293b;
            }}
        """)
        generate_btn.clicked.connect(self._on_generate)
        footer_layout.addWidget(generate_btn)

        layout.addWidget(footer)

        return panel

    def _refresh_ocr_ui_state(self) -> None:
        """刷新主界面的 OCR 状态展示。"""
        status = get_ocr_dependency_status()

        if status.available:
            self._ocr_status_label.setText("OCR 增强能力已就绪，可直接上传证件或判决书。")
            self._ocr_status_label.setStyleSheet("font-size: 12px; color: #15803d;")
            self._ocr_primary_btn.setText("上传文件")
            self._ocr_help_btn.setVisible(False)
            self._ocr_paste_btn.setEnabled(True)
            return

        self._ocr_status_label.setText(
            f"当前不可用：{status.summary}。模板生成、案件管理等核心功能不受影响。"
        )
        self._ocr_status_label.setStyleSheet("font-size: 12px; color: #c2410c;")
        self._ocr_primary_btn.setText("查看说明")
        self._ocr_help_btn.setVisible(True)
        self._ocr_paste_btn.setEnabled(False)

    def _show_ocr_setup_guide(self) -> None:
        """显示 OCR 安装说明。"""
        status = get_ocr_dependency_status()
        QMessageBox.information(
            self,
            "OCR 增强能力说明",
            format_ocr_setup_message(status)
        )

    def _create_preview_panel(self) -> QWidget:
        """创建预览面板"""
        c = COLORS
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {c['surface_1']}; border-left: 1px solid {c['border']};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setStyleSheet(f"border-bottom: 1px solid {c['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)

        title = QLabel("预生成文件夹结构预览")
        title.setStyleSheet(f"font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: {c['text_muted']};")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # 纯预览模式：已移除保存修改按钮
        # 文件夹结构编辑请使用"模板管理"功能

        refresh_btn = QPushButton("🔄")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {c['text_muted']};
                font-size: 11px;
            }}
        """)
        refresh_btn.clicked.connect(self._on_refresh_preview)
        header_layout.addWidget(refresh_btn)
        layout.addWidget(header)

        # 文件夹树预览（纯预览模式，不可编辑）
        self._folder_preview = FolderTreePreview()
        layout.addWidget(self._folder_preview, 1)

        return panel

    def _load_templates(self) -> None:
        """加载模板列表"""
        # 清除现有卡片
        for card in self._template_cards.values():
            card.deleteLater()
        self._template_cards.clear()

        # 获取模板列表
        templates = self._config_manager.get_templates()

        # 获取当前筛选条件
        filter_category = getattr(self, '_current_filter', 'all')
        search_text = getattr(self, '_search_text', '').lower().strip()

        # 过滤模板
        filtered_templates = []
        for template in templates:
            # 类别过滤
            if filter_category != 'all':
                template_cat = template.get('category', '').lower()
                # 民事类别包含 civil 和 civil2
                if filter_category.lower() == 'civil':
                    if template_cat not in ('civil', 'civil2'):
                        continue
                # 仲裁类别包含 arbitration, labor_arbitration, commercial_arbitration
                elif filter_category.lower() == 'arbitration':
                    if template_cat not in ('arbitration', 'labor_arbitration', 'commercial_arbitration'):
                        continue
                elif template_cat != filter_category.lower():
                    continue

            # 搜索过滤
            if search_text:
                name = template.get('name', '').lower()
                desc = template.get('description', '').lower()
                # 支持在名称或描述中搜索
                if search_text not in name and search_text not in desc:
                    continue

            filtered_templates.append(template)

        # 获取置顶模板列表用于排序
        pinned_global = set(self._config_manager.get_pinned_templates())
        
        # 对模板进行排序：置顶模板排前面
        def sort_key(template):
            tid = template.get("id", "")
            cat = template.get("category", "")
            
            # 检查是否全局置顶
            if tid in pinned_global:
                # 全局置顶优先级最高，按置顶顺序排序
                try:
                    pin_index = list(pinned_global).index(tid)
                    return (0, pin_index, template.get("name", ""))
                except ValueError:
                    pass
            
            # 检查是否分类置顶（在分类筛选时）
            if filter_category != 'all':
                cat_pinned = self._config_manager.get_category_pinned(cat)
                if cat_pinned == tid:
                    return (1, 0, template.get("name", ""))
            
            # 普通模板按名称排序
            return (2, 0, template.get("name", ""))
        
        filtered_templates.sort(key=sort_key)

        # 创建卡片
        pinned_global = set(self._config_manager.get_pinned_templates())
        for template in filtered_templates:
            card = TemplateCard(template)
            card.clicked.connect(self._on_template_clicked)
            card.edit_clicked.connect(self._on_edit_template)
            
            # 设置置顶标记
            tid = template.get("id", "")
            cat = template.get("category", "")
            is_pinned = tid in pinned_global
            if not is_pinned and filter_category != 'all':
                is_pinned = self._config_manager.get_category_pinned(cat) == tid
            card.set_pinned(is_pinned)

            self._template_layout.insertWidget(
                self._template_layout.count() - 1,
                card
            )
            self._template_cards[template["id"]] = card

        # 恢复上次选择的模板
        last_template_id = self._config_manager.get("app.last_template_id")
        if last_template_id and last_template_id in self._template_cards:
            self._select_template(last_template_id)
        elif self._template_cards:
            # 选择第一个模板
            first_id = list(self._template_cards.keys())[0]
            self._select_template(first_id)

    def _select_template(self, template_id: str) -> None:
        """选择模板"""
        # 更新选中状态
        for tid, card in self._template_cards.items():
            card.set_selected(tid == template_id)

        self._selected_template_id = template_id

        # 加载变量
        template = self._config_manager.get_template(template_id)
        if template:
            # 更新面包屑
            template_name = template.get("name", "未知模板")
            self._breadcrumb.setText(
                f"<span style='color: {COLORS['text_tertiary']};'>案卷生成</span> / "
                f"<span style='font-weight: 500;'>{template_name}</span>"
            )

            var_defs = template.get("variables", [])
            self._variables_form.set_variables(var_defs)
            self._variables_form.clear_all()

            # 更新预览
            self._preview_update_timer.stop()
            self._update_preview()

            # 更新置顶按钮状态
            self._update_pin_button_state(template)

        # 保存选择
        self._config_manager.set("app.last_template_id", template_id)

    def _on_template_clicked(self, template_id: str) -> None:
        """模板点击事件"""
        self._select_template(template_id)

    def _on_edit_template(self, template_id: str) -> None:
        """编辑模板"""
        self._on_manage_templates(template_id)

    def _on_add_template(self) -> None:
        """新建模板 — 打开电子模板制作器"""
        self._on_template_maker()

    def _on_manage_templates(self, select_id: str = None) -> None:
        """管理模板"""
        dialog = TemplateManagerDialog(self)
        if select_id:
            dialog.select_template(select_id)

        if dialog.exec():
            self._load_templates()

    def _on_template_maker(self) -> None:
        """打开 Word 模板制作器"""
        dialog = TemplateManagerDialog(self, initial_tab="maker")
        dialog.exec()

    def _on_archive(self) -> None:
        """打开电子化归档"""
        # 选择文件夹
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择案卷文件夹",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder_path:
            return

        from src.gui.archive_dialog import ArchiveDialog
        dialog = ArchiveDialog(Path(folder_path), self)
        dialog.exec()

    def _on_case_manager(self) -> None:
        """打开案件管理"""
        from src.gui.case_manager_dialog import CaseManagerDialog
        dialog = CaseManagerDialog(self)
        dialog.exec()

    def open_default_case_manager_home(self) -> None:
        """以案件管理作为默认落地界面。"""
        from src.gui.case_manager_dialog import CaseManagerDialog

        dialog = CaseManagerDialog(self)
        dialog.exec()
        if not self.isVisible():
            app = QApplication.instance()
            self.close()
            if app is not None:
                app.quit()

    def _open_case_manager_for_deadline(self, case_id: str, deadline_id: str) -> None:
        """从期限日历跳转到指定案件的期限编辑。"""
        from src.gui.case_manager_dialog import CaseManagerDialog

        dialog = CaseManagerDialog(
            self,
            initial_case_id=case_id,
            initial_deadline_id=deadline_id,
        )
        dialog.exec()

    def _on_calendar(self) -> None:
        """打开期限日历"""
        self._open_calendar_dialog()

    def _open_calendar_dialog(self, date_text: str = "", *, detail_mode: str = "day") -> None:
        """打开期限日历，并可选定位到指定日期。"""
        from src.gui.calendar_dialog import CalendarDialog
        dialog = CalendarDialog(self)
        if date_text:
            dialog.focus_date_text(date_text, detail_mode=detail_mode)
        pending_navigation: Dict[str, str] = {}
        dialog.navigate_to_deadline_requested.connect(
            lambda case_id, deadline_id: pending_navigation.update({
                "case_id": case_id,
                "deadline_id": deadline_id,
            })
        )
        dialog.exec()
        if pending_navigation:
            self._open_case_manager_for_deadline(
                pending_navigation.get("case_id", ""),
                pending_navigation.get("deadline_id", ""),
            )

    def _on_tool_center(self) -> None:
        """打开工具中心"""
        from src.gui.tool_center_dialog import ToolCenterDialog
        dialog = ToolCenterDialog(self)
        pending_navigation: Dict[str, str] = {}
        dialog.navigate_to_case_requested.connect(
            lambda case_id: pending_navigation.update({
                "target": "case",
                "case_id": case_id,
            })
        )
        dialog.navigate_to_calendar_requested.connect(
            lambda date_text: pending_navigation.update({
                "target": "calendar",
                "date": date_text,
            })
        )
        dialog.exec()
        if pending_navigation.get("target") == "case":
            self._open_case_manager_for_deadline(pending_navigation.get("case_id", ""), "")
        elif pending_navigation.get("target") == "calendar":
            self._open_calendar_dialog(pending_navigation.get("date", ""), detail_mode="all")

    def _on_settings(self) -> None:
        """打开设置"""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _on_about(self) -> None:
        """关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            f"""<h3>{APP_DISPLAY_NAME} · {APP_BRAND_ENGLISH}</h3>
            <p>版本: {get_version()}</p>
            <p>一款以本地文件夹为核心载体的案件管理桌面应用。</p>
            <p>支持案件台账、模板生成、OCR 信息识别、电子归档与工具中心。</p>
            <p style='color:#888;'>开发者：汪立（安徽始信律师事务所）</p>
            <p style='color:#888;'>邮箱：491445490@qq.com</p>
            """
        )

    def _update_filter_btn_style(self, btn: QPushButton, active: bool) -> None:
        """更新筛选按钮样式 - 带淡淡阴影"""
        c = COLORS
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['accent_subtle']};
                    color: {c['accent']};
                    border: 1px solid {c['accent_light']};
                    border-radius: 7px;
                    padding: 0 10px;
                    min-height: 26px;
                    max-height: 26px;
                    font-size: 11px;
                    font-weight: 600;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['surface_0']};
                    color: {c['text_secondary']};
                    border: 1px solid {c['border']};
                    border-radius: 7px;
                    padding: 0 10px;
                    min-height: 26px;
                    max-height: 26px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {c['surface_1']};
                    color: {c['text_primary']};
                    border: 1px solid {c['border_strong']};
                }}
                QPushButton:pressed {{
                    background-color: {c['surface_2']};
                }}
            """)

    def _on_filter_clicked(self, clicked_btn: QPushButton) -> None:
        """分类筛选点击事件"""
        # 更新按钮状态
        for btn in self._filter_buttons:
            btn.setChecked(btn == clicked_btn)
            self._update_filter_btn_style(btn, btn == clicked_btn)

        # 记录当前筛选
        self._current_filter = clicked_btn.property("category")

        # 重新加载模板（应用筛选）
        self._load_templates()

    def _on_search_text_changed(self, text: str) -> None:
        """搜索文本改变事件"""
        self._search_text = text.lower().strip()
        self._load_templates()

    def _on_new_case(self) -> None:
        """顶部工具栏/工作台新建案件：跳转到创建中心。"""
        self._switch_page("documents")

    def _on_new_deadline(self) -> None:
        """工作台新建期限：跳转到日历并打开添加期限对话框。"""
        self._switch_page("calendar")
        if hasattr(self._calendar_page, "_on_add_deadline"):
            self._calendar_page._on_add_deadline("deadline")

    def _on_import_case(self) -> None:
        """工作台导入案件：打开导入对话框，完成后跳转到案件中心。"""
        self._case_center._on_import_folder()
        self._start_file_index_rebuild("导入案件后更新文件索引")
        self._switch_page("cases")

    def _toggle_search_mode(self) -> None:
        """切换顶部搜索模式。"""
        self._search_mode = "file" if self._search_mode == "case" else "case"
        self._top_search.clear()
        self._search_popup.hide()
        self._update_search_mode_ui()
        if self._search_mode != "file":
            return
        try:
            service = self._get_file_search_service()
        except Exception as exc:
            self.statusBar().showMessage(f"文件索引不可用：{exc}", 7000)
            return
        if service.count_entries() == 0:
            self._start_file_index_rebuild("正在建立文件索引")

    def _get_file_search_service(self) -> FileSearchService:
        """懒加载文件搜索服务，避免启动时就访问磁盘索引。"""
        if self._file_search_service is None:
            self._file_search_service = FileSearchService()
        return self._file_search_service

    def _update_search_mode_ui(self) -> None:
        """刷新顶部搜索模式按钮与输入框状态。"""
        c = COLORS
        is_file_mode = self._search_mode == "file"
        self._top_search.setPlaceholderText("搜索文件..." if is_file_mode else "搜索案件...")
        self._search_mode_btn.setText("文件搜索" if is_file_mode else "案件搜索")
        self._search_mode_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['accent_subtle'] if is_file_mode else c['surface_0']};
                color: {c['accent'] if is_file_mode else c['text_secondary']};
                border: 1px solid {c['accent'] if is_file_mode else c['border']};
                border-radius: 12px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['accent_light'] if is_file_mode else c['surface_1']};
                color: {c['accent'] if is_file_mode else c['text_primary']};
                border-color: {c['accent'] if is_file_mode else c['border_strong']};
            }}
        """)

    def _on_open_tools_tab(self, tab_key: str) -> None:
        """工作台快捷操作：跳转到工具中心指定标签页。"""
        self._switch_page("tools")
        tab_index_map = {
            "court_sms": 0,
            "screenshot_merge": 6,
        }
        idx = tab_index_map.get(tab_key)
        if idx is not None and hasattr(self._tool_center_page, "_tabs"):
            self._tool_center_page._tabs.setCurrentIndex(idx)

    def _on_navigate_to_calendar_from_dashboard(self, filter_key: str = "") -> None:
        """工作台跳转日历：切换页面并应用对应风险筛选。"""
        self._switch_page("calendar")
        if filter_key and hasattr(self._calendar_page, "_apply_risk_filter"):
            self._calendar_page._apply_risk_filter(filter_key)

    def _on_navigate_to_calendar_from_tool(self, date_text: str = "") -> None:
        """工具中心跳转日历：切换页面并尝试定位到指定日期。"""
        self._switch_page("calendar")
        if date_text and hasattr(self._calendar_page, "focus_date_text"):
            self._calendar_page.focus_date_text(date_text)

    def _on_open_ocr(self) -> None:
        """工作台 OCR 识别：跳转到创建中心并打开信息识别对话框。"""
        self._switch_page("documents")
        self._on_info_extraction()

    def _on_directory_abnormal(self) -> None:
        """工作台目录异常：跳转到案件中心并筛选目录缺失案件。"""
        self._case_center.set_filter(directory_value="missing")
        self._switch_page("cases")

    def _on_top_search_text_changed(self, text: str) -> None:
        """顶部搜索框输入时刷新即时结果。"""
        text = text.strip()
        if not text:
            self._search_case_map = {}
            self._search_popup_items = []
            if hasattr(self, "_search_popup"):
                self._search_popup.hide()
            return
        self._search_update_timer.start()

    def _on_search_case_selected(self, name: str) -> None:
        """从补全列表中选择案件后跳转到案件中心并选中。"""
        case_id = self._search_case_map.get(name)
        if not case_id:
            return
        self._open_case_search_result(case_id)

    def _open_case_search_result(self, case_id: str) -> None:
        """打开案件搜索结果。"""
        self._case_center._sync_navigation_filter_state()
        self._case_center._selected_case_ids = {case_id}
        self._case_center._load_cases()
        self._switch_page("cases")
        self._top_search.clear()
        if hasattr(self, "_search_popup"):
            self._search_popup.hide()

    def _refresh_search_popup(self) -> None:
        """刷新顶部即时搜索结果面板。"""
        if not hasattr(self, "_search_popup") or not self._top_bar.isVisible():
            return
        text = self._top_search.text().strip()
        if not text:
            self._search_popup.hide()
            return

        if self._search_mode == "file":
            self._populate_file_search_results(text)
        else:
            self._populate_case_search_results(text)

    def _populate_case_search_results(self, text: str) -> None:
        """填充案件搜索即时结果。"""
        cases = get_case_manager().search_cases(text)[:40]
        self._search_popup_items = []
        self._search_table.setRowCount(0)
        self._search_table.setHorizontalHeaderLabels(["案件名称", "分类", "路径/标签"])

        for case in cases:
            case_id = str(case.get("id", "")).strip()
            name = str(case.get("name", "")).strip() or "未命名案件"
            if not case_id:
                continue
            tags = " ".join(str(tag) for tag in case.get("tags", [])[:3])
            path_text = str(case.get("path", "")).strip()
            location = tags or (Path(path_text).name if path_text else "未关联目录")
            category = str(case.get("category", "")).strip() or "案件"
            self._add_search_popup_row(
                name,
                category,
                location,
                {"type": "case", "case_id": case_id},
            )

        if not self._search_popup_items:
            self._add_search_info_row("没有匹配案件", "案件搜索", "换个关键词试试")

        self._show_search_popup(f"案件搜索结果：{len(cases)} 项")

    def _populate_file_search_results(self, text: str) -> None:
        """填充文件搜索即时结果。"""
        self._search_popup_items = []
        self._search_table.setRowCount(0)
        self._search_table.setHorizontalHeaderLabels(["文件名", "案件", "相对路径"])

        try:
            service = self._get_file_search_service()
        except Exception as exc:
            self._add_search_info_row("文件索引不可用", "文件搜索", str(exc))
            self._show_search_popup("文件搜索")
            return

        if service.count_entries() == 0:
            self._start_file_index_rebuild("正在建立文件索引")
            self._add_search_info_row("正在建立文件索引", "文件搜索", "完成后会显示文件结果")
            self._show_search_popup("文件搜索索引建立中")
            return

        results = service.search(text, limit=80)
        for result in results:
            self._add_search_popup_row(
                result.filename,
                result.case_name,
                result.relative_path,
                {"type": "file", "path": result.absolute_path},
            )

        if not self._search_popup_items:
            self._add_search_info_row("没有匹配文件", "文件搜索", "可在设置中重建文件索引")

        self._show_search_popup(f"文件搜索结果：{len(results)} 项")

    def _add_search_info_row(self, name: str, middle: str, detail: str) -> None:
        """添加不可执行的信息行。"""
        self._add_search_popup_row(name, middle, detail, {"type": "info"})

    def _add_search_popup_row(
        self,
        name: str,
        middle: str,
        detail: str,
        payload: Dict[str, Any],
    ) -> None:
        """向即时搜索表格添加一行。"""
        row = self._search_table.rowCount()
        self._search_table.insertRow(row)
        self._search_popup_items.append(payload)

        for column, value in enumerate((name, middle, detail)):
            item = QTableWidgetItem(str(value))
            item.setData(Qt.ItemDataRole.UserRole, row)
            if payload.get("type") == "info":
                item.setForeground(QColor(COLORS["text_tertiary"]))
            self._search_table.setItem(row, column, item)

        self._search_table.setRowHeight(row, 30)

    def _show_search_popup(self, title: str) -> None:
        """定位并显示即时搜索面板。"""
        if not self._search_popup_items:
            self._search_popup.hide()
            return

        self._search_popup_title.setText(title)
        row_height = 30
        header_height = 28
        chrome_height = 42
        available_height = max(220, int(self.height() * 0.5))
        max_visible_rows = max(5, (available_height - header_height - chrome_height) // row_height)
        visible_rows = min(max(self._search_table.rowCount(), 2), max_visible_rows)
        table_height = header_height + visible_rows * row_height
        popup_height = min(available_height, table_height + chrome_height)
        pos = self._top_search.mapTo(self, QPoint(0, self._top_search.height() + 6))
        right_limit = max(640, self.width() - 24)
        popup_width = min(920, max(680, right_limit - pos.x()))
        self._search_popup.setGeometry(pos.x(), pos.y(), popup_width, popup_height)
        content_width = max(560, popup_width - 22)
        if self._search_mode == "file":
            first_width = int(content_width * 0.32)
            second_width = int(content_width * 0.25)
        else:
            first_width = int(content_width * 0.46)
            second_width = int(content_width * 0.18)
        third_width = max(160, content_width - first_width - second_width)
        self._search_table.setColumnWidth(0, first_width)
        self._search_table.setColumnWidth(1, second_width)
        self._search_table.setColumnWidth(2, third_width)
        self._search_table.setMinimumHeight(table_height)
        self._search_table.setMaximumHeight(table_height)
        self._search_popup.raise_()
        self._search_popup.show()
        self._search_table.setCurrentCell(0, 0)

    def _activate_search_popup_selection(self) -> None:
        """执行当前选中的即时搜索结果。"""
        if not hasattr(self, "_search_table") or not self._search_popup.isVisible():
            return
        row = self._search_table.currentRow()
        if row < 0 or row >= len(self._search_popup_items):
            return
        payload = self._search_popup_items[row]
        kind = payload.get("type")
        if kind == "case":
            self._open_case_search_result(str(payload.get("case_id", "")))
            return
        if kind == "file":
            path = Path(str(payload.get("path", "")))
            ok, error = open_path(path)
            if not ok:
                QMessageBox.warning(self, "打开失败", error or "无法打开文件")
            self._search_popup.hide()

    def _on_open_case_deadline(self, case_id: str, deadline_id: str) -> None:
        """工作台点击待办事项：关联案件跳转到案件中心期限签页，未关联案件跳转到日历。"""
        if not case_id:
            # 未关联案件，跳转到日历界面
            self._switch_page("calendar")
            return
        self._case_center.open_case_deadline_tab(case_id, deadline_id)
        self._switch_page("cases")

    def _on_filter_by_status(self, status: str) -> None:
        """工作台环形图点击：按状态筛选案件。"""
        self._case_center.set_filter(status_value=status)
        self._switch_page("cases")

    def _on_filter_by_category(self, category: str) -> None:
        """工作台条形图点击：按分类筛选案件。"""
        self._case_center.set_filter(filter_value=category)
        self._switch_page("cases")

    def _on_global_search(self) -> None:
        """全局搜索框回车：按当前模式搜索案件或文件。"""
        text = self._top_search.text().strip()
        if hasattr(self, "_search_popup") and self._search_popup.isVisible():
            self._activate_search_popup_selection()
            return
        if text:
            if self._search_mode == "file":
                self._refresh_search_popup()
                return
            self._case_center.apply_search(text)
            self._switch_page("cases")
            self._top_search.clear()

    def _start_file_index_rebuild(self, status_message: str = "正在更新文件索引") -> None:
        """后台重建文件级索引。"""
        if self._file_index_thread and self._file_index_thread.isRunning():
            self._file_index_pending = True
            return

        cases = [dict(case) for case in get_case_manager().get_all_cases()]
        if not cases:
            return

        self.statusBar().showMessage(status_message)
        self._file_index_thread = QThread(self)
        self._file_index_worker = _FileIndexWorker(cases)
        self._file_index_worker.moveToThread(self._file_index_thread)
        self._file_index_thread.started.connect(self._file_index_worker.run)
        self._file_index_worker.finished.connect(self._on_file_index_finished)
        self._file_index_worker.failed.connect(self._on_file_index_failed)
        self._file_index_worker.finished.connect(self._file_index_thread.quit)
        self._file_index_worker.failed.connect(self._file_index_thread.quit)
        self._file_index_thread.finished.connect(self._file_index_worker.deleteLater)
        self._file_index_thread.finished.connect(self._on_file_index_thread_finished)
        self._file_index_thread.start()

    def _on_file_index_finished(self, summary: Any) -> None:
        """文件索引后台刷新完成。"""
        self.statusBar().showMessage(
            f"文件索引已更新：{summary.cases_indexed} 个案件，{summary.files_indexed} 个文件",
            5000,
        )
        if self._search_mode == "file" and self._top_search.text().strip():
            self._refresh_search_popup()

    def _on_file_index_failed(self, error: str) -> None:
        """文件索引后台刷新失败。"""
        self.statusBar().showMessage(f"文件索引更新失败：{error}", 7000)

    def _on_file_index_thread_finished(self) -> None:
        """清理索引线程。"""
        self._file_index_thread = None
        self._file_index_worker = None
        if self._file_index_pending:
            self._file_index_pending = False
            QTimer.singleShot(300, lambda: self._start_file_index_rebuild("继续更新文件索引"))

    def _on_clear_values(self) -> None:
        """清空变量值"""
        self._variables_form.clear_all()
        self._preview_update_timer.stop()
        self._update_preview()

    def _on_values_changed(self, values: Dict[str, Any]) -> None:
        """变量值改变"""
        self._schedule_preview_update()

    def _schedule_preview_update(self) -> None:
        """输入时延迟刷新预览，避免每个字符都重建树。"""
        if not self._selected_template_id:
            return
        self._preview_update_timer.start()

    def _on_preview(self) -> None:
        """预览"""
        self._preview_update_timer.stop()
        self._update_preview()

    def _update_preview(self) -> None:
        """更新预览"""
        if not self._selected_template_id:
            return

        template = self._config_manager.get_template(self._selected_template_id)
        if not template:
            return

        structure = template.get("folder_structure", {})
        values = self._variables_form.get_values()

        self._folder_preview.set_structure(structure, values)

    def _on_refresh_preview(self) -> None:
        """刷新预览（放弃修改，重新加载）"""
        self._update_preview()
        self._status_bar.showMessage("预览已刷新")

    def _on_generate(self) -> None:
        """生成案卷"""
        if not self._selected_template_id:
            QMessageBox.warning(self, "警告", "请先选择模板")
            return

        # 验证变量
        is_valid, errors = self._variables_form.validate()
        if not is_valid:
            QMessageBox.warning(
                self,
                "验证失败",
                "以下字段存在问题:\n\n" + "\n".join(errors)
            )
            return

        # 获取当前模板
        template = self._config_manager.get_template(self._selected_template_id)
        values = self._variables_form.get_values()
        
        # 纯预览模式：不再检查未保存的修改
        # 文件夹结构编辑请使用"模板管理"功能
        
        # 打开生成对话框
        dialog = GenerationDialog(template, values, self)
        dialog.exec()

    def _on_info_extraction(self) -> None:
        """打开信息识别对话框"""
        if not get_ocr_dependency_status().available:
            self._show_ocr_setup_guide()
            return

        # 获取当前模板的变量定义
        template_vars = []
        if self._selected_template_id:
            template = self._config_manager.get_template(self._selected_template_id)
            if template:
                template_vars = template.get("variables", [])

        try:
            from src.gui.info_extraction_dialog import InfoExtractionDialog
        except Exception as e:
            self._logger.error(f"加载信息识别模块失败: {e}")
            QMessageBox.warning(
                self,
                "信息识别不可用",
                f"当前环境无法加载 OCR/信息识别模块：\n{e}"
            )
            return

        # 打开信息识别对话框
        dialog = InfoExtractionDialog(template_vars, template_id=self._selected_template_id, parent=self)
        dialog.data_applied.connect(self._on_extraction_data_applied)
        dialog.exec()

    def _on_extraction_data_applied(self, data: dict) -> None:
        """
        处理从信息识别应用的数据
        
        Args:
            data: {变量key: 值} 的字典，可能包含当前模板中没有的新变量
        """
        if not data:
            return
        
        if not self._selected_template_id:
            return
        
        # 获取当前模板
        template = self._config_manager.get_template(self._selected_template_id)
        if not template:
            return
        
        # 分离已有变量和新变量
        existing_values = {}
        new_vars_to_add = []
        
        for var_key, value in data.items():
            if self._variables_form.has_variable(var_key):
                # 表单中已存在该变量
                existing_values[var_key] = value
            else:
                # 新变量，需要添加到表单和模板
                label = self._get_field_label(var_key)
                new_var = {
                    'key': var_key,
                    'label': label,
                    'type': 'text',
                    'required': False
                }
                new_vars_to_add.append(new_var)
        
        # 如果有新变量，动态添加到表单和模板
        if new_vars_to_add:
            for new_var in new_vars_to_add:
                # 添加到表单
                self._variables_form.add_variable(new_var)
            # 添加到模板配置
            self._add_variables_to_template(new_vars_to_add)
        
        # 填充所有值（包括新变量的值）
        self._variables_form.set_values(data)
        
        # 更新预览
        self._update_preview()
        
        # 显示提示
        total_count = len(data)
        new_count = len(new_vars_to_add)
        
        msg = f"已从识别结果自动填充 {total_count} 个字段"
        if new_count > 0:
            msg += f"（其中 {new_count} 个为新创建变量）"
        self._status_bar.showMessage(msg, 5000)
    
    def _get_field_label(self, var_key: str) -> str:
        """
        根据变量 key 获取显示标签
        
        Args:
            var_key: 变量 key
            
        Returns:
            显示标签
        """
        # 常见字段映射
        label_mapping = {
            'name': '姓名',
            'gender': '性别',
            'ethnicity': '民族',
            'birth_date': '出生日期',
            'address': '住址',
            'id_number': '身份证号',
            'issuer': '签发机关',
            'validity_period': '有效期限',
            'client_name': '委托人姓名',
            'client_gender': '委托人性别',
            'client_ethnicity': '委托人民族',
            'client_birth_date': '委托人出生日期',
            'client_address': '委托人住址',
            'client_id_number': '委托人身份证号',
            'case_number': '案号',
            'case_type': '案件类型',
            'court_name': '受理法院',
        }
        
        # 检查是否为对方当事人变量（以 opponent_ 开头）
        if var_key.startswith('opponent_'):
            # 去除前缀获取基础变量名
            base_key = var_key[9:]  # len('opponent_') == 9
            
            # 特殊处理：client_name 对方当事人显示为"对方姓名(名称)"
            if base_key == 'client_name':
                return "对方姓名(名称)"
            
            base_label = label_mapping.get(base_key, base_key)
            return f"对方{base_label}"
        
        return label_mapping.get(var_key, var_key)
    
    def _add_variables_to_template(self, new_vars: list) -> bool:
        """
        向当前模板添加新变量
        
        Args:
            new_vars: 新变量定义列表
            
        Returns:
            是否成功
        """
        if not self._selected_template_id or not new_vars:
            return False
        
        try:
            template = self._config_manager.get_template(self._selected_template_id)
            if not template:
                return False
            
            # 获取现有变量
            variables = template.get('variables', [])
            
            # 添加新变量
            for new_var in new_vars:
                # 检查是否已存在
                if not any(var['key'] == new_var['key'] for var in variables):
                    variables.append(new_var)
            
            # 更新模板
            template['variables'] = variables
            self._config_manager.update_template(self._selected_template_id, template)
            
            self._logger.info(f"已向模板 {self._selected_template_id} 添加 {len(new_vars)} 个新变量")
            return True
            
        except Exception as e:
            self._logger.error(f"添加新变量失败: {e}")
            return False

    def _update_pin_button_state(self, template: dict) -> None:
        """更新置顶按钮状态
        
        Args:
            template: 当前选中的模板
        """
        template_id = template.get("id", "")
        category = template.get("category", "")
        
        # 显示置顶按钮
        self._pin_btn.setVisible(True)
        
        # 检查是否已置顶
        is_global_pinned = template_id in self._config_manager.get_pinned_templates()
        is_category_pinned = self._config_manager.get_category_pinned(category) == template_id
        
        # 设置按钮状态
        is_pinned = is_global_pinned or is_category_pinned
        self._pin_btn.setChecked(is_pinned)
        
        # 更新按钮文本
        if is_pinned:
            self._pin_btn.setText("📌 已置顶")
        else:
            self._pin_btn.setText("📌 置顶")
        
        # 更新提示文本
        pinned_count = len(self._config_manager.get_pinned_templates())
        if is_pinned:
            tooltip = "已置顶"
            if is_global_pinned:
                tooltip += f"（全局 {pinned_count}/3）"
            if is_category_pinned:
                tooltip += f"（{self._get_category_display_name(category)}分类）"
            tooltip += "，点击取消置顶"
        else:
            tooltip = f"置顶此模板（全局 {pinned_count}/3，分类最多1个）"
        self._pin_btn.setToolTip(tooltip)

    def _get_category_display_name(self, category: str) -> str:
        """获取分类显示名称"""
        return CATEGORY_NAMES.get(category, category)

    def _on_pin_button_clicked(self, is_pinned: bool) -> None:
        """置顶按钮点击事件
        
        Args:
            is_pinned: 点击后是否处于置顶状态（True=将要置顶）
        """
        if not self._selected_template_id:
            return
        
        template = self._config_manager.get_template(self._selected_template_id)
        if not template:
            return
        
        template_id = template.get("id", "")
        category = template.get("category", "")
        
        if is_pinned:
            # 要置顶
            # 先尝试全局置顶
            success = self._config_manager.pin_template_global(template_id)
            if not success:
                # 全局已满，尝试分类置顶
                self._config_manager.pin_template_in_category(template_id, category)
        else:
            # 要取消置顶
            self._config_manager.unpin_template_global(template_id)
            self._config_manager.unpin_template_in_category(category)
        
        # 刷新模板列表以反映排序变化
        self._load_templates()
        
        # 恢复选中状态
        self._select_template(template_id)

    def _restore_geometry(self) -> None:
        """恢复窗口几何信息"""
        width = self._config_manager.get("ui.window_width", APP_SURFACE_DEFAULT_SIZE[0])
        height = self._config_manager.get("ui.window_height", APP_SURFACE_DEFAULT_SIZE[1])
        width = max(APP_SURFACE_MIN_SIZE[0], min(int(width), APP_SURFACE_DEFAULT_SIZE[0]))
        height = max(APP_SURFACE_MIN_SIZE[1], min(int(height), APP_SURFACE_DEFAULT_SIZE[1]))
        self.resize(width, height)

    def closeEvent(self, event) -> None:
        """关闭事件"""
        if hasattr(self, "_calendar_page") and hasattr(self._calendar_page, "perform_auto_export_on_close"):
            try:
                self._calendar_page.perform_auto_export_on_close(silent=True)
            except Exception as exc:
                self._logger.warning(f"关闭时自动导出期限事项失败: {exc}")

        # 保存窗口几何信息
        self._config_manager.set("ui.window_width", self.width())
        self._config_manager.set("ui.window_height", self.height())

        event.accept()
