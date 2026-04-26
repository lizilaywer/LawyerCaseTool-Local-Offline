# 案件文件夹管理系统 - 核心 API 文档

## 核心模块

### VariableParser - 变量解析器

变量解析器用于处理模板中的 `{{variable}}` 格式变量。

**位置:** `src/core/variable_parser.py`

```python
from src.core.variable_parser import VariableParser

parser = VariableParser()
```

#### 方法

##### extract_variables(text: str) -> List[str]

从文本中提取变量名。

```python
text = "案卷_{{case_name}}_{{date}}"
variables = parser.extract_variables(text)
# 返回: ['case_name', 'date']
```

##### extract_from_structure(structure: Dict[str, Any]) -> List[str]

从文件夹结构配置中提取所有变量名。

```python
structure = {
    "root_name": "{{case_name}}",
    "folders": [
        {"name": "{{client_name}}_材料", "subfolders": []}
    ]
}
variables = parser.extract_from_structure(structure)
# 返回: ['case_name', 'client_name']
```

##### replace_variables(text: str, values: Dict[str, Any], sanitize: bool = False) -> str

替换文本中的变量为实际值。

```python
values = {"case_name": "张三案", "date": "2024-01-15"}
result = parser.replace_variables("案卷_{{case_name}}_{{date}}", values)
# 返回: "案卷_张三案_2024-01-15"

# sanitize=True 会清理非法文件名字符
result = parser.replace_variables("文件夹_{{name}}", {"name": "test<>file"}, sanitize=True)
# 返回: "文件夹_test__file"
```

##### validate_values(values: Dict[str, Any], variable_definitions: List[Dict[str, Any]]) -> Tuple[bool, List[str]]

验证变量值是否符合定义规则。

```python
definitions = [
    {"key": "case_name", "label": "案由", "type": "text", "required": True},
    {"key": "amount", "label": "金额", "type": "number", "validation": {"min_value": 0}}
]
values = {"case_name": "", "amount": -100}

is_valid, errors = parser.validate_values(values, definitions)
# 返回: (False, ["案由: 此字段为必填项", "金额: 值不能小于 0"])
```

##### check_required_variables(values: Dict[str, Any], variable_definitions: List[Dict[str, Any]]) -> List[str]

检查必填变量是否都有值。

```python
missing = parser.check_required_variables(values, definitions)
# 返回缺失的必填变量键列表
```

##### apply_defaults(values: Dict[str, Any], variable_definitions: List[Dict[str, Any]]) -> Dict[str, Any]

为未填写的变量应用默认值。

```python
definitions = [
    {"key": "status", "default_value": "进行中"}
]
result = parser.apply_defaults({}, definitions)
# 返回: {"status": "进行中"}
```

---

### FolderGenerator - 文件夹生成器

根据模板配置生成文件夹结构。

**位置:** `src/core/folder_generator.py`

```python
from src.core.folder_generator import FolderGenerator
from pathlib import Path

generator = FolderGenerator()
```

#### 方法

##### generate(structure: Dict[str, Any], values: Dict[str, Any], output_dir: Path, exist_ok: bool = False) -> Path

生成文件夹结构。

```python
structure = {
    "root_name": "{{case_name}}_案卷",
    "folders": [
        {"name": "01_起诉材料", "subfolders": ["起诉状", "证据材料"]},
        {"name": "02_庭审材料", "subfolders": []}
    ]
}
values = {"case_name": "张三案"}
output_dir = Path("C:/案卷")

root_path = generator.generate(structure, values, output_dir)
# 创建: C:/案卷/张三案_案卷/
#       ├── 01_起诉材料/
#       │   ├── 起诉状/
#       │   └── 证据材料/
#       └── 02_庭审材料/
```

##### preview(structure: Dict[str, Any], values: Dict[str, Any]) -> List[Dict[str, Any]]

预览文件夹结构（不实际创建）。

```python
preview_data = generator.preview(structure, values)
# 返回: [
#     {"name": "张三案_案卷", "level": 0, "type": "folder"},
#     {"name": "01_起诉材料", "level": 1, "type": "folder"},
#     {"name": "起诉状", "level": 2, "type": "folder"},
#     ...
# ]
```

##### get_required_variables(structure: Dict[str, Any]) -> List[str]

获取文件夹结构中使用的所有变量。

```python
variables = generator.get_required_variables(structure)
# 返回: ['case_name']
```

