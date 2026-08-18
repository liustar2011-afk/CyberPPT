# Visual Structure Fidelity Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**相对 v1 的改动：** v1（`2026-08-18-visual-structure-fidelity.md`）在 `structural_decision` 下新增 `topology`/`primary_relation`/`focus_node`/`nodes`/`edges`，但 `page-visual-spec.schema.json` 中已经存在 `semantic_graph` 对象，携带同名或同语义字段（`primary_relation`、`nodes`、`edges`、`business_relationships`、`decision_relationship`），并已有成熟审计逻辑（`visual_structure_contract.py` 中的 `_audit_relationship_coverage`、`_audit_focus_competition`、`audit_visual_deck_rhythm` 等）在消费它。v1 会造成同一页面规格内出现两组"这个页面的关系是什么"的答案，直接违反计划自身"不新增第二套页面语义权威"的约束。v2 改为**扩展 `semantic_graph`**，不在 `structural_decision` 下新建平行结构；同时不考虑历史项目的兼容与迁移，`semantic_graph`/`page-visual-spec.schema.json` 可直接按新形状修改，无需版本门控或旧数据升级路径。

**Goal:** 将视觉结构设计从"生成版式意图"升级为可审计的业务关系模型，确保页面使命、主判断、关系拓扑和实际送图提示词保持一致，并允许后续替换 Style09、Style10 而不重新改写页面结构。

**Architecture:** 保留现有 `visual-design-input.json`、`visual-design-decisions.json` 和 `deck-visual-spec.json` 的主流程；在既有 `semantic_graph` 中补充页面拓扑（`topology`）、焦点节点（`focus_node`）、结构化节点/关系边（升级 `nodes`/`edges` 的形状）和内容分组合并依据（`grouping_decisions`、`forbidden_structures`），使 `semantic_graph` 成为唯一的业务关系与拓扑权威。`structural_decision` 保持其原有职责（空间语法、阅读顺序、文字绑定、表达自由度），新增的一致性审计负责校验 `structural_decision.semantic_focus` 与 `semantic_graph.focus_node` 是否指向同一业务对象。新增关系保真、页面使命一致性和语义增补审计；风格文件只作为 Prompt 编译阶段的适配输入，不参与业务结构决策。

**Tech Stack:** Python 3.12、现有 `cyberppt` CLI、JSON Schema、unittest/pytest。

## Global Constraints

- 不改变最终脚本中的事实、主体、责任、数字、边界和锁定文字。
- 不新增第二套页面语义权威；`semantic_graph` 是页面业务拓扑与关系的唯一权威字段，`structural_decision` 只表达空间/文字承载方式，不得重复定义 `topology`/`primary_relation`/`nodes`/`edges`。
- `business_relationships` 是业务关系权威来源；`author_visual_notes` 仅作参考。
- Style09、Style10 只能改变视觉表面和承载方式，不得改变页面拓扑、关系边、阅读方向和文字绑定。
- 视觉结构审计未通过时，不得重建正式 ImageGen Prompt，也不得把旁路重组提示词作为正式生产输入。
- 保留现有公开 CLI、JSON 文件路径和 Stage 02 门禁行为；`schema_version` 沿用当前值，不引入新的版本号或旧数据兼容层——历史项目数据不在本计划兼容范围内，按新 Schema 直接改写。
- 修改生成逻辑后必须重新生成派生产物，不能手工修补 `deck-visual-spec.json` 或 `generation-prompts.md`。

## 文件与职责映射

- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/assets/page-visual-spec.schema.json` — 扩展 `semantic_graph`，新增 `topology`/`focus_node`/`grouping_decisions`/`forbidden_structures`，升级 `nodes`/`edges` 形状。
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py` — 生成结构化视觉决策、编译规格、执行回执和 Prompt 重建门禁。
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_structure_contract.py` — 扩展现有 `_audit_relationship_coverage`/`_audit_focus_competition`/`audit_visual_deck_rhythm`，新增关系保真、焦点一致性、分组合并和语义增补审计，避免与既有函数重复判断同一事实。
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_prompt_consumer.py` — 只消费审计通过的 `semantic_graph` 结构规格和风格适配输入，禁止旁路重写结构。
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/page_artifact_spec.py` — 若正式送图编译入口需要新结构字段，保持字段透传和来源绑定。
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/output-contract.md` — 固化 `semantic_graph` 新增字段、`structural_decision` 与 `semantic_graph` 的职责边界，以及风格边界。
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/quality-gates.md` — 增加业务结构正确性门禁。
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py` — 覆盖输入、编译、审计、回执和风格替换。
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_contract.py` — 覆盖关系保真、焦点一致性和分组合并审计，并覆盖"新旧字段不重复权威"的回归用例。
- Test: `/Volumes/DOC/CyberPPT/tests/test_imagegen_no_visual_structure.py` — 防止 ImageGen 层重新生成视觉结构。

### Task 0: 建立现状基线（先于任何改动）

**Files:**
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py`（只读，不新增用例）
- Test: `/Volumes/DOC/CyberPPT/tests/test_imagegen_no_visual_structure.py`（只读，不新增用例）

