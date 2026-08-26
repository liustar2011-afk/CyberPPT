# CyberPPT Stage 01 源材料到页面脚本开发计划

- 日期：2026-08-25
- 依据：[源材料到页面脚本代码链路分析报告](stage01-source-to-page-script-code-chain-analysis-20260825.md)
- 主要回归项目：`projects/ai_power_training_business_feasibility`
- 重点回归页面：P04
- 适用范围：Source Foundation、业务语义理解、页面规划、Handoff、写前预检、单页脚本审计

## 实施状态（2026-08-26）

| 工作包 | 状态 | 落地结果 |
|---|---|---|
| WP0 | 已完成 | required、legacy、跨页多职责、peer set、写前阻断等回归用例已建立 |
| WP1 | 已完成 | `evidence_roles` v2、受控词表、逐事实一次消费和 author gate 已落地 |
| WP2 | 已完成 | required 模式按页面消费合同确定性投影，Source Truth 保持页面中立 |
| WP3 | 已完成 | P04 专属词表已删除，preflight 输出通用语义拓扑并在合同缺失时阻断写作输入 |
| WP4 | 已完成 | lint 按 group、peer set、主链顺序和 anti-merge 规则核对页面执行结果，状态完成三级划分 |
| WP5 | 已完成 | 表格 trace parent 与稳定 cell child 已落地，语义层新增原子性和诊断 resolution 检查 |
| WP6 | 部分完成 | 主流程和相关 Skill 已更新；当前项目 P04 已迁移为 v2 advisory 并通过正式 Handoff。其余 12 个内容页等待逐页作者判断后再切换整套 required |

当前项目没有批量套用默认页面职责。其余页面仍使用 legacy 记录，validator 在 advisory 模式下逐页发出迁移 warning。该处置保留了“页面消费语义由作者产生”的架构条件，并避免用自动规则替代页面取舍。

实施与验证详情见：[Stage 01 页面消费语义改造实施报告](stage01-page-consumption-implementation-report-20260826.md)。

## 一、结论与技术判断

技术判断：`SUPPORT WITH CONDITIONS`

将页面脚本治理前移到写作之前，能够直接降低错分组、全量上屏、边界混淆和写后返工。现有代码和提交历史已经证明 preflight 具备承接事前约束的运行入口；当前缺口集中在正式上游生产者、页面级语义合同和兼容迁移。

落地必须满足五项条件：

1. 页面消费语义由 `ppt-outline-planning` 的作者合同产生。
2. Source Truth 只保留事实固有语义，不保存页面专属职责、页面可见性和页面分组。
3. Handoff 只执行 ID 映射、字段映射和兼容投影。
4. preflight 输出机器可验证的页面拓扑，不生成具体业务标题，不内置项目词汇。
5. 新项目启用强校验，旧项目保留显式兼容入口；兼容入口只提供迁移诊断。

### 反例验证

如果直接在 preflight 增加严格门禁，现有项目没有正式的页面消费字段，P04 等高密度页面会整体阻断。此时规则前移只改变了报错时间，页面职责仍由下游猜测。

如果把 `argument_function`、`decision_scope`、`visibility` 写入全局 Source Truth，同一事实跨页承担不同职责时会发生覆盖冲突。现有 `build_projection()` 已经把源论点节点和页面节点共同写入 `semantic_node_ids`，并用首个节点角色产生全局 `argument_duty`；继续扩展全局页面字段会扩大这一冲突。

因此，本计划采用“page plan 产生页面消费语义—Handoff 确定性投影—preflight 形成写前拓扑—lint 核对执行结果”的单向链路。

## 二、当前代码基线

### 2.1 已具备的基础

- `authoring-spec.json` 已经是 `author_edited` 的正式作者输入，生成器能够把作者字段写入 `page-plan.json`。
- `evidence_roles` 已支持对象列表形式，当前 validator 和 Handoff 已有规范化入口。
- `build_page_preflight_from_contract()` 已被 `prepare_page_script_input()` 和 CLI 共同消费，适合承接写前语义拓扑。
- `content_units` 已进入页面脚本覆盖审计、Stage 02 handoff 和页面 lint，具备端到端消费链。
- `excluded_from_onscreen` 已在 page plan 层存在，当前 Handoff 会读取 source refs。

