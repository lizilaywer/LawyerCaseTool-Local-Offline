# 变量定义排序功能

## 功能概述

在模板管理的"变量定义"模块中添加变量排序功能，支持：
1. 上移/下移按钮调整顺序
2. 拖拽排序

---

## 界面修改

### 按钮位置

在变量操作按钮区域新增上移、下移按钮：

```
[添加变量] [编辑变量] [删除变量] [↑ 上移] [↓ 下移]        [拉伸]
```

---

## 功能特性

### 1. 上移按钮 (↑ 上移)

- **位置**：删除变量按钮右侧
- **功能**：将选中的变量向上移动一位
- **限制**：
  - 第一个变量无法上移
  - 未选中变量时无效

### 2. 下移按钮 (↓ 下移)

- **位置**：上移按钮右侧
- **功能**：将选中的变量向下移动一位
- **限制**：
  - 最后一个变量无法下移
  - 未选中变量时无效

### 3. 拖拽排序

- **操作**：鼠标按住变量项，拖动到目标位置
- **效果**：变量插入到拖动位置
- **视觉反馈**：拖动时显示半透明效果

---

## 代码修改

### 修改文件

**`src/gui/template_manager.py`**

#### 1. 启用拖拽功能

```python
self._variables_list = QListWidget()
self._variables_list.setMinimumHeight(200)
# 启用拖拽排序
self._variables_list.setDragEnabled(True)
self._variables_list.setAcceptDrops(True)
self._variables_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
```

#### 2. 添加按钮

```python
# 上移/下移按钮
move_up_btn = self._create_btn("↑ 上移")
move_up_btn.clicked.connect(self._on_move_variable_up)
var_btn_layout.addWidget(move_up_btn)

move_down_btn = self._create_btn("↓ 下移")
move_down_btn.clicked.connect(self._on_move_variable_down)
var_btn_layout.addWidget(move_down_btn)
```

#### 3. 上移方法

```python
def _on_move_variable_up(self) -> None:
    """上移变量"""
    current_row = self._variables_list.currentRow()
    if current_row > 0:
        current_item = self._variables_list.takeItem(current_row)
        self._variables_list.insertItem(current_row - 1, current_item)
        self._variables_list.setCurrentItem(current_item)
```

#### 4. 下移方法

```python
def _on_move_variable_down(self) -> None:
    """下移变量"""
    current_row = self._variables_list.currentRow()
    if current_row >= 0 and current_row < self._variables_list.count() - 1:
        current_item = self._variables_list.takeItem(current_row)
        self._variables_list.insertItem(current_row + 1, current_item)
        self._variables_list.setCurrentItem(current_item)
```

---

## 使用说明

### 通过按钮排序

1. **选中变量**：点击变量列表中的某一项
2. **点击上移/下移**：变量移动一位，保持选中状态

### 通过拖拽排序

1. **按住变量**：鼠标左键按住要移动的变量
2. **拖动到位置**：拖动到目标位置
3. **释放鼠标**：变量插入到目标位置

### 保存排序

- 排序后点击右下角【保存】按钮生效
- 保存后模板中的变量顺序即为新顺序

---

## 示例

### 排序前

```
1. 委托人姓名 (client_name)
2. 案号 (case_number)
3. 被告名称 (opposing_party)
4. 受理法院 (court)
```

### 选中"被告名称"点击上移后

```
1. 委托人姓名 (client_name)
2. 被告名称 (opposing_party)  ← 上移
3. 案号 (case_number)
4. 受理法院 (court)
```

---

*功能实现时间: 2026-03-26*