**Interfaces:**
- Consumes: 当前 `semantic_graph`、`structural_decision`、`visual_prompt_consumer.py`、`page_artifact_spec.py` 的现状实现。
- Produces: 一份现状说明（写入本任务的 PR 描述或提交说明即可，不需要新建文档文件），列出：`semantic_graph` 当前字段清单、`structural_decision` 当前字段清单、当前是否已有 Style 适配代码路径写入这两个对象。

- [ ] **Step 1: 跑通现有全套相关测试，记录基线**

```bash
cd /Volumes/DOC/CyberPPT
.venv/bin/python3 -m pytest tests/test_visual_structure_stage.py tests/test_visual_structure_contract.py tests/test_imagegen_no_visual_structure.py -q
```

预期：全部通过，作为后续改动的回归基线。

- [ ] **Step 2: 确认 Style09/Style10 当前是否写入结构字段**

在 `visual_prompt_consumer.py`、`page_artifact_spec.py` 中确认当前 Style 适配路径是否已经在写 `semantic_graph.nodes`/`edges`/`primary_relation` 或 `structural_decision.*`。如果已经存在这类写入，先记录下来，作为 Task 4 结构字段不变测试要修复的既有问题，而不是当作 Task 4 中途才发现的意外。

### Task 1: 扩展 `semantic_graph` 为唯一的页面拓扑与关系权威

