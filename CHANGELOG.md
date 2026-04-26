# 更新日志

本文档记录案件文件夹管理系统的开发历程和版本更新。

## [2.0.0] - 2026-04-21

### 工作台全面重构与交互链路打通

这是一次大版本更新，核心目标是把 Dashboard（工作台）从"只能看"变成"真正能点、能跳、能操作"。

**快捷操作全面重映射**：
1. `+ 新建案件` → `📁 导入案件`：原按钮与顶部工具栏重复，改为直接唤起案件导入对话框，完成后自动跳转到案件中心
2. `+ 新建期限`：修复点击无反应，现在跳转日历界面并自动打开"添加期限"对话框
3. `📄 文书中心` → `📨 法院短信`：跳转工具中心并直接切换到"法院短信"标签页
4. `🔍 OCR识别`：修复点击无反应，跳转创建中心并打开信息识别对话框
5. `📁 导入案件` → `🖼️ 截图合并`：跳转工具中心并直接切换到"截图合并"标签页
6. `⚠️ 目录异常`：跳转案件中心并自动筛选"目录缺失"案件

**顶部工具栏修复**：
- 右上角 `+ 新建案件` 按钮修复，点击后跳转到创建中心

**Dashboard 图表交互**：
- 横向柱状图新增 hover 高亮效果（蓝色外圈）
- 修复 hover 时蓝色外圈与填充之间的白边问题
- 修复案件数为 1 时红色填充溢出边框的问题（QPainterPath clip 裁剪）
- 柱状图分类点击后跳转到案件中心并自动应用对应分类筛选

**案件中心 UI 优化**：
- 筛选面板在"分类 / 状态 / 目录 / 标签"四组之间添加水平分隔线，视觉层次更清晰
- `set_filter()` API 扩展支持 `directory_value` 参数

**Bug 修复**：
- 修复 `dashboard_widget.py` 中 `QCursor` 错误地从 `PySide6.QtCore` 导入的问题（正确应为 `PySide6.QtGui`）

## [1.6.1] - 2026-04-18

### 核心稳定性修复与产品重定位

**Bug 修复**：
1. `config_manager.py`：配置和模板读取/重置改为深拷贝，避免调用方修改返回值后污染运行时状态
2. `case_manager.py`：物理删除目录失败时完整回滚案件索引，恢复路径/历史/搜索/排序缓存
3. `template_path_manager.py`：修复 macOS/Linux 绝对路径解析，并按“分类 + 文件名”去重，避免跨分类串档
4. `template_engine.py`：空值改为显式保留 `{{variable}}` 占位符，避免 docxtpl/Jinja 将字段渲染为空串
5. `word_editor.py`：另存为后更新当前文档路径，后续“保存”继续写回新文件

**测试补充**：
- 新增模板路径管理器测试
- 补充配置深拷贝、案件删除回滚、空值占位符、另存为路径切换回归测试

**产品命名与定位**：
- 对外名称统一调整为“案件文件夹管理系统”
- 产品定位更新为“以本地文件夹为核心载体的案件管理桌面应用”
- 为兼容现有用户数据，运行时配置目录继续沿用 `LawyerCaseTool`

## [1.6.0] - 2026-04-18

### 截图合并 PDF 功能上线

**功能新增**：工具中心新增「截图合并」Tab，用于将微信聊天记录截图等图片批量合并为 PDF。

**新增功能**：
1. 图片导入：支持拖放文件夹/文件、点击选择文件夹导入
2. 排序规则：手动拖拽排序、正序/倒序（按文件名数字排序）
3. 布局设置：每页 1/2/3 张图片，横向/纵向 A4，页边距与图片间距可调
4. 标签系统：位置（上方/下方/不显示）、模式（自动编号/自定义前缀/文件名/不显示）、文字大小 5 挡位
5. 保存方式：支持「保存到源文件夹」自动落盘，或弹出保存对话框
6. 视图切换：缩略图视图（120×120）与列表视图可切换，双击打开图片

**新增文件**：
- `src/core/screenshot_pdf_merger.py` — 核心引擎（fpdf2 + Pillow）
- `src/gui/widgets/screenshot_image_list.py` — 自定义图片列表控件
- `tests/test_screenshot_pdf_merger.py` — 单元测试

**修改文件**：
- `src/gui/tool_center_dialog.py` — 新增 Tab 与界面集成
- `requirements-core.txt` — 新增 `fpdf2` 依赖

---

## [1.5.0] - 2026-04-17

### 全面性能审查与优化

**性能优化**：
1. 案件索引管理器：`batch_update` 批量模式、路径/搜索/排序内存索引、线程锁保护，磁盘 I/O 减少 90%+
2. 法院短信服务：`requests.Session` + 连接池 + 自动重试、并发下载、正则预编译、流式写入
3. 批量处理器：`ThreadPoolExecutor` 并发生成案卷，速度提升 2~5 倍
4. Word 模板引擎：修复缓存未命中时双次读取问题
5. UI 后台线程化：法院短信 I/O 操作全部移至 `QThread`，消除 UI 冻结

**新增文件**：
- `PERFORMANCE_OPTIMIZATION_REPORT.md` — 性能优化报告

**修改文件**：
- `src/core/case_manager.py` — 批量模式 + 索引优化
- `src/core/court_sms_service.py` — 网络层重构
- `src/core/batch_processor.py` — 并发批量处理
- `src/core/template_engine.py` — I/O 优化
- `src/gui/tool_center_dialog.py` — 后台线程化

---

## [1.4.0] - 2026-03-31

### 全面代码审查与功能优化

本次更新包含新功能开发、Bug 修复和全面代码质量审查。

---

### 电子化归档 - 图片预览缩放控件

**功能新增**：电子化归档中图片预览新增缩放工具栏，与 PDF 预览体验一致。

**新增功能**：
1. 放大/缩小按钮
2. 适应宽度、适应窗口、原始大小切换
3. 缩放比例实时显示
4. 图片预览自动隐藏翻页控件（图片为单页）

**技术实现**：
- 复用 PDF 工具栏基础设施，翻页控件封装为 `_page_nav_widget`
- 新增 `_render_image()` 方法，支持 4 种 fit mode
- 缩放回调根据 `_current_type` 分发到图片/PDF 渲染

**修改文件**：`src/gui/widgets/archive_preview.py`

---

### 信息识别 - 对方当事人智能映射

**功能改进**：在被告/被申请人模板中勾选"是否为对方当事人"后，对方姓名直接填入原告/申请人变量。

**映射规则**：
| 模板 | 对方姓名填入 |
|------|------------|
| 民事案件简易模板(被告) | 原告名称 (`plaintiff_name`) |
| 行政案件简易模板(被告) | 原告名称 (`plaintiff_name`) |
| 劳动仲裁简易模板(被申请人) | 申请人姓名 (`applicant_name`) |
| 商事仲裁简易模板(被申请人) | 申请人名称 (`applicant_name`) |

**修改文件**：
- `src/gui/info_extraction_dialog.py` - 新增 `OPPONENT_DIRECT_MAP`，修改 `_on_apply_to_template()` 和 `_save_and_apply()`
- `src/gui/main_window.py` - 传入 `template_id` 参数

---

### 默认配置同步

**功能改进**：将运行时配置（templates.json、config.json）同步为代码默认值。

**同步内容**：
- 10 个模板的完整配置（含 Word 模板关联路径、用户自定义变量）
- 置顶模板设置
- 应用配置、生成配置、UI 配置

**消除重复**：
- `config_manager._get_default_config()` 改为直接引用 `DEFAULT_*_CONFIG` 常量
- 修复了默认配置不一致的问题

**修改文件**：
- `src/config/default_templates.py` - 从运行时配置重新生成
- `src/config/config_manager.py` - `_get_default_config()` 消除重复定义

---

### Bug 修复

1. `archive_engine.py`：`get_config_dir()` → `.config_dir`（property 不是方法）
2. `archive_engine.py`：删除冗余的 DocxTemplate 加载
3. `generation_dialog.py`：root_path 空值检查 + subprocess 替换 os.system（修复命令注入）
4. `pdf_utils.py`：compress_pdf 用 `_updateObject` 替换 `_deleteObject`（修复图片丢失）
5. `config_manager.py`：6 处 `.copy()` → `copy.deepcopy()`（修复浅拷贝数据共享）
6. `default_templates.py`：6 个模板分类从 "criminal" 修正为正确值

