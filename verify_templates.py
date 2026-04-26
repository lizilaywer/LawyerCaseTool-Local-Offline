# -*- coding: utf-8 -*-
"""验证默认模板配置"""

from src.config.default_templates import DEFAULT_TEMPLATES

print(f'默认模板数量: {len(DEFAULT_TEMPLATES)}')
print('\n模板列表:')
for i, t in enumerate(DEFAULT_TEMPLATES, 1):
    var_count = len(t.get('variables', []))
    folder_count = len(t.get('folder_structure', {}).get('folders', []))
    print(f"{i}. {t['id']}: {t['name']} ({var_count}个变量, {folder_count}个文件夹)")

# 验证第一个模板的变量
if DEFAULT_TEMPLATES:
    first = DEFAULT_TEMPLATES[0]
    print(f"\n第一个模板 '{first['name']}' 的变量:")
    for v in first.get('variables', []):
        print(f"  - {v['label']} ({v['key']}): {v['type']}, 必填={v.get('required', False)}")