### 2.2 已确认的缺口

| 层级 | 当前行为 | 直接风险 |
|---|---|---|
| Fact base | 表格按整行生成 `table_record` | 一条记录混合阶段、金额、投入方式和收费条件 |
| Page plan | `evidence_roles` 只回答证据角色 | 无法表达事实在当前页面的用途、时域、可见性和拓扑位置 |
| Author gate | 提供 authoring spec 即可把根状态设为 `author_edited` | 页面取舍字段完整性仍不足 |
| Source projection | `_page_fact_usage()` 用页面 importance 批量提升事实优先级 | 核心页上的全部事实容易成为 P0 |
| Source Truth | `build_projection()` 把页面节点和源论点节点合并后生成全局 duty | 页面职责污染事实固有语义 |
| Outline projection | `onscreen_required` 由全局 priority、role 和 structural duty 共同推导 | 页面作者的可见性取舍无法完整生效 |
| Exclusion projection | `excluded_from_onscreen` 最终退化为 `detail_refs` | 原因和目标承载层丢失 |
| Preflight | `_ARGUMENT_FUNCTION_GROUPS` 内置 P04 业务分类和中文标题 | 对其他项目缺乏通用性 |
| Lint | value reference 与 gate 同页时整页跳过模块维度检查 | 同页其他真实 peer modules 失去检查 |
| Page lint status | 只有 error 触发 `rewrite_required` | 多项高信号 warning 仍返回 `passed` |

## 三、目标架构

```text
source.md / structure / fact base
                │
                ▼
normalized facts + relations + argument chain
                │  事实固有语义
                ▼
authoring spec → page-plan.json
                │  页面消费语义唯一权威
                ▼
CyberPPT Handoff
                │  确定性映射
                ▼
outline.json / content_units / semantic_topology
                │
                ├── preflight：写前结构门禁
                └── page lint：写后合同核对
```

权威边界：

| 信息 | 权威层 | 下游处理 |
|---|---|---|
| 原文、来源位置、事实状态、事实固有限定 | Source Foundation / semantic outputs | 只读消费 |
| 页面使命、核心判断、证据角色、用途、时域、可见性、拓扑位置 | page plan | Handoff 原样投影 |
| ST ID、CyberPPT page ID、content unit ID | Handoff | 机械生成 |
| 页面分组标题、短语表达、完整文字稿 | page script | 受 preflight 约束 |
| 覆盖、归属、结构执行结果 | lint | 核对合同 |

## 四、页面消费语义合同

### 4.1 选择现有 `evidence_roles` v2

分析报告提出了独立 `evidence_consumption` 字段。代码核验后，本计划采用更小的兼容改动：扩展现有列表形态的 `evidence_roles`，形成 v2 记录。现有 dict 形态继续作为 legacy 输入；v2 是新作者流程的唯一页面消费语义输入。

这样可以复用现有 `_role_map()`、`_normalize_evidence_roles()`、authoring spec 和 Handoff 入口，并减少平行字段同步。

### 4.2 v2 记录示例

```json
{
  "role": "claim",
  "source_refs": ["NF-0011"],
  "page_function": "value_reference",
  "relation_to_proposition": "supports",
  "decision_scope": "future_reference",
  "visibility": "supporting_onscreen",
  "topology_role": "satellite",
  "group_id": "long_term_value",
  "peer_set_id": null,
  "sequence_index": null,
  "rationale": "用于说明长期培育空间，不承担首期收入承诺"
}
```

### 4.3 字段约束

