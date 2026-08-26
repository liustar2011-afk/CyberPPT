# Visual Structure Fidelity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将视觉结构设计从“生成版式意图”升级为可审计的业务关系模型，确保页面使命、主判断、关系拓扑和实际送图提示词保持一致，并允许后续替换 Style09、Style10 而不重新改写页面结构。

**Architecture:** 保留现有 `visual-design-input.json`、`visual-design-decisions.json` 和 `deck-visual-spec.json` 的主流程，在 `structural_decision` 中补充页面拓扑、节点、关系边、焦点节点和内容分组合并依据。新增关系保真、页面使命一致性和语义增补审计；风格文件只作为 Prompt 编译阶段的适配输入，不参与业务结构决策。

**Tech Stack:** Python 3.12、现有 `cyberppt` CLI、JSON Schema、unittest/pytest、Graft。

## Global Constraints

- 不改变最终脚本中的事实、主体、责任、数字、边界和锁定文字。
- 不新增第二套页面语义权威；`stage02-handoff.json` 和最终视觉结构规格继续作为正式输入。
- `business_relationships` 是业务关系权威来源；`author_visual_notes` 仅作参考。
- Style09、Style10 只能改变视觉表面和承载方式，不得改变页面拓扑、关系边、阅读方向和文字绑定。
- 视觉结构审计未通过时，不得重建正式 ImageGen Prompt，也不得把旁路重组提示词作为正式生产输入。
- 保留现有公开 CLI、JSON 文件路径、哈希绑定和 Stage 02 门禁行为。
- 修改生成逻辑后必须重新生成派生产物，不能手工修补 `deck-visual-spec.json` 或 `generation-prompts.md`。

## 文件与职责映射

- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py` — 生成结构化视觉决策、编译规格、执行回执和 Prompt 重建门禁。
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_structure_contract.py` — 增加关系保真、焦点一致性、分组合并和语义增补审计。
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_prompt_consumer.py` — 只消费审计通过的结构规格和风格适配输入，禁止旁路重写结构。
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/page_artifact_spec.py` — 若正式送图编译入口需要结构字段，保持字段透传和来源绑定。
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/output-contract.md` — 固化新增结构字段和风格边界。
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/quality-gates.md` — 增加业务结构正确性门禁。
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py` — 覆盖输入、编译、审计、回执和风格替换。
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_contract.py` — 覆盖关系保真、焦点一致性和分组合并审计。
- Test: `/Volumes/DOC/CyberPPT/tests/test_imagegen_no_visual_structure.py` — 防止 ImageGen 层重新生成视觉结构。

### Task 1: 固化页面视觉关系数据契约

