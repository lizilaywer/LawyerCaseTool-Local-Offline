# LawyerCaseTool 工程审查 + 事故响应综合报告

**日期**：2026-05-16
**工作流**：工作流 3（事故响应）+ 工作流 1（代码审查）+ 工作流 5（技术债评估）
**参与成员**：Cody（代码审查师）/ Archi（架构师）/ Rex（SRE 工程师）/ Tessa（测试专家）/ Docu（技术文档师）

---

## 📌 TL;DR（执行摘要）

- **事故**：git filter-repo 操作因文件名拼写错误导致 2 个核心模板文件（民事起诉状.docx、民事答辩状.docx）被永久删除，SEV3 评级，数据不可恢复，需重建模板
- **代码审查**：发现 27 项问题——🔴严重 2 项 / 🟠高 5 项 / 🟡中 12 项 / 🟢低 8 项，2 处严重问题（取消信号丢失、竞态条件）阻塞上线
- **架构评估**：总体 B+，核心风险为 MainWindow 上帝对象（2419 行）和 GUI↔Core 紧耦合（45 处直接 import）
- **文档健康度**：2.4/5，版本号四散不同步，架构文档和 API 文档严重滞后
- 严重度分布：🔴严重 X+2 项 / 🟠高 X+5 项 / 🟡中 X+12 项 / 🟢低 X+8 项
- 阻塞项：2 处代码严重问题 + 2 个模板文件缺失

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🟡 有条件通过 |
| 阻塞项数量 | 4（2 代码严重 + 2 模板缺失） |
| 关键行动项 | 10 条 |
| 建议下一步 | 修复 S-1/S-2 代码问题 → 重建模板 → 启用 Branch Protection → 统一版本号 |

---

## 🔥 事故响应（INC-2026-001）

### 事故摘要

2026-05-16，项目所有者执行 `git filter-repo` 清除两个 Word 模板文件的 Git 历史时，因命令行拼写错误（"民事"→"民 事"，多一空格），导致 `民事起诉状.docx` 和 `民事答辩状.docx` 从 Git 历史、本地磁盘和 GitHub 远端被永久删除，且无法恢复。

### SEV 评级：SEV3

- 非线上服务中断，应用本身仍在运行
- 两个核心业务模板永久删除（不可逆数据丢失）
- 模板文件可重新制作，降低严重度

### 事故时间线

| 时间 | 事件 |
|------|------|
| T0 | 需求产生：替换 GitHub 上有错误的 2 个模板文件，要求清除历史 |
| T1 | 选择 `git filter-repo --invert-paths` 方案 |
| T2 | 执行命令（含拼写错误："民 事起诉状"）+ `--force` 跳过安全确认 |
| T3 | filter-repo 执行"成功"（静默执行不匹配路径，未报错） |
| T4 | 工作目录被刷新，两个文件从本地消失 |
| T5 | 发现文件丢失，尝试 `git add` 失败 |
| T6 | 放弃恢复，直接在 GitHub 网页删除文件 |
| T7 | 当前状态：两个文件从全部历史/本地/远端完全消失 |

### 5 Why 根因分析

1. **Why 文件被永久删除？** → filter-repo 重写历史并擦除 reflog
2. **Why 结果与预期不符？** → 文件名拼写错误（"民 事"），路径不匹配但 filter-repo 静默执行
3. **Why 拼写错误未发现？** → 无 dry-run 预检 + `--force` 跳过安全确认
4. **Why 执行前无备份？** → 对 filter-repo 破坏性认知不足
5. **Why 恢复失败？** → reflog 被擦除 + 无外部备份 + 慌乱中做出不可逆决策

**根本原因**：命令行拼写错误 + 静默成功 + `--force` 跳过安全网 + 无备份 + 无恢复策略

### 经验教训（5 条）

1. **静默成功是最危险的失败模式** — filter-repo 不验证路径存在性，拼写错误被吞掉
2. **`--force` 是"跳过安全网"而非"确认执行"**
3. **中文文件名是命令行操作的高风险点** — 输入法切换产生不可见空格
4. **filter-repo 擦除 reflog** — 安全网不存在，必须先手动备份 `.git`
5. **恢复决策应有预定义策略** — "先备份再操作"应是肌肉记忆

