# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A、Batch B1–B3、Batch C1–C2、Batch D1–D3、Batch E1–E8、Batch F1、Batch F2.1
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F2.2，为 Comparison `A vs B` 无方向解析增加专门回归测试

## 剩余任务

- [ ] Batch F2.2：Comparison adapter 回归测试
- [ ] Batch F3：Governance 原子关系边与解析保真
- [ ] Batch F4–F9：其余黄金页视觉结构五项合同归一
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 已确认链路

`Golden Page → Final Script 视觉结构 → stage02_relationship_adapter → topology_resolver / relation_semantics → Stage2 expression`

关键文件：
- 黄金页：`.agents/skills/cyberppt-script-workflow/references/golden-page-*.md`
- 视觉结构五项合同：`.agents/skills/cyberppt-script-workflow/references/golden-page-visual-structure-contract.md`
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
| Step 0.2 跨层基线映射 | 完成 | 进度提交 `7e585307f34f444d5d05eb388a195ca6abe3d5b9` | 定位 8 类黄金页、fixture、topology、Stage2 adapter、测试入口 | 发现文档与 fixture 语义漂移 |
| Batch A | 完成 | 索引及 8 页提交 | 统一 Relation Contract 与 Grammar 横向边界 | 完成 |
| Batch B1–B3 | 完成 | `1b26d08f...`、`df4b65c4...`、`b14788dd...` | Governance / Comparison / Causal 关系重构 | 完成 |
| Batch C1–C2 | 完成 | `bd323d56...`、`3ce2b3e5...` | Parallel 同层尺度、Convergence 输入角色优化 | 完成 |
| Batch D1–D3 | 完成 | `b85a5b70...`、`a404c1a2...`、`519f0f22...` | Flow 交接物、Roadmap 状态链、Mapping 方向与 Cardinality | 完成 |
| Batch E1–E8 | 完成 | `5531a74a...` 至 `65cc4da9...` | 8 页上屏微语法；Speaker Notes 改为增量判别信息 | 完成 |
| Batch F1 Visual Structure Contract | 完成 | `6f07e780691b6b880a6777e30e69157fe9fcf2d4` | 新增五项视觉结构合同、原子边规范和无方向 Comparison `vs` 表达 | 完成 |
| Batch F2.1 Comparison adapter | 完成 | `2b9930d117507c0df553c9c8b46773b4d484f95a` | `stage02_relationship_adapter` 新增 `A vs B` 解析；产出 `comparison` + `direction=unspecified`；箭头路径不变 | 下一步：F2.2 回归测试 |

## Batch F2.1 验收

- 新增 `_COMPARISON_RE` 和 `比较对象｜` 前缀解析。
- `A vs B：对照比较` 通过 `_relation_record(..., directional=False)` 生成无方向关系。
- `derive_business_relationships()` 仍优先解析显式箭头；没有箭头时再解析 Comparison pair；既有 Flow / Causal / Mapping 行为不被改写。
- 未新增 Final Script 字段，Comparison 可读表达与 Runtime relationship 之间建立了最小适配层。
