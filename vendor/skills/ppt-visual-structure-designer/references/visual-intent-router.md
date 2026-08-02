# 视觉意图路由

## 目录

- 路由原则
- 意图类型
- 选择算法
- 冲突处理
- 退化风险

## 路由原则

视觉意图不是版式名称，而是“本页判断通过何种关系被看见”。先确定决策关系，再选择主视觉载体和空间组织。

## 意图类型

| `visual_intent_type` | 适用关系 | 推荐主视觉载体 | 主要风险 |
|---|---|---|---|
| `single_judgment_anchor` | 一个结论由少量证据支撑 | 单一结果对象、关键场景或中心能力体 | 大标题海报化 |
| `multi_semantic_foundation` | 多个不同基础共同支撑判断 | 共享承载体、基座、工作台或综合场景 | 一基础一卡片 |
| `evidence_to_judgment` | 多类证据推导一个结论 | 证据路径汇聚到判断区 | 把证据排成列表 |
| `scene_embedded_flow` | 流程依托真实业务场景发生 | 连续行业场景中的动作链 | 图是图、流程是流程 |
| `transformation_pipeline` | 输入经处理转为输出 | 有权重差异的转换通道 | 等宽流水线框 |
| `convergence_to_capability` | 多路资源汇聚为核心能力 | 汇聚中枢、服务工作台或能力引擎 | 中心圆加图标 |
| `capability_to_outcomes` | 一组能力产生多类结果 | 主能力体向结果场景展开 | 结果卡片同权 |
| `layered_architecture` | 多层架构逐层支撑 | 有深度的分层空间或剖面 | 软件后台式分层盒子 |
| `dual_engine_synergy` | 两个主体或能力协同 | 两侧非对称力量通过共享载体协同 | 简单左右对半 |
| `closed_loop_operation` | 多阶段反馈迭代 | 有起点、关键门控和反馈的闭环 | 装饰圆环 |
| `comparison_tension` | 两种方案或状态形成差异 | 同轴对照、分水岭或转换前后 | 两列卡片照抄 |
| `phased_roadmap` | 阶段推进和里程碑 | 有节奏差异的路径、地形或建设进程 | 均匀时间轴 |
| `network_ecosystem` | 多主体交换和协同 | 有主次节点、流向和边界的网络 | 蜘蛛网或图标星云 |
| `policy_to_action` | 政策要求映射到业务动作 | 上层约束向下转为任务链 | 政策原文堆叠 |
| `risk_control_boundary` | 风险、边界和控制措施 | 门控、隔离区、受控通道和输出边界 | 红色警示卡片墙 |
| `data_flow_value_chain` | 数据流动并产生价值 | 数据对象在业务场景中受控流转 | 技术管道与业务脱节 |
| `role_responsibility_map` | 多主体分工并交付成果 | 主体位置、任务区和交付接口 | 组织架构图化 |
| `problem_cause_resolution` | 问题、原因、解决路径 | 张力中心与因果/解法两条链 | 三段式文字框 |

## 选择算法

按顺序判断：

1. 本页是否只有一个需要被记住的结论，证据较少？选择`single_judgment_anchor`。
2. 是否存在多个性质不同但共同构成基础的要素？选择`multi_semantic_foundation`。
3. 是否强调多类证据最终推导判断？选择`evidence_to_judgment`。
4. 是否存在明显输入、处理、输出？选择`transformation_pipeline`。
5. 流程是否必须依托真实行业活动理解？选择`scene_embedded_flow`。
6. 是否由多路资源汇聚为一个平台、能力或服务？选择`convergence_to_capability`。
7. 是否由核心能力向多个结果展开？选择`capability_to_outcomes`。
8. 是否强调层级、底座、平台和应用的依赖？选择`layered_architecture`。
9. 是否是两个主体或能力共同驱动同一结果？选择`dual_engine_synergy`。
10. 是否存在持续反馈、更新和迭代？选择`closed_loop_operation`。
11. 是否比较两种状态、路线或前后变化？选择`comparison_tension`。
12. 是否按阶段推进并有里程碑？选择`phased_roadmap`。
13. 是否多主体交换资源并存在主次关系？选择`network_ecosystem`。
14. 是否从政策要求转为建设任务？选择`policy_to_action`。
15. 是否核心在安全边界和受控输出？选择`risk_control_boundary`。
16. 是否数据流转与价值形成同时重要？选择`data_flow_value_chain`。
17. 是否主要说明职责分工和交付接口？选择`role_responsibility_map`。
18. 是否从问题追到原因并导出方案？选择`problem_cause_resolution`。

多个类型均适用时，选择最能承载核心结论的一个作为主类型；另一个只能作为次级语法，不得并列形成两个视觉中心。

## 冲突处理

- “流程+场景”：流程是核心时选`scene_embedded_flow`；转换机制是核心时选`transformation_pipeline`。
- “架构+数据流”：层级依赖是核心时选`layered_architecture`；受控流转和价值形成是核心时选`data_flow_value_chain`。
- “协同+网络”：只有两个核心主体时选`dual_engine_synergy`；三个以上主体且有交换关系时选`network_ecosystem`。
- “基础+汇聚”：强调共同基础时选`multi_semantic_foundation`；强调汇聚后形成中枢能力时选`convergence_to_capability`。
- “闭环+路线”：存在反馈回到前序节点时选`closed_loop_operation`；只有阶段推进时选`phased_roadmap`。

## 退化风险

选择意图后检查是否退化：

- 主视觉载体是否只是一个大框。
- 文字是否仍按原项目符号排列。
- 图片是否能删除而不影响逻辑；若能，说明图片未参与表达。
- 连接线是否只起装饰作用。
- 视觉中心是否由面积最大元素决定，而不是由核心判断决定。
- 意图类型是否被机械映射为固定模板。
