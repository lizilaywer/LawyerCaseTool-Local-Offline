# 全面代码审查报告

**项目**: 案件文件夹管理系统 v2.0.0
**审查日期**: 2026-04-26
**审查范围**: 80+ 源文件, 30 测试文件, 全部依赖配置

---

## 一、总体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 项目结构 | B+ | 模块划分清晰，但存在God类 |
| 代码质量 | B- | 整体规范，但有重复代码和封装破坏 |
| 安全性 | B | 基础防护到位，但存在若干漏洞 |
| 性能 | B- | 大部分场景可用，多处主线程阻塞 |
| 测试覆盖 | C+ | 核心模块覆盖较好，大量模块零测试 |
| 可维护性 | C+ | 高耦合、单例滥用、代码重复严重 |

**发现问题总计**: 4 Critical / 19 High / 38 Medium / 29 Low

---

## 二、Critical 级别问题 (必须立即修复)

### C1. CaseManager 单例初始化竞态条件
**文件**: `src/core/case_manager.py:256-259`, `src/app.py:40-42`
`__init__` 中 `self._initialized` 的检查和设置不在锁保护范围内，多线程可能同时通过检查导致重复初始化。

### C2. CaseManager 读取方法缺乏线程安全
**文件**: `src/core/case_manager.py` 多处方法
`get_case()`(847)、`search_cases()`(914)、`get_all_cases()`(862) 等读取 `self._cases` 时未获取锁，与后台写入线程并发时可能读到不一致状态。

### C3. ArchiveEngine 非原子 JSON 写入
**文件**: `src/core/archive_engine.py:121-134`
使用 `open(..., 'w')` 直接写入 `history.json`，崩溃时数据丢失。项目已有 `safe_write_json` 但此处未使用。

### C4. GUI猴子补丁破坏封装
**文件**: `src/gui/info_extraction_dialog.py:762-771`
在模块外部为 `ImageListWidget` 类动态挂载方法，重构时极易崩溃：
```python
def _set_current_item_by_path(self, path: str):
    ...
ImageListWidget.setCurrentItemByPath = _set_current_item_by_path
```

---

## 三、High 级别问题 (应尽快修复)

### H1. `_select_case` 方法未定义 — 运行时崩溃
**文件**: `src/gui/case_manager_dialog.py:1572, 1765`
调用 `self._select_case()` 但类中仅定义了 `_select_single_case`，将触发 `AttributeError`。

### H2. 备份/导入操作阻塞主线程
**文件**: `src/gui/settings_dialog.py:452-479, 528-549`
`BackupService().create_backup()` 和 `import_backup()` 在主线程同步执行，可能冻结 GUI 数十秒。

### H3. 案件搜索无防抖，每次击键全量重载
**文件**: `src/gui/case_manager_dialog.py:1451-1453`
搜索输入无防抖，每次击键触发 `_load_cases()` 重建整个卡片列表，数百案件时严重卡顿。

### H4. CaseManager 删除操作回滚不完整
**文件**: `src/core/case_manager.py:764-781`
`remove_case` 先持久化删除再执行 `rmtree`，若 `rmtree` 失败则数据不一致；回滚 `save()` 若再失败则案件丢失。

### H5. `is_pdf` 缺少 `@staticmethod` 装饰器
**文件**: `src/utils/pdf_utils.py:231`
定义为实例方法但无 `self` 参数，以实例调用时将崩溃。

### H6. `write_text_file` 非原子写入
**文件**: `src/utils/file_utils.py:181-203`
直接写入目标文件，未使用与 `write_json_file` 相同的原子写入模式，用于 `notes.md` 等关键文件时有数据丢失风险。

### H7. 版本号三处不一致
**文件**: `pyproject.toml:8` (1.6.1) vs `src/utils/version.py:33` (2.0.0) vs `CLAUDE.md` (v2.0.0)

### H8. Python 版本要求与 PySide6 不兼容
**文件**: `pyproject.toml` 声明 `requires-python = ">=3.8"`，但 `PySide6>=6.4.0` 在 6.5+ 需要 Python 3.9+，6.8+ 需要 3.10+。

### H9. BatchProcessor 取消检测使用字符串匹配
**文件**: `src/core/batch_processor.py:155, 253`
通过 `"取消" in str(e)` 检测取消操作，合法错误信息含此子串时误判。

