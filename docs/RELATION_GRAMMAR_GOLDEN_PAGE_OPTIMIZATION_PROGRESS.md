# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A–E、Batch F1、Batch F2.1–F2.2
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F3，给 Governance 增加可解析的原子责任/控制关系边，并验证不会把控制机制误当第四 Actor

## 剩余任务

- [ ] Batch F3：Governance 原子关系边与解析保真
- [ ] Batch F4–F9：其余黄金页视觉结构五项合同归一
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 关键文件

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
| Step 0 | 完成 | `98d43c27...`、`7e585307...` | 建立分支、台账并完成跨层基线映射 | 完成 |
| Batch A | 完成 | 索引及 8 页提交 | 统一 Relation Contract 与 Grammar 横向边界 | 完成 |
| Batch B | 完成 | `1b26d08f...`、`df4b65c4...`、`b14788dd...` | Governance / Comparison / Causal 关系重构 | 完成 |
| Batch C | 完成 | `bd323d56...`、`3ce2b3e5...` | Parallel 同层尺度、Convergence 输入角色优化 | 完成 |
| Batch D | 完成 | `b85a5b70...`、`a404c1a2...`、`519f0f22...` | Flow 交接物、Roadmap 状态链、Mapping 方向与 Cardinality | 完成 |
| Batch E | 完成 | `5531a74a...` 至 `65cc4da9...` | 8 页上屏微语法；Speaker Notes 增量化 | 完成 |
| Batch F1 | 完成 | `6f07e780691b6b880a6777e30e69157fe9fcf2d4` | 新增五项视觉结构合同、原子边规范和无方向 Comparison `vs` 表达 | 完成 |
| Batch F2.1 | 完成 | `2b9930d117507c0df553c9c8b46773b4d484f95a` | Stage2 adapter 新增 `A vs B` 解析，产出 non-directional `comparison` | 完成 |
| Batch F2.2 | 完成 | `a2b75c91bc7feaf57eec8721fc5aeb48009e9295` | 跨层回归新增 `A vs B` 用例，断言 subject/object、`comparison`、`direction=unspecified` 与 `comparison_2col` | 下一步：F3 Governance |

## 当前验证状态

- F2.2 已把自动回归用例写入仓库；本轮尚未触发远端 CI，全量执行统一放在 Batch H。
- 新测试与既有跨层测试共用 `derive_business_relationships()` 和 `resolve_relation_expression()`，没有创建第二套测试入口。
