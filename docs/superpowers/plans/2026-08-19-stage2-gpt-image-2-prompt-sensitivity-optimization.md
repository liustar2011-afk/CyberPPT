# Stage 2 GPT Image 2 提示词敏感度优化（基于 p08 敏感性分析）

**Goal:** 依据 `gpt-image-2-ppt-prompt-sensitivity-analysis.md` 的结论——GPT Image 2 对"产物模式词（S+级）"和"关系动词（S级）"最敏感——修正 Stage 2 最终提示词编译链路中两处已用真实代码核实存在的浪费点：`deliverable.asset_type` 硬编码为后端占位符，以及 `_TOPOLOGY_PHRASES` 的九条关系短语用弱名词短语而非强关系动词表达。

**范围声明：** 本方案不重建任何架构，只调整两个既有映射点的取值；不改变 `PageArtifactSpec`/`FinalPromptIR` 的字段形状，不改变七段式渲染顺序，不改变 Style09 正文。

## 现状核实证据

1. `cyberppt/page_artifact_spec.py:428` 硬编码 `asset_type="powerpoint_body_visual_asset"`，经 [scripts/imagegen_pipeline/artifact_prompt.py:304](../../../scripts/imagegen_pipeline/artifact_prompt.py:304) 的 `_deliverable_sentence()` 直接拼入最终提示词第 1 段（Deliverable，对应 p08 的 S+ 级 "OUTPUT MODE"）：`"Create one finished powerpoint_body_visual_asset for a PowerPoint {page_role} page."`。这是一个工程标识符，不是 p08 验证过的自然语言触发词；`final_prompt_contract.py:49-52` 的 `_ALLOWED_SNAKE_CASE_TOKENS` 专门为它开了白名单豁免，说明团队已知其形态异常但未处理。
2. `cyberppt/page_artifact_spec.py` 的 `_TOPOLOGY_PHRASES`（9 条）把 `semantic_graph.topology` 的九种拓扑映射为英文短语，投影进最终提示词第 5 段（Composition，对应 p08 的 S 级"关系语义"）。当前短语多为静态名词短语（如 `"a set of coordinate peers with no forced order between them"`），未使用 p08 文档第四节归纳、经验证有效的强关系动词句式（`converge into` / `branch into` / `one continuous flow` / `hub-and-spoke` / `closed-loop cycle` / `foundation layer supporting upper layers`）。
3. `parallel_set` 拓扑对应 p08 文档第六节"grid 适合使用"的典型场景（指标展示、模块清单、多对象并列），但当前短语和全局 `equal_peer_cards` 禁令（`cyberppt/commands/visual_structure_stage.py:115`，对每个拓扑一视同仁）没有给出"结构化编辑网格"这一 p08 验证过的折中表达，可能让本应等权并列的内容被迫伪装出不必要的非对称构图。

## Global Constraints

- 不修改 Source Truth、Stage 01 语义事实、`PageArtifactSpec`/`FinalPromptIR` 字段形状。
- 不改变 `_TOPOLOGY_PHRASES` 各拓扑的业务含义，只增强其触发构图的动词强度；`equal_peer_cards` 等既有反模式禁令保持不变（禁止字面卡片边框/图标墙，不禁止"等权并列网格"本身）。
- 运行 Python 命令使用仓库 `.venv/bin/python3`（若不存在则用 `python3`）。
- 每步先跑受影响测试确认失败原因符合预期，再改代码，再跑测试确认通过。

## Task 1：Deliverable 触发词从后端占位符改为 p08 验证的 S+ 级短语

**Files:**
- Modify: `cyberppt/page_artifact_spec.py`（`asset_type="powerpoint_body_visual_asset"` → `asset_type="presentation content visual"`）
- Modify: `scripts/imagegen_pipeline/final_prompt_contract.py`（移除 `_ALLOWED_SNAKE_CASE_TOKENS` 中不再需要的豁免项及其注释）
- Modify: `tests/test_page_artifact_spec.py`、`tests/test_artifact_prompt.py`、`tests/test_final_prompt_ir.py`（同步夹具与断言）

- [ ] **Step 1:** 跑 `tests/test_page_artifact_spec.py::PageArtifactSpecTests::test_builds_nine_section_projection_without_backend_ids`，确认当前断言为 `"powerpoint_body_visual_asset"`（基线）。
- [ ] **Step 2:** 修改 `page_artifact_spec.py` 的 `asset_type` 取值。
- [ ] **Step 3:** 同步更新三个测试文件里手写 `asset_type="powerpoint_body_visual_asset"` 的夹具和断言为新值；`test_final_prompt_ir.py:44` 的 `deliverable="Create one finished powerpoint_body_visual_asset."` 同步改写。
- [ ] **Step 4:** 从 `final_prompt_contract.py` 的 `_ALLOWED_SNAKE_CASE_TOKENS` 移除该项并更新其上方注释（不再需要豁免，因为新值本身不是 snake_case）。
- [ ] **Step 5:** 运行：
  ```bash
  .venv/bin/python3 -m pytest -q tests/test_page_artifact_spec.py tests/test_artifact_prompt.py tests/test_final_prompt_ir.py tests/test_final_prompt_contract.py tests/test_final_prompt_renderer.py
  ```
  Expected: PASS。