##### set_progress_callback(callback: Callable[[int, int, str], None])

设置进度回调函数。

```python
def on_progress(current, total, message):
    print(f"[{current}/{total}] {message}")

generator.set_progress_callback(on_progress)
```

---

### TemplateEngine - Word 模板引擎

处理 Word 模板文件，替换变量并生成新文档。

**位置:** `src/core/template_engine.py`

```python
from src.core.template_engine import TemplateEngine
from pathlib import Path

engine = TemplateEngine()
```

#### 方法

##### process_template(template_path: Path, output_path: Path, values: Dict[str, Any]) -> Path

处理 Word 模板，替换变量并保存。

```python
template_path = Path("templates/委托合同.docx")
output_path = Path("output/张三案/委托合同.docx")
values = {
    "client_name": "张三",
    "case_type": "民事纠纷",
    "date": datetime.now()
}

result = engine.process_template(template_path, output_path, values)
# 返回输出文件路径
```

##### extract_variables(template_path: Path) -> List[str]

从 Word 模板中提取变量名。

```python
variables = engine.extract_variables(template_path)
# 返回: ['client_name', 'case_type', 'date']
```

##### validate_template(template_path: Path) -> Tuple[bool, str]

验证模板文件是否有效。

```python
is_valid, error = engine.validate_template(template_path)
if not is_valid:
    print(f"模板无效: {error}")
```

##### copy_template(template_path: Path, output_path: Path) -> Path

直接复制模板文件（不替换变量）。

```python
result = engine.copy_template(template_path, output_path)
```

---

### ConfigManager - 配置管理器

单例配置管理器，管理应用配置和模板配置。

**位置:** `src/config/config_manager.py`

```python
from src.config.config_manager import ConfigManager, get_config_manager

# 使用工厂函数获取单例实例
config = get_config_manager()
```

#### 应用配置方法

##### get(key: str, default: Any = None) -> Any

获取配置值，支持点分隔的嵌套键。

```python
language = config.get("app.language", "zh_CN")
output_dir = config.get("generation.default_output_dir", "~/案卷")
window_width = config.get("ui.window_width", 1000)
```

##### set(key: str, value: Any, save: bool = True) -> None

设置配置值。

```python
config.set("app.last_template_id", "civil_001")
config.set("ui.window_width", 1200)
# save=False 可延迟保存
config.set("ui.window_height", 800, save=False)
```

##### get_all_config() -> Dict[str, Any]

获取所有配置。

```python
all_config = config.get_all_config()
```

##### reset_config() -> None

重置配置为默认值。

```python
config.reset_config()
```

#### 模板配置方法

##### get_templates() -> List[Dict[str, Any]]

获取所有模板。

```python
templates = config.get_templates()
# 返回: [
#     {"id": "civil_001", "name": "民事案件", "structure": {...}, ...},
#     ...
# ]
```

##### get_template(template_id: str) -> Optional[Dict[str, Any]]

获取指定模板。

```python
template = config.get_template("civil_001")
if template:
    print(f"模板名称: {template['name']}")
```

##### add_template(template: Dict[str, Any]) -> bool

添加新模板。

```python
new_template = {
    "id": "custom_001",
    "name": "自定义模板",
    "description": "我的自定义模板",
    "structure": {
        "root_name": "{{case_name}}",
        "folders": []
    },
    "variables": []
}
success = config.add_template(new_template)
```

##### update_template(template_id: str, template: Dict[str, Any]) -> bool

更新模板。

```python
template["name"] = "更新后的名称"
success = config.update_template("custom_001", template)
```

##### delete_template(template_id: str) -> bool

删除模板。

```python
success = config.delete_template("custom_001")
```

##### reset_templates() -> None

重置模板为默认值。

```python
config.reset_templates()
```

---

## 工具模块

### Logger - 日志管理器

**位置:** `src/utils/logger.py`

```python
from src.utils.logger import get_logger, setup_logging
from pathlib import Path

# 初始化日志系统
log_dir = Path("C:/AppData/LawyerCaseTool/logs")
logger = setup_logging(log_dir, console=True)

# 或直接获取已配置的日志器
logger = get_logger()

# 使用
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

---

### Validators - 数据验证器

**位置:** `src/utils/validators.py`

```python
from src.utils.validators import (
    validate_variable,
    validate_folder_name,
    sanitize_filename
)
```

#### validate_variable(value, var_type, required, rules)

验证变量值。

```python
# 文本验证
is_valid, error = validate_variable(
    "测试文本",
    var_type="text",
    required=True,
    rules={"min_length": 2, "max_length": 100}
)