**Files:**
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py`
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/assets/page-visual-spec.schema.json`
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/output-contract.md`
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: 当前 `visual-design-input.json` 中的 `core_judgment`、`business_relationships`、`stage01_relationship_features`、`locked_text_items` 和 `expression_constraints`。
- Produces: `structural_decision` 中的 `topology`、`primary_relation`、`focus_node`、`nodes`、`edges`、`grouping_decisions`、`forbidden_structures`。

- [ ] **Step 1: 定义字段形状和枚举边界**

使用以下最小结构，不把布局方向写入拓扑字段：

```json
{
  "topology": "causal_convergence",
  "primary_relation": "supports_then_leads_to",
  "focus_node": "necessity",
  "nodes": [
    {"id": "demand", "role": "evidence", "source_refs": []},
    {"id": "supply", "role": "evidence", "source_refs": []},
    {"id": "necessity", "role": "judgment", "source_refs": []}
  ],
  "edges": [
    {"from": "demand", "to": "necessity", "relation": "supports", "direction": "forward"},
    {"from": "supply", "to": "necessity", "relation": "supports", "direction": "forward"}
  ],
  "grouping_decisions": [],
  "forbidden_structures": ["equal_peer_cards", "invented_center_hub"]
}
```

允许的 `topology` 至少包括：`parallel_set`、`causal_convergence`、`layered_architecture`、`directed_flow`、`lifecycle_loop`、`governance_boundary`、`ecosystem_map`、`allocation_flow`、`conclusion_anchor`。

- [ ] **Step 2: 将结构字段写入页面 Schema 和 Markdown 输出**

要求 JSON Schema 拒绝缺少 `focus_node` 或 `edges` 的关系型页面；Markdown 复核摘要必须显示节点、关系边、焦点和禁止结构，避免只显示一句空间组织描述。

- [ ] **Step 3: 编写契约测试**

测试以下情况：

```text
有因果关系但没有结果节点 → 失败
有闭环关系但没有回流边 → 失败
有分层关系但所有节点都是 peer → 失败
关系型页面缺少 focus_node → 失败
parallel_set 页面含有强制先后边 → 警告或失败
```

- [ ] **Step 4: 运行定向测试**

运行：

```bash
cd /Volumes/DOC/CyberPPT
.venv/bin/python3 -m pytest tests/test_visual_structure_stage.py -q
```

预期：新增契约测试通过；既有页面字段兼容测试不回退。

### Task 2: 增加页面使命与视觉焦点一致性审计

**Files:**
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_structure_contract.py`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py`
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: `page_mission`、`core_judgment`、`structural_decision.focus_node`、节点角色和 `visual_decision.visual_hierarchy`。
- Produces: `FOCUS_NOT_JUDGMENT`、`MISSION_TOPOLOGY_MISMATCH`、`EVIDENCE_PROMOTED_TO_JUDGMENT` 等审计发现。

- [ ] **Step 1: 实现焦点角色校验**

规则：`focus_node` 默认必须是 `judgment`、`result` 或 `outcome`；若是 `evidence`，必须提供明确的 `focus_override_reason`，并由人工复核标记为允许。

- [ ] **Step 2: 实现页面类型反模式校验**

至少覆盖：

```text
conclusion_anchor 页面出现多个等权结论 → 失败
layered_architecture 缺少依赖边 → 失败
lifecycle_loop 缺少 feedback/returns_to/iterates 边 → 失败
allocation_flow 缺少角色或价值去向 → 失败
governance_boundary 缺少边界或控制关系 → 失败
```

- [ ] **Step 3: 编写 P04、P06、P17、P22、P31 回归用例**

用项目当前页面作为固定回归样本，但测试验证的是关系规则，不写“P04 必须三角构图”之类页面特例。

- [ ] **Step 4: 运行定向审计**

运行：

```bash
cd /Volumes/DOC/CyberPPT
.venv/bin/python3 -m pytest tests/test_visual_structure_stage.py tests/test_visual_structure_contract.py -q
```

预期：错误关系结构被阻断；正确的并列基础页、分层架构页和闭环页分别通过。

### Task 3: 建立内容合并与来源覆盖审计

**Files:**
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_structure_contract.py`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py`
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/quality-gates.md`
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: 原始 `content_units`、`source_refs`、结构节点和 `grouping_decisions`。
- Produces: `GROUPING_SOURCE_UNMAPPED`、`GROUPING_REASON_MISSING`、`GROUPING_ROLE_COLLISION`、`GROUPING_LOSS_RISK_HIGH`。

- [ ] **Step 1: 为每个结构节点登记源节点去向**

每个 `source_unit_id` 必须属于以下之一：

```text
独立呈现
合并到某一结构节点
保留为讲解层
明确不上屏
```

- [ ] **Step 2: 为合并增加理由和风险等级**

合并项必须包含：

```json
{
  "source_nodes": ["platform", "implementation"],
  "target_node": "resource_foundation",
  "reason": "两项均承担建设条件支撑职责",
  "loss_risk": "medium"
}
```

- [ ] **Step 3: 设置高风险合并阻断**

不同主体、不同阶段、不同责任、不同权利边界或不同结果类型不得在无人工确认的情况下合并。

- [ ] **Step 4: 增加 P07、P22 回归测试**

验证六项建设基础压缩为三组时每个源节点都有去向；验证收益分配页不能把定价依据、成本扣除、分配比例和动态调整无理由合并成普通三步流程。

### Task 4: 将风格适配器与结构编译器解耦

**Files:**
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_prompt_consumer.py`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/page_artifact_spec.py`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py`
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/prompt-assembly.md`
- Test: `/Volumes/DOC/CyberPPT/tests/test_imagegen_no_visual_structure.py`

**Interfaces:**
- Consumes: 审计通过的 `deck-visual-spec.json`、锁定文字和外部 Style lock。
- Produces: 风格变体 Prompt；不改变 `topology`、`edges`、`focus_node`、`reading_sequence` 和 `text_bindings`。

- [ ] **Step 1: 定义风格适配输入边界**

风格适配器只能写入颜色、材质、字体、线条、光影、场景政策和装饰政策；不得写入新的业务节点、关系边、页面使命或结论。

- [ ] **Step 2: 增加结构字段不变测试**

对同一 `deck-visual-spec.json` 分别注入 Style09 和 Style10，断言以下字段完全一致：

```text
topology
primary_relation
focus_node
nodes
edges
reading_sequence
text_bindings
```

- [ ] **Step 3: 阻断旁路 Prompt**

当正式视觉结构审计未通过时，Style 适配器不得把 `workbench/prompts/imagegen/send` 下的独立重组文件标记为正式送图输入。

- [ ] **Step 4: 运行 ImageGen 结构隔离测试**

运行：

```bash
cd /Volumes/DOC/CyberPPT
.venv/bin/python3 -m pytest tests/test_imagegen_no_visual_structure.py -q
```

