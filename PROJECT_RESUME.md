# 案件文件夹管理系统 - 项目快速恢复指南

## 🚀 快速开始

### 第一步：让 Claude Code 了解项目状态

**在开始任何对话时，首先粘贴以下内容给 Claude Code：**

```
请阅读以下项目恢复文档，然后等待我的指令。

文件位置：C:\Users\49144\Desktop\ClaudeCodeHub\filemst\LawyerCaseTool\PROJECT_RESUME.md
```

然后等待 Claude Code 读取文档，再继续你的工作。

---

## 📋 项目概览

### 项目信息
- **项目名称**: 案件文件夹管理系统（兼容标识：LawyerCaseTool）
- **当前版本**: v2.0.0 (2026-04-21)
- **开发语言**: Python 3.11+
- **GUI 框架**: PySide6
- **项目路径**: `C:\Users\49144\Desktop\ClaudeCodeHub\filemst\LawyerCaseTool`

### 项目描述
基于 Python + PySide6 的本地案件管理桌面应用，以案件文件夹为核心载体，支持案件台账、模板生成、OCR 智能识别、变量替换、电子归档和工具中心等功能。

### 当前设计基线
- **工作台重构方案**: [docs/WORKBENCH_REDESIGN_PLAN.md](/Users/a49144/Desktop/codexhub/LawyerCaseTool-开发包/docs/WORKBENCH_REDESIGN_PLAN.md)
- **高保真 HTML 原型**: `prototypes/local_case_management_workbench/`
- 说明：后续主界面一体化、工作台、标签页和模块整合，统一以该方案和该原型为准。

---

## 📁 项目结构

```
LawyerCaseTool/
├── src/
│   ├── core/              # 核心业务逻辑
│   │   ├── ocr/           # OCR 信息识别 ⭐ 新增 (v1.2.0)
│   │   │   ├── paddle_engine.py      # RapidOCR 引擎
│   │   │   ├── document_parser.py    # 文档解析器基类
│   │   │   ├── field_matcher.py      # 字段匹配系统
│   │   │   └── parsers/              # 各类证件解析器
│   │   │       ├── id_card_parser.py      # 身份证 ⭐ 已实现
│   │   │       ├── household_parser.py    # 户口簿
│   │   │       ├── passport_parser.py     # 护照
│   │   │       └── ...
│   │   ├── batch_processor.py      # 批量处理器
│   │   ├── folder_generator.py     # 文件夹生成器 ⭐ 关键
│   │   ├── template_engine.py      # Word 模板引擎 ⭐ 关键
│   │   ├── variable_parser.py      # 变量解析器
│   │   └── word_editor.py          # Word 编辑器 ⭐ 新增 (v1.1.0)
│   ├── gui/               # 用户界面
│   │   ├── main_window.py          # 主窗口
│   │   ├── info_extraction_dialog.py # 信息识别对话框 ⭐ 新增 (v1.2.0)
│   │   ├── generation_dialog.py    # 生成对话框
│   │   ├── template_manager.py     # 模板管理器 ⭐ 关键
│   │   ├── template_file_dialog.py # 模板关联对话框 ⭐ 关键
│   │   ├── template_maker.py       # 模板制作器 ⭐ 新增 (v1.1.0)
│   │   ├── settings_dialog.py      # 设置对话框
│   │   └── widgets/                # 自定义控件
│   │       ├── template_card.py    # 模板卡片
│   │       ├── image_list_widget.py # 图片列表+预览 ⭐ 新增 (v1.2.0)
│   │       ├── ocr_result_widget.py # OCR 结果展示 ⭐ 新增 (v1.2.0)
│   │       ├── folder_tree.py      # 文件夹树
│   │       ├── variable_input.py   # 变量输入
│   │       └── word_preview.py     # Word 预览 ⭐ 新增 (v1.1.0)
│   ├── config/            # 配置管理
│   │   ├── config_manager.py       # 配置管理器
│   │   ├── path_manager.py         # 路径管理器
│   │   └── default_templates.py    # 默认模板定义
│   ├── utils/            # 工具模块
│   │   ├── template_path_manager.py # 模板路径管理器 ⭐ 关键
│   │   ├── logger.py               # 日志管理
│   │   ├── exceptions.py           # 自定义异常
│   │   └── validators.py           # 数据验证
│   └── integration/       # 系统集成
│       ├── context_menu.py         # 右键菜单
│       └── registry_manager.py     # 注册表管理
├── templates/           # Word 模板文件
│   ├── civil/          # 民事案件模板
│   ├── criminal/       # 刑事案件模板
│   └── non_litigation/ # 非诉讼案件模板
├── scripts/            # 实用脚本
│   └── create_test_templates.py  # 测试模板生成
├── tests/              # 测试文件
├── docs/               # 文档
│   └── WORD_TEMPLATE_MAKER_DESIGN.md  # 模板制作器设计文档
├── prototypes/         # HTML 原型
│   └── template_maker_design.html    # 模板制作器 UI 设计稿
├── CHANGELOG.md        # 更新日志 ⭐ 已更新 (v1.2.3)
├── VERSION             # 版本号
├── CLAUDE.md           # Claude Code 开发指南 ⭐ 已更新 (v1.2.3)
├── AGENTS.md           # AI 助手开发指南 ⭐ 已更新 (v1.2.3)
├── PROJECT_RESUME.md   # 项目恢复指南
└── docs/PROJECT_STATUS.md  # 项目状态报告 ⭐ 新增
```