**Files:**
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/assets/page-visual-spec.schema.json`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py`
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/output-contract.md`
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: 当前 `visual-design-input.json` 中的 `core_judgment`、`business_relationships`、`stage01_relationship_features`、`locked_text_items` 和 `expression_constraints`；当前 `semantic_graph` 中已有的 `primary_relation`、`direction`、`nodes`、`edges`、`decision_relationship`、`business_relationships`。
- Produces: 扩展后的 `semantic_graph`，新增 `topology`、`focus_node`、`grouping_decisions`、`forbidden_structures`；`nodes` 从字符串数组升级为对象数组（`id`/`role`/`source_refs`）；`edges` 增加 `direction` 字段（区别于页面级已有的 `direction` 枚举，这里是每条边的方向）。**不新增 `structural_decision.primary_relation`/`structural_decision.nodes`/`structural_decision.edges`**——这些概念只存在于 `semantic_graph` 一处。

- [ ] **Step 1: 定义字段形状和枚举边界（写入 `semantic_graph`，非 `structural_decision`）**

在现有 `semantic_graph` 基础上新增字段，不新建平行对象：

```json
{
  "primary_relation": "cause",
  "direction": "outside_to_center",
  "topology": "causal_convergence",
  "focus_node": "necessity",
  "nodes": [
    {"id": "demand", "role": "evidence", "source_refs": []},
    {"id": "supply", "role": "evidence", "source_refs": []},
    {"id": "necessity", "role": "judgment", "source_refs": []}
  ],
  "edges": [
    {"from": "demand", "to": "necessity", "relation": "supports", "label": "…", "direction": "forward"},
    {"from": "supply", "to": "necessity", "relation": "supports", "label": "…", "direction": "forward"}
  ],
  "decision_relationship": "…",
  "business_relationships": [],
  "grouping_decisions": [],
  "forbidden_structures": ["equal_peer_cards", "invented_center_hub"]
}
```

`nodes`/`edges` 字段名保持不变，但 schema 中的 `items` 形状从字符串升级为对象；旧的字符串数组写法不再合法（不做兼容，历史项目数据不在本计划范围内）。

允许的 `topology` 至少包括：`parallel_set`、`causal_convergence`、`layered_architecture`、`directed_flow`、`lifecycle_loop`、`governance_boundary`、`ecosystem_map`、`allocation_flow`、`conclusion_anchor`。

- [ ] **Step 2: 明确 `structural_decision.semantic_focus` 与 `semantic_graph.focus_node` 的职责边界**

在 `output-contract.md` 中写清楚：`semantic_graph.focus_node` 回答"业务上哪个节点是焦点"（结构权威），`structural_decision.semantic_focus.ref` 回答"版面上焦点节点用什么承载方式呈现"（表达层）。两者必须指向同一业务对象，一致性由 Task 2 的审计负责，`structural_decision` 不得自行声明另一个焦点。

- [ ] **Step 3: 将新增字段写入 Schema 和 Markdown 输出**

要求 JSON Schema 拒绝缺少 `focus_node` 或 `edges` 的关系型页面；Markdown 复核摘要必须显示节点、关系边、焦点和禁止结构，避免只显示一句空间组织描述。

- [ ] **Step 4: 编写契约测试**

测试以下情况：

```text
有因果关系但没有结果节点 → 失败
有闭环关系但没有回流边 → 失败
有分层关系但所有节点都是 peer → 失败
关系型页面缺少 focus_node → 失败
parallel_set 页面含有强制先后边 → 警告或失败
structural_decision 中出现 topology/primary_relation/nodes/edges 字段 → schema 拒绝（防止第二套权威复活）
```

- [ ] **Step 5: 运行定向测试**

```bash
cd /Volumes/DOC/CyberPPT
.venv/bin/python3 -m pytest tests/test_visual_structure_stage.py -q
```

预期：新增契约测试通过。

### Task 2: 增加页面使命与视觉焦点一致性审计（复用并扩展现有审计函数）

**Files:**
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_structure_contract.py`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py`
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: `page_mission`、`core_judgment`、`semantic_graph.focus_node`、节点角色、`structural_decision.semantic_focus`、`visual_decision.visual_hierarchy`；现有 `_audit_focus_competition`、`_audit_relationship_coverage`、`audit_visual_deck_rhythm`。
- Produces: `FOCUS_NOT_JUDGMENT`、`MISSION_TOPOLOGY_MISMATCH`、`EVIDENCE_PROMOTED_TO_JUDGMENT`、`FOCUS_LAYER_MISMATCH`（`semantic_graph.focus_node` 与 `structural_decision.semantic_focus.ref` 不一致时报出）等审计发现。

- [ ] **Step 1: 先读一遍现有 `_audit_focus_competition` 的判断逻辑，明确新规则是扩展还是替代**

`_audit_focus_competition`（`visual_structure_contract.py:366`）已经在做焦点相关的审计。新增规则前，先确认它当前覆盖了什么、遗漏了什么，避免重复实现同一判断或产生互相矛盾的结论。只在它没有覆盖的地方新增函数。

- [ ] **Step 2: 实现焦点角色校验**

规则：`focus_node` 默认必须是 `judgment`、`result` 或 `outcome`；若是 `evidence`，必须提供明确的 `focus_override_reason`，并由人工复核标记为允许。

- [ ] **Step 3: 实现页面类型反模式校验**

至少覆盖：

```text
conclusion_anchor 页面出现多个等权结论 → 失败
layered_architecture 缺少依赖边 → 失败
lifecycle_loop 缺少 feedback/returns_to/iterates 边 → 失败
allocation_flow 缺少角色或价值去向 → 失败
governance_boundary 缺少边界或控制关系 → 失败
```

- [ ] **Step 4: 编写关系规则回归用例**

用项目当前页面作为固定回归样本，但测试验证的是关系规则，不写"某页必须三角构图"之类页面特例。

- [ ] **Step 5: 运行定向审计**

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
- Consumes: 原始 `content_units`、`source_refs`、`semantic_graph.nodes`（升级后的对象数组）和 `grouping_decisions`。
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

- [ ] **Step 4: 增加回归测试**

验证多项建设基础压缩为若干组时每个源节点都有去向；验证收益分配类页面不能把定价依据、成本扣除、分配比例和动态调整无理由合并成普通三步流程。

### Task 4: 将风格适配器与结构编译器解耦

**Files:**
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/visual_prompt_consumer.py`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/page_artifact_spec.py`
- Modify: `/Volumes/DOC/CyberPPT/cyberppt/commands/visual_structure_stage.py`
- Modify: `/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/prompt-assembly.md`
- Test: `/Volumes/DOC/CyberPPT/tests/test_imagegen_no_visual_structure.py`

**Interfaces:**
- Consumes: 审计通过的 `deck-visual-spec.json`、锁定文字和外部 Style lock；Task 0 记录的现状基线。
- Produces: 风格变体 Prompt；不改变 `semantic_graph.topology`、`semantic_graph.primary_relation`、`semantic_graph.focus_node`、`semantic_graph.nodes`、`semantic_graph.edges`、`structural_decision.reading_sequence`、`structural_decision.text_bindings`。

- [ ] **Step 1: 定义风格适配输入边界**

风格适配器只能写入颜色、材质、字体、线条、光影、场景政策和装饰政策；不得写入新的业务节点、关系边、页面使命或结论。

- [ ] **Step 2: 若 Task 0 发现既有违规写入，先修复再加测试**

如果 Task 0 Step 2 发现 Style09/Style10 当前已经在写结构字段，先在本步骤移除这些写入路径，确保下一步的不变测试是在干净状态下新增的，而不是靠新测试意外发现旧代码问题。

- [ ] **Step 3: 增加结构字段不变测试**

对同一 `deck-visual-spec.json` 分别注入 Style09 和 Style10，断言以下字段完全一致：

```text
semantic_graph.topology
semantic_graph.primary_relation
semantic_graph.focus_node
semantic_graph.nodes
semantic_graph.edges
structural_decision.reading_sequence
structural_decision.text_bindings
```

- [ ] **Step 4: 阻断旁路 Prompt**

当正式视觉结构审计未通过时，Style 适配器不得把 `workbench/prompts/imagegen/send` 下的独立重组文件标记为正式送图输入。

- [ ] **Step 5: 运行 ImageGen 结构隔离测试**

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
- Consumes: 当前 Skill、Prompt builder、Validator、Schema 和 Style lock 的哈希（含 Task 1 扩展后的 Schema 哈希）。
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

### Task 6: 运行全套回归并抽样复核（不涉及历史项目产物重建）

**Files:**
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_stage.py`
- Test: `/Volumes/DOC/CyberPPT/tests/test_visual_structure_contract.py`
- Test: `/Volumes/DOC/CyberPPT/tests/test_imagegen_no_visual_structure.py`