| 字段 | 必填条件 | 建议枚举或规则 |
|---|---|---|
| `role` | 全部 evidence | 复用 `claim/reason/instance/boundary/trace_only` |
| `source_refs` | 全部 evidence | v2 记录不得混合 normalized fact、relation 和 argument node 三种 ID 类型 |
| `page_function` | 直接 normalized fact | `claim_basis/mechanism/action/output/metric/value_reference/gate_condition/operating_boundary/deferred_constraint/example/trace` |
| `relation_to_proposition` | 直接 normalized fact | `supports/explains/constrains/gates/contextualizes/illustrates/traces` |
| `decision_scope` | 直接 normalized fact | `current/future_reference/future_gate/deferred/cross_phase/timeless` |
| `visibility` | 直接 normalized fact | `primary_onscreen/supporting_onscreen/prose_only/notes_only/trace_only` |
| `topology_role` | 直接 normalized fact | `main_chain/satellite/boundary/context/trace` |
| `group_id` | 上屏事实 | 稳定机器 ID；不保存最终中文标题 |
| `peer_set_id` | 需要同维比较时 | 同一 peer set 才接受模块维度一致性检查 |
| `sequence_index` | 存在真实顺序时 | 正整数；其余情况为空 |
| `rationale` | prose/notes/trace 或易混淆事实 | 说明页面取舍和边界 |

### 4.4 合同不变量

1. 每个页面直接 normalized fact 恰好命中一条 v2 消费记录。
2. 同一 fact 在不同页面可拥有不同 `page_function`、`decision_scope` 和 `visibility`。
3. `visibility` 独立决定上屏责任；页面 importance 不参与逐事实可见性推导。
4. `topology_role=main_chain` 只在来源关系或页面主论证链存在方向时使用。
5. `peer_set_id` 只标记可按共同维度扫描的模块。
6. v2 模式下，`excluded_from_onscreen` 由 visibility 和 rationale 生成兼容投影；validator 校验两者一致。
7. Handoff 不新增 `page_function`、group、peer set 和业务标题。

### 4.5 兼容模式

在 page plan 根节点增加 `page_consumption_contract_mode`：

- 缺失或 `legacy`：现有项目继续运行；preflight 输出迁移诊断，不宣称语义合同完整。
- `advisory`：生成 v2 诊断，缺失字段以 warning 呈现。
- `required`：新 authoring spec 默认值；字段不完整时阻断 `author_edited` 和 Handoff。

不增加独立 CLI 严格开关。门禁强度随权威 page plan 一起版本化，避免同一输入因命令参数不同产生不同结论。

## 五、开发工作包

### WP0：建立失败基线和迁移护栏

目标：先把当前缺陷固定为可重复测试，保护旧项目运行路径。

改动范围：

- `tests/test_ppt_outline_generator.py`
- `tests/test_ppt_outline_planning_defaults.py`
- `tests/test_cyberppt_handoff_projection.py`
- `tests/test_source_foundation_integration.py`
- `tests/test_preview_page_anchors_command.py`
- `tests/test_script_quality_contract.py`
- 必要时新增最小 P04 语义 fixture；fixture 只保留触发问题的事实和关系。

新增测试：

1. 旧 dict `evidence_roles` 在 legacy 模式继续通过。
2. required 模式缺少 v2 字段时阻断 author gate。
3. 同一事实跨页拥有不同 page function，重跑 Handoff 后保持差异。
4. value reference、future gate、current boundary、deferred constraint 四种 P04 职责保持分离。
5. 同页包含 value reference 和 gate 时，其他 peer set 的维度错误仍被发现。
6. Handoff 重跑不依赖手工修改后的 `outline.json` 或 `source-truth.json`。

验收：上述测试在功能实现前稳定失败，legacy 测试保持通过。

建议提交：`test(stage01): lock page-consumption regressions`

### WP1：升级 page plan 作者合同

目标：让页面作者在 page plan 阶段完成逐事实取舍。

改动范围：

