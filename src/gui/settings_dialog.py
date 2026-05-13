# -*- coding: utf-8 -*-
"""设置对话框模块"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QGroupBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDoubleSpinBox,
    # QFormLayout — 使用 TransparentFormLayout 替代
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QWidget,
    QSizePolicy,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtGui import QPixmap, QIcon

from src.config.config_manager import get_config_manager
from src.core.backup import BackupService
from src.core.case_manager import get_case_manager
from src.core.calendar_exporter import FORMAT_OPTIONS, THEME_OPTIONS
from src.core.search import FileSearchService
from src.gui.styles import APP_COLORS as COLORS, button_style, hint_banner_style
from src.utils.logger import get_logger
from src.utils.platform_utils import get_default_output_dir


class _SettingsFileIndexWorker(QObject):
    """设置页后台重建文件索引。"""

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


class _BackupWorker(QObject):
    """后台备份/导入工作线程。"""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, action: str, **kwargs):
        super().__init__()
        self._action = action
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            svc = BackupService()
            if self._action == "create":
                result = svc.create_backup(**self._kwargs)
            else:
                result = svc.import_backup(**self._kwargs)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_manager = get_config_manager()
        self._logger = get_logger()
        self._index_thread: Optional[QThread] = None
        self._index_worker: Optional[_SettingsFileIndexWorker] = None
        self._backup_thread: Optional[QThread] = None
        self._backup_worker: Optional[_BackupWorker] = None
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        self.setWindowTitle("设置")
        self.setMinimumSize(720, 600)
        self.resize(820, 660)
        self.setStyleSheet(f"""
            QDialog {{
                background: {c['surface_1']};
            }}
            QLabel {{
                background: transparent;
            }}
            QCheckBox {{
                background: transparent;
                border: none;
                spacing: 8px;
                color: {c['text_secondary']};
                font-size: 12px;
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
            }}
            QSpinBox {{
                background: {c['surface_0']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 28px 0 12px;
                min-height: 34px;
                max-height: 34px;
                font-size: 12px;
            }}
            QSpinBox:focus {{
                border-color: {c['accent']};
                background: {c['surface_0']};
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 22px;
                border: none;
                border-left: 1px solid {c['border']};
                border-bottom: 1px solid {c['border']};
                border-top-right-radius: 9px;
                margin: 1px 1px 0 0;
                background: {c['surface_1']};
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 22px;
                border: none;
                border-left: 1px solid {c['border']};
                border-bottom-right-radius: 9px;
                margin: 0 1px 1px 0;
                background: {c['surface_1']};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {c['surface_2']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        banner = QLabel("设置会保存到本地配置目录，影响默认输出目录、窗口尺寸与生成偏好。")
        banner.setWordWrap(True)
        banner.setStyleSheet(hint_banner_style("info"))
        layout.addWidget(banner)

        # 选项卡
        tab_widget = QTabWidget()
        tab_widget.setDocumentMode(True)
        tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 6px 16px;
                margin-top: 8px;
                margin-right: 6px;
                font-size: 13px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {c['accent']};
                color: {c['surface_0']};
                border-color: {c['accent']};
            }}
            QTabBar::tab:hover:!selected {{
                background: {c['surface_2']};
                border-color: {c['border_strong']};
            }}
        """)

        # 常规设置
        general_tab = self._create_general_tab()
        tab_widget.addTab(general_tab, "常规")

        # 生成设置
        generation_tab = self._create_generation_tab()
        tab_widget.addTab(generation_tab, "生成")

        # 界面设置
        ui_tab = self._create_ui_tab()
        tab_widget.addTab(ui_tab, "界面")

        # 备份与迁移
        backup_tab = self._create_backup_tab()
        tab_widget.addTab(backup_tab, "备份与迁移")

        # 日历导出
        calendar_export_tab = self._create_calendar_export_tab()
        tab_widget.addTab(calendar_export_tab, "日历导出")

        # LPR 数据管理
        lpr_data_tab = self._create_lpr_data_tab()
        tab_widget.addTab(lpr_data_tab, "LPR数据")

        # 关于
        about_tab = self._create_about_tab()
        tab_widget.addTab(about_tab, "关于")

        layout.addWidget(tab_widget)

        # 分割线：与按钮留足呼吸感
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {c['border']}; max-height: 1px; border: none;")
        layout.addWidget(separator)
        layout.addSpacing(12)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        reset_btn = QPushButton("恢复默认")
        reset_btn.setStyleSheet(button_style())
        reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(reset_btn)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(button_style(primary=True))
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(button_style())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        """创建常规设置选项卡"""
        widget = QWidget()
        from src.gui.widgets.transparent_form_layout import TransparentFormLayout
        layout = TransparentFormLayout(widget)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # 语言
        self._language_combo = QLineEdit("简体中文")
        self._language_combo.setReadOnly(True)
        layout.addRow("语言:", self._language_combo)

        # 检查更新
        self._check_updates_cb = QCheckBox()
        layout.addRow("自动检查更新:", self._check_updates_cb)

        return widget

    def _create_generation_tab(self) -> QWidget:
        """创建生成设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        # 默认输出目录
        dir_group = QGroupBox("默认输出目录")
        dir_group.setProperty("card", True)
        dir_layout = QHBoxLayout(dir_group)
        dir_layout.setContentsMargins(16, 18, 16, 16)

        self._output_dir_edit = QLineEdit()
        dir_layout.addWidget(self._output_dir_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet(button_style(compact=True))
        browse_btn.clicked.connect(self._on_browse_output_dir)
        dir_layout.addWidget(browse_btn)

        layout.addWidget(dir_group)

        # 生成选项
        options_group = QGroupBox("生成选项")
        options_group.setProperty("card", True)
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(16, 18, 16, 16)
        options_layout.setSpacing(10)

        self._auto_open_cb = QCheckBox("生成后自动打开文件夹")
        options_layout.addWidget(self._auto_open_cb)

        self._create_readme_cb = QCheckBox("创建 README 文件")
        options_layout.addWidget(self._create_readme_cb)

        layout.addWidget(options_group)

        layout.addStretch()

        return widget

    def _create_ui_tab(self) -> QWidget:
        """创建界面设置选项卡"""
        widget = QWidget()
        from src.gui.widgets.transparent_form_layout import TransparentFormLayout
        layout = TransparentFormLayout(widget)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # 窗口大小
        size_layout = QHBoxLayout()
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(8)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(800, 2000)
        self._width_spin.setSuffix(" px")
        self._width_spin.setFixedWidth(154)
        size_layout.addWidget(self._width_spin)

        multiply_label = QLabel("x")
        multiply_label.setFixedWidth(16)
        multiply_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        multiply_label.setStyleSheet(f"""
            background: transparent;
            border: none;
            color: {COLORS['text_secondary']};
            font-size: 12px;
            font-weight: 700;
        """)
        size_layout.addWidget(multiply_label)

        self._height_spin = QSpinBox()
        self._height_spin.setRange(600, 1500)
        self._height_spin.setSuffix(" px")
        self._height_spin.setFixedWidth(154)
        size_layout.addWidget(self._height_spin)
        size_layout.addStretch()

        layout.addRow("窗口大小:", size_layout)

        # 显示预览
        self._show_preview_cb = QCheckBox()
        layout.addRow("显示文件夹预览:", self._show_preview_cb)

        return widget

    def _create_settings_card(self, title: str) -> Tuple[QWidget, QVBoxLayout]:
        """创建设置页普通卡片，标题放在卡片内部。"""
        c = COLORS
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QCheckBox {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 700;
            background: transparent;
            border: none;
            padding: 0;
        """)
        layout.addWidget(title_label)
        return card, layout

    def _create_description_label(self, text: str, *, min_height: int = 38) -> QLabel:
        """创建不会被压扁的说明文字。"""
        c = COLORS
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMinimumHeight(min_height)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 12px;
            padding: 2px 0;
            background: transparent;
        """)
        return label

    def _create_lpr_data_tab(self) -> QWidget:
        """创建 LPR 数据管理选项卡。"""
        from src.core.lpr_data import default_lpr_history, get_lpr_manager

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 16, 20, 16)
        c = COLORS

        hint = QLabel("管理 LPR（贷款市场报价利率）数据。下方表格显示系统内置数据，您可以通过「添加自定义」补充新的 LPR 报价。自定义数据会覆盖同日内置数据。")
        hint.setWordWrap(True)
        hint.setStyleSheet(hint_banner_style("info"))
        layout.addWidget(hint)

        # 数据表格
        self._lpr_table = QTableWidget()
        self._lpr_table.setColumnCount(4)
        self._lpr_table.setHorizontalHeaderLabels(["报价日期", "1年期(%)", "5年期以上(%)", "来源"])
        self._lpr_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._lpr_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._lpr_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._lpr_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._lpr_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._lpr_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._lpr_table.setStyleSheet(f"""
            QTableWidget {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
            QHeaderView::section {{
                background: {c['surface_1']};
                color: {c['text_secondary']};
                font-weight: 600;
                padding: 8px;
                border: none;
                border-bottom: 1px solid {c['border']};
            }}
        """)
        layout.addWidget(self._lpr_table)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        add_btn = QPushButton("添加自定义")
        add_btn.setFixedHeight(32)
        add_btn.setStyleSheet(button_style(primary=True))
        add_btn.clicked.connect(self._on_lpr_add_custom)
        btn_row.addWidget(add_btn)

        del_btn = QPushButton("删除选中")
        del_btn.setFixedHeight(32)
        del_btn.setStyleSheet(button_style())
        del_btn.clicked.connect(self._on_lpr_delete_custom)
        btn_row.addWidget(del_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedHeight(32)
        refresh_btn.setStyleSheet(button_style())
        refresh_btn.clicked.connect(self._refresh_lpr_table)
        btn_row.addWidget(refresh_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._refresh_lpr_table()
        return widget

    def _refresh_lpr_table(self) -> None:
        """刷新 LPR 数据表格。"""
        from src.core.lpr_data import default_lpr_history, get_lpr_manager

        manager = get_lpr_manager()
        custom_dates = {
            str(item.get("date", ""))
            for item in (self._config_manager.get("tools.lpr_custom", []) or [])
        }
        records = manager.all_records()

        self._lpr_table.setRowCount(len(records))
        for row, (date_str, rates) in enumerate(records):
            self._lpr_table.setItem(row, 0, QTableWidgetItem(date_str))
            self._lpr_table.setItem(row, 1, QTableWidgetItem(f"{rates.get('1y', 0):.2f}"))
            self._lpr_table.setItem(row, 2, QTableWidgetItem(f"{rates.get('5y', 0):.2f}"))
            source = "自定义" if date_str in custom_dates else "内置"
            self._lpr_table.setItem(row, 3, QTableWidgetItem(source))

    def _on_lpr_add_custom(self) -> None:
        """添加自定义 LPR 记录。"""
        from src.core.lpr_data import get_lpr_manager

        dialog = QDialog(self)
        dialog.setWindowTitle("添加 LPR 数据")
        dialog.setMinimumWidth(360)
        c = COLORS
        dialog.setStyleSheet(f"QDialog {{ background: {c['surface_0']}; }}")

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        date_edit = QLineEdit()
        date_edit.setPlaceholderText("YYYY-MM-DD")
        date_edit.setText(datetime.now().strftime("%Y-%m-%d"))
        layout.addWidget(QLabel("报价日期:"))
        layout.addWidget(date_edit)

        rate_1y_spin = QDoubleSpinBox()
        rate_1y_spin.setRange(0, 100)
        rate_1y_spin.setDecimals(2)
        rate_1y_spin.setSingleStep(0.05)
        rate_1y_spin.setValue(3.00)
        layout.addWidget(QLabel("1年期利率(%):"))
        layout.addWidget(rate_1y_spin)

        rate_5y_spin = QDoubleSpinBox()
        rate_5y_spin.setRange(0, 100)
        rate_5y_spin.setDecimals(2)
        rate_5y_spin.setSingleStep(0.05)
        rate_5y_spin.setValue(3.50)
        layout.addWidget(QLabel("5年期以上利率(%):"))
        layout.addWidget(rate_5y_spin)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedHeight(32)
        ok_btn.setStyleSheet(button_style(accent=True))
        ok_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setStyleSheet(button_style())
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        date_str = date_edit.text().strip()
        if not date_str:
            QMessageBox.warning(self, "输入错误", "请输入报价日期。")
            return

        manager = get_lpr_manager()
        manager.add_custom(date_str, rate_1y_spin.value(), rate_5y_spin.value())
        self._refresh_lpr_table()
        QMessageBox.information(self, "添加成功", f"已添加 {date_str} 的 LPR 数据。")

    def _on_lpr_delete_custom(self) -> None:
        """删除选中的自定义 LPR 记录。"""
        from src.core.lpr_data import get_lpr_manager

        row = self._lpr_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一行。")
            return

        source_item = self._lpr_table.item(row, 3)
        if source_item and source_item.text() != "自定义":
            QMessageBox.information(self, "提示", "只能删除自定义数据，内置数据无法删除。")
            return

        date_str = self._lpr_table.item(row, 0).text()
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除 {date_str} 的自定义 LPR 数据吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        manager = get_lpr_manager()
        if manager.remove_custom(date_str):
            self._refresh_lpr_table()
            QMessageBox.information(self, "删除成功", f"已删除 {date_str} 的自定义 LPR 数据。")

    def _create_about_tab(self) -> QWidget:
        """创建'关于'选项卡。"""
        from src.utils.version import get_version

        c = COLORS
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(0, 0, 0, 0)

        # 可滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── 应用与开发者信息（合并卡片，左右分栏） ──
        about_card = QFrame()
        about_card.setStyleSheet(f"""
            QFrame {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}
        """)
        about_layout = QHBoxLayout(about_card)
        about_layout.setContentsMargins(24, 24, 24, 24)
        about_layout.setSpacing(0)

        # 左侧：软件介绍
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent; border: none;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo（SVG 源文件，由 QIcon 自动按设备 DPI 渲染，杜绝缩放模糊）
        logo_svg = Path(__file__).parent.parent.parent / "resources" / "icons" / "lexora_app_icon_flat.svg"
        logo_png = Path(__file__).parent.parent.parent / "resources" / "icons" / "lexora_app_icon_flat.png"
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if logo_svg.exists():
            icon = QIcon(str(logo_svg))
            pix = icon.pixmap(72, 72)
            logo_label.setPixmap(pix)
        elif logo_png.exists():
            pix = QPixmap(str(logo_png)).scaled(
                72, 72,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(pix)
        logo_label.setStyleSheet("background: transparent; border: none; padding: 4px 0 8px 0;")
        left_layout.addWidget(logo_label)

        app_name = QLabel("案件文件夹管理系统")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setStyleSheet(f"""
            color: {c['text_primary']};
            font-size: 22px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        left_layout.addWidget(app_name)

        brand_en = QLabel("LEXORA")
        brand_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_en.setStyleSheet(f"""
            color: {c['accent']};
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 4px;
            background: transparent;
            border: none;
        """)
        left_layout.addWidget(brand_en)

        ver_label = QLabel(f"v{get_version()}")
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_label.setStyleSheet(f"""
            color: {c['text_muted']};
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        left_layout.addWidget(ver_label)

        tagline = QLabel("以本地文件夹为核心载体的案件管理桌面应用")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setWordWrap(True)
        tagline.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        left_layout.addWidget(tagline)
        left_layout.addStretch()

        about_layout.addWidget(left_widget, 1)

        # 中间：浅分割线
        v_line = QFrame()
        v_line.setFrameShape(QFrame.Shape.VLine)
        v_line.setStyleSheet(f"background-color: {c['border']}; max-width: 1px; border: none;")
        about_layout.addWidget(v_line)

        # 右侧：开发者信息
        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent; border: none;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 0, 0, 0)
        right_layout.setSpacing(10)

        dev_title = QLabel("开发者")
        dev_title.setStyleSheet(f"""
            color: {c['text_primary']};
            font-size: 14px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        right_layout.addWidget(dev_title)

        # 姓名 + 身份
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        dev_name = QLabel("汪立")
        dev_name.setStyleSheet(f"""
            color: {c['accent']};
            font-size: 16px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        name_row.addWidget(dev_name)
        dev_role = QLabel("安徽始信律师事务所执业律师 ｜ 全栈型律师")
        dev_role.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        name_row.addWidget(dev_role)
        name_row.addStretch()
        right_layout.addLayout(name_row)

        email_label = QLabel('邮箱：491445490@qq.com')
        email_label.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        right_layout.addWidget(email_label)

        right_layout.addSpacing(8)

        social_title = QLabel("关注开发者")
        social_title.setStyleSheet(f"""
            color: {c['text_primary']};
            font-size: 14px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        right_layout.addWidget(social_title)

        _social_items = [
            ("微信公众号", "池州汪律的Ai进化论"),
            ("抖音 / 小红书 / B站", "池州有个汪律师"),
        ]
        for label_text, value_text in _social_items:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(f"{label_text}：")
            lbl.setStyleSheet(f"""
                color: {c['text_muted']};
                font-size: 12px;
                background: transparent;
                border: none;
            """)
            row.addWidget(lbl)
            val = QLabel(value_text)
            val.setStyleSheet(f"""
                color: {c['text_primary']};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            """)
            row.addWidget(val)
            row.addStretch()
            right_layout.addLayout(row)

        right_layout.addStretch()
        about_layout.addWidget(right_widget, 1)

        root.addWidget(about_card)

        # ── 二维码占位 ──
        qr_row = QHBoxLayout()
        qr_row.setSpacing(16)

        qr_cards = [
            ("扫码关注公众号", "wx_qrcode.png"),
            ("打赏支持开发者", "donate_qrcode.png"),
        ]
        for title_text, qr_path in qr_cards:
            card = QFrame()
            card.setFixedSize(160, 200)
            card.setStyleSheet(f"""
                QFrame {{
                    background: {c['surface_0']};
                    border: 1px solid {c['border']};
                    border-radius: 14px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 14, 12, 14)
            card_layout.setSpacing(8)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 尝试加载二维码图片
            from pathlib import Path as _P
            img_path = _P(__file__).parent.parent.parent / qr_path
            if img_path.exists():
                pix = QPixmap(str(img_path))
                qr_img = QLabel()
                qr_img.setPixmap(pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                qr_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                qr_img.setStyleSheet("background: transparent; border: none;")
            else:
                # 占位符：虚线框 + 提示文字
                qr_img = QLabel("二维码\n占位")
                qr_img.setFixedSize(120, 120)
                qr_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                qr_img.setStyleSheet(f"""
                    background: {c['surface_1']};
                    border: 2px dashed {c['border']};
                    border-radius: 10px;
                    color: {c['text_muted']};
                    font-size: 12px;
                """)
            card_layout.addWidget(qr_img)

            qr_title = QLabel(title_text)
            qr_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qr_title.setStyleSheet(f"""
                color: {c['text_secondary']};
                font-size: 11px;
                font-weight: 600;
                background: transparent;
                border: none;
            """)
            card_layout.addWidget(qr_title)

            qr_row.addWidget(card)

        qr_row.addStretch()
        root.addLayout(qr_row)

        # ── 版权 ──
        root.addSpacing(8)
        copyright_label = QLabel("© 2024-2026 汪立  版权所有")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet(f"""
            color: {c['text_muted']};
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        root.addWidget(copyright_label)

        root.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        return widget

    def _create_calendar_export_tab(self) -> QWidget:
        """创建日历导出设置选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        preset_group, preset_layout = self._create_settings_card("快速导出预设")
        preset_hint = self._create_description_label(
            "设置默认导出目录、格式和主题。在日历详情面板点击「快速导出」时将直接使用此预设。",
            min_height=46,
        )
        preset_layout.addWidget(preset_hint)

        # 导出目录
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self._calendar_export_dir_edit = QLineEdit()
        self._calendar_export_dir_edit.setPlaceholderText("选择默认导出目录")
        dir_row.addWidget(self._calendar_export_dir_edit, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet(button_style(compact=True))
        browse_btn.clicked.connect(self._on_browse_calendar_export_dir)
        dir_row.addWidget(browse_btn)
        preset_layout.addLayout(dir_row)

        # 导出格式
        format_row = QHBoxLayout()
        format_row.setSpacing(8)
        format_label = QLabel("导出格式:")
        format_label.setStyleSheet("background: transparent;")
        format_row.addWidget(format_label)
        self._calendar_export_format_combo = QComboBox()
        for key, label in FORMAT_OPTIONS:
            self._calendar_export_format_combo.addItem(label, key)
        format_row.addWidget(self._calendar_export_format_combo, 1)
        preset_layout.addLayout(format_row)

        # 导出主题
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        theme_label = QLabel("导出主题:")
        theme_label.setStyleSheet("background: transparent;")
        theme_row.addWidget(theme_label)
        self._calendar_export_theme_combo = QComboBox()
        for key, label in THEME_OPTIONS:
            self._calendar_export_theme_combo.addItem(label, key)
        theme_row.addWidget(self._calendar_export_theme_combo, 1)
        preset_layout.addLayout(theme_row)

        layout.addWidget(preset_group)

        # 自动导出
        auto_group, auto_layout = self._create_settings_card("自动导出")
        auto_hint = self._create_description_label(
            "关闭软件时自动使用上述预设导出选定的筛选结果。",
            min_height=38,
        )
        auto_layout.addWidget(auto_hint)

        scope_row = QHBoxLayout()
        scope_row.setSpacing(8)
        scope_label = QLabel("导出范围:")
        scope_label.setStyleSheet("background: transparent;")
        scope_row.addWidget(scope_label)
        self._calendar_auto_export_scope_combo = QComboBox()
        self._calendar_auto_export_scope_combo.addItem("未来全部", "future")
        self._calendar_auto_export_scope_combo.addItem("逾期全部", "overdue")
        self._calendar_auto_export_scope_combo.addItem("当前日历筛选结果", "current")
        scope_row.addWidget(self._calendar_auto_export_scope_combo, 1)
        auto_layout.addLayout(scope_row)

        self._calendar_auto_export_cb = QCheckBox("关闭软件时自动导出")
        auto_layout.addWidget(self._calendar_auto_export_cb)
        layout.addWidget(auto_group)

        layout.addStretch()
        return widget

    def _on_browse_calendar_export_dir(self) -> None:
        """浏览日历导出目录。"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择日历导出目录",
            self._calendar_export_dir_edit.text() or str(Path.home()),
        )
        if dir_path:
            self._calendar_export_dir_edit.setText(dir_path)

    def _create_backup_tab(self) -> QWidget:
        """创建备份与迁移选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(14)

        backup_group, backup_layout = self._create_settings_card("创建本地备份")

        backup_hint = self._create_description_label(
            "备份包含配置、案件台账、模板和案件 sidecar 元数据。可选包含真实案件文件。",
            min_height=46,
        )
        backup_layout.addWidget(backup_hint)

        self._backup_include_files_cb = QCheckBox("包含真实案件文件夹（备份会变大）")
        backup_layout.addWidget(self._backup_include_files_cb)

        backup_btn = QPushButton("创建备份...")
        backup_btn.setStyleSheet(button_style(primary=True))
        backup_btn.clicked.connect(self._on_create_backup)
        backup_layout.addWidget(backup_btn)

        layout.addWidget(backup_group)

        restore_group, restore_layout = self._create_settings_card("导入备份")

        restore_hint = self._create_description_label(
            "导入会先保存当前配置快照，再恢复备份内的数据。导入后建议重启软件。",
            min_height=46,
        )
        restore_layout.addWidget(restore_hint)

        self._restore_case_files_cb = QCheckBox("恢复备份内案件文件到指定目录")
        restore_layout.addWidget(self._restore_case_files_cb)

        restore_btn = QPushButton("导入备份...")
        restore_btn.setStyleSheet(button_style())
        restore_btn.clicked.connect(self._on_import_backup)
        restore_layout.addWidget(restore_btn)

        layout.addWidget(restore_group)

        index_group, index_layout = self._create_settings_card("文件搜索索引")

        index_hint = self._create_description_label(
            "文件搜索只索引文件名和相对路径。导入案件后会自动更新，也可以在这里手动重建。",
            min_height=46,
        )
        index_layout.addWidget(index_hint)

        self._rebuild_index_btn = QPushButton("重建文件索引")
        self._rebuild_index_btn.setStyleSheet(button_style())
        self._rebuild_index_btn.clicked.connect(self._on_rebuild_file_index)
        index_layout.addWidget(self._rebuild_index_btn)

        layout.addWidget(index_group)
        layout.addStretch()
        return widget

    def _load_settings(self) -> None:
        """加载设置"""
        # 常规
        self._check_updates_cb.setChecked(
            self._config_manager.get("app.check_updates", True)
        )

        # 生成
        self._output_dir_edit.setText(
            self._config_manager.get(
                "generation.default_output_dir",
                str(get_default_output_dir())
            ) or str(get_default_output_dir())
        )
        self._auto_open_cb.setChecked(
            self._config_manager.get("generation.auto_open_folder", True)
        )
        self._create_readme_cb.setChecked(
            self._config_manager.get("generation.create_readme", False)
        )

        # 界面
        self._width_spin.setValue(
            self._config_manager.get("ui.window_width", 1000)
        )
        self._height_spin.setValue(
            self._config_manager.get("ui.window_height", 700)
        )
        self._show_preview_cb.setChecked(
            self._config_manager.get("ui.show_preview", True)
        )

        # 日历导出
        cal_settings = self._config_manager.get("ui.calendar_export", {}) or {}
        self._calendar_export_dir_edit.setText(
            str(cal_settings.get("last_directory", "") or "")
        )
        format_idx = self._calendar_export_format_combo.findData(
            cal_settings.get("last_format", "pdf")
        )
        self._calendar_export_format_combo.setCurrentIndex(
            format_idx if format_idx >= 0 else 0
        )
        theme_idx = self._calendar_export_theme_combo.findData(
            cal_settings.get("last_theme", "stream")
        )
        self._calendar_export_theme_combo.setCurrentIndex(
            theme_idx if theme_idx >= 0 else 0
        )
        self._calendar_auto_export_cb.setChecked(
            bool(cal_settings.get("auto_export_on_close", False))
        )
        scope_idx = self._calendar_auto_export_scope_combo.findData(
            cal_settings.get("auto_export_scope", "future")
        )
        self._calendar_auto_export_scope_combo.setCurrentIndex(
            scope_idx if scope_idx >= 0 else 0
        )

    def _on_browse_output_dir(self) -> None:
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择默认输出目录",
            self._output_dir_edit.text()
        )
        if dir_path:
            self._output_dir_edit.setText(dir_path)

    def _on_create_backup(self) -> None:
        """创建本地迁移备份。"""
        if self._backup_thread and self._backup_thread.isRunning():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        default_name = str(Path.home() / f"lexora_backup_{timestamp}.lexora-backup")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存备份文件",
            default_name,
            "LEXORA 备份 (*.lexora-backup);;ZIP 文件 (*.zip)",
        )
        if not file_path:
            return

        self._start_backup_worker(
            "create",
            output_path=Path(file_path),
            cases=get_case_manager().get_all_cases(),
            include_case_files=self._backup_include_files_cb.isChecked(),
        )

    def _on_import_backup(self) -> None:
        """导入本地迁移备份。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择备份文件",
            str(Path.home()),
            "LEXORA 备份 (*.lexora-backup);;ZIP 文件 (*.zip);;所有文件 (*)",
        )
        if not file_path:
            return

        self.import_backup_from_path(Path(file_path), allow_restore_case_files=True)

    def import_backup_from_path(
        self,
        file_path: Path,
        *,
        allow_restore_case_files: bool = False,
    ) -> None:
        """从指定备份文件发起导入，供文件关联/命令行入口复用。"""
        reply = QMessageBox.question(
            self,
            "确认导入",
            "导入备份会覆盖当前配置、案件台账和模板配置。系统会先保存当前配置快照。确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        restore_case_files = (
            allow_restore_case_files
            and self._restore_case_files_cb.isChecked()
        )
        case_files_target = None
        if restore_case_files:
            folder = QFileDialog.getExistingDirectory(
                self,
                "选择案件文件恢复目录",
                str(Path.home()),
                QFileDialog.Option.ShowDirsOnly,
            )
            if not folder:
                return
            case_files_target = Path(folder)

        self._import_backup_file(Path(file_path), restore_case_files, case_files_target)

    def _import_backup_file(
        self,
        file_path: Path,
        restore_case_files: bool,
        case_files_target: Optional[Path],
    ) -> None:
        """执行备份导入（后台线程）。"""
        self._start_backup_worker(
            "import",
            file_path=file_path,
            restore_case_files=restore_case_files,
            case_files_target=case_files_target,
        )

    def _start_backup_worker(self, action: str, **kwargs) -> None:
        """启动后台备份/导入工作线程。"""
        self._backup_thread = QThread(self)
        self._backup_worker = _BackupWorker(action, **kwargs)
        self._backup_worker.moveToThread(self._backup_thread)
        self._backup_thread.started.connect(self._backup_worker.run)
        self._backup_worker.finished.connect(self._on_backup_finished)
        self._backup_worker.failed.connect(self._on_backup_failed)
        self._backup_worker.finished.connect(self._backup_thread.quit)
        self._backup_worker.failed.connect(self._backup_thread.quit)
        self._backup_thread.finished.connect(self._backup_worker.deleteLater)
        self._backup_thread.finished.connect(self._cleanup_backup_thread)
        self._backup_thread.start()

    def _on_backup_finished(self, result) -> None:
        """备份/导入完成。"""
        QMessageBox.information(
            self,
            "操作完成",
            f"已处理 {result.files_written} 个文件。\n路径：{result.output_path if hasattr(result, 'output_path') else ''}",
        )

    def _on_backup_failed(self, error: str) -> None:
        """备份/导入失败。"""
        QMessageBox.warning(self, "操作失败", error)

    def _cleanup_backup_thread(self) -> None:
        """清理备份线程状态。"""
        self._backup_thread = None
        self._backup_worker = None

    def _on_rebuild_file_index(self) -> None:
        """手动后台重建文件搜索索引。"""
        if self._index_thread and self._index_thread.isRunning():
            return

        cases = [dict(case) for case in get_case_manager().get_all_cases()]
        if not cases:
            QMessageBox.information(self, "没有案件", "当前没有可建立索引的案件。")
            return

        self._rebuild_index_btn.setEnabled(False)
        self._rebuild_index_btn.setText("正在重建...")
        self._index_thread = QThread(self)
        self._index_worker = _SettingsFileIndexWorker(cases)
        self._index_worker.moveToThread(self._index_thread)
        self._index_thread.started.connect(self._index_worker.run)
        self._index_worker.finished.connect(self._on_rebuild_file_index_finished)
        self._index_worker.failed.connect(self._on_rebuild_file_index_failed)
        self._index_worker.finished.connect(self._index_thread.quit)
        self._index_worker.failed.connect(self._index_thread.quit)
        self._index_thread.finished.connect(self._index_worker.deleteLater)
        self._index_thread.finished.connect(self._cleanup_index_thread)
        self._index_thread.start()

    def _on_rebuild_file_index_finished(self, summary: Any) -> None:
        """文件索引重建完成。"""
        QMessageBox.information(
            self,
            "索引完成",
            f"已索引 {summary.cases_indexed} 个案件、{summary.files_indexed} 个文件。",
        )

    def _on_rebuild_file_index_failed(self, error: str) -> None:
        """文件索引重建失败。"""
        QMessageBox.warning(self, "索引失败", error)

    def _cleanup_index_thread(self) -> None:
        """清理索引线程状态。"""
        self._index_thread = None
        self._index_worker = None
        self._rebuild_index_btn.setEnabled(True)
        self._rebuild_index_btn.setText("重建文件索引")

    def _on_reset(self) -> None:
        """恢复默认设置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要恢复默认设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._config_manager.reset_config()
            self._load_settings()
            QMessageBox.information(self, "重置成功", "设置已恢复为默认值")

    def _on_save(self) -> None:
        """保存设置"""
        # 常规
        self._config_manager.set("app.check_updates", self._check_updates_cb.isChecked())

        # 生成
        self._config_manager.set(
            "generation.default_output_dir",
            self._output_dir_edit.text()
        )
        self._config_manager.set(
            "generation.auto_open_folder",
            self._auto_open_cb.isChecked()
        )
        self._config_manager.set(
            "generation.create_readme",
            self._create_readme_cb.isChecked()
        )

        # 界面
        self._config_manager.set("ui.window_width", self._width_spin.value())
        self._config_manager.set("ui.window_height", self._height_spin.value())
        self._config_manager.set("ui.show_preview", self._show_preview_cb.isChecked())

        # 日历导出
        cal_settings = self._config_manager.get("ui.calendar_export", {}) or {}
        directory = self._calendar_export_dir_edit.text()
        export_format = str(self._calendar_export_format_combo.currentData() or "pdf")
        theme = str(self._calendar_export_theme_combo.currentData() or "stream")
        cal_settings["last_directory"] = directory
        cal_settings["last_format"] = export_format
        cal_settings["last_theme"] = theme
        cal_settings["auto_export_on_close"] = self._calendar_auto_export_cb.isChecked()
        cal_settings["auto_export_scope"] = str(
            self._calendar_auto_export_scope_combo.currentData() or "future"
        )
        # 同步更新 quick_preset，确保「设置界面」与「自动导出」使用的格式一致
        preset = dict(cal_settings.get("quick_preset", {}) or {})
        preset["directory"] = directory
        preset["format"] = export_format
        preset["theme"] = theme
        cal_settings["quick_preset"] = preset
        self._config_manager.set("ui.calendar_export", cal_settings)

        QMessageBox.information(self, "保存成功", "设置已保存")
        self.accept()