---

## 🔧 最近修复的关键问题

### v1.4.0 全面代码审查与功能优化 (2026-03-31)
- **图片预览缩放**: 电子化归档图片预览新增缩放控件（+/-/适应宽度/窗口/原始大小），自动隐藏翻页
- **对方当事人智能映射**: 4个被告/被申请人模板中对方姓名直接填入原告/申请人变量
- **默认配置同步**: 运行时模板配置（含Word模板路径、用户变量）同步为代码默认值
- **代码质量**: 6处bug修复、变量正则统一、死代码清理、统一配色方案styles.py
- **配置管理**: _get_default_config() 消除重复定义，统一引用DEFAULT_*_CONFIG常量
- **测试**: 18/18 全部通过

### v1.2.21 模板管理与制作器优化 (2026-03-15)

**模板管理界面 UI 精简**：
1. **去边框化**: 移除右侧编辑器外边框、分组区域边框、左侧列表边框
2. **紧凑化**: 减小内边距和间距，信息密度更高
3. **Modern UI v3**: 统一配色方案，背景色分层更清晰
4. **图标系统**: 文件夹结构树添加 📁📄📎 图标区分类型
5. **高度优化**: 文件夹树和变量列表增加最小高度，展示更充分

**模板制作器重构**：
1. **实时文件浏览器**: 左侧直接显示 `templates/` 文件夹实际结构
2. **展开/收缩按钮**: 📂/📁 一键控制全部文件夹展开状态
3. **单击双击分离**: 单击重命名、双击打开（定时器区分）
4. **文件操作**: 支持 Word 文档在预览区编辑，其他文件用系统默认程序打开
5. **工具栏整合**: 底部"打开文件"按钮合并到顶部工具栏

**模板置顶功能**：
1. **置顶按钮**: 左侧分类栏添加 📌 置顶按钮
2. **置顶规则**: "全部"最多3个，各分类最多1个
3. **自动排序**: 置顶模板自动排在列表前面

### v1.2.5 UI 全面现代化改造 (2026-03-15)

**界面全面升级**：
1. **UI 现代化**: 全新三栏式布局，现代化配色系统
2. **模板卡片**: 全新设计，支持搜索筛选
3. **表单优化**: 更紧凑的输入控件设计
4. **文件夹预览**: 支持拖拽排序和编辑，可保存到模板
5. **应用图标**: 设计并生成完整图标资源包

### v1.2.4 项目全面整理 (2026-03-15)

**项目大扫除**：
1. **文档清理**: 删除8个冗余的修复总结文档
2. **代码修复**: 
   - 移除 PySide6 弃用 API
   - 统一版本号管理（pyproject.toml + main_window.py）
   - 更新 OCR 文档依赖说明
