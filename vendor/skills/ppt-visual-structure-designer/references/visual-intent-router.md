# 视觉意图路由

## 目录

- 路由原则
- 三层关系契约
- 意图类型
- 选择算法
- 冲突处理
- 退化风险

## 路由原则

视觉意图不是版式或媒介名称，而是“本页判断通过何种关系被看见”。先确定决策关系，再选择语义焦点、空间语法和阅读顺序；具体载体保持开放。

**`expression_constraints.reading_requirement` 是权威输入，不是候选参考。** CyberPPT 工作台模式下，每页在进入本路由前，Stage 02 handoff 已经通过 `cyberppt/onscreen_expression.py` 锁定了该页的表达形式及其 `reading_requirement`。本路由必须遵守该阅读关系边界：

- `parallel`（包括 `key_points_3`、`framework_4`、`parallel_classification`）：来源已确认这些项之间没有必然优先级、先后或因果关系。禁止把其中某一并列项升格为结果节点；禁止仅因存在分类或 `supports` 词汇就选择分层或流程结构。
- `mapped`（`mapping_2_6`）：来源已确认存在问题—响应、对象—能力或其他成对映射。必须保持每个源对象与其对应对象的绑定；不得自动改造成“双列比较”，除非内容本身明确要求比较且具有共同比较维度。
- `grouped`（`grouped_2`）：来源已确认这是“一组确立主体，另一组展开其机制或边界”的主从关系，不是纯并列。
- `directed` / `convergent` / `cyclic`：来源已确认存在真实顺序、因果、汇聚或反馈，可采用相应的路径、收敛或闭环表达。
- `layered`：来源已确认层级或依赖关系；只有这种情况下才允许将分类项表现成上下层结构。
- `paired`：表示存在同一维度下的对照，不等于所有 `corresponds_to` 都应画成比较页。

如果调用方式没有 `expression_constraints`，按“选择算法”从内容本身判断关系；缺少来源支持的先后、因果、层级时，保持并列或映射关系，不为构图便利增加关系。

若上游 Outline 阶段已把本页内容匹配为 `references/semantic-expression-models.md` 中的语义模型，其 `forbidden_inferences` 同样约束视觉关系编码，视觉阶段不得重新引入论证阶段已排除的因果、层级或先后关系。

## 三层关系契约

CyberPPT 工作台必须区分三个层次：

1. `business_relationships`：业务语义真值，回答“A 与 B 在业务上是什么关系”。关系词可以是 `supports`、`responds_to`、`corresponds_to`、`causes`、`sequence_before`、`feedback_to`、`classified_as`、`layered_as`、`bounded_by`、`covers` 等。
2. `expression_constraints`：阅读结构边界，回答“受众应该按并列、映射、收敛、流程、闭环、分层等何种关系阅读”。它约束候选，但不指定版式。
3. `topology`：Stage 02 视觉拓扑，由本 Skill 基于前两层和页面证据选择。业务关系词不得与 topology 建立一对一硬映射。

`business_relationships[*].semantic_qualifiers`若存在必须保留。特别是：

- `independent_selection`：各模式可以独立选择；
- `optional_progression`：各模式可以随着成熟度逐步深化；
- 两者同时出现时，页面必须同时表达“并列可选”和“可选择的深化路径”。`directed_flow`不得成为唯一主拓扑，因为它会把可选深化误读成强制必经流程。

关系到 topology 的判断必须同时考虑基数与结构：

- 多个 `supports` 指向同一结论：优先考虑 `conclusion_anchor` 或收敛型结构；不得因为 `supports` 直接选择四模块框架或分层架构。
- `responds_to` / `corresponds_to`：优先保持问题—响应或对象—能力映射；只有明确存在共同比较维度时才允许比较结构。
- `classified_as`：默认是并列 taxonomy，优先 `parallel_set`；不得自动转为 `layered_architecture` 或 `directed_flow`。
- `layered_as` / `part_of`：有真实层级依赖时才可进入 `layered_architecture`。
- `sequence_before`：存在真实阶段顺序时可进入 `directed_flow`。
- `feedback_to`：必须存在返回关系，才可进入 `lifecycle_loop`。