---

### 代码质量

- 新建 `src/gui/styles.py`：统一配色方案 `APP_COLORS` + `CATEGORY_NAMES`，12 个文件 14 处去重
- 变量正则统一为 `r'\{\{(\w+)\}\}'`（4 个文件）
- `file_utils.py` write_json_file 改为原子写入
- `validators.py` 增强文件夹名校验（尾部点号/空格/控制字符）
- `config_manager.py` bare except → except OSError
- `registry_manager.py` WindowsError → OSError
- `paddle_engine.py` 简化初始化，统一日志
- `info_storage.py` 改用原子写入

---

### 死代码清理

- 删除 5 个空解析器文件（base_parser、document_detector、civil_parser、judgment_parser、ruling_parser）
- `folder_tree.py`：删除 7 个死方法（FolderTreePreview）
- 删除 ScreenshotOverlay、BatchOCRResultWidget 类
- 清理 7 个文件的未使用导入

---

### UI 修复

- 隐藏无功能的"保存草稿"按钮
- 面包屑导航改为动态更新

---

### 测试

18/18 全部通过。

---

## [1.3.3] - 2026-03-28

### 电子化归档 - 变量设置高亮修复

**问题修复**：修复了在电子化归档界面中，选中文字右键"设置为变量"后，变量占位符没有被高亮显示的问题。

**修复内容**：
1. **即时替换与高亮**：选中文字后，立即替换为 `{{变量名}}` 占位符
2. **实时高亮刷新**：替换后自动重新高亮所有变量（绿色背景）
3. **文本同步更新**：更新内部文本缓存，确保保存时包含最新变量

**技术实现**：
- 修改 `_on_set_variable()` 方法，在发送信号前先执行文本替换
- 调用 `_highlight_text_with_variables()` 重新渲染全部变量高亮
- 保持与Word模板制作器一致的绿色高亮样式

**修改文件**：`src/gui/widgets/archive_preview.py`

---

### 电子化归档 - 变量面板拖拽排序与卡片化

**界面优化**：重新设计左侧变量面板，支持拖拽排序和卡片化展示。

**改进内容**：
1. **卡片化设计**：每个变量项改为圆角卡片，带阴影和悬停效果
2. **拖拽排序**：按住卡片左侧 "≡" 手柄或任意位置拖动，可自由调整变量顺序
3. **放置指示器**：拖拽时显示蓝色指示条，清晰标示插入位置
4. **视觉反馈**：拖拽时卡片半透明跟随鼠标

**技术实现**：
- 重写 `VariableItem` 类，添加 `mousePressEvent`、`mouseMoveEvent` 支持拖拽
- 实现 `dropEvent` 处理变量重新排序逻辑
- 添加 `DropIndicator` 显示放置位置

**修改文件**：`src/gui/widgets/archive_variable_panel.py`

---

### OCR截图提示优化

**界面微调**：根据用户反馈调整OCR截图提示文字。

**修改内容**：
- 提示文字从 "放大后识别更清楚，建议PDF比例调到150%" 改为 "放大后识别更清楚，建议PDF比例调到100%"
- 识别结果自动复制到系统剪贴板，方便粘贴使用

**修改文件**：
- `src/gui/widgets/screenshot_tool.py` - 提示文字
- `src/gui/widgets/archive_variable_panel.py` - 剪贴板复制

---

## [1.3.2] - 2026-03-26

### 电子化归档 - 保存与另存为功能

**功能改进**：在电子化归档界面添加文档保存功能，支持将设置了变量的文档保存回原文件或另存为新文件。

**新增功能**：
1. **保存按钮**：将当前预览内容（含变量占位符）保存回原文件
2. **另存为按钮**：选择新位置保存，默认文件名格式为 `原文件名_已设置变量.docx`
3. **格式保留**：基于原始文档进行变量替换，完整保留原有格式（字体、字号、段落样式等）
4. **变量记录**：自动记录变量替换操作，保存时批量应用

**技术实现**：
- 复制原始文档到目标位置（`shutil.copy2`）
- 遍历段落和表格单元格，定位原文本位置
- 替换为变量占位符，同时保持第一个Run的格式

**修改文件**：
- `src/gui/archive_dialog.py` - 添加保存/另存为处理方法
- `src/gui/widgets/archive_preview.py` - 添加按钮和信号

---

### 电子化归档 - 变量高亮颜色统一

**界面优化**：将变量高亮颜色从蓝色改为绿色，与Word模板制作器保持一致。

**颜色值**：
- 背景色：`#d4edda` (RGB: 212, 237, 218)
- 文字色：`#155724` (RGB: 21, 87, 36)

**修改文件**：`src/gui/widgets/archive_preview.py`

---

### 配置管理 - 当前状态保存为默认

**功能改进**：将当前软件状态（模板、Word关联、置顶设置等）保存为默认配置，点击"重置默认"即可恢复。

**包含内容**：
- 10个模板的完整配置和变量定义
- Word模板关联配置
- 置顶模板设置
- 应用配置（语言、主题等）
- 生成配置（输出目录等）
- UI配置（窗口大小等）

**使用方式**：
- 设置对话框 → 恢复默认
- 模板管理 → 重置默认

**修改文件**：
- `src/config/default_templates.py` - 更新为当前状态
- `src/config/config_manager.py` - 修改重置逻辑

---

## [1.3.1] - 2026-03-25

### Word 模板制作器 - 添加自定义变量功能增强

**功能改进**：将"+ 添加自定义变量"功能与模板管理的"变量定义"进行深度整合。

**改进内容**：
1. **统一界面**：添加变量对话框与模板管理器变量定义界面保持一致
2. **完整字段**：支持设置键名、标签、类型、必填、归属模板
3. **模板关联**：新增"归属模板"下拉选择，可将变量直接添加到指定模板
4. **自动保存**：变量自动保存到对应模板的配置中，实现全局同步

**界面字段**：
- **键名***：变量键名（英文，如 `client_name`）
- **标签***：显示名称（如 `委托人姓名`）
- **类型**：文本 / 日期 / 下拉选择 / 数字
- **必填**：是 / 否
- **归属模板***：选择10个默认模板之一

**修改文件**：`src/gui/template_maker.py`

---

### Word 模板制作器功能修复

**问题描述**：在 Word 模板制作器中，选中包含空格的文字或跨格式的文字（如公司名称"安徽省仁盛实业有限公司"）无法替换为变量。

**根本原因**：Word 文档中的文本可能被分割成多个 Run 对象，原替换逻辑只在单个 Run 内检查匹配，无法处理跨 Run 的文本。

**修复方案**：重写 `_replace_in_paragraph` 方法：
1. 在段落级别检查文本是否存在
2. 构建 Run 映射表，定位匹配文本跨越的 Run 范围
3. 支持跨 Run 的文本替换，保持第一个 Run 的格式
4. 从后向前处理多个匹配位置，避免位置偏移问题

**修改文件**：`src/core/word_editor.py`

**测试验证**：
- ✅ 跨 Run 文本替换（公司名称等）
- ✅ 包含空格的文本替换
- ✅ 单 Run 内的文本替换（向后兼容）

---

## [1.3.0] - 2026-03-20

### 新增电子化归档功能

**功能目的**：为律师提供从现有案卷文件夹中提取信息、生成标准化归档文档的能力。

**核心流程**：
```
选择案卷文件夹 → 浏览文件结构 → 提取变量信息 → 选择归档模板 → 替换导出
```

#### 界面设计

**三栏布局**：
- 左侧：变量定义面板（280px）
  - 变量名称 + 变量名 + 值输入框
  - 支持导入/导出 JSON
  - 与主界面模板变量系统同步（只增不减）
- 中间：文件预览区（自适应）
  - 支持 Word(.docx)、PDF、图片预览
  - 变量高亮显示
  - 右键菜单：设置为变量、定义为变量字段
