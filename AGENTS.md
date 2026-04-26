# AGENTS.md

本文件为 AI 编程助手提供项目背景、架构和开发指南。预期读者为对该项目一无所知的 AI 助手。

## 项目概述

**案件文件夹管理系统** (显示名称) 是一个基于 Python + PySide6 的桌面应用程序，面向以本地文件夹管理案件材料的法律从业者。系统以案件目录为核心载体，提供案件台账、模板生成、OCR 信息识别、电子归档和工具中心能力。

### 主要功能

- **案件管理**: 管理本地案件目录、标签、状态、期限、路径历史和笔记
- **模板管理**: 创建、编辑、复制和删除案件目录模板（民事、刑事、非诉、仲裁等）
- **变量替换**: 支持 `{{variable_name}}` 格式在文件夹名称和 Word 文档中进行变量替换
- **批量生成**: 一键生成完整的案件文件夹结构和初始文档
- **OCR 与归档**: 识别证件/裁判文书信息，支持电子化归档、截图合并 PDF
- **Windows 右键菜单集成**: 在资源管理器右键菜单中添加“在此处新建案件目录”选项
- **实时预览**: 生成前预览文件夹结构

### 目标用户

法律行业从业者，特别是依赖本地文件夹组织案件材料、文书和办案节点的律师团队。

## 技术栈

| 类别 | 技术 |
|------|------|
| 编程语言 | Python 3.8+ |
| GUI 框架 | PySide6 >= 6.4.0 |
| Word 处理 | python-docx >= 0.8.11, docxtpl >= 0.16.7 |
| 打包工具 | PyInstaller >= 5.0.0 |
| 测试框架 | pytest >= 7.0.0 |

### 系统要求

- **操作系统**: Windows 10 或更高版本，macOS
- **Python**: 3.8+
- **权限**: 安装右键菜单需要管理员权限

## 项目结构

```
LawyerCaseTool/
├── src/                      # 源代码
│   ├── main.py              # 应用程序入口
│   ├── app.py               # QApplication 单例管理
│   ├── core/                # 核心业务逻辑
│   │   ├── variable_parser.py    # 变量解析器，处理 {{variable}} 格式
│   │   ├── folder_generator.py   # 文件夹结构生成器
│   │   ├── template_engine.py    # Word 模板处理（docxtpl）
│   │   ├── batch_processor.py    # 批量处理器
│   │   └── word_editor.py        # Word 文档编辑工具
│   ├── gui/                 # GUI 界面（PySide6）
│   │   ├── main_window.py        # 主窗口
│   │   ├── generation_dialog.py  # 生成对话框
│   │   ├── template_manager.py   # 模板管理器
│   │   ├── template_maker.py     # 模板制作器
│   │   ├── settings_dialog.py    # 设置对话框
│   │   └── widgets/              # 自定义控件
│   │       ├── template_card.py
│   │       ├── variable_input.py
│   │       ├── folder_tree.py
│   │       └── word_preview.py
│   ├── config/              # 配置管理
│   │   ├── config_manager.py     # 单例配置管理器
│   │   ├── path_manager.py       # 路径管理
│   │   └── default_templates.py  # 默认模板定义
│   ├── integration/         # 系统集成
│   │   ├── registry_manager.py   # Windows 注册表管理
│   │   └── context_menu.py       # 右键菜单集成
│   └── utils/               # 工具模块
│       ├── logger.py             # 日志管理
│       ├── exceptions.py         # 自定义异常
│       ├── validators.py         # 验证器
│       ├── file_utils.py         # 文件工具
│       ├── migration.py          # 配置迁移
│       └── template_path_manager.py  # 模板路径管理
├── tests/                   # 测试文件
│   ├── test_config_manager.py
│   ├── test_folder_generator.py
│   └── test_template_engine.py
├── scripts/                 # 脚本文件
│   ├── install_context_menu.py   # 安装右键菜单（需管理员权限）
│   ├── uninstall_context_menu.py # 卸载右键菜单
│   └── create_templates.py       # 创建模板
├── templates/               # 模板文件目录
│   ├── civil/               # 民事案件模板
│   ├── criminal/            # 刑事案件模板
│   └── non_litigation/      # 非诉案件模板
├── resources/               # 资源文件
│   └── icons/               # 图标文件
├── pyproject.toml          # Python 项目配置
├── requirements.txt        # 依赖列表
└── VERSION                 # 版本号文件（当前 2.0.0）
```

## 关键设计模式

### 1. 单例模式（线程安全）

以下类使用单例模式，通过 `get_xxx()` 函数获取实例：

```python
# 双重检查锁定模式实现
class ConfigManager:
    _instance: Optional['ConfigManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
```

涉及的单例类：
- `Application` (`src/app.py`) - 通过 `get_application()` 获取
- `ConfigManager` (`src/config/config_manager.py`) - 通过 `get_config_manager()` 获取
- `PathManager` (`src/config/path_manager.py`) - 通过 `get_path_manager()` 获取
- `LoggerManager` (`src/utils/logger.py`) - 通过 `get_logger()` 获取

### 2. 变量系统

使用 `{{variable_name}}` 格式定义变量：

