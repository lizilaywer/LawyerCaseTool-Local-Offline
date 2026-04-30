# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

案件文件夹管理系统 - 一款以本地文件夹为核心载体的案件管理桌面应用，支持案件台账、模板生成、OCR、归档与工具中心。

**当前版本**: v2.0.0 (2026-04-30)

**开发者**: 汪立（安徽始信律师事务所执业律师）

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python src/main.py

# 运行测试
pytest tests/

# 运行单个测试文件
pytest tests/test_template_engine.py

# 打包为 EXE
pyinstaller --name="案件文件夹管理系统" --windowed --onefile --icon=resources/icons/app.ico src/main.py

# 安装/卸载 Windows 右键菜单（需管理员权限）
python scripts/install_context_menu.py
python scripts/uninstall_context_menu.py
```

## 近期更新

### v2.1.0 (2026-04-30) - 工具中心大升级与开发者品牌
- **自动排版**: 新增 Word 文档自动排版功能，参照 GB/T 9704-2012 标准智能识别标题层级并应用法律文书格式（方正小标宋/黑体/仿宋）
- **文档对比**: 新增 Word 文档对比功能，左右双栏展示差异
- **法院短信增强**: 支持拖拽 PDF/图片到输入框自动识别传票信息；新增被传唤人提取；庭审识别结果支持双击编辑；新增"不关联案件"按钮直接保存到桌面
- **OCR 传票解析**: 多策略解析传票中的被传唤人姓名（PDF 紧凑文本/OCR 片段拼接/标题提取）
- **设置-关于页**: 新增精美"关于"标签页，展示开发者信息、社交媒体、二维码占位
- **开发者署名**: 全局更新作者信息为汪立律师（__author__、pyproject.toml、关于对话框、User-Agent 等）

### v1.5.0 (2026-04-02) - 案件管理与期限日历系统
- **案件管理**: 新增案件管理对话框，支持按状态分组（进行中/待立案/已结案）、分类筛选、搜索、导入已有文件夹
- **案件详情面板**: 从 `case["variables"]` 提取关键字段（案由/法院/案号/委托人等）以键值对网格展示；期限提醒前置并增加醒目样式；文件树+预览并排布局；案件速记编辑器（Markdown 工具栏 + 1秒防抖自动保存）
- **期限日历**: 自绘日历控件（QPainter），彩色圆点标记期限（红=期限/蓝=开庭/黄=自定义），支持添加/删除期限和开庭
- **案件卡片**: 60px 紧凑型卡片，含分类色条、状态标签、标签 chips、更新日期
- **生成自动注册**: 生成案卷后自动注册到案件管理并创建 `.case/notes.md` 速记文件
- **文件树懒加载**: 案件详情面板中的文件树支持懒加载（展开时才读取子目录）
- **UI 对齐设计稿**: 对照 PRODUCT_ROADMAP 设计稿优化布局，包括筛选栏合并单行、状态分组标题加色条、期限提醒区醒目化

### v1.4.0 (2026-03-31) - 全面代码审查与功能优化
- **图片预览优化**: 电子化归档中图片预览新增缩放控件（放大/缩小/适应宽度/适应窗口/原始大小），与 PDF 预览体验一致；图片预览自动隐藏翻页控件
- **对方当事人智能映射**: 信息识别中"是否为对方当事人"勾选后，对4个被告/被申请人模板（民事被告、行政被告、劳动仲裁被申请人、商事仲裁被申请人）直接将对方姓名填入原告/申请人变量，不再生成多余变量
- **默认配置同步**: 将运行时模板配置（含 Word 模板关联路径、用户自定义变量等）同步为代码默认值；消除 `config_manager._get_default_config()` 与 `DEFAULT_*_CONFIG` 常量的重复定义
- **代码质量**: 修复 6 处 bug（属性调用、原子写入、命令注入等），统一变量正则，增强文件名校验，清理死代码，新建统一配色方案 `styles.py`，18/18 测试通过

### v1.2.21 (2026-03-15) - 模板管理与制作器优化
- 模板管理界面去边框化、紧凑化（Modern UI v3）
- 模板制作器重构：实时文件浏览器、单击双击分离
- 文件夹结构树添加 📁📄📎 图标系统
- 模板置顶功能：全部最多3个，分类最多1个
- 工具栏按钮整合优化

### v1.2.4 (2026-03-15) - 项目全面整理
- 删除8个冗余文档，精简项目结构
- 修复 PySide6 弃用 API
- 统一版本号管理
- 更新 OCR 依赖文档

### v1.2.3 (2026-03-13) - 代码质量审查
- 修复单例模式线程安全问题（PathManager、LoggerManager）
- 修复 BatchProcessor 竞态条件
- 实现配置文件原子写入
- 添加模板引擎缓存机制
- 完善资源清理和异常处理

### v1.2.2 (2026-03-12) - 模板扩展
- 默认模板从3个扩展到8个
- 新增劳动仲裁、商事仲裁模板
- 新增民事案件模板(被告)

### v1.2.0 (2026-03-10) - OCR 功能
- 新增信息识别功能，支持身份证等证件识别
- 从 PaddleOCR 迁移至 RapidOCR

## 架构

```
src/
├── core/           # 核心业务逻辑
│   ├── variable_parser.py   # 变量解析器，处理 {{variable}} 格式
│   ├── folder_generator.py  # 文件夹结构生成器
│   ├── template_engine.py   # Word 模板处理（使用 docxtpl）
│   ├── batch_processor.py   # 批量处理器
│   ├── case_manager.py      # 案件索引管理器（CRUD/搜索/标签/期限）
│   ├── court_sms_service.py # 法院短信与传票解析服务
│   ├── docx_auto_format.py  # Word 文档自动排版引擎
│   └── docx_compare.py      # Word 文档文本对比
├── gui/            # GUI 界面（PySide6）
│   ├── main_window.py       # 主窗口
│   ├── generation_dialog.py # 生成对话框
│   ├── template_manager.py  # 模板管理器
│   ├── settings_dialog.py   # 设置对话框（含"关于"标签页）
│   ├── tool_center_dialog.py # 工具中心（法院短信/费用/文档对比/自动排版等）
│   ├── case_manager_dialog.py # 案件管理对话框
│   ├── case_detail_panel.py # 案件详情面板
│   ├── calendar_dialog.py   # 期限日历对话框
│   └── widgets/             # 自定义控件
│       ├── docx_auto_format_widget.py  # 自动排版界面
│       ├── docx_compare_widget.py      # 文档对比界面
│       ├── archive_file_tree.py        # 归档文件树
│       └── archive_preview.py          # 文件预览控件
├── config/         # 配置管理
│   ├── config_manager.py    # 单例配置管理器
│   ├── path_manager.py      # 路径管理
│   └── default_templates.py # 默认模板定义
├── integration/    # 系统集成
│   ├── registry_manager.py  # Windows 注册表管理
│   └── context_menu.py      # 右键菜单集成
└── utils/          # 工具模块
    ├── logger.py            # 日志
    ├── exceptions.py        # 自定义异常
    ├── validators.py        # 验证器
    └── file_utils.py        # 文件工具
```

## 关键设计模式

- **单例模式**: `Application`、`ConfigManager`、`PathManager`、`CaseManager` 都使用单例模式，通过 `get_xxx()` 函数获取实例
- **变量系统**: 使用 `{{variable_name}}` 格式定义变量，由 `VariableParser` 统一解析和替换
- **模板结构**: 模板配置包含 `root_name`（根目录名）和 `folders`（子文件夹列表）

## 配置存储位置

Windows: `%APPDATA%/LawyerCaseTool/`（兼容保留旧目录名）
- `config.json` - 应用配置
- `templates.json` - 模板配置
- `config/cases.json` - 案件索引
- `logs/` - 日志文件

## 依赖

- PySide6 >= 6.4.0 (GUI 框架)
- python-docx >= 0.8.11 (Word 文档处理)
- docxtpl >= 0.16.7 (Word 模板引擎)
