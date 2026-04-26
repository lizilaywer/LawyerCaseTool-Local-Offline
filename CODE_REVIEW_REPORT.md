# 代码审查报告

**项目**: 律师案卷自动化生成工具 v1.5.0
**审查日期**: 2026-04-12
**审查范围**: 全量源码 (src/, tests/, scripts/)

---

## 一、总体评估

| 维度 | 评分 (1-5) | 说明 |
|------|-----------|------|
| 代码结构与组织 | 4.0 | 模块划分清晰，职责明确，层次合理 |
| 编码规范 | 3.5 | 基本遵循 PEP 8，存在部分硬编码和不一致 |
| 安全性 | 3.5 | 配置文件权限管控到位，存在少量注入风险 |
| 性能 | 3.5 | 整体可接受，存在若干性能隐患 |
| 错误处理 | 4.0 | 异常层次完整，原子写入到位，少量吞异常 |
| 测试覆盖 | 3.0 | 核心模块有测试，GUI/集成测试仍不足 |
| 依赖管理 | 3.5 | 分层合理，但版本锁定不够严格 |

**综合评价**: 代码质量总体良好，架构设计合理，单例模式和原子写入等关键机制实现正确。主要改进方向集中在硬编码消除、线程安全加固、性能优化和测试覆盖扩展。

---

## 二、问题清单

### Critical (严重 - 必须修复)

#### C-01: OcrWorker 线程中直接操作 GUI 剪贴板
- **文件**: `src/gui/widgets/ocr_worker.py:196-204`
- **问题**: `_copy_to_clipboard()` 在 QThread 子线程中调用 `QApplication.clipboard()`，Qt 的剪贴板操作**必须在主线程执行**，否则会导致未定义行为或崩溃。
- **建议**: 通过信号将文本传回主线程，在主线程中执行剪贴板写入。

#### C-02: OcrWorker 行分组算法 O(n^2) 且与排序方法重复
- **文件**: `src/gui/widgets/ocr_worker.py:90-135` 和 `:137-193`
- **问题**: `_sort_by_reading_order()` 和 `_merge_text()` 包含几乎完全相同的行分组逻辑，且内层循环对每个文本块遍历所有已有行，时间复杂度 O(n^2)。当文本块数量多时会严重影响性能。
- **建议**: 抽取为单一方法，使用更高效的分组算法（如先按 y 坐标排序再合并邻近行）。

#### C-03: main.py 命令行参数未验证
- **文件**: `src/main.py:53-61`
- **问题**: `--directory` 参数直接传递给配置管理器，未做路径有效性验证。恶意或错误输入（如 `--directory "../../../../etc"`）可能导致路径遍历问题。
- **建议**: 对 `--directory` 参数执行路径规范化和有效性检查（如 `Path.resolve()` 后验证是否在预期范围内）。

### High (高 - 应尽快修复)

#### H-01: 大量硬编码的颜色值和 UI 尺寸
- **文件**: `src/gui/widgets/case_card.py:22-29`, `src/gui/widgets/archive_preview.py:285-329` 等
- **问题**: 部分控件直接硬编码颜色（如 `#f59e0b`, `#10b981`, `#8b5cf6`），而非引用 `styles.py` 中的 `APP_COLORS`。这破坏了统一配色方案，后续主题切换时容易遗漏。
- **涉及**: `case_card.py:25-29` 的 `CATEGORY_STYLE` 中 6 个颜色值、`archive_preview.py` 多处硬编码样式。
- **建议**: 将所有颜色值统一到 `styles.py` 的 `APP_COLORS` 字典中。

#### H-02: CaseManager 单例重置模式不安全
- **文件**: `tests/test_case_manager.py:18,30` 等多处，以及 `tests/test_case_detail_panel.py:43,49`
- **问题**: 测试中通过 `CaseManager._instance = None` 重置单例，这是一种侵入式操作。生产代码中如果意外重置 `_instance`，会导致数据丢失。且测试间如果清理不完全，会产生状态泄漏。
- **建议**: 为单例类添加 `_reset()` 类方法用于测试，或使用依赖注入/工厂模式在测试中隔离实例。

#### H-03: CaseManager.get_all_cases() 每次调用都遍历并刷新所有案件状态
- **文件**: `src/core/case_manager.py:662-675`
- **问题**: `get_all_cases()` 对每个案件调用 `_refresh_case_runtime_state()`，该方法会检查目录存在性和读取笔记文件。当案件数量较多时，每次列表刷新都触发大量 I/O 操作。
- **建议**: 增加缓存机制或定期刷新策略，避免每次获取列表都执行全量 I/O。

#### H-04: CaseManager.search_cases() 通过 JSON 序列化搜索变量值
- **文件**: `src/core/case_manager.py:693-714`
- **问题**: 搜索时用 `json.dumps()` 将整个 `variables` 和 `info_fields` 字典序列化为字符串再进行子串匹配，效率低且可能产生误匹配（如搜索关键字恰好在 JSON 键名中）。
- **建议**: 遍历变量值进行直接比较，或维护一个独立的搜索索引。

