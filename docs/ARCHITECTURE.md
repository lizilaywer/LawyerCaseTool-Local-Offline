# 案件文件夹管理系统 - 架构设计文档

## 系统架构概述

案件文件夹管理系统采用分层架构设计，将业务逻辑、用户界面、配置管理和系统集成分离，确保以本地文件夹为核心载体的案件管理能力保持可维护、可扩展。

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户界面层 (GUI)                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │ MainWindow  │ │GenerationDlg│ │TemplateMgr  │ │SettingsDlg│  │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬─────┘  │
│         │               │               │               │        │
│  ┌──────┴───────────────┴───────────────┴───────────────┴─────┐  │
│  │                    自定义控件 (Widgets)                      │  │
│  │   TemplateCard │ VariableInput │ FolderTree                │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        核心业务层 (Core)                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │VariableParser│ │FolderGen   │ │TemplateEng │ │BatchProc  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        配置管理层 (Config)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│  │ConfigManager│ │PathManager  │ │DefaultTmpl  │                │
│  └─────────────┘ └─────────────┘ └─────────────┘                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      基础设施层 (Utils)                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │   Logger    │ │ Exceptions  │ │ Validators  │ │ FileUtils │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      系统集成层 (Integration)                     │
│  ┌────────────────────────────┐ ┌────────────────────────────┐   │
│  │     RegistryManager        │ │     ContextMenuManager     │   │
│  └────────────────────────────┘ └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 模块职责说明

### 1. 核心业务层 (src/core/)

| 模块 | 职责 |
|------|------|
| `variable_parser.py` | 变量解析器，处理 `{{variable}}` 格式的变量提取、替换和验证 |
| `folder_generator.py` | 文件夹结构生成器，根据模板配置创建目录结构 |
| `template_engine.py` | Word 模板处理引擎，使用 docxtpl 库处理 .docx 模板 |
| `batch_processor.py` | 批量处理器，支持批量生成多个案卷 |

### 2. 用户界面层 (src/gui/)

| 模块 | 职责 |
|------|------|
| `main_window.py` | 主窗口，包含模板选择、变量输入、预览等功能 |
| `generation_dialog.py` | 生成对话框，显示生成进度和结果 |
| `template_manager.py` | 模板管理器，支持模板的增删改查 |
| `settings_dialog.py` | 设置对话框，管理应用配置 |
| `widgets/` | 自定义控件（TemplateCard, VariableInput, FolderTree） |

### 3. 配置管理层 (src/config/)

| 模块 | 职责 |
|------|------|
| `config_manager.py` | 单例配置管理器，管理应用配置和模板配置 |
| `path_manager.py` | 路径管理器，统一管理配置文件、日志等路径 |
| `default_templates.py` | 默认模板定义，包含内置的案卷模板 |

### 4. 基础设施层 (src/utils/)

| 模块 | 职责 |
|------|------|
| `logger.py` | 日志管理器，支持文件和控制台输出 |
| `exceptions.py` | 自定义异常类，提供详细的错误信息 |
| `validators.py` | 数据验证器，支持文本、数字、日期、选择等类型 |
| `file_utils.py` | 文件操作工具函数 |

### 5. 系统集成层 (src/integration/)

| 模块 | 职责 |
|------|------|
| `registry_manager.py` | Windows 注册表管理，封装注册表操作 |
| `context_menu.py` | 右键菜单集成，支持在资源管理器中快速启动 |

## 数据流程

### 案卷生成流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  选择模板    │ ──▶ │  输入变量    │ ──▶ │  预览结构    │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  完成/打开   │ ◀── │  复制模板    │ ◀── │  生成文件夹  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 详细流程描述

1. **模板选择**
   - 用户从模板列表选择一个模板
   - 系统加载模板配置，提取变量定义

2. **变量输入**
   - VariableParser 解析模板中的变量
   - GUI 根据变量定义动态生成输入控件
   - Validators 验证用户输入

3. **预览结构**
   - FolderGenerator.preview() 生成预览数据
   - FolderTree 控件显示目录树结构

4. **生成执行**
   - FolderGenerator.generate() 创建文件夹结构
   - TemplateEngine.process_template() 处理 Word 模板
   - 复制模板文件到目标目录

5. **完成通知**
   - 显示生成结果
   - 可选：自动打开目标文件夹

## 关键设计模式

### 1. 单例模式 (Singleton)

多个核心类使用单例模式确保全局唯一实例：

```python
class ConfigManager:
    _instance: Optional['ConfigManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

# 使用工厂函数获取实例
def get_config_manager() -> ConfigManager:
    return ConfigManager()
```

应用的单例类：
- `ConfigManager` - 配置管理
- `PathManager` - 路径管理
- `LoggerManager` - 日志管理
- `Application` - 应用实例

### 2. 策略模式 (Strategy)

验证器使用策略模式，根据变量类型选择不同的验证策略：

```python
validators = {
    'text': TextValidator,
    'number': NumberValidator,
    'date': DateValidator,
    'select': SelectValidator
}
validator = validators.get(var_type, TextValidator)
```

### 3. 观察者模式 (Observer)

进度回调使用观察者模式：

```python
def set_progress_callback(self, callback: Callable[[int, int, str], None]):
    self._progress_callback = callback

def _report_progress(self, current: int, total: int, message: str):
    if self._progress_callback:
        self._progress_callback(current, total, message)
```

### 4. 模板方法模式 (Template Method)

验证器基类定义了验证接口，子类实现具体验证逻辑：

```python
class Validator:
    @staticmethod
    def validate(value: Any, rules: Dict[str, Any]) -> Tuple[bool, str]:
        raise NotImplementedError
```

## 模块依赖关系

```
                    ┌───────────────────┐
                    │      main.py      │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │       app.py      │
                    └─────────┬─────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
┌─────────▼─────────┐ ┌───────▼───────┐ ┌─────────▼─────────┐
│       gui/        │ │     core/     │ │   integration/    │
│  (PySide6 UI)     │ │  (Business)   │ │  (Windows API)    │
└─────────┬─────────┘ └───────┬───────┘ └─────────┬─────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │     config/       │
                    │  (Configuration)  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │      utils/       │
                    │   (Utilities)     │
                    └───────────────────┘
```

## 配置存储

### Windows 配置路径

```
%APPDATA%/LawyerCaseTool/
├── config.json        # 应用配置（主题、窗口大小等）
├── templates.json     # 模板配置
└── logs/              # 日志文件
    └── lawyer_tool_YYYYMMDD.log
```

### 配置文件格式

**config.json:**
```json
{
  "app": {
    "language": "zh_CN",
    "theme": "default",
    "check_updates": true,
    "last_template_id": ""
  },
  "generation": {
    "default_output_dir": "~/案卷",
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

## 扩展指南

### 添加新的变量类型

1. 在 `utils/validators.py` 中添加新的验证器类
2. 在 `validate_variable()` 函数中注册新类型
3. 在 `gui/widgets/variable_input.py` 中添加对应的输入控件

### 添加新的模板

1. 在 `config/default_templates.py` 中定义模板结构
2. 或通过 GUI 的模板管理器添加自定义模板

### 添加新的系统集成

1. 在 `integration/` 目录下创建新模块
2. 在 `settings_dialog.py` 中添加配置选项
