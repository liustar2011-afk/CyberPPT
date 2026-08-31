# 黄金页面索引：Relation Grammar

本文件是黄金示例导航，不是 AUTHOR 的第二套运行规则。AUTHOR、CRITIQUE、REWRITE 的单一操作权威仍为 [authoring-contract.md](authoring-contract.md)。示例用于说明如何把该 Contract 已有的 independent arguments / reasoning units、claim–argument–evidence 和 relation grammar 落成可读页面。

## Relation Units 的示例口径

本示例库允许使用 `Relation Units` 作为教学标签，指核心结论之下承担独立论证角色的一级业务语义单元。它映射到 AUTHOR Contract 中现有的 independent arguments / reasoning units：

`core_message → independent arguments / Relation Units → decisive evidence`

该标签不进入 Final Script schema，不形成新的 Stage1 authoritative IR，也不要求 AUTHOR 新增持久化字段。

## 8 类黄金页面

| 编号 | 关系类型 | Authoring Topology | 示例文件 | 训练重点 |
|---|---|---|---|---|
| 01 | Parallel / MECE Classification | parallel grouping | [golden-page-parallel.md](golden-page-parallel.md) | 同维度并列、独立支撑总论 |
| 02 | Flow / Feedback Loop | directed chain + feedback | [golden-page-flow.md](golden-page-flow.md) | 阶段顺序、真实交接、回写闭环 |
| 03 | Causal Chain | directed chain | [golden-page-causal.md](golden-page-causal.md) | 原因、影响、结论逐级成立 |
| 04 | Convergence | convergence | [golden-page-convergence.md](golden-page-convergence.md) | 多个独立输入共同形成结果 |
| 05 | Mapping | mapping | [golden-page-mapping.md](golden-page-mapping.md) | 两端对象与对应规则同时可见 |
| 06 | Comparison | comparison | [golden-page-comparison.md](golden-page-comparison.md) | 同一标准下可比、差异可解释 |
| 07 | Roadmap | roadmap | [golden-page-roadmap.md](golden-page-roadmap.md) | 起点、阶段、触发条件、新状态 |
| 08 | Governance / Boundary | governance chain | [golden-page-governance.md](golden-page-governance.md) | 主体、责任、控制机制、受保护结果 |

## Authoring Grammar 与机器语义拓扑的衔接

这张表只用于解释层间关系，不替代运行时代码。AUTHOR 先按业务关系写清语义，再由正式 relationship vocabulary 和 `cyberppt.topology_resolver` 解析 semantic topology；Stage2 的详细表达继续由 `cyberppt.onscreen_expression` 决定。

| Authoring Grammar | 典型 semantic relationship | 常见 semantic topology | 粗粒度 carrier family |
|---|---|---|---|
| parallel grouping | `peer_classification` / `classified_as` | `peer_set` | `parallel_set` |
| directed chain（顺序） | `sequence_before` / `sequence_after` | `sequence` | `directed_flow` |
| directed chain（因果） | `causes` | `causal_chain` | `directed_flow` / `causal_convergence` |
| directed chain（依赖） | verified directed dependency chain | `dependency_chain` | `directed_flow` |
| feedback loop | `feedback` / `feeds_back_to` 等 | `feedback_loop` | `lifecycle_loop` |
| convergence | 多来源 `supports` / `evidence_supports` 指向同一对象 | `support_convergence` | `causal_convergence` / `conclusion_anchor` |
| mapping | `problem_response` / `semantic_mapping` / `corresponds_to` | `mapping` | `parallel_set` / `conclusion_anchor` |
| comparison | `comparison` | `comparison` | `parallel_set` |
| roadmap | 真实阶段之间的 sequence relationship | `sequence` | `directed_flow` |
| governance chain | 按实际责任、依赖、映射或顺序关系编码 | 由真实 relationship 解析 | 不预设单一 carrier |
| bounded decision package | 按建议、条件、边界之间的真实关系编码 | 由真实 relationship 解析 | 不预设单一 carrier |

另有机器语义 topology `containment` 与 `matrix`，分别处理组成/包含关系和明确二维矩阵表面；它们属于 semantic topology 层，不要求 AUTHOR 为了视觉多样性主动套用。当前粗粒度 carrier family 分别复用 `layered_architecture` 与 `parallel_set`，详细版式仍由 Stage2 后续表达层选择。

## 统一示例结构

每个完整黄金页面均包含：

1. 页面使命；
2. 核心结论；
3. 主论证链；
4. Argument Topology；
5. Relation Units（教学标签）；
6. 完整文字稿；
7. 上屏文字；
8. 视觉结构；
9. 演讲者备注；
10. 作者自检。

## 使用原则

- 先判断页面结论依靠什么关系成立，再选择最小可解释 topology。
- `Relation Units` 必须共同支撑 `core_message`，兄弟单元处于可解释的同一语义层级。
- Evidence 只证明、解释或限定直接父级；没有论证作用的事实不升级为主单元。
- 上屏保持 `Core Message → Relation Units → Evidence` 的可恢复层级，同时保留方向、映射、汇聚、反馈等真实关系。
- 示例中的视觉结构是关系表达参考，不锁定 Stage2 的具体版式或视觉载体。
- Stage2 仍只消费锁定后的 Stage1 文案及关系，不重新创作业务文字。