- 右侧：文件夹结构树（300px）
  - 显示完整目录结构
  - 📁📄🖼️ 图标系统
  - 单击重命名、双击打开、拖拽移动

#### 新增文件

| 文件 | 说明 |
|------|------|
| `src/gui/archive_dialog.py` | 电子化归档主对话框 |
| `src/gui/widgets/archive_file_tree.py` | 文件夹结构树控件 |
| `src/gui/widgets/archive_variable_panel.py` | 变量定义面板 |
| `src/gui/widgets/archive_preview.py` | 文件预览控件 |
| `src/core/archive_engine.py` | 归档引擎 |
| `docs/ARCHIVE_FEATURE_PLAN.md` | 功能设计文档 |

#### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/gui/main_window.py` | 添加"电子化归档"入口按钮 |

#### 技术实现

- **变量同步机制**：从主界面模板系统获取变量，只增不减
- **文件预览**：使用 python-docx 和 PyMuPDF 实现文档预览
- **变量高亮**：使用 QTextCharFormat 实现变量高亮显示
- **右键菜单**：支持设置为变量、定义为变量字段两种操作
- **历史记录**：保存到 `%APPDATA%/LawyerCaseTool/archive/history.json`

#### 数据存储

- 变量定义：`%APPDATA%/LawyerCaseTool/archive/variables.json`
- 历史记录：`%APPDATA%/LawyerCaseTool/archive/history.json`

---

## [1.2.21] - 2026-03-15

### 模板管理界面优化

**文件夹结构树图标化**：
- 📁 文件夹图标（所有层级）
- 📄 普通文件图标
- 📎 已关联模板的文件图标
- 新增/重命名/更新时自动保持图标

### 版本迭代记录

**v1.2.20** - 模板管理界面紧凑化（基本信息区域）  
**v1.2.19** - 模板管理界面边框精简（Modern UI v3风格）  
**v1.2.18** - 模板制作器工具栏按钮整合  
**v1.2.17** - 修复Word编辑器加载问题  
**v1.2.16** - 修复单击/双击事件冲突  
**v1.2.15** - 模板制作器文件操作优化（单击重命名、双击打开）  
**v1.2.14** - 展开/收缩按钮  
**v1.2.13** - 文件浏览器重构  

## [1.2.15] - 2026-03-15

### 模板制作器文件操作优化

**单击重命名**：
- 单击左侧文件/文件夹项：进入编辑模式，可修改名称
- 编辑完成后自动执行重命名操作
- 如果名称已存在或为空，会提示错误并恢复原名称

**双击打开**：
- 双击 Word 文档：在中间预览区打开进行编辑
- 双击其他文件：使用系统默认程序打开

## [1.2.14] - 2026-03-15

### 模板制作器优化

**展开/收缩按钮**：
- 将刷新按钮改为展开/收缩切换按钮
- 📂 状态：点击展开所有文件夹
- 📁 状态：点击收缩所有文件夹
- 按钮为切换状态，可一键展开/收缩全部

## [1.2.13] - 2026-03-15

### 模板制作器重构

**左侧文件浏览器**：
- 改为实时显示 `templates` 文件夹的实际文件结构
- 支持递归浏览子文件夹
- 文件类型图标：📁 文件夹、📄 Word 文档、📑 PDF、📝 文本、⚙️ 配置等
- 双击文件直接打开编辑（Word 文档在预览区打开，其他文件用系统默认程序）

**底部按钮**：
- 将"上传 Word 文档"改为"📂 打开文件"按钮

## [1.2.12] - 2026-03-15

### 模板制作器优化（已废弃）

**左侧模板库更新**（此版本已废弃，v1.2.13 改为文件浏览器）：
- ~~从 ConfigManager 加载所有模板~~
- ~~支持分类显示~~

**UI 风格统一（Modern UI v3）**：
- 配色方案与主界面保持一致
- 工具栏按钮样式统一

## [1.2.11] - 2026-03-15

### 界面优化

**工具栏按钮调整**：
- 移除"生成案卷"和"刷新"按钮
- 新增"模板管理"按钮（蓝色主按钮样式）
- "制作模板"按钮保留（白色边框样式）

## [1.2.9] - 2026-03-15

### 界面优化

**置顶按钮位置调整**：
- 将置顶按钮移到左侧模板面板的分类筛选栏
- 位于分类按钮（全部、民事、刑事等）右侧，与筛选按钮保持对齐
- 采用图标按钮形式（📌），固定大小 28x28，更加紧凑和谐
- 选中模板后显示，未选中时隐藏

## [1.2.8] - 2026-03-15

### 界面优化

**置顶按钮位置调整**：
- 将置顶按钮从文件夹预览面板内部移到标题栏
- 置顶按钮与"文件夹结构预览"标题对齐，位于同一行
- 按钮大小适中（11px字体，3px 10px内边距），与周围元素协调

## [1.2.7] - 2026-03-15

### 新增模板置顶功能

**功能特点**：
- 右侧预览面板添加置顶按钮（📌 置顶）
- 模板卡片显示置顶标记（📌）
- 置顶模板自动排在列表最前面

**置顶规则**：
- "全部"分类下最多可置顶 3 个模板
- 各分类下（民事、刑事、行政、非诉、仲裁）最多可置顶 1 个模板
- 全局置顶优先级高于分类置顶

**技术实现**：
- ConfigManager 新增置顶模板存储（`pinned.global` 和 `pinned.by_category`）
- FolderTreePreview 添加置顶按钮和信号
- 模板列表按置顶状态自动排序

## [1.2.6] - 2026-03-15

### 新增9个简易模板

**新增模板列表**：
1. 民事案件简易模板(原告)
2. 民事案件简易模板(被告)
3. 刑事案件简易模板
4. 行政案件简易模板(原告)
5. 行政案件简易模板(被告)
6. 劳动仲裁简易模板(申请人)
7. 劳动仲裁简易模板(被申请人)
8. 商事仲裁简易模板(申请人)
9. 商事仲裁简易模板(被申请人)

**模板特点**：
- 仅保留4个核心文件夹（委托手续、文书材料、证据材料、检索及其他）
- 精简文件数量，仅生成必要性文件
- 适用于简单案件，提高工作效率

**技术改进**：
- 自动合并新默认模板机制（保留用户自定义模板）
- 添加"行政"分类筛选按钮
- 更新模板卡片分类映射（支持所有分类的颜色标识）

**模板总数**：17个（8个完整版 + 9个简易版）

## [1.2.5] - 2026-03-15

### UI 全面现代化改造

本次更新对应用界面进行了全面的现代化改造，提升了视觉美观度和用户体验。

#### 主窗口界面优化

**布局改进**:
- 三栏式布局优化：左侧模板面板 (280px) | 中间表单区域 (自适应) | 右侧预览面板 (320px)
- 统一 16px 水平边距，视觉对齐一致
- 现代化工具栏：使用 QWidget 容器替代 QToolBar，避免样式覆盖问题

**颜色系统升级**:
- 主色调：专业蓝 `#3b82f6`
- 背景层次：`#ffffff` (表面0) → `#f8fafc` (表面1) → `#f1f5f9` (表面2)
- 文字层次：`#0f172a` (主文字) → `#475569` (次要) → `#64748b` (第三级)
- 边框统一：`#e2e8f0` 标准边框

**模板卡片改进** (`src/gui/widgets/template_card.py`):
- 全新卡片设计：圆角 8px、白色背景、淡灰边框
- 类别标签改为按钮样式，带边框和圆角
- 悬停效果：边框变蓝色
- 选中状态：浅蓝背景 + 蓝色边框
- 添加编辑按钮 (✎)，悬停显示
- 删除多余 "..." 按钮

**表单区域优化** (`src/gui/widgets/variable_input.py`):
- 输入框高度从 36px 缩减到 28px，更紧凑
- 统一内边距和间距
- 添加蓝色聚焦状态

**文件夹树预览** (`src/gui/widgets/folder_tree.py`):
- 使用 Emoji 图标：📁 文件夹、📄 文件
- 选中状态：透明背景 + 文字加粗（无蓝色反色）
- 统计区域：扁平化设计，无边框痕迹
- **新增功能**：支持拖拽排序、双击编辑名称
- **新增功能**：编辑后可保存到模板