```python
# 变量解析器使用正则表达式
VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')

# 示例
structure = {
    "root_name": "{{case_number}}_{{client_name}}",
    "folders": [
        {"name": "{{folder_name}}", "subfolders": []}
    ]
}
```

### 3. 模板结构

模板配置包含以下字段：

```python
{
    "id": "civil_001",                    # 唯一标识
    "name": "民事案件模板",                # 显示名称
    "description": "适用于民事诉讼案件",    # 描述
    "category": "civil",                  # 分类
    "template_file": "templates/civil/template.docx",
    "folder_structure": {
        "root_name": "{{case_number}}_{{client_name}}",
        "folders": [
            {
                "name": "0委托手续",
                "subfolders": [
                    {
                        "name": "委托合同.docx",
                        "type": "file",
                        "template_path": "civil/委托合同.docx",
                        "use_template": True
                    }
                ]
            }
        ]
    },
    "variables": [
        {
            "key": "case_number",
            "label": "案号",
            "type": "text",
            "required": True
        }
    ]
}
```

## 配置存储

### 存储位置

Windows: `%APPDATA%/LawyerCaseTool/`（为兼容现有用户数据，目录名暂保留旧标识）

```
%APPDATA%/LawyerCaseTool/
├── config.json          # 应用配置
├── templates.json       # 模板配置
└── logs/                # 日志文件
    └── lawyer_tool_20260310.log
```

### 配置结构

```json
{
  "app": {
    "language": "zh_CN",
    "theme": "default",
    "check_updates": true,
    "last_template_id": ""
  },
  "generation": {
    "default_output_dir": "C:\\Users\\xxx\\案卷",
    "auto_open_folder": true,
    "create_readme": false
  },
  "ui": {
    "window_width": 1000,
    "window_height": 700,
    "show_preview": true
  }
}
```

## 常用命令

### 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python src/main.py

# 运行测试
pytest tests/

# 运行单个测试文件
pytest tests/test_template_engine.py -v
```

### 打包部署

```bash
# 打包为 EXE（单文件）
pyinstaller --name="案件文件夹管理系统" --windowed --onefile --icon=resources/icons/app.ico src/main.py

# 安装/卸载 Windows 右键菜单（需管理员权限）
python scripts/install_context_menu.py
python scripts/uninstall_context_menu.py
```

## 代码规范

### 文件头格式

所有 Python 文件必须包含以下文件头：

```python
# -*- coding: utf-8 -*-
"""模块简要描述"""
```

### 类型注解

推荐使用类型注解，特别是公共 API：

```python
from pathlib import Path
from typing import Dict, Any, Optional, List

def process_template(
    template_path: Path,
    output_path: Path,
    values: Dict[str, Any]
) -> Path:
    ...
```

### 异常处理

使用项目自定义异常体系，避免捕获所有异常：

```python
from src.utils.exceptions import (
    LawyerToolError,      # 基础异常
    TemplateError,        # 模板相关
    TemplateNotFoundError,
    TemplateFileError,
    VariableError,        # 变量相关
    VariableValidationError,
    VariableMissingError,
    FolderGenerationError,
    ConfigError,
    RegistryError,
    PermissionDeniedError
)

# 好的做法：区分具体异常类型
try:
    doc = DocxTemplate(str(template_path))
except FileNotFoundError as e:
    raise TemplateFileError(str(template_path), "文件不存在")
except PermissionError as e:
    raise TemplateFileError(str(template_path), "无权限访问")
except KeyError as e:
    raise TemplateFileError(str(template_path), f"格式错误: {e}")
```

### 日志记录

使用项目统一的日志管理器：

```python
from src.utils.logger import get_logger

logger = get_logger()

# 不同级别
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

## 测试策略

### 测试框架

使用 pytest，测试文件放在 `tests/` 目录，命名规范为 `test_*.py`。

### 测试类结构

```python
# -*- coding: utf-8 -*-
"""测试模块描述"""

import pytest
from pathlib import Path

class TestClassName:
    """测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        pass

    def teardown_method(self):
        """每个测试方法后执行"""
        pass

    def test_specific_feature(self):
        """测试特定功能"""
        assert True
```

### 测试命令

```bash
# 运行所有测试
pytest tests/

# 详细输出
pytest tests/ -v

# 运行特定测试类
pytest tests/test_folder_generator.py::TestFolderGenerator -v

# 运行特定测试方法
pytest tests/test_folder_generator.py::TestFolderGenerator::test_preview_structure -v
```

## 安全注意事项

### 路径遍历防护

处理用户输入路径时，必须进行安全检查：

```python
from src.utils.template_path_manager import TemplatePathManager

# 使用 TemplatePathManager 提供的安全方法
manager = TemplatePathManager()
safe_path = manager.resolve_template_path(user_input)
```

### 配置文件验证

加载 JSON 配置时必须验证结构：

```python
def _validate_config(self, config: Dict[str, Any]) -> bool:
    if not isinstance(config, dict):
        return False
    required_keys = ['app', 'generation', 'ui']
    for key in required_keys:
        if key not in config:
            return False
    return True
```