预期：ImageGen 编译器只消费正式 Stage 02 结构规格，不自行生成页面拓扑。

### Task 5: 修复回执过期与 Prompt 新鲜度闭环

**Files:**
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/run_autonomous.py` 如调用链需要同步
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: 当前 Skill、Prompt builder、Validator、Schema 和 Style lock 的哈希。
- Produces: 只有当前合同全部匹配时才允许生成新的 `generation-prompts.md`。

- [ ] **Step 1: 保留旧回执失败行为**

不得通过忽略 `EXECUTION_RECEIPT_STALE` 或放宽哈希检查来恢复流程。

- [ ] **Step 2: 增加重新执行提示**

错误信息必须同时指出：

```text
过期字段
当前期望哈希来源
需要重新执行的命令
```

- [ ] **Step 3: 增加风格替换不触发结构重算测试**

仅替换 Style lock 时，结构规格哈希不变；仅结构决策变化时，Prompt 必须重建。

- [ ] **Step 4: 运行 Stage 02 定向验证**

使用仓库 `.venv/bin/python3` 运行现有视觉结构审计命令，并核对：

```text
execution_receipt.status = passed
prompt_freshness.status = passed
validation-report.status = passed
```

### Task 6: 重新生成项目产物并完成结构抽样复核

**Files:**
- Regenerate: `/Volumes/DOC/CyberPPT/projects/power-data-infrastructure-cooperation-v16-20260815-foundation/visual/visual-design-decisions.json`
- Regenerate: `/Volumes/DOC/CyberPPT/projects/power-data-infrastructure-cooperation-v16-20260815-foundation/visual/deck-visual-spec.json`
- Regenerate: `/Volumes/DOC/CyberPPT/projects/power-data-infrastructure-cooperation-v16-20260815-foundation/visual/generation-prompts.md`
- Regenerate: `/Volumes/DOC/CyberPPT/projects/power-data-infrastructure-cooperation-v16-20260815-foundation/visual/validation-report.json`

- [ ] **Step 1: 重新准备 Stage 02 handoff 和视觉结构输入**

必须使用当前最终脚本，不消费旧的 Style09/Style10 图片或旁路 Prompt。

- [ ] **Step 2: 重新执行视觉结构 Skill 并记录当前回执**

回执必须绑定当前 Skill bundle、合同文件和最终脚本语义哈希。

- [ ] **Step 3: 运行视觉结构审计**

审计必须通过后才能重建正式 Prompt。

- [ ] **Step 4: 抽样复核 P04、P06、P07、P17、P22、P31**

每页至少确认：页面使命、主判断、拓扑、焦点节点、关系边、内容合并和禁止结构。

- [ ] **Step 5: 运行全套相关测试并保存结果**

验证内容包括：结构 Schema、关系保真、分组合并、风格隔离、回执哈希、Prompt 新鲜度和 ImageGen 入口隔离。

## 验收标准

1. 所有内容页均有可审计的 `topology`、`focus_node`、`nodes` 和 `edges`。
2. 因果、分层、流程、闭环、治理和收益分配页面不能退化为无关系的等权卡片集合。
3. 每个源内容单元都有独立呈现、合并、讲解层或不上屏的明确去向。
4. 高风险内容合并会被阻断或进入人工复核，不会静默丢失主体、阶段、责任或边界。
5. 页面使命、核心判断和视觉焦点不一致时，视觉结构审计失败。
6. Style09 与 Style10 生成的结构字段完全一致，仅风格字段发生变化。
7. 视觉结构回执过期时，正式 Prompt 不会被重建，旁路 Prompt 不会被视为正式输入。
8. 当前项目 `validation-report.json` 达到 `status: passed`，且 `execution_receipt` 与 `prompt_freshness` 均通过。
9. 抽样页面复核确认：P04 的背景与必要性关系、P06 的分层与贯穿关系、P07 的内容合并、P17 的生命周期回流、P22 的收益分配关系、P31 的结论收束均没有被结构模型改写。

## 风险与控制

- 风险：新增字段导致旧项目规格无法读取。控制：字段采用向后兼容默认值，旧项目只在重新执行视觉结构阶段时升级。
- 风险：关系边过度结构化，限制视觉设计自由度。控制：约束业务拓扑和语义关系，不固定具体图形、位置和材质。
- 风险：风格适配器再次承担页面设计。控制：增加结构字段不变测试和 ImageGen 入口隔离门禁。
- 风险：合并审计误把正常的内容归并判为错误。控制：允许作者提供合并理由和风险等级，对高风险项人工复核，不对所有归并一律阻断。
- 风险：当前项目旧执行回执阻断重建。控制：重新执行当前注册 Skill，不降低哈希门禁。
