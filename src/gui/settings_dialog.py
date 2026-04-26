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
    # QFormLayout — 使用 TransparentFormLayout 替代
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QWidget,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QObject, QThread, Signal

from src.config.config_manager import get_config_manager
from src.core.backup import BackupService
from src.core.case_manager import get_case_manager
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

        layout.addWidget(tab_widget)

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

        QMessageBox.information(self, "保存成功", "设置已保存")
        self.accept()
