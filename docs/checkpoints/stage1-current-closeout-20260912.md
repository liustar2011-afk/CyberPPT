# Stage1 当前尾项收口检查点

日期：2026-09-12

状态：实现完成，等待本分支 PR CI 验证。

## 一、本轮排查范围

本轮从当前 `main` 反查 Stage1 文档、近期合并 PR、当前 `script_engine` 实现与回归测试，重点区分两类记录：

1. 当前架构仍然有效的待办；
2. 已被后续重构、合并或目录迁移取代，但历史文档仍保留 `partial` / `in progress` 字样的旧记录。

## 二、历史记录判定

### 1. Stage1 hardening 已完成

`docs/checkpoints/stage1-hardening-current.md` 已明确记录 PR #34、#36 的 hard gate、Page Source Packet v2、Author Preflight v2、Final Script 来源血缘和 native-source fidelity audit 已完成并进入 `main`，该检查点不再包含待执行事项。

### 2. 页面消费语义 WP6 不再是当前 backlog

`docs/stage01-development-plan-20260825.md` 与 `docs/stage01-page-consumption-implementation-report-20260826.md` 曾记录旧页面消费语义方案的 WP6 为部分完成：旧回归项目仅迁移 P04，其余 12 个内容页保留 advisory。

该记录依赖当时的 `projects/ai_power_training_business_feasibility` 和 `.agents/skills/ppt-outline-planning` 路径。当前 `main` 已不存在这两个执行入口，Stage1 已迁移到 `script_engine`、`cyberppt-script-workflow`、Foundation / Deck Plan / Final Script 三权威工件链，因此不应把旧项目的 12 页迁移继续解释为当前代码待办。

### 3. `dev-stage1-faithful-progress.md` 的 Step 7A 属于历史状态

该进度文档仍保留 `Step 7A — Start repository-native CI verification / Status: in progress`，但对应 PR #28 已合并，后续又连续完成 #34、#35、#36、#47 等 Stage1 hardening、Final Script 1.2 与 fidelity contract 收敛。

因此 Step 7A 的 `in progress` 不是当前分支待办。

## 三、本轮确认并完成的真实尾项

`docs/dev-stage1-faithful-progress.md` 在 Step 3 明确 deferred：`final_lean.py` 仍保留 legacy 的 `argument paragraphs` 等措辞，计划在 source-addition audit 落地后清理。

source-addition audit 后续已经完成，但该诊断措辞仍存在于当前 `main`：

- `AUTHOR_SOURCE_CONSUMPTION_TOO_NARROW` 仍写成页面不能把 `whole argument` 放在一个事实之上；
- `AUTHOR_FULL_COPY_TOO_THIN` 仍要求 `argument paragraph(s)`，并写成 `before onscreen compression`。

这些措辞与当前 faithful / Final Script 1.2 合同不一致。Final Script 1.2 的 Stage1 权威输出是 `full_copy + fidelity_text`，Stage1 不再 authored `onscreen`；faithful 页面也不应被诊断文本暗示必须构造分析型论证结构。

本轮采取最小必要修复：

- 保留原有 source-consumption 阈值和 source-retention 判定逻辑；
- 仅将 `whole argument` 改为 `source-backed content`；
- 将 `argument paragraph(s)` 改为 `source-backed content paragraph(s)`；
- 将 `audience-facing reasoning hierarchy before onscreen compression` 改为版本中性的 `audience-facing content hierarchy`；
- 新增定向回归，防止上述 analytical / onscreen 旧措辞重新进入 faithful source-consumption 诊断。

## 四、当前 Stage1 状态

截至本检查点，本轮文档扫描没有发现其他仍适用于当前架构、且尚未实现的 Stage1 代码任务。

当前 Stage1 继续以以下合同为准：

- 默认 faithful route 的 exact-source hard gate；
- Foundation / Deck Plan / Final Script 三个权威工件；
- Final Script 1.2 内容页由 Stage1 负责 `full_copy + fidelity_text`，不得 authored `onscreen`；
- Stage2 从 `full_copy` 形成运行时可见正文，并仅对 `fidelity_text` literal 执行精确保真检查；
- 历史 strict/legacy 路径保留兼容，但不作为新 faithful 项目的默认作者流程。

后续若新增 Stage1 功能，应建立新的开发计划或 checkpoint，不应继续沿用 2026-08 页面消费项目或 2026-09-07 PR #28 的历史 `partial` / `in progress` 状态。

## 五、验收

本分支新增定向回归：

`tests/script_engine/test_stage01_faithful_diagnostic_wording.py`

验收条件：

1. 新增定向回归通过；
2. 现有 Stage1 / script_engine 回归无新增失败；
3. GitHub Actions 仓库 CI 通过后，本检查点可视为完成。
