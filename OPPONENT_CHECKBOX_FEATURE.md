# 对方当事人复选框功能

## 功能概述

在信息识别（OCR）界面添加"是否为对方当事人"复选框，用于区分我方和对方当事人的证件识别结果。

---

## 修改内容

### 1. 界面修改

**文件**: `src/gui/info_extraction_dialog.py`

在信息识别对话框右下角按钮区域添加了复选框：

```
[是否为对方当事人] [历史记录] [关闭] [保存并应用到案卷]
```

- 位置：右下角按钮区域
- 样式：13px字体，18x18复选框
- 提示：勾选后，识别生成的变量名将添加'opponent_'前缀以区分

### 2. 功能逻辑

#### 不勾选（默认状态）
识别生成的变量名和标签保持原样：
| 变量名 | 变量标签 |
|--------|----------|
| `name` | 姓名 |
| `id_number` | 身份证号 |
| `address` | 住址 |
| ... | ... |

#### 勾选状态
识别生成的变量名添加 `opponent_` 前缀，变量标签添加"对方"前缀：
| 变量名 | 变量标签 |
|--------|----------|
| `opponent_name` | 对方姓名 |
| `opponent_id_number` | 对方身份证号 |
| `opponent_address` | 对方住址 |
| ... | ... |

### 3. 适用场景

1. **双方证件识别**：同时识别我方和对方当事人的身份证
2. **避免变量冲突**：区分同名变量（如双方都有"姓名"）
3. **清晰标识**：一目了然知道变量属于哪一方

---

## 代码修改详情

### 导入模块
```python
from PySide6.QtWidgets import (
    # ... 其他导入
    QCheckBox  # 新增
)
```

### 创建复选框
```python
self._opponent_checkbox = QCheckBox("是否为对方当事人")
self._opponent_checkbox.setStyleSheet("""
    QCheckBox {
        font-size: 13px;
        color: #333;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
""")
self._opponent_checkbox.setToolTip("勾选后，识别生成的变量名将添加'opponent_'前缀以区分")
btn_layout.addWidget(self._opponent_checkbox)
```

### 3. 变量名和标签前缀处理

在 `_on_apply_to_template` 方法中（`info_extraction_dialog.py`）：

```python
# 检查是否为对方当事人
is_opponent = self._opponent_checkbox.isChecked()

for var_key, (value, _, match_type) in matches.items():
    # 如果是对方当事人，变量名添加前缀
    if is_opponent:
        var_key = f"opponent_{var_key}"
    
    apply_data[var_key] = value
    
    if match_type == 'new':
        # 获取字段标签
        label = self._field_matcher.get_recognized_field_label(
            var_key, result.document_type
        )
        # 如果是对方当事人，标签也添加"对方"前缀
        if is_opponent:
            label = f"对方{label}"
        new_vars.append({
            'key': var_key,
            'label': label,
            'value': value,
            'source_field': var_key
        })
```

### 4. 主窗口标签处理

在 `_get_field_label` 方法中（`main_window.py`）：

```python
def _get_field_label(self, var_key: str) -> str:
    label_mapping = {
        'name': '姓名',
        'gender': '性别',
        'id_number': '身份证号',
        'client_name': '委托人姓名',
        # ... 其他映射
    }
    
    # 检查是否为对方当事人变量（以 opponent_ 开头）
    if var_key.startswith('opponent_'):
        base_key = var_key[9:]  # 去除前缀
        
        # 特殊处理：client_name 对方当事人显示为"对方姓名(名称)"
        if base_key == 'client_name':
            return "对方姓名(名称)"
        
        base_label = label_mapping.get(base_key, base_key)
        return f"对方{base_label}"
    
    return label_mapping.get(var_key, var_key)
```

**特殊处理说明**：
- `client_name` 的普通标签是"委托人姓名"
- 对方当事人的 `opponent_client_name` 标签显示为"**对方姓名(名称)**"（而不是"对方委托人姓名"）

### 提示信息

当勾选复选框时，提示信息会显示：
```
已自动填充 X 个变量（对方当事人）到案卷表单。

匹配现有变量: X 个
创建新变量: X 个

变量名已添加 'opponent_' 前缀
```

---

## 使用示例

### 场景：民事案件双方证件识别

1. **识别我方当事人身份证**
   - 不勾选复选框
   - 识别结果：`name=张三`, `id_number=110101...`
   - 应用到案卷：
     | 变量名 | 变量标签 | 值 |
     |--------|----------|-----|
     | `name` | 姓名 | 张三 |
     | `id_number` | 身份证号 | 110101... |

2. **识别对方当事人身份证**
   - 勾选"是否为对方当事人"
   - 识别结果：`client_name=李四`, `id_number=310101...`
   - 应用到案卷：
     | 变量名 | 变量标签 | 值 |
     |--------|----------|-----|
     | `opponent_client_name` | **对方姓名(名称)** | 李四 |
     | `opponent_id_number` | 对方身份证号 | 310101... |
     
   > 注意：`client_name` 对方当事人特殊显示为"**对方姓名(名称)**"而不是"对方委托人姓名"

3. **在模板中使用**
   - 我方信息：`{{name}}`, `{{id_number}}`
   - 对方信息：`{{opponent_name}}`, `{{opponent_id_number}}`

---

## 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/gui/info_extraction_dialog.py` | 添加 QCheckBox 导入、创建复选框、修改变量名和标签处理逻辑 |
| `src/gui/main_window.py` | 修改 `_get_field_label` 方法，支持对方当事人标签 |

---

## 测试验证

- [x] QCheckBox 导入正确
- [x] 复选框创建成功
- [x] 复选框文本正确
- [x] `_save_and_apply` 方法前缀处理正确
- [x] `_on_apply_to_template` 方法前缀处理正确
- [x] 提示信息更新正确

---

*功能实现时间: 2026-03-26*