3. **测试修复**: 修复2个过期测试，18/18全部通过

### v1.2.2 默认模板大扩展 (2026-03-12)

**模板分类细化**（8个默认模板）：
- 民事案件模板(原告) - 更名
- 民事案件模板(被告) - 新增
- 刑事案件模板
- 非诉案件模板
- 劳动仲裁模板(申请人) - 新增
- 劳动仲裁模板(被申请人) - 新增
- 商事仲裁模板(申请人) - 新增
- 商事仲裁模板(被申请人) - 新增

**新增变量**：所有模板增加"办理阶段"和"联系方式"

**文件变更**：
- `src/config/default_templates.py` - 重命名 CIVIL_TEMPLATE 为 CIVIL_PLAINTIFF_TEMPLATE，新增5个模板配置
- `templates/civil2/` - 新建文件夹，存放被告方模板文件
- `templates/labor_arbitration/` - 新建文件夹
- `templates/commercial_arbitration/` - 新建文件夹

### v1.2.1 功能优化与Bug修复 (2026-03-11)

#### 1. OCR 字段全面应用优化

**功能优化**：点击"应用到案卷变量"后，所有识别字段都会被应用到案卷表单。

- 已存在的变量直接填充值
- 不存在的变量自动创建并添加到模板配置
- 自动为新变量生成中文标签

#### 2. 模板管理功能修复

**修复问题**:
- 新建模板无法保存 - 修复保存逻辑，新建模板调用 `add_template`
- 删除模板无效 - 修复删除逻辑，从配置文件中彻底删除
- 重置功能优化 - 点击重置恢复到3个默认模板，删除所有自定义模板

#### 优化内容
1. **全面匹配** (`src/core/ocr/field_matcher.py`)
   - 新增 `match_all()` 方法返回所有识别字段
   - 未匹配的字段自动创建新变量

2. **动态变量创建** (`src/gui/main_window.py`)
   - 新变量自动添加到表单和模板配置
   - 自动为新变量生成中文标签

3. **表单动态更新** (`src/gui/widgets/variable_input.py`)
   - 支持运行时动态添加变量输入控件

**效果对比**:
- 优化前：只填充 1 个变量（姓名）
- 优化后：填充 5 个变量（姓名、性别、出生日期、住址、身份证号）

---

### v1.2.0 OCR 信息识别功能 (2026-03-10)

**重磅更新**：引入 OCR 智能识别功能，支持从证件图片自动提取信息并填充到案卷模板。

#### 技术架构变更
- **OCR 引擎**: 从 PaddleOCR 迁移至 RapidOCR
  - PaddleOCR 体积过大（200MB+），依赖复杂
  - RapidOCR 轻量（40MB），基于 ONNX Runtime，启动快且稳定
  - 删除了所有 Paddle 相关依赖和模型缓存

#### 新增功能
1. **信息识别对话框** (`src/gui/info_extraction_dialog.py`)
   - 双栏布局：左侧文件列表 + 右侧识别结果
   - 支持批量添加图片/PDF
   - 进度条显示识别进度
   - 一键应用到案卷变量

2. **图片预览功能** (`src/gui/widgets/image_list_widget.py`)
   - 单张图片时自动显示预览
   - PDF 自动转换为图片预览
   - 选中文件时预览自动切换

3. **OCR 结果展示** (`src/gui/widgets/ocr_result_widget.py`)
   - 字段编辑（可手动修正）
   - 置信度指示器（高/中/低颜色标识）
   - 低置信度字段红色警告

4. **文档解析器** (`src/core/ocr/parsers/`)
   - ✅ 身份证解析器（已实现）
   - ⚠️ 户口簿/护照/驾驶证等（框架已搭建）

5. **主界面集成** (`src/gui/main_window.py`)
   - 新增"信息识别"按钮（橙色）
   - 位于"清空"和"预览"按钮之间

