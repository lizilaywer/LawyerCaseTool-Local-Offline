# -*- coding: utf-8 -*-
"""默认模板和配置定义"""

from typing import Any, Dict, List


DEFAULT_TEMPLATES: List[Dict[str, Any]] = [
    {
        'id': 'non_litigation_001',
        'name': '非诉案件模板',
        'description': '适用于非诉讼法律事务的标准化案卷',
        'category': 'non_litigation',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_{{Cause_of_Action}}',
            'folders': [
                {
                    'name': '0委托材料',
                    'subfolders': [
                        {
                            'name': '0 {{client_name}}_委托合同.docx',
                            'template_path': '',
                            'type': 'file',
                        },
                        {
                            'name': '1 {{client_name}}_授权委托书.docx',
                            'template_path': '',
                            'type': 'file',
                        },
                        {
                            'name': '2 法定代表人身份证明书(可删除).docx',
                            'template_path': '',
                            'type': 'file',
                        },
                    ],
                },
                {
                    'name': '1基础材料',
                    'subfolders': [],
                },
                {
                    'name': '2工作记录',
                    'subfolders': [
                        {
                            'name': '0工作日志.docx',
                            'template_path': '',
                            'type': 'file',
                        },
                        {
                            'name': '1 {{client_name}}_谈话笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '3法律文书',
                    'subfolders': [
                        {
                            'name': '0 {{client_name}}_法律意见书.docx',
                            'template_path': '',
                            'type': 'file',
                        },
                        {
                            'name': '1 {{client_name}}_律师函.docx',
                            'template_path': '',
                            'type': 'file',
                        },
                        {
                            'name': '2审查报告.docx',
                            'template_path': '',
                            'type': 'file',
                        },
                    ],
                },
                {
                    'name': '4成果文件',
                    'subfolders': [],
                },
                {
                    'name': '5结案材料',
                    'subfolders': [
                        {
                            'name': '0 {{client_name}}_结案报告.docx',
                            'template_path': '',
                            'type': 'file',
                        },
                    ],
                },
            ],
        },
        'variables': [
            {
                'default_value': '',
                'key': 'client_name',
                'label': '委托人名称',
                'required': True,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'matter_number',
                'label': '事项编号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'default_value': '',
                'key': 'matter_type',
                'label': '事项类型',
                'required': False,
                'type': 'select',
                'validation': {
                    'options': [
                        '法律咨询',
                        '合同审查',
                        '尽职调查',
                        '法律意见',
                        '其他',
                    ],
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
            {
                'key': 'Cause_of_Action',
                'label': '案由',
                'required': False,
                'type': 'text',
            },
        ],
    },
    {
        'id': 'civil_simple_001',
        'name': '民事案件简易模板(原告)',
        'description': '适用于简单民事案件原告方的基础案卷结构(精简版)',
        'category': 'civil',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_民事_{{Cause_of_Action}}',
            'folders': [
                {
                    'name': ' 1委托手续及程序材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_委托合同.docx',
                            'template_path': 'civil_simple_plaintiff/民事委托代理合同.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': ' {{client_name}} _授权委托书.docx',
                            'template_path': 'civil_simple_plaintiff/民事授权委托书.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '法定代表人身份证明书（可删除）.docx',
                            'template_path': 'civil_simple_plaintiff/法定代表人身份证明书.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '风险告知书.docx',
                            'template_path': 'civil_simple_plaintiff/诉讼风险告知书.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '{{client_name}}_谈话笔录.docx',
                            'template_path': 'civil_simple_plaintiff/谈话笔录规范.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '📄质量反馈意见卡.docx',
                            'template_path': 'civil_simple_plaintiff/质量反馈意见卡.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                    ],
                },
                {
                    'name': '2文书材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}} _起诉状.docx',
                            'template_path': 'civil_simple_plaintiff/民事起诉状.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': ' {{client_name}} _证据目录.docx',
                            'template_path': 'civil_simple_plaintiff/证据目录.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': ' {{client_name}} _代理词.docx',
                            'template_path': 'civil_simple_plaintiff/代理词.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                    ],
                },
                {
                    'name': '3证据材料',
                    'subfolders': [],
                },
                {
                    'name': '4检索及其他材料',
                    'subfolders': [],
                },
            ],
        },
        'variables': [
            {
                'default_value': '',
                'key': 'client_name',
                'label': '委托人姓名',
                'required': True,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'opposing_party',
                'label': '被告名称',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                },
            },
            {
                'key': 'Cause_of_Action',
                'label': '案由',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'Case_adjudication_stage',
                'label': '办理阶段',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'payment',
                'label': '律师费支付-例：伍仟圆（¥5000）',
                'required': False,
                'type': 'text',
            },
            {
                'default_value': '',
                'key': 'court',
                'label': '受理法院',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'key': 'legal_representative',
                'label': '法定代表人',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'legal_representative_id',
                'label': '法定代表人身份证号',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'address',
                'label': '住址',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'birth_date',
                'label': '出生日期',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'ethnicity',
                'label': '民族',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'gender',
                'label': '性别',
                'required': False,
                'type': 'text',
            },
        ],
    },
    {
        'id': 'civil_simple_002',
        'name': '民事案件简易模板(被告)',
        'description': '适用于简单民事案件被告方的基础案卷结构(精简版)',
        'category': 'civil',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_民事_{{Cause_of_Action}}',
            'folders': [
                {
                    'name': '1委托手续及程序材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_ 委托合同.docx',
                            'template_path': 'civil_simple_defendant/民事委托代理合同.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '{{client_name}}_授权委托书.docx',
                            'template_path': 'civil_simple_defendant/民事授权委托书.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '法定代表人身份证明书(可删除).docx',
                            'template_path': 'civil_simple_defendant/法定代表人身份证明书.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '风险告知书.docx',
                            'template_path': 'civil_simple_defendant/诉讼风险告知书.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '{{client_name}}_谈话笔录.docx',
                            'template_path': 'civil_simple_defendant/谈话笔录规范.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                    ],
                },
                {
                    'name': '2文书材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_民事答辩状.docx',
                            'template_path': 'civil_simple_defendant/民事答辩状.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '{{client_name}}_ 证据目录.docx',
                            'template_path': 'civil_simple_defendant/证据目录.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                        {
                            'name': '{{client_name}}_代理词.docx',
                            'template_path': 'civil_simple_defendant/代理词.docx',
                            'type': 'file',
                            'use_template': True,
                        },
                    ],
                },
                {
                    'name': '3证据材料',
                    'subfolders': [],
                },
                {
                    'name': '4检索及其他材料',
                    'subfolders': [],
                },
            ],
        },
        'variables': [
            {
                'default_value': '',
                'key': 'client_name',
                'label': '委托人姓名',
                'required': True,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'plaintiff_name',
                'label': '原告名称',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                },
            },
            {
                'key': 'Cause_of_Action',
                'label': '案由',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'Case_adjudication_stage',
                'label': '办理阶段',
                'required': False,
                'type': 'text',
            },
            {
                'default_value': '',
                'key': 'court',
                'label': '受理法院',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'key': 'payment',
                'label': '律师费支付-例：伍仟圆（¥5000）',
                'required': False,
                'type': 'text',
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
            {
                'key': 'address',
                'label': '住址',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'birth_date',
                'label': '出生日期',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'ethnicity',
                'label': '民族',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'gender',
                'label': '性别',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'id_number',
                'label': '身份证号',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'opponent_address',
                'label': '对方住址',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'opponent_birth_date',
                'label': '对方出生日期',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'opponent_ethnicity',
                'label': '对方民族',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'opponent_gender',
                'label': '对方性别',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'opponent_id_number',
                'label': '对方身份证号',
                'required': False,
                'type': 'text',
            },
        ],
    },
    {
        'id': 'criminal_simple_001',
        'name': '刑事案件简易模板',
        'description': '适用于简单刑事案件辩护的基础案卷结构(精简版)',
        'category': 'criminal',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{defendant_name}}_刑事_{{crime_name}}',
            'folders': [
                {
                    'name': '1委托辩护材料',
                    'subfolders': [
                        {
                            'name': '{{defendant_name}}_委托辩护合同.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{defendant_name}}_ 授权委托书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '风险告知书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_谈话笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '2会见及阅卷材料',
                    'subfolders': [
                        {
                            'name': '{{defendant_name}}_会见笔录1.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{defendant_name}}_阅卷笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '3庭审材料',
                    'subfolders': [
                        {
                            'name': '{{defendant_name}}_辩护词.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '4裁判及其他材料',
                    'subfolders': [],
                },
            ],
        },
        'variables': [
            {
                'default_value': '',
                'key': 'client_name',
                'label': '委托人姓名',
                'required': True,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'defendant_name',
                'label': '被告人姓名',
                'required': True,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'default_value': '',
                'key': 'crime_name',
                'label': '涉嫌罪名',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '辩护律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
            {
                'key': 'payment',
                'label': '律师费支付-例：壹万圆（¥10000）',
                'required': False,
                'type': 'text',
            },
        ],
    },
    {
        'id': 'admin_simple_001',
        'name': '行政案件简易模板(原告)',
        'description': '适用于简单行政案件原告方的基础案卷结构(精简版)',
        'category': 'administrative',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_行政诉讼_{{Cause_of_Action}}',
            'folders': [
                {
                    'name': '1委托手续及程序材料',
                    'subfolders': [
                        {
                            'name': '1{{client_name}}_委托合同.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '2{{client_name}}_授权委托书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '4法定代表人人身份证明书（可删除）.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '3{{client_name}}_谈话笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '2文书材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_行政起诉状.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_证据目录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_代理词.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '3证据材料',
                    'subfolders': [],
                },
                {
                    'name': '4检索及其他材料',
                    'subfolders': [],
                },
            ],
        },
        'variables': [
            {
                'default_value': '',
                'key': 'client_name',
                'label': '委托人姓名',
                'required': True,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'default_value': '',
                'key': 'defendant_agency',
                'label': '被告行政机关',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'court',
                'label': '受理法院',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
            {
                'key': 'Cause_of_Action',
                'label': '案由',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'address',
                'label': '住址',
                'type': 'text',
                'required': False,
            },
            {
                'key': 'birth_date',
                'label': '出生日期',
                'type': 'text',
                'required': False,
            },
            {
                'key': 'ethnicity',
                'label': '民族',
                'type': 'text',
                'required': False,
            },
            {
                'key': 'gender',
                'label': '性别',
                'type': 'text',
                'required': False,
            },
            {
                'key': 'id_number',
                'label': '身份证号',
                'type': 'text',
                'required': False,
            },
        ],
    },
    {
        'id': 'admin_simple_002',
        'name': '行政案件简易模板(被告)',
        'description': '适用于简单行政案件被告方的基础案卷结构(精简版)',
        'category': 'administrative',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_行政诉讼_{{Cause_of_Action}}',
            'folders': [
                {
                    'name': '1委托手续及程序材料',
                    'subfolders': [
                        {
                            'name': '1{{client_name}}_委托合同.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '2{{client_name}}_授权委托书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '法定代表人身份证明.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '3{{client_name}}_谈话笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '2文书材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_ 行政答辩状.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_证据目录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_代理词.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '3证据材料',
                    'subfolders': [],
                },
                {
                    'name': '4检索及其他材料',
                    'subfolders': [],
                },
            ],
        },
        'variables': [
            {
                'key': 'client_name',
                'label': '行政机关名称',
                'required': True,
                'type': 'text',
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'default_value': '',
                'key': 'plaintiff_name',
                'label': '原告名称',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                },
            },
            {
                'default_value': '',
                'key': 'court',
                'label': '受理法院',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
            {
                'key': 'Cause_of_Action',
                'label': '案由',
                'required': False,
                'type': 'text',
            },
        ],
    },
    {
        'id': 'labor_simple_001',
        'name': '劳动仲裁简易模板(申请人)',
        'description': '适用于简单劳动仲裁申请人方的基础案卷结构(精简版)',
        'category': 'labor_arbitration',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_劳动仲裁',
            'folders': [
                {
                    'name': '1委托手续',
                    'subfolders': [
                        {
                            'name': '1{{client_name}}_委托合同.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '2{{client_name}}_授权委托书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '风险告知书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '3{{client_name}}_谈话笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '2仲裁文书材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_ 劳动仲裁申请书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_证据目录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_代理词.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '3证据材料',
                    'subfolders': [],
                },
                {
                    'name': '4庭审及裁决材料',
                    'subfolders': [],
                },
            ],
        },
        'variables': [
            {
                'default_value': '',
                'key': 'client_name',
                'label': '申请人姓名',
                'required': True,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '仲裁案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'default_value': '',
                'key': 'employer_name',
                'label': '被申请人(用人单位)',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'arbitration_committee',
                'label': '劳动仲裁委员会',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
        ],
    },
    {
        'id': 'labor_simple_002',
        'name': '劳动仲裁简易模板(被申请人)',
        'description': '适用于简单劳动仲裁被申请人方的基础案卷结构(精简版)',
        'category': 'labor_arbitration',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_劳动仲裁',
            'folders': [
                {
                    'name': '1委托手续',
                    'subfolders': [
                        {
                            'name': '1{{client_name}}_委托合同.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '2{{client_name}}_授权委托书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '法定代表人身份证明.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '风险告知书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '3{{client_name}}_谈话笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '2答辩材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_劳动仲裁答辩书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_证据目录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '3证据材料',
                    'subfolders': [],
                },
                {
                    'name': '4庭审及裁决材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_代理词.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
            ],
        },
        'variables': [
            {
                'key': 'client_name',
                'label': '用人单位名称',
                'required': True,
                'type': 'text',
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '仲裁案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'key': 'applicant_name',
                'label': '申请人姓名',
                'required': False,
                'type': 'text',
            },
            {
                'default_value': '',
                'key': 'arbitration_committee',
                'label': '劳动仲裁委员会',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
        ],
    },
    {
        'id': 'commercial_simple_001',
        'name': '商事仲裁简易模板(申请人)',
        'description': '适用于简单商事仲裁申请人方的基础案卷结构(精简版)',
        'category': 'commercial_arbitration',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_商事仲裁_{{Cause_of_Action}}',
            'folders': [
                {
                    'name': '1委托手续',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_委托合同.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_授权委托书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '风险告知书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_谈话笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '法定代表人身份证明书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '2仲裁申请材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_仲裁申请书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_证据目录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '3证据材料',
                    'subfolders': [],
                },
                {
                    'name': '4庭审及裁决材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_代理词.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
            ],
        },
        'variables': [
            {
                'default_value': '',
                'key': 'client_name',
                'label': '申请人名称',
                'required': True,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '仲裁案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'default_value': '',
                'key': 'respondent_name',
                'label': '被申请人名称',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'arbitration_institution',
                'label': '仲裁机构',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
            {
                'key': 'Cause_of_Action',
                'label': '案由',
                'required': False,
                'type': 'text',
            },
            {
                'key': 'address',
                'label': '住址',
                'type': 'text',
                'required': False,
            },
            {
                'key': 'birth_date',
                'label': '出生日期',
                'type': 'text',
                'required': False,
            },
            {
                'key': 'ethnicity',
                'label': '民族',
                'type': 'text',
                'required': False,
            },
            {
                'key': 'gender',
                'label': '性别',
                'type': 'text',
                'required': False,
            },
            {
                'key': 'id_number',
                'label': '身份证号',
                'type': 'text',
                'required': False,
            },
        ],
    },
    {
        'id': 'commercial_simple_002',
        'name': '商事仲裁简易模板(被申请人)',
        'description': '适用于简单商事仲裁被申请人方的基础案卷结构(精简版)',
        'category': 'commercial_arbitration',
        'template_file': 'templates/blank.docx',
        'folder_structure': {
            'root_name': '{{receive_date}}_{{client_name}}_商事仲裁_{{Cause_of_Action}}',
            'folders': [
                {
                    'name': '1委托手续',
                    'subfolders': [
                        {
                            'name': '1{{client_name}}_ 委托合同.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '2{{client_name}}_授权委托书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '法定代表人身份证明.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '3{{client_name}}_谈话笔录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '2答辩材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_仲裁答辩书.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                        {
                            'name': '{{client_name}}_证据目录.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
                {
                    'name': '3证据材料',
                    'subfolders': [],
                },
                {
                    'name': '4庭审及裁决材料',
                    'subfolders': [
                        {
                            'name': '{{client_name}}_代理词.docx',
                            'template_path': '',
                            'type': 'file',
                            'use_template': False,
                        },
                    ],
                },
            ],
        },
        'variables': [
            {
                'key': 'client_name',
                'label': '被申请人名称',
                'required': True,
                'type': 'text',
            },
            {
                'default_value': '',
                'key': 'case_number',
                'label': '仲裁案号',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 50,
                    'min_length': 1,
                },
            },
            {
                'key': 'applicant_name',
                'label': '申请人名称',
                'required': False,
                'type': 'text',
            },
            {
                'default_value': '',
                'key': 'arbitration_institution',
                'label': '仲裁机构',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 100,
                },
            },
            {
                'default_value': '',
                'key': 'lawyer_name',
                'label': '承办律师',
                'required': False,
                'type': 'text',
                'validation': {
                    'max_length': 20,
                    'min_length': 2,
                },
            },
            {
                'default_value': '',
                'key': 'receive_date',
                'label': '收案日期',
                'required': False,
                'type': 'date',
                'validation': {
                    'format': '%Y-%m-%d',
                },
            },
            {
                'key': 'Cause_of_Action',
                'label': '案由',
                'required': False,
                'type': 'text',
            },
        ],
    },
]

DEFAULT_PINNED_CONFIG: Dict[str, Any] = {
    'global': [
        'criminal_simple_001',
        'civil_simple_001',
    ],
}

DEFAULT_APP_CONFIG: Dict[str, Any] = {
    'language': 'zh_CN',
    'theme': 'default',
    'check_updates': True,
    'last_template_id': '',
}

DEFAULT_GENERATION_CONFIG: Dict[str, Any] = {
    'default_output_dir': '',
    'auto_open_folder': True,
    'create_readme': False,
}

DEFAULT_UI_CONFIG: Dict[str, Any] = {
    'window_width': 1407,
    'window_height': 947,
    'show_preview': True,
}
