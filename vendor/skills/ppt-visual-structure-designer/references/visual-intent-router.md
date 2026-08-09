# 视觉意图路由

## 目录

- 路由原则
- 意图类型
- 选择算法
- 冲突处理
- 退化风险

## 路由原则

视觉意图不是版式或媒介名称，而是“本页判断通过何种关系被看见”。先确定决策关系，再选择语义焦点、空间语法和阅读顺序；具体载体保持开放。

## 意图类型

| `visual_intent_type` | 适用关系 | 空间语法 | 必须保留的结构事实 | 主要风险 |
|---|---|---|---|---|
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

1. 本页是否只有一个需要被记住的结论，证据较少？选择`single_judgment_anchor`。
2. 是否存在多个性质不同但共同构成基础的要素？选择`multi_semantic_foundation`。
3. 是否强调多类证据最终推导判断？选择`evidence_to_judgment`。
4. 是否存在明显输入、处理、输出？选择`transformation_pipeline`。
5. 流程是否必须依托真实行业活动理解？选择`scene_embedded_flow`。
6. 是否由多路资源共同作用并形成一个能力、状态或结果？选择`convergence_to_capability`。
7. 是否由核心能力向多个结果展开？选择`capability_to_outcomes`。
8. 是否强调不同层级之间的依赖、包含或支撑？选择`layered_architecture`。
9. 是否是两个主体或能力共同驱动同一结果？选择`dual_engine_synergy`。
10. 是否存在持续反馈、更新和迭代？选择`closed_loop_operation`。
11. 是否比较两种状态、路线或前后变化？选择`comparison_tension`。
12. 是否按阶段推进并有里程碑？选择`phased_roadmap`。
13. 是否多主体交换资源并存在主次关系？选择`network_ecosystem`。
14. 是否从外部规则或要求转为执行动作？选择`policy_to_action`。
15. 是否核心在安全边界和受控输出？选择`risk_control_boundary`。
16. 是否数据流转与价值形成同时重要？选择`data_flow_value_chain`。
17. 是否主要说明职责分工和交付接口？选择`role_responsibility_map`。
18. 是否从问题追到原因并导出方案？选择`problem_cause_resolution`。

多个类型均适用时，选择最能承载核心结论的一个作为主类型；其他关系只记录为次级语义标签或辅助语法，不得并列形成两个主结构。

## 冲突处理

- “流程+场景”：流程是核心时选`scene_embedded_flow`；转换机制是核心时选`transformation_pipeline`。
- “架构+数据流”：层级依赖是核心时选`layered_architecture`；受控流转和价值形成是核心时选`data_flow_value_chain`。
- “协同+网络”：只有两个核心主体时选`dual_engine_synergy`；三个以上主体且有交换关系时选`network_ecosystem`。
- “基础+汇聚”：强调共同基础时选`multi_semantic_foundation`；强调汇聚后形成中枢能力时选`convergence_to_capability`。
- “闭环+路线”：存在反馈回到前序节点时选`closed_loop_operation`；只有阶段推进时选`phased_roadmap`。

## 退化风险

选择意图后检查是否退化：

- 语义焦点是否只剩一个没有职责的名称。
- 文字是否仍按原项目符号排列。
- 所选媒介是否能删除而完全不影响逻辑；若能，说明媒介未参与表达。
- 连接线是否只起装饰作用。
- 视觉中心是否由面积最大元素决定，而不是由核心判断决定。
- 意图类型是否被机械映射为固定模板。
- 三个候选是否只更换载体、媒介或外观，而没有改变语义焦点、空间语法或阅读顺序。