#### 文件变更
| 文件 | 说明 |
|------|------|
| `src/core/ocr/` | 新增 OCR 模块目录 |
| `src/gui/info_extraction_dialog.py` | 信息识别主对话框 |
| `src/gui/widgets/image_list_widget.py` | 图片列表+预览 |
| `src/gui/widgets/ocr_result_widget.py` | OCR 结果展示 |
| `src/core/data/info_storage.py` | 识别数据存储 |
| `requirements.txt` | 替换 paddleocr 为 rapidocr-onnxruntime |

---

### v1.1.4 代码质量全面审查 (2026-03-05)

本次更新是一次全面的代码审查和优化，修复了多个严重问题、性能问题和安全隐患。

#### 严重问题修复 ✅
1. **重复方法定义**: `template_manager.py` 中删除重复的 `_on_browse_template` 方法
2. **版本号同步**: 统一 `app.py` 和 `main_window.py` 版本号为 1.1.4
3. **文件名非法字符**: `default_templates.py` 中中文引号替换为下划线
4. **单例模式线程安全**: 添加双重检查锁定模式

#### 性能优化 ✅
1. **模板扫描缓存**: `TemplatePathManager` 添加缓存机制，TTL 30秒
2. **变量列表刷新优化**: 使用 `setVisible()` 过滤而非重建控件
3. **配置批量更新**: 添加 `batch_update()` 上下文管理器

#### 安全加固 ✅
1. **路径遍历防护**: `resolve_template_path()` 添加路径安全检查
2. **配置文件验证**: 添加 `_validate_config()` 和 `_validate_templates()` 验证

### v1.1.2 新增功能 (2026-03-02)

#### Word 模板制作器右键菜单 ✅
**文件**: `src/gui/widgets/word_preview.py`, `src/gui/template_maker.py`
- 功能: 预览区域选中文本后右键可直接"替换选中"
- 去掉了默认的 Copy/Select All 菜单
- 选中文本时显示"替换选中..."菜单项
- 无选中文本时显示"请先选择文字"提示

### v1.1.1 修复 (2026-03-01)

#### 1. 模板管理器文件名包含 "✓" 符号 ✅
**文件**: `src/gui/template_manager.py`, `src/utils/validators.py`
- 问题: 导出的 Word 文件名变成 `xxx.docx✓`
- 修复: 在保存 name 字段时清理显示标记符号

#### 2. Word 模板制作器文本选择只获取首字 ✅
**文件**: `src/gui/widgets/word_preview.py`, `src/gui/template_maker.py`
- 问题: 选择多个文字时只获取首字
- 修复: 改用 `selectionChanged` 信号，打开对话框时直接获取选中文本

#### 3. 变量同步问题 ✅
**文件**: `src/gui/template_maker.py`
- 问题: 模板管理器和 Word 模板制作器变量不同步
- 修复: 从配置管理器读取用户自定义变量

#### 4. Word 预览高亮格式问题 ✅
**文件**: `src/gui/widgets/word_preview.py`
- 问题: 变量后面的普通文字也被高亮
- 修复: 插入普通文本时显式设置默认格式

#### 5. 撤销功能崩溃问题 ✅
**文件**: `src/core/word_editor.py`, `src/gui/template_maker.py`
- 问题: 点击撤销后 `IndexError: pop from empty list`
- 修复: 移除多余的 `pop()` 调用，添加刷新预览逻辑

### v1.1.0 修复

#### 1. Word COM 预览失败 ✅
**文件**: `src/gui/widgets/word_preview.py`
- 问题: `asObject()` 是 PyQt5 API，PySide6 不支持
- 修复: 改用 python-docx 进行文本预览

#### 2. 替换后预览不更新 ✅
**文件**: `src/gui/template_maker.py`
- 问题: 替换后从原文件重新加载，不显示修改
- 修复: 添加 `set_preview_text()` 从内存更新预览

#### 3. 字符串引号语法错误 ✅
**文件**: `src/gui/template_maker.py:864`
- 问题: 中文引号与 Python 字符串引号冲突
- 修复: 将外层双引号改为单引号

### v1.0.2 修复

#### 1. 系统模板库无法显示模板 ✅
**文件**: `src/utils/template_path_manager.py:110-174`
- 修改 `get_available_templates()` 扫描所有子目录
- 现在可以找到 34 个模板（之前是 0 个）

