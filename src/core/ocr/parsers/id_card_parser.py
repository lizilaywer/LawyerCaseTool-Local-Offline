# -*- coding: utf-8 -*-
"""身份证解析器模块"""

import re
from typing import List, Any, Optional, Tuple

from ..document_parser import DocumentParser, DocumentType, RecognitionResult, FieldConfidence


class IDCardFrontParser(DocumentParser):
    """身份证正面解析器（人像面）"""
    
    def __init__(self):
        super().__init__(DocumentType.ID_CARD_FRONT)
    
    def _is_valid_name(self, name: str) -> bool:
        """检查是否为有效姓名"""
        # 排除常见非人名词和关键字
        invalid_words = ['姓名', '性别', '民族', '出生', '住址', '身份', '公民', 
                        '中华', '人民', '共和', '国', '省', '市', '区', '县',
                        '男', '女']  # 性别不能作为姓名
        if name in invalid_words:
            return False
        # 姓名长度2-4个汉字
        if len(name) < 2 or len(name) > 4:
            return False
        # 姓名通常全是汉字
        if not re.match(r'^[\u4e00-\u9fa5]+$', name):
            return False
        # 排除纯数字
        if name.isdigit():
            return False
        return True
    
    def parse(self, ocr_results: List[Any]) -> RecognitionResult:
        """
        解析身份证正面 OCR 结果
        
        包含字段：姓名、性别、民族、出生日期、住址、公民身份号码
        """
        # 提取所有文本和置信度
        texts = []
        text_confidences = {}
        
        for block in ocr_results:
            text = getattr(block, 'text', str(block))
            confidence = getattr(block, 'confidence', 0.8)
            texts.append(text)
            text_confidences[text] = confidence
        
        fields = {}
        
        # 1. 提取姓名（通常在"姓名"后面）
        name = self._extract_name(texts)
        if name:
            fields['name'] = name
        
        # 2. 提取性别
        gender = self._extract_gender(texts)
        if gender:
            fields['gender'] = gender
        
        # 3. 提取民族
        ethnicity = self._extract_ethnicity(texts)
        if ethnicity:
            fields['ethnicity'] = ethnicity
        
        # 4. 提取出生日期
        birth_date = self._extract_birth_date(texts)
        if birth_date:
            fields['birth_date'] = birth_date
        
        # 5. 提取住址
        address = self._extract_address(texts)
        if address:
            fields['address'] = address
        
        # 6. 提取身份证号
        id_number = self._extract_id_number(texts)
        if id_number:
            fields['id_number'] = id_number
        
        # 计算整体置信度
        overall_confidence = sum(f.confidence for f in fields.values()) / len(fields) if fields else 0.0
        
        return RecognitionResult(
            document_type=self.document_type,
            fields=fields,
            raw_texts=texts,
            overall_confidence=overall_confidence
        )
    
    def _extract_name(self, texts: List[str]) -> Optional[FieldConfidence]:
        """提取姓名"""
        # 方法1：在"姓名"标签后面查找
        for i, text in enumerate(texts):
            if '姓名' in text and '性别' not in text:  # 排除"性别"误识别
                # 尝试在同一行提取（格式：姓名张三）
                name_match = re.search(r'姓名\s*([\u4e00-\u9fa5]{2,4})', text)
                if name_match:
                    name = name_match.group(1)
                    if self._is_valid_name(name):
                        return FieldConfidence(
                            value=name,
                            confidence=0.9,
                            raw_texts=[text]
                        )
                
                # 尝试在下一行找名字
                if i + 1 < len(texts):
                    name_text = texts[i + 1]
                    # 严格过滤：只保留纯中文
                    name = re.sub(r'[^\u4e00-\u9fa5]', '', name_text)
                    # 排除包含关键字的文本（性别、民族等）
                    if any(kw in name for kw in ['性别', '民族', '出生', '住址', '身份', '公民', '男', '女']):
                        continue
                    if 2 <= len(name) <= 4 and self._is_valid_name(name):
                        return FieldConfidence(
                            value=name,
                            confidence=0.85,
                            raw_texts=[text, name_text]
                        )
        
        # 方法2：根据位置推断（姓名通常在身份证右上方）
        for i, text in enumerate(texts[:8]):  # 只看前8个文本块
            # 严格排除包含关键字的文本
            if any(kw in text for kw in ['姓名', '性别', '民族', '出生', '住址', '身份', '公民', '号码']):
                continue
            # 提取2-4个连续汉字
            names = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
            for name in names:
                if self._is_valid_name(name):
                    return FieldConfidence(
                        value=name,
                        confidence=0.75,
                        raw_texts=[text]
                    )
        
        return None
    
    def _extract_gender(self, texts: List[str]) -> Optional[FieldConfidence]:
        """提取性别"""
        for i, text in enumerate(texts):
            if '性别' in text:
                # 在同一行提取（格式：性别男）
                gender_match = re.search(r'性别\s*(男|女)', text)
                if gender_match:
                    return FieldConfidence(
                        value=gender_match.group(1),
                        confidence=0.95,
                        raw_texts=[text]
                    )
                
                # 在下一行找
                if i + 1 < len(texts):
                    next_text = texts[i + 1].strip()
                    if next_text == '男':
                        return FieldConfidence(value='男', confidence=0.9, raw_texts=[text, next_text])
                    if next_text == '女':
                        return FieldConfidence(value='女', confidence=0.9, raw_texts=[text, next_text])
            
            # 全局搜索独立的性别标识（单独一行的"男"或"女"）
            stripped = text.strip()
            if stripped == '男' or stripped == '女':
                return FieldConfidence(value=stripped, confidence=0.85, raw_texts=[text])
        
        return None
    
    def _extract_ethnicity(self, texts: List[str]) -> Optional[FieldConfidence]:
        """提取民族"""
        ethnicity_list = [
            '汉', '满', '蒙', '回', '藏', '维吾尔', '苗', '彝', '壮', '布依',
            '侗', '瑶', '白', '土家', '哈尼', '哈萨克', '傣', '黎', '傈僳',
            '佤', '畲', '高山', '拉祜', '水', '东乡', '纳西', '景颇', '柯尔克孜',
            '土', '达斡尔', '仫佬', '羌', '布朗', '撒拉', '毛南', '仡佬', '锡伯',
            '阿昌', '普米', '塔吉克', '怒', '乌孜别克', '俄罗斯', '鄂温克', '德昂',
            '保安', '裕固', '京', '塔塔尔', '独龙', '鄂伦春', '赫哲', '门巴', '珞巴', '基诺'
        ]
        
        for i, text in enumerate(texts):
            if '民族' in text:
                # 在同一行提取（格式：民族汉）
                for ethnic in ethnicity_list:
                    if ethnic in text:
                        return FieldConfidence(
                            value=ethnic + '族',
                            confidence=0.9,
                            raw_texts=[text]
                        )
                
                # 在下一行找民族
                if i + 1 < len(texts):
                    next_text = texts[i + 1]
                    for ethnic in ethnicity_list:
                        if ethnic in next_text:
                            return FieldConfidence(
                                value=ethnic + '族',
                                confidence=0.85,
                                raw_texts=[text, next_text]
                            )
        
        return None
    
    def _extract_birth_date(self, texts: List[str]) -> Optional[FieldConfidence]:
        """提取出生日期"""
        for i, text in enumerate(texts):
            if '出生' in text:
                # 在同一样本中查找日期
                date_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', text)
                if date_match:
                    year, month, day = date_match.groups()
                    return FieldConfidence(
                        value=f"{year}-{int(month):02d}-{int(day):02d}",
                        confidence=0.9,
                        raw_texts=[text]
                    )
                
                # 在后续文本中查找
                for j in range(i + 1, min(i + 4, len(texts))):
                    date_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})', texts[j])
                    if date_match:
                        year, month, day = date_match.groups()
                        return FieldConfidence(
                            value=f"{year}-{int(month):02d}-{int(day):02d}",
                            confidence=0.85,
                            raw_texts=[text, texts[j]]
                        )
        
        # 方法2：全局搜索日期格式
        for text in texts:
            # YYYY-MM-DD 格式
            match = re.search(r'(19|20)\d{2}[-年](0[1-9]|1[0-2])[-月](0[1-9]|[12]\d|3[01])', text)
            if match:
                date_str = match.group(0).replace('年', '-').replace('月', '-').replace('日', '')
                return FieldConfidence(
                    value=date_str,
                    confidence=0.8,
                    raw_texts=[text]
                )
        
        return None
    
    def _extract_address(self, texts: List[str]) -> Optional[FieldConfidence]:
        """提取住址"""
        address_keywords = ['省', '市', '区', '县', '镇', '乡', '村', '街', '路', '号']
        
        for i, text in enumerate(texts):
            if '住址' in text or '地址' in text:
                address_parts = []
                raw_texts = [text]
                
                # 方法1：检查"住址"同一行是否包含地址内容（格式：住址安徽省...）
                # 移除"住址"标签后检查剩余内容
                same_line_address = re.sub(r'^.*?住址', '', text).strip()
                # 清理可能的冒号、空格等
                same_line_address = re.sub(r'^[:：\s]+', '', same_line_address)
                
                # 如果同一行有地址内容（包含省、市、区等关键词或长度足够）
                if same_line_address and len(same_line_address) >= 4:
                    if any(kw in same_line_address for kw in address_keywords):
                        address_parts.append(same_line_address)
                
                # 方法2：收集后续的几行作为地址（多行地址情况）
                for j in range(i + 1, min(i + 5, len(texts))):
                    next_text = texts[j]
                    # 如果遇到下一个字段的关键字，停止
                    if any(kw in next_text for kw in ['身份', '号码', '公民', '签发', '有效', '姓名', '性别', '民族', '出生']):
                        break
                    # 排除纯数字（可能是身份证号的一部分）
                    if next_text.strip().isdigit():
                        break
                    address_parts.append(next_text)
                    raw_texts.append(next_text)
                
                if address_parts:
                    address = ''.join(address_parts)
                    # 清理地址，移除"办证使用"等无关文字
                    address = re.sub(r'办证使用|办证使', '', address)
                    # 清理其他非地址字符，但保留中文、英文、数字、横杠
                    address = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\-]', '', address)
                    if len(address) >= 6:
                        return FieldConfidence(
                            value=address,
                            confidence=0.8,
                            raw_texts=raw_texts
                        )
        
        # 方法3：搜索包含省市区的文本
        for text in texts:
            if any(kw in text for kw in ['省', '自治区', '直辖市']):
                if any(kw in text for kw in ['市', '区', '县']):
                    # 清理地址
                    address = re.sub(r'办证使用|办证使', '', text)
                    address = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\-]', '', address)
                    if len(address) >= 6:
                        return FieldConfidence(
                            value=address,
                            confidence=0.7,
                            raw_texts=[text]
                        )
        
        return None
    
    def _extract_id_number(self, texts: List[str]) -> Optional[FieldConfidence]:
        """提取身份证号"""
        for text in texts:
            # 18位身份证号
            match = re.search(r'(\d{6})(19|20)(\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(\d{3}[\dXx])', text)
            if match:
                id_number = match.group(0).upper()
                return FieldConfidence(
                    value=id_number,
                    confidence=0.95,
                    raw_texts=[text]
                )
            
            # 15位身份证号
            match = re.search(r'(\d{6})(\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(\d{3})', text)
            if match:
                potential_id = match.group(0)
                if len(potential_id) == 15:
                    return FieldConfidence(
                        value=potential_id,
                        confidence=0.85,
                        raw_texts=[text]
                    )
        
        return None


