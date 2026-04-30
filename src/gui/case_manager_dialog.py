# -*- coding: utf-8 -*-
"""案件管理对话框"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QTimer, QObject, QThread
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.core.case_manager import (
    FOLDER_STATUS_AVAILABLE,
    FOLDER_STATUS_MISSING,
    FOLDER_STATUS_UNLINKED,
    get_case_manager,
)
from src.gui.archive_dialog import ArchiveDialog
from src.gui.calendar_dialog import CalendarDialog
from src.gui.case_aux_dialogs import TagEditorDialog, normalize_tags
from src.gui.tool_center_dialog import ToolCenterDialog
from src.gui.case_detail_panel import CaseDetailPanel
from src.gui.styles import APP_COLORS as COLORS
from src.gui.window_metrics import APP_SURFACE_DEFAULT_SIZE, APP_SURFACE_MIN_SIZE
from src.gui.widgets.case_card import CaseCard
from src.utils.logger import get_logger
from src.utils.platform_utils import open_path


FILTER_OPTIONS = [
    ("全部", "all"),
    ("未分类", ""),
    ("民事", "civil"),
    ("刑事", "criminal"),
    ("行政", "administrative"),
    ("非诉", "non_litigation"),
    ("劳动仲裁", "labor_arbitration"),
    ("商事仲裁", "commercial_arbitration"),
]

STATUS_OPTIONS = [
    ("全部", "all"),
    ("推进中", "active"),
    ("未完结", "pending"),
    ("待归档", "closed"),
]

DIRECTORY_OPTIONS = [
    ("全部目录", "all"),
    ("目录正常", FOLDER_STATUS_AVAILABLE),
    ("目录缺失", FOLDER_STATUS_MISSING),
    ("未关联", FOLDER_STATUS_UNLINKED),
]

STATUS_GROUPS = [
    ("推进中", "active"),
    ("未完结", "pending"),
    ("待归档", "closed"),
]

SORT_MODES = [
    ("updated_desc", "修改时间 ↓", "修改时间 新→旧"),
    ("updated_asc", "修改时间 ↑", "修改时间 旧→新"),
    ("created_desc", "导入时间 ↓", "导入时间 新→旧"),
    ("created_asc", "导入时间 ↑", "导入时间 旧→新"),
    ("name_asc", "标题 A-Z", "标题 A→Z"),
    ("name_desc", "标题 Z-A", "标题 Z→A"),
]


class _CaseOperationWorker(QObject):
    """后台执行案件文件操作。"""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, operation):
        super().__init__()
        self._operation = operation

    def run(self) -> None:
        try:
            self.finished.emit(self._operation())
        except Exception as exc:
            self.failed.emit(str(exc))

DEFAULT_TAG_SUGGESTIONS = [
    "紧急",
    "开庭",
    "立案",
    "合同",
    "劳动",
    "仲裁",
    "证据",
    "保全",
    "执行",
    "待立案",
    "待开庭",
    "待判决",
    "待保全",
    "待执行",
    "待缴费",
]


class CaseSidebarDropPanel(QFrame):
    """左侧整栏拖拽导入区域。"""

    paths_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._set_drag_active(False)

    def _set_drag_active(self, active: bool) -> None:
        c = COLORS
        if active:
            self.setStyleSheet(f"""
                CaseSidebarDropPanel {{
                    background: {c['accent_subtle']};
                    border-right: 1px solid {c['border']};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                CaseSidebarDropPanel {{
                    background: {c['surface_1']};
                    border-right: 1px solid {c['border']};
                }}
            """)

    def dragEnterEvent(self, event) -> None:
        paths = self._extract_folder_paths(event.mimeData().urls())
        if paths:
            self._set_drag_active(True)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        paths = self._extract_folder_paths(event.mimeData().urls())
        if paths:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        self._set_drag_active(False)
        paths = self._extract_folder_paths(event.mimeData().urls())
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
            return
        event.ignore()

    def _extract_folder_paths(self, urls) -> List[str]:
        folders = []
        seen = set()
        for url in urls:
            local_path = url.toLocalFile()
            if not local_path:
                continue
            path = Path(local_path)
            if not path.exists() or not path.is_dir():
                continue
            normalized = str(path.resolve())
            if normalized in seen:
                continue
            seen.add(normalized)
            folders.append(str(path))
        return folders


class CaseImportDropFrame(QFrame):
    """案件导入拖拽区。"""

    paths_dropped = Signal(list)
    new_case_clicked = Signal()
    import_clicked = Signal()
    batch_scan_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()
        self._set_drag_active(False)

    def _setup_ui(self) -> None:
        c = COLORS
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(8)

        self._new_case_btn = QPushButton("新建案件")
        self._new_case_btn.setFixedHeight(34)
        self._new_case_btn.clicked.connect(self.new_case_clicked.emit)
        self._new_case_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
            }}
        """)
        layout.addWidget(self._new_case_btn, 1)

        self._import_btn = QPushButton("导入案件")
        self._import_btn.setFixedHeight(34)
        self._import_btn.clicked.connect(self.import_clicked.emit)
        self._import_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['accent']};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['accent_hover']};
            }}
        """)
        layout.addWidget(self._import_btn, 1)

        self._batch_btn = QPushButton("案件扫描")
        self._batch_btn.setFixedHeight(34)
        self._batch_btn.clicked.connect(self.batch_scan_clicked.emit)
        self._batch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
            }}
        """)
        layout.addWidget(self._batch_btn, 1)

    def _set_drag_active(self, active: bool) -> None:
        c = COLORS
        if active:
            self.setStyleSheet(f"""
                CaseImportDropFrame {{
                    background: {c['accent_subtle']};
                    border: 1px dashed {c['accent']};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                CaseImportDropFrame {{
                    background: {c['surface_0']};
                    border: 1px dashed {c['border']};
                    border-radius: 10px;
                }}
            """)

    def dragEnterEvent(self, event) -> None:
        paths = self._extract_folder_paths(event.mimeData().urls())
        if paths:
            self._set_drag_active(True)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        paths = self._extract_folder_paths(event.mimeData().urls())
        if paths:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        self._set_drag_active(False)
        paths = self._extract_folder_paths(event.mimeData().urls())
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
            return
        event.ignore()

    def _extract_folder_paths(self, urls) -> List[str]:
        folders = []
        seen = set()
        for url in urls:
            local_path = url.toLocalFile()
            if not local_path:
                continue
            path = Path(local_path)
            if not path.exists() or not path.is_dir():
                continue
            normalized = str(path.resolve())
            if normalized in seen:
                continue
            seen.add(normalized)
            folders.append(str(path))
        return folders