#### H-05: ArchivePreview 在 resizeEvent 中频繁触发渲染
- **文件**: `src/gui/widgets/archive_preview.py:380-382`
- **问题**: 每次窗口大小变化都调用 `_schedule_visual_refresh()`，虽然使用了 `QTimer.singleShot(0, ...)`，但在持续拖拽调整窗口大小时会积压大量待执行的渲染请求。
- **建议**: 使用 debounce 机制（如 100ms 延时器），确保只在调整结束后触发一次渲染。

#### H-06: 依赖版本未锁定上限
- **文件**: `requirements-core.txt`, `requirements-ocr.txt`
- **问题**: 所有依赖使用 `>=` 下限约束（如 `PySide6>=6.4.0`），未设置兼容性上限。PySide6 主版本升级（如 7.x）可能引入破坏性变更。
- **建议**: 对关键依赖（PySide6, python-docx, docxtpl）使用兼容性约束，如 `PySide6>=6.4.0,<7.0.0`。

### Medium (中等 - 计划修复)

#### M-01: ScreenshotTool 未在 paintEvent 中配对 QPainter begin/end
- **文件**: `src/gui/widgets/screenshot_tool.py:122-125`
- **问题**: `paintEvent()` 中创建 `QPainter(self)` 但没有显式调用 `painter.end()`。虽然 Qt 在析构时会自动结束，但显式配对是更好的实践。
- **建议**: 使用 `with QPainter(self) as painter:` 上下文管理器或显式调用 `end()`。

#### M-02: registry_manager.py 中注册表操作未用上下文管理器
- **文件**: `src/integration/registry_manager.py:51-68`
- **问题**: `winreg.CreateKey()` 返回的 key 手动调用 `CloseKey()`，如果中间操作抛出异常，key 可能不会被正确关闭。
- **建议**: 使用 `with winreg.CreateKey(...) as key:` 上下文管理器。

#### M-03: ConfigManager.reset_config() 使用浅拷贝
- **文件**: `src/config/config_manager.py:399-404`
- **问题**: `DEFAULT_APP_CONFIG.copy()` 是浅拷贝，如果默认配置中包含嵌套字典，修改重置后的配置可能污染默认值。
- **建议**: 使用 `copy.deepcopy()`（与 `reset_templates()` 保持一致）。

#### M-04: ConfigManager._save_config() 捕获过于宽泛的异常
- **文件**: `src/config/config_manager.py:268-281`
- **问题**: `_save_config()` 中 `except Exception` 捕获了所有异常，包括 `safe_write_json` 可能抛出的 `IOError`，但只是记录日志返回 False，没有通知用户。
- **建议**: 让关键错误向上传播或在日志中标记为需要用户注意的错误。

#### M-05: 测试中直接操作私有属性
- **文件**: `tests/test_case_manager.py:19-21`, `tests/test_case_manager_dialog.py:30-33`
- **问题**: 测试中直接设置 `self.manager._cases_file`, `_cases`, `_common_tags` 等私有属性。如果内部实现变更，测试会大规模失效。
- **建议**: 通过公开 API 或专门的测试辅助方法来设置测试状态。

#### M-06: ~~ocr_worker.py 中 `import re` 但 regex 功能可简化~~
- **状态**: 已在 C-02 修复中一并解决（合并为单个预编译正则 `_CLEANUP_SPACES`）

#### M-07: case_manager.py 中 `_normalize_case_record` 每次调用 `datetime.now().isoformat()`
- **文件**: `src/core/case_manager.py:319`
- **问题**: 规范化记录时调用 `datetime.now()` 两次（created_at 和 updated_at 的默认值），且每次保存都更新 `updated_at`，频繁创建 ISO 字符串有轻微性能开销。
- **建议**: 将 `now` 作为参数传入或使用模块级缓存。

#### M-08: ArchivePreview 中硬编码字体名 "Microsoft YaHei"
- **文件**: `src/gui/widgets/archive_preview.py:693,746`
- **问题**: 直接硬编码 Windows 字体名，在 macOS/Linux 上不存在该字体，会导致回退到系统默认字体，体验不一致。项目已有 `get_default_ui_font_family()` 和 `get_default_monospace_font_family()` 工具函数。
- **建议**: 使用已有的平台字体工具函数。

#### M-09: 测试覆盖不完整 - 缺少关键模块的测试
- **涉及模块**:
  - `src/core/variable_parser.py` - 无独立测试文件
  - `src/core/batch_processor.py` - 无测试文件
  - `src/core/word_editor.py` - 测试文件存在但需验证
  - `src/gui/template_maker.py` - 无测试
  - `src/gui/settings_dialog.py` - 无测试
  - `src/gui/main_window.py` - 无测试
  - `src/utils/file_utils.py` - 无测试
  - `src/utils/migration.py` - 无测试
  - `src/integration/` - 无测试
- **建议**: 优先为 `variable_parser`, `batch_processor`, `migration` 添加单元测试。

