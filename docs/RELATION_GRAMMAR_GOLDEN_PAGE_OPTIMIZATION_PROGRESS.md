# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 维护规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件追加一条进度记录，写明完成内容、改动文件、实现 commit、测试结果、已发现问题、剩余任务和下一恢复点。

## 总体状态

- 当前阶段：Batch C2 — Convergence 输入角色优化
- 总体状态：进行中
- 已完成：开发分支建立；独立进度台账初始化；8 类黄金页与跨层关系链路完成基线映射；8 页统一 Relation Contract 与横向 Grammar 边界表完成；Governance、Comparison、Causal、Parallel 优化完成
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把 AUTHOR/CRITIQUE 的生成式判断硬编码成低精度 lint
- 下一恢复点：优化 Convergence 的输入角色命名，使各输入都以“独立贡献 → 共同结果”的同一语义尺度进入汇聚点

## 已确认的现状映射

- 黄金页索引：`.agents/skills/cyberppt-script-workflow/references/golden-page-script-example.md`
- 8 个黄金页：同目录 `golden-page-parallel.md`、`golden-page-flow.md`、`golden-page-causal.md`、`golden-page-convergence.md`、`golden-page-mapping.md`、`golden-page-comparison.md`、`golden-page-roadmap.md`、`golden-page-governance.md`
- AUTHOR 操作权威：`.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`
- 正向 fixture：`tests/stage1_authoring/fixtures.py`
- 跨层回归：`tests/stage1_authoring/test_cross_layer_regressions.py`
- semantic topology：`cyberppt/topology_resolver.py`
- relation expression：`cyberppt/relation_semantics.py`
- Stage2 relationship adapter：`cyberppt/stage02_relationship_adapter.py`

## 任务清单

- [x] Step 0：仓库基线盘点与映射
- [x] Batch A：统一黄金页面模板与 Relation Contract
- [x] Batch B1：Governance 重构
- [x] Batch B2：Comparison 重构
- [x] Batch B3：Causal 收紧真实因果
- [x] Batch C1：Parallel 同层尺度统一
- [ ] Batch C2：Convergence 输入角色优化
- [ ] Batch D1：Flow 增加真实业务交接物
- [ ] Batch D2：Roadmap 增加状态化进入条件与起终点
- [ ] Batch D3：Mapping 修正方向与 Cardinality
- [ ] Batch E：Onscreen 微语法与 Speaker Notes 去重
- [ ] Batch F：统一视觉结构合同
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 进度记录

### Step 0.1 — 初始化本轮开发台账

- 状态：完成
- 完成内容：
  - 建立独立开发分支 `agent/relation-grammar-golden-page-20260831`。
  - 新建本进度文件，固定“小步骤、立即提交、立即记录”的恢复机制。
  - 将开发任务拆分到可单独验证的最小步骤。
- 改动文件：
  - `docs/RELATION_GRAMMAR_GOLDEN_PAGE_OPTIMIZATION_PROGRESS.md`
- 实现 commit：`98d43c2750f0f8b96682d39b1fad5d59e350d534`
- 测试结果：无代码改动，不适用。
- 已发现问题：初始化时尚未完成仓库文件映射。
- 剩余任务：见“任务清单”。
- 下一恢复点：读取仓库目录与关键入口，形成黄金页 → fixture → topology → Stage2 expression → tests 的现状映射。

### Step 0.2 — 完成 Relation Grammar 跨层基线映射

- 状态：完成
- 完成内容：
  - 定位全部 8 类黄金页及索引文件。
  - 定位现有正向 fixture 和跨层回归入口。
  - 确认 `resolve_semantic_topology()` 位于 `cyberppt/topology_resolver.py`。
  - 确认 Stage2 从 `visual_structure` 恢复关系的入口为 `derive_business_relationships()`。
  - 确认现有 fixture 已覆盖 8 类 Grammar，但文档与 fixture 仍存在语义漂移：Comparison fixture 仍使用方向箭头；Governance fixture 使用通用 dependency chain，未对应黄金页的 Actor/Responsibility/Control/Outcome；Convergence fixture 与黄金页业务输入不同。
- 改动文件：
  - `docs/RELATION_GRAMMAR_GOLDEN_PAGE_OPTIMIZATION_PROGRESS.md`
