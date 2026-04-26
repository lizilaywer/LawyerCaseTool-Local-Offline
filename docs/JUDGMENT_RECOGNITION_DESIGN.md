# 民事判决书识别功能设计方案

## 功能概述

基于规则的离线本地识别方案，实现民事判决书的结构化信息提取，无需联网、无需AI模型。

## 已创建的文件

| 文件 | 说明 |
|------|------|
| `src/core/ocr/parsers/judgment_parser.py` | 判决书解析器核心 |
| `src/core/ocr/judgment_matcher.py` | 字段匹配器 |
| `src/gui/judgment_dialog.py` | 判决书识别结果展示对话框 |

## 核心功能模块

### 1. 文档解析模块 (`judgment_parser.py`)

**功能：**
- 自动检测是否为民事判决书
- 分段识别：标题、案号、当事人、诉请、答辩、查明、认为、判决等
- 提取结构化数据

**识别模块：**

| 模块 | 识别特征 | 提取字段 |
|------|----------|----------|
| 标题信息 | 法院名称+文书类型 | court_name, document_type |
| 案号信息 | (年份)省份代码+法院+类型+序号 | case_number |
| 当事人信息 | 原告/被告/第三人+姓名+详情 | name, gender, birth, id, address, agent |
| 程序信息 | 立案日期、适用程序、到庭情况 | filing_date, procedure |
| 原告诉请 | "诉讼请求"后的序号列表 | plaintiff_claims |
| 被告答辩 | "辩称"后的内容 | defense_statement |
| 法院查明 | "经审理查明"后的内容 | facts_found |
| 法院认为 | "本院认为"后的内容 | court_opinion |
| 判决结果 | "判决如下"后的主文 | verdict_items |
| 法律依据 | 《法律名称》第X条 | legal_basis |
| 诉讼费用 | 案件受理费+负担方 | case_costs |
| 尾部信息 | 审判员、书记员、日期 | judges, clerk, date |

**核心算法：**

```python
# 1. 模块标记正则表达式
SECTION_MARKERS = {
    'parties': [r'原告[：:]', r'被告[：:]', ...],
    'plaintiff_claim': [r'原告.+?向本院提出诉讼请求[：:]?', ...],
    'defense': [r'被告.+?辩称[：:]?', ...],
    'facts_found': [r'经审理查明[，：:]?', ...],
    'court_opinion': [r'本院认为[，：:]?', ...],
    'verdict': [r'判决如下[：:]?', ...],
}

# 2. 分段算法
- 遍历所有标记正则，记录匹配位置
- 按位置排序，确定各模块起止范围
- 提取各段文本内容

# 3. 当事人解析
party_pattern = r'([原告被告第三人]+)[：:]\s*([^，。：（\n]+)[，：]?\s*(.*?)(?=原告|被告|第三人|$)'

# 4. 判决结果解析
- 按中文/阿拉伯数字序号分割
- 提取每条判决主文
```

### 2. 字段匹配模块 (`judgment_matcher.py`)

**功能：**
- 将解析后的数据映射到案卷模板变量
- 支持自定义字段映射
- 计算匹配置信度

**默认映射表：**

| 判决书字段 | 模板变量 | 标签 | 优先级 |
|------------|----------|------|--------|
| case_number | case_number | 案号 | 10 |
| court_name | court_name | 审理法院 | 9 |
| judgment_date | judgment_date | 判决日期 | 8 |
| plaintiff_name | client_name | 原告姓名 | 10 |
| plaintiff_id | client_id_number | 原告身份证 | 9 |
| defendant_name | opponent_name | 被告姓名 | 10 |
| defendant_id | opponent_id_number | 被告身份证 | 9 |
| presiding_judge | presiding_judge | 审判长/员 | 8 |
| verdict_summary | verdict | 判决结果 | 10 |
| case_costs | case_costs | 诉讼费用 | 8 |

### 3. GUI展示模块 (`judgment_dialog.py`)

**界面结构：**

```
┌─────────────────────────────────────────────────────────────┐
│ 民事判决书解析结果                    案号: (2025)皖1722民初57号 │
├──────────────────────────┬──────────────────────────────────┤
│ [全选] [全不选]    已选:8/12 │  当事人信息 | 判决结果 | 完整文本  │
├──────────────────────────┼──────────────────────────────────┤
│ 基本信息                    │ ┌──────────────────────────────┐ │
│ ☑ 案号: (2025)皖1722...   │ │ 当事人信息                    │ │
│ ☑ 法院: 安徽省石台县法院  │ │ 身份 | 姓名 | 性别 | 身份证   │ │
│ ☑ 判决日期: 2025-02-26    │ │ 原告 | 舒萍萍 | 女 | ...      │ │
├──────────────────────────┤ │ 被告 | 汪爱月 | 女 | ...      │ │
│ 原告信息                    │ └──────────────────────────────┘ │
│ ☑ 原告姓名: 舒萍萍        │ ┌──────────────────────────────┐ │
│ ☑ 原告性别: 女            │ │ 判决主文                      │ │
│ ☑ 原告身份证: ...         │ │ 一、被告赔偿原告...           │ │
│ ☐ 原告住址: ...           │ └──────────────────────────────┘ │
├──────────────────────────┤                                  │
│ 被告信息                    │                                  │
│ ☑ 被告姓名: 汪爱月        │                                  │
│ ☑ 被告代理人: 吴建        │                                  │
├──────────────────────────┤                                  │
│ 判决结果                    │                                  │
│ ☑ 判决结果: 一、被告...   │                                  │
│ ☑ 诉讼费用: 300元         │                                  │
└──────────────────────────┴──────────────────────────────────┘
│                                    [取消]  [应用到案卷变量 ✓] │
└─────────────────────────────────────────────────────────────┘
```

