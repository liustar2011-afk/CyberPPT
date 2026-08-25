# 与 ppt-script 工作台的衔接

## 适用范围

用于将已验证逐页脚本传递到本 Skill 完成视觉结构设计。该衔接层不重新开展材料研究、故事线规划和页面分配；它消费 Stage 02 已完成的语义校验结果，并在语义边界内完成视觉决策。

## 工作台语义权威规则

本文件中的工作台规则覆盖旧版“`business_relationships` 是唯一权威关系来源”的兼容表述。新版 Stage 02 将“上游提案”“语义校验结果”“视觉决策”分开管理：

1. `semantic_proposals`：上游关系提案及其来源、证据、置信度和权威等级，仅用于追溯，不能直接锁定视觉关系。
2. `semantic_verification`：Stage 02 Semantic Verifier 的 accepted / refined / rejected / unresolved 回执，是判断上游关系是否可继续使用的依据。
3. `verified_business_relationships`：通过校验或经校验细化后的业务关系，是视觉阶段优先消费的关系集合。
4. `semantic_topology`：Topology Resolver 形成的业务拓扑候选及主拓扑，只回答“页面是什么关系图”，不等于 PPT 版式。
5. `onscreen_expression` 与 `expression_constraints`：根据 verified topology 形成的阅读合同，用于限定阅读关系和信息均衡，不直接指定卡片、列、箭头、循环、金字塔或矩阵模板。
6. `author_visual_notes`：始终为 `advisory_only`，不得覆盖已校验业务关系。

为兼容旧工作台，如果输入中尚无 `verified_business_relationships`，才允许回退到 `business_relationships`。一旦存在 verifier 字段，禁止用原始 `business_relationships` 重新覆盖已校验结果。

## 约束权威等级

`constraint_authority` 只允许：

- `hard`：源材料或人工明确关系且证据充分。候选不得改变其方向、因果、顺序、反馈、层级、对应或并列等核心关系。
- `strong`：可靠结构化抽取得到的关系。默认保持；若候选提出调整，必须引用冲突证据并说明为什么原分类不完整。
- `soft`：模型推断、脚本推断、适配器推断或低置信度关系。它只参与候选排序，不能成为排除其他合理拓扑的硬锁。

当 `semantic_verification.status=unresolved`、`semantic_topology.primary_topology=unknown`，或主拓扑为 `soft` 且存在接近的第二候选时，必须保留至少两个合理的结构候选进行比较；不得为了得到确定答案而自动降级为并列结构。

## 并列结构资格门槛

`parallel_set` / `parallel_classification_3_6` 只有在 `semantic_topology.eligibility.peer_set.allowed=true` 时才能作为主候选。以下任一情况存在时不得使用并列结构压平关系：

- 显式方向；
- 顺序或先后；
- 因果；
- 输入—输出或依赖链；
- 多源指向同一结果的收敛；
- 层级、承托或包含；
- 对应、映射或比较；
- 反馈回流。

“出现三至六个模块”“多个标题长度相近”“模块都有动作词”都不能单独证明并列关系。

## 上游就绪条件

正式项目进入视觉阶段前应满足：

- 页面集合、页序和锁定正文已通过上游闸门；
- Source Truth 中的事实、状态、主体、数字和边界可追溯；
- 页面使命、核心结论和来源 ID 已确认；
- Stage 02 handoff 已生成 semantic proposals、verification 和 topology 回执；
- 对 verifier 已判为 `rejected` 的上游关系，不得继续作为视觉权威。

缺少非关键关系时允许以 `unknown` / `neutral` 继续进入候选设计；不得用视觉设计掩盖事实或责任边界缺口。

## 推荐输入优先级

1. Source Truth 中的事实、状态和边界。
2. 已批准页面合同中的页面使命与核心结论。
3. Stage 02 `verified_business_relationships` 与 `semantic_topology`。
4. 已批准逐页脚本中的终稿文字。
5. `semantic_proposals`、原始 `business_relationships`，仅用于冲突追溯。
6. 原脚本草图、视觉形式和构图建议。
7. 本 Skill 默认规则。

## 字段映射

| 上游字段 | 本 Skill 用途 | 处理规则 |
|---|---|---|
| `page_id` | 页面身份 | 原样继承 |
| `page_mission` | 页面使命 | 原样继承，不改成排版任务 |
| `core_judgment` | 核心判断 | 不改变事实强度 |
| `locked_text_items` | 内容锁 | 完整覆盖且只出现一次 |
| `semantic_proposals` | 上游关系追溯 | 不直接决定视觉结构 |
| `semantic_verification` | 关系校验回执 | rejected 不得继续传播 |
| `verified_business_relationships` | 业务关系 | 视觉阶段优先权威 |
| `semantic_topology` | 语义拓扑 | 用于候选资格与排序，不等于版式 |
| `constraint_authority` | 约束强度 | hard / strong / soft 分级处理 |
| `expression_constraints` | 阅读合同 | 不得直接翻译成固定模板 |
| `author_visual_notes` | 作者视觉提示 | `advisory_only` |
| `trace_refs` | 审计追溯 | 不进入可见页面或生图文字 |

## 候选设计规则

- `hard` 拓扑明确时，可只生成一个满足约束的候选；候选仍应自由选择空间语法和视觉载体。
- `strong` 拓扑明确时，至少检查一个替代解释是否被证据排除；无需为了数量编造无效方案。
- `soft` 或 `unknown` 时，应比较 2–3 个真正不同的语义拓扑/空间组织方案。
- 每个候选必须写清 `visual_thesis`、`topology`、`reading_sequence`、`expression_fit` 和选择依据。
- 候选不得通过改颜色、改媒介或交换左右位置伪装成不同结构。
- 不允许因为视觉多样性而改变真实语义；整套重复检查只触发复核，不强制修改语义正确的页面。

## 不允许的降级

- 不把上游推断当作 Source Truth。
- 不用 raw `business_relationships` 覆盖 verifier 已修正或否决的关系。
- 不把 `semantic_topology` 直接翻译为固定版式。
- 不把未知关系自动变成并列关系。
- 不因进入视觉阶段停止回查事实、状态和边界。
- 不用“视觉优化”删除 P0 内容、改变主体责任或改变事项状态。
- 不将讲解词、来源 ID、审核结论和后台元数据画到页面上。