class IDCardBackParser(DocumentParser):
    """身份证反面解析器（国徽面）"""
    
    def __init__(self):
        super().__init__(DocumentType.ID_CARD_BACK)
    
    def parse(self, ocr_results: List[Any]) -> RecognitionResult:
        """解析身份证反面 OCR 结果"""
        texts = []
        for block in ocr_results:
            text = getattr(block, 'text', str(block))
            texts.append(text)
        
        fields = {}
        
        # 提取签发机关
        issuer = self._extract_issuer(texts)
        if issuer:
            fields['issuer'] = issuer
        
        # 提取有效期限
        validity = self._extract_validity(texts)
        if validity:
            fields['validity_period'] = validity
        
        overall_confidence = sum(f.confidence for f in fields.values()) / len(fields) if fields else 0.0
        
        return RecognitionResult(
            document_type=self.document_type,
            fields=fields,
            raw_texts=texts,
            overall_confidence=overall_confidence
        )
    
    def _extract_issuer(self, texts: List[str]) -> Optional[FieldConfidence]:
        """提取签发机关"""
        for i, text in enumerate(texts):
            if '签发机关' in text or '签发' in text:
                # 在后续行查找
                for j in range(i + 1, min(i + 3, len(texts))):
                    issuer_text = texts[j]
                    # 清理并验证
                    issuer = re.sub(r'[^\u4e00-\u9fa5]', '', issuer_text)
                    if '公安局' in issuer or '分局' in issuer:
                        return FieldConfidence(
                            value=issuer,
                            confidence=0.85,
                            raw_texts=[text, issuer_text]
                        )
        
        # 方法2：直接搜索包含公安局的文本
        for text in texts:
            match = re.search(r'[\u4e00-\u9fa5]+公安局[\u4e00-\u9fa5]*', text)
            if match:
                return FieldConfidence(
                    value=match.group(0),
                    confidence=0.8,
                    raw_texts=[text]
                )
        
        return None
    
    def _extract_validity(self, texts: List[str]) -> Optional[FieldConfidence]:
        """提取有效期限"""
        for i, text in enumerate(texts):
            if '有效期限' in text or '有效期' in text:
                # 查找日期范围
                for j in range(i + 1, min(i + 3, len(texts))):
                    validity_text = texts[j]
                    # 匹配多种格式
                    # 格式1：2010.01.01-2020.01.01
                    match = re.search(r'(\d{4}[.\-年]\d{1,2}[.\-月]\d{1,2})[\-~至]*(\d{4}[.\-年]\d{1,2}[.\-月]\d{1,2})', validity_text)
                    if match:
                        return FieldConfidence(
                            value=validity_text.strip(),
                            confidence=0.85,
                            raw_texts=[text, validity_text]
                        )
                    
                    # 格式2：长期
                    if '长期' in validity_text:
                        return FieldConfidence(
                            value='长期',
                            confidence=0.9,
                            raw_texts=[text, validity_text]
                        )
        
        # 全局搜索日期范围
        for text in texts:
            match = re.search(r'(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})[\-~至]*(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}|长期)', text)
            if match:
                return FieldConfidence(
                    value=text.strip(),
                    confidence=0.8,
                    raw_texts=[text]
                )
        
        return None
