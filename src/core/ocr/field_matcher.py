# -*- coding: utf-8 -*-
"""字段匹配器模块 - 将 OCR 识别结果映射到模板变量"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .document_parser import RecognitionResult, FieldConfidence, DocumentType


@dataclass
class FieldMapping:
    """字段映射关系"""
    source_field: str          # 识别结果中的字段名
    target_variable: str       # 模板变量名
    confidence: float          # 匹配置信度
    transform_func: Optional[callable] = None  # 可选的转换函数


class FieldMatcher:
    """
    字段匹配器
    
    将 OCR 识别结果自动映射到模板变量
    """
    
    # 默认字段映射表
    # key: 识别字段名, value: 可能匹配的模板变量名列表（按优先级排序）
    DEFAULT_MAPPINGS = {
        # 身份证/个人信息
        'name': ['client_name', '委托人姓名', '当事人姓名', '姓名', 'name', '委托人'],
        'gender': ['client_gender', '委托人性别', '性别', 'gender'],
        'ethnicity': ['client_ethnicity', '委托人民族', '民族', 'ethnicity'],
        'birth_date': ['client_birth_date', '委托人出生日期', '出生日期', 'birth_date', '出生年月'],
        'address': ['client_address', '委托人住址', '住址', 'address', '地址', '住所'],
        'id_number': ['client_id_number', '委托人身份证号', '身份证号', 'id_number', '身份证号码', '公民身份号码'],
        
        # 身份证反面
        'issuer': ['id_issuer', '签发机关', 'issuer'],
        'validity_period': ['id_validity', '有效期限', 'validity_period'],
        
        # 案件信息
        'case_number': ['case_number', '案号', '案件编号'],
        'case_type': ['case_type', '案件类型', '案由'],
        'court': ['court_name', '法院', '受理法院'],
        
        # 企业信息
        'company_name': ['company_name', '企业名称', '公司名称', '名称'],
        'credit_code': ['credit_code', '统一社会信用代码'],
        'legal_representative': ['legal_representative', '法定代表人', '法人'],
        'registered_capital': ['registered_capital', '注册资本'],
        'establishment_date': ['establishment_date', '成立日期'],
        
        # 律师信息
        'lawyer_name': ['lawyer_name', '承办律师', '律师姓名'],
    }
    
    def __init__(self, custom_mappings: Optional[Dict[str, List[str]]] = None):
        """
        初始化字段匹配器
        
        Args:
            custom_mappings: 自定义映射表，会覆盖默认映射
        """
        self.mappings = self.DEFAULT_MAPPINGS.copy()
        if custom_mappings:
            self.mappings.update(custom_mappings)
    
    def match(self, recognition_result: RecognitionResult, 
              template_variables: List[Dict[str, Any]]) -> Dict[str, Tuple[str, FieldConfidence]]:
        """
        将识别结果匹配到模板变量
        
        Args:
            recognition_result: OCR 识别结果
            template_variables: 模板变量定义列表
            
        Returns:
            {模板变量key: (匹配值, 原始字段置信度)}
        """
        matches = {}
        
        # 提取模板变量的 key 和 label
        var_keys = [var['key'] for var in template_variables]
        var_labels = {var['key']: var.get('label', var['key']) for var in template_variables}
        
        # 遍历识别结果的字段
        for source_field, field_conf in recognition_result.fields.items():
            # 查找匹配的模板变量
            matched_var = self._find_best_match(
                source_field, 
                field_conf.value,
                var_keys, 
                var_labels
            )
            
            if matched_var:
                matches[matched_var] = (field_conf.value, field_conf)
        
        return matches
    
    def match_all(self, recognition_result: RecognitionResult, 
                  template_variables: List[Dict[str, Any]]) -> Dict[str, Tuple[str, FieldConfidence, str]]:
        """
        将识别结果匹配到模板变量，包括未匹配的字段
        
        对于未匹配的字段，使用原始字段名作为变量名，并标记为需要创建新变量
        
        Args:
            recognition_result: OCR 识别结果
            template_variables: 模板变量定义列表
            
        Returns:
            {变量key: (匹配值, 原始字段置信度, 匹配类型)}
            匹配类型: 'matched'(已匹配现有变量), 'new'(需要创建新变量)
        """
        matches = {}
        
        # 提取模板变量的 key 和 label
        var_keys = [var['key'] for var in template_variables]
        var_labels = {var['key']: var.get('label', var['key']) for var in template_variables}
        
        # 遍历识别结果的字段
        for source_field, field_conf in recognition_result.fields.items():
            # 查找匹配的模板变量
            matched_var = self._find_best_match(
                source_field, 
                field_conf.value,
                var_keys, 
                var_labels
            )
            
            if matched_var:
                # 已匹配到现有变量
                matches[matched_var] = (field_conf.value, field_conf, 'matched')
            else:
                # 未匹配到现有变量，使用原始字段名创建新变量
                # 将字段名转换为有效的变量名格式
                new_var_key = self._field_name_to_var_key(source_field)
                matches[new_var_key] = (field_conf.value, field_conf, 'new')
        
        return matches
    
    def _field_name_to_var_key(self, field_name: str) -> str:
        """
        将字段名转换为有效的变量名格式
        
        Args:
            field_name: 原始字段名
            
        Returns:
            有效的变量名 key
        """
        import re
        
        # 中文字段名到英文变量名的映射
        common_field_mapping = {
            'name': 'name',
            '姓名': 'name',
            'gender': 'gender',
            '性别': 'gender',
            'ethnicity': 'ethnicity',
            '民族': 'ethnicity',
            'birth_date': 'birth_date',
            '出生日期': 'birth_date',
            'address': 'address',
            '住址': 'address',
            'id_number': 'id_number',
            '身份证号': 'id_number',
            'issuer': 'issuer',
            '签发机关': 'issuer',
            'validity_period': 'validity_period',
            '有效期限': 'validity_period',
        }
        
        # 如果是已知字段，使用标准变量名
        if field_name in common_field_mapping:
            return common_field_mapping[field_name]
        
        # 否则转换为 snake_case 格式
        # 移除特殊字符，替换空格为下划线
        var_key = re.sub(r'[^\w\s]', '', field_name)
        var_key = re.sub(r'\s+', '_', var_key.strip())
        var_key = var_key.lower()
        
        # 如果为空，使用原始字段名
        if not var_key:
            var_key = field_name.lower().replace(' ', '_')
        
        return var_key
    
    def _find_best_match(self, source_field: str, value: str,
                         var_keys: List[str], 
                         var_labels: Dict[str, str]) -> Optional[str]:
        """
        查找最佳匹配的模板变量
        
        Args:
            source_field: 识别字段名
            value: 识别值
            var_keys: 模板变量 key 列表
            var_labels: 模板变量 label 字典
            
        Returns:
            最佳匹配的变量 key，如果没有匹配则返回 None
        """
        # 获取该识别字段可能匹配的变量名列表
        possible_names = self.mappings.get(source_field, [])
        
        # 1. 精确匹配 key
        for name in possible_names:
            if name in var_keys:
                return name
        
        # 2. 匹配 label
        for var_key, var_label in var_labels.items():
            for name in possible_names:
                if name == var_label or name in var_label:
                    return var_key
        
        # 3. 模糊匹配（识别字段名直接等于变量 key）
        if source_field in var_keys:
            return source_field
        
        # 4. 模糊匹配 label
        for var_key, var_label in var_labels.items():
            if source_field == var_label or source_field in var_label:
                return var_key
        
        return None
    
    def suggest_mappings(self, recognition_result: RecognitionResult,
                        template_variables: List[Dict[str, Any]]) -> List[FieldMapping]:
        """
        建议字段映射关系（用于用户确认）
        
        Args:
            recognition_result: OCR 识别结果
            template_variables: 模板变量定义列表
            
        Returns:
            FieldMapping 列表
        """
        suggestions = []
        
        var_keys = [var['key'] for var in template_variables]
        var_labels = {var['key']: var.get('label', var['key']) for var in template_variables}
        
        for source_field, field_conf in recognition_result.fields.items():
            matched_var = self._find_best_match(
                source_field,
                field_conf.value,
                var_keys,
                var_labels
            )
            
            if matched_var:
                suggestions.append(FieldMapping(
                    source_field=source_field,
                    target_variable=matched_var,
                    confidence=field_conf.confidence
                ))
        
        return suggestions
    
    def add_mapping(self, source_field: str, target_variables: List[str]):
        """
        添加自定义字段映射
        
        Args:
            source_field: 识别字段名
            target_variables: 目标模板变量名列表（按优先级）
        """
        self.mappings[source_field] = target_variables
    
    def get_recognized_field_label(self, field_name: str, 
                                   document_type: DocumentType) -> str:
        """
        获取识别字段的显示标签
        
        Args:
            field_name: 字段名
            document_type: 文档类型
            
        Returns:
            显示标签
        """
        # 通用字段标签
        common_labels = {
            'name': '姓名',
            'gender': '性别',
            'ethnicity': '民族',
            'birth_date': '出生日期',
            'address': '住址',
            'id_number': '身份证号',
            'issuer': '签发机关',
            'validity_period': '有效期限',
        }
        
        # 按文档类型的特殊标签
        type_specific_labels = {
            DocumentType.HOUSEHOLD: {
                'householder': '户主',
                'household_type': '户别',
                'household_number': '户号',
            },
            DocumentType.PASSPORT: {
                'passport_number': '护照号',
                'nationality': '国籍',
                'issue_date': '签发日期',
                'expiry_date': '有效期至',
            },
            DocumentType.BUSINESS_LICENSE: {
                'company_name': '企业名称',
                'credit_code': '统一社会信用代码',
                'legal_representative': '法定代表人',
            },
        }
        
        labels = type_specific_labels.get(document_type, {})
        labels.update(common_labels)
        
        return labels.get(field_name, field_name)
    
    @staticmethod
    def get_document_type_variables(document_type: DocumentType) -> List[str]:
        """
        获取某类文档通常包含的字段列表
        
        Args:
            document_type: 文档类型
            
        Returns:
            字段名列表
        """
        type_fields = {
            DocumentType.ID_CARD_FRONT: [
                'name', 'gender', 'ethnicity', 'birth_date', 'address', 'id_number'
            ],
            DocumentType.ID_CARD_BACK: [
                'issuer', 'validity_period'
            ],
            DocumentType.HOUSEHOLD: [
                'householder', 'household_type', 'household_number', 'address'
            ],
            DocumentType.PASSPORT: [
                'passport_number', 'name', 'gender', 'nationality', 
                'birth_date', 'birth_place', 'issue_date', 'expiry_date'
            ],
            DocumentType.BUSINESS_LICENSE: [
                'credit_code', 'company_name', 'type', 'address',
                'legal_representative', 'registered_capital', 'establishment_date'
            ],
        }
        
        return type_fields.get(document_type, [])