---

## 🔍 代码审查发现（按严重度排序）

### 🔴 严重

| # | 类别 | 文件:行 | 问题描述 | 建议修复 | 来源 |
|---|------|---------|---------|---------|------|
| S-1 | 安全 | `batch_processor.py:195-196` | BatchProcessor 线程池中 FolderGenerator 的 `_cancel_checker` 未设置，取消操作不会传播到 worker 线程，文件生成过程中的取消检查形同虚设 | `folder_generator.set_cancel_checker(self.is_cancelled)` | Cody |
| S-2 | 正确性 | `case_manager.py:320-324` | CaseManager 单例 `__new__` 锁与 `__init__` 锁不一致，可能导致 `_load()` 并发调用，数据丢失或损坏 | 统一在 `__new__` 中完成初始化，或使用模块级 `get_case_manager()` 的 DCL 模式 | Cody |

### 🟠 高

| # | 类别 | 文件:行 | 问题描述 | 建议修复 | 来源 |
|---|------|---------|---------|---------|------|
| H-1 | 性能 | `case_manager.py:456-457` | `_update_case_index` 中 `list.remove()` + `list.insert(0)` 是 O(n) | 改用 `OrderedDict` 或 `SortedDict` | Cody |
| H-2 | 性能 | `case_manager.py:556-593` | `_refresh_case_runtime_state` 在主线程执行磁盘 I/O，案件多时阻塞 UI | 放入 `QThreadPool` 或后台线程 | Cody |
| H-3 | 安全 | `court_sms_service.py:435-436` | HTTP 请求未验证 SSL 证书，敏感参数可能泄露 | 设置 `verify=True` | Cody |
| H-4 | 安全 | `court_sms_service.py:514-521` | 下载文件未限制大小，恶意服务器可耗尽磁盘 | 添加 `MAX_DOWNLOAD_SIZE` 限制 | Cody |
| H-5 | 正确性 | `template_engine.py:8` | `import io` 重复导入 | 删除方法内的重复 import | Cody |

### 🟡 中（12 项，摘要）

| # | 类别 | 文件 | 问题 | 来源 |
|---|------|------|------|------|
| M-1 | 性能 | template_engine.py | 模板缓存无上限，无 LRU 淘汰 | Cody |
| M-2 | 正确性 | variable_parser.py | `extract_variables` 返回顺序不确定（`list(set(...))`） | Cody |
| M-3 | 性能 | file_utils.py | `list_files` 一次性加载所有文件到内存 | Cody |
| M-4 | 安全 | template_path_manager.py | 路径遍历检测混用字符串操作和 Path.resolve() | Cody |
| M-5 | 可维护性 | case_manager.py | 文件超 1900 行，职责过多，违反 SRP | Cody |
| M-6 | 正确性 | config_manager.py | 单例 `__init__` 竞态条件（同 S-2 模式） | Cody |
| M-7 | 性能 | case_manager.py | `update_case` 每次都执行 `deepcopy`，GC 压力大 | Cody |
| M-8 | 正确性 | court_sms_service.py | `_ocr_pdf_pages` 中 `fitz.open()` 异常时文档句柄不关闭 | Cody |
| M-9 | 可维护性 | validators.py | `sanitize_filename` 正则混合中文引号，每次重编译 | Cody |
| M-10 | 性能 | batch_processor.py | `max_workers` 默认过高（8），I/O 争用反降性能 | Cody |
| M-11 | 正确性 | migration.py | 浅拷贝导致原始数据可能被意外修改 | Cody |
| M-12 | 可维护性 | template_engine.py | 方法内局部 `import re`，违反 PEP 8 | Cody |

### 🟢 低（8 项，摘要）