## Task 2：`_TOPOLOGY_PHRASES` 注入 p08 强关系动词，`parallel_set` 增加网格例外表述

**Files:**
- Modify: `cyberppt/page_artifact_spec.py`（`_TOPOLOGY_PHRASES` 九条取值）
- Modify: `tests/test_page_artifact_spec.py`（`test_builds_nine_section_projection_without_backend_ids` 中 `directed_flow` 的精确匹配断言）

- [ ] **Step 1:** 跑 `tests/test_page_artifact_spec.py`，确认 `assertEqual("a directed business flow from input to result", spec.composition.topology)` 为基线断言。
- [ ] **Step 2:** 按下表更新九条短语（保留原意，叠加 p08 强动词/句式；`parallel_set` 额外声明"结构化编辑网格"的有条件许可，且不触碰 `equal_peer_cards` 等既有反模式禁令）：

  | topology | 新短语要点 |
  |---|---|
  | `parallel_set` | 等权并列 + 允许 `structured editorial grid`，但仍避免字面卡片边框/逐项图标 |
  | `causal_convergence` | `converging into` + "one continuous convergent flow" |
  | `layered_architecture` | "foundation layer supporting upper layers" + "one continuous dependency chain" |
  | `directed_flow` | "one continuous left-to-right flow" |
  | `lifecycle_loop` | 显式改称 "closed-loop cycle" |
  | `governance_boundary` | "one continuous boundary" 强调非装饰性 |
  | `ecosystem_map` | 改用 "hub-and-spoke" |
  | `allocation_flow` | "branching out from one source into" |
  | `conclusion_anchor` | "converging into" + "one continuous convergent flow toward a single anchor" |

- [ ] **Step 3:** 更新 `tests/test_page_artifact_spec.py:184` 断言为新的 `directed_flow` 短语。
- [ ] **Step 4:** 运行：
  ```bash
  .venv/bin/python3 -m pytest -q tests/test_page_artifact_spec.py tests/test_artifact_prompt.py tests/test_final_prompt_ir.py tests/test_final_prompt_contract.py tests/test_final_prompt_renderer.py
  ```
  Expected: PASS。

## Task 3：全量回归

- [ ] 运行 `.venv/bin/python3 -m pytest -q` 全量测试，对比改动前后失败用例集合应完全一致（新增改动不引入新失败，也不意外修复已知无关失败）。

## 实施纪要（2026-08-19，已完成）

- Task 1：`asset_type` 由 `"powerpoint_body_visual_asset"` 改为 `"presentation content visual"`；同步移除 `final_prompt_contract.py` 中不再需要的 snake_case 豁免项（改为空的、带说明的 `frozenset` 占位，供未来真实需要时复用），并删除了专门测试该豁免机制的 `test_allowlists_the_deliverable_asset_type_token`（其测试对象已不存在于生产路径）。
- Task 2：`_TOPOLOGY_PHRASES` 九条全部按 p08 强关系动词/句式改写；`parallel_set` 按方案叠加了 `structured editorial grid` 的有条件许可，未触碰 `equal_peer_cards` 等既有反模式禁令。
- 全部改动均为字符串取值调整，未改变任何 dataclass 字段形状或渲染顺序。
- 回归对照：`git stash -u` 前后各跑一次全量 `pytest`，均为 `12 failed`（同一 12 个既有失败用例，`test_extended_style_10`/`test_imagegen_creative_brief`/`test_imagegen_handoff_modularization`/`test_reassemble_style10_migration_only`/`test_visual_proof_preflight_diagnostics`，与本次改动无关），passed 数从 1110 降到 1109 是因为按计划删除了 1 个失去测试对象的用例，非回归。

## 验收标准

- 最终提示词第 1 段（Deliverable）不再包含 `powerpoint_body_visual_asset` 或任何 snake_case 占位符。
- 九种拓扑短语均包含至少一个 p08 文档验证过的强关系动词/句式（`converg`、`branch`、`one continuous`、`hub-and-spoke`、`closed-loop`、`foundation layer supporting`）。
- `parallel_set` 短语显式许可 `structured editorial grid`，同时不移除 `equal_peer_cards` 等既有反模式禁令。
- 全量测试通过，且失败用例集合与改动前一致（无回归）。
