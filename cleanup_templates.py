# -*- coding: utf-8 -*-
"""清理模板数据"""

import re

with open('src/config/default_templates.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 清理 ✓ 符号
content = content.replace('.docx ✓', '.docx')
content = content.replace('.docx  ✓', '.docx')

# 清理中文引号 " 和 "
content = content.replace('"{{', '{{')
content = content.replace('}}"', '}}')
content = content.replace('"{{', '{{')
content = content.replace('}}"', '}}')

# 清理测试文本
content = content.replace('文书材料打发打发', '文书材料')
content = content.replace('1文书材料', '1文书材料')

with open('src/config/default_templates.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('已清理模板数据')