- `.agents/skills/ppt-outline-planning/ppt_outline_planning/authoring_spec.py`
- `.agents/skills/ppt-outline-planning/ppt_outline_planning/generate.py`
- `.agents/skills/ppt-outline-planning/ppt_outline_planning/authoring.py`
- `.agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py`
- `.agents/skills/ppt-outline-planning/ppt_outline_planning/render.py`
- `.agents/skills/ppt-outline-planning/references/authoring-spec.md`
- `.agents/skills/ppt-outline-planning/references/outline-contract.md`
- `.agents/skills/ppt-outline-planning/SKILL.md`

实现任务：

1. authoring spec schema 升级，默认生成 `page_consumption_contract_mode=required`。
2. 准备模板为每页列出 direct facts、relations 和 argument nodes，保留作者填写区域。
3. 新增 v2 evidence record validator 和受控词表。
4. 校验 direct fact 一次且仅一次消费、ID 类型不混合、visibility 与 topology 合法组合。
5. 校验高密度页面的 deletion test 与 visibility rationale。
6. 只有合同完整、判断推导完整、页面取舍完整时设置 `author_edited`。
7. Markdown 审阅稿展示每页“主链、卫星、边界、正文保留、追溯保留”，供人工审核。

验收：

- P04 的直接 facts 全部拥有逐事实页面职责。
- 全部 direct facts 填入 claim 会触发 `evidence_role_collapse` 或等价错误。
- 空排除列表且全部 evidence 可见时必须提供整体可见性理由。
- 旧 authoring spec 只在 legacy 模式运行。

建议提交：`feat(outline): author page-scoped evidence consumption`

### WP2：修复 Handoff 投影语义

目标：从 page plan 机械产生每页 content units，消除全局职责污染。

改动范围：

- `.agents/skills/cyberppt-handoff/cyberppt_handoff/source_projection.py`
- `.agents/skills/cyberppt-handoff/cyberppt_handoff/project.py`
- `.agents/skills/cyberppt-handoff/cyberppt_handoff/outline_projection.py`
- `.agents/skills/cyberppt-handoff/cyberppt_handoff/validate.py`
- `.agents/skills/cyberppt-handoff/references/handoff-contract.md`
- `.agents/skills/cyberppt-handoff/tests/`
- `tests/test_cyberppt_handoff_projection.py`
- `tests/test_source_foundation_integration.py`

实现任务：

1. 新增保留 v2 记录的规范化函数，避免 `_normalize_evidence_roles()` 只留下 role 和 refs。
2. required 模式下，content unit 的 `argument_function`、`decision_scope`、`visibility`、`topology_role`、`group_id`、`peer_set_id` 全部来自 page plan。
3. `onscreen_required` 只由 visibility 映射；`full_prose_required` 由 visibility 和 role 映射。
4. content unit priority 由逐事实消费记录映射。`_page_fact_usage()` 只服务 legacy 路径，required 模式不再用页面 importance 批量提升 Source Truth。
5. 页面 argument duty 优先读取页面 argument chain 和 topology，required 模式不读取 Source Truth 的全局页面职责。
6. `excluded_from_onscreen` 保留 refs、reason 和 target layer；`detail_refs` 继续作为兼容索引。
7. `authority-map.json` 记录 page plan evidence record 到 content unit 的 ID 映射与输入哈希，不保存新业务语义。
8. 缺失 v2 合同时返回明确上游错误，required 模式不填默认 page function。

验收：

- 同一 ST record 在两页生成不同 page function 和 visibility。
- P04 不再因为页面 importance 产生 10 个 P0 onscreen units。
- Handoff 连续运行两次产物一致。
- page plan 改变一个 fact 的 visibility 后，只影响消费该记录的页面投影。

建议提交：`refactor(handoff): project page consumption deterministically`

### WP3：把 preflight 升级为语义拓扑门禁

目标：作者落笔前获得可执行的页面结构合同。

改动范围：

- `cyberppt/commands/preview_page_anchors.py`
- `cyberppt/commands/prepare_stage01_input.py`
- `tests/test_preview_page_anchors_command.py`
- `tests/test_prepare_stage01_input.py`

删除内容：

