# 律师案卷工具 - 代码审查报告

**审查日期**: 2026-03-13
**审查范围**: src/core/, src/gui/, src/config/, src/utils/
**当前版本**: v1.2.2

---

## 一、严重问题（必须修复）

### 1. 单例模式线程安全问题

**类比**：想象一个银行只有一个柜台，如果两个人同时去办业务，没有排队系统就会乱套。

**问题位置**：
- `src/config/path_manager.py` - PathManager 类
- `src/utils/logger.py` - LoggerManager 类

**现有代码问题**：
```python
# ❌ 没有线程安全保护
class PathManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:  # 多线程时可能同时进入
            cls._instance = super().__new__(cls)
        return cls._instance
```

**正确做法**：
```python
# ✅ 使用双重检查锁定
import threading

class PathManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
```

---

### 2. 批量处理器竞态条件

**类比**：两个人同时操作同一个开关，最后状态不可预测。

**问题位置**：`src/core/batch_processor.py`

```python
# ❌ 非线程安全的标志
class BatchProcessor:
    def __init__(self):
        self._cancelled = False  # 普通布尔值，非线程安全

    def cancel(self):
        self._cancelled = True  # 多线程访问可能出问题
```

**正确做法**：
```python
# ✅ 使用线程安全的事件
import threading

class BatchProcessor:
    def __init__(self):
        self._cancel_event = threading.Event()  # 线程安全

    def cancel(self):
        self._cancel_event.set()  # 安全设置

    def is_cancelled(self):
        return self._cancel_event.is_set()
```

---

### 3. 配置文件写入不安全

**类比**：在写一份重要文件，写到一半突然停电，文件损坏。

**问题位置**：`src/config/config_manager.py` 保存配置时

**现有问题**：
- 直接写入目标文件，如果中途崩溃，文件损坏
- 没有备份机制

**正确做法**：
```python
import tempfile
import shutil

def safe_write_json(path: Path, data: dict):
    """原子写入 - 要么全成功，要么全失败"""
    # 1. 先写入临时文件
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8',
        dir=path.parent, delete=False
    )

    try:
        json.dump(data, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()

        # 2. 原子替换（瞬间完成）
        shutil.move(temp_file.name, path)
    except Exception:
        # 3. 失败时清理临时文件
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise
```

---

## 二、性能问题

### 1. 模板引擎重复加载

**类比**：每次用字典查单词，都要先去书店买一本新字典。

**问题位置**：`src/core/template_engine.py`

```python
# ❌ 每次都重新加载模板
def render(self, template_path, variables):
    doc = DocxTemplate(template_path)  # 每次都从磁盘加载
    doc.render(variables)
    return doc
```

**正确做法**：
```python
# ✅ 添加模板缓存
class TemplateEngine:
    def __init__(self):
        self._cache = {}  # 模板缓存

    def render(self, template_path, variables):
        # 检查缓存
        if template_path not in self._cache:
            self._cache[template_path] = DocxTemplate(template_path)

        # 从缓存复制
        doc = self._cache[template_path]
        # 复制缓存的模板进行处理
        doc = self._cache[template_path]
        # ...
```

---

### 2. 变量列表频繁重建

**类比**：每次要找一个人，你都要把整个通讯录重新整理一遍。

**问题位置**：`src/gui/template_maker.py` - `_refresh_variable_list`

```python
# ❌ 每次搜索都删除重建所有控件
def _refresh_variable_list(self, filter_text):
    # 清空所有
    while self._layout.count():
        item = self._layout.takeAt(0)
        item.widget().deleteLater()

    # 重新创建所有
    for var in self._variables:
        if filter_text in var:
            self._create_variable_item(var)
```

**正确做法**：
```python
# ✅ 使用显示/隐藏，而不是重建
def _refresh_variable_list(self, filter_text):
    for i in range(self._layout.count()):
        item = self._layout.itemAt(i)
        widget = item.widget()

        # 根据过滤条件显示或隐藏
        if filter_text in widget.variable_name:
            widget.show()
        else:
            widget.hide()
```

---

### 3. OCR 批量处理串行执行

**类比**：一个厨师一道一道菜做，而不是同时开几个灶台。

**问题位置**：`src/gui/info_extraction_dialog.py`

```python
# ❌ 串行处理
for file_path in file_paths:
    result = self._ocr_engine.recognize(file_path)  # 一个一个处理
    results.append(result)
```

**正确做法**：
```python
# ✅ 并行处理
from concurrent.futures import ThreadPoolExecutor

def process_batch(self, file_paths):
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(
            self._ocr_engine.recognize,
            file_paths
        ))
    return results
```

---

## 三、安全问题

### 1. 路径遍历漏洞（已部分修复）

**类比**：你让客人去指定房间，但客人可能会偷偷溜进其他房间。

**问题**：用户输入的路径可能包含 `../` 跳出限制目录。

