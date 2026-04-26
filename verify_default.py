# -*- coding: utf-8 -*-
from src.config.default_templates import DEFAULT_TEMPLATES

print(f'默认模板数量: {len(DEFAULT_TEMPLATES)}')
print('\n模板列表:')
for i, t in enumerate(DEFAULT_TEMPLATES, 1):
    var_count = len(t.get('variables', []))
    folder_count = len(t.get('folder_structure', {}).get('folders', []))
    print(f"{i}. {t['id']}: {t['name']}")
    print(f"   变量: {var_count}个, 文件夹: {folder_count}个")
    print(f"   模板文件: {t.get('template_file', 'N/A')}")
