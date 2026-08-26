# CyberPPT 源材料到页面脚本代码链路分析与优化建议

- 报告日期：2026-08-25
- 分析范围：源材料转换、事实基础、业务语义理解、PPT 页面规划、CyberPPT Handoff、页面写前预检、页面脚本写作与页面审计
- 当前项目：`projects/ai_power_training_business_feasibility`
- 对照项目：
  - `projects/ai-power-education-training-business-feasibility-20260822`
  - `projects/power-data-infrastructure-cooperation-v16-20260815-foundation`
- 分析性质：代码与项目产物只读审查

## 一、执行摘要

CyberPPT Stage 01 已经具备清晰的工程骨架：源材料解析、事实追溯、语义产物、页面计划、确定性 Handoff、写前预检和写后审计均有正式入口。当前主要问题集中在“页面如何消费事实”的语义合同上。

现有系统能够稳定回答“内容来自哪里”，对以下问题的回答仍不稳定：

- 一条事实为什么进入当前页面；
- 该事实对页面命题承担什么作用；
- 该事实属于当前决策、长期参考、后续门控还是经营边界；
- 该事实是否必须上屏；
- 该事实应与哪些内容形成同级关系、主从关系或卫星关系。

当前项目 P04 暴露出完整的故障传播链：源材料已经区分长期空间、后续放大条件和首期管理口径；语义诊断也提示需要区分长期前景与当前决策依据；页面计划仍把 10 条直接事实全部归为 `claim`；Handoff 又把它们提升为 P0、赋予同一结构职责并全部标记为必须上屏；页面预检最终只能通过下游硬编码分类进行补救。

总体评价如下：

| 能力层 | 评价 | 说明 |
|---|---:|---|
| 来源追溯 | 8/10 | 事实、证据坐标和 ID 映射较完整 |
| 事实原子化 | 5/10 | 正文可按标点拆分，表格整行仍会形成复合事实 |
| 业务语义建模 | 4/10 | 关系图稀疏，论点节点跨度过大，诊断未进入下游门禁 |
| 页面作者化 | 3/10 | `author_edited` 可在缺少真实取舍的情况下通过 |
| Handoff 投影 | 5/10 | 来源映射确定性较强，页面职责和可见性存在错误放大 |
| 写前预检 | 4/10 | 能暴露锚点与关系，近期分类依赖下游硬编码 |
| 写后审计 | 6/10 | 格式和覆盖检查较丰富，高信号 warning 仍可整体通过 |

首要优化方向是：在权威 `page-plan.json` 中建立页面级证据消费语义，并由 Handoff 机械投影到页面写作合同。继续增加下游关键词、中文分组名和全页审计豁免，无法形成稳定的跨项目能力。

## 二、正式代码链路

仓库正式 Stage 01 路线为：

```text
源材料
  → 标准化 Markdown
  → structure.json / fact-base.json
  → normalized-facts.json / concept-base.json
  → relation-graph.json / argument-chain.json
  → deck-brief.json / page-plan.json
  → CyberPPT Handoff
  → source-truth.json / outline.json
  → page-preflight / prepare-page-script-input
  → 页面 Markdown
  → page-lint / script-audit
```

权威关系如下：

- `normalized-facts.json`、`concept-base.json`、`relation-graph.json`、`argument-chain.json`、`deck-brief.json` 和 `page-plan.json` 为上游权威。
- `semantic-argument-model.json`、`source-truth.json` 和 `outline.json` 为兼容投影。
- 投影文件不得形成第二套业务语义权威。

主流程依据见 [CYBERPPT_WORKFLOW.md](CYBERPPT_WORKFLOW.md)。

## 三、已验证事实

### 3.1 当前项目语义基础

当前项目包含：

- 114 条 normalized facts；
- 5 条语义关系；
- 7 条事实进入关系图；
- 15 个 source-chain 节点；
- 6 个 reconstructed-chain 节点；
- 最大 source-chain 节点覆盖 15 条事实；
- 最大 reconstructed-chain 节点覆盖 38 条事实；
- 1 条语义诊断。

以上数据来自：