如果输入提供 `stage01_relationship_features.semantic_relation_profile`，其中：

- `topology_candidates` 是候选集合，不是强制选择；
- `forbidden_topologies` 是硬约束，候选不得违反；
- `cardinality`、`shared_target`、`independent_selection`、`optional_progression` 是关系形状证据；
- `topology_authority` 应为 `visual_structure_designer`，表示最终拓扑仍由本阶段负责选择。

## 意图类型

| `visual_intent_type` | 适用关系 | 空间语法 | 必须保留的结构事实 | 主要风险 |
|---|---|---|---|---|
| `coordinate_peer_set` | 多个语义独立、来源未表明先后或因果关系的并列项，共同支撑同一个不属于其中任一项的抽象判断 | `peer` | 各并列项完整语义、共享抽象判断、无优先级声明 | 挑选某一并列项充当结果节点 |
| `single_judgment_anchor` | 一个结论由少量证据支撑 | `anchor` | 判断、证据及支撑方向 | 大标题海报化 |
| `multi_semantic_foundation` | 多个不同基础共同支撑判断 | `anchor`或`layer` | 基础差异、共同作用对象及判断 | 一基础一卡片 |
| `evidence_to_judgment` | 多类证据推导一个结论 | `path`或`convergence` | 证据、推导方向及判断 | 把证据排成列表 |
| `scene_embedded_flow` | 流程必须依托上下文理解 | `path` | 动作顺序、参与者及发生环境 | 图与流程分离 |
| `transformation_pipeline` | 输入经处理转为输出 | `path` | 输入、动作、状态变化及输出 | 等宽流水线框 |
| `convergence_to_capability` | 多路资源汇聚形成统一能力 | `convergence` | 多路来源、共同作用点及形成结果 | 中心圆加图标 |
| `capability_to_outcomes` | 一组能力产生多类结果 | `divergence` | 能力来源、不同结果及主次 | 结果卡片同权 |
| `layered_architecture` | 多层结构逐层支撑 | `layer` | 层级、依赖方向及贯穿关系 | 软件后台式分层盒子 |
| `dual_engine_synergy` | 两个主体或能力协同 | `interface` | 双方角色、交互内容及共同结果 | 简单左右对半 |
| `closed_loop_operation` | 多阶段反馈迭代 | `path`加`feedback` | 起点、主路径、反馈对象及返回方向 | 装饰圆环 |
| `comparison_tension` | 两种方案或状态形成差异 | `tension` | 共同基准、对比项及结论 | 两列卡片照抄 |
| `phased_roadmap` | 阶段推进和里程碑 | `path` | 阶段顺序、权重差异及里程碑 | 均匀时间轴 |
| `network_ecosystem` | 多主体交换和协同 | `network` | 节点角色、交换类型、方向及边界 | 蜘蛛网或图标星云 |
| `policy_to_action` | 规则要求映射到执行动作 | `control`加`path` | 约束来源、作用对象、动作及结果 | 原文堆叠 |
| `risk_control_boundary` | 风险、边界和控制措施 | `boundary` | 内外、入口、控制条件及允许输出 | 警示卡片墙 |
| `data_flow_value_chain` | 数据流动并产生价值 | `path`加`boundary` | 数据状态、控制条件、动作及价值结果 | 技术路径与业务脱节 |
| `role_responsibility_map` | 多主体分工并交付成果 | `interface`或`network` | 主体、职责、交付物及接口 | 组织架构图化 |
| `problem_cause_resolution` | 问题、原因、解决路径 | `tension`加`path` | 问题、原因、干预动作及结果 | 三段式文字框 |

## 选择算法

按顺序判断：