**现有保护**：`template_path_manager.py` 已经有检查，但不够全面。

**建议加强**：
```python
def validate_path(self, user_path: str, base_dir: Path) -> Path:
    """安全路径验证"""
    # 1. 规范化路径
    full_path = (base_dir / user_path).resolve()

    # 2. 检查是否在允许的目录内
    if not str(full_path).startswith(str(base_dir.resolve())):
        raise SecurityError("路径遍历攻击检测")

    # 3. 检查文件扩展名白名单
    allowed_extensions = {'.docx', '.doc', '.pdf', '.png', '.jpg'}
    if full_path.suffix.lower() not in allowed_extensions:
        raise SecurityError("不允许的文件类型")

    return full_path
```

---

### 2. 配置文件权限

**类比**：你的日记本放在公共区域，谁都能看。

**问题**：配置文件没有设置权限，可能被其他用户读取。

```python
# ✅ 创建配置文件时设置权限
import stat

def create_config_file(path: Path):
    path.touch()
    # 仅所有者可读写 (rw-------)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
```

---

## 四、代码质量问题

### 1. 异常处理过于宽泛

**类比**：不管什么病都开同样的药，不区分感冒还是骨折。

**问题位置**：多处使用 `except Exception`

```python
# ❌ 捕获所有异常
try:
    config = json.load(f)
except Exception:
    print("加载失败")  # 丢失了具体错误信息
```

**正确做法**：
```python
# ✅ 区分不同异常
try:
    config = json.load(f)
except json.JSONDecodeError as e:
    logger.error(f"配置文件格式错误: {e}")
    raise ConfigError("配置文件格式错误，请检查JSON格式")
except PermissionError:
    logger.error("无权限读取配置文件")
    raise ConfigError("无权限读取配置文件，请检查文件权限")
except FileNotFoundError:
    logger.error("配置文件不存在")
    raise ConfigError("配置文件不存在，将使用默认配置")
```

---

### 2. 资源清理不彻底

**类比**：用完的东西不收拾，房间越来越乱。

**问题位置**：`src/gui/widgets/variable_input.py`

```python
# ❌ 清理不彻底
def clear_inputs(self):
    for key, widget in self._inputs.items():
        widget.deleteLater()  # 只是标记删除
    self._inputs.clear()
```

**正确做法**：
```python
# ✅ 彻底清理
def clear_inputs(self):
    for key, widget in list(self._inputs.items()):
        # 断开信号连接
        try:
            widget.textChanged.disconnect()
        except:
            pass
        # 从布局移除
        self._layout.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()
    self._inputs.clear()
```

---

## 五、改进建议总结

### 高优先级（建议立即修复）

| 问题 | 位置 | 影响 |
|------|------|------|
| 单例线程安全 | path_manager.py, logger.py | 多线程崩溃 |
| 竞态条件 | batch_processor.py | 数据不一致 |
| 文件写入安全 | config_manager.py | 配置丢失 |

### 中优先级（下个版本修复）

| 问题 | 位置 | 影响 |
|------|------|------|
| 异常处理细化 | 多处 | 调试困难 |
| 模板缓存 | template_engine.py | 性能下降 |
| 资源清理 | variable_input.py | 内存泄漏 |

### 低优先级（有时间再优化）

| 问题 | 位置 | 影响 |
|------|------|------|
| 变量列表优化 | template_maker.py | 轻微卡顿 |
| OCR 并行处理 | info_extraction_dialog.py | 处理速度 |
| 配置文件权限 | config_manager.py | 安全隐患 |

---

## 六、修复进度追踪
### 高优先级
- [x] 修复 PathManager 单例线程安全 (2026-03-13)
- [x] 修复 LoggerManager 单例线程安全 (2026-03-13)
- [x] 修复 BatchProcessor 竞态条件 (2026-03-13)
- [x] 实现配置文件原子写入 (2026-03-13)
### 中优先级
- [x] 细化异常处理 (2026-03-13)
- [x] 添加模板缓存机制 (2026-03-13)
- [x] 完善资源清理 (2026-03-13)
### 低优先级
- [ ] 优化变量列表刷新 (待实施)
- [ ] OCR 并行处理 (待实施)
- [ ] 配置文件权限设置 (待实施)
### 修复文件清单
| 文件 | 修改内容 |
|------|----------|
| `src/config/path_manager.py` | 添加线程锁和双重检查锁定 |
| `src/utils/logger.py` | 添加线程锁和双重检查锁定 |
| `src/core/batch_processor.py` | 使用 `threading.Event` 替代布尔标志 |
| `src/config/config_manager.py` | 添加 `safe_write_json()` 埪子原子写入 |
| `src/core/template_engine.py` | 添加模板字节缓存机制 |
| `src/gui/widgets/variable_input.py` | 完善资源清理（断开信号、移除控件）|

---

*报告生成时间: 2026-03-13*
*审查工具: Claude Code*