- [normalized-facts.json](../projects/ai_power_training_business_feasibility/workbench/source-foundation/semantic/AI+电力教育培训业务商业可行性分析报告0819_processed/normalized-facts.json)
- [relation-graph.json](../projects/ai_power_training_business_feasibility/workbench/source-foundation/semantic/AI+电力教育培训业务商业可行性分析报告0819_processed/relation-graph.json)
- [argument-chain.json](../projects/ai_power_training_business_feasibility/workbench/source-foundation/semantic/AI+电力教育培训业务商业可行性分析报告0819_processed/argument-chain.json)

### 3.2 当前项目页面计划

当前项目 13 个内容页具有以下特征：

- 109 条直接 normalized fact 引用全部归入 `claim`；
- `boundary` 为 0；
- `trace_only` 为 0；
- 13 页的 `excluded_from_onscreen` 全部为空；
- 页面 argument chain 直接引用 26 条 normalized facts；
- 83 条直接页面事实没有被页面 argument chain 的 `normalized_fact_ids` 直接引用。

对应权威产物为 [page-plan.json](../projects/ai_power_training_business_feasibility/workbench/outline/page-plan.json)。

### 3.3 当前项目 Handoff 结果

当前投影后的 13 个内容页共有 109 个内容单元：

- 106 个内容单元为 P0；
- 109 个内容单元全部 `onscreen_required=true`；
- 单页最多 14 个内容单元；
- P04 有 10 个内容单元，10 个均为 P0，10 个均要求上屏。

对应投影产物为 [outline.json](../projects/ai_power_training_business_feasibility/workbench/stages/01-analysis/outline.json)。

### 3.4 历史项目对照

| 项目 | 内容页 | 直接事实 | 页面链直接引用 | 直接事实未被页面链直接引用 | 不上屏取舍 |
|---|---:|---:|---:|---:|---:|
| 当前 AI 电力培训项目 | 13 | 109 | 26 | 83 | 0 页 |
| 20260822 AI 电力培训项目 | 13 | 123 | 123 | 0 | 13 页 |
| v16 Foundation 项目 | 23 | 327 | 191 | 136 | 23 页 |

历史项目说明两个问题长期并存：

1. 页面证据职责和不上屏取舍的作者化质量在不同项目之间波动较大；
2. 页面链与直接事实之间缺少稳定的消费闭环，部分项目使用泛化链条实现形式覆盖，部分项目保留大量链外事实。

## 四、P04 故障传播分析

### 4.1 源材料表达

源材料“核心结论”部分明确包含以下不同性质的信息：

| 来源事实 | 源材料含义 | 正确语义定位 |
|---|---|---|
| NF-0006 | 紫金云现有能力可向培训和教学转化 | 能力基础 |
| NF-0007 | 轻量投入、快速验证、成熟放大 | 首期验证原则 |
| NF-0008 | 首期复用资源并形成课程、场景和付费试点 | 首期执行安排 |
| NF-0009 | 10—20 万元、30—50 万元投入控制 | 首期投入边界 |
| NF-0010 | 课程、场景、付费项目、价格、成本和复制结果 | 首期验证产出 |
| NF-0011 | 0.5—1.7 亿元/年用于长期空间判断 | 长期价值参考 |
| NF-0012 | 完成付费交付、复制和单位经济核算后再研究放大 | 后续研究门槛 |
| NF-0013 | 首期投入和产出按验证性质管理 | 首期经营边界 |
| NF-0014 | 首期允许收入较小，重点验证商业闭环 | 首期收入边界 |
| NF-0015 | 固定平台、批量许可和大额采购后置 | 后续事项约束 |