**OCR 区域改进**:
- 去除边框，使用浅蓝圆角背景
- 更紧凑的布局

#### 搜索与筛选功能

**模板搜索**:
- 实时搜索：输入时即时过滤模板
- 搜索范围：模板名称和描述

**分类筛选**:
- 5 个分类按钮：全部、民事、刑事、非诉、仲裁
- 选中状态：蓝色背景和文字
- 悬停效果：浅灰背景

#### 新增功能

**图标系统**:
- 设计并生成应用图标（25 个尺寸 + ICO 文件）
- 文件夹 + 文档的现代扁平化设计
- 主色调：专业蓝 `#3b82f6`

**文件夹预览编辑**:
- 支持拖拽调整文件夹/文件顺序
- 双击编辑文件夹/文件名称
- 修改后可保存到模板
- 添加"保存修改"和"刷新"按钮

#### 修复问题

- 修复 `QLineEdit` 导入缺失
- 修复 `KeyError: 'accent_subtle'` 颜色缺失
- 修复字符串格式化错误（使用 f-string 替代 .format()）
- 修复选中项蓝色背景反色问题

#### 修改文件

- `src/gui/main_window.py` - 主窗口 UI 现代化
- `src/gui/widgets/template_card.py` - 模板卡片重写
- `src/gui/widgets/variable_input.py` - 输入控件优化
- `src/gui/widgets/folder_tree.py` - 文件夹树增强
- `scripts/generate_icons.py` - 图标生成脚本（新增）
- `resources/icons/` - 图标资源（新增）

## [1.2.4] - 2026-03-15

### 项目全面审查与整理

今天进行了一次彻底的项目大扫除，就像春节前的家庭大扫除一样，把积攒的"技术债务"和"文档包袱"都清理了一遍。

#### 删除冗余文档 ✅
**背景**: 项目中积累了大量重复的修复总结文档，它们的内容都已经整合到了 CHANGELOG.md 中
**删除文件**:
- FIX_SUMMARY_PART2.md
- FIX_SUMMARY_TEMPLATE_MANAGER.md  
- FIX_SUMMARY_TEMPLATE_SAVE_DELETE.md
- FIX_SUMMARY_WORD_TEMPLATE.md
- FIX_SUMMARY_OCR_FIELD_APPLY.md
- RELEASE_NOTES_v1.0.1.md
- RELEASE_NOTES_v1.0.2.md
- IMPLEMENTATION_SUMMARY.md

**效果**: 项目根目录从 17 个文档减少到 9 个，更加清爽

#### 代码问题修复 ✅

##### 1. PySide6 弃用 API 清理
**问题**: `app.py` 中使用了 PySide6 6.4.0+ 已弃用的高 DPI 设置 API
**修复**: 删除 `Qt.AA_EnableHighDpiScaling` 和 `Qt.AA_UseHighDpiPixmaps` 设置
**说明**: PySide6 新版本默认启用高 DPI，无需手动设置

##### 2. 版本号统一
**问题**: 
- `pyproject.toml` 中版本号为 1.0.0（严重过时）
- `main_window.py` 关于对话框硬编码为 1.1.4
**修复**:
- 更新 `pyproject.toml` 版本号为 1.2.4
- 关于对话框改为动态获取版本号

##### 3. OCR 文档更新
**问题**: `INFO_EXTRACTION_FEATURE.md` 仍建议使用已弃用的 PaddleOCR
**修复**: 更新为当前使用的 RapidOCR

##### 4. 窗口标题显示版本号
**修改**: 主窗口标题改为动态显示产品名称与版本号
**文件**: `src/gui/main_window.py`
**效果**: 用户可以在窗口标题栏直接看到当前版本号

##### 5. 测试修复
**修复文件**:
- `test_template_engine.py` - 更新 None 值处理测试
- `test_config_manager.py` - 更新模板名称预期

**测试结果**: 18/18 全部通过 ✅

---

## [1.2.3] - 2026-03-13

### 代码质量全面审查与修复

本次更新是一次全面的代码审查和优化，修复了多个线程安全、性能和安全隐患问题。

#### 高优先级修复（严重问题）

##### 1. 单例模式线程安全问题 ✅
**问题**: `PathManager` 和 `LoggerManager` 的单例实现没有线程锁保护
- **类比**: 银行柜台没有排队系统，多线程同时访问可能混乱
- **影响**: 多线程环境下可能创建多个实例，导致状态不一致
- **修复**: 添加 `threading.Lock` + 双重检查锁定模式

**修改文件**:
- `src/config/path_manager.py` - 添加线程锁和 `_initialized` 标志
- `src/utils/logger.py` - 添加线程锁和 `_initialized` 标志

##### 2. 批量处理器竞态条件 ✅
**问题**: `BatchProcessor` 使用普通布尔值 `_cancelled` 作为取消标志
- **类比**: 两个人同时操作同一个开关，最后状态不可预测
- **影响**: 多线程访问时可能读取到过时的值
- **修复**: 使用 `threading.Event` 替代布尔标志

**修改文件**:
- `src/core/batch_processor.py` - `_cancel_event` 替代 `_cancelled`

##### 3. 配置文件写入不安全 ✅
**问题**: 直接写入目标文件，如果中途崩溃会导致配置文件损坏
- **类比**: 写日记时停电，本页损坏
- **影响**: 配置丢失，应用无法启动
- **修复**: 实现原子写入 - 先写入临时文件，成功后再替换

**修改文件**:
- `src/config/config_manager.py` - 添加 `safe_write_json()` 函数

#### 中优先级修复（性能问题）

##### 1. 模板引擎重复加载 ✅
**问题**: 每次渲染都重新从磁盘加载 Word 模板
- **类比**: 每次查单词都要去书店买新字典
- **影响**: 性能下降，特别是批量处理时
- **修复**: 添加模板字节缓存机制 + TTL 过期

**修改文件**:
- `src/core/template_engine.py` - 添加 `_template_cache` 和缓存清理

##### 2. 资源清理不彻底 ✅
**问题**: `variable_input.py` 清理控件时未断开信号连接
- **类比**: 用完的东西不收拾，房间越来越乱
- **影响**: 潜在的内存泄漏
- **修复**: 彻底清理 - 断开信号、移除控件、设置父为空

**修改文件**:
- `src/gui/widgets/variable_input.py` - 完善 `clear_inputs()` 方法

##### 3. 异常处理过于宽泛 ✅
**问题**: 多处使用 `except Exception` 捕获所有异常
- **类比**: 不管什么病都开同样的药
- **影响**: 调试困难，无法区分具体错误类型
- **修复**: 区分 `FileNotFoundError`、`PermissionError`、`JSONDecodeError` 等

**修改文件**:
- `src/core/template_engine.py` - 细化异常处理
- `src/config/config_manager.py` - 细化异常处理

#### 低优先级修复（优化建议）

##### 1. 变量列表刷新优化 ✅
**状态**: 已有实现
- 代码已使用 `setVisible()` 进行过滤，无需删除重建控件

##### 2. OCR 并行处理 ✅
**状态**: 已有基础
- 已使用 `QThread` 实现异步处理

##### 3. 配置文件权限设置 ✅
**问题**: 配置文件没有设置权限，可能被其他用户读取
- **修复**: 创建配置文件时设置 `chmod(0o600)`，仅所有者可读写

**修改文件**:
- `src/config/config_manager.py` - 添加文件权限设置

#### 代码审查统计

| 类别 | 数量 | 状态 |
|------|------|------|
| 高优先级问题 | 3 | 全部修复 |
| 中优先级问题 | 3 | 全部修复 |
| 低优先级问题 | 3 | 全部完成/已有基础 |

#### 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `src/config/path_manager.py` | 添加线程锁和双重检查锁定 |
| `src/utils/logger.py` | 添加线程锁和双重检查锁定 |
| `src/core/batch_processor.py` | 使用 `threading.Event` 替代布尔标志 |
| `src/config/config_manager.py` | 添加 `safe_write_json()` 原子写入和文件权限设置 |
| `src/core/template_engine.py` | 添加模板字节缓存机制 |
| `src/gui/widgets/variable_input.py` | 完善资源清理（断开信号、移除控件） |

