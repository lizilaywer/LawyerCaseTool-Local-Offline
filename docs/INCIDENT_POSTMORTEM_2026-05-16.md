# 事故复盘文档：git filter-repo 操作导致模板文件永久删除

| 字段 | 内容 |
|------|------|
| **事故编号** | INC-2026-001 |
| **事故标题** | git filter-repo 操作导致民事起诉状/答辩状模板文件永久删除 |
| **SEV 评级** | SEV3 |
| **事故状态** | 已关闭 — 数据不可恢复，待模板重建 |
| **复盘日期** | 2026-05-16 |
| **复盘人** | 雷克斯（Rex）· SRE 工程师 |
| **项目** | LawyerCaseTool-Local-Offline |
| **仓库** | https://github.com/lizilaywer/LawyerCaseTool-Local-Offline |

---

## 1. 事故摘要

2026 年 5 月，项目所有者在执行 `git filter-repo` 命令清除两个 Word 模板文件的 Git 历史时，因命令行拼写错误（"民事" 被误写为 "民 事"，中间多一个空格）和操作流程缺陷，导致 `民事起诉状.docx` 和 `民事答辩状.docx` 两个核心业务模板文件从 Git 历史、本地磁盘和 GitHub 远端被永久删除，且无法恢复。

---

## 2. 事故时间线

| 时间 | 事件 | 关键细节 |
|------|------|---------|
| T0 | **需求产生** | 用户发现 GitHub 仓库中 `民事起诉状.docx` 和 `民事答辩状.docx` 有错误内容，需要替换并彻底清除历史记录 |
| T1 | **选择方案** | 用户选择 `git filter-repo --invert-paths` 方案，意图从 Git 历史中彻底删除这两个文件 |
| T2 | **执行命令（含拼写错误）** | 执行命令：`git filter-repo --path "templates/civil_simple_plaintiff/民 事起诉状.docx" --path "templates/civil_simple_defendant/民事答辩状.docx" --invert-paths --force`。第一条路径中"民事"被误写为"民 事"（中间多一个空格） |
| T3 | **filter-repo 执行成功** | 命令未报错。`git filter-repo` 不验证路径是否实际存在于仓库中，静默执行了不匹配的过滤操作。实际只有第二条路径（民事答辩状.docx）被匹配，第一条因拼写错误未匹配 |
| T4 | **工作目录被刷新** | `git filter-repo` 重写历史后重新 checkout 工作目录，两个文件从本地工作目录消失 |
| T5 | **发现文件丢失** | 用户尝试 `git add` 恢复，发现文件不存在于工作目录中 |
| T6 | **放弃恢复** | 用户决定放弃从 Git 历史恢复，直接在 GitHub 网页上删除了这两个文件 |
| T7 | **当前状态** | 两个文件从 Git 历史、本地磁盘、GitHub 远端完全消失，不可恢复。`git reflog` 为空，无回退路径 |

---

## 3. 影响范围

### 3.1 数据影响

| 维度 | 严重度 | 说明 |
|------|--------|------|
| **数据丢失** | 🔴 严重 | `民事起诉状.docx` 和 `民事答辩状.docx` 从 Git 历史中彻底清除（reflog 已被 filter-repo 擦除），本地磁盘和 GitHub 远端均不存在 |
| **Git 历史损坏** | 🔴 严重 | filter-repo 重写了全部历史，原有提交记录被压缩为仅 5 个提交（3aa88d6 → 5319aa1），reflog 为空，原始历史不可恢复 |
| **协作者影响** | 🟡 中等 | 已 force push 到远端，任何协作者的本地克隆将产生历史冲突，需 re-clone |

### 3.2 业务影响

| 维度 | 严重度 | 说明 |
|------|--------|------|
| **服务中断** | 🟢 无影响 | LawyerCaseTool 应用本身仍在运行，其余模板文件完好 |
| **用户影响** | 🟡 中等 | 民事案件（最常见案件类型）的起诉状和答辩状模板缺失，用户创建此类案件时模板选择中缺少关键文档 |

### 3.3 仓库当前状态验证

**本地磁盘**：
- `templates/civil_simple_plaintiff/` — 存在 12 个文件，**缺少** `民事起诉状.docx`
- `templates/civil_simple_defendant/` — 存在 8 个文件，**缺少** `民事答辩状.docx`
- `git status` 显示 clean（无未提交的删除）

**GitHub 远端**（通过 API 验证）：
- `civil_simple_plaintiff/` — 12 个文件，无 `民事起诉状.docx`
- `civil_simple_defendant/` — 8 个文件，无 `民事答辩状.docx`
- 与本地状态一致

**Git 历史**：
- 仅剩 5 个提交（3aa88d6 → b96e12b → 420d6f9 → 3d026af → 5319aa1）
- `git log -- "民事起诉状.docx"` 或 `git log -- "民事答辩状.docx"` 均返回空 — 文件已从所有历史中完全抹除
- `git reflog` 为空 — 无回退路径

---

## 4. SEV 评级：SEV3

