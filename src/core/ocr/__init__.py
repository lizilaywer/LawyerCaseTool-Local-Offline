# -*- coding: utf-8 -*-
"""OCR 模块 - 使用 RapidOCR"""

from .paddle_engine import (
    OCRAvailability,
    RapidOCREngine,
    PaddleOCREngine,
    format_ocr_setup_message,
    get_ocr_dependency_status,
    get_ocr_engine,
    get_ocr_runtime_status,
)
from .document_parser import DocumentParser, RecognitionResult, FieldConfidence, DocumentType
from .field_matcher import FieldMatcher

__all__ = [
    'RapidOCREngine',
    'PaddleOCREngine',  # 保留别名以兼容旧代码
    'OCRAvailability',
    'get_ocr_engine',
    'get_ocr_dependency_status',
    'get_ocr_runtime_status',
    'format_ocr_setup_message',
    'DocumentParser',
    'RecognitionResult',
    'FieldConfidence',
    'FieldMatcher',
    'DocumentType',
]
