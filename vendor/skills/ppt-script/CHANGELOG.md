# Changelog

## 3.7.0 — 2026-07-18

- 新增结构化经验案例库、批准状态控制、案例索引和混合检索。
- 新增 `case-index`、`case-search`、`experience-pack` 和 `case-capture`。
- 历史案例仅在认知闸门通过后参与故事线、页面规划和质量审查；不得作为 Source ID 或当前项目事实。
- 新增适用条件、不适用条件和反模式惩罚，防止错误套用案例。
- 新增复杂材料认知和经验检索评分表，为真实模型 A/B 评测提供统一口径。

## 3.6.0 — 2026-07-18

- 新增忠实阅读、决策阅读和综合裁决三阶段认知工作流，使用隔离上下文避免两次阅读相互污染。
- 新增 `contracts/evidence-graph.json`，记录主张、支撑来源、反向来源、适用条件、置信度、主张关系和页面关联。
- 新增 `cognitive-init`、`cognitive-pack`、`cognitive-check`、`evidence-check` 和 `trace-claim`。
- 新增 `COGNITIVE_READY` 状态；新正式项目默认启用认知增强闸门，旧项目保持兼容。
- 新增认知工作区、证据图谱校验和复杂材料回归测试。

## 3.5.1 — 2026-07-18

- 修复 V3.5.0 模块化导致的复杂材料解读能力下降：新增常驻 `stage1-deep-reading-kernel`，恢复意图识别、原文结构评估、跨章节证据综合、状态和边界控制、冲突处理等认知方法。
- `context-pack` 升级为 `ppt-script.active-context.v2`：正式项目默认 `deep`，嵌入可提取的源材料正文、当前分析、Source Truth Map、决策稿、提纲和结构化合同；`compact` 仅作为显式轻量选项。
- 新增 `understanding-check` 与 `analysis/02-understanding-gate.*`，防止只有形式化 Source Truth 表格、缺少深度分析的项目过早进入故事线阶段。
- 恢复故事线、章节合同、页面合同、逐页脚本和质量审查模块中被过度压缩的方法规则。
- 新项目默认 `source_truth_mode=full`、`context_mode=deep`，并生成完整材料分析脚手架。
- 新增复杂正式材料回归样例和深度解读测试。


## 3.5.0 — 2026-07-18

- 新增 10 类任务路由、材料状态与汇报目标组合。
- 新增项目显式状态机和 `route`、`state` 命令。
- 新增 Source Truth、整套决策、章节和页面 JSON 合同及 `contract-check`。
- 将 Stage 1/2 拆分为按需 Prompt 模块，新增 `context-pack`。
- 新增页面类型差异化文字预算和质量阻断。
- 保留 V3.3 项目、页面模板、正式汇报配置和原有命令兼容性。

## 3.4.0 — 2026-07-18

- 建立 `VERSION` 单一版本来源。
- 清理重复命令、重复定义和旧初始化入口。
- 新增 `doctor`、仓库一致性检查和完整发布复测。
- 安装提示、项目元数据和运行时版本改为动态读取。

## 3.3.0

- 新增 15 类汇报类型、7 种汇报目的、9 类受众层级和 7 个项目阶段。
- 新增 `government-soe-formal` 与 `style-check`。
- 保留模块化命令、统一规则注册表、质量闸门、结构化讲解词及生图上下文净化。
- 新项目四维场景字段为必填契约，不提供旧项目缺字段兼容。

## 3.1.0

- Added structured speaker notes for substantive pages.
- Added `notes-check`, duration and source-number checks.
- Added `script-speaker-notes.md` and `speaker-notes.json` outputs.
- Preserved modular commands, unified `run`, and centralized page rules.

## 3.0.0 — 2026-07-17

- Unified the production-oriented `ppt-script` workflow with source-truth governance and deterministic auditing.
- Added six execution modes: source interpretation, source-to-script, evaluation, optimization, comparison, and full pipeline.
- Made Source Truth Map mandatory for formal source-based work, using unified `S###` IDs and F/P/J/I/R/B/U classification.
- Added deck storyline, chapter contracts, page contracts, and a mandatory planning gate.
- Added a 100-point evaluation model and four quality gates.
- Added MD/TXT/DOCX/PPTX/PDF deterministic extraction.
- Added `source-inventory`, `plan-check`, `audit`, and `compare` commands.
- Preserved existing project commands, page templates, semantic diagrams, Stage 2 visual handoff, and three assembled script outputs.
- Added clean installation for Codex and Claude Code.
