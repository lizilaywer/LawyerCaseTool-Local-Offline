# Word 模板制作器 - 功能设计文档

## 一、需求概述

### 1.1 核心需求
用户希望能够自行制作 Word 模板，具体功能包括：
1. **上传 Word**：将 Word 文档上传到 `templates/civil`、`templates/criminal`、`templates/non_litigation` 三个分类文件夹
2. **预览 Word**：查看上传的 Word 文档内容
3. **变量替换**：将 Word 中的固定文字替换为变量（如 `{{client_name}}`）
   - **选中文字替换**：选中文本后从下拉菜单选择变量
   - **手动输入替换**：输入要查找的文字，批量替换为变量
   - **全部替换**：一键替换文档中所有相同关键词
   - **智能替换建议**：根据文字内容推荐变量
4. **格式保持**：替换操作完全保持原文档格式
   - 字体、字号、颜色
   - 加粗、斜体、下划线
   - 段落格式、行间距
   - 表格格式

### 1.2 设计目标
- 与现有"模板管理器"形成互补
- 让用户无需手动编辑 Word 就能制作模板
- 变量定义复用现有系统
- **格式零损失**

---

## 二、入口位置设计

### 2.1 入口方案

**方案：菜单栏 + 工具栏双重入口**

| 入口位置 | 操作路径 | 快捷键 |
|----------|----------|--------|
| 菜单栏 | 模板(T) → 制作 Word 模板 | Ctrl+M |
| 工具栏 | 点击"📝 制作模板"按钮 | - |

### 2.2 界面层级

```
主窗口 (MainWindow)
├── 菜单栏
│   └── 模板(T)
│       ├── 管理模板(&M)...     → TemplateManagerDialog
│       └── 制作 Word 模板      → TemplateMakerDialog  ← 新增
├── 工具栏
│   ├── 生成案卷
│   ├── 刷新模板
│   └── 制作模板               → TemplateMakerDialog  ← 新增
└── ...
```

---

## 二、现有架构分析

### 2.1 可复用的模块

| 模块 | 文件 | 可复用内容 |
|------|------|-----------|
| 变量系统 | `default_templates.py` | 变量定义格式（key, label, type） |
| 模板引擎 | `template_engine.py` | `extract_variables()` 变量提取 |
| 路径管理 | `template_path_manager.py` | 模板文件路径管理 |
| 配置管理 | `config_manager.py` | 配置存储机制 |

### 2.2 需要新增的模块

| 模块 | 文件 | 功能 |
|------|------|------|
| Word 编辑器 | `src/core/word_editor.py` | Word 文档编辑、变量替换 |
| 模板制作器界面 | `src/gui/template_maker.py` | 模板制作器主界面 |
| Word 预览控件 | `src/gui/widgets/word_preview.py` | Word 文档预览控件 |

---

## 三、技术可行性评估

### 3.1 Word 预览方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **QAxWidget + Word COM** | 完美预览、支持选中 | 仅限 Windows、依赖 Office | ⭐⭐⭐⭐⭐ |
| python-docx 读取文本 | 跨平台、简单 | 无格式、无选中 | ⭐⭐ |
| 转换为 HTML | 可渲染格式 | 转换复杂、可能失真 | ⭐⭐ |
| 转换为图片 | 可预览 | 文件大、不可选中 | ⭐⭐⭐ |

**推荐方案**: QAxWidget + Word COM
- 理由：本工具仅支持 Windows，且用户通常已安装 Office
- 可提供完美的预览和交互体验

### 3.2 Word 编辑方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **python-docx** | 纯 Python、格式保留好 | 无法处理复杂格式 | ⭐⭐⭐⭐⭐ |
| Word COM 自动化 | 功能完整 | 依赖 Office、速度慢 | ⭐⭐⭐ |
| docxtpl | 模板渲染优秀 | 不适合编辑 | ⭐⭐ |

**推荐方案**: python-docx
- 理由：已安装、格式保留较好、处理速度快

### 3.3 风险评估

| 风险项 | 风险等级 | 缓解措施 |
|--------|----------|----------|
| Office 版本兼容 | 低 | QAxWidget 兼容主流版本 |
| 复杂格式丢失 | 中 | 提示用户、测试常见格式 |
| 大文件性能 | 低 | 添加加载提示 |
| .doc 格式支持 | 中 | 自动转换为 .docx 或提示用户 |