## 集成步骤

### 步骤1：更新 `src/core/ocr/parsers/__init__.py`

添加新解析器的导出：

```python
from .judgment_parser import JudgmentParser, parse_judgment, JudgmentDocument

__all__ = [
    # ... 其他解析器
    'JudgmentParser',
    'parse_judgment',
    'JudgmentDocument',
]
```

### 步骤2：更新 `src/core/ocr/document_parser.py`

添加判决书类型检测：

```python
class DocumentType(Enum):
    # ... 其他类型
    JUDGMENT = "judgment"        # 民事判决书
    RULING = "ruling"            # 民事裁定书

# 在 detect_document_type 函数中添加：
if any('民事判决书' in text or '判决如下' in text for text in texts):
    return DocumentType.JUDGMENT
```

### 步骤3：更新 `src/gui/info_extraction_dialog.py`

在 `_get_parser` 方法中添加：

```python
from src.core.ocr.parsers.judgment_parser import JudgmentParser

def _get_parser(self, doc_type: DocumentType) -> DocumentParser:
    parsers = {
        # ... 其他解析器
        DocumentType.JUDGMENT: JudgmentParser(),
    }
    return parsers.get(doc_type, IDCardFrontParser())
```

### 步骤4：添加判决书特殊处理

在 `_on_file_recognized` 方法中，如果是判决书类型，弹出专用对话框：

```python
from src.gui.judgment_dialog import show_judgment_dialog

def _on_file_recognized(self, file_path: str, result: RecognitionResult):
    # ... 原有代码
    
    # 如果是判决书，使用专用对话框
    if result.document_type == DocumentType.JUDGMENT:
        from src.core.ocr.parsers.judgment_parser import JudgmentParser
        parser = JudgmentParser()
        judgment_doc = parser.parse(result.raw_text)
        
        if judgment_doc:
            selected_data = show_judgment_dialog(judgment_doc, self)
            if selected_data:
                self._apply_judgment_data(selected_data)
```

## 使用示例

### 代码示例1：解析判决书

```python
from src.core.ocr.parsers.judgment_parser import parse_judgment

# OCR识别后的文本
text = """
安徽省石台县人民法院
民事判决书
(2025)皖1722民初57号

原告：舒萍萍，女，1970年4月5日出生...
被告：汪爱月，女，1964年3月18日出生...

判决如下：
一、被告赔偿原告损失25,290.02元；
二、驳回原告其他诉讼请求。
"""

# 解析
judgment_doc = parse_judgment(text)

# 访问数据
print(judgment_doc.case_number)  # (2025)皖1722民初57号
print(judgment_doc.parties[0].name)  # 舒萍萍
print(judgment_doc.verdict_items)  # ['一、被告赔偿...', '二、驳回...']
```

### 代码示例2：匹配到模板变量

```python
from src.core.ocr.judgment_matcher import match_judgment_to_template

# 匹配字段
matches = match_judgment_to_template(judgment_doc)

# 应用到案卷
for var_key, info in matches.items():
    print(f"{info['label']}: {info['value']} (置信度: {info['confidence']})")
```

### 代码示例3：GUI展示

```python
from src.gui.judgment_dialog import show_judgment_dialog

# 显示对话框
selected_data = show_judgment_dialog(judgment_doc, parent_window)

if selected_data:
    # 用户点击了"应用到案卷变量"
    for var_key, info in selected_data.items():
        print(f"{info['label']}: {info['value']}")
```

## 准确度说明

| 模块 | 预期准确度 | 影响因素 |
|------|------------|----------|
| 案号提取 | >95% | 标准格式，正则匹配 |
| 法院名称 | >90% | 文书顶部，位置固定 |
| 当事人姓名 | >90% | 身份标识明确 |
| 当事人身份证 | >85% | 需OCR准确识别18位数字 |
| 诉讼请求 | >80% | 需正确分段 |
| 判决结果 | >85% | 序号格式规整 |
| 诉讼费用 | >90% | 金额格式固定 |
| 审判人员 | >85% | 尾部位置固定 |

## 离线优势

1. **无需联网** - 所有处理在本地完成
2. **无需AI模型** - 基于规则引擎，体积小巧
3. **响应快速** - 毫秒级解析速度
4. **隐私安全** - 敏感法律文书不上传云端
5. **准确可控** - 规则透明，错误可调试

## 扩展建议

1. **支持更多文书类型**
   - 民事裁定书（已实现框架）
   - 刑事判决书
   - 行政判决书
   - 仲裁裁决书

2. **增强识别能力**
   - 添加更多正则模式匹配不同地区格式
   - 支持表格型判决书（如要素式判决）
   - 支持多页跨页内容合并

3. **智能纠错**
   - 身份证校验位验证
   - 案号格式校验
   - 法条引用规范化

## 版本规划

- **v1.3.0**: 民事判决书完整支持
- **v1.4.0**: 民事裁定书、调解书支持
- **v1.5.0**: 刑事判决书支持
- **v2.0.0**: 全文书类型支持 + 智能纠错