`NF-0011` 原文明确声明该数字“用于判断长期发展空间，不作为当前投资和收入承诺依据”。见 [normalized-facts.json](../projects/ai_power_training_business_feasibility/workbench/source-foundation/semantic/AI+电力教育培训业务商业可行性分析报告0819_processed/normalized-facts.json#L196)。

语义诊断 `D-001` 同时指出：长期潜在空间、首期验证预算和阶段性经营目标处于混合层级，后续页面规划需要区分前景判断与当前决策依据。见 [argument-chain.json](../projects/ai_power_training_business_feasibility/workbench/source-foundation/semantic/AI+电力教育培训业务商业可行性分析报告0819_processed/argument-chain.json#L443)。

### 4.2 页面计划丢失职责差异

P04 的权威页面计划出现以下问题：

- 10 条事实全部归入 `claim`；
- `boundary`、`trace_only` 为空；
- `excluded_from_onscreen` 为空；
- argument chain 只有两个节点；
- argument chain 只直接引用 NF-0006 和 NF-0007；
- “客户、产品、投入、合作机制分别在后续章节展开”被写成 `response`，该表达承担页间转场作用，无法代表当前页事实链中的业务回应。

见 [P04 page plan](../projects/ai_power_training_business_feasibility/workbench/outline/page-plan.json#L1029) 和 [P04 evidence roles](../projects/ai_power_training_business_feasibility/workbench/outline/page-plan.json#L1262)。

### 4.3 Handoff 放大错误

Handoff 存在三个关键放大机制。

#### 页面重要度提升全部事实优先级

`_page_fact_usage` 以页面 `importance` 计算页面内全部事实的使用优先级。页面为 `core` 时，全部直接事实被规范化为 high，进而投影为 P0。

代码位置：[source_projection.py](../.agents/skills/cyberppt-handoff/cyberppt_handoff/source_projection.py#L153)。

这使“页面重要”被转换为“页面内每条事实都同等重要”。当前项目 12 个内容页被标记为 `core`，最终产生 106 个 P0 内容单元。

#### 宽泛语义节点覆盖页面级职责

`build_projection` 先把 reconstructed-chain 节点写入每条 Source Truth 的 `semantic_node_ids`，随后把页面节点追加到列表，并以第一个节点角色生成全局 `argument_duty`。

代码位置：[project.py](../.agents/skills/cyberppt-handoff/cyberppt_handoff/project.py#L21)。

P04 的 10 条事实都先属于 `RC-01/context`，因此全部被投影为 `premise`。长期价值参考、后续研究门槛和首期经营边界由此失去差异。

#### P0/P1 与上屏责任耦合

`_content_units_from_source_truth` 对 `claim/reason/instance` 中的 P0/P1 内容默认设置 `onscreen_required=true`；结构职责为 premise、driver、consequence、gap、response 时也会强制上屏。

代码位置：[outline_projection.py](../.agents/skills/cyberppt-handoff/cyberppt_handoff/outline_projection.py#L179)。

这一步最终把 P04 的 10 条复合事实全部推入上屏合同。

### 4.4 写前预检采用局部补丁分类

近期代码新增以下字段：

- `argument_function`
- `decision_scope`
- `decision_effect`

当前正式上游状态为：

- normalized facts 中有 0 条记录包含这些字段；
- Source Truth 中有 0 条记录包含这些字段；
- 投影后的 P04 `outline.json` 中有 10 条内容单元包含这些字段。

正式 Handoff 的 Source Truth producer 没有生成这些字段；Handoff 的 Outline projector 只执行读取和复制。正式重跑 Handoff 时，当前 P04 的局部注解无法稳定保留。

当前预检还在代码中硬编码了以下业务分组：

- 能力基础；
- 首期验证原则；
- 首期验证安排；
- 长期培育价值参考；
- 后续研究门槛；
- 验证管理边界。

代码位置：[preview_page_anchors.py](../cyberppt/commands/preview_page_anchors.py#L22)。

其中 `operating_boundary` 和 `deferred_constraint` 被放入同一个“验证管理边界”分组，导致首期经营口径与后续事项约束再次发生混合。

### 4.5 写后审计无法阻止语义误组

历史 AI 电力培训项目 P04 将“长期空间”置于“放大条件与边界”分组。见 [历史 P04 脚本](../projects/ai-power-education-training-business-feasibility-20260822/workbench/scripts/final/script-final.md#L79)。

使用仓库 `.venv/bin/python3` 重新执行 P04 `page-lint`，结果为 `passed`，同时产生 13 条 warning，包括：

- 8 条 P0 锚点覆盖 warning；
- 模块维度不一致；
- 路径关系不可从模块顺序读取；
- 上屏文字 370 字，目标 268 字；
- 流程动作标题缺失；
- 循环回流节点缺失。

`page-lint` 只统计 error 决定 `rewrite_required`，warning 不改变 passed 状态。代码位置：[page_lint.py](../cyberppt/commands/page_lint.py#L12)。

近期代码还规定：页面同时存在 `value_reference` 与 `gate_condition` 时，整页模块维度检查直接返回空结果。该逻辑可能同步隐藏页面其他模块的真实维度问题。代码位置：[onscreen.py](../cyberppt/script_quality/onscreen.py#L1199)。

## 五、代码层根因评价

### 5.1 事实基础：表格行被视为单一事实

正文块通过句号、问号、感叹号和分号拆分为事实候选；表格块则按整行生成一个 `table_record`。

代码位置：[factbase.py](../.agents/skills/source-structure-factbase/source_structure_factbase/factbase.py#L10) 和 [表格处理](../.agents/skills/source-structure-factbase/source_structure_factbase/factbase.py#L60)。

“首期投入”一行同时包含：

- 联合验证阶段现金边界；
- 正式付费试点阶段现金边界；
- 内部人员投入方式；
- 紫金云环境和收费合作方式。

这些内容最终成为一个 Source Truth 记录和一个 content unit，锚点自然超过页面短语体量。

### 5.2 语义验证：重追溯，轻原子性与关系覆盖

normalized fact 验证器检查：

- statement 是否存在；
- fact type、normalization、confidence 是否合法；
- source assertion 和 evidence 坐标是否有效。

当前没有检查：

- 一个 normalized fact 是否包含多个独立命题；
- 是否保留了 Markdown 表格管道符；
- 是否混合当前状态、未来条件和长期参考；
- 决策型章节是否建立足够的语义关系；
- 诊断是否被下游页面计划处置。

代码位置：[business semantic validate](../.agents/skills/business-semantic-understanding/business_semantic_understanding/validate.py#L105)。

### 5.3 页面作者化：状态晋级过早

生成器只要接收到 `authoring_spec`，就会：

- 应用页面 spec；
- 设置 `judgment_status=author_edited`；
- 设置根 `editorial_authoring_status=author_edited`。

代码位置：[generate.py](../.agents/skills/ppt-outline-planning/ppt_outline_planning/generate.py#L806) 和 [根状态生成](../.agents/skills/ppt-outline-planning/ppt_outline_planning/generate.py#L852)。

验证器保证所有证据都被某个 role 分配，但不限制所有事实进入同一个 role；`excluded_from_onscreen` 只要求为数组，空数组可以通过。代码位置：[authoring.py](../.agents/skills/ppt-outline-planning/ppt_outline_planning/authoring.py#L127) 和 [validate.py](../.agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py#L783)。

因此，当前的 `author_edited` 更接近“结构化 spec 已提交”，尚未充分代表“页面取舍已经完成”。

### 5.4 Handoff：全局事实属性与页面消费属性混合

当前 Handoff 在 Source Truth 上写入：

- 由页面重要度推导的 priority；
- 由首个语义节点角色推导的 argument duty；
- reconstructed-chain 节点和页面节点混合的 semantic node IDs。

这些字段随后被多个页面共同消费。事实本体属性、全篇语义角色和页面内论证职责由此发生耦合。

同一事实可以在不同页面承担不同作用。例如长期市场测算在核心结论页承担价值参考，在市场空间页承担核心测算依据，在最终结论页承担持续培育价值说明。全局 Source Truth 记录无法用单一 `argument_function` 准确描述所有页面消费情境。

### 5.5 不上屏取舍理由在投影中丢失

Handoff 已计算 `excluded_refs` 并用它决定 content unit 是否上屏；页面输出字段 `excluded_from_onscreen` 最终却写成 `detail_refs`，原始结构化理由没有进入投影页面。

代码位置：[outline_projection.py](../.agents/skills/cyberppt-handoff/cyberppt_handoff/outline_projection.py#L345)。

页面写作输入又输出 `intentional_omissions`，没有直接输出结构化的 `excluded_from_onscreen` 理由。代码位置：[prepare_stage01_input.py](../cyberppt/commands/prepare_stage01_input.py#L290)。

因此，作者能够看到 `onscreen_required=false`，却可能看不到上游作者做出该取舍的完整原因。

### 5.6 页面审计：表面文本启发式承担过多语义职责

当前页面审计大量依赖：

- 缩进；
- 冒号；
- 模块标题词；
- 动作关键词；
- 字符长度；
- 文本重合度；
- 固定关系提示词。

这类检查适合格式、密度和明显结构错误，无法稳定判断长期价值参考与未来门槛的业务差异。通过扩大关键词和全页豁免修复误报，会继续增加规则之间的耦合。

## 六、目标架构

### 6.1 分离源事实语义与页面消费语义

建议建立两层明确合同。

#### 源事实固有语义

归属于 normalized fact 或其结构化 proposition：

- `proposition_kind`：事实、测算、建议、条件、约束、责任、状态；
- `temporal_scope`：当前、首期、长期、条件成熟后；
- `modality`：已、拟、建议、可、原则上；
- `condition`：成立或执行前提；
- `effect`：该命题直接影响的对象；
- `prohibited_inference`：禁止升级出的承诺、因果或确定性。

#### 页面消费语义

归属于 `page-plan.json` 中的当前页面：

- `evidence_role`：claim、reason、instance、boundary、trace_only；
- `page_function`：foundation、validation_method、output、value_reference、gate、operating_boundary 等；
- `relation_to_proposition`：supports、explains、contextualizes、constrains、gates；
- `decision_scope`：当前决策、首期验证、长期价值、后续研究；
- `visibility`：primary_onscreen、supporting_onscreen、prose_only、trace_only；
- `peer_set_id`：允许参与同维并列比较的集合；
- `group_id`：页面信息架构中的父级归属；
- `sequence_role`：main_chain、satellite、boundary、footer。

### 6.2 推荐页面消费合同

建议在 `page-plan.json` 增加或演进为以下结构：

```json
{
  "normalized_fact_id": "NF-0011",
  "evidence_role": "instance",
  "page_function": "value_reference",
  "relation_to_proposition": "contextualizes",
  "decision_scope": "long_term_value",
  "visibility": "supporting_onscreen",
  "peer_set_id": "long_term_reference",
  "group_id": "value_context",
  "sequence_role": "satellite"
}
```

该结构保持在现有权威 `page-plan.json` 中，无需新增确认文件、状态文件或平行事实源。

### 6.3 P04 推荐语义拓扑

P04 的页面拓扑可以表达为：

```text
主链：能力基础 → 首期验证原则 → 首期执行与投入 → 首期验证产出

卫星：长期空间只提供长期培育价值参考
门控：付费交付 + 第二客户复制 + 单位经济核算 → 后续平台化研究
当前边界：首期投入、产出和收入均按验证口径管理
后置约束：固定平台、批量许可和大额采购后置
```

这套拓扑允许页面作者根据密度选择三组、四组或主链加边界带；代码只传递关系、职责和禁止合并边，不预写业务分组标题。

## 七、优化建议与实施路线

### P0：止损与闭环验证

目标：阻止当前局部补丁继续扩大，建立正式链路回归。

1. 隔离 `_ARGUMENT_FUNCTION_GROUPS` 的业务硬编码；缺少上游页面消费语义时，preflight 返回 `semantic_contract_incomplete`。
2. 删除“同时出现 value reference 和 gate condition 时整页跳过模块维度检查”的逻辑，改为基于 `peer_set_id` 的定向比较。
3. 增加完整链路测试：normalized facts → page plan → Handoff → outline → page preflight。
4. 测试必须证明字段来自正式 producer，重跑 Handoff 后仍然存在。
5. `page-preflight` 优先消费权威 page plan，或在内存中重建对应页面投影并验证一致性；不新增持久哈希或确认文件。

验收标准：

- 删除投影文件中的局部 `argument_function` 后，正式链路能够重新生成页面消费合同；
- P04 中长期价值、后续门槛、首期经营边界和后置约束保持四类不同职责；
- 页面同时存在 value reference 和 gate 时，其他 peer modules 的维度错误仍可被发现。

### P1：事实原子化与语义质量门禁

目标：消除复合事实对页面合同的持续污染。

1. 表格行保留行标题作为上下文，对内容单元格生成独立 proposition candidates。
2. 每个拆分命题保留 `parent_table_record_id`、`cell_index`、`segment_index` 和原始证据坐标。
3. 引用标记进入 `citation_refs`，不进入 statement 和 onscreen anchors。
4. normalized fact validator 增加复合命题诊断：多句、多阶段、多条件、多动作和表格管道残留。
5. 允许多个 normalized facts 引用同一 layer-two source assertion，保持证据可追溯。
6. 对 decision-bearing section 要求关键事实具备关系、条件、边界或显式的 `unlinked_context` 处置。
7. `mixed_level`、`scope_shift`、`unsupported_jump` 等诊断必须在 page plan 中形成结构化 resolution。

验收标准：

- “首期投入”至少能够区分现金边界、人员投入和合作收费方式；
- “长期前景”能够区分市场测算、用途和禁止推导；
- 页面内容单元不再直接携带 Markdown 表格管道文本。

### P2：页面作者化合同升级

目标：让 `author_edited` 代表真实页面判断和取舍。

1. 每条直接页面事实必须进入 main chain、satellite、boundary、prose_only 或 trace_only 之一。
2. 每条 `primary_onscreen` 和 `supporting_onscreen` 事实必须声明 `relation_to_proposition`。
3. 页面重要度与页面内事实重要度分离；页面为 core 不再自动把全部事实提升为 P0。
4. P0 负责完整稿、追溯和关键事实保留，visibility 单独决定上屏责任。
5. 空 `excluded_from_onscreen` 需要 `all_evidence_visible_rationale`；高密度页面需要逐事实可见性决策。
6. `author_edited` 由作者 spec 提交、语义门禁通过和取舍完整共同决定。
7. 删除测试从自然语言字段演进为结构化结果：删除对象、页面影响、相邻页替代性和最终处置。

验收标准：

- 全部事实进入 `claim` 的复杂页面触发 `evidence_role_collapse` 或等价诊断；
- P04 不再产生 10 条全部必须上屏的合同；
- 页面链外事实都有明确卫星、边界、正文或追溯归属。

### P3：Handoff 机械投影修复

目标：Handoff 只做确定性映射，完整保留页面作者判断。

1. Source Truth 保留事实固有语义，页面 duty 与 visibility 从 page plan 逐页投影。
2. `_content_units_from_source_truth` 优先使用页面 consumption contract，停止以全局 record duty 覆盖页面职责。
3. `_page_fact_usage` 改为读取逐事实 importance 或 visibility，不再用页面 importance 批量提升。
4. 完整投影 `excluded_from_onscreen` 的 source refs、reason 和目标层。
5. `authority-map.json` 增加页面消费字段的 ID 映射，不创建第二套语义内容。
6. Outline projector 遇到缺失职责时停止并报告上游 page-plan 缺陷。

验收标准：

- 同一 normalized fact 在两页可拥有不同 page function；
- 重跑 Handoff 不改变权威 page-plan 的职责和可见性；
- Handoff 不生成新的业务分组名称或页面判断。

### P4：写前预检升级为语义拓扑

目标：从写前分类提示升级为可验证的页面设计合同。

preflight 建议输出：

- `page_proposition`；
- `main_chain_nodes` 和 `main_chain_edges`；
- `satellite_nodes`；
- `boundary_nodes`；
- `peer_sets`；
- `anti_merge_edges`；
- `visibility_budget`；
- `prose_only_units`；
- `unresolved_semantic_contracts`。

代码不生成“能力基础”“验证管理边界”等最终中文标题。页面作者依据语义拓扑命名业务分组，lint 再根据 evidence mapping 验证事实归属。

验收标准：

- 没有真实顺序的页面不返回 chain 型 composition；
- 主链与卫星内容可以在机器合同中区分；
- 当前经营边界与后续研究约束具备禁止合并边。

### P5：页面审计收敛

目标：保留格式审计优势，减少关键词规则承担的语义判断。

1. 模块维度检查只比较同一 `peer_set_id` 下的模块。
2. 事实到模块的 evidence mapping 采用现有页面 Markdown 字段承载，不新增平行脚本文件。
3. 高信号 warning 组合形成 `passed_with_warnings` 或 `rewrite_required`：
   - 明显超载；
   - 多条 P0 锚点缺口；
   - 主链不可读；
   - 表达模型与页面拓扑冲突。
4. 格式检查继续使用缩进、冒号和长度规则；业务职责检查转向消费合同。
5. expression model 由页面拓扑选择和验证，避免普通判断页被误判为 operation loop。

验收标准：

- 历史 P04 的 370/268 字超载不能以普通 `passed` 结束；
- 长期价值和后续门槛的分组错误由消费合同发现；
- 无业务语义冲突的模块不因关键词巧合产生阻断。

## 八、回归测试设计

建议建立以下黄金测试。

### 8.1 当前 P04 反例

- 0.5—1.7 亿元/年必须识别为长期价值参考；
- 付费交付、第二客户复制和单位经济核算必须识别为后续研究门槛；
- 首期投入产出验证性质和较小收入规模必须识别为首期经营边界；
- 固定平台建设和大额采购必须识别为后置约束。

### 8.2 同一事实跨页多角色

同一市场规模事实分别进入：

- 核心结论页：value reference；
- 市场空间页：claim 或 metric evidence；
- 最终结论页：supporting context。

验证 Handoff 不把其中一个页面角色写回全局 Source Truth。

### 8.3 Handoff 再生测试

从正式 normalized facts、page plan 重新执行 Handoff，验证：

- 页面消费字段完整；
- 局部投影修改不会被当作权威输入；
- 投影重建后语义职责不漂移。

### 8.4 审计误豁免测试

页面同时包含 value reference 和 gate condition，并另有两个真正的同级 peer modules。后两个模块维度不一致时，审计仍需报告问题。

### 8.5 高密度页面测试

构造 10 个直接事实的核心结论页，验证：

- 页面 core 不会自动产生 10 个 P0 onscreen units；
- deletion test 和 visibility budget 能够形成合理取舍；
- 页面正文完整保留事实，屏幕层保持可读。

## 九、建议开发顺序与工作量边界

| 阶段 | 工作重点 | 预期价值 | 风险 |
|---|---|---|---|
| P0 | 撤除局部硬编码、补正式链路测试 | 立即阻止错误扩散 | 低 |
| P1 | 表格原子化、源事实语义字段、诊断处置 | 提升所有后续阶段输入质量 | 中 |
| P2 | 页面 evidence consumption 合同 | 解决页面职责和上屏取舍根因 | 中高 |
| P3 | Handoff 投影调整 | 消除 priority、duty 和 visibility 错误放大 | 中 |
| P4 | 语义拓扑 preflight | 把页面结构判断前移 | 中 |
| P5 | 合同感知 lint 和历史回归 | 降低返工和误报 | 中 |

建议先完成 P0—P3，再扩大页面审计规则。P0—P3 决定权威语义能否稳定进入页面写作；P4—P5 负责提升作者体验和自动质检质量。

## 十、最终判断

当前代码没有发生单点失效。故障来源是一组连续的语义合同缺口：

1. 表格复合事实进入 normalized facts；
2. 关系图和论点节点没有达到单页消费粒度；
3. 页面作者化门禁允许角色塌缩和空取舍；
4. Handoff 将页面重要度、全局节点角色和上屏责任耦合；
5. 写前预检通过局部分类硬编码补救；
6. 写后审计以表面文本启发式和非阻断 warning 收尾。

优化的核心原则是：

> 源事实记录事实固有语义，page plan 记录页面消费语义，Handoff 只做机械投影，preflight 输出页面语义拓扑，lint 验证作者是否遵守该拓扑。

按这一原则改造后，系统才能稳定区分长期价值、后续门槛、当前经营边界和后置约束，并将页面质量控制真正前移到写作之前。
