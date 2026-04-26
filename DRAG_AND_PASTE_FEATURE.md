# 拖拽文件和粘贴图片功能

## 功能概述

在信息识别界面的左侧待识别文件区域，添加：
1. **拖拽文件**功能 - 支持鼠标拖拽文件到列表
2. **粘贴图片**功能 - 支持Ctrl+V粘贴截图

---

## 界面修改

### 新增输入框

在文件列表下方添加输入框：
- **提示文字**："截图贴入，输入文字无效"
- **边框样式**：虚线边框
- **功能**：接收Ctrl+V粘贴的图片

### 拖拽提示

原有提示文字："拖拽文件到此处或点击添加"

---

## 功能特性

### 1. 拖拽文件

**操作方式**：
- 从资源管理器选中文件
- 拖拽到左侧文件列表区域
- 释放鼠标，文件自动添加

**支持格式**：
- JPG、JPEG、PNG、BMP、TIFF
- PDF

**视觉反馈**：
- 拖拽进入时接受拖放
- 文件自动添加到列表

### 2. 粘贴图片

**操作方式**：
- 使用截图工具（QQ、微信、系统截图等）截图
- 点击粘贴输入框
- 按 Ctrl+V 粘贴
- 图片自动添加到列表

**处理逻辑**：
1. 检测剪贴板是否有图片数据
2. 将图片保存为临时文件
3. 添加到识别列表
4. 清空输入框
5. 显示成功提示

**错误提示**：
- 剪贴板中没有图片 → "剪贴板中没有图片"
- 剪贴板中是文字 → "剪贴板中是文字，不是图片\n请使用截图工具（如QQ/微信截图）后按Ctrl+V粘贴"

---

## 代码修改

### 修改文件

**`src/gui/widgets/image_list_widget.py`**

#### 1. 导入模块
```python
from PySide6.QtWidgets import (
    # ... 其他导入
    QLineEdit  # 新增
)
from PySide6.QtGui import (
    # ... 其他导入
    QDragEnterEvent, QDropEvent  # 新增
)
```

#### 2. 启用拖拽功能
```python
self._list_widget.setAcceptDrops(True)
self._list_widget.dragEnterEvent = self._drag_enter_event
self._list_widget.dragMoveEvent = self._drag_move_event
self._list_widget.dropEvent = self._drop_event
```

#### 3. 添加粘贴输入框
```python
self._paste_edit = QLineEdit()
self._paste_edit.setPlaceholderText("截图贴入，输入文字无效")
# 安装事件过滤器捕获粘贴事件
self._paste_edit.installEventFilter(self)
```

#### 4. 拖拽处理方法
```python
def _drag_enter_event(self, event: QDragEnterEvent):
    """拖拽进入事件"""
    if event.mimeData().hasUrls():
        event.acceptProposedAction()

def _drop_event(self, event: QDropEvent):
    """拖拽放下事件"""
    urls = event.mimeData().urls()
    file_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
    if file_paths:
        self.add_files(file_paths)
```

#### 5. 粘贴处理方法
```python
def _handle_paste(self):
    """处理粘贴事件"""
    clipboard = QApplication.clipboard()
    mime_data = clipboard.mimeData()
    
    if mime_data.hasImage():
        image = clipboard.image()
        # 保存为临时文件并添加
    elif mime_data.hasText():
        # 尝试作为文件路径处理
```

---

## 使用示例

### 场景1：拖拽添加文件

1. 打开资源管理器
2. 选中身份证图片文件
3. 拖拽到左侧文件列表区域
4. 文件自动添加到待识别列表

### 场景2：粘贴截图

1. 打开身份证图片
2. 使用QQ截图（Ctrl+Alt+A）截取身份证
3. 点击粘贴输入框
4. 按 Ctrl+V
5. 截图自动添加到待识别列表

---

## 样式说明

### 粘贴输入框
- **边框**：1px dashed #aaa（虚线）
- **背景**：#f8f8f8（浅灰）
- **聚焦**：边框变为蓝色，背景变为浅蓝
- **提示文字**：灰色，显示"截图贴入，输入文字无效"

---

*功能实现时间: 2026-03-26*
