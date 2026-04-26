# -*- coding: utf-8 -*-
"""营业执照解析器模块"""

from typing import List, Any

from ..document_parser import DocumentParser, DocumentType, RecognitionResult, FieldConfidence


class BusinessLicenseParser(DocumentParser):
    """营业执照解析器"""
    
    def __init__(self):
        super().__init__(DocumentType.BUSINESS_LICENSE)
    
    def parse(self, ocr_results: List[Any]) -> RecognitionResult:
        """解析营业执照 OCR 结果"""
        texts = []
        for block in ocr_results:
            text = getattr(block, 'text', str(block))
            texts.append(text)
        
        fields = {}
        
        # TODO: 实现营业执照解析逻辑
        # 包含：统一社会信用代码、名称、类型、住所、
        # 法定代表人、注册资本、成立日期、经营范围等
        
        overall_confidence = 0.0
        
        return RecognitionResult(
            document_type=self.document_type,
            fields=fields,
            raw_texts=texts,
            overall_confidence=overall_confidence
        )