**总体风险**: 低，技术方案成熟可行

---

## 四、界面设计方案

### 4.1 入口位置

**方案 A**: 在现有"模板管理器"中增加 Tab 页
- 优点：统一入口、共享变量定义
- 缺点：界面拥挤

**方案 B**: 新建独立的"模板制作器"窗口（推荐）
- 优点：界面清晰、功能聚焦
- 缺点：需要新增入口

**推荐方案 B**，在主窗口工具栏增加"模板制作器"按钮

### 4.2 界面布局

```
┌─────────────────────────────────────────────────────────────────┐
│                        模板制作器                                │
├──────────────┬────────────────────────────────┬─────────────────┤
│              │                                │                 │
│   模板库     │         Word 预览区            │    变量面板     │
│              │                                │                 │
│  ┌────────┐  │  ┌──────────────────────────┐  │  ┌───────────┐  │
│  │民事案件│  │  │                          │  │  │ 委托人姓名│  │
│  │ ├ 委托 │  │  │     Word 文档内容        │  │  │ client_name│  │
│  │ ├ 起诉 │  │  │                          │  │  ├───────────┤  │
│  │ └ ...  │  │  │   （支持选中文字）        │  │  │ 案号      │  │
│  ├────────┤  │  │                          │  │  │ case_number│  │
│  │刑事案件│  │  │                          │  │  ├───────────┤  │
│  └────────┘  │  └──────────────────────────┘  │  │ ...       │  │
│              │                                │  └───────────┘  │
│  [上传Word]  │  [替换选中] [全部替换] [保存]   │  [添加变量]     │
│              │                                │                 │
└──────────────┴────────────────────────────────┴─────────────────┘
```

### 4.3 操作流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  1. 上传    │ ──► │  2. 预览    │ ──► │  3. 替换    │
│  Word 文档  │     │  选中文字   │     │  为变量     │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  5. 管理    │ ◄── │  4. 保存    │
                    │  已有模板   │     │  到模板库   │
                    └─────────────┘     └─────────────┘
```

---

## 五、详细功能设计

### 5.1 模板库面板（左侧）

**功能**：
- 树形展示 `templates/` 下的三个分类文件夹
- 显示每个分类下的 Word 模板文件
- 支持上传新模板到指定分类
- 支持删除、重命名模板

**交互**：
- 点击模板文件 → 右侧预览
- 右键菜单：删除、重命名、复制
- 拖拽上传文件到分类

### 5.2 Word 预览区（中间）

**功能**：
- 使用 QAxWidget 嵌入 Word 预览
- 支持鼠标选中文字
- 高亮显示已有的 `{{变量}}`
- 工具栏：缩放、翻页

**交互**：
- 选中文本 → 右侧变量面板激活"替换选中"按钮
- 双击变量 → 显示变量详情

### 5.3 变量面板（右侧）

**功能**：
- 显示所有可用变量（从模板管理器同步）
- 支持添加自定义变量
- 智能推荐：根据选中文字推荐变量

**交互**：
- 点击变量 → 插入到选中位置
- 拖拽变量 → 插入到文档

### 5.4 替换工具栏

**功能**：
- **替换选中**：将选中的文字替换为选定的变量
- **手动输入替换**：输入要查找的文字进行替换
- **全部替换**：将文档中所有相同文字替换为变量
- **智能替换**：自动识别并替换常见词汇
- **撤销**：撤销上一步操作
- **保存**：保存修改到原文件

**格式保持机制**：
使用 python-docx 进行文本替换时，在 Run 级别操作，确保格式不丢失：

```python
def replace_text_with_format(doc, old_text, new_text):
    """替换文本并保持格式"""
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            if old_text in run.text:
                # 在 run 内部替换，格式保持不变
                run.text = run.text.replace(old_text, new_text)

    # 处理表格中的文本
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        if old_text in run.text:
                            run.text = run.text.replace(old_text, new_text)
