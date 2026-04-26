# -*- coding: utf-8 -*-
"""创建9个简易模板的脚本"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, List, Any


# ============ 1. 民事案件简易模板(原告) ============
CIVIL_SIMPLE_PLAINTIFF_TEMPLATE: Dict[str, Any] = {
    "id": "civil_simple_001",
    "name": "民事案件简易模板(原告)",
    "description": "适用于简单民事案件原告方的基础案卷结构",
    "category": "civil",
    "template_file": "templates/civil_simple_plaintiff/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{client_name}}",
        "folders": [
            {
                "name": "1委托手续及程序材料",
                "subfolders": [
                    {"name": "委托合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "当事人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2文书材料",
                "subfolders": [
                    {"name": "起诉状.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "证据清单.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3证据材料",
                "subfolders": []
            },
            {
                "name": "4检索及其他材料",
                "subfolders": []
            }
        ]
    },
    "variables": [
        {"key": "client_name", "label": "委托人姓名", "type": "text", "required": True},
        {"key": "case_number", "label": "案号", "type": "text", "required": False},
        {"key": "opposing_party", "label": "被告名称", "type": "text", "required": False},
        {"key": "court", "label": "受理法院", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "承办律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# ============ 2. 民事案件简易模板(被告) ============
CIVIL_SIMPLE_DEFENDANT_TEMPLATE: Dict[str, Any] = {
    "id": "civil_simple_002",
    "name": "民事案件简易模板(被告)",
    "description": "适用于简单民事案件被告方的基础案卷结构",
    "category": "civil2",
    "template_file": "templates/civil_simple_defendant/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{client_name}}",
        "folders": [
            {
                "name": "1委托手续及程序材料",
                "subfolders": [
                    {"name": "委托合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "当事人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2文书材料",
                "subfolders": [
                    {"name": "答辩状.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "证据清单.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3证据材料",
                "subfolders": []
            },
            {
                "name": "4检索及其他材料",
                "subfolders": []
            }
        ]
    },
    "variables": [
        {"key": "client_name", "label": "委托人姓名", "type": "text", "required": True},
        {"key": "case_number", "label": "案号", "type": "text", "required": False},
        {"key": "plaintiff_name", "label": "原告名称", "type": "text", "required": False},
        {"key": "court", "label": "受理法院", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "承办律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# ============ 3. 刑事案件简易模板 ============
CRIMINAL_SIMPLE_TEMPLATE: Dict[str, Any] = {
    "id": "criminal_simple_001",
    "name": "刑事案件简易模板",
    "description": "适用于简单刑事案件辩护的基础案卷结构",
    "category": "criminal",
    "template_file": "templates/criminal_simple/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{defendant_name}}",
        "folders": [
            {
                "name": "1委托辩护材料",
                "subfolders": [
                    {"name": "委托辩护合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "委托人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2会见及阅卷材料",
                "subfolders": [
                    {"name": "会见笔录.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "阅卷笔录.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3庭审材料",
                "subfolders": [
                    {"name": "辩护词.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "4裁判及其他材料",
                "subfolders": [
                    {"name": "判决书.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            }
        ]
    },
    "variables": [
        {"key": "client_name", "label": "委托人姓名", "type": "text", "required": True},
        {"key": "defendant_name", "label": "被告人姓名", "type": "text", "required": True},
        {"key": "case_number", "label": "案号", "type": "text", "required": False},
        {"key": "crime_name", "label": "涉嫌罪名", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "辩护律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# ============ 4. 行政案件简易模板(原告) ============
ADMINISTRATIVE_SIMPLE_PLAINTIFF_TEMPLATE: Dict[str, Any] = {
    "id": "admin_simple_001",
    "name": "行政案件简易模板(原告)",
    "description": "适用于简单行政案件原告方的基础案卷结构",
    "category": "administrative",
    "template_file": "templates/administrative_simple_plaintiff/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{client_name}}",
        "folders": [
            {
                "name": "1委托手续及程序材料",
                "subfolders": [
                    {"name": "委托合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "当事人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2文书材料",
                "subfolders": [
                    {"name": "行政起诉状.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "证据清单.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3证据材料",
                "subfolders": []
            },
            {
                "name": "4检索及其他材料",
                "subfolders": []
            }
        ]
    },
    "variables": [
        {"key": "client_name", "label": "委托人姓名", "type": "text", "required": True},
        {"key": "case_number", "label": "案号", "type": "text", "required": False},
        {"key": "defendant_agency", "label": "被告行政机关", "type": "text", "required": False},
        {"key": "court", "label": "受理法院", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "承办律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# ============ 5. 行政案件简易模板(被告) ============
ADMINISTRATIVE_SIMPLE_DEFENDANT_TEMPLATE: Dict[str, Any] = {
    "id": "admin_simple_002",
    "name": "行政案件简易模板(被告)",
    "description": "适用于简单行政案件被告方的基础案卷结构",
    "category": "administrative",
    "template_file": "templates/administrative_simple_defendant/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{agency_name}}",
        "folders": [
            {
                "name": "1委托手续及程序材料",
                "subfolders": [
                    {"name": "委托合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "法定代表人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2文书材料",
                "subfolders": [
                    {"name": "答辩状.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "证据清单.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3证据材料",
                "subfolders": []
            },
            {
                "name": "4检索及其他材料",
                "subfolders": []
            }
        ]
    },
    "variables": [
        {"key": "agency_name", "label": "行政机关名称", "type": "text", "required": True},
        {"key": "case_number", "label": "案号", "type": "text", "required": False},
        {"key": "plaintiff_name", "label": "原告名称", "type": "text", "required": False},
        {"key": "court", "label": "受理法院", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "承办律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# ============ 6. 劳动仲裁简易模板(申请人) ============
LABOR_SIMPLE_APPLICANT_TEMPLATE: Dict[str, Any] = {
    "id": "labor_simple_001",
    "name": "劳动仲裁简易模板(申请人)",
    "description": "适用于简单劳动仲裁申请人方的基础案卷结构",
    "category": "labor_arbitration",
    "template_file": "templates/labor_simple_applicant/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{client_name}}_劳动仲裁",
        "folders": [
            {
                "name": "1委托手续",
                "subfolders": [
                    {"name": "委托合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "当事人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2仲裁申请材料",
                "subfolders": [
                    {"name": "劳动仲裁申请书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "证据清单.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3证据材料",
                "subfolders": []
            },
            {
                "name": "4庭审及裁决材料",
                "subfolders": [
                    {"name": "代理词.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "仲裁裁决书.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            }
        ]
    },
    "variables": [
        {"key": "client_name", "label": "申请人姓名", "type": "text", "required": True},
        {"key": "case_number", "label": "仲裁案号", "type": "text", "required": False},
        {"key": "employer_name", "label": "被申请人(用人单位)", "type": "text", "required": False},
        {"key": "arbitration_committee", "label": "劳动仲裁委员会", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "承办律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# ============ 7. 劳动仲裁简易模板(被申请人) ============
LABOR_SIMPLE_RESPONDENT_TEMPLATE: Dict[str, Any] = {
    "id": "labor_simple_002",
    "name": "劳动仲裁简易模板(被申请人)",
    "description": "适用于简单劳动仲裁被申请人方的基础案卷结构",
    "category": "labor_arbitration",
    "template_file": "templates/labor_simple_respondent/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{employer_name}}_劳动仲裁",
        "folders": [
            {
                "name": "1委托手续",
                "subfolders": [
                    {"name": "委托合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "法定代表人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2答辩材料",
                "subfolders": [
                    {"name": "答辩书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "证据清单.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3证据材料",
                "subfolders": []
            },
            {
                "name": "4庭审及裁决材料",
                "subfolders": [
                    {"name": "代理词.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "仲裁裁决书.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            }
        ]
    },
    "variables": [
        {"key": "employer_name", "label": "用人单位名称", "type": "text", "required": True},
        {"key": "case_number", "label": "仲裁案号", "type": "text", "required": False},
        {"key": "applicant_name", "label": "申请人姓名", "type": "text", "required": False},
        {"key": "arbitration_committee", "label": "劳动仲裁委员会", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "承办律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# ============ 8. 商事仲裁简易模板(申请人) ============
COMMERCIAL_SIMPLE_APPLICANT_TEMPLATE: Dict[str, Any] = {
    "id": "commercial_simple_001",
    "name": "商事仲裁简易模板(申请人)",
    "description": "适用于简单商事仲裁申请人方的基础案卷结构",
    "category": "commercial_arbitration",
    "template_file": "templates/commercial_simple_applicant/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{client_name}}_商事仲裁",
        "folders": [
            {
                "name": "1委托手续",
                "subfolders": [
                    {"name": "委托合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "当事人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2仲裁申请材料",
                "subfolders": [
                    {"name": "仲裁申请书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "证据清单.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3证据材料",
                "subfolders": []
            },
            {
                "name": "4庭审及裁决材料",
                "subfolders": [
                    {"name": "代理词.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "仲裁裁决书.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            }
        ]
    },
    "variables": [
        {"key": "client_name", "label": "申请人名称", "type": "text", "required": True},
        {"key": "case_number", "label": "仲裁案号", "type": "text", "required": False},
        {"key": "respondent_name", "label": "被申请人名称", "type": "text", "required": False},
        {"key": "arbitration_institution", "label": "仲裁机构", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "承办律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# ============ 9. 商事仲裁简易模板(被申请人) ============
COMMERCIAL_SIMPLE_RESPONDENT_TEMPLATE: Dict[str, Any] = {
    "id": "commercial_simple_002",
    "name": "商事仲裁简易模板(被申请人)",
    "description": "适用于简单商事仲裁被申请人方的基础案卷结构",
    "category": "commercial_arbitration",
    "template_file": "templates/commercial_simple_respondent/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{respondent_name}}_商事仲裁",
        "folders": [
            {
                "name": "1委托手续",
                "subfolders": [
                    {"name": "委托合同.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "授权委托书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "法定代表人身份证明.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "2答辩材料",
                "subfolders": [
                    {"name": "答辩书.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "证据清单.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            },
            {
                "name": "3证据材料",
                "subfolders": []
            },
            {
                "name": "4庭审及裁决材料",
                "subfolders": [
                    {"name": "代理词.docx", "type": "file", "template_path": "", "use_template": False},
                    {"name": "仲裁裁决书.docx", "type": "file", "template_path": "", "use_template": False}
                ]
            }
        ]
    },
    "variables": [
        {"key": "respondent_name", "label": "被申请人名称", "type": "text", "required": True},
        {"key": "case_number", "label": "仲裁案号", "type": "text", "required": False},
        {"key": "applicant_name", "label": "申请人名称", "type": "text", "required": False},
        {"key": "arbitration_institution", "label": "仲裁机构", "type": "text", "required": False},
        {"key": "lawyer_name", "label": "承办律师", "type": "text", "required": False},
        {"key": "receive_date", "label": "收案日期", "type": "date", "required": False}
    ]
}


# 所有简易模板列表
SIMPLE_TEMPLATES: List[Dict[str, Any]] = [
    CIVIL_SIMPLE_PLAINTIFF_TEMPLATE,
    CIVIL_SIMPLE_DEFENDANT_TEMPLATE,
    CRIMINAL_SIMPLE_TEMPLATE,
    ADMINISTRATIVE_SIMPLE_PLAINTIFF_TEMPLATE,
    ADMINISTRATIVE_SIMPLE_DEFENDANT_TEMPLATE,
    LABOR_SIMPLE_APPLICANT_TEMPLATE,
    LABOR_SIMPLE_RESPONDENT_TEMPLATE,
    COMMERCIAL_SIMPLE_APPLICANT_TEMPLATE,
    COMMERCIAL_SIMPLE_RESPONDENT_TEMPLATE
]


def create_template_directories():
    """创建模板文件夹和空Word文档"""
    templates_dir = Path(__file__).parent.parent / "templates"
    
    template_mapping = {
        "civil_simple_plaintiff": CIVIL_SIMPLE_PLAINTIFF_TEMPLATE,
        "civil_simple_defendant": CIVIL_SIMPLE_DEFENDANT_TEMPLATE,
        "criminal_simple": CRIMINAL_SIMPLE_TEMPLATE,
        "administrative_simple_plaintiff": ADMINISTRATIVE_SIMPLE_PLAINTIFF_TEMPLATE,
        "administrative_simple_defendant": ADMINISTRATIVE_SIMPLE_DEFENDANT_TEMPLATE,
        "labor_simple_applicant": LABOR_SIMPLE_APPLICANT_TEMPLATE,
        "labor_simple_respondent": LABOR_SIMPLE_RESPONDENT_TEMPLATE,
        "commercial_simple_applicant": COMMERCIAL_SIMPLE_APPLICANT_TEMPLATE,
        "commercial_simple_respondent": COMMERCIAL_SIMPLE_RESPONDENT_TEMPLATE
    }
    
    for folder_name, template_config in template_mapping.items():
        template_folder = templates_dir / folder_name
        template_folder.mkdir(parents=True, exist_ok=True)
        
        # 创建空的template.docx文件
        template_file = template_folder / "template.docx"
        if not template_file.exists():
            # 创建一个最小的空docx文件
            create_empty_docx(template_file)
            print(f"Created: {template_file}")
        
        print(f"Ensured directory: {template_folder}")


def create_empty_docx(filepath: Path):
    """创建一个空的docx文件（最小有效文件）"""
    from zipfile import ZipFile
    import io
    
    # 最小docx文件内容
    content_types = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''

    rels = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

    document = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:pPr>
                <w:pStyle w:val="Normal"/>
            </w:pPr>
            <w:r>
                <w:t></w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>'''

    # 创建ZIP文件
    with ZipFile(filepath, 'w') as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', rels)
        zf.writestr('word/document.xml', document)


def print_template_definitions():
    """打印模板定义代码，用于复制到default_templates.py"""
    print("\n" + "="*80)
    print("Please add the following templates to src/config/default_templates.py")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("Creating 9 simple templates...")
    create_template_directories()
    print("\n✓ Template directories created successfully!")
    print_template_definitions()