- 实现 commit：只读盘点，无代码实现 commit；本条由进度记录提交承载。
- 测试结果：完成静态链路核对；尚未执行代码测试。
- 已发现问题：
  - `stage02_relationship_adapter.py` 当前主要依赖显式 `A → B：关系标签` 或少量结构关键词；新的五项视觉合同需要在 Batch G/F 期间验证不会丢关系。
  - 文档示例与 executable fixture 尚未建立直接一致性约束。
- 剩余任务：Batch A–H。
- 下一恢复点：Batch A，先更新索引和统一 Relation Contract，再逐页补齐模板。

### Batch A — 统一黄金页面模板与 Relation Contract

- 状态：完成
- 完成内容：
  - 在黄金页索引增加 8 类 Grammar 的横向边界判别表，明确“何时使用 / 易混关系 / 最小区分规则”。
  - 为 8 个黄金页统一增加 `Relation Contract`，固定六项：Node Role、Edge Semantics、Direction / Cardinality、Invariant、Confusable With、Disambiguation Rule。
  - 明确 Parallel / Convergence、Flow / Causal / Roadmap、Mapping / Comparison、Governance / Parallel 等高混淆关系的判别边界。
  - 保持 AUTHOR Contract 为唯一操作权威；Relation Contract 仅作为黄金示例教学层，不进入 Final Script schema，不形成新的 Stage1 authoritative IR。
- 改动文件与实现 commit：
  - `golden-page-script-example.md`：`1c949e0c1e2f047a0441bd9a3a9f6e79d3675a75`
  - `golden-page-parallel.md`：`4b09b5dea079d2a408c5f124cd7a178977ad3f1f`
  - `golden-page-flow.md`：`97bc03b469edd4d3adc4a2225ac035c6cd835d0b`
  - `golden-page-causal.md`：`36895005bd439549415791b548dfa4bb3b8c80f0`
  - `golden-page-convergence.md`：`6b95c21fc186a69641be649c366984cb432b142b`
  - `golden-page-mapping.md`：`75a4d44e787d1de822c98b3f6f3f7436fb9c695e`
  - `golden-page-comparison.md`：`c234a92ec5c0e49ae9ddfd15e50492bfc5f70566`
  - `golden-page-roadmap.md`：`1b192d4c2b373f73353cd6cb92a55b86ec99c64c`
  - `golden-page-governance.md`：`fbd4493cfbdaed34b34554c4d8a8126b2cf5b7d2`
- 测试结果：文档结构变更；逐页静态核对 8 个 Relation Contract 已存在，未改 Runtime 代码。
- 已发现问题：
  - Governance 的正文与上屏仍把“会商审校与发布机制”放在第四个同层 Relation Unit，与新 Contract 的分层要求不完全一致。
  - Comparison 的上屏与 fixture 仍以方向箭头表达状态差异，存在误读为演进流程的风险。
  - Causal 的现有四节点链中仍混有“叙事递进”和“真实因果”，需要进一步收紧。
- 剩余任务：Batch B1–H。
- 下一恢复点：Batch B1，先重构 Governance 页面本体，再同步 fixture / adapter 的跨层语义。

### Batch B1 — Governance：分离 Actor 与共同控制层

- 状态：完成
- 完成内容：
  - 将 Governance 的 Relation Units 从“四个同层模块”调整为三个真正的责任主体绑定：业务牵头方、数据责任方、分析执行方。
  - 将会商审校、发布授权、复盘留痕独立为“共同控制机制”，明确其跨主体控制作用。
  - 单独增加“受保护结果”，将结论口径一致、来源可追溯、过程可复核、变更有记录作为最终治理输出。
  - 重写上屏层级为“责任主体与责任对象 → 共同控制机制 → 受保护结果”，避免共同控制机制被误读为第四责任主体。
  - 更新视觉结构和作者自检，明确三条责任线汇入共同治理层。
- 改动文件：
  - `.agents/skills/cyberppt-script-workflow/references/golden-page-governance.md`
- 实现 commit：`1b26d08fdde93e456b7633f1327c6a1d45a53445`
- 测试结果：静态语义核对通过；本步仅改黄金示例文档，Runtime 测试留到 Batch G/H 统一执行。
- 已发现问题：现有 `tests/stage1_authoring/fixtures.py` 中 Governance 仍是“使用申请 → 授权决策 → 受控调用 → 审计记录”的通用 dependency chain，与当前黄金页语义不一致，需在 Batch G1 同步。
- 剩余任务：Batch B2–H。
- 下一恢复点：Batch B2，修正 Comparison 的“状态差异被箭头误读为方向关系”问题。