- `_ARGUMENT_FUNCTION_GROUPS`
- `_ARGUMENT_FUNCTION_GROUP_ORDER`
- P04 专属的中文分组名和 reference/gate 专属提示句

正式输出：

```text
contract_status
page_proposition
main_chain_nodes / main_chain_edges
satellite_nodes
boundary_nodes
context_nodes
group_contracts
peer_sets
anti_merge_edges
visibility_budget
prose_only_units / trace_only_units
unresolved_semantic_contracts
```

规则：

1. `main_chain` 只有在真实关系或 sequence index 存在时生成边。
2. group 只输出稳定 ID、成员、职责和来源，不生成显示标题。
3. 不同 decision scope、不同 gate/boundary 关系可形成 `anti_merge_edges`。
4. peer sets 完全来自 page plan 显式声明。
5. required 模式发现 unresolved contract 时，`prepare-page-script-input` 阻断写作输入生成。
6. legacy 模式只输出兼容诊断和迁移建议。

验收：

- 无真实顺序的页面不返回 chain 型结构。
- P04 的长期价值参考、后续研究门槛、首期经营边界和后置约束形成不同拓扑位置。
- 另一历史项目运行时不出现“首期验证”“长期培育”等项目词汇。

建议提交：`feat(preflight): emit source-neutral semantic topology`

### WP4：让 page lint 核对拓扑执行结果

目标：写后审计验证作者是否执行事前合同，保留格式和来源底线。

改动范围：

- `cyberppt/script_quality/parsing.py`
- `cyberppt/script_quality/onscreen.py`
- `cyberppt/script_quality/source_coverage.py`
- `cyberppt/script_quality/presentation.py`
- `cyberppt/commands/page_lint.py`
- `tests/test_page_lint_command.py`
- `tests/test_script_quality_contract.py`
- `.agents/skills/cyberppt-write-single-page/references/page-script-contract.md`

实现任务：

1. 复用现有页面 Markdown 的 `证据映射` 字段承载 group/module 到 source refs 的映射。
2. 解析 group ID、module ID 和 source refs，核对 main chain、satellite、boundary 与 anti-merge 约束。
3. 模块维度检查只比较同一 `peer_set_id` 的模块。
4. 删除 value reference + gate 同页时整页跳过的逻辑。
5. 明显超载、多条 P0/P1 缺口、主链缺失、anti-merge 冲突形成 error 或高信号 warning。
6. `page_lint` 状态升级为 `passed`、`passed_with_warnings`、`rewrite_required`。
7. 关键词启发式只保留语言与格式检查，业务职责以合同字段为准。

验收：

- P04 的 reference/gate 错分组由拓扑合同发现。
- 其他 peer set 的维度不一致仍能被报告。
- 370/268 字等明显超载不再返回普通 `passed`。
- 没有语义冲突的非同级模块不触发维度一致性错误。

建议提交：`feat(lint): verify authored pages against semantic topology`

### WP5：治理源事实原子性

目标：减少下游作者面对的复合事实，保证业务对象、阶段、条件和数值可单独消费。

本工作包安排在页面消费合同稳定之后。它会引入 source assertion 子 ID 和项目迁移，影响面高于 page plan 字段升级。

改动范围：

- `.agents/skills/source-structure-factbase/source_structure_factbase/factbase.py`
- `.agents/skills/source-structure-factbase/references/fact-base-contract.md`
- `.agents/skills/business-semantic-understanding/business_semantic_understanding/validate.py`
- `.agents/skills/source-structure-factbase/SKILL.md`
- 新增 `tests/test_source_structure_factbase.py`
- 对应业务语义 Skill 文档和测试
- Source Foundation 集成测试

实现任务：