#### M-10: 根目录存在测试脚本污染
- **文件**: `test_word_template.py`, `test_template_fixes.py`, `test_fixes_part2.py`
- **问题**: 根目录下存在 3 个临时测试脚本，不属于正式测试套件，且有硬编码路径和临时调试代码。
- **建议**: 将有效的测试用例迁移到 `tests/` 目录，删除临时脚本。

### Low (低 - 可选优化)

#### L-01: 部分测试方法缺少 docstring
- **文件**: `tests/test_config_manager.py` 中的方法有 docstring，但其他测试文件中的方法部分缺失
- **建议**: 保持一致的测试文档风格。

#### L-02: 测试中 `_get_app()` 模式重复
- **文件**: 几乎所有 GUI 测试文件 (test_calendar_dialog.py, test_case_card.py, test_case_detail_panel.py 等)
- **问题**: 每个测试文件都定义了自己的 `_get_app()` 辅助函数，代码重复。
- **建议**: 提取为 `tests/conftest.py` 中的 pytest fixture。

#### L-03: ArchivePreview._create_pdf_toolbar() 方法过长 (126行)
- **文件**: `src/gui/widgets/archive_preview.py:206-331`
- **建议**: 考虑将工具栏按钮创建拆分为更小的辅助方法。

#### L-04: case_manager.py 文件超过 1200 行
- **文件**: `src/core/case_manager.py`
- **问题**: 单个文件承担了案件 CRUD、期限管理、笔记管理、导入导出、搜索等所有职责。
- **建议**: 考虑将期限管理、导入导出、搜索等功能拆分为独立模块。

#### L-05: 异常模块中重复定义 message 属性
- **文件**: `src/utils/exceptions.py`
- **问题**: 所有自定义异常类都定义了 `self.message` 属性，但 Python 3 的 `Exception` 已经内置了 `args` 属性存储消息。
- **建议**: 简化为只调用 `super().__init__(message)`，不额外存储 `self.message`。

#### L-06: `backups/` 目录包含在项目中
- **文件**: `backups/ui_20260315_115032/`, `backups/v1.0.1_fix_2026-02-25/`
- **问题**: 备份文件应该由版本控制系统管理，不应包含在项目目录中。
- **建议**: 将 `backups/` 加入 `.gitignore`，或迁移到单独的归档位置。

#### L-07: `src/main.py` 中 `sys.path.insert(0, ...)` 脆弱
- **文件**: `src/main.py:8-9`
- **问题**: 手动修改 `sys.path` 是一种脆弱的包导入方式，依赖于脚本执行路径。
- **建议**: 使用 `pyproject.toml` 的 `[project.scripts]` 或设置 `PYTHONPATH` 环境变量。

---

## 三、架构优点

1. **分层清晰**: `core/` (业务) → `gui/` (界面) → `config/` (配置) → `utils/` (工具) 四层分离，依赖方向正确
2. **单例模式一致**: `Application`, `ConfigManager`, `PathManager`, `CaseManager` 均使用双重检查锁定
3. **原子写入**: `safe_write_json()` 使用临时文件+原子替换，防止配置损坏
4. **数据规范化**: `CaseManager` 中的 `_normalize_*` 系列函数确保数据一致性
5. **Sidecar 模式**: 案件数据同时存在中央索引和目录侧边文件中，支持目录迁移后重关联
6. **依赖分层**: `requirements-core.txt` / `requirements-ocr.txt` / `requirements-full.txt` 三层分离
7. **异常层次完整**: `exceptions.py` 按模块定义异常继承链
8. **配置文件权限**: `_save_config()` 中设置了 `chmod 0o600` 保护

---

## 四、修复优先级建议

| 优先级 | 问题编号 | 预估工作量 | 状态 |
|--------|---------|-----------|------|
| P0 (立即) | C-01, C-02 | 2-3 小时 | **已修复** |
| P1 (本周) | C-03, H-03, H-05 | 2-4 小时 | **已修复** |
| P2 (下次迭代) | H-01, H-02, H-06 | 3-5 小时 | **已修复** |
| P3 (季度内) | M-01 ~ M-10 | 1-2 天 | **已修复** (M-06 随 C-02 修复, M-07 经评估无需修改) |
| P4 (有空时) | L-01 ~ L-07 | 0.5 天 | L-02, L-05, L-06 **已修复**; L-01, L-03, L-04, L-07 保留 |

---

## 五、总结

项目整体代码质量良好，架构设计成熟，关键机制（单例安全、原子写入、数据规范化）实现到位。需要重点关注：

1. **线程安全**: OcrWorker 在工作线程中操作 GUI 对象是最紧迫的问题
2. **性能优化**: CaseManager 的全量刷新策略需要改进
3. **代码重复**: OCR 工作线程中的行分组算法、测试辅助函数需要去重
4. **测试扩展**: 核心模块（variable_parser, batch_processor, migration）缺少测试
5. **硬编码消除**: 颜色值和字体名需要统一管理

按上述优先级修复后，项目代码质量可提升至优秀水平。