### Batch B2 — Comparison：固定双列、移除方向箭头

- 状态：完成
- 完成内容：
  - 将 Relation Units 从“状态 A ↔ 状态 B”改为“评价维度｜分散方式状态｜统一体系状态”，固定比较对象与评价维度。
  - 将上屏文字中的四组 `A → B` 全部改为同维度下的双对象证据，消除流程方向语义。
  - 更新主论证链为“固定比较对象 × 共同评价维度 → 差异结论”。
  - 更新视觉结构，明确固定双列、稳定行头，通过列位、对齐、栏头和差异强调建立 Comparison，不使用流程箭头。
  - 更新作者自检，新增“比较对象之间没有方向箭头”的硬性检查。
- 改动文件：
  - `.agents/skills/cyberppt-script-workflow/references/golden-page-comparison.md`
- 实现 commit：`df4b65c47753a758a33878557c939cf6c2baccd7`
- 测试结果：静态语义核对通过；未改 Runtime 代码。
- 已发现问题：现有 Stage2 adapter 的正向 Comparison fixture 依赖 `分散预测模式 → 统一预测体系：对照比较` 才能恢复 `comparison`，与新黄金页的无方向表达不一致；需在 Batch F/G 补充无箭头的 Comparison 结构识别。
- 剩余任务：Batch B3–H。
- 下一恢复点：Batch B3，收紧 Causal 的边语义，只保留可明确解释的真实因果。

### Batch B3 — Causal：收缩为逐边可证明的真实因果链

- 状态：完成
- 完成内容：
  - 将原“业务对象扩展 → 分析要求增加 → 能力缺口 → 能力升级”叙事链重构为可逐边证明的业务因果链。
  - 新链固定为“数据口径和版本分散 → 同一指标计算基准不一致 → 跨周期结论难以校核 → 预测偏差难以追溯 → 风险预警难以持续更新”。
  - 每个 Relation Unit 改写为“前因造成的直接后果”，确保全部边可通过“因为 A，所以 B”测试。
  - 在视觉结构中加入四条显式 `A → B：因果导致` 关系，便于 Stage2 恢复真实 causal semantics。
  - 更新 Speaker Notes 与作者自检，移除实施步骤、交接阶段等 Flow / Roadmap 语义。
- 改动文件：
  - `.agents/skills/cyberppt-script-workflow/references/golden-page-causal.md`
- 实现 commit：`b14788dd4d887161419b30c9f20b0f2a17dd8721`
- 测试结果：静态逐边“因为 A，所以 B”核对通过；Runtime 统一验证留到 Batch G/H。
- 已发现问题：正向 fixture 的 causal case 已使用“数据口径不一致 → 跨周期结论不可比 → 风险判断难以持续复盘”，方向与新黄金页一致，但节点细度和最终业务影响仍需 Batch G1 对齐。
- 剩余任务：Batch C1–H。
- 下一恢复点：Batch C1，统一 Parallel 三个兄弟单元的业务尺度与命名句法。

### Batch C1 — Parallel：统一兄弟单元的语义尺度与句法

- 状态：完成
- 完成内容：
  - 将三个兄弟单元统一为同一业务尺度的能力维度：研判范围、周期规则、运行机制。
  - Relation Units 统一采用“维度名｜该维度承担的建设动作”句法。
  - 明确三个兄弟单元都回答同一上位问句：“统一预测体系需要建设哪一个能力维度？”
  - 重写上屏证据，使三个分组的信息深度、标题句法和视觉权重一致。
  - 更新视觉结构，明确三组均直接支撑总论，兄弟之间不建立箭头、先后或因果关系。
- 改动文件：
  - `.agents/skills/cyberppt-script-workflow/references/golden-page-parallel.md`
- 实现 commit：`bd323d56afa606ae68d6c12e8f63586dd6e87fa8`
- 测试结果：静态同层问句检查通过；Runtime 统一验证留到 Batch G/H。
- 已发现问题：现有 fixture 使用“研判范围 / 周期规则 / 运行闭环”，其中第三项命名仍需在 Batch G1 与黄金页“运行机制”对齐。
- 剩余任务：Batch C2–H。
- 下一恢复点：Batch C2，统一 Convergence 各输入的角色尺度与共同结果表达。