---

## [1.2.2] - 2026-03-12

### 默认模板扩展与功能优化

**模板大扩展**：从3个默认模板扩展到8个，覆盖更多业务场景。

#### 新增模板
1. **民事案件模板(被告)** (`civil_002`)
   - 针对被告方优化的文件夹结构
   - 包含管辖权异议、反诉状、执行异议等材料
   - 新增"原告姓名"变量

2. **劳动仲裁模板(申请人)** (`labor_001`)
   - 适用于劳动者申请仲裁
   - 包含劳动关系证明、工资社保记录等证据材料
   - 支持执行申请材料

3. **劳动仲裁模板(被申请人)** (`labor_002`)
   - 适用于用人单位应诉
   - 包含规章制度、考勤记录等
   - 支持反申请

4. **商事仲裁模板(申请人)** (`commercial_001`)
   - 支持买卖合同、建设工程、股权投资等争议
   - 包含仲裁协议、合同文本、往来函件等
   - 支持财产保全申请

5. **商事仲裁模板(被申请人)** (`commercial_002`)
   - 针对被申请人优化的答辩材料
   - 支持管辖权异议、反请求等
   - 支持执行异议

#### 模板更名
- **民事案件模板** → **民事案件模板(原告)**

#### 新增默认变量
所有8个模板新增两个非必填变量：
- `case_stage` - "办理阶段"（下拉选择，各模板选项不同）
- `contact_info` - "联系方式"（文本输入）

#### 文件变更
- `src/config/default_templates.py` - 重命名 CIVIL_TEMPLATE，新增5个模板配置
- `templates/civil2/` - 新建文件夹，存放被告方模板文件
- `templates/labor_arbitration/` - 新建文件夹，存放劳动仲裁模板
- `templates/commercial_arbitration/` - 新建文件夹，存放商事仲裁模板

---

## [1.2.1] - 2026-03-11

### 1. OCR 字段全面应用优化

**问题**: 点击"应用到案卷变量"后，只有"姓名"字段被填充，其他识别信息未被应用。

**解决方案**:
- `src/core/ocr/field_matcher.py` - 新增 `match_all()` 方法，返回所有识别字段
- `src/gui/main_window.py` - 动态创建新变量并添加到模板配置
- `src/gui/widgets/variable_input.py` - 支持动态添加变量控件

**效果**: 所有识别字段（姓名、性别、出生日期、住址、身份证号）都会自动应用到案卷表单。

### 2. 模板管理功能修复

**问题 1: 新建模板无法保存**
- 修复 `_on_save()` 方法，新建模板调用 `add_template` 而非 `update_template`

**问题 2: 删除模板无效**
- 修复 `_on_delete_template()` 方法，从配置文件中彻底删除

**优化: 重置功能**
- 点击"重置默认"恢复3个默认模板，删除所有自定义模板

---

## [1.2.0] - 2026-03-10

### 重磅更新：OCR 信息识别功能

本次更新引入了强大的 OCR 信息识别功能，支持从身份证、户口簿、护照等证件图片中自动提取信息并填充到案卷模板中。

#### 技术架构变更
- **OCR 引擎**: 从 PaddleOCR 迁移至 RapidOCR
  - PaddleOCR 体积过大（200MB+），依赖复杂，版本兼容性差
  - RapidOCR 轻量（40MB），基于 ONNX Runtime，启动快且稳定
  - 删除了所有 Paddle 相关依赖和模型缓存

#### 新增功能 (Features)

##### 1. 信息识别对话框 (`src/gui/info_extraction_dialog.py`)
- 左侧文件列表 + 右侧识别结果展示的双栏布局
- 支持批量添加图片/PDF 文件
- 进度条显示识别进度
- 识别完成后自动填充到案卷变量

##### 2. 图片预览功能 (`src/gui/widgets/image_list_widget.py`)
- 单张图片时自动在顶部显示预览
- 选中不同文件时预览自动切换
- PDF 文件自动转换为图片预览
- 支持拖拽添加文件

##### 3. OCR 识别结果展示 (`src/gui/widgets/ocr_result_widget.py`)
- 字段编辑控件（可手动修正识别结果）
- 置信度指示器（高/中/低置信度颜色标识）
- 低置信度字段红色警告提示
- 支持导出为 JSON/Excel/Word

##### 4. 文档解析器系统 (`src/core/ocr/parsers/`)
- 身份证正面解析器（姓名、性别、民族、出生日期、住址、身份证号）
- 身份证反面解析器（签发机关、有效期限）
- 户口簿解析器（框架）
- 护照解析器（框架）
- 驾驶证解析器（框架）
- 营业执照解析器（框架）
- 判决书/裁定书解析器（框架）

##### 5. 字段匹配系统 (`src/core/ocr/field_matcher.py`)
- 自动将识别字段映射到模板变量
- 支持自定义字段映射规则
- 智能匹配建议

##### 6. 数据存储管理 (`src/core/data/info_storage.py`)
- JSON 格式存储识别记录
- 按日期分目录存储
- 支持历史记录查询和清理

#### 界面集成
- 主界面底部新增"信息识别"按钮（橙色，位于"清空"和"预览"之间）
- 点击打开信息识别对话框
- 识别结果可一键应用到当前案卷表单

#### 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `VERSION` | 修改 | 版本号更新至 1.2.0 |
| `requirements.txt` | 修改 | 移除 paddlepaddle/paddleocr，添加 rapidocr-onnxruntime |
| `src/core/ocr/paddle_engine.py` | 重写 | 改用 RapidOCR |
| `src/core/ocr/document_parser.py` | 新建 | 文档解析器基类 |
| `src/core/ocr/field_matcher.py` | 新建 | 字段匹配系统 |
| `src/core/ocr/parsers/id_card_parser.py` | 新建 | 身份证解析器 |
| `src/core/ocr/parsers/household_parser.py` | 新建 | 户口簿解析器（框架） |
| `src/core/ocr/parsers/passport_parser.py` | 新建 | 护照解析器（框架） |
| `src/core/ocr/parsers/license_parser.py` | 新建 | 驾驶证解析器（框架） |
| `src/core/ocr/parsers/business_license_parser.py` | 新建 | 营业执照解析器（框架） |
| `src/core/ocr/parsers/judgment_parser.py` | 新建 | 判决书解析器（框架） |
| `src/core/ocr/parsers/ruling_parser.py` | 新建 | 裁定书解析器（框架） |
| `src/core/data/info_storage.py` | 新建 | 识别数据存储管理 |
| `src/gui/info_extraction_dialog.py` | 新建 | 信息识别主对话框 |
| `src/gui/widgets/image_list_widget.py` | 重写 | 添加图片预览功能 |
| `src/gui/widgets/ocr_result_widget.py` | 新建 | OCR 结果展示控件 |
| `src/gui/main_window.py` | 修改 | 添加"信息识别"按钮 |
| `src/utils/pdf_utils.py` | 新建 | PDF 处理工具 |

#### 今日迭代优化 (2026-03-10 晚)

在白天完成 OCR 基础功能后，晚上继续进行了以下优化：

**1. 界面布局优化**
- 左侧预览区域和文件列表使用 `QSplitter` 分割，支持手动调节大小
- 预览区域默认占更大空间（350px vs 150px），方便查看证件细节

**2. 重新识别功能修复**
- 修复"重新识别"按钮点击无效果的问题
- 将按钮从右侧结果区移动到左下角，与"开始识别"按钮对齐
- 添加信号机制，实现当前选中文件的重新识别

**3. 身份证住址识别修复**
- 修复多行地址识别不完整的问题（漏掉第一行省市区信息）
- 优化 `_extract_address()` 方法，同时检查"住址"标签同行内容和后续行
- 示例：`住址安徽省池州市贵池区` + `街道办事处新龙村` + `3号` → 完整地址

**4. 图片预览缩放功能**
- 添加放大/缩小控制工具栏（[−] [+] [重置] [适应]）
- 支持 Ctrl + 鼠标滚轮缩放
- 缩放范围：10% ~ 500%
- 使用 `QScrollArea` 支持大图滚动查看