```

---

## 六、代码架构设计

### 6.1 新增文件

```
src/
├── core/
│   └── word_editor.py          # Word 编辑器核心逻辑
├── gui/
│   ├── template_maker.py       # 模板制作器主窗口
│   └── widgets/
│       └── word_preview.py     # Word 预览控件
```

### 6.2 类设计

```python
# src/core/word_editor.py
class WordEditor:
    """Word 文档编辑器"""

    def load_document(path: Path) -> bool
    def save_document(path: Path) -> bool
    def replace_text(old_text: str, new_text: str, all: bool) -> int
    def get_selected_text() -> str
    def insert_variable(variable: str) -> bool
    def extract_all_text() -> str

# src/gui/widgets/word_preview.py
class WordPreviewWidget(QWidget):
    """Word 预览控件"""

    signal_text_selected = Signal(str)  # 文本选中信号

    def load_file(path: Path) -> bool
    def get_selected_text() -> str
    def highlight_variables(variables: List[str])

# src/gui/template_maker.py
class TemplateMakerDialog(QDialog):
    """模板制作器主窗口"""

    def _setup_ui()
    def _on_template_selected(template_path: Path)
    def _on_text_selected(text: str)
    def _on_replace_selected()
    def _on_replace_all()
    def _on_save_template()
```

### 6.3 数据流

```
用户操作 → TemplateMakerDialog → WordEditor → python-docx → 修改文件
                ↓
          WordPreviewWidget ← QAxWidget ← Word COM
                ↓
          signal_text_selected → 变量面板更新
```

---

## 七、实现计划

### Phase 1: 基础框架（预计 2-3 小时）
- [ ] 创建 `TemplateMakerDialog` 主窗口
- [ ] 实现左侧模板库树形结构
- [ ] 实现文件上传功能

### Phase 2: Word 预览（预计 2-3 小时）
- [ ] 创建 `WordPreviewWidget` 预览控件
- [ ] 集成 QAxWidget 调用 Word COM
- [ ] 实现文本选中信号

### Phase 3: 变量替换（预计 3-4 小时）
- [ ] 创建 `WordEditor` 核心类
- [ ] 实现文本替换功能
- [ ] 实现变量插入功能

### Phase 4: 变量面板（预计 1-2 小时）
- [ ] 实现变量列表显示
- [ ] 实现变量拖拽/点击插入
- [ ] 实现智能推荐

### Phase 5: 完善与测试（预计 2-3 小时）
- [ ] 添加撤销功能
- [ ] 添加保存功能
- [ ] 测试各种 Word 格式
- [ ] 编写单元测试

---

## 八、兼容性考虑

### 8.1 向后兼容
- 不修改现有模块的接口
- 新功能通过新模块实现
- 变量定义格式保持一致

### 8.2 平台兼容
- 主功能仅支持 Windows（QAxWidget）
- 可选：为非 Windows 提供简化版本（仅文本预览）

---

## 九、用户体验优化

### 9.1 操作提示
- 首次使用显示引导
- 替换操作显示预览
- 保存前提示备份

### 9.2 错误处理
- 文件损坏提示
- 格式不支持提示
- Office 未安装提示

### 9.3 快捷操作
- Ctrl+S 保存
- Ctrl+Z 撤销
- 双击变量快速插入

---

## 十、快速恢复指南

### 下次开发时，请先发送以下指令给 Claude Code：

```
请阅读以下文档，然后开始实现"Word 模板制作器"功能：

1. 设计文档：docs/WORD_TEMPLATE_MAKER_DESIGN.md
2. 设计稿：prototypes/template_maker_design.html（浏览器打开查看）

请从 Phase 1 开始实现，完成后告诉我进度。
```

### 相关文件位置

| 文件类型 | 路径 |
|----------|------|
| 设计文档 | `docs/WORD_TEMPLATE_MAKER_DESIGN.md` |
| UI 设计稿 | `prototypes/template_maker_design.html` |
| 主窗口代码 | `src/gui/main_window.py` |
| 模板管理器 | `src/gui/template_manager.py` |
| 模板引擎 | `src/core/template_engine.py` |

### 预计新增文件

```
src/
├── core/
│   └── word_editor.py          # Word 编辑器核心逻辑
├── gui/
│   ├── template_maker.py       # 模板制作器主窗口
│   └── widgets/
│       └── word_preview.py     # Word 预览控件
```

---

*文档版本: 1.1*
*创建日期: 2026-02-27*
*最后更新: 2026-02-27*
*作者: Claude Code*
