# -*- coding: utf-8 -*-
"""生成对话框模块"""

from pathlib import Path
from typing import Any, Dict

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QFileDialog,
    QGroupBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from src.core.batch_processor import BatchProcessor
from src.config.config_manager import get_config_manager
from src.gui.styles import APP_COLORS as COLORS, button_style, hint_banner_style
from src.utils.logger import get_logger
from src.utils.platform_utils import get_default_output_dir, open_path


class GenerationWorker(QThread):
    """生成工作线程"""

    progress = Signal(int, int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        template_config: Dict[str, Any],
        values: Dict[str, Any],
        output_dir: Path
    ):
        super().__init__()
        self._template_config = template_config
        self._values = values
        self._output_dir = output_dir
        self._processor = BatchProcessor()

    def run(self) -> None:
        """运行生成任务"""
        try:
            self._processor.set_progress_callback(self._on_progress)

            result = self._processor.process_single(
                self._template_config,
                self._values,
                self._output_dir,
                process_template=True
            )

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, current: int, total: int, message: str) -> None:
        """进度回调"""
        self.progress.emit(current, total, message)

    def cancel(self) -> None:
        """取消任务"""
        self._processor.cancel()


class GenerationDialog(QDialog):
    """生成对话框"""

    def __init__(
        self,
        template_config: Dict[str, Any],
        values: Dict[str, Any],
        parent=None
    ):
        super().__init__(parent)
        self._template_config = template_config
        self._values = values
        self._config_manager = get_config_manager()
        self._logger = get_logger()
        self._worker = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        self.setWindowTitle("生成案卷")
        self.setMinimumSize(560, 460)
        self.resize(680, 540)
        self.setModal(True)
        self.setStyleSheet(f"QDialog {{ background: {c['surface_1']}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        banner = QLabel("生成前可再次确认输出目录与案卷名称，进度和日志会在下方实时更新。")
        banner.setWordWrap(True)
        banner.setStyleSheet(hint_banner_style("info"))
        layout.addWidget(banner)

        # 输出目录选择
        dir_group = QGroupBox("输出目录")
        dir_group.setProperty("card", True)
        dir_layout = QHBoxLayout(dir_group)
        dir_layout.setContentsMargins(16, 18, 16, 16)

        self._dir_label = QLabel()
        self._dir_label.setWordWrap(True)
        self._dir_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_secondary']};
            font-size: 12px;
            line-height: 1.5;
        """)
        default_dir = self._config_manager.get(
            "generation.default_output_dir",
            str(get_default_output_dir())
        ) or str(get_default_output_dir())
        self._output_dir = Path(default_dir)
        self._update_dir_label()

        dir_layout.addWidget(self._dir_label, 1)

        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet(button_style(compact=True))
        browse_btn.clicked.connect(self._on_browse)
        dir_layout.addWidget(browse_btn)

        layout.addWidget(dir_group)

        # 案卷信息
        info_group = QGroupBox("案卷信息")
        info_group.setProperty("card", True)
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(16, 18, 16, 16)
        info_layout.setSpacing(6)

        template_name = self._template_config.get("name", "")
        info_layout.addWidget(QLabel(f"模板：{template_name}"))

        root_name = self._template_config.get("folder_structure", {}).get("root_name", "")
        from src.core.variable_parser import VariableParser
        parser = VariableParser()
        resolved_name = parser.replace_variables(root_name, self._values, sanitize=True)
        case_name = QLabel(f"案卷名称：{resolved_name}")
        case_name.setWordWrap(True)
        case_name.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 700;
        """)
        info_layout.addWidget(case_name)

        layout.addWidget(info_group)

        # 进度
        progress_group = QGroupBox("生成进度")
        progress_group.setProperty("card", True)
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(16, 18, 16, 16)
        progress_layout.setSpacing(10)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("准备就绪")
        self._status_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_secondary']};
            font-size: 12px;
            font-weight: 600;
        """)
        progress_layout.addWidget(self._status_label)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(180)
        progress_layout.addWidget(self._log_text)

        layout.addWidget(progress_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setStyleSheet(button_style())
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._generate_btn = QPushButton("开始生成")
        self._generate_btn.setStyleSheet(button_style(primary=True))
        self._generate_btn.clicked.connect(self._on_generate)
        btn_layout.addWidget(self._generate_btn)

        self._close_btn = QPushButton("关闭")
        self._close_btn.setStyleSheet(button_style())
        self._close_btn.clicked.connect(self.accept)
        self._close_btn.setVisible(False)
        btn_layout.addWidget(self._close_btn)

        layout.addLayout(btn_layout)

    def _update_dir_label(self) -> None:
        """更新目录标签"""
        self._dir_label.setText(str(self._output_dir))

    def _on_browse(self) -> None:
        """浏览目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            str(self._output_dir)
        )
        if dir_path:
            self._output_dir = Path(dir_path)
            self._update_dir_label()

    def _on_generate(self) -> None:
        """开始生成"""
        self._generate_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._log_text.clear()

        # 创建工作线程
        self._worker = GenerationWorker(
            self._template_config,
            self._values,
            self._output_dir
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

        self._log("开始生成案卷...")

    def _on_cancel(self) -> None:
        """取消生成"""
        if self._worker:
            self._worker.cancel()
            self._cancel_btn.setEnabled(False)
            self._status_label.setText("正在取消...")
            self._log("正在取消...")

    def _on_progress(self, current: int, total: int, message: str) -> None:
        """进度更新"""
        if total > 0:
            progress = int(current / total * 100)
            self._progress_bar.setValue(progress)
        self._status_label.setText(message)
        self._log(message)

    def _on_finished(self, result: Dict[str, Any]) -> None:
        """生成完成"""
        self._generate_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

        if result.get("cancelled"):
            self._status_label.setText("已取消")
            self._log("生成已取消")

            self._generate_btn.setVisible(False)
            self._cancel_btn.setVisible(False)
            self._close_btn.setVisible(True)

            QMessageBox.information(self, "已取消", "生成任务已取消。")
            return

        if result.get("success"):
            self._progress_bar.setValue(100)
            self._status_label.setText("生成成功!")
            self._log(f"案卷已生成: {result.get('root_path')}")

            # 显示关闭按钮
            self._generate_btn.setVisible(False)
            self._cancel_btn.setVisible(False)
            self._close_btn.setVisible(True)

            # 自动打开文件夹
            root_path = result.get("root_path")
            if root_path and self._config_manager.get("generation.auto_open_folder", True):
                ok, error = open_path(root_path)
                if not ok:
                    self._logger.warning(f"自动打开文件夹失败: {error}")

            # 自动注册案件 + 创建速记文件
            if root_path:
                try:
                    from src.core.case_manager import get_case_manager
                    cm = get_case_manager()
                    cm.register_case({
                        'name': Path(root_path).name,
                        'path': root_path,
                        'category': self._template_config.get("category", ""),
                        'template_id': self._template_config.get("id", ""),
                        'variables': self._values,
                    })
                    case_notes_dir = Path(root_path) / ".case"
                    case_notes_dir.mkdir(exist_ok=True)
                    notes_file = case_notes_dir / "notes.md"
                    if not notes_file.exists():
                        notes_file.write_text("# 案件速记\n\n", encoding='utf-8')
                except Exception as e:
                    self._logger.warning(f"自动注册案件失败: {e}")

            QMessageBox.information(
                self,
                "成功",
                f"案卷已成功生成!\n\n位置: {result.get('root_path')}"
            )
        else:
            self._status_label.setText("生成失败")
            self._log(f"错误: {result.get('error')}")

            QMessageBox.critical(
                self,
                "错误",
                f"生成失败:\n{result.get('error')}"
            )

    def _on_error(self, error_msg: str) -> None:
        """错误处理"""
        self._generate_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._status_label.setText("发生错误")
        self._log(f"错误: {error_msg}")

        QMessageBox.critical(self, "错误", f"发生错误:\n{error_msg}")

    def _log(self, message: str) -> None:
        """添加日志"""
        self._log_text.append(message)

    def closeEvent(self, event) -> None:
        """关闭事件"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)

        event.accept()