1. 保留现有表格整行 parent record，作为兼容和追溯记录。
2. 对所有满足规则的内容单元格生成候选子命题，ID 采用 `parent-cell-segment` 稳定坐标。
3. 子命题保存 `parent_fact_id`、`cell_index`、`header`、`segment_index` 和原 source ref。
4. 表头、引用标记和纯登记字段不进入 proposition statement。
5. normalized fact validator 增加多阶段、多条件、多动作、表格管道残留和 scope shift 诊断。
6. 一个 layer-two assertion 可支持多个 normalized facts；每个 normalized fact 保持独立 statement 和 evidence。
7. `mixed_level`、`scope_shift`、`unsupported_jump` 等诊断进入现有 semantic report，并要求明确 resolution。

禁止实现：

- 只对“首期投入”或其他业务关键词写专用拆分分支。
- 重新顺序编号全部旧 fact IDs。
- 自动改写已批准的 normalized facts 和 page plan。

验收：

- “首期投入”类复合表格能够拆出现金边界、人员投入和收费条件。
- “长期空间”能够区分市场测算、页面用途和禁止推导。
- 父级 ID 保持可追溯，旧项目不发生全量 ID 断裂。
- 页面 content unit 不携带 Markdown 表格管道文本。

建议提交：`feat(foundation): emit stable atomic table propositions`

### WP6：跨项目迁移与规则收敛

目标：证明新合同适用于当前项目和历史项目，随后收紧默认门禁。

任务：

1. 迁移当前 AI+电力教育培训项目的 page plan 到 required 模式。
2. 选择至少两个历史项目：一个标准 Source Foundation 项目、一个 legacy Stage 01 项目。
3. 比较迁移前后的 page count、direct fact coverage、P0/P1 数量、onscreen 数量和 lint 状态。
4. required 模式稳定后，新项目默认 required；legacy 入口继续保留一个发布周期。
5. 下一个发布周期删除 legacy 中的业务语义猜测，只保留结构兼容。
6. 更新主流程、三个相关 Skill 和人工审核文档。

验收：

- 三类项目全部通过正式 Handoff 和 Stage 01 审计。
- 新项目 page plan 的 direct facts 具备 100% v2 消费记录。
- 生产代码中不再存在项目专属业务分组词表。
- 兼容模式使用情况可从现有报告字段识别。

建议提交：`chore(stage01): migrate projects and require consumption contract`

## 六、依赖顺序与里程碑

```text
M0 失败基线
 │
 ▼
M1 page plan v2 作者合同
 │
 ▼
M2 Handoff 确定性投影
 │
 ├──────────────┐
 ▼              ▼
M3 preflight    M4 lint
 │              │
 └──────┬───────┘
        ▼
M5 源事实原子性
        │
        ▼
M6 跨项目迁移
```

建议按 6—10 个工作日拆分：

| 里程碑 | 建议工期 | 可交付结果 |
|---|---:|---|
| M0 | 0.5—1 天 | 失败用例和 legacy 护栏 |
| M1 | 1.5—2 天 | v2 authoring spec、validator、审阅稿 |
| M2 | 1.5—2 天 | Handoff 投影和幂等回归 |
| M3 | 1—1.5 天 | 通用 semantic topology preflight |
| M4 | 1—1.5 天 | topology-aware page lint |
| M5 | 1.5—2 天 | 通用表格原子化和语义诊断 |
| M6 | 1 天 | 三类项目迁移报告和默认门禁调整 |

工期以现有测试速度和历史项目迁移量为变量；M5 完成试点后更新剩余估算。

## 七、测试矩阵

| 测试层 | 必测内容 | 核心断言 |
|---|---|---|
| 单元：page plan | v2 schema、枚举、不变量 | 每个 direct fact 恰好一条消费记录 |
| 单元：Handoff | v2 映射、legacy fallback | required 模式无推断，legacy 模式可运行 |
| 单元：preflight | topology、peer set、anti-merge | 不输出业务标题，不制造顺序 |
| 单元：lint | evidence map、peer set、状态分级 | 合同冲突可定位到 group 和 source refs |
| 集成：正式 Handoff | normalized facts → page plan → outline | 重跑幂等、职责不漂移 |
| 回归：P04 | 四类易混淆事实 | 用途、门槛、当前边界、后置约束分离 |
| 回归：历史项目 | Source Foundation + legacy | 无专属词汇泄漏，旧路径可迁移 |
| 全量 | 仓库测试 | 无新增失败，区分既有失败 |