---

## [1.2.1] - 2026-03-11

### 1. 默认模板扩展与优化

**模板分类细化**：
1. **民事案件模板(原告)** - 原"民事案件模板"更名
2. **民事案件模板(被告)** - 新增，针对被告方优化
3. **刑事案件模板** - 现有模板保留
4. **非诉案件模板** - 现有模板保留
5. **劳动仲裁模板(申请人)** - 新增
6. **劳动仲裁模板(被申请人)** - 新增
7. **商事仲裁模板(申请人)** - 新增
8. **商事仲裁模板(被申请人)** - 新增

**新增默认变量**：
所有模板新增两个非必填变量：
- `case_stage` - "办理阶段"（下拉选择）
- `contact_info` - "联系方式"（文本输入）

**文件变更**：
- `src/config/default_templates.py` - 重命名 CIVIL_TEMPLATE 为 CIVIL_PLAINTIFF_TEMPLATE，新增 5 个模板配置
- `templates/civil2/` - 新建文件夹，存放被告方模板文件
- `templates/labor_arbitration/` - 新建文件夹，存放劳动仲裁模板
- `templates/commercial_arbitration/` - 新建文件夹，存放商事仲裁模板

### 2. OCR 字段全面应用优化

**问题**: 点击"应用到案卷变量"后，只有"姓名"字段被填充到主界面，其他识别信息（性别、出生日期、住址、身份证号）未被应用。

**解决方案**:
1. **字段全面匹配** (`src/core/ocr/field_matcher.py`)
   - 新增 `match_all()` 方法：返回所有识别字段的匹配结果
   - 对于未匹配到现有变量的字段，自动创建新变量名
   - 新增 `_field_name_to_var_key()` 方法，将字段名转换为有效的变量名格式

2. **动态变量创建** (`src/gui/main_window.py`)
   - 识别数据应用到案卷时，自动区分已有变量和新变量
   - 新变量动态添加到表单和模板配置
   - 自动为新变量生成友好的中文标签

3. **表单动态更新** (`src/gui/widgets/variable_input.py`)
   - 新增 `add_variable()` 方法支持动态添加变量输入控件
   - 新增 `has_variable()` 方法检查变量是否已存在

4. **提示信息优化** (`src/gui/info_extraction_dialog.py`)
   - 弹窗显示详细的匹配信息：匹配现有变量数 + 创建新变量数
   - 状态栏提示包含新创建变量数量

**使用示例**:
识别身份证后，所有字段都会自动应用：
- 姓名 → 填充/创建"姓名"变量
- 性别 → 填充/创建"性别"变量  
- 出生日期 → 填充/创建"出生日期"变量
- 住址 → 填充/创建"住址"变量
- 身份证号 → 填充/创建"身份证号"变量

**文件变更清单**:
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `src/core/ocr/field_matcher.py` | 修改 | 新增 `match_all()` 和 `_field_name_to_var_key()` 方法 |
| `src/gui/info_extraction_dialog.py` | 修改 | 使用 `match_all()`，优化提示信息 |
| `src/gui/main_window.py` | 修改 | 支持动态创建新变量并添加到模板 |
| `src/gui/widgets/variable_input.py` | 修改 | 支持动态添加变量控件 |

### 2. 模板管理功能修复

**问题 1: 新建模板无法保存**
- 现象: 点击"新建"创建模板并保存后，重启软件模板消失
- 原因: `_on_save()` 方法对所有模板都调用 `update_template`，但新建模板不存在于配置中
- 修复: 检查模板是否已存在，不存在则调用 `add_template` 添加

**问题 2: 删除模板无效**
- 现象: 删除模板后重启软件，模板仍然存在
- 原因: 只从内存列表删除，未从配置文件删除
- 修复: 先调用 `config_manager.delete_template()` 从配置删除

**优化: 重置功能**
- 点击"重置默认"现在会：
  - 删除所有自定义添加的模板
  - 恢复民事、刑事、非诉3个默认模板
  - 重置对默认模板的所有修改
- 添加详细确认提示和成功提示

**文件变更**:
- `src/gui/template_manager.py` - 修复 `_on_save()`、`_on_delete_template()`、`_on_reset_templates()`

---

#### 待完成工作
- [ ] 户口簿解析器完整实现
- [ ] 护照解析器完整实现
- [ ] 驾驶证解析器完整实现
- [ ] 营业执照解析器完整实现
- [ ] 判决书/裁定书解析器完整实现
- [ ] 历史记录对话框
- [ ] Excel/Word 导出功能完善

---

## [1.1.4] - 2026-03-05

### 代码质量全面审查与优化

本次更新是一次全面的代码审查和优化，修复了多个严重问题、性能问题和安全隐患。

### 修复内容 (Fixes)

#### 1. 重复方法定义 ✅
**问题**: `template_manager.py` 中 `_on_browse_template` 方法被定义了两次
- 修复: 删除重复的方法定义

#### 2. 版本号不同步 ✅
**问题**: `app.py` 和 `main_window.py` 中的版本号是 1.0.0，与实际版本 1.1.3 不符
- 修复: 统一版本号为 1.1.3

#### 3. 默认模板文件名包含非法字符 ✅
**问题**: `default_templates.py` 中多处文件名包含中文引号 `""`
- 修复: 将中文引号替换为下划线，如 `0_{{client_name}}_委托合同.docx`

#### 4. 单例模式无线程安全保护 ✅
**问题**: `ConfigManager`、`Application`、`TemplatePathManager` 的单例实现没有线程锁
- 修复: 添加双重检查锁定模式（Double-Checked Locking）

### 性能优化 (Performance)

#### 1. 模板扫描缓存机制 ✅
**问题**: `get_available_templates()` 每次调用都扫描文件系统
- 修复: 添加缓存机制，TTL 30秒，新增 `clear_cache()` 方法

#### 2. 变量列表刷新优化 ✅
**问题**: `_refresh_variable_list()` 每次搜索都删除并重建所有控件
- 修复: 使用 `setVisible()` 过滤而非重建，新增 `force_rebuild` 参数

#### 3. 配置批量更新模式 ✅
**问题**: `ConfigManager.set()` 默认每次都写入磁盘
- 修复: 添加 `batch_update()` 上下文管理器支持批量更新

### 代码改进 (Improvements)

#### 1. 异常处理细化 ✅
**问题**: 多处使用 `except Exception as e` 捕获所有异常
- 修复: 区分 `FileNotFoundError`、`PermissionError`、`KeyError` 等具体异常类型

#### 2. 类型注解补充 ✅
**问题**: `word_editor.py` 中部分方法缺少类型注解
- 修复: 补充 `DocxDocument`、`Paragraph` 等类型提示

#### 3. 日志级别优化 ✅
**问题**: `template_path_manager.py` 中有过多 DEBUG 日志
- 修复: 将部分 DEBUG 日志改为 INFO 级别

### 安全加固 (Security)

#### 1. 路径遍历攻击防护 ✅
**问题**: `resolve_template_path()` 没有防止路径遍历攻击
- 修复: 添加路径安全检查，防止 `..` 和非法绝对路径

#### 2. 配置文件验证 ✅
**问题**: JSON 配置文件加载时没有 schema 验证
- 修复: 添加 `_validate_config()` 和 `_validate_templates()` 验证方法

### 文件变更清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `src/gui/template_manager.py` | 删除 | 移除重复方法定义 |
| `src/app.py` | 修改 | 版本号同步、线程安全 |
| `src/gui/main_window.py` | 修改 | 版本号同步 |
| `src/config/default_templates.py` | 修改 | 清理文件名非法字符 |
| `src/config/config_manager.py` | 新增 | 线程安全、批量更新、配置验证 |
| `src/utils/template_path_manager.py` | 新增 | 缓存机制、路径安全 |
| `src/gui/template_maker.py` | 修改 | 变量列表刷新优化 |
| `src/core/template_engine.py` | 修改 | 异常处理细化 |
| `src/core/word_editor.py` | 修改 | 类型注解补充 |

---

## [1.1.3] - 2026-03-02

### 新增功能 (Features)