## UI 设计规范

### 现代化 UI 设计（v2.0 规划中）

项目正在进行现代化 UI 改造，参考 VS Code、Linear、Notion 等 2025 年主流应用设计语言。

#### 设计原则

1. **清晰的信息层次** - 重要信息优先显示
2. **一致的视觉语言** - 统一的颜色、间距、圆角
3. **高效的交互路径** - 减少点击次数
4. **即时反馈** - 操作状态清晰可见
5. **可预测性** - 符合用户心智模型

#### 布局结构（规划中）

```
┌─────────────────────────────────────────────────────────────┐
│  顶部工具栏 (面包屑导航 + 全局操作)                          │
├──────────┬──────────────────────────────┬───────────────────┤
│          │                              │                   │
│  左侧    │         中间                 │      右侧         │
│  模板    │      变量表单                │   预览面板        │
│  导航    │      输入区域                │   320px           │
│  260px   │      自适应                  │                   │
│          │                              │                   │
└──────────┴──────────────────────────────┴───────────────────┘
```

#### 配色系统

```css
/* 主色调 - 专业蓝 */
--primary: #2563eb;
--primary-hover: #1d4ed8;
--primary-light: #dbeafe;

/* 语义色 */
--success: #10b981;   /* 成功 - 绿色 */
--warning: #f59e0b;   /* 警告 - 黄色 */
--danger: #ef4444;    /* 危险 - 红色 */
--info: #3b82f6;      /* 信息 - 蓝色 */

/* 中性色 */
--gray-50: #f9fafb;   /* 最浅背景 */
--gray-100: #f3f4f6;  /* 卡片背景 */
--gray-200: #e5e7eb;  /* 边框 */
--gray-500: #6b7280;  /* 次要文字 */
--gray-700: #374151;  /* 标题 */
```

#### 设计文档

- `docs/MODERN_UI_DESIGN_GUIDE.md` - 详细设计规范
- `prototypes/modern_ui_design_2025.html` - HTML 交互原型

---

## 性能优化

### 批量更新模式

当需要多次修改配置时，使用批量更新模式减少磁盘写入：

```python
from src.config.config_manager import get_config_manager

config_manager = get_config_manager()

# 使用上下文管理器
with config_manager.batch_update():
    config_manager.set('key1', 'value1')
    config_manager.set('key2', 'value2')
    # 只在退出时保存一次
```

### 模板扫描缓存

`TemplatePathManager` 内置缓存机制，TTL 为 30 秒：

```python
# 自动使用缓存
manager.get_available_templates()

# 手动清除缓存
manager.clear_cache()
```

## 版本历史

- **v2.0.0** (2026-04-21): 工作台快捷操作全面重构（6个按钮功能重映射、顶部新建案件修复），Dashboard柱状图交互链路打通（hover高亮、clip防溢出、分类筛选跳转），案件中心筛选面板分组分隔线
- **v1.6.1** (2026-04-18): 核心稳定性修复（配置深拷贝、案件删除回滚、模板路径解析/去重、Word 占位符保留、另存为后续保存），对外名称与产品定位调整为“案件文件夹管理系统”
- **v1.4.0** (2026-03-31): 图片预览缩放控件，对方当事人智能映射（被告模板直接填入原告/申请人变量），默认配置同步，全面代码审查（6处bug修复、死代码清理、统一配色方案），18/18测试通过
- **v1.3.1** (2026-03-25): Word模板制作器功能修复（跨Run文本替换），添加自定义变量功能增强（与模板管理变量定义整合）
- **v1.2.21** (2026-03-15): 模板管理界面UI精简（去边框、紧凑化），模板制作器重构（实时文件浏览器、图标系统），模板置顶功能
- **v1.2.5** (2026-03-15): UI 全面现代化改造，搜索筛选功能，可编辑文件夹预览
- **v1.2.4** (2026-03-15): 项目全面整理，删除冗余文档，修复弃用API
- **v1.2.3** (2026-03-13): 代码质量全面审查，修复线程安全、竞态条件等问题
- **v1.2.2** (2026-03-12): 默认模板扩展至8个，新增劳动仲裁、商事仲裁模板
- **v1.2.1** (2026-03-11): OCR 字段全面应用优化，模板管理功能修复
- **v1.2.0** (2026-03-10): OCR 信息识别功能上线，支持身份证等证件识别
- **v1.1.4** (2026-03-05): 代码质量优化，修复线程安全问题，添加批量更新模式
- **v1.0.x**: 初始版本，基础功能实现

版本号记录在 `VERSION` 文件中。

## 故障排查

### 常见问题

1. **右键菜单安装失败**: 确保以管理员身份运行脚本
2. **Word 模板无法加载**: 检查 `docxtpl` 和 `python-docx` 是否正确安装
3. **配置加载失败**: 检查 `%APPDATA%/LawyerCaseTool/config.json` 的 JSON 格式

### 调试技巧

- 查看日志文件: `%APPDATA%/LawyerCaseTool/logs/`
- 使用 `--directory` 参数从命令行启动指定输出目录
- 使用 `--template` 参数从命令行启动指定模板

## 许可证

MIT License
