# -*- coding: utf-8 -*-
"""验证默认模板配置"""

from src.config.default_templates import DEFAULT_TEMPLATES

print(f'默认模板数量: {len(DEFAULT_TEMPLATES)}')
print('\n模板列表:')
for i, t in enumerate(DEFAULT_TEMPLATES, 1):
    print(f"{i}. {t['id']}: {t['name']}")