### H10. CaseManager `rename_case` 未校验文件名安全性
**文件**: `src/core/case_manager.py:823-845`
`new_name` 未过滤文件系统非法字符 (`/\:*?"<>|`)，可能触发 OS 错误。

### H11. GenerationDialog Worker 线程无清理
**文件**: `src/gui/generation_dialog.py:28-71, 347-353`
Worker 线程未连接 `finished -> deleteLater`，`closeEvent` 中 `wait()` 无限阻塞。

### H12. InfoExtractionDialog 关闭时未停止 OCR Worker
**文件**: `src/gui/info_extraction_dialog.py`
未覆写 `closeEvent`，关闭对话框时 OCR 线程继续运行并向已销毁 Widget 发信号，可能崩溃。

---

## 四、Medium 级别问题 (计划修复)

| # | 类别 | 文件 | 问题描述 |
|---|------|------|----------|
| M1 | 性能 | `case_manager.py` 多处 | 过度使用 `deepcopy`，每次更新全量拷贝 |
| M2 | 性能 | `case_manager.py:391,742` | `_sorted_case_ids.remove()` 是 O(n) 操作 |
| M3 | 性能 | `case_manager.py:454-460` | 启动时对每个案件同步 `Path.exists()` 检测 |
| M4 | 性能 | `template_engine.py:29,77` | 模板缓存无大小限制，批量处理时内存膨胀 |
| M5 | 设计 | `main_window.py` | God 类 ~2414 行，职责过多 |
| M6 | 设计 | `case_manager_dialog.py:178,322` | `_extract_folder_paths` 两处完全重复 |
| M7 | 设计 | `template_maker.py:491,1776` | `_save_variable_to_template` 两处完全重复 |
| M8 | 设计 | 5个文件 | 分类名称映射五处重复定义 |
| M9 | 设计 | `config_manager.py:436-459` | `reset_config` 重复构建默认配置而非调用 `_get_default_config` |
| M10 | 设计 | `variable_parser.py` vs `archive_engine.py` | 变量提取逻辑两处重复实现 |
| M11 | 一致性 | `archive_engine.py:56-59` vs `template_engine.py` | 空值处理策略不一致（跳过 vs 保留占位符）|
| M12 | 安全 | `generation_dialog.py:220-228` | 用户可选任意目录作为输出路径，无安全校验 |
| M13 | 安全 | `pdf_utils.py:280` | 使用 PyMuPDF 内部 `_updateObject` API，版本更新时可能崩溃 |
| M14 | 安全 | `migration.py:36,151` | 浅拷贝导致嵌套结构与原始对象共享 |
| M15 | 依赖 | `pyproject.toml` | 缺少 `fpdf2` 依赖声明 |
| M16 | 依赖 | `requirements-core.txt:21` | `requests==2.32.5` 精确锁定阻碍安全更新 |
| M17 | 资源泄漏 | `pdf_utils.py` 多处 | PDF 文档句柄未用 context manager，异常时泄漏 |
| M18 | 代码质量 | `template_engine.py:8,112` | `import io` 重复 |
| M19 | 代码质量 | `template_engine.py:235` | `import re` 放在方法体内 |
| M20 | 内存 | `case_manager_dialog.py:1011-1020` | 空状态 QLabel 未清理，反复切换时累积 |
| M21 | 逻辑 | `word_editor.py:566-569` | `undo_variable` 仅匹配 `new_text`，反向替换时无法撤销 |
| M22 | 逻辑 | `word_editor.py:384-392` | 段落替换后未重算 match_positions |
| M23 | 配置 | `config_manager.py:72` | `shutil.move` 跨文件系统非原子 |
| M24 | 文档 | `case_manager.py:1780` | docstring 错误：写的"路径管理器"应为"案件管理器" |
| M25 | 样式 | `main_window.py:179-182` | 全局 `!important` 覆盖所有 QLabel 背景 |
| M26 | 安全 | `platform_utils.py:155-158` | `subprocess.Popen` 参数未验证 |
| M27 | 设计 | `info_extraction_dialog.py:676-684,751-754` | 3个功能按钮为 stub 但仍显示在 UI |
| M28 | 设计 | `archive_dialog.py:455-456` | `_variable_replacements` 用 `hasattr` 而非 `__init__` 初始化 |
| M29 | 集成 | `registry_manager.py:92-102` | 注册表删除失败时静默返回 `True` |