| # | 问题 | 来源 |
|---|------|------|
| L-1 | 异常类未用 `__slots__` 存储结构化字段 | Cody |
| L-2 | Word 编辑器撤销操作需重放完整历史 | Cody |
| L-3 | `mkdir(parents=True)` 未设置权限 | Cody |
| L-4 | `subprocess.Popen` 未等待子进程 | Cody |
| L-5 | `safe_write_json` 与 `file_utils.write_json_file` 代码重复 | Cody |
| L-6 | `get_case_manager()` 文档字符串复制粘贴错误 | Cody |
| L-7 | `_rebuild_sorted_ids` 每次全量排序 | Cody |
| L-8 | docx_auto_format.py 依赖 python-docx 内部 XML API | Cody |

### 代码亮点

- ✅ 路径遍历防护（`TemplatePathManager` 多层安全检查）
- ✅ 原子写入（`safe_write_json` 临时文件 + `shutil.move`）
- ✅ 单例线程安全（双重检查锁定）
- ✅ 配置文件损坏恢复（`_backup_corrupt_file`）
- ✅ 删除操作安全防护（符号链接/根目录/metadata 一致性检查）
- ✅ 文件名校验（Windows 保留名/非法字符/控制字符）
- ✅ 取消机制（`threading.Event`）
- ✅ 缓存机制（TTL + mtime + 锁保护）

---

## 🏗️ 架构评估

### 总体评分：B+

项目分层方向正确（utils → config → core → gui），但存在 GUI↔Core 紧耦合和 MainWindow 上帝对象问题。

### 关键 ADR

| ADR | 决策 | 评估 |
|-----|------|------|
| ADR-001 | 单例模式（DCL） | ✅ 合理，但缺测试重置机制 |
| ADR-002 | JSON 文件存储配置 | ✅ 合理，原子写入质量高 |
| ADR-003 | 双通道模板引擎（正则+Jinja2） | ✅ 非常合理，占位符保留策略体现行业理解 |
| ADR-004 | 模块分层 | ⚠️ 方向正确，但 45 处 GUI→Core 直接 import |
| ADR-005 | OCR 可选依赖 | ✅ 降级体验好，但 GUI 直接依赖 OCR 内部类 |
| ADR-006 | PyInstaller --onefile | ✅ 务实选择，启动速度可优化 |

### 核心风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| R1: MainWindow 上帝对象（2419 行） | 🔴 | 任何修改高概率引入回归 |
| R2: GUI↔Core 紧耦合 | 🔴 | 45 处直接 import，无法独立测试 |
| R3: 单例无重置机制 | 🟡 | 测试隔离困难 |
| R4: 配置层职责溢出 | 🟡 | `safe_write_json` 被业务层复用 |
| R5: TemplatePathManager 单例风格不一致 | 🟡 | 两种单例实现并存 |

### 改进建议

| 优先级 | 建议 | 风险 |
|--------|------|------|
| P0 | 拆分 MainWindow（App Shell + Mixin/MVP） | 中 |
| P0 | 为单例添加 `_reset()` 方法 | 极低 |
| P1 | 引入 Service Locator / DI | 中 |
| P1 | 将 `safe_write_json` 提升为 utils 层工具 | 极低 |
| P1 | 统一 TemplatePathManager 单例实现 | 极低 |
| P2 | 配置 Schema 验证（dataclass/pydantic） | 低 |
| P2 | 评估 --onedir 打包模式 | 低 |
| P2 | 默认模板外部化（JSON/YAML） | 低 |

---

## 📝 文档债评估

### 文档健康度：2.4/5（中等偏下）

### 严重问题（P0）

| # | 问题 | 影响 |
|---|------|------|
| 1 | 版本号四散不同步（VERSION=2.1.0, README=2.0.0, PROJECT_RESUME=1.2.0） | 开发者/AI 无法确认真实版本 |
| 2 | CHANGELOG.md 缺 v2.1.0 条目 | 版本记录断裂 |
| 3 | PROJECT_RESUME.md 严重过时（v1.2.0） | AI 上下文恢复可能用错误信息 |

### 高优先级（P1）