class CaseManagerDialog(QDialog):
    """案件管理对话框"""

    def __init__(
        self,
        parent=None,
        initial_case_id: str = "",
        initial_deadline_id: str = "",
        embed_mode: bool = False,
    ):
        super().__init__(parent)
        self._embed_mode = embed_mode
        if embed_mode:
            self.setWindowFlags(Qt.Widget)
        self._logger = get_logger()
        self._cm = get_case_manager()
        self._current_filter = "all"
        self._current_status = "all"
        self._current_directory = "all"
        self._selected_tag = ""
        self._search_text = ""
        self._current_sort_mode = "updated_desc"
        self._filters_collapsed = True
        self._sidebar_collapsed = False
        self._sidebar_expanded_width = 282
        self._selected_case_ids: set = set()
        self._initial_case_id = initial_case_id.strip()
        self._initial_deadline_id = initial_deadline_id.strip()
        self._case_cards: Dict[str, CaseCard] = {}
        self._tag_buttons: Dict[str, QPushButton] = {}
        self._case_id_order: List[str] = []
        self._case_task_thread: Optional[QThread] = None
        self._case_task_worker: Optional[_CaseOperationWorker] = None
        self._case_task_dialog: Optional[QProgressDialog] = None
        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(200)
        self._search_debounce_timer.timeout.connect(self._do_search)
        self._setup_ui()
        self._load_cases()
        if self._initial_case_id or self._initial_deadline_id:
            QTimer.singleShot(0, self._apply_initial_navigation)

    def _run_case_operation_async(
        self,
        title: str,
        message: str,
        operation,
        on_success,
    ) -> None:
        """在后台执行案件文件操作，并统一处理进度和失败说明。"""
        if self._case_task_thread is not None and self._case_task_thread.isRunning():
            QMessageBox.information(self, "任务进行中", "已有案件文件任务正在进行，请稍后再试。")
            return

        worker = _CaseOperationWorker(operation)
        thread = QThread(self)
        worker.moveToThread(thread)

        progress = QProgressDialog(message, "后台继续", 0, 0, self)
        progress.setWindowTitle(title)
        progress.setMinimumDuration(250)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.canceled.connect(
            lambda: self._logger.info("用户隐藏了案件文件操作进度窗口，任务仍在后台继续。")
        )

        def _success(result) -> None:
            if self._case_task_dialog is not None:
                self._case_task_dialog.close()
            on_success(result)

        def _failed(error_message: str) -> None:
            if self._case_task_dialog is not None:
                self._case_task_dialog.close()
            QMessageBox.warning(
                self,
                f"{title}失败",
                f"{error_message}\n\n软件会尽量保留或回滚案件记录；如真实文件夹状态不确定，请刷新案件列表后核对。",
            )

        worker.finished.connect(_success)
        worker.failed.connect(_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_case_operation)

        self._case_task_worker = worker
        self._case_task_thread = thread
        self._case_task_dialog = progress
        progress.show()
        thread.start()

    def _clear_case_operation(self) -> None:
        self._case_task_worker = None
        self._case_task_thread = None
        self._case_task_dialog = None

    def _setup_ui(self) -> None:
        c = COLORS
        if not self._embed_mode:
            self.setWindowTitle("案件管理")
            self.setMinimumSize(*APP_SURFACE_MIN_SIZE)
            self.resize(*APP_SURFACE_DEFAULT_SIZE)
        self.setStyleSheet(f"QDialog {{ background: {c['surface_0']}; }}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(True)
        self._splitter.setHandleWidth(8)
        self._splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: transparent;
            }}
        """)
        self._splitter.splitterMoved.connect(self._on_splitter_moved)

        self._list_panel = self._create_list_panel()
        self._list_panel.setMinimumWidth(0)
        self._splitter.addWidget(self._list_panel)

        self._detail_panel = CaseDetailPanel()
        self._detail_panel.open_folder_requested.connect(self._on_open_folder)
        self._detail_panel.open_file_requested.connect(self._on_open_file)
        self._detail_panel.edit_tags_requested.connect(self._on_edit_tags)
        self._detail_panel.archive_requested.connect(self._on_archive_case)
        self._detail_panel.relink_folder_requested.connect(self._on_relink_folder)
        self._detail_panel.case_refreshed.connect(self._on_detail_case_refreshed)
        self._detail_panel.preview_fullscreen_toggled.connect(self._on_preview_fullscreen_toggled)
        self._detail_panel.view_calendar_requested.connect(self._on_view_calendar)
        self._detail_panel.tool_center_requested.connect(self._on_tool_center)
        self._splitter.addWidget(self._detail_panel)
        self._splitter.setCollapsible(0, True)

        self._splitter.setSizes([self._sidebar_expanded_width, 998])
        self._setup_sidebar_toggle()

        # 主页面栈：支持案件管理与功能页面内嵌切换
        self._case_page = QWidget()
        case_page_layout = QVBoxLayout(self._case_page)
        case_page_layout.setContentsMargins(0, 0, 0, 0)
        case_page_layout.setSpacing(0)
        case_page_layout.addWidget(self._splitter, 1)

        self._main_stack = QStackedWidget()
        self._main_stack.addWidget(self._case_page)
        main_layout.addWidget(self._main_stack, 1)

        self._status_bar = QLabel("")
        self._status_bar.setFixedHeight(30)
        self._status_bar.setStyleSheet(f"""
            QLabel {{
                background: {c['surface_1']};
                color: {c['text_muted']};
                border-top: 1px solid {c['border']};
                padding-left: 16px;
                font-size: 11px;
            }}
        """)
        main_layout.addWidget(self._status_bar)

    def _setup_sidebar_toggle(self) -> None:
        """在分隔条上放置侧栏折叠按钮。"""
        c = COLORS
        handle = self._splitter.handle(1)
        handle_layout = QVBoxLayout(handle)
        handle_layout.setContentsMargins(0, 14, 0, 0)
        handle_layout.setSpacing(0)

        self._btn_toggle_sidebar = QToolButton(handle)
        self._btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_toggle_sidebar.setAutoRaise(True)
        self._btn_toggle_sidebar.setFixedSize(12, 54)
        self._btn_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        self._btn_toggle_sidebar.setStyleSheet(f"""
            QToolButton {{
                background: {c['surface_0']};
                color: {c['text_muted']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
                padding: 0;
            }}
            QToolButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """)
        handle_layout.addWidget(self._btn_toggle_sidebar, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        handle_layout.addStretch()
        self._update_sidebar_toggle_button()

    def _on_preview_fullscreen_toggled(self, is_fullscreen: bool) -> None:
        """响应文件预览全屏信号：折叠或展开左侧案件栏。"""
        if is_fullscreen:
            if not self._sidebar_collapsed:
                self._toggle_sidebar()
        else:
            if self._sidebar_collapsed:
                self._toggle_sidebar()

    def _update_sidebar_toggle_button(self) -> None:
        if not hasattr(self, "_btn_toggle_sidebar"):
            return
        self._btn_toggle_sidebar.setText("›" if self._sidebar_collapsed else "‹")
        self._btn_toggle_sidebar.setToolTip("展开左侧案件列表" if self._sidebar_collapsed else "收起左侧案件列表")

    def _toggle_sidebar(self) -> None:
        """折叠或展开左侧案件栏。"""
        sizes = self._splitter.sizes()
        total = max(1, sum(sizes))
        if self._sidebar_collapsed:
            left_width = max(self._sidebar_expanded_width, 260)
            self._splitter.setSizes([left_width, max(1, total - left_width)])
            self._sidebar_collapsed = False
        else:
            if sizes and sizes[0] > 40:
                self._sidebar_expanded_width = sizes[0]
            self._splitter.setSizes([0, total])
            self._sidebar_collapsed = True
        self._update_sidebar_toggle_button()

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """同步记录侧栏宽度和折叠状态。"""
        del pos, index
        sizes = self._splitter.sizes()
        if not sizes:
            return
        left_width = sizes[0]
        if left_width > 40:
            self._sidebar_expanded_width = left_width
        collapsed = left_width < 20
        if collapsed != self._sidebar_collapsed:
            self._sidebar_collapsed = collapsed
            self._update_sidebar_toggle_button()

    def _create_separator(self) -> QFrame:
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(f"background: {COLORS['border']}; max-height: 20px;")
        return separator

    def _create_filter_separator(self) -> QFrame:
        """筛选面板分组之间的水平细线分隔。"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLORS['border']}; margin: 2px 8px;")
        return line

    def _create_filter_buttons(self, layout, options, handler, property_name: str) -> List[QPushButton]:
        buttons = []
        for label, value in options:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(value == "all")
            btn.setProperty(property_name, value)
            btn.clicked.connect(lambda checked=False, b=btn: handler(b))
            self._update_filter_style(btn, value == "all")
            layout.addWidget(btn)
            buttons.append(btn)
        return buttons

    def _create_wrapped_filter_buttons(
        self,
        parent_layout: QVBoxLayout,
        options,
        handler,
        property_name: str,
        row_sizes: List[int],
    ) -> List[QPushButton]:
        buttons: List[QPushButton] = []
        start = 0
        for size in row_sizes:
            if start >= len(options):
                break
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            current_options = options[start:start + size]
            buttons.extend(self._create_filter_buttons(row_layout, current_options, handler, property_name))
            row_layout.addStretch()
            parent_layout.addWidget(row)
            start += size
        if start < len(options):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            buttons.extend(self._create_filter_buttons(row_layout, options[start:], handler, property_name))
            row_layout.addStretch()
            parent_layout.addWidget(row)
        return buttons

    def _create_import_button(self) -> QToolButton:
        c = COLORS
        button = QToolButton()
        button.setText("导入案件")
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(f"""
            QToolButton {{
                background: {c['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QToolButton:hover {{
                background: {c['accent_hover']};
            }}
            QToolButton::menu-indicator {{
                image: none;
                width: 0;
            }}
        """)

        menu = QMenu(button)
        menu.addAction("导入单个案件文件夹", self._on_import_folder)
        menu.addAction("批量扫描上级目录", self._on_import_batch_scan)
        button.setMenu(menu)
        return button

    def _create_search_filter_panel(self) -> QFrame:
        c = COLORS
        panel = QFrame()
        panel.setObjectName("searchFilterPanel")
        panel.setStyleSheet(f"""
            QFrame#searchFilterPanel {{
                background: {c['surface_0']};
                border: 1px solid rgba(226, 232, 240, 0.88);
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel("搜索与筛选")
        title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
            font-weight: 700;
        """)
        header.addWidget(title)
        header.addStretch()

        self._btn_toggle_filters = QPushButton("")
        self._btn_toggle_filters.clicked.connect(self._toggle_filter_panel)
        self._btn_toggle_filters.setFixedHeight(24)
        header.addWidget(self._btn_toggle_filters)
        layout.addLayout(header)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索案件、标签、案号、当事人或信息字段...")
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.setFixedHeight(30)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 2px 10px;
                color: {c['text_primary']};
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {c['accent']};
            }}
        """)
        layout.addWidget(self._search_input)

        self._filter_summary_label = QLabel("")
        self._filter_summary_label.setWordWrap(True)
        self._filter_summary_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 10px;
            padding: 0 2px;
        """)
        layout.addWidget(self._filter_summary_label)

        self._filter_controls = QWidget()
        controls_layout = QVBoxLayout(self._filter_controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self._filter_buttons = self._create_wrapped_filter_buttons(
            controls_layout,
            FILTER_OPTIONS,
            self._on_filter_clicked,
            "filter_value",
            [3, 3],
        )

        controls_layout.addWidget(self._create_filter_separator())

        self._status_buttons = self._create_wrapped_filter_buttons(
            controls_layout,
            STATUS_OPTIONS,
            self._on_status_clicked,
            "status_value",
            [2, 2],
        )

        controls_layout.addWidget(self._create_filter_separator())

        self._directory_buttons = self._create_wrapped_filter_buttons(
            controls_layout,
            DIRECTORY_OPTIONS,
            self._on_directory_clicked,
            "directory_value",
            [2, 2],
        )

        controls_layout.addWidget(self._create_filter_separator())

        tags_label = QLabel("标签/字段")
        tags_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
            font-weight: 600;
            padding-left: 2px;
        """)
        controls_layout.addWidget(tags_label)

        self._tag_scroll = QScrollArea()
        self._tag_scroll.setWidgetResizable(True)
        self._tag_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._tag_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._tag_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tag_scroll.setFixedHeight(36)
        self._tag_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._tag_container = QWidget()
        self._tag_layout = QHBoxLayout(self._tag_container)
        self._tag_layout.setContentsMargins(0, 4, 0, 4)
        self._tag_layout.setSpacing(6)
        self._tag_layout.addStretch()
        self._tag_scroll.setWidget(self._tag_container)
        controls_layout.addWidget(self._tag_scroll)

        layout.addWidget(self._filter_controls)
        self._sync_filter_panel_state()
        return panel

    def _create_cases_panel(self) -> QFrame:
        c = COLORS
        panel = QFrame()
        panel.setObjectName("casesPanel")
        panel.setStyleSheet(f"""
            QFrame#casesPanel {{
                background: {c['surface_0']};
                border: 1px solid rgba(226, 232, 240, 0.88);
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("案件列表")
        title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 700;
        """)
        header.addWidget(title)

        self._sort_btn = QPushButton("⇅")
        self._sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['text_muted']};
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 6px;
                min-width: 28px;
                max-width: 28px;
                min-height: 22px;
            }}
            QPushButton:hover {{
                background: {c['surface_1']};
                color: {c['text_primary']};
            }}
            QToolTip {{
                background-color: #1e293b;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                outline: none;
            }}
        """)
        self._sort_btn.clicked.connect(self._on_sort_clicked)
        header.addWidget(self._sort_btn)
        self._update_sort_button()

        header.addStretch()

        self._list_count_label = QLabel("共 0 个案件")
        self._list_count_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
            font-weight: 600;
        """)
        header.addWidget(self._list_count_label)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, 1)
        return panel

    def _toggle_filter_panel(self) -> None:
        self._filters_collapsed = not self._filters_collapsed
        self._sync_filter_panel_state()

    def _sync_filter_panel_state(self) -> None:
        if hasattr(self, "_filter_controls"):
            self._filter_controls.setVisible(not self._filters_collapsed)
        if hasattr(self, "_filter_summary_label"):
            self._filter_summary_label.setVisible(self._filters_collapsed)
        if hasattr(self, "_btn_toggle_filters"):
            self._btn_toggle_filters.setText("展开" if self._filters_collapsed else "收起")
            self._update_filter_style(self._btn_toggle_filters, False)

    def _update_filter_summary(self) -> None:
        if not hasattr(self, "_filter_summary_label"):
            return

        filter_text = next((label for label, value in FILTER_OPTIONS if value == self._current_filter), "未分类" if self._current_filter == "" else "全部")
        status_text = next((label for label, value in STATUS_OPTIONS if value == self._current_status), "全部")
        directory_text = next((label for label, value in DIRECTORY_OPTIONS if value == self._current_directory), "全部目录")
        tag_text = f"#{self._selected_tag}" if self._selected_tag else "全部标签"
        parts = [f"分类：{filter_text}", f"状态：{status_text}", f"目录：{directory_text}", f"标签：{tag_text}"]
        if self._search_text:
            parts.insert(0, f"搜索：{self._search_text}")
        self._filter_summary_label.setText("  ·  ".join(parts))

    def _create_list_panel(self) -> QWidget:
        panel = CaseSidebarDropPanel()
        panel.paths_dropped.connect(self._on_paths_dropped)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(8)

        self._drop_frame = CaseImportDropFrame()
        self._drop_frame.new_case_clicked.connect(self._on_new_case)
        self._drop_frame.import_clicked.connect(self._on_import_folder)
        self._drop_frame.batch_scan_clicked.connect(self._on_import_batch_scan)
        self._drop_frame.paths_dropped.connect(self._on_paths_dropped)
        layout.addWidget(self._drop_frame)
        layout.addWidget(self._create_search_filter_panel())
        layout.addWidget(self._create_cases_panel(), 1)
        return panel

    def _update_filter_style(self, btn: QPushButton, active: bool) -> None:
        c = COLORS
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c['accent_subtle']};
                    color: {c['accent']};
                    border: 1px solid {c['accent_light']};
                    border-radius: 7px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    min-height: 18px;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c['surface_0']};
                    color: {c['text_secondary']};
                    border: 1px solid {c['border']};
                    border-radius: 7px;
                    padding: 2px 10px;
                    font-size: 11px;
                    min-height: 18px;
                }}
                QPushButton:hover {{
                    background: {c['surface_2']};
                    color: {c['text_primary']};
                }}
            """)

    def _load_cases(self) -> None:
        """加载案件列表，使用增量更新避免全部重建卡片。"""
        self._refresh_tag_filters()
        self._update_filter_summary()
        cases = self._get_filtered_cases()

        # 1. 删除旧的分组标题
        for header in getattr(self, "_group_headers", []):
            self._list_layout.removeWidget(header)
            header.deleteLater()
        self._group_headers = []

        visible_ids = {case["id"] for case in cases}

        # 2. 删除不再显示的卡片（而不是全部清空）
        for cid in list(self._case_cards.keys()):
            if cid not in visible_ids:
                card = self._case_cards.pop(cid)
                self._list_layout.removeWidget(card)
                card.deleteLater()

        # 3. 重建显示顺序并复用/创建卡片
        self._case_id_order = [case["id"] for case in cases]
        self._list_container.setUpdatesEnabled(False)
        try:
            insert_position = 0
            for group_name, group_status in STATUS_GROUPS:
                group_cases = [case for case in cases if case.get("status", "active") == group_status]
                if not group_cases:
                    continue

                group_header = QLabel(f"  {group_name} ({len(group_cases)})")
                group_header.setStyleSheet(f"""
                    background: {COLORS["surface_0"]};
                    color: {COLORS["text_secondary"]};
                    font-size: 11px;
                    font-weight: 600;
                    padding: 6px 8px;
                    border-left: 3px solid {COLORS["accent"]};
                    border-radius: 0 6px 6px 0;
                    margin: 4px 2px 2px 2px;
                """)
                self._group_headers.append(group_header)
                self._list_layout.insertWidget(insert_position, group_header)
                insert_position += 1

                for case in group_cases:
                    case_id = case["id"]
                    if case_id in self._case_cards:
                        # 复用现有卡片，刷新数据并调整位置
                        card = self._case_cards[case_id]
                        card.refresh(case)
                        self._list_layout.removeWidget(card)
                        self._list_layout.insertWidget(insert_position, card)
                    else:
                        card = CaseCard(case)
                        card.selection_requested.connect(self._on_case_selection_requested)
                        card.context_menu_requested.connect(self._on_case_context_menu)
                        self._case_cards[case_id] = card
                        self._list_layout.insertWidget(insert_position, card)
                    insert_position += 1
        finally:
            self._list_container.setUpdatesEnabled(True)

        if not cases:
            empty = QLabel('暂无案件\n可拖入案件文件夹，或点击上方"导入案件"添加')
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"""
                background: transparent;
                color: {COLORS["text_muted"]};
                font-size: 13px;
                padding: 60px 0;
            """)
            self._list_layout.insertWidget(0, empty)
            self._detail_panel.clear()
            self._selected_case_ids.clear()
        elif self._selected_case_ids:
            valid_selected = {cid for cid in self._selected_case_ids if cid in self._case_cards}
            self._selected_case_ids = valid_selected
            self._update_selection_states()
            if self._selected_case_ids:
                first_selected = next(iter(self._selected_case_ids))
                case = self._cm.get_case(first_selected)
                if case:
                    self._detail_panel.load_case(case)
        else:
            first_id = cases[0]["id"]
            self._selected_case_ids = {first_id}
            self._update_selection_states()
            case = self._cm.get_case(first_id)
            if case:
                self._detail_panel.load_case(case)

        self._update_status_bar(cases)

    def _rebuild_group_headers(self) -> None:
        """仅重建分组标题并重新排列卡片。"""
        # 移除所有 widget（分组头 + 卡片），后面按顺序重新插入
        for header in getattr(self, "_group_headers", []):
            self._list_layout.removeWidget(header)
            header.deleteLater()
        self._group_headers = []

        cases = self._get_filtered_cases()
        self._case_id_order = [case["id"] for case in cases]

        self._list_container.setUpdatesEnabled(False)
        try:
            # 先把所有卡片从 layout 中取出（不销毁）
            for cid in self._case_id_order:
                if cid in self._case_cards:
                    self._list_layout.removeWidget(self._case_cards[cid])

            insert_position = 0
            for group_name, group_status in STATUS_GROUPS:
                group_cases = [c for c in cases if c.get("status", "active") == group_status]
                if not group_cases:
                    continue

                group_header = QLabel(f"  {group_name} ({len(group_cases)})")
                group_header.setStyleSheet(f"""
                    background: {COLORS["surface_0"]};
                    color: {COLORS["text_secondary"]};
                    font-size: 11px;
                    font-weight: 600;
                    padding: 6px 8px;
                    border-left: 3px solid {COLORS["accent"]};
                    border-radius: 0 6px 6px 0;
                    margin: 4px 2px 2px 2px;
                """)
                self._group_headers.append(group_header)
                self._list_layout.insertWidget(insert_position, group_header)
                insert_position += 1

                for case in group_cases:
                    cid = case["id"]
                    if cid in self._case_cards:
                        self._list_layout.insertWidget(insert_position, self._case_cards[cid])
                    insert_position += 1

            # 删除不在 visible_ids 中的残余卡片
            visible_ids = {c["id"] for c in cases}
            for cid in list(self._case_cards.keys()):
                if cid not in visible_ids:
                    card = self._case_cards.pop(cid)
                    self._list_layout.removeWidget(card)
                    card.deleteLater()
        finally:
            self._list_container.setUpdatesEnabled(True)

    def _get_filtered_cases(self) -> List[Dict]:
        if self._search_text:
            cases = self._cm.search_cases(self._search_text)
        elif self._current_filter == "all":
            cases = self._cm.get_all_cases()
        else:
            cases = self._cm.get_cases_by_category(self._current_filter)

        if self._current_filter != "all":
            allowed_categories = self._get_filter_categories()
            cases = [case for case in cases if case.get("category", "") in allowed_categories]

        if self._current_status != "all":
            cases = [case for case in cases if case.get("status", "active") == self._current_status]

        if self._current_directory != "all":
            cases = [case for case in cases if case.get("folder_status", "") == self._current_directory]

        if self._selected_tag:
            cases = [case for case in cases if self._selected_tag in case.get("tags", [])]

        # 排序
        if self._current_sort_mode == "name_asc":
            cases.sort(key=lambda c: str(c.get("name", "")).lower())
        elif self._current_sort_mode == "name_desc":
            cases.sort(key=lambda c: str(c.get("name", "")).lower(), reverse=True)
        elif self._current_sort_mode == "created_asc":
            cases.sort(key=lambda c: c.get("created_at", ""))
        elif self._current_sort_mode == "created_desc":
            cases.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        elif self._current_sort_mode == "updated_asc":
            cases.sort(key=lambda c: c.get("updated_at", ""))
        elif self._current_sort_mode == "updated_desc":
            cases.sort(key=lambda c: c.get("updated_at", ""), reverse=True)

        return cases
    def _update_status_bar(self, cases: List[Dict]) -> None:
        total = len(cases)
        if hasattr(self, "_list_count_label"):
            self._list_count_label.setText(f"共 {total} 个案件")
        active_count = sum(1 for case in cases if case.get("status", "active") == "active")
        pending_count = sum(1 for case in cases if case.get("status", "active") == "pending")
        closed_count = sum(1 for case in cases if case.get("status", "active") == "closed")
        missing_count = sum(1 for case in cases if case.get("folder_status", "") == FOLDER_STATUS_MISSING)
        unlinked_count = sum(1 for case in cases if case.get("folder_status", "") == FOLDER_STATUS_UNLINKED)
        parts = [
            f"共 {total} 个案件",
            f"推进中 {active_count}",
            f"未完结 {pending_count}",
            f"待归档 {closed_count}",
            f"目录缺失 {missing_count}",
]
        if unlinked_count:
            parts.append(f"未关联 {unlinked_count}")
        if self._selected_tag:
            parts.append(f"标签筛选 #{self._selected_tag}")
        self._status_bar.setText("  " + "  |  ".join(parts))

    def _get_filter_categories(self) -> List[str]:
        cat_map = {
            "civil": ["civil", "civil2"],
            "criminal": ["criminal"],
            "administrative": ["administrative"],
            "non_litigation": ["non_litigation"],
            "labor_arbitration": ["labor_arbitration"],
            "commercial_arbitration": ["commercial_arbitration"],
        }
        return cat_map.get(self._current_filter, [self._current_filter])

    def _update_selection_states(self) -> None:
        """根据 _selected_case_ids 更新所有卡片的选中样式。"""
        for cid, card in self._case_cards.items():
            card.set_selected(cid in self._selected_case_ids)

    def _load_detail_for_first_selected(self) -> None:
        """加载第一个选中案件的详情到右侧面板。"""
        if not self._selected_case_ids:
            return
        first_id = next(iter(self._selected_case_ids))
        case = self._cm.get_case(first_id)
        if case:
            self._detail_panel.load_case(case)

    def _select_single_case(self, case_id: str) -> None:
        """单选指定案件。"""
        self._selected_case_ids = {case_id}
        self._update_selection_states()
        self._load_detail_for_first_selected()

    def _sync_navigation_filter_state(self) -> None:
        """重置筛选状态，保证日历跳转目标案件可见。"""
        self._current_filter = "all"
        self._current_status = "all"
        self._current_directory = "all"
        self._selected_tag = ""
        self._search_text = ""
        if hasattr(self, "_search_input"):
            self._search_input.blockSignals(True)
            self._search_input.clear()
            self._search_input.blockSignals(False)
        for btn in getattr(self, "_filter_buttons", []):
            active = btn.property("filter_value") == "all"
            btn.setChecked(active)
            self._update_filter_style(btn, active)
        for btn in getattr(self, "_status_buttons", []):
            active = btn.property("status_value") == "all"
            btn.setChecked(active)
            self._update_filter_style(btn, active)
        for btn in getattr(self, "_directory_buttons", []):
            active = btn.property("directory_value") == "all"
            btn.setChecked(active)
            self._update_filter_style(btn, active)
        for value, button in self._tag_buttons.items():
            self._sync_tag_filter_style(button, value)

    def refresh_cases(self, preferred_case_id: str = "") -> None:
        """刷新案件列表与详情，并尽量保留当前选中案件。"""
        target_case_id = preferred_case_id or next(iter(self._selected_case_ids), "")
        if target_case_id:
            self._selected_case_ids = {target_case_id}
        self._load_cases()
        if target_case_id and target_case_id in self._case_cards:
            self._select_single_case(target_case_id)

    def open_case_deadline_tab(self, case_id: str, deadline_id: str = "") -> bool:
        """跳转到指定案件并切换到期限签页（不打开编辑弹窗）。"""
        case_id = case_id.strip()
        if not case_id:
            return False

        if case_id not in self._case_cards:
            self._sync_navigation_filter_state()
            self._selected_case_ids = {case_id}
            self._load_cases()

        if case_id not in self._case_cards:
            return False

        self._select_single_case(case_id)
        return self._detail_panel.show_deadline_tab(deadline_id)

    def open_case_deadline_from_calendar(self, case_id: str, deadline_id: str) -> bool:
        """从期限日历跳转到指定案件的期限编辑。"""
        case_id = case_id.strip()
        deadline_id = deadline_id.strip()
        if not case_id:
            return False

        if case_id not in self._case_cards:
            self._sync_navigation_filter_state()
            self._selected_case_ids = {case_id}
            self._load_cases()

        if case_id not in self._case_cards:
            return False

        self._select_single_case(case_id)
        if deadline_id:
            return self._detail_panel.open_deadline_editor_from_calendar(deadline_id)
        return True

    def _apply_initial_navigation(self) -> None:
        case_id = self._initial_case_id
        deadline_id = self._initial_deadline_id
        self._initial_case_id = ""
        self._initial_deadline_id = ""
        if case_id:
            self.open_case_deadline_from_calendar(case_id, deadline_id)

    def _on_case_selection_requested(self, case_id: str, modifiers: int) -> None:
        """处理案件卡片的点击/多选请求。"""
        ctrl_pressed = bool(modifiers & (Qt.KeyboardModifier.ControlModifier.value | Qt.KeyboardModifier.MetaModifier.value))
        shift_pressed = bool(modifiers & Qt.KeyboardModifier.ShiftModifier.value)

        if ctrl_pressed:
            # Ctrl/Cmd + 点击：切换选中
            if case_id in self._selected_case_ids:
                self._selected_case_ids.discard(case_id)
            else:
                self._selected_case_ids.add(case_id)
            self._update_selection_states()
            self._load_detail_for_first_selected()
        elif shift_pressed and self._selected_case_ids:
            # Shift + 点击：范围选中
            last_selected = next(iter(self._selected_case_ids))
            try:
                idx_last = self._case_id_order.index(last_selected)
                idx_current = self._case_id_order.index(case_id)
            except ValueError:
                self._select_single_case(case_id)
                return
            start, end = sorted((idx_last, idx_current))
            self._selected_case_ids = set(self._case_id_order[start:end + 1])
            self._update_selection_states()
            self._load_detail_for_first_selected()
        else:
            # 普通点击：单选
            self._select_single_case(case_id)

    def _on_detail_case_refreshed(self, case_id: str) -> None:
        """右侧详情变更后，实时刷新左侧对应案件卡片（局部刷新，避免重建整个列表）。"""
        if case_id and case_id in self._case_cards:
            case = self._cm.get_case(case_id)
            if case:
                self._case_cards[case_id].refresh(case)
        if case_id:
            self._select_single_case(case_id)

    def _on_case_context_menu(self, case_id: str, global_pos) -> None:
        """案件卡片右键菜单，支持批量操作。"""
        # 如果在未选中项上右键，先单选该项
        if case_id not in self._selected_case_ids:
            self._select_single_case(case_id)

        selected_count = len(self._selected_case_ids)
        is_batch = selected_count > 1

        menu = QMenu(self)
        open_folder_action = menu.addAction(f"打开文件夹 ({selected_count})")
        if not is_batch:
            rename_action = menu.addAction("重命名")
            redefine_action = menu.addAction("重新定义案件目录")
            migrate_action = menu.addAction("迁移案件文件夹")
        tags_action = menu.addAction(f"标签/分类 ({selected_count})")
        menu.addSeparator()
        delete_action = menu.addAction(f"删除 ({selected_count})")

        selected_action = menu.exec(global_pos)
        if selected_action is open_folder_action:
            self._on_open_folders_for_selected()
        elif selected_action is tags_action:
            self._on_edit_tags_for_selected()
        elif not is_batch and selected_action is rename_action:
            self._on_rename_case(case_id)
        elif not is_batch and selected_action is redefine_action:
            self._on_redefine_case_path(case_id)
        elif not is_batch and selected_action is migrate_action:
            self._on_migrate_case_folder(case_id)
        elif selected_action is delete_action:
            self._on_delete_selected_cases()

    def _on_rename_case(self, case_id: str) -> None:
        case = self._cm.get_case(case_id)
        if not case:
            return

        current_name = str(case.get("name", "")).strip()
        new_name, accepted = QInputDialog.getText(
            self,
            "重命名案件",
            "请输入新的案件名称：",
            text=current_name,
        )
        if not accepted:
            return

        target_name = str(new_name or "").strip()
        if not target_name:
            QMessageBox.information(self, "名称不能为空", "案件名称不能为空。")
            return
        if target_name == current_name:
            return

        try:
            success = self._cm.rename_case(case_id, target_name)
        except FileExistsError as exc:
            QMessageBox.warning(self, "重命名失败", str(exc))
            return
        except OSError as exc:
            QMessageBox.warning(self, "重命名失败", f"更新案件目录时出现问题：{exc}")
            return

        if not success:
            QMessageBox.warning(self, "重命名失败", "更新案件名称时出现问题。")
            return

        self._load_cases()
        self._select_single_case(case_id)

    def _on_delete_case(self, case_id: str) -> None:
        case = self._cm.get_case(case_id)
        if not case:
            return

        path_text = str(case.get("path", "")).strip()
        folder_path = Path(path_text) if path_text else None
        can_delete_folder = bool(folder_path and folder_path.exists())

        box = QMessageBox(self)
        box.setWindowTitle("删除案件")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(f"要如何处理案件“{case.get('name', '未命名案件')}”？")
        if can_delete_folder and folder_path is not None:
            box.setInformativeText(
                f"当前已关联目录：{folder_path}\n你可以只从软件剔除，也可以连同真实文件夹一起删除。"
            )
        else:
            box.setInformativeText("当前案件目录不可用，只能从软件中剔除案件记录。")

        remove_only_btn = box.addButton("仅在软件中剔除", QMessageBox.ButtonRole.AcceptRole)
        remove_folder_btn = None
        if can_delete_folder:
            remove_folder_btn = box.addButton("剔除并删除文件夹", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked is remove_only_btn:
            # 仅剔除记录（JSON 操作），同步执行即可
            success = self._cm.remove_case(case_id, delete_folder=False)
            self._after_delete_case(case_id, bool(success), False)
        elif remove_folder_btn is not None and clicked is remove_folder_btn:
            confirm = QMessageBox.warning(
                self,
                "确认删除文件夹",
                (
                    "这会把案件从软件中剔除，并真实删除对应文件夹。\n\n"
                    f"目录：{folder_path}\n\n"
                    "此操作不可撤销，是否继续？"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

            self._run_case_operation_async(
                "删除案件",
                "正在删除案件记录和真实文件夹...",
                lambda: self._cm.remove_case(case_id, delete_folder=True),
                lambda success: self._after_delete_case(case_id, bool(success), True),
            )
        else:
            return

    def _after_delete_case(self, case_id: str, success: bool, deleted_folder: bool) -> None:
        """案件删除后台任务完成后刷新界面 — 增量更新，避免全量重建。"""
        if not success:
            QMessageBox.warning(self, "删除失败", "删除案件时出现问题。")
            return

        # 1. 增量移除卡片（不触发全量 _load_cases）
        if case_id in self._case_cards:
            card = self._case_cards.pop(case_id)
            self._list_layout.removeWidget(card)
            card.deleteLater()
        self._selected_case_ids.discard(case_id)

        # 2. 清空详情面板（避免为自动选中的案件做全量 load_case）
        self._detail_panel.clear()

        # 3. 刷新标签过滤（带缓存，无变化时跳过）
        self._refresh_tag_filters()
        self._update_filter_summary()

        # 4. 重建分组头 + 重排卡片
        self._rebuild_group_headers()

        # 5. 更新状态栏
        cases = self._get_filtered_cases()
        self._update_status_bar(cases)

        if deleted_folder:
            QMessageBox.information(self, "删除完成", "案件记录和真实文件夹已删除。")

    def _on_sort_clicked(self) -> None:
        """点击排序按钮：循环切换排序模式。"""
        modes = [mode[0] for mode in SORT_MODES]
        current_idx = modes.index(self._current_sort_mode)
        next_idx = (current_idx + 1) % len(modes)
        self._current_sort_mode = modes[next_idx]
        self._update_sort_button()
        self._load_cases()

    def _update_sort_button(self) -> None:
        """更新排序按钮 tooltip，显示当前模式和切换提示。"""
        if not hasattr(self, "_sort_btn"):
            return
        for mode_key, short_label, tooltip_label in SORT_MODES:
            if mode_key == self._current_sort_mode:
                self._sort_btn.setToolTip(f"当前排序：{tooltip_label}，点击切换")
                break

    def _on_filter_clicked(self, clicked_btn: QPushButton) -> None:
        for btn in self._filter_buttons:
            btn.setChecked(btn is clicked_btn)
            self._update_filter_style(btn, btn is clicked_btn)
        self._current_filter = clicked_btn.property("filter_value")
        self._load_cases()

    def _on_status_clicked(self, clicked_btn: QPushButton) -> None:
        for btn in self._status_buttons:
            btn.setChecked(btn is clicked_btn)
            self._update_filter_style(btn, btn is clicked_btn)
        self._current_status = clicked_btn.property("status_value")
        self._load_cases()

    def _on_directory_clicked(self, clicked_btn: QPushButton) -> None:
        for btn in self._directory_buttons:
            btn.setChecked(btn is clicked_btn)
            self._update_filter_style(btn, btn is clicked_btn)
        self._current_directory = clicked_btn.property("directory_value")
        self._load_cases()

    def set_filter(self, filter_value: str = None, status_value: str = None, directory_value: str = None) -> None:
        """从外部设置筛选条件并刷新列表。"""
        if filter_value is not None:
            self._current_filter = filter_value
            for btn in getattr(self, "_filter_buttons", []):
                active = btn.property("filter_value") == filter_value
                btn.setChecked(active)
                self._update_filter_style(btn, active)
        if status_value is not None:
            self._current_status = status_value
            for btn in getattr(self, "_status_buttons", []):
                active = btn.property("status_value") == status_value
                btn.setChecked(active)
                self._update_filter_style(btn, active)
        if directory_value is not None:
            self._current_directory = directory_value
            for btn in getattr(self, "_directory_buttons", []):
                active = btn.property("directory_value") == directory_value
                btn.setChecked(active)
                self._update_filter_style(btn, active)
        self._load_cases()

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text.strip().lower()
        self._search_debounce_timer.start()

    def _do_search(self) -> None:
        """防抖后的实际搜索执行。"""
        self._load_cases()

    def apply_search(self, text: str) -> None:
        """从外部（如全局搜索框）应用搜索关键词并刷新列表。"""
        self._search_text = text.strip().lower()
        if hasattr(self, "_search_input"):
            self._search_input.blockSignals(True)
            self._search_input.setText(text)
            self._search_input.blockSignals(False)
        self._load_cases()

    def _refresh_tag_filters(self) -> None:
        # 标签缓存：标签没变化时跳过重建
        new_tags = self._cm.get_all_tags()
        if hasattr(self, "_cached_tags") and self._cached_tags == new_tags:
            return
        self._cached_tags = new_tags

        while self._tag_layout.count():
            item = self._tag_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._tag_buttons = {}
        tags = new_tags
        if self._selected_tag and self._selected_tag not in tags:
            self._selected_tag = ""

        self._add_tag_button("全部标签", "")
        for tag in tags:
            self._add_tag_button(f"#{tag}", tag)

        if not tags:
            empty = QLabel("暂无字段标签映射，后续可在“信息”里把字段值转为筛选标签。")
            empty.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['text_muted']};
                font-size: 11px;
            """)
            self._tag_layout.addWidget(empty)

        self._tag_layout.addStretch()

    def _add_tag_button(self, label: str, value: str) -> None:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.clicked.connect(lambda checked=False, tag_value=value: self._on_tag_clicked(tag_value))
        self._tag_buttons[value] = btn
        self._sync_tag_filter_style(btn, value)
        self._tag_layout.addWidget(btn)

    def _sync_tag_filter_style(self, btn: QPushButton, value: str) -> None:
        active = value == self._selected_tag if value else not self._selected_tag
        btn.setChecked(active)
        self._update_filter_style(btn, active)

    def _on_tag_clicked(self, tag_value: str) -> None:
        self._selected_tag = tag_value
        for value, button in self._tag_buttons.items():
            self._sync_tag_filter_style(button, value)
        self._load_cases()

    def _on_import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择案件文件夹",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return
        self._import_case_paths([Path(folder)], "单个案件导入")

    def _on_new_case(self) -> None:
        """关闭案件管理并返回主界面，继续使用原有新建案件流程。"""
        parent = self.parentWidget()
        self.close()
        if parent is not None:
            parent.show()
            parent.raise_()
            parent.activateWindow()

    def _on_import_batch_scan(self) -> None:
        root_folder = QFileDialog.getExistingDirectory(
            self,
            "选择案件上级目录",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if not root_folder:
            return

        candidates = self._collect_child_case_folders(Path(root_folder))
        if not candidates:
            QMessageBox.information(self, "未找到案件目录", "所选目录下没有可导入的子文件夹。")
            return

        self._import_case_paths(candidates, "批量扫描导入")

    def _collect_child_case_folders(self, root: Path) -> List[Path]:
        candidates = []
        for item in sorted(root.iterdir(), key=lambda path: path.name.lower()):
            if not item.is_dir() or item.name.startswith("."):
                continue
            candidates.append(item)
        return candidates

    def _on_paths_dropped(self, folder_paths: List[str]) -> None:
        self._import_case_paths([Path(path) for path in folder_paths], "拖拽导入")

    def _import_case_paths(self, folder_paths: List[Path], mode_label: str) -> None:
        if not folder_paths:
            return

        result = self._cm.import_existing_folders(folder_paths)
        self._load_cases()

        preferred_case_id = ""
        if result["imported_ids"]:
            preferred_case_id = result["imported_ids"][0]
        elif result["existing_ids"]:
            preferred_case_id = result["existing_ids"][0]

        if preferred_case_id:
            self._select_single_case(preferred_case_id)

        if len(folder_paths) > 1 or result["invalid_paths"] or result["existing_ids"]:
            self._show_import_summary(mode_label, result)

    def _show_import_summary(self, mode_label: str, result: Dict[str, List[str]]) -> None:
        imported_count = len(result["imported_ids"])
        existing_count = len(result["existing_ids"])
        invalid_count = len(result["invalid_paths"])
        parts = [f"{mode_label}完成。", f"新增 {imported_count} 个案件"]
        if existing_count:
            parts.append(f"已存在或重关联 {existing_count} 个")
        if invalid_count:
            parts.append(f"无效目录 {invalid_count} 个")
        QMessageBox.information(self, "导入结果", "，".join(parts))

    def _on_edit_tags(self, case_id: str) -> None:
        case = self._cm.get_case(case_id)
        if not case:
            return

        suggested_tags = self._cm.get_common_tags() or list(DEFAULT_TAG_SUGGESTIONS)
        dialog = TagEditorDialog(
            case.get("tags", []),
            suggested_tags,
            self,
            current_category=case.get("category", ""),
            current_status=case.get("status", "active"),
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self._cm.set_common_tags(dialog.get_common_tags())
        self._cm.update_case(case_id, {
            "tags": dialog.get_tags(),
            "category": dialog.get_category(),
            "status": dialog.get_status(),
        })
        self._load_cases()
        self._select_single_case(case_id)

    def _on_archive_case(self, case_id: str) -> None:
        case = self._cm.get_case(case_id)
        if not case:
            return

        folder_path = Path(case.get("path", ""))
        if not folder_path.exists():
            QMessageBox.warning(self, "路径不存在", "当前案件目录不存在，无法进行电子化归档。")
            return

        self._show_embed_page("电子化归档", ArchiveDialog(folder_path, embed_mode=True))

    def _on_view_calendar(self) -> None:
        """内嵌显示期限日历。"""
        dialog = CalendarDialog(self, embed_mode=True)
        self._show_embed_page("期限日历", dialog)

    def _on_tool_center(self) -> None:
        """内嵌显示工具中心。"""
        dialog = ToolCenterDialog(self, initial_case_id=getattr(self._detail_panel, "_case_id", ""), embed_mode=True)
        self._show_embed_page("工具中心", dialog)

    def _show_embed_page(self, title: str, content_widget: QWidget) -> None:
        """切换到指定功能的内嵌页面。"""
        page = self._create_embed_page(title, content_widget)

        # 清理旧的功能页面（保留第 0 页案件管理）
        while self._main_stack.count() > 1:
            old = self._main_stack.widget(1)
            self._main_stack.removeWidget(old)
            old.deleteLater()

        self._main_stack.addWidget(page)
        self._main_stack.setCurrentWidget(page)

    def _create_embed_page(self, title: str, content_widget: QWidget) -> QWidget:
        """创建带返回栏的内嵌页面。"""
        c = COLORS
        page = QWidget()
        page.setStyleSheet(f"QWidget {{ background: {c['surface_1']}; }}")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部返回栏
        nav = QWidget()
        nav.setFixedHeight(48)
        nav.setStyleSheet(f"""
            QWidget {{
                background: {c['surface_0']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(8)

        btn_back = QPushButton("← 返回案件")
        btn_back.setFixedHeight(32)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """)
        btn_back.clicked.connect(self._back_to_case_page)
        nav_layout.addWidget(btn_back)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 15px;
            font-weight: 600;
        """)
        nav_layout.addWidget(title_label)
        nav_layout.addStretch()

        layout.addWidget(nav)
        layout.addWidget(content_widget, 1)
        return page

    def _back_to_case_page(self) -> None:
        """返回案件管理主页面。"""
        self._main_stack.setCurrentWidget(self._case_page)
        # 清理功能页面释放资源
        while self._main_stack.count() > 1:
            old = self._main_stack.widget(1)
            self._main_stack.removeWidget(old)
            old.deleteLater()

    def _on_open_folders_for_selected(self) -> None:
        """批量打开选中案件的文件夹。"""
        opened = 0
        missing = 0
        for case_id in list(self._selected_case_ids):
            case = self._cm.get_case(case_id)
            if not case:
                continue
            path_text = str(case.get("path", "")).strip()
            if not path_text:
                missing += 1
                continue
            path = Path(path_text)
            if not path.exists():
                missing += 1
                continue
            ok, _ = open_path(path)
            if ok:
                opened += 1
        if missing:
            QMessageBox.information(self, "打开文件夹", f"成功打开 {opened} 个文件夹，{missing} 个路径不存在或已失效。")

    def _on_edit_tags_for_selected(self) -> None:
        """批量编辑选中案件的标签、分类和状态。"""
        if not self._selected_case_ids:
            return

        # 以第一个选中案件作为初始值
        first_case_id = next(iter(self._selected_case_ids))
        first_case = self._cm.get_case(first_case_id) or {}

        suggested_tags = self._cm.get_common_tags() or list(DEFAULT_TAG_SUGGESTIONS)
        dialog = TagEditorDialog(
            first_case.get("tags", []),
            suggested_tags,
            self,
            current_category=first_case.get("category", ""),
            current_status=first_case.get("status", "active"),
        )
        # 设置批量模式标题
        dialog.setWindowTitle(f"批量标签/分类（{len(self._selected_case_ids)} 个案件）")
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self._cm.set_common_tags(dialog.get_common_tags())
        updates = {
            "tags": dialog.get_tags(),
            "category": dialog.get_category(),
            "status": dialog.get_status(),
        }
        failed = []
        for case_id in list(self._selected_case_ids):
            if not self._cm.update_case(case_id, updates):
                failed.append(case_id)

        self._load_cases()
        if failed:
            QMessageBox.warning(self, "保存结果", f"成功更新 {len(self._selected_case_ids) - len(failed)} 个案件，{len(failed)} 个失败。")

    def _on_delete_selected_cases(self) -> None:
        """删除选中的案件。"""
        count = len(self._selected_case_ids)
        if count == 0:
            return

        # 统计有多少案件有真实文件夹
        has_folder_count = 0
        for cid in self._selected_case_ids:
            case = self._cm.get_case(cid)
            if case:
                p = str(case.get("path", "")).strip()
                if p and Path(p).exists():
                    has_folder_count += 1

        box = QMessageBox(self)
        box.setWindowTitle("删除案件")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(f"确定要删除选中的 {count} 个案件吗？")
        box.setInformativeText("此操作只会从软件中剔除案件记录，不会删除真实文件夹。")

        # 复选框：删除真实文件夹
        delete_folder_cb = None
        if has_folder_count > 0:
            delete_folder_cb = QCheckBox(
                f"同时删除真实文件夹（{has_folder_count} 个目录存在）", box
            )
            box.setCheckBox(delete_folder_cb)

        ok_btn = box.addButton("确定删除", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)

        # 勾选时动态切换提示文字
        def _on_checkbox_changed(checked):
            if checked:
                box.setInformativeText(
                    "⚠️ 警告：勾选后将从磁盘永久删除对应的真实文件夹及其全部内容！\n"
                    "此操作不可撤销，请确认已做好备份。"
                )
            else:
                box.setInformativeText("此操作只会从软件中剔除案件记录，不会删除真实文件夹。")

        if delete_folder_cb:
            delete_folder_cb.stateChanged.connect(_on_checkbox_changed)

        box.exec()

        if box.clickedButton() is not ok_btn:
            return

        delete_folder = bool(delete_folder_cb and delete_folder_cb.isChecked())
        case_ids = list(self._selected_case_ids)

        # 同步删除（文件夹删除通常也很快，避免 _run_case_operation_async 卡顿）
        failed = []
        for case_id in case_ids:
            if not self._cm.remove_case(case_id, delete_folder=delete_folder):
                failed.append(case_id)
            for case_id in case_ids:
                if not self._cm.remove_case(case_id, delete_folder=False):
                    failed.append(case_id)
            deleted_ids = set(case_ids) - set(failed)
            self._update_after_delete(deleted_ids, failed, count)

    def _update_after_delete(self, deleted_ids: set, failed: list, count: int) -> None:
        """删除案件后的增量界面更新。"""
        for cid in deleted_ids:
            if cid in self._case_cards:
                card = self._case_cards.pop(cid)
                self._list_layout.removeWidget(card)
                card.deleteLater()
        self._selected_case_ids -= deleted_ids
        if not self._selected_case_ids:
            self._detail_panel.clear()
        self._refresh_tag_filters()
        self._update_filter_summary()
        self._rebuild_group_headers()
        cases = self._get_filtered_cases()
        self._update_status_bar(cases)
        if failed:
            QMessageBox.warning(self, "删除结果", f"成功删除 {count - len(failed)} 个案件，{len(failed)} 个失败。")

    def _on_open_folder(self, folder_path: str) -> None:
        path = Path(folder_path)
        if not path.exists():
            QMessageBox.warning(self, "路径不存在", f"找不到目录：{path}")
            return

        ok, error = open_path(path)
        if not ok:
            QMessageBox.warning(self, "打开失败", error or f"无法打开：{path}")

    def _on_open_file(self, file_path: Path) -> None:
        if not file_path.exists():
            QMessageBox.warning(self, "文件不存在", f"找不到文件：{file_path}")
            return

        ok, error = open_path(file_path)
        if not ok:
            QMessageBox.warning(self, "打开失败", error or f"无法打开：{file_path}")

    def _on_relink_folder(self, case_id: str) -> None:
        case = self._cm.get_case(case_id)
        if not case:
            return

        current_path = str(case.get("path", "")).strip()
        start_dir = str(Path(current_path).parent) if current_path else ""
        folder = QFileDialog.getExistingDirectory(
            self,
            "重新关联案件目录",
            start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return

        if not self._cm.update_case_path(case_id, Path(folder)):
            QMessageBox.warning(self, "关联失败", "更新案件目录时出现问题。")
            return

        self._load_cases()
        self._select_single_case(case_id)
        QMessageBox.information(self, "关联成功", f"案件目录已更新为：{folder}")

    def _on_redefine_case_path(self, case_id: str) -> None:
        """重新定义案件目录：选择新目录后预览冲突并选择处理策略。"""
        case = self._cm.get_case(case_id)
        if not case:
            return

        current_path = str(case.get("path", "")).strip()
        start_dir = str(Path(current_path).parent) if current_path else ""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择新的案件目录",
            start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return

        folder_path = Path(folder)
        # 预览冲突
        try:
            sidecar, conflict_fields = self._cm.redefine_case_path(case_id, folder_path, mode="preview")
        except ValueError as exc:
            QMessageBox.warning(self, "预览失败", str(exc))
            return
        except Exception as exc:
            QMessageBox.warning(self, "预览失败", f"无法读取新目录的 sidecar：{exc}")
            return

        if not conflict_fields:
            # 无冲突，直接替换
            try:
                success = self._cm.redefine_case_path(case_id, folder_path, mode="replace")
            except Exception as exc:
                QMessageBox.warning(self, "操作失败", str(exc))
                return
            if success:
                self._load_cases()
                self._select_single_case(case_id)
                QMessageBox.information(self, "完成", "案件目录已重新定义，记录已替换。")
            else:
                QMessageBox.warning(self, "操作失败", "重新定义目录时出现问题。")
            return

        # 有冲突，弹出选择对话框
        dialog = _RedefineCaseDialog(self, case, sidecar, conflict_fields)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        mode = dialog.get_selected_mode()
        if not mode:
            return

        try:
            success = self._cm.redefine_case_path(case_id, folder_path, mode=mode)
        except Exception as exc:
            QMessageBox.warning(self, "操作失败", str(exc))
            return

        if success:
            self._load_cases()
            self._select_single_case(case_id)
            mode_names = {"replace": "替换", "keep": "仅更新路径", "merge": "智能合并"}
            QMessageBox.information(self, "完成", f"案件目录已重新定义（策略：{mode_names.get(mode, mode)}）。")
        else:
            QMessageBox.warning(self, "操作失败", "重新定义目录时出现问题。")

    def _on_migrate_case_folder(self, case_id: str) -> None:
        """迁移案件文件夹到新的父目录。"""
        case = self._cm.get_case(case_id)
        if not case:
            return

        current_path = str(case.get("path", "")).strip()
        start_dir = str(Path(current_path).parent) if current_path else ""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择目标父目录（案件文件夹将移入此目录）",
            start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return

        def _after_migrate(new_path: Path) -> None:
            self._load_cases()
            self._select_single_case(case_id)
            QMessageBox.information(self, "迁移成功", f"案件文件夹已迁移到：{new_path}")

        self._run_case_operation_async(
            "迁移案件",
            "正在迁移案件文件夹...",
            lambda: self._cm.migrate_case_folder(case_id, Path(folder)),
            _after_migrate,
        )



class _RedefineCaseDialog(QDialog):
    """重新定义案件目录时的冲突解决对话框。"""

    def __init__(
        self,
        parent: QWidget,
        case: Dict[str, Any],
        sidecar: Dict[str, Any],
        conflict_fields: List[str],
    ):
        super().__init__(parent)
        self.setWindowTitle("重新定义案件目录 — 冲突处理")
        self.setMinimumSize(560, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 说明文字
        info = QLabel(
            f"新目录中包含 {len(conflict_fields)} 处与当前记录不同的数据字段。\n"
            "请选择处理策略："
        )
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # 差异表格
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["字段", "当前记录", "新目录"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)

        field_labels = {
            "name": "案件名称",
            "category": "分类",
            "tags": "标签",
            "deadlines": "期限",
            "info_fields": "信息字段",
            "notes": "主笔记",
            "notes_secondary": "辅助笔记",
            "info_section_titles": "分组标题",
        }

        self._table.setRowCount(len(conflict_fields))
        for row, field in enumerate(conflict_fields):
            old_val = case.get(field, "")
            new_val = sidecar.get(field, "")

            def _fmt(val: Any) -> str:
                if isinstance(val, list):
                    if not val:
                        return "（空）"
                    if isinstance(val[0], dict):
                        return f"{len(val)} 条"
                    return ", ".join(str(v) for v in val[:5]) + ("..." if len(val) > 5 else "")
                if isinstance(val, dict):
                    return f"{len(val)} 项"
                text = str(val or "").strip()
                if not text:
                    return "（空）"
                # 截断长文本
                if len(text) > 80:
                    return text[:77] + "..."
                return text

            self._table.setItem(row, 0, QTableWidgetItem(field_labels.get(field, field)))
            self._table.setItem(row, 1, QTableWidgetItem(_fmt(old_val)))
            self._table.setItem(row, 2, QTableWidgetItem(_fmt(new_val)))

        self._table.resizeColumnsToContents()
        layout.addWidget(self._table)

        # 策略选择
        self._radio_replace = QRadioButton("替换 — 用新目录数据完全覆盖现有记录")
        self._radio_keep = QRadioButton("仅更新路径 — 保留现有记录，只改目录路径")
        self._radio_merge = QRadioButton("智能合并 — 合并标签/期限/字段/笔记，名称和分组标题保留现有")
        self._radio_merge.setChecked(True)

        radio_layout = QVBoxLayout()
        radio_layout.setSpacing(6)
        radio_layout.addWidget(self._radio_replace)
        radio_layout.addWidget(self._radio_keep)
        radio_layout.addWidget(self._radio_merge)
        layout.addLayout(radio_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("确定")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def get_selected_mode(self) -> str:
        if self._radio_replace.isChecked():
            return "replace"
        if self._radio_keep.isChecked():
            return "keep"
        return "merge"