---

## 五、测试覆盖率评估

### 测试覆盖矩阵

```
模块                      测试数   覆盖度    说明
─────────────────────────────────────────────────────────
case_manager.py           19      +++      CRUD/搜索/期限/回滚
calendar_dialog.py        39      +++      最详尽的 GUI 测试
court_sms_service.py      10      +++      解析/下载/路径遍历防护
screenshot_pdf_merger.py  10      +++      排序/生成/错误处理
config_manager.py         10      +++      深拷贝/损坏恢复
folder_generator.py       10      ++       生成/变量/模板
case_detail_panel.py      12      ++       速记/自动保存/导出
legal_toolkit.py           5      ++       费用计算
case_aux_dialogs.py       16      ++       日期解析/智能输入
tool_center_dialog.py      7      ++       费用/SMS/开庭通知
template_engine.py         5      +        未测 generate_document
batch_processor.py         1      +        仅测试取消
variable_parser.py         0      -        无专门测试文件
archive_engine.py          0      -        整个归档流程零测试
validators.py              0      -        输入验证零测试
file_utils.py              0      -        文件工具零测试
generation_dialog.py       0      -        主工作流零测试
template_manager.py        0      -        模板管理零测试
settings_dialog.py         0      -        设置持久化零测试
OCR parsers (5个)          0      -        全部解析器零测试
path_manager.py            0      -        路径管理零测试
```

### 测试质量问题
1. **单例重置分散**: 6+ 个测试文件各自手动 `CaseManager._instance = None`，应使用 `conftest.py` 的 `autouse` fixture
2. **根目录测试脚本**: `test_word_template.py`、`test_template_fixes.py`、`test_fixes_part2.py` 不是 pytest 测试，用 `print()` 输出，应迁移或删除
3. **共享 fixture 缺失**: `conftest.py` 仅定义 1 个 `qapp` fixture，缺少临时目录、单例重置等公共 fixture
4. **午夜边界风险**: 4 个测试文件使用 `datetime.now()` 构造截止日期，午夜前后可能间歇失败

---

## 六、可维护性评估

### 主要架构问题

1. **God 类**: `main_window.py` (2414行)、`case_manager.py` (1782行)、`case_manager_dialog.py` (~1800行)、`court_sms_service.py` (868行) 职责过重

2. **单例滥用**: 5 个类使用单例模式 (`Application`, `ConfigManager`, `PathManager`, `CaseManager`, `TemplatePathManager`)，测试困难且实现不一致（两种不同的单例模式）

3. **层级穿透**: `main.py` 直接访问 `MainWindow` 的私有方法和属性（`_select_template`、`_pending_backup_import_dialog`）

4. **代码重复热区**:
   - 分类名称映射: 5 处重复
   - 变量提取逻辑: 2 处重复
   - `_extract_folder_paths`: 2 处重复
   - `_save_variable_to_template`: 2 处逐字重复

---

## 七、优先修复建议

### P0 — 立即修复（运行时崩溃/数据丢失风险）
1. 修复 `_select_case` AttributeError (`case_manager_dialog.py:1572`)
2. 为 `is_pdf` 添加 `@staticmethod` (`pdf_utils.py:231`)
3. CaseManager 单例初始化移入锁保护
4. ArchiveEngine 改用 `safe_write_json`
5. `write_text_file` 改为原子写入

### P1 — 尽快修复（用户体验/安全）
6. 案件搜索添加 200ms 防抖
7. 备份操作移至后台线程
8. InfoExtractionDialog 添加 `closeEvent` 清理 OCR Worker
9. GenerationDialog Worker 添加 `deleteLater` 连接
10. 统一版本号、修正 `requires-python`
11. 移除猴子补丁，将方法归入原类

### P2 — 计划修复（代码质量）
12. 提取共享分类名称常量到 `styles.py`
13. 提取共享 fixture 到 `conftest.py`
14. 为 `archive_engine`、`validators`、`file_utils` 补充测试
15. God 类拆分：`main_window.py` 抽取子模块
16. 迁移根目录测试脚本到 `tests/`
17. CaseManager 读方法添加锁保护或返回深拷贝