#### Word 模板制作器右键撤销变量功能 ✅
**功能**: 右键点击已替换的变量，可直接撤销替换
- 检测变量：精确检测鼠标位置是否在 `{{变量名}}` 范围内
- 单个撤销：只撤销当前点击的这一处变量
- 整体撤销：撤销文档中所有同名的 `{{变量名}}`
- 修复文件:
  - `src/core/word_editor.py`: 新增 `undo_variable()` 和 `get_variable_original_text()` 方法
  - `src/gui/widgets/word_preview.py`: 新增变量检测和右键菜单
  - `src/gui/template_maker.py`: 连接撤销信号和处理方法

### 修复内容 (Fixes)

#### 变量检测精度问题 ✅
**问题**: 点击变量附近的普通文字也会误判为在变量上
- 原因: 原逻辑从当前位置向前后搜索100字符内的 `{{` 和 `}}`，导致误判
- 修复: 改用正则 `finditer` 精确匹配，只有光标位置在变量的 `start` 和 `end` 范围内才判定为变量
- 修复文件: `src/gui/widgets/word_preview.py`

---

## [1.1.2] - 2026-03-02

### 新增功能 (Features)

#### Word 模板制作器预览区域右键菜单 ✅
**功能**: 在预览区域选中文本后右键，可直接进入替换功能
- 去掉了默认的 "Copy"、"Select All" 菜单
- 选中文本时：显示"替换选中..."菜单项
- 无选中文本时：显示"请先选择文字"（灰色禁用）
- 修改文件: `src/gui/widgets/word_preview.py`, `src/gui/template_maker.py`

---

## [1.1.1] - 2026-03-01

### 修复内容 (Fixes)

#### 1. 模板管理器文件名包含 "✓" 符号问题 ✅
**问题**: 导出的 Word 文档文件名后带有 "✓" 符号，如 `委托代理合同.docx✓`
- 现象: 模板关联成功后显示的 "✓" 标记被错误地保存到文件名中
- 根本原因:
  - `_on_item_changed` 方法将显示文本（含 "✓"）直接保存到 `name` 字段
  - `_get_folder_structure` 方法未清理显示标记
- 修复文件:
  - `src/gui/template_manager.py`: 在保存 name 时清理 "✓" 和 "📎" 标记
  - `src/utils/validators.py`: 在 `sanitize_filename()` 中添加标记清理作为最后防线

#### 2. Word 模板制作器文本选择只获取首字问题 ✅
**问题**: 在预览区域选择多个文字时，替换框只显示首字
- 现象: 选择"委托人姓名"多个字，替换框只显示"委"
- 根本原因: 使用 `copyAvailable` 信号，该信号只在选择状态改变时触发一次
- 修复方案:
  - 改用 `selectionChanged` 信号，每次选区改变时都会触发
  - 在打开替换对话框时直接从预览控件获取当前选中文本
  - 处理 Unicode 段落分隔符 (U+2029)
- 修复文件: `src/gui/widgets/word_preview.py`, `src/gui/template_maker.py`

#### 3. 变量同步问题 ✅
**问题**: 模板管理器和 Word 模板制作器的变量列表不同步
- 现象: 在模板管理器中添加的变量不会出现在 Word 模板制作器中
- 根本原因: Word 模板制作器只从硬编码的 `DEFAULT_TEMPLATES` 加载变量
- 修复方案:
  - 修改 `_load_default_variables()` 优先从配置管理器读取用户自定义变量
  - 添加 `_reload_variables_from_config()` 方法在刷新变量列表时重新加载
- 修复文件: `src/gui/template_maker.py`

#### 4. Word 预览高亮格式问题 ✅
**问题**: 变量后面的普通文字也被高亮显示
- 现象: `{{matter_type}}，保证诉讼程序进行` 中逗号后面的文字也被高亮
- 根本原因: `QTextCursor` 在插入文本时继承了之前的高亮格式
- 修复方案: 在插入普通文本时显式设置默认格式，重置高亮效果
- 修复文件: `src/gui/widgets/word_preview.py`

#### 5. 撤销功能崩溃问题 ✅
**问题**: 点击撤销按钮后程序崩溃
- 现象: `IndexError: pop from empty list`
- 根本原因: `load_document()` 清空历史记录后又尝试 `pop()`
- 修复方案:
  - 移除 `load_document()` 之后的 `pop()` 调用
  - 添加撤销后刷新预览的逻辑
- 修复文件: `src/core/word_editor.py`, `src/gui/template_maker.py`

### 技术改进

| 文件 | 修改内容 |
|------|----------|
| `src/gui/template_manager.py` | 清理保存时的显示标记，修复方法定义丢失问题 |
| `src/gui/template_maker.py` | 变量同步、撤销刷新、选中文字获取 |
| `src/gui/widgets/word_preview.py` | 信号类型、高亮格式重置 |
| `src/core/word_editor.py` | 撤销逻辑修复 |
| `src/utils/validators.py` | 文件名清理增强 |

---

## [1.1.0] - 2026-02-28

### 待修复问题 (Known Issues)

#### 文本选择只获取首字 (v1.1.0-bug1)
**问题**: 在预览区域选择多个文字时，替换框只显示首字
- 现象: 选择"委托人姓名"多个字，替换框只显示"委"
- 影响功能: "替换选中"功能
- 可能原因:
  1. `QTextEdit.textCursor().selectedText()` 返回值处理问题
  2. 信号传递过程中被截断
- 定位文件: `src/gui/widgets/word_preview.py` 的 `_on_selection_changed` 方法
- 下次修复: 检查 selectedText() 的返回值，可能需要处理 Unicode 分隔符

### 修复内容 (Fixes)

#### Word 预览控件 API 兼容性修复 (v1.1.0-hotfix1)
**问题**: 使用 `asObject()` 方法导致 Word COM 预览失败
- 现象: `'PySide6.QtAxContainer.QAxWidget' object has no attribute 'asObject'`
- 根本原因: `asObject()` 是 PyQt5 的 API，PySide6 不支持
- 修复方案:
  - 改用 python-docx 进行文本预览（稳定可靠）
  - 支持变量高亮显示
  - 支持文本选择和复制
  - 移除对 Word COM 的依赖

#### 替换功能不生效问题 (v1.1.0-hotfix2)
**问题**: 点击"替换选中"或"全部替换"后，预览区域没有变化
- 现象: 替换对话框点击 OK 后，预览无变化
- 根本原因:
  1. 预览刷新时从原文件重新加载，而不是从已修改的内存文档更新
  2. 用户未在预览区域选择文字时，`_selected_text` 为空
- 修复方案:
  1. 添加 `set_preview_text()` 方法，直接从编辑器更新预览内容
  2. 添加 `_refresh_preview_from_editor()` 方法，替换后从内存更新预览
  3. 当没有选中文字时，提示用户先选择或使用"全部替换"
  4. 添加详细的调试日志

#### 字符串引号语法错误 (v1.1.0-hotfix3)
**问题**: 代码中中文引号与 Python 字符串引号冲突
- 现象: `SyntaxError: invalid syntax`
- 修复: 将外层双引号改为单引号

### 新增功能 (Features)

#### Word 模板制作器
**核心功能：让用户自行制作 Word 模板，上传到分类文件夹并进行变量替换**

1. **主窗口框架** (`src/gui/template_maker.py`)
   - 三栏布局：左侧模板库、中间 Word 预览区、右侧变量面板
   - 工具栏：打开、替换选中、全部替换、撤销、保存、另存为
   - 状态栏：显示操作状态

2. **模板库面板**
   - 树形展示三个分类文件夹（民事/刑事/非诉）
   - 显示各分类下的 Word 模板文件
   - 支持上传新模板到指定分类
   - 点击模板文件触发预览

3. **Word 预览控件** (`src/gui/widgets/word_preview.py`)
   - 使用 QAxWidget 调用 Word COM 组件
   - 支持文本选中信号
   - 支持缩放和翻页功能
   - 回退方案：python-docx 纯文本预览

4. **Word 编辑器核心** (`src/core/word_editor.py`)
   - 格式保持的文本替换（在 Run 级别操作）
   - 变量提取功能
   - 文档加载和保存
   - 操作历史（撤销支持）

