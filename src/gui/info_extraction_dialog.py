# -*- coding: utf-8 -*-
"""信息识别对话框模块"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QMessageBox, QProgressBar,
    QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QThread, Slot

from src.core.ocr import (
    FieldMatcher,
    format_ocr_setup_message,
    get_ocr_dependency_status,
    get_ocr_engine,
    get_ocr_runtime_status,
)
from src.core.ocr.document_parser import DocumentParser, RecognitionResult, DocumentType
from src.core.ocr.parsers import (
    IDCardFrontParser, IDCardBackParser, HouseholdParser,
    PassportParser, LicenseParser, BusinessLicenseParser
)
from src.core.data.info_storage import InfoStorage, ExtractionRecord
from src.utils.pdf_utils import get_pdf_processor
from src.utils.logger import get_logger
from src.gui.styles import APP_COLORS as COLORS, button_style, hint_banner_style
from src.gui.widgets.image_list_widget import ImageListWidget
from src.gui.widgets.ocr_result_widget import OCRResultWidget

# 模块级 logger
logger = get_logger()

DEFAULT_HINT_TEXT = "💡 添加身份证、户口簿、护照等图片或 PDF 文件，系统将自动识别信息"
INFO_HINT_STYLE = hint_banner_style("info")
WARNING_HINT_STYLE = hint_banner_style("warning")
SUCCESS_HINT_STYLE = hint_banner_style("success")


class OCRWorker(QThread):
    """OCR 识别工作线程"""
    
    # 信号
    progress = Signal(int, str)           # 进度 (百分比, 状态信息)
    file_completed = Signal(str, object)  # 单个文件完成 (文件路径, 识别结果)
    all_completed = Signal()              # 全部完成
    error_occurred = Signal(str, str)     # 错误 (文件路径, 错误信息)
    
    def __init__(self, file_paths: List[str], parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self._is_cancelled = False
    
    def cancel(self):
        """取消识别"""
        self._is_cancelled = True
    
    def run(self):
        """执行识别"""
        ocr_engine = get_ocr_engine()
        pdf_processor = get_pdf_processor()
        
        if not ocr_engine.is_ready():
            self.error_occurred.emit("", format_ocr_setup_message(get_ocr_runtime_status()))
            return
        
        total = len(self.file_paths)
        
        for idx, file_path in enumerate(self.file_paths):
            if self._is_cancelled:
                break
            
            self.progress.emit(
                int((idx / total) * 100),
                f"正在识别: {Path(file_path).name} ({idx + 1}/{total})"
            )
            
            try:
                result = self._process_single_file(file_path, ocr_engine, pdf_processor)
                if result:
                    self.file_completed.emit(file_path, result)
                else:
                    self.error_occurred.emit(file_path, "识别失败")
                    
            except Exception as e:
                self.error_occurred.emit(file_path, str(e))
        
        self.progress.emit(100, "识别完成")
        self.all_completed.emit()
    
    def _process_single_file(self, file_path: str, ocr_engine, pdf_processor) -> Optional[RecognitionResult]:
        """处理单个文件"""
        from pathlib import Path
        
        ext = Path(file_path).suffix.lower()
        image_paths = []
        
        # 如果是 PDF，先转换为图片
        if ext == '.pdf':
            if not pdf_processor.is_available():
                raise Exception("PDF 处理依赖未安装")
            
            temp_dir = Path(tempfile.gettempdir()) / 'ocr_temp'
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            image_paths = pdf_processor.convert_to_images(
                file_path, 
                str(temp_dir),
                page_range=(1, 1)  # 只处理第一页
            )
        else:
            image_paths = [file_path]
        
        if not image_paths:
            return None
        
        # OCR 识别
        ocr_results = ocr_engine.recognize(image_paths[0])
        
        if not ocr_results:
            logger.debug(f"OCR 未识别到任何文本: {file_path}")
            return None
        
        logger.debug(f"OCR 识别到 {len(ocr_results)} 个文本块")
        for i, block in enumerate(ocr_results[:5]):  # 只显示前5个
            logger.debug(f"  [{i}] {block.text} (置信度: {block.confidence})")
        
        # 自动检测文档类型
        texts = [block.text for block in ocr_results]
        doc_type = DocumentParser.detect_document_type(texts, Path(file_path).name)
        logger.debug(f"检测到文档类型: {doc_type}")
        
        # 根据类型选择解析器
        parser = self._get_parser(doc_type)
        
        # 解析结果
        result = parser.parse(ocr_results)
        result.image_path = file_path
        
        logger.debug(f"解析完成，提取字段数: {len(result.fields)}")
        
        return result

    def _get_parser(self, doc_type: DocumentType) -> DocumentParser:
        """获取对应类型的解析器"""
        parsers = {
            DocumentType.ID_CARD_FRONT: IDCardFrontParser(),
            DocumentType.ID_CARD_BACK: IDCardBackParser(),
            DocumentType.HOUSEHOLD: HouseholdParser(),
            DocumentType.PASSPORT: PassportParser(),
            DocumentType.DRIVING_LICENSE: LicenseParser(),
            DocumentType.BUSINESS_LICENSE: BusinessLicenseParser(),
        }

        # 已知仍未完整实现的解析器先回退到“未知类型”，避免误导性字段输出
        unimplemented_types = {
            DocumentType.HOUSEHOLD,
            DocumentType.PASSPORT,
            DocumentType.DRIVING_LICENSE,
            DocumentType.BUSINESS_LICENSE,
        }
        if doc_type in unimplemented_types:
            logger.warning(f"文档类型 {doc_type.value} 解析器未完整实现，回退为未知类型")
            return UnknownDocumentParser()

        parser = parsers.get(doc_type)
        if parser is None:
            logger.warning(f"文档类型 {doc_type.value} 无匹配解析器，回退为未知类型")
            return UnknownDocumentParser()
        return parser


class UnknownDocumentParser(DocumentParser):
    """兜底解析器：未知/未实现类型仅保留原始文本，避免误导字段。"""

    def __init__(self):
        super().__init__(DocumentType.UNKNOWN)

    def parse(self, ocr_results: List[Any]) -> RecognitionResult:
        texts = [getattr(block, "text", str(block)) for block in ocr_results]
        return RecognitionResult(
            document_type=self.document_type,
            fields={},
            raw_texts=texts,
            overall_confidence=0.0,
        )


class InfoExtractionDialog(QDialog):
    """信息识别对话框"""
    
    # 信号
    data_applied = Signal(dict)  # 数据应用到案卷信号
    
    # 被告/被申请人模板中，对方当事人姓名(名称)直接映射到现有变量
    OPPONENT_DIRECT_MAP = {
        "civil_simple_002": "plaintiff_name",       # 民事(被告) → 原告名称
        "admin_simple_002": "plaintiff_name",       # 行政(被告) → 原告名称
        "labor_simple_002": "applicant_name",       # 劳动仲裁(被申请人) → 申请人姓名
        "commercial_simple_002": "applicant_name",  # 商事仲裁(被申请人) → 申请人名称
    }

    def __init__(self, template_vars: Optional[List[Dict[str, Any]]] = None,
                 template_id: Optional[str] = None,
                 parent: Optional[QWidget] = None):
        """
        初始化信息识别对话框

        Args:
            template_vars: 当前模板的变量定义列表
            template_id: 当前模板 ID
            parent: 父窗口
        """
        super().__init__(parent)

        self.setWindowTitle("信息识别")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['surface_1']}; }}")

        self._template_vars = template_vars or []
        self._template_id = template_id or ""
        self._logger = get_logger()
        self._storage = InfoStorage()
        self._field_matcher = FieldMatcher()
        
        # 识别结果存储
        self._recognition_results: Dict[str, RecognitionResult] = {}
        self._current_file: Optional[str] = None
        
        # OCR 工作线程
        self._ocr_worker: Optional[OCRWorker] = None
        
        self._setup_ui()
        self._refresh_ocr_ui_state()
    
    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 顶部提示栏
        self._hint_bar = QLabel(DEFAULT_HINT_TEXT)
        self._hint_bar.setStyleSheet(INFO_HINT_STYLE)
        layout.addWidget(self._hint_bar)
        
        # 主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {COLORS['border']};
                width: 1px;
            }}
        """)
        
        # 左侧：图片列表
        self._image_list = ImageListWidget()
        self._image_list.image_added.connect(self._on_image_added)
        self._image_list.image_removed.connect(self._on_image_removed)
        self._image_list.image_selected.connect(self._on_image_selected)
        self._image_list.images_changed.connect(self._on_images_changed)
        splitter.addWidget(self._image_list)
        
        # 右侧：识别结果展示
        self._result_widget = OCRResultWidget()
        self._result_widget.field_edited.connect(self._on_field_edited)
        self._result_widget.apply_to_template.connect(self._on_apply_to_template)
        self._result_widget.export_requested.connect(self._on_export_requested)
        self._result_widget.re_recognize_requested.connect(self._on_re_recognize)
        splitter.addWidget(self._result_widget)
        
        # 设置分割器比例
        splitter.setSizes([300, 500])
        layout.addWidget(splitter, 1)
        
        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        
        self._recognize_btn = QPushButton("开始识别")
        self._recognize_btn.setStyleSheet(button_style(primary=True))
        self._recognize_btn.clicked.connect(self._start_recognition)
        btn_layout.addWidget(self._recognize_btn)
        
        # 重新识别按钮（与开始识别对齐，初始隐藏）
        self._re_recognize_btn = QPushButton("重新识别")
        self._re_recognize_btn.setStyleSheet(button_style(warning=True))
        self._re_recognize_btn.clicked.connect(self._on_re_recognize)
        self._re_recognize_btn.setVisible(False)  # 初始隐藏，有识别结果后显示
        btn_layout.addWidget(self._re_recognize_btn)
        
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setStyleSheet(button_style())
        self._cancel_btn.clicked.connect(self._cancel_recognition)
        self._cancel_btn.setVisible(False)
        btn_layout.addWidget(self._cancel_btn)

        self._ocr_help_btn = QPushButton("安装说明")
        self._ocr_help_btn.setStyleSheet(button_style())
        self._ocr_help_btn.clicked.connect(self._show_ocr_setup_guide)
        self._ocr_help_btn.setVisible(False)
        btn_layout.addWidget(self._ocr_help_btn)
        
        btn_layout.addStretch()
        
        # 是否为对方当事人复选框
        self._opponent_checkbox = QCheckBox("是否为对方当事人")
        self._opponent_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-size: 12px;
                color: {COLORS['text_secondary']};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)
        self._opponent_checkbox.setToolTip("勾选后，识别生成的变量名将添加'opponent_'前缀以区分")
        btn_layout.addWidget(self._opponent_checkbox)
        
        btn_layout.addSpacing(16)  # 添加间距保持对齐
        
        # 历史记录按钮
        history_btn = QPushButton("历史记录")
        history_btn.setStyleSheet(button_style())
        history_btn.clicked.connect(self._show_history)
        btn_layout.addWidget(history_btn)

        self._close_btn = QPushButton("关闭")
        self._close_btn.setStyleSheet(button_style())
        self._close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._close_btn)

        self._save_apply_btn = QPushButton("保存并应用到案卷")
        self._save_apply_btn.setStyleSheet(button_style(success=True))
        self._save_apply_btn.clicked.connect(self._save_and_apply)
        btn_layout.addWidget(self._save_apply_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_image_added(self, file_path: str):
        """图片添加事件"""
        self._logger.debug(f"添加图片: {file_path}")
    
    def _on_image_removed(self, file_path: str):
        """图片移除事件"""
        if file_path in self._recognition_results:
            del self._recognition_results[file_path]
        self._logger.debug(f"移除图片: {file_path}")
    
    def _on_image_selected(self, file_path: str):
        """图片选中事件"""
        self._current_file = file_path
        
        # 显示对应的识别结果
        if file_path in self._recognition_results:
            result = self._recognition_results[file_path]
            self._result_widget.set_result(result, self._template_vars)
        else:
            self._result_widget.clear()
    
    def _on_images_changed(self, file_paths: List[str]):
        """图片列表变化事件"""
        has_images = len(file_paths) > 0
        if get_ocr_dependency_status().available:
            self._recognize_btn.setEnabled(has_images)
        else:
            self._recognize_btn.setEnabled(False)

    def _refresh_ocr_ui_state(self) -> None:
        """刷新 OCR 可用性相关 UI 状态。"""
        status = get_ocr_dependency_status()
        has_images = len(self._image_list.get_all_files()) > 0

        if status.available:
            self._hint_bar.setText(DEFAULT_HINT_TEXT)
            self._hint_bar.setStyleSheet(INFO_HINT_STYLE)
            self._recognize_btn.setText("开始识别")
            self._recognize_btn.setEnabled(has_images)
            self._ocr_help_btn.setVisible(False)
            self._re_recognize_btn.setEnabled(True)
            return

        self._hint_bar.setText(f"{status.summary}。点击“安装说明”查看处理方式。")
        self._hint_bar.setStyleSheet(WARNING_HINT_STYLE)
        self._recognize_btn.setText("OCR 不可用")
        self._recognize_btn.setEnabled(False)
        self._ocr_help_btn.setVisible(True)
        self._re_recognize_btn.setEnabled(False)

    def _show_ocr_setup_guide(self) -> None:
        """显示 OCR 安装说明。"""
        status = get_ocr_runtime_status()
        QMessageBox.information(
            self,
            "OCR 增强能力说明",
            format_ocr_setup_message(status)
        )
    
    def _start_recognition(self):
        """开始识别"""
        files = self._image_list.get_all_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先添加图片或 PDF 文件")
            return
        
        # 清除之前的识别结果
        self._recognition_results.clear()
        self._result_widget.clear()
        
        # 开始识别所有文件
        self._start_recognition_for_files(files)
    
    def _cancel_recognition(self):
        """取消识别"""
        if self._ocr_worker and self._ocr_worker.isRunning():
            self._ocr_worker.cancel()
            self._ocr_worker.wait(3000)
        
        self._progress_bar.setVisible(False)
        self._recognize_btn.setVisible(True)
        self._cancel_btn.setVisible(False)
    
    @Slot(int, str)
    def _on_recognition_progress(self, percentage: int, message: str):
        """识别进度更新"""
        self._progress_bar.setValue(percentage)
        self._hint_bar.setText(message)
    
    def _on_re_recognize(self):
        """重新识别当前选中的文件"""
        current_file = self._image_list.get_selected_file()
        if not current_file:
            QMessageBox.warning(self, "警告", "请先选择要重新识别的文件")
            return
        
        # 清除该文件的旧识别结果
        if current_file in self._recognition_results:
            del self._recognition_results[current_file]
        
        # 开始识别单个文件
        self._start_recognition_for_files([current_file])
    
    def _start_recognition_for_files(self, file_paths: List[str]):
        """识别指定文件列表"""
        # 检查 OCR 引擎
        runtime_status = get_ocr_runtime_status()
        if not runtime_status.available:
            self._hint_bar.setText(f"{runtime_status.summary}。点击“安装说明”查看处理方式。")
            self._hint_bar.setStyleSheet(WARNING_HINT_STYLE)
            self._show_ocr_setup_guide()
            self._refresh_ocr_ui_state()
            return
        
        # 创建并启动工作线程
        self._ocr_worker = OCRWorker(file_paths)
        self._ocr_worker.progress.connect(self._on_recognition_progress)
        self._ocr_worker.file_completed.connect(self._on_file_recognized)
        self._ocr_worker.all_completed.connect(self._on_recognition_completed)
        self._ocr_worker.error_occurred.connect(self._on_recognition_error)
        
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._recognize_btn.setVisible(False)
        self._re_recognize_btn.setVisible(False)
        self._cancel_btn.setVisible(True)
        
        self._ocr_worker.start()
    
    @Slot(str, object)
    def _on_file_recognized(self, file_path: str, result: RecognitionResult):
        """单个文件识别完成"""
        self._recognition_results[file_path] = result
        
        # 更新图片列表中的文档类型
        self._image_list.set_document_type(file_path, result.document_type)
        
        # 显示重新识别按钮（如果有识别结果）
        if self._recognition_results:
            self._re_recognize_btn.setVisible(True)
        
        # 调试日志
        self._logger.debug(f"识别结果字段数: {len(result.fields)}")
        self._logger.debug(f"识别原始文本: {result.raw_texts[:5] if result.raw_texts else 'None'}")
        for name, field_conf in result.fields.items():
            self._logger.debug(f"  字段 {name}: {field_conf.value} (置信度: {field_conf.confidence})")
        
        # 如果是当前选中的文件，显示结果
        if file_path == self._current_file:
            self._result_widget.set_result(result, self._template_vars)
        
        self._logger.info(f"文件识别完成: {file_path}, 类型: {result.document_type}, 字段数: {len(result.fields)}")
    
    @Slot()
    def _on_recognition_completed(self):
        """全部识别完成"""
        self._progress_bar.setVisible(False)
        self._recognize_btn.setVisible(True)
        self._cancel_btn.setVisible(False)
        
        # 如果有识别结果，显示重新识别按钮
        if self._recognition_results:
            self._re_recognize_btn.setVisible(True)
        
        success_count = len(self._recognition_results)
        total_count = len(self._image_list.get_all_files())
        
        self._hint_bar.setText(
            f"✅ 识别完成！成功: {success_count}/{total_count} 个文件"
        )
        self._hint_bar.setStyleSheet(SUCCESS_HINT_STYLE)
        
        # 自动显示第一个结果
        if self._recognition_results:
            first_file = list(self._recognition_results.keys())[0]
            self._current_file = first_file
            self._image_list.setCurrentItemByPath(first_file)
            # 显示第一个结果
            result = self._recognition_results[first_file]
            self._result_widget.set_result(result, self._template_vars)
    
    @Slot(str, str)
    def _on_recognition_error(self, file_path: str, error_msg: str):
        """识别错误"""
        self._logger.error(f"识别失败 {file_path}: {error_msg}")
        if file_path:
            QMessageBox.warning(
                self,
                "识别失败",
                f"文件: {Path(file_path).name}\n错误: {error_msg}"
            )
        else:
            QMessageBox.critical(self, "错误", error_msg)
    
    def _on_field_edited(self, field_name: str, new_value: str):
        """字段编辑事件"""
        if self._current_file and self._current_file in self._recognition_results:
            result = self._recognition_results[self._current_file]
            if field_name in result.fields:
                result.fields[field_name].value = new_value
    
    def _on_apply_to_template(self, values: Dict[str, str]):
        """应用到模板变量"""
        if not self._current_file:
            return
        
        result = self._recognition_results.get(self._current_file)
        if not result:
            return
        
        # 使用字段匹配器获取所有映射（包括未匹配的）
        matches = self._field_matcher.match_all(result, self._template_vars)
        
        if not matches:
            QMessageBox.information(
                self,
                "未匹配到变量",
                "当前识别结果与模板变量未自动匹配，请手动复制需要的信息。"
            )
            return
        
        # 检查是否为对方当事人
        is_opponent = self._opponent_checkbox.isChecked()
        # 被告模板中对方姓名直接映射到原告/申请人变量
        direct_target = self.OPPONENT_DIRECT_MAP.get(self._template_id) if is_opponent else None

        # 构建应用数据
        apply_data = {}
        new_vars = []
        matched_count = 0
        new_count = 0

        for var_key, (value, _, match_type) in matches.items():
            if is_opponent:
                if direct_target and var_key == "client_name":
                    # 被告模板：对方姓名直接映射到原告/申请人变量
                    var_key = direct_target
                else:
                    var_key = f"opponent_{var_key}"

            apply_data[var_key] = value
            if match_type == 'matched':
                matched_count += 1
            else:
                new_count += 1
                # 获取字段标签
                label = self._field_matcher.get_recognized_field_label(
                    var_key, result.document_type
                )
                if is_opponent:
                    if direct_target and var_key == direct_target:
                        # 直接映射到现有变量，不需要特殊标签
                        pass
                    elif var_key == 'opponent_client_name':
                        label = "对方姓名(名称)"
                    else:
                        label = f"对方{label}"
                new_vars.append({
                    'key': var_key,
                    'label': label,
                    'value': value,
                    'source_field': var_key
                })

        # 构建详细信息
        prefix_info = "（对方当事人）" if is_opponent else ""
        detail_msg = f"已自动填充 {len(apply_data)} 个变量{prefix_info}到案卷表单。\n\n"
        if matched_count > 0:
            detail_msg += f"匹配现有变量: {matched_count} 个\n"
        if new_count > 0:
            detail_msg += f"创建新变量: {new_count} 个\n"
        if is_opponent:
            if direct_target:
                detail_msg += f"\n对方姓名已直接填入对应变量"
            else:
                detail_msg += f"\n变量名已添加 'opponent_' 前缀"

        # 发送数据，包括新变量信息
        self.data_applied.emit(apply_data)

        QMessageBox.information(self, "应用成功", detail_msg)
    
    def _on_export_requested(self, export_type: str):
        """导出请求"""
        if not self._recognition_results:
            QMessageBox.warning(self, "警告", "没有识别结果可导出")
            return
        
        # 这里实现导出逻辑
        if export_type == 'json':
            self._export_to_json()
        elif export_type == 'excel':
            self._export_to_excel()
        elif export_type == 'word':
            self._export_to_word()
    
    def _export_to_json(self):
        """导出为 JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为 JSON",
            "ocr_result.json",
            "JSON 文件 (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            data = {
                'export_time': datetime.now().isoformat(),
                'results': {
                    path: result.to_dict()
                    for path, result in self._recognition_results.items()
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "成功", f"已导出到: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
    
    def _export_to_excel(self):
        """导出为 Excel"""
        # TODO: 实现 Excel 导出
        QMessageBox.information(self, "提示", "Excel 导出功能开发中")
    
    def _export_to_word(self):
        """导出为 Word"""
        # TODO: 实现 Word 导出
        QMessageBox.information(self, "提示", "Word 导出功能开发中")
    
    def _save_and_apply(self):
        """保存并应用到案卷"""
        if not self._recognition_results:
            QMessageBox.warning(self, "警告", "没有识别结果")
            return
        
        # 保存到存储
        record = ExtractionRecord(
            id=f"ext_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.now(),
            results=list(self._recognition_results.values())
        )
        self._storage.save_record(record)
        
        # 应用所有匹配的数据（包括未匹配的字段）
        all_matches = {}
        matched_count = 0
        new_count = 0
        
        # 检查是否为对方当事人
        is_opponent = self._opponent_checkbox.isChecked()
        direct_target = self.OPPONENT_DIRECT_MAP.get(self._template_id) if is_opponent else None

        for file_path, result in self._recognition_results.items():
            matches = self._field_matcher.match_all(result, self._template_vars)
            for var_key, (value, _, match_type) in matches.items():
                if is_opponent:
                    if direct_target and var_key == "client_name":
                        var_key = direct_target
                    else:
                        var_key = f"opponent_{var_key}"

                if var_key not in all_matches:  # 避免覆盖
                    all_matches[var_key] = value
                    if match_type == 'matched':
                        matched_count += 1
                    else:
                        new_count += 1

        if all_matches:
            self.data_applied.emit(all_matches)

            # 构建详细信息
            prefix_info = "（对方当事人）" if is_opponent else ""
            detail_msg = f"已保存识别记录，并自动填充 {len(all_matches)} 个变量{prefix_info}到案卷表单。\n\n"
            if matched_count > 0:
                detail_msg += f"匹配现有变量: {matched_count} 个\n"
            if new_count > 0:
                detail_msg += f"创建新变量: {new_count} 个"
            if is_opponent:
                if direct_target:
                    detail_msg += f"\n对方姓名已直接填入对应变量"
                else:
                    detail_msg += f"\n变量名已添加 'opponent_' 前缀"
            
            QMessageBox.information(self, "保存成功", detail_msg)
        else:
            QMessageBox.information(
                self,
                "保存成功",
                "识别记录已保存，但未匹配到可自动填充的变量。"
            )
        
        self.accept()
    
    def _show_history(self):
        """显示历史记录"""
        # TODO: 实现历史记录对话框
        QMessageBox.information(self, "提示", "历史记录功能开发中")
    
    def get_applied_data(self) -> Dict[str, str]:
        """获取已应用的数据"""
        # 由调用者通过 data_applied 信号接收
        return {}

    def closeEvent(self, event) -> None:
        """关闭时取消 OCR 工作线程。"""
        if self._ocr_worker and self._ocr_worker.isRunning():
            self._ocr_worker.cancel()
            self._ocr_worker.wait(3000)
        event.accept()