- [ ] **Step 1: 运行全套相关测试**

```bash
cd /Volumes/DOC/CyberPPT
.venv/bin/python3 -m pytest tests/test_visual_structure_stage.py tests/test_visual_structure_contract.py tests/test_imagegen_no_visual_structure.py -q
```

验证内容包括：结构 Schema、关系保真、分组合并、风格隔离、回执哈希、Prompt 新鲜度和 ImageGen 入口隔离，全部通过。

- [ ] **Step 2: 用 fixtures/example 页面做结构类型抽样**

使用 `vendor/skills/ppt-visual-structure-designer/assets/example-page-spec.json`、`example-deck-spec.json` 及 `domain-neutral-structure-fixtures.json` 中已有的样例，对每种 `topology` 类型至少跑一次审计，确认新规则对因果、分层、流程、闭环、治理、收益分配等类型分别给出正确通过/阻断结果。若确实需要在某个正式项目上验证真实效果，由你另行指定项目和时机，不在本计划默认范围内。

## 验收标准

1. 所有内容页均有可审计的 `semantic_graph.topology`、`focus_node`、`nodes` 和 `edges`，且这是页面拓扑与关系的唯一权威来源——`structural_decision` 中不出现同名或同语义字段。
2. 因果、分层、流程、闭环、治理和收益分配页面不能退化为无关系的等权卡片集合。
3. 每个源内容单元都有独立呈现、合并、讲解层或不上屏的明确去向。
4. 高风险内容合并会被阻断或进入人工复核，不会静默丢失主体、阶段、责任或边界。
5. 页面使命、核心判断和视觉焦点不一致时，视觉结构审计失败；`semantic_graph.focus_node` 与 `structural_decision.semantic_focus.ref` 不一致时审计失败。
6. Style09 与 Style10 生成的 `semantic_graph`/`structural_decision` 结构字段完全一致，仅风格字段发生变化。
7. 视觉结构回执过期时，正式 Prompt 不会被重建，旁路 Prompt 不会被视为正式输入。
8. `test_visual_structure_stage.py`、`test_visual_structure_contract.py`、`test_imagegen_no_visual_structure.py` 全部通过，且新增了"`structural_decision` 出现 topology/primary_relation/nodes/edges 即失败"的回归用例。

## 风险与控制

- 风险：`semantic_graph.nodes`/`edges` 形状升级（字符串数组 → 对象数组）导致所有既有页面数据在下次执行 Stage 02 前不可读。控制：不做兼容层，明确本计划不覆盖历史项目数据升级；仅保证新执行的 Stage 02 输出符合新 Schema。
- 风险：关系边过度结构化，限制视觉设计自由度。控制：约束业务拓扑和语义关系，不固定具体图形、位置和材质。
- 风险：风格适配器再次承担页面设计。控制：Task 0 先摸清现状，Task 4 增加结构字段不变测试和 ImageGen 入口隔离门禁。
- 风险：合并审计误把正常的内容归并判为错误。控制：允许作者提供合并理由和风险等级，对高风险项人工复核，不对所有归并一律阻断。
- 风险：新增的 `topology`/`focus_node` 审计与既有 `_audit_focus_competition`/`_audit_relationship_coverage` 逻辑重复或冲突，产生两套互相矛盾的判断。控制：Task 2 Step 1 强制先读现有函数覆盖范围，只在空白处新增，不重复实现。