5. **变量面板**
   - 显示所有可用变量（从默认模板同步）
   - 变量搜索功能
   - 智能推荐（根据选中文字推荐变量）
   - 支持添加自定义变量
   - 双击变量快速插入

6. **替换对话框**
   - 选中文字替换模式
   - 手动输入替换模式
   - 全部替换选项
   - 替换预览
   - 格式保持提示

#### 主窗口入口
- **菜单栏**：模板(T) → 制作 Word 模板（快捷键 Ctrl+M）
- **工具栏**：新增"制作模板"按钮

### 技术实现

| 文件 | 说明 |
|------|------|
| `src/gui/template_maker.py` | 模板制作器主窗口 |
| `src/gui/widgets/word_preview.py` | Word 预览控件 |
| `src/core/word_editor.py` | Word 编辑器核心逻辑 |
| `src/gui/main_window.py` | 主窗口（新增入口） |

### 设计文档

- `docs/WORD_TEMPLATE_MAKER_DESIGN.md` - 详细设计文档
- `prototypes/template_maker_design.html` - UI 设计稿

---

## [1.0.2] - 2026-02-25

### 修复内容 (Fixes)

#### Word 模板系统修复
**问题 1: 系统模板库无法获取模板**
- 现象: "从系统模板库选择"模块无法显示 `templates/civil/` 文件夹下的 Word 模板
- 根本原因: `get_available_templates()` 在不传类别参数时只扫描根目录，未扫描子目录
- 修复方案:
  - 修改 `TemplatePathManager.get_available_templates()` 扫描所有子目录 (civil, criminal, non_litigation)
  - 测试结果: 从 0 个模板增加到 34 个模板

**问题 2: 模板变量被删除而不是替换**
- 现象: 案卷生成后，Word 文档中的变量被直接删除，而不是替换为用户填写的内容
- 根本原因: `_prepare_context()` 将 None 值转换为空字符串 `""`，导致 docxtpl 删除变量
- 修复方案:
  - 修改 `TemplateEngine._prepare_context()` 跳过 None 和空字符串值
  - 结果: 未填写的变量保留为 `{{变量名}}` 占位符

**问题 3: 模板管理器文件夹结构不同步**
- 现象: 在模板管理中添加/重命名文件夹文件后，主界面预览显示不匹配，终端显示 `WARNING: 文件夹项缺少 'name' 字段`
- 根本原因:
  - 新建项目时未设置 "name" 字段到用户数据
  - 重命名时未同步到用户数据
  - 导出时未确保 "name" 字段存在
- 修复方案:
  - 添加 `itemChanged` 信号处理器同步名称到用户数据
  - 修复 `_on_add_folder` / `_on_add_subfolder` / `_on_add_file` 设置完整用户数据
  - 修复 `_load_folder_structure` 确保所有项有 "name" 字段
  - 修复 `_get_folder_structure` 同步名称并移除无效字段
  - 修复 `_update_item_display` 双向同步名称

#### 启动崩溃修复
**问题: KeyError: 'name' 导致应用无法启动**
- 现象: 应用启动时在预览文件夹结构时崩溃
- 根本原因: 用户 templates.json 中存在格式错误的条目（缺少 name 字段）
- 修复方案: 在 `FolderGenerator._preview_folder` / `_create_subfolder` / `_create_file` 中添加防御性检查

### 新增功能 (Features)

#### 测试 Word 模板生成脚本
- 创建 `scripts/create_test_templates.py` 自动生成包含变量的测试模板
- 支持生成委托合同、授权委托书、出庭通知书三种模板
- 每个模板包含 22+ 个中文变量

#### 完整的测试验证脚本
- `test_fixes_part2.py` - 验证模板系统和变量替换修复
- `test_template_fixes.py` - 原有测试脚本

### 文档更新

- `FIX_SUMMARY_PART2.md` - Word 模板系统修复总结
- `FIX_SUMMARY_TEMPLATE_MANAGER.md` - 模板管理器修复总结
- `FIX_SUMMARY_WORD_TEMPLATE.md` - Word 模板关联修复总结
- `WORD_TEMPLATE_IMPLEMENTATION.md` - Word 模板实现文档

### 技术改进

- 增强模板路径解析逻辑
- 改进变量提取功能（支持中文变量名）
- 优化模板扫描算法
- 添加更详细的调试日志

### 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `VERSION` | 修改 | 版本号更新至 1.0.2 |
| `src/utils/template_path_manager.py` | 修改 | 扫描所有子目录，支持 .doc 和 .docx |
| `src/core/template_engine.py` | 修改 | 跳过 None/空值，保留变量占位符 |
| `src/core/folder_generator.py` | 修改 | 添加防御性检查，处理缺失 name 字段 |
| `src/gui/template_manager.py` | 修改 | 同步名称到用户数据，修复新建/重命名逻辑 |
| `src/gui/template_file_dialog.py` | 修改 | 添加使用说明区域，显示真实变量 |
| `scripts/create_test_templates.py` | 新建 | 测试模板生成脚本 |
| `test_fixes_part2.py` | 新建 | 综合测试脚本 |

### 向后兼容性

所有修复保持向后兼容:
- 现有模板配置继续正常工作
- 无破坏性 API 变更
- 旧格式的子文件夹（字符串格式）仍然支持

### 测试结果

```
Template Scanning (No Category)   [PASS] - 34 templates found
Template Scanning (With Category)  [PASS] - 16 templates in civil
Variable Replacement (None Values) [PASS] - None values preserved
Variable Replacement (All Values)  [PASS] - All values processed
```

---

## [1.0.1] - 2026-02-25

### 修复内容

**[关键修复] 文件名非法字符错误**
- 问题: 生成案卷时出现 `[Errno 22] Invalid argument` 错误
- 根本原因: 默认模板文件名包含引号（如 `0"{{client_name}}"委托合同.docx`）
- 解决方案:
  1. 增强 `sanitize_filename()` 函数包含中文引号
  2. 修改 `replace_variables()` 清理整个替换后的字符串
- 测试结果: 文件名从 `0"共和国和"委托合同.docx` 转换为 `0_共和国和_委托合同.docx`

**Bug 修复**
- 修复 `TemplateCard` QFont 初始化错误

---

## [1.0.0] - 2026-02-25

### 初始版本

#### 核心功能
- 变量解析系统 (`{{variable}}` 格式)
- 文件夹结构生成
- Word 模板处理
- 批量生成支持

#### GUI 功能
- 主窗口界面
- 模板选择卡片
- 动态变量输入
- 文件夹预览
- 生成进度显示
- 模板管理器
- 设置对话框

#### 系统集成
- Windows 右键菜单
- 注册表管理

---

## 版本规划

### [1.2.0] - 计划中

#### 待优化功能
- [ ] Word COM 预览稳定性优化
- [ ] 模板导入/导出功能
- [ ] 更多内置模板
- [ ] 案卷搜索功能
- [ ] 操作历史记录
- [ ] 数据库支持
- [ ] 多语言支持
- [ ] 主题定制

---

## 版本历史

### [1.1.0] - 2026-02-27 (当前版本)

#### 新增功能：Word 模板制作器
- ✅ 模板制作器主窗口 (`src/gui/template_maker.py`)
- ✅ Word 预览控件 (`src/gui/widgets/word_preview.py`)
- ✅ Word 编辑器核心 (`src/core/word_editor.py`)
- ✅ 上传 Word 文档到分类文件夹
- ✅ Word 文档预览（QAxWidget + Word COM）
- ✅ 选中文字替换为变量
- ✅ 手动输入文字批量替换
- ✅ 格式保持的文本替换
- ✅ 智能变量推荐
- ✅ 主窗口菜单栏/工具栏入口

---

## 贡献指南

### 开发环境设置

```bash
# 克隆仓库
git clone <repository-url>
cd LawyerCaseTool

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行应用
python src/main.py
```

### 代码风格

- 遵循 PEP 8 规范
- 使用 UTF-8 编码
- 文件头部添加编码声明
- 类和函数添加文档字符串

### 提交规范

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关

---

*本文档由 Claude Code 自动生成并维护*
