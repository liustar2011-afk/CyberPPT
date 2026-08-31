# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch E — Onscreen 微语法与 Speaker Notes 去重
- 总体状态：进行中
- 已完成：Step 0、Batch A、Batch B1–B3、Batch C1–C2、Batch D1–D3、Batch E1 Parallel
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch E2 Flow，统一“阶段｜产出 / 交接｜内容 / 回写｜内容”微语法，并让备注只解释交接判别与误读风险

## 剩余任务

- [ ] Batch E2：Flow 上屏微语法与备注去重
- [ ] Batch E3：Causal 上屏微语法与备注去重
- [ ] Batch E4：Convergence 上屏微语法与备注去重
- [ ] Batch E5：Mapping 上屏微语法与备注去重
- [ ] Batch E6：Comparison 上屏微语法与备注去重
- [ ] Batch E7：Roadmap 上屏微语法与备注去重
- [ ] Batch E8：Governance 上屏微语法与备注去重
- [ ] Batch F：统一视觉结构合同
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 已确认链路

`Golden Page → Final Script 视觉结构 → stage02_relationship_adapter → topology_resolver / relation_semantics → Stage2 expression`

关键文件：
- 黄金页：`.agents/skills/cyberppt-script-workflow/references/golden-page-*.md`
- AUTHOR 权威：`.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`
- 正向 fixture：`tests/stage1_authoring/fixtures.py`
- 跨层回归：`tests/stage1_authoring/test_cross_layer_regressions.py`
- Semantic topology：`cyberppt/topology_resolver.py`
- Relation expression：`cyberppt/relation_semantics.py`
- Stage2 adapter：`cyberppt/stage02_relationship_adapter.py`

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 遗留 / 下一恢复点 |
|---|---|---|---|---|
| Step 0.1 初始化台账 | 完成 | `98d43c2750f0f8b96682d39b1fad5d59e350d534` | 建立开发分支和单一进度文件 | 下一步：仓库映射 |
| Step 0.2 跨层基线映射 | 完成 | 只读盘点；进度提交 `7e585307f34f444d5d05eb388a195ca6abe3d5b9` | 定位 8 类黄金页、fixture、topology、Stage2 adapter、测试入口 | 发现文档与 fixture 存在语义漂移 |
| Batch A 统一 Relation Contract | 完成 | 索引 `1c949e0c...`；Parallel `4b09b5de...`；Flow `97bc03b4...`；Causal `36895005...`；Convergence `6b95c21f...`；Mapping `75a4d44e...`；Comparison `c234a92e...`；Roadmap `1b192d4c...`；Governance `fbd4493c...` | 8 页统一六项 Relation Contract；索引增加横向 Grammar 边界 | 下一步：逐页修正文档与 Contract 不一致处 |
| Batch B1 Governance | 完成 | `1b26d08fdde93e456b7633f1327c6a1d45a53445` | 三个 Actor 分别绑定 Responsibility Object；会商审校/发布授权/复盘留痕独立为共同控制层；增加 Protected Outcome | fixture 仍为通用 dependency chain；Batch G1 对齐 |
| Batch B2 Comparison | 完成 | `df4b65c47753a758a33878557c939cf6c2baccd7` | 固定双列与共同评价维度；移除对象之间方向箭头 | Stage2 adapter 目前依赖箭头识别 comparison；Batch F/G 修正 |
| Batch B3 Causal | 完成 | `b14788dd4d887161419b30c9f20b0f2a17dd8721` | 因果链收缩为“口径/版本分散 → 基准不一致 → 跨周期难校核 → 偏差难追溯 → 预警难持续更新”；每条边可通过“因为 A，所以 B” | fixture 节点细度待 Batch G1 对齐 |
| Batch C1 Parallel | 完成 | `bd323d56afa606ae68d6c12e8f63586dd6e87fa8` | 三个兄弟单元统一为“研判范围 / 周期规则 / 运行机制”，统一句法和业务尺度 | fixture 第三项仍为“运行闭环”；Batch G1 对齐 |
| Batch C2 Convergence | 完成 | `3ce2b3e5c53677c17ad1bc1dcdf2d1e04dd4faa6` | 输入角色统一为“供给边界 / 需求压力 / 互济缓释 / 波动扰动”，四条输入显式汇入共同结果 | fixture 业务输入不同；Batch G1 对齐 |
| Batch D1 Flow | 完成 | `b85a5b702f77dc43c88811589fa4d47cd7093ee9` | 三条正向边增加真实交接物，反馈边增加明确回写物；视觉结构保留“顺序衔接 / 反馈回流”关系标签 | fixture 需补交接信息但保持 feedback_loop 解析 |
| Batch D2 Roadmap | 完成 | `a404c1a253b96ea5e4bc053c9b4b50f635dd53f8` | 固定 Current State S0、S1/S2/S3 新状态、进入条件和 Target State；箭头只表达满足条件后的状态跃迁 | fixture 需补 S0/S1/S2/S3 与进入条件语义；Batch G1 对齐 |
| Batch D3 Mapping | 完成 | `519f0f22bce685e21c6f2583e9a4641be58cff1a` | 清理 `↔`；固定 `Problem → Response` 单向语义；四组关系显式标注 1:1；视觉结构增加可被 Stage2 adapter 直接解析的“问题回应”关系边 | Batch G1 对齐 fixture；Batch F 统一视觉合同格式 |
| Batch E1 Parallel | 完成 | `5531a74a7952dd1ea0c3ef9a61e54442050e6751` | 保留“维度名｜建设动作”上屏微语法；Speaker Notes 改为解释同层判别、边界和误读风险，不再按上屏顺序复述三项内容 | 下一步：Flow 微语法 |

## Batch D2 详细验收

- Current State S0 已显式：周期业务已存在，数据口径、版本规则和判断尺度仍相对分散。
- Stage 1–3 均同时包含“进入条件 + 新状态”。
- S1、S2 实际成为下一阶段进入条件，避免空跳。
- Target State S3 已显式：共同输入可复用、跨周期结论可校核、偏差可追溯、复盘可持续回写。
- 视觉结构使用 `顺序演进｜进入条件：...`，保留 sequence semantics，同时说明状态跃迁依据。
- 本步仅改黄金页文档；Runtime 回归统一放在 Batch G/H。

## Batch D3 详细验收

- 主论证链已由对称 `↔` 改为单向 `Problem → Response`。
- 四个 Relation Units 均显式标注 1:1，避免视觉对称被误读为双向作用。
- Relation Contract 明确：映射方向表示“问题由哪项能力响应”，不代表流程、状态演进或双向影响。
- 视觉结构新增四条独立 `A → B：问题回应` 关系边，现有 `stage02_relationship_adapter` 可直接恢复为 mapping semantics。
- 本步未新增任何 Final Script 字段，Cardinality 仅作为黄金页语义约束和可读标记存在。
