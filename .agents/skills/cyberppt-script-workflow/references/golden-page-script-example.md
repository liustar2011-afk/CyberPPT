# 黄金页面索引：Relation Grammar

本文件同时承担黄金示例导航和历史可解析入口兼容职责。AUTHOR、CRITIQUE、REWRITE 的单一操作权威仍为 [authoring-contract.md](authoring-contract.md)。示例用于说明如何把该 Contract 已有的 independent arguments / reasoning units、claim–argument–evidence 和 relation grammar 落成可读页面。

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

每个完整黄金页面均包含：页面使命、核心结论、主论证链、Argument Topology、Relation Units、完整文字稿、上屏文字、视觉结构、演讲者备注和作者自检。

## 使用原则

- 先判断页面结论依靠什么关系成立，再选择最小可解释 topology。
- `Relation Units` 必须共同支撑 `core_message`，兄弟单元处于可解释的同一语义层级。
- Evidence 只证明、解释或限定直接父级；没有论证作用的事实不升级为主单元。
- 上屏保持 `Core Message → Relation Units → Evidence` 的可恢复层级，同时保留方向、映射、汇聚、反馈等真实关系。
- 示例中的视觉结构是关系表达参考，不锁定 Stage2 的具体版式或视觉载体。
- Stage2 仍只消费锁定后的 Stage1 文案及关系，不重新创作业务文字。

## 历史可解析入口

下面两页保留原 `golden-page-script-example.md` 的可解析结构，供既有 parser / hierarchy regression 使用。Parallel 与 Flow 的扩展教学版本仍以上述独立文件为准。

## 第1页：统一预测体系的建设维度

- 页面类型：内容页
- 页面标题：统一预测体系的建设维度
- 内容负载：dense
- 页面使命：说明统一预测体系为何需要同时贯通研判范围、周期规则和运行闭环。
- 核心结论：统一预测体系贯通研判范围、周期规则和运行闭环，形成持续风险预警。
- 主论证链：体系目标 → 研判范围扩展、周期规则贯通、运行闭环形成 → 持续风险预警
- 上屏表达结构：parallel_classification_3_6

### 完整文字稿

统一预测体系需要同时处理研判对象和成果形态的扩展、不同业务周期的统一规则，以及预测、审校、发布和复盘的持续运行。三项建设维度共同决定风险预警能否稳定形成并持续更新。

### 上屏文字

- 统一预测体系贯通研判范围、周期规则和运行闭环，形成持续风险预警
  - 研判范围扩展为多维分析与多形态成果
    - 供给、需求和市场因素共同影响总量、结构、区域、时段与风险判断
    - 预测延伸到区间、概率和情景分析，成果扩展到清单、图谱、专报与会商支撑
  - 月报、季报和年报需要统一口径、数据与流程
    - 既有月报、季报和年报提供稳定业务基础，各周期规则仍需打通
    - 月度、季度、年度和重点时段分析需要统一指标口径、数据版本和判断尺度
    - 预测分析和报告生产需要固化流程
  - 月季年预测需要形成可审校、可复盘的运行闭环
    - 月度滚动、季度校核和年度展望共用分析框架，三类周期结论相互验证
    - 基准预测、情景分析和专家修正形成研判结果
    - 报告发布和误差复盘推动业务闭环持续运行

### 视觉结构

总论位于页面上方入口区域，先于所有分组进入视线。三组采用同级、可变形的分区表达；每组的标题置于其论证之上。视觉可围绕报告、数据或风险预警对象建立主视觉，三组与主视觉保持语义邻近。页面不将三组画成实施先后或因果链。

### 演讲者备注

供需预测的难点已经超出单一数值的预测精度。供给侧可用能力、需求侧负荷形态和市场互济机制会共同改变判断对象，结论也需要从单点趋势扩展到区间、概率和情景。

不同周期若使用不同的数据版本、指标口径和判断尺度，同一风险在月度、季度和年度之间就难以相互验证。因此，范围扩展解决“看什么、产出什么”，周期规则解决“按什么尺度判断”，运行闭环解决“结论如何持续更新”。三项建设维度共同支撑可解释、可追溯的风险预警能力。