| # | 问题 | 影响 |
|---|------|------|
| 4 | API 文档仅覆盖 4/29+ 核心模块 | 新开发者无法了解公共接口 |
| 5 | 架构文档严重过时（v1.0~v1.1 时代） | 无法理解系统全貌 |
| 6 | 缺少终端用户手册 | 法律从业者无自助参考 |
| 7 | 缺少贡献指南 | 外部参与门槛高 |

### 建议结构重组

- 根目录仅保留 5 个核心文档（README/CHANGELOG/AGENTS/CLAUDE/PROJECT_RESUME）
- 特性文档移入 `docs/features/`，审查报告移入 `docs/reviews/`
- 新增 `docs/README.md` 作为文档导航中心

---

## 🧪 测试覆盖评估

> 注：测试专家 Tessa 的详细产出因消息传递延迟未完整接收。基于代码审查中 Cody 对测试文件的扫描，以下为已知状况：

- 测试文件：35 个（位于 `tests/`）
- 测试框架：pytest
- 关键风险模块无测试覆盖：`court_sms_service.py`（1121 行）、`calendar_exporter.py`（2084 行）、`docx_auto_format.py`（923 行）
- 单例模式导致测试隔离困难（无 `_reset()` 方法）
- 无 CI/CD 管道配置（缺少 `.github/workflows/`）

---

## ✅ 行动清单（按优先级排序）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 1 | **修复 S-1**：BatchProcessor 取消信号丢失 — 设置 `folder_generator.set_cancel_checker(self.is_cancelled)` | 开发者 | P0 | 本周 |
| 2 | **修复 S-2**：CaseManager 单例竞态条件 — 统一 `__new__` 中的初始化逻辑 | 开发者 | P0 | 本周 |
| 3 | **重建民事起诉状.docx 模板** | 项目所有者 | P0 | 本周 |
| 4 | **重建民事答辩状.docx 模板** | 项目所有者 | P0 | 本周 |
| 5 | **启用 GitHub Branch Protection**（禁止 force push） | 项目所有者 | P1 | 1 周内 |
| 6 | **统一版本号**（README/CLAUDE/PROJECT_STATUS → 2.1.0） | 开发者 | P1 | 本周 |
| 7 | **补充 CHANGELOG.md v2.1.0 条目** | 开发者 | P1 | 本周 |
| 8 | **修复 H-3**：court_sms_service.py SSL 证书验证 | 开发者 | P1 | 2 周内 |
| 9 | **修复 H-4**：court_sms_service.py 下载文件大小限制 | 开发者 | P1 | 2 周内 |
| 10 | **重写 docs/ARCHITECTURE.md**（反映当前架构） | 开发者 | P1 | 2 周内 |

---

## ⚠️ 待完善 / 已知局限

- 测试专家 Tessa 的完整测试覆盖报告因消息传递延迟未完整接收，测试章节基于有限信息编写，建议后续补充完整测试覆盖评估
- 架构评估中的改进建议（拆分 MainWindow、引入 DI）需要单独的实施计划，未包含在本报告的行动项中
- 文档债评估中的建议结构重组需要较大工作量，建议分批执行
- 事故复盘文档已独立保存至 `docs/INCIDENT_POSTMORTEM_2026-05-16.md`

---

## 📚 数据来源 & 成员产出索引

- **Cody（代码审查师）**原始产出：27 项发现（2 严重 / 5 高 / 12 中 / 8 低），含代码定位和修复建议
- **Archi（架构师）**原始产出：6 个 ADR + 5 个风险 + 8 条改进建议 + 架构图
- **Rex（SRE 工程师）**原始产出：事故分诊报告（SEV3）+ 事故复盘文档（`docs/INCIDENT_POSTMORTEM_2026-05-16.md`，含时间线/5Why/行动项/经验教训）
- **Tessa（测试专家）**原始产出：部分接收，测试文件盘点和关键风险模块识别
- **Docu（技术文档师）**原始产出：文档健康度 2.4/5 + 16 项文档债务 + 结构重组建议

---

> 本报告由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。