### 评级依据

- **非 SEV1/SEV2**：该事故不影响线上服务的可用性，LawyerCaseTool 应用本身仍在运行，其他模板文件完好
- **SEV3 而非 SEV4**：两个核心业务模板文件从 Git 历史、本地磁盘、GitHub 远端被**永久删除**，且无 reflog 可恢复。这属于不可逆的数据丢失，对民事案件业务流程有实际影响
- **降级因素**：项目为个人/小团队项目，非大规模用户服务；模板文件可重新制作

---

## 5. 根因分析（5 Why）

**核心问题**：`民事起诉状.docx` 和 `民事答辩状.docx` 被永久删除且无法恢复

### Why 1：为什么两个文件被永久删除？

→ 因为 `git filter-repo` 重写了整个 Git 历史，且 filter-repo 会擦除 reflog，导致无法通过 `git reflog` 回退到操作前的状态。

### Why 2：为什么 filter-repo 的结果与预期不符？

→ 因为命令中"民事起诉状"被误写为"民 事起诉状"（多了一个空格），导致路径不匹配。`git filter-repo` 不验证路径是否实际存在于仓库中，静默执行了不匹配的过滤。

### Why 3：为什么拼写错误在执行前未被发现？

→ 因为 `git filter-repo` 命令是手动输入的，没有预检机制（dry-run）来验证路径匹配。用户直接使用了 `--force` 跳过了 filter-repo 的安全确认提示。

### Why 4：为什么执行前没有创建备份？

→ 因为用户对 `git filter-repo` 的破坏性认知不足，没有在执行前创建仓库备份或测试分支。filter-repo 文档明确警告应在克隆的副本上操作。

### Why 5：为什么恢复失败？

→ 因为：(a) filter-repo 擦除了 reflog；(b) 用户没有远程备份或推送前的历史快照；(c) 用户放弃恢复后直接在 GitHub 网页删除了文件，进一步消除了残留痕迹。

### 根本原因汇总

| 层面 | 根因 |
|------|------|
| **直接原因** | 命令行拼写错误 + `git filter-repo` 静默执行不匹配路径 |
| **流程原因** | 缺少执行前预检/模拟运行（dry-run）步骤 |
| **系统原因** | 缺少 Git 破坏性操作的防护机制（备份、分支保护、操作前验证） |
| **认知原因** | 对 `git filter-repo` 的破坏性（不可逆、擦除 reflog）认知不足 |

---

## 6. 行动项

### 6.1 短期修复（紧急）

| # | 行动项 | 负责人 | 优先级 | 状态 |
|---|--------|--------|--------|------|
| 1 | **重建 `民事起诉状.docx` 模板** — 基于业务需求重新制作正确版本的模板文件 | 项目所有者 | P0 | 待执行 |
| 2 | **重建 `民事答辩状.docx` 模板** — 同上 | 项目所有者 | P0 | 待执行 |
| 3 | **将重建后的模板提交到仓库** — `git add` + `git commit` + `git push` | 项目所有者 | P0 | 待执行 |
| 4 | **通知所有协作者 re-clone** — 因历史重写，协作者的本地仓库需要重新克隆 | 项目所有者 | P1 | 待执行 |

### 6.2 长期预防（建议）

| # | 行动项 | 负责人 | 优先级 | 建议时间 |
|---|--------|--------|--------|---------|
| 5 | **建立模板文件备份机制** — 在项目外维护模板文件的原件备份（云盘/NAS/独立 Git 仓库） | 项目所有者 | P1 | 1 周内 |
| 6 | **启用 GitHub Branch Protection** — 对 main 分支启用保护，禁止 force push | 项目所有者 | P1 | 1 周内 |
| 7 | **编写 Git 破坏性操作 SOP** — 包含：必须先 dry-run、必须在克隆副本上操作、必须先备份 reflog | 项目所有者 | P2 | 2 周内 |
| 8 | **在 CI 中添加模板完整性检查** — 验证关键模板文件存在且非空 | 项目所有者 | P2 | 2 周内 |

---

## 7. 预防措施

### 7.1 技术层面

#### a) Git 破坏性操作安全协议（SOP）

```bash
# Step 1: 创建仓库完整备份
cp -r /path/to/repo /path/to/repo-backup-$(date +%Y%m%d)

# Step 2: 在克隆副本上操作
git clone /path/to/repo /path/to/repo-test
cd /path/to/repo-test

# Step 3: 先 dry-run 验证路径匹配
git filter-repo --path "目标路径" --invert-paths --dry-run

# Step 4: 确认无误后正式执行
git filter-repo --path "目标路径" --invert-paths --force

# Step 5: 验证结果
git log --oneline --name-status | grep "目标文件名"
ls -la 目标文件路径
```

#### b) GitHub Branch Protection 配置

- Settings → Branches → Branch protection rules → main
- ✅ Require a pull request before merging
- ✅ Require status checks to pass
- ❌ 禁止 force pushes

#### c) CI 模板完整性检查