P04 必测语义：

| 源材料内容 | 目标页面职责 | 禁止升级 |
|---|---|---|
| `0.5—1.7亿元/年` | `value_reference` / `future_reference` | 首期收入目标、后续研究条件 |
| 付费交付、复制、核算条件 | `gate_condition` / `future_gate` | 当前经营结果 |
| 首期投入和产出按验证性质管理 | `operating_boundary` / `current` | 后续判断条件 |
| 首期允许收入较小，重点验证商业闭环 | `operating_boundary` / `current` | 收入规模承诺 |
| 固定平台、大额采购等事项 | `deferred_constraint` / `deferred` | 首期实施动作 |

## 八、验证命令

运行前确认仓库解释器：

```bash
test -x .venv/bin/python3
.venv/bin/python3 -c "import sys; print(sys.executable)"
```

定向测试：

```bash
.venv/bin/python3 -m pytest \
  tests/test_ppt_outline_generator.py \
  tests/test_ppt_outline_planning_defaults.py \
  tests/test_cyberppt_handoff_projection.py \
  tests/test_source_foundation_integration.py \
  tests/test_preview_page_anchors_command.py \
  tests/test_prepare_stage01_input.py \
  tests/test_page_lint_command.py \
  tests/test_script_quality_contract.py
```

每个工作包合并前再运行：

```bash
.venv/bin/python3 -m pytest
```

项目级验证必须从权威 semantic outputs 和 page plan 重新执行 Handoff；删除或忽略手工回填的 projection 字段后复跑，检查输出幂等性、权威映射和 P04 预检结果。

## 九、完成定义

全部条件满足后，Stage 01 页面消费语义改造才算完成：

1. 新 authoring spec 默认 required 模式。
2. direct normalized facts 的页面消费记录覆盖率达到 100%。
3. Source Truth 不保存页面专属 page function、visibility、group 和 peer set。
4. Handoff required 模式不推导页面业务职责。
5. preflight 不包含项目专属词表和中文标题模板。
6. page lint 依据 peer set 和 evidence map 核对页面执行结果。
7. P04 五组反例全部通过。
8. 两个历史项目完成兼容或迁移验证。
9. 定向测试和全量测试通过。
10. 主流程文档、Skill 文档和人工审核稿同步更新。

## 十、风险与控制

| 风险 | 触发点 | 控制措施 |
|---|---|---|
| 旧项目被新 validator 阻断 | WP1 | 根级 contract mode；缺失字段进入 legacy |
| 新旧字段形成双权威 | WP1/WP2 | v2 只 author 一处；legacy 字段由生成器投影并校验一致 |
| Source Truth schema 破坏下游 | WP2 | required 模式绕开全局页面 duty；旧字段先保留兼容读取 |
| 表格子事实造成 ID 大面积变化 | WP5 | 保留 parent ID，新增坐标型 child ID |
| preflight 继续替作者写标题 | WP3 | 只输出 group ID、职责、成员和关系 |
| lint 过度阻断 | WP4 | peer set 限定比较范围；warning 分级；反例测试 |
| 迁移时手工补丁被当作权威 | WP2/WP6 | 从正式 Foundation 和 page plan 重跑，检查幂等和 authority map |

## 十一、实施起点

第一批只执行 WP0 和 WP1：先把 P04 反例、legacy 兼容和跨页多角色固定为测试，再升级作者合同。WP1 通过后进入 Handoff 改造。该顺序能够让每个提交拥有清晰失败原因和独立回滚边界。

M1 评审重点：字段是否足够通用、作者填写成本是否可控、旧项目是否保持运行。M2 评审重点：Handoff 是否保持纯投影、Source Truth 是否恢复事实级职责边界。M3/M4 评审重点：事前拓扑和事后核对是否使用同一份 page plan 合同。
