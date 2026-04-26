# -*- coding: utf-8 -*-
"""文档解析器基类模块"""

import re
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


class DocumentType(Enum):
    """文档类型枚举"""
    ID_CARD_FRONT = "id_card_front"          # 身份证正面
    ID_CARD_BACK = "id_card_back"            # 身份证反面
    HOUSEHOLD = "household"                  # 户口簿
    PASSPORT = "passport"                    # 护照
    DRIVING_LICENSE = "driving_license"      # 驾驶证
    BUSINESS_LICENSE = "business_license"    # 营业执照
    UNKNOWN = "unknown"                      # 未知类型


@dataclass
class FieldConfidence:
    """字段置信度信息"""
    value: str
    confidence: float
    raw_texts: List[str] = field(default_factory=list)  # 原始识别文本
    
    @property
    def is_high_confidence(self) -> bool:
        """是否高置信度 (>= 0.9)"""
        return self.confidence >= 0.9
    
    @property
    def is_medium_confidence(self) -> bool:
        """是否中等置信度 (0.8 - 0.9)"""
        return 0.8 <= self.confidence < 0.9
    
    @property
    def is_low_confidence(self) -> bool:
        """是否低置信度 (< 0.8)"""
        return self.confidence < 0.8
    
    @property
    def confidence_level(self) -> str:
        """获取置信度等级"""
        if self.is_high_confidence:
            return 'high'
        elif self.is_medium_confidence:
            return 'medium'
        else:
            return 'low'


@dataclass
class RecognitionResult:
    """识别结果"""
    document_type: DocumentType
    fields: Dict[str, FieldConfidence] = field(default_factory=dict)
    raw_texts: List[str] = field(default_factory=list)  # 所有原始文本
    image_path: str = ""
    recognition_time: datetime = field(default_factory=datetime.now)
    overall_confidence: float = 0.0
    
    def get_field(self, name: str) -> Optional[FieldConfidence]:
        """获取指定字段"""
        return self.fields.get(name)
    
    def get_field_value(self, name: str, default: str = "") -> str:
        """获取字段值"""
        field = self.fields.get(name)
        return field.value if field else default
    
    def get_all_low_confidence_fields(self) -> List[Tuple[str, FieldConfidence]]:
        """获取所有低置信度字段"""
        return [(name, field) for name, field in self.fields.items() if field.is_low_confidence]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'document_type': self.document_type.value,
            'fields': {
                name: {
                    'value': field.value,
                    'confidence': field.confidence,
                    'raw_texts': field.raw_texts
                }
                for name, field in self.fields.items()
            },
            'raw_texts': self.raw_texts,
            'image_path': self.image_path,
            'recognition_time': self.recognition_time.isoformat(),
            'overall_confidence': self.overall_confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecognitionResult':
        """从字典创建"""
        fields = {}
        for name, field_data in data.get('fields', {}).items():
            fields[name] = FieldConfidence(
                value=field_data['value'],
                confidence=field_data['confidence'],
                raw_texts=field_data.get('raw_texts', [])
            )
        
        return cls(
            document_type=DocumentType(data.get('document_type', 'unknown')),
            fields=fields,
            raw_texts=data.get('raw_texts', []),
            image_path=data.get('image_path', ''),
            recognition_time=datetime.fromisoformat(data['recognition_time']),
            overall_confidence=data.get('overall_confidence', 0.0)
        )


class DocumentParser(ABC):
    """文档解析器基类"""
    
    # 文档类型名称映射
    DOCUMENT_TYPE_NAMES = {
        DocumentType.ID_CARD_FRONT: '身份证（正面）',
        DocumentType.ID_CARD_BACK: '身份证（反面）',
        DocumentType.HOUSEHOLD: '居民户口簿',
        DocumentType.PASSPORT: '护照',
        DocumentType.DRIVING_LICENSE: '驾驶证',
        DocumentType.BUSINESS_LICENSE: '营业执照',
        DocumentType.UNKNOWN: '未知类型',
    }
    
    # 关键词映射，用于自动判断文档类型
    TYPE_KEYWORDS = {
        DocumentType.ID_CARD_FRONT: ['身份证', '公民身份号码', '姓名', '性别'],
        DocumentType.ID_CARD_BACK: ['身份证', '签发机关', '有效期限'],
        DocumentType.HOUSEHOLD: ['户口簿', '户主', '户别', '住址'],
        DocumentType.PASSPORT: ['护照', 'PASSPORT', '国籍', '护照号'],
        DocumentType.DRIVING_LICENSE: ['驾驶证', '证号', '准驾车型'],
        DocumentType.BUSINESS_LICENSE: ['营业执照', '统一社会信用代码'],
    }
    
    def __init__(self, document_type: DocumentType):
        """
        初始化解析器
        
        Args:
            document_type: 文档类型
        """
        self.document_type = document_type
    
    @abstractmethod
    def parse(self, ocr_results: List[Any]) -> RecognitionResult:
        """
        解析 OCR 结果
        
        Args:
            ocr_results: OCR 文本块列表
            
        Returns:
            RecognitionResult 识别结果
        """
        pass
    
    @classmethod
    def detect_document_type(cls, ocr_texts: List[str], filename: str = "") -> DocumentType:
        """
        根据 OCR 文本和文件名自动检测文档类型
        
        Args:
            ocr_texts: OCR 识别的文本列表
            filename: 文件名（可选）
            
        Returns:
            DocumentType 文档类型
        """
        # 首先根据文件名判断
        filename_lower = filename.lower()
        for doc_type, keywords in cls.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in filename_lower:
                    return doc_type
        
        # 根据内容判断
        text_combined = ' '.join(ocr_texts)
        scores = {}
        
        for doc_type, keywords in cls.TYPE_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text_combined:
                    score += 1
            if score > 0:
                scores[doc_type] = score
        
        if scores:
            # 返回得分最高的类型
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return DocumentType.UNKNOWN
    
    @staticmethod
    def extract_field_by_pattern(texts: List[str], pattern: str, group: int = 1) -> Optional[Tuple[str, float]]:
        """
        使用正则表达式从文本中提取字段
        
        Args:
            texts: 文本列表
            pattern: 正则表达式
            group: 捕获组索引
            
        Returns:
            (提取的值, 平均置信度) 或 None
        """
        for text in texts:
            match = re.search(pattern, text)
            if match:
                value = match.group(group).strip()
                if value:
                    return value, 0.85  # 默认置信度
        return None
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\-]', '', text)
        return text.strip()
    
    @staticmethod
    def extract_id_number(texts: List[str]) -> Optional[Tuple[str, float]]:
        """提取身份证号"""
        pattern = r'(\d{17}[\dXx]|\d{15})'
        for text in texts:
            match = re.search(pattern, text)
            if match:
                id_num = match.group(1).upper()
                # 简单校验
                if len(id_num) == 18 or len(id_num) == 15:
                    return id_num, 0.95
        return None
    
    @staticmethod
    def extract_date(texts: List[str]) -> Optional[Tuple[str, float]]:
        """提取日期（格式：YYYY-MM-DD 或 YYYY年MM月DD日）"""
        patterns = [
            r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日]?',
            r'(\d{4})(\d{2})(\d{2})',
        ]
        
        for text in texts:
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        year, month, day = groups
                        return f"{year}-{int(month):02d}-{int(day):02d}", 0.85
        return None
    
    def get_document_type_name(self) -> str:
        """获取文档类型名称"""
        return self.DOCUMENT_TYPE_NAMES.get(self.document_type, '未知类型')