0. 先读取 `business_relationships`、`semantic_relation_profile`（若有）和 `expression_constraints`。若 profile 明确禁止某一 topology，直接排除该候选。
1. 各项之间没有来源支持的先后、主从或因果关系？选择 `coordinate_peer_set`，不得编造顺序或结果关系。
2. 存在明确问题—响应、对象—能力等映射，且阅读关系为 `mapped`？保持映射结构；不要自动转为比较。
3. 本页只有一个需要被记住的结论，证据较少？选择 `single_judgment_anchor`。
4. 多类证据共同指向一个判断，且 profile 显示 `many_to_one/shared_target`？选择 `evidence_to_judgment` 或与其等价的收敛结构。
5. 多个性质不同的基础共同支撑判断？选择 `multi_semantic_foundation`；若不存在真实支撑对象，回到并列结构。
6. 存在明显输入、处理、输出？选择 `transformation_pipeline`。
7. 流程必须依托真实行业活动理解？选择 `scene_embedded_flow`。
8. 多路资源共同作用并形成一个能力、状态或结果？选择 `convergence_to_capability`。
9. 核心能力向多个结果展开？选择 `capability_to_outcomes`。
10. 强调真实层级依赖、包含或支撑？选择 `layered_architecture`。
11. 两个主体或能力共同驱动同一结果？选择 `dual_engine_synergy`。
12. 存在持续反馈、更新和迭代？选择 `closed_loop_operation`。
13. 明确比较两种状态、路线或方案，并具有共同维度？选择 `comparison_tension`。
14. 按阶段推进并有里程碑？选择 `phased_roadmap`。
15. 多主体交换资源并存在主次关系？选择 `network_ecosystem`。
16. 外部规则或要求转为执行动作？选择 `policy_to_action`。
17. 核心在安全边界和受控输出？选择 `risk_control_boundary`。
18. 数据流转与价值形成同时重要？选择 `data_flow_value_chain`。
19. 主要说明职责分工和交付接口？选择 `role_responsibility_map`。
20. 从问题追到原因并导出方案？选择 `problem_cause_resolution`。

多个类型均适用时，选择最能承载核心结论的一个作为主类型；其他关系只记录为次级语义标签或辅助语法。对于“并列可选 + 可逐步深化”这类双重关系，可在一个主关系场中用次级深化路径表达，不得删除并列可选性。

## 冲突处理

- “并列+可深化”：并列选择关系为基础结构，深化路径作为次级关系；不得使用单一路径暗示所有对象必须依次经历。
- “映射+比较”：只有内容明确要求同维度比较时才选比较；普通问题—响应映射保持对应关系。
- “流程+场景”：流程是核心时选`scene_embedded_flow`；转换机制是核心时选`transformation_pipeline`。
- “架构+数据流”：层级依赖是核心时选`layered_architecture`；受控流转和价值形成是核心时选`data_flow_value_chain`。
- “协同+网络”：只有两个核心主体时选`dual_engine_synergy`；三个以上主体且有交换关系时选`network_ecosystem`。
- “基础+汇聚”：强调共同基础时选`multi_semantic_foundation`；强调汇聚后形成中枢能力时选`convergence_to_capability`。
- “闭环+路线”：存在反馈回到前序节点时选`closed_loop_operation`；只有阶段推进时选`phased_roadmap`。

## 退化风险

选择意图后检查：

- 是否把业务关系词机械映射成固定 topology 或版式。
- 是否把 `classified_as` 误画成层级或流程。
- 是否把普通 `corresponds_to/responds_to` 误画成比较。
- 是否把多个 `supports` 指向同一结论误画成并列四卡或分层架构。
- 是否丢失 `independent_selection` / `optional_progression` 等关系限定语。
- 语义焦点是否只剩一个没有职责的名称。
- 文字是否仍按原项目符号排列。
- 所选媒介是否能删除而完全不影响逻辑；若能，说明媒介未参与表达。
- 连接线是否只起装饰作用。
- 视觉中心是否由面积最大元素决定，而非核心判断决定。
- 写了多个候选时，是否只更换载体、媒介或外观，而没有改变语义焦点、空间语法或阅读顺序。