## 作者自检

1. 一级文字与核心结论表达同一完整判断，包含对象、关系和结果。
2. 二级三组都回答“统一预测体系由哪一项建设维度支撑”。
3. 三组互不重叠：研判范围处理分析对象与成果形态；周期规则处理跨周期口径与流程；运行闭环处理审校、发布与复盘。
4. 遮住三级文字后，二级标题仍可独立解释其对总论的贡献。
5. 遮住二级标题后，三级文字仍提供新事实、动作或结果，没有机械重述标题。
6. 上方总论为唯一页面入口结论；三组在视觉上同级展开。

---

## 第2页：统一预测闭环的运行路径

- 页面类型：内容页
- 页面标题：统一预测闭环的运行路径
- 内容负载：dense
- 页面使命：说明统一数据、分析与审校机制如何形成持续更新的预测运行闭环。
- 核心结论：统一数据、分析与审校流程把预测结果转化为持续更新的风险预警闭环。
- 主论证链：统一数据与规则 → 预测研判 → 审校发布 → 误差复盘回写 → 下一轮风险预警
- 上屏表达结构：flow_3_5

### 完整文字稿

统一预测闭环以一致的数据目录、口径和版本管理为起点，按不同业务周期接入统计、高频负荷、气象、交易和新型主体等数据。基准预测、情景分析和专家修正共同形成研判结果，经会商审校和发布管理转化为月报、季报、年报或专题专报。发布后的误差复盘再回写数据版本、分析规则和预测参数，推动下一轮月度滚动、季度校核和年度展望持续更新。

### 上屏文字

- 统一数据、分析与审校流程把预测结果转化为持续更新的风险预警闭环
  - 统一数据与规则为各周期研判提供一致输入
    - 统计、高频负荷、气象、交易和新型主体等数据按业务需要接入，并统一目录、口径和版本管理
  - 基准预测、情景分析和专家修正共同形成研判结果
    - 月度滚动、季度校核和年度展望共用分析框架，在不同时间尺度上相互验证
  - 会商审校和发布管理把研判结果沉淀为正式成果
    - 月报、季报、年报和专题专报沿用统一的指标、图表、章节与结论模板
  - 误差复盘回写规则与参数，驱动下一轮预测更新
    - 发布结果与复盘结论进入后续月度滚动、季度校核和年度展望，持续形成可解释的风险判断

### 视觉结构

总论位于页面顶部的首个阅读入口，以与流程主视觉融合的方式出现，不能放入流程节点。主体采用从左至右、再回写起点的连续运行路径：数据与规则准备进入预测研判，经审校发布形成正式成果，复盘以清晰回流关系返回数据规则与预测参数。四个二级单元按阶段出现，三级文字紧贴各自阶段说明输入、动作、成果或反馈。月度、季度和年度作为共用框架内的不同业务周期呈现，不能被画成三道串行工序。

### 演讲者备注

月报、季报和年报分别承担滚动、校核和展望职责，并在同一数据版本和判断尺度上衔接。运行起点是可信的数据与规则，重点在于让不同周期使用可追溯、可比对的共同输入。

预测环节将基准判断、情景变化和专家经验合并为可解释的研判结果；会商审校和发布管理再把结果固化为正式成果。复盘的价值在于把发布后的偏差回写到数据版本、分析规则和预测参数，使下一轮判断能够更新而且能够追溯。这样，报告生产就沉淀为持续运行的风险预警能力。

## 作者自检：流程页

1. 一级文字完整说明“统一流程如何形成持续更新的风险预警闭环”。
2. 二级四项回答同一问题：“闭环在哪一个运行阶段发生什么？”并按真实交接顺序排列。
3. 每项三级文字分别补足输入、研判方法、正式成果或反馈动作，不能重述阶段名。
4. 从“复盘”回到“数据与规则”的回写关系清晰可见；不可把闭环画成单向四卡流程。
5. 月度、季度和年度是共用框架中的业务周期，不得被误画为串行阶段。
