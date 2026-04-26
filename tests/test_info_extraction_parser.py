# -*- coding: utf-8 -*-
"""信息识别解析器选择测试"""

from src.core.ocr.document_parser import DocumentType
from src.gui.info_extraction_dialog import OCRWorker, UnknownDocumentParser


class TestInfoExtractionParserSelection:
    """OCR 解析器选择测试"""

    def test_unknown_type_uses_unknown_parser(self):
        worker = OCRWorker([])
        parser = worker._get_parser(DocumentType.UNKNOWN)
        assert isinstance(parser, UnknownDocumentParser)

    def test_unimplemented_type_uses_unknown_parser(self):
        worker = OCRWorker([])
        parser = worker._get_parser(DocumentType.HOUSEHOLD)
        assert isinstance(parser, UnknownDocumentParser)