建议在 `.github/workflows/` 中添加：

```yaml
- name: Verify critical templates
  run: |
    for f in \
      "templates/civil_simple_plaintiff/民事起诉状.docx" \
      "templates/civil_simple_defendant/民事答辩状.docx"
    do
      [ -f "$f" ] || { echo "CRITICAL: Missing template $f"; exit 1; }
    done
```

### 7.2 流程层面

#### a) 破坏性 Git 命令清单（需特别审批/备份后操作）

| 命令 | 风险等级 | 要求 |
|------|---------|------|
| `git filter-repo` | 🔴 极高 | 必须在副本上操作，必须 dry-run |
| `git filter-branch` | 🔴 极高 | 同上 |
| `git push --force` | 🟡 高 | 需确认无协作者或已通知 |
| `git rebase -i`（public branch） | 🟡 高 | 需确认分支无其他提交者 |
| `git reset --hard` | 🟡 高 | 需确认已 stash/commit 当前更改 |

#### b) 操作前检查清单

- [ ] 是否已在克隆副本上操作？
- [ ] 是否已创建备份？
- [ ] 是否已执行 dry-run 或模拟验证？
- [ ] 是否已通知所有协作者？
- [ ] 命令中的路径/文件名是否已二次确认（特别是中文文件名）？

---

## 8. 经验教训

### 教训 1：`git filter-repo` 不验证路径存在性——静默成功是最危险的失败模式

`git filter-repo` 的设计哲学是"灵活性优先"——它不会因为路径不匹配而报错或警告。这意味着拼写错误会被静默吞掉，命令显示"成功"但实际效果与预期完全不同。**对于破坏性操作，静默成功比显式失败更危险**，因为用户会误以为操作已正确完成，从而错过最后的恢复窗口。

**可复用原则**：任何不可逆操作的命令行工具，都应在执行前验证输入参数的合法性（如路径是否存在、文件是否匹配），或在输出中明确报告"0 个路径匹配"以引起警觉。

### 教训 2：`--force` 不是"我确认"——它是"跳过所有安全网"

`git filter-repo` 的 `--force` 参数跳过了"请在克隆副本上操作"的安全警告。很多 Git 命令都有类似的 `--force` 参数，其本质是**跳过安全检查**而非"确认执行"。在输入 `--force` 前，应逐条阅读被跳过的安全警告，确认每一条都不适用。

**可复用原则**：当需要使用 `--force` 时，先明确回答"这个命令默认会阻止我做什么？阻止的原因是什么？"再决定是否跳过。

### 教训 3：中文文件名是命令行操作的高风险点

输入法切换（中/英文）容易产生不可见的空格、全角/半角字符差异。本次事故中"民事"→"民 事"的差异在终端中极难肉眼发现。类似的问题还包括全角括号 `（）` vs 半角括号 `()`、全角逗号 `，` vs 半角逗号 `,` 等。

**可复用原则**：操作中文文件名时，应使用 tab 补全或 `git ls-files` 复制路径，而非手动输入。如果必须手动输入，应在执行前用 `ls` 或 `git show` 验证路径匹配。

### 教训 4：`git filter-repo` 擦除 reflog——"安全网"不存在

普通 Git 操作（commit、reset、rebase）都可通过 `git reflog` 回退，这给用户形成了"Git 操作总是可撤销"的惯性思维。但 `git filter-repo` 会擦除 reflog，这意味着**操作一旦执行就没有任何回退路径**。这种从"有安全网"到"无安全网"的环境切换，极易导致依赖 reflog 的恢复策略失败。

**可复用原则**：在执行任何会擦除 reflog 的操作前，必须先手动创建外部备份（`cp -r .git .git-backup`），不能用 Git 自身的机制作为唯一的恢复手段。

### 教训 5：恢复决策应有时间压力下的预定义策略

用户在发现文件丢失后，因不熟悉恢复方法且处于时间压力下，选择了"放弃恢复、直接删除"的决策。如果在操作前就定义了恢复策略（如"filter-repo 前先备份整个 .git 目录"），就能在出错时从容执行恢复，而非在慌乱中做出不可逆的决定。

**可复用原则**：为每个破坏性操作预定义回滚策略，并将其作为操作的必要前置步骤（而非事后补救）。"先备份再操作"应成为肌肉记忆。

---

## 附录

### A. 相关命令参考

- [git filter-repo 官方文档](https://github.com/newren/git-filter-repo)
- [GitHub Branch Protection 设置指南](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

### B. 术语表

| 术语 | 定义 |
|------|------|
| filter-repo | Git 历史重写工具，可从仓库历史中永久删除文件或修改提交 |
| reflog | Git 引用日志，记录 HEAD 的每次移动，通常用于恢复误操作 |
| --invert-paths | filter-repo 参数，表示删除匹配的路径（而非保留） |
| --force | filter-repo 参数，跳过安全确认（如"请在克隆副本上操作"警告） |
| SEV | 严重性等级（Severity），SEV1 最严重，SEV4 最轻微 |