### 2. Word 文档变量被删除 ✅
**文件**: `src/core/template_engine.py:69-103`
- 修改 `_prepare_context()` 跳过 None/空值
- 未填写的变量保留为 `{{变量名}}` 占位符

### 3. 模板管理器文件夹结构不同步 ✅
**文件**: `src/gui/template_manager.py`
- 添加 `itemChanged` 信号处理器
- 修复新建/重命名逻辑
- 确保 user_data 包含 "name" 字段

### 4. 应用启动崩溃 ✅
**文件**: `src/core/folder_generator.py`
- 添加防御性检查处理缺失 "name" 字段

---

## 🎯 核心代码位置速查

| 功能 | 文件 | 行号 | 说明 |
|------|------|------|------|
| OCR 引擎 | `src/core/ocr/paddle_engine.py` | - | RapidOCR 封装 |
| 身份证解析 | `src/core/ocr/parsers/id_card_parser.py` | - | 姓名/性别/民族/住址/身份证号提取 |
| 字段匹配 | `src/core/ocr/field_matcher.py` | - | 识别字段→模板变量映射 |
| 信息识别对话框 | `src/gui/info_extraction_dialog.py` | - | 主界面 |
| 图片预览 | `src/gui/widgets/image_list_widget.py` | - | 列表+预览 |
| OCR 结果展示 | `src/gui/widgets/ocr_result_widget.py` | - | 字段编辑+置信度显示 |
| 模板路径管理 | `src/utils/template_path_manager.py` | 110-174 | `get_available_templates()` |
| 变量替换 | `src/core/template_engine.py` | 69-103 | `_prepare_context()` |
| 变量提取 | `src/core/template_engine.py` | 93-148 | `extract_variables()` |
| 文件夹生成 | `src/core/folder_generator.py` | 70-97 | `generate()` |
| 文件夹预览 | `src/core/folder_generator.py` | 319-396 | `preview()` / `_preview_folder()` |
| 模板管理器 | `src/gui/template_manager.py` | 296-448 | 添加/重命名/删除 |
| 模板关联 | `src/gui/template_file_dialog.py` | 352-381 | 变量显示 |

---

## 🐛 常见问题诊断

### 问题 1: 应用启动崩溃
**症状**: `KeyError: 'name'`
**原因**: 用户配置文件中有格式错误的条目
**检查**: `src/core/folder_generator.py` 的 `_preview_folder` 方法
**已修复**: 添加了防御性检查

### 问题 2: 模板库显示为空
**症状**: "暂无可用模板"
**原因**: `get_available_templates()` 未扫描子目录
**检查**: `src/utils/template_path_manager.py:124-144`
**已修复**: 修改为扫描所有子目录

### 问题 3: 变量被删除
**症状**: Word 文档中变量位置为空
**原因**: `_prepare_context()` 将 None 转为空字符串
**检查**: `src/core/template_engine.py:82-84`
**已修复**: 改为跳过 None 值

### 问题 4: 模板管理器不同步
**症状**: 修改后预览不更新
**原因**: 名称未同步到 user_data
**检查**: `src/gui/template_manager.py` 的 `_on_item_changed`
**已修复**: 添加信号处理器

---

## 🧪 测试命令

### 运行应用
```bash
cd C:\Users\49144\Desktop\ClaudeCodeHub\filemst\LawyerCaseTool
python src/main.py
```

### 运行测试
```bash
# 测试模板系统和变量替换
python test_fixes_part2.py

# 测试模板关联
python test_word_template.py
```

### 创建测试模板
```bash
python scripts/create_test_templates.py
```

---

## 📝 重要配置文件