# 数字验证
is_valid, error = validate_variable(
    "100",
    var_type="number",
    required=False,
    rules={"min_value": 0, "max_value": 1000}
)

# 日期验证
is_valid, error = validate_variable(
    "2024-01-15",
    var_type="date",
    required=True,
    rules={"format": "%Y-%m-%d"}
)

# 选择验证
is_valid, error = validate_variable(
    "option1",
    var_type="select",
    required=True,
    rules={"options": ["option1", "option2", "option3"]}
)
```

#### sanitize_filename(filename: str) -> str

清理文件名中的非法字符。

```python
safe_name = sanitize_filename('test<>:"/\\|?*file')
# 返回: "test_________file"
```

#### validate_folder_name(name: str) -> Tuple[bool, str]

验证文件夹名称。

```python
is_valid, error = validate_folder_name("我的文件夹")
is_valid, error = validate_folder_name("CON")  # 返回 False，保留名称
```

---

### Exceptions - 自定义异常

**位置:** `src/utils/exceptions.py`

```python
from src.utils.exceptions import (
    LawyerToolError,      # 基础异常
    TemplateError,        # 模板错误
    TemplateNotFoundError,
    TemplateFileError,
    VariableError,        # 变量错误
    VariableValidationError,
    VariableMissingError,
    FolderGenerationError,  # 文件夹生成错误
    ConfigError,          # 配置错误
    ConfigNotFoundError,
    RegistryError,        # 注册表错误
    PermissionDeniedError
)
```

使用示例：

```python
try:
    generator.generate(structure, values, output_dir)
except FolderGenerationError as e:
    logger.error(f"文件夹生成失败: {e.message}")
except PermissionDeniedError as e:
    logger.error(f"权限不足: {e.message}")
```

---

## 系统集成模块

### ContextMenuManager - 右键菜单管理

**位置:** `src/integration/context_menu.py`

```python
from src.integration.context_menu import (
    ContextMenuManager,
    install_context_menu,
    uninstall_context_menu,
    is_context_menu_installed
)
```

#### 使用便捷函数

```python
# 安装右键菜单
success = install_context_menu(icon_path="resources/icons/app.ico")

# 检查是否已安装
if is_context_menu_installed():
    print("右键菜单已安装")

# 卸载右键菜单
success = uninstall_context_menu()
```

#### 使用类方法

```python
manager = ContextMenuManager()

# 获取详细安装状态
status = manager.get_install_status()
print(f"背景菜单: {status['background_menu']}")
print(f"文件夹菜单: {status['directory_menu']}")
```

---

## 完整使用示例

### 示例 1：基本案卷生成

```python
from pathlib import Path
from src.config.config_manager import get_config_manager
from src.core.folder_generator import FolderGenerator
from src.core.template_engine import TemplateEngine

# 获取配置
config = get_config_manager()
template = config.get_template("civil_001")

# 准备变量值
values = {
    "case_name": "张三诉李四",
    "client_name": "张三",
    "case_type": "民事诉讼",
    "date": "2024-01-15"
}

# 生成文件夹结构
generator = FolderGenerator()
output_dir = Path(config.get("generation.default_output_dir", "~/案卷")).expanduser()
root_path = generator.generate(template["structure"], values, output_dir)

# 处理 Word 模板
engine = TemplateEngine()
template_file = Path("templates/委托合同.docx")
output_file = root_path / "委托合同.docx"
engine.process_template(template_file, output_file, values)

print(f"案卷已生成: {root_path}")
```

### 示例 2：批量生成

```python
from src.core.batch_processor import BatchProcessor

# 批量数据
cases = [
    {"case_name": "案件A", "client_name": "客户A"},
    {"case_name": "案件B", "client_name": "客户B"},
    {"case_name": "案件C", "client_name": "客户C"},
]

processor = BatchProcessor()

def on_progress(current, total, case_name):
    print(f"处理中 [{current}/{total}]: {case_name}")

processor.set_progress_callback(on_progress)
results = processor.process_batch(template, cases, output_dir)

for result in results:
    if result["success"]:
        print(f"成功: {result['path']}")
    else:
        print(f"失败: {result['error']}")
```