### 用户配置位置
- Windows: `%APPDATA%\LawyerCaseTool\`（兼容保留旧目录名）
  - `config/config.json` - 应用配置
  - `config/templates.json` - 模板配置（⭐ 重要，经常出错）

### 系统配置
- `src/config/default_templates.py` - 默认模板定义
- `src/config/path_manager.py` - 路径配置

---

## 🔄 开发工作流

### 修复 Bug 的标准流程
1. 在 `src/` 中找到相关文件
2. 修复问题
3. 运行 `test_fixes_part2.py` 验证
4. 更新相关文档
5. 提交 git

### 添加新功能的标准流程
1. 确定功能位置（core/gui/utils/config）
2. 编写代码
3. 添加测试
4. 更新 CHANGELOG.md
5. 提交 git

---

## 📦 依赖管理

### 安装依赖
```bash
pip install -r requirements.txt
```

### 主要依赖
- PySide6 >= 6.4.0 (GUI)
- rapidocr-onnxruntime >= 1.4.0 (OCR 识别) ⭐ 新增 (v1.2.0)
- python-docx >= 0.8.11 (Word 文档)
- docxtpl >= 0.16.7 (Word 模板)
- PyMuPDF >= 1.23.0 (PDF 处理) ⭐ 新增 (v1.2.0)

---

## 🔍 调试技巧

### 启用调试日志
在代码中添加：
```python
from src.utils.logger import get_logger
logger = get_logger()
logger.setLevel(logging.DEBUG)
```

### 常用日志位置
- 模板扫描: `TemplatePathManager.get_available_templates()`
- 变量替换: `TemplateEngine._prepare_context()`
- 文件夹生成: `FolderGenerator._create_file()`

---

## 🐛 当前待修复问题

暂无待修复问题。

---

## 📓 今日开发日记

详见 `docs/diary/2026-03-10_OCR功能完善与界面优化_diary.md`

今日关键词：分割器、重新识别、多行地址、图片缩放

---

## 📌 下次开发重点

### ✅ Word 模板制作器（v1.1.0 已实现）

**功能概述**：让用户自行制作 Word 模板，上传到分类文件夹并进行变量替换

**已实现功能**：
1. ✅ 上传 Word 文档到 civil/criminal/non_litigation 分类
2. ✅ Word 文档预览（支持选中文字）
3. ✅ 两种替换方式：选中替换 + 手动输入替换
4. ✅ 格式保持的文本替换（字体、字号、颜色等）
5. ✅ 智能变量推荐
6. ✅ 主窗口菜单栏和工具栏入口

**入口位置**：
- 菜单栏：模板(T) → 制作 Word 模板（快捷键 Ctrl+M）
- 工具栏："制作模板"按钮

**相关文件**：
- `src/gui/template_maker.py` - 模板制作器主窗口
- `src/gui/widgets/word_preview.py` - Word 预览控件
- `src/core/word_editor.py` - Word 编辑器核心

### 待优化项
1. Word COM 预览优化（提高稳定性）
2. 模板管理器实时同步优化
3. 添加模板验证功能
4. 支持模板导入/导出
5. 优化变量输入界面

### 已知问题
- Word COM 预览依赖 Office 安装（有回退方案）
- 重命名后需要点击其他项目才能看到同步效果（非阻塞）
- .doc 格式文件不支持变量提取（格式限制）

---

## 🚀 提交代码前检查清单

- [ ] 运行 `test_fixes_part2.py` 确保测试通过
- [ ] 更新 CHANGELOG.md
- [ ] 更新 VERSION（如果需要）
- [ ] 运行应用确保没有明显错误
- [ ] 提交前检查 `git status`

---

## 📞 获取帮助

### 查看最近的提交
```bash
git log --oneline -5
```

### 查看最近的修改
```bash
git diff HEAD~1
```

### 回滚到上一个版本
```bash
git reset --hard HEAD~1
```

---

*最后更新: 2026-03-10 深夜*
*版本: 1.2.0*

### 今日更新
- ✅ 信息识别界面布局优化（可分割调节）
- ✅ 重新识别功能修复（支持单文件重新识别）
- ✅ 身份证多行住址识别修复
- ✅ 图片预览缩放功能（10%~500%，支持滚轮缩放）

### v1.3.0 规划

- [ ] 户口簿解析器完整实现
- [ ] 护照解析器完整实现
- [ ] 驾驶证/营业执照解析器
- [ ] 历史记录对话框
- [ ] 数据库支持
- [ ] 多语言支持
