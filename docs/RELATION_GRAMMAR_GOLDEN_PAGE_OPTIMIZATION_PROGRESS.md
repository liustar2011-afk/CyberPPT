# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A–E、Batch F1、Batch F2、Batch F3.1、Batch F3.2a
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F3.2b，为 Governance 原子关系边补跨层回归

## 剩余任务

- [ ] Batch F3.2b：Governance 原子边回归测试
- [ ] Batch F4–F9：其余黄金页视觉结构五项合同归一
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 关键文件

- 黄金页：`.agents/skills/cyberppt-script-workflow/references/golden-page-*.md`
- 五项合同：`.agents/skills/cyberppt-script-workflow/references/golden-page-visual-structure-contract.md`
- 跨层回归：`tests/stage1_authoring/test_cross_layer_regressions.py`
- Stage2 adapter：`cyberppt/stage02_relationship_adapter.py`
- Reading contract：`cyberppt/relation_semantics.py`

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 遗留 / 下一恢复点 |
|---|---|---|---|---|
| Step 0 | 完成 | `98d43c27...`、`7e585307...` | 建立分支、台账并完成跨层基线映射 | 完成 |
| Batch A–E | 完成 | 见历史提交 | Relation Grammar 文档重构、上屏微语法和 Notes 增量化 | 完成 |
| Batch F1 | 完成 | `6f07e780691b6b880a6777e30e69157fe9fcf2d4` | 新增五项 Visual Structure Contract | 完成 |
| Batch F2 | 完成 | `2b9930d1...`、`a2b75c91...` | Comparison `A vs B` 无方向解析及回归 | 完成 |
| Batch F3.1 | 完成 | `f363d256a849ef07eba6559f42382976e30fca65` | Governance 五项视觉结构 + 7 条原子关系边 | 完成 |
| Batch F3.2a | 完成 | `9a0d3ef12a80641ac17e4b88fee14648e828f548` | 修正通用有向关系 reading-contract 优先级：存在连续链时优先 `directed_dependency_2_6`，纯 N→1 才落 `support_convergence_3_6` | 下一步：F3.2b 回归 |

## F3.2a 发现与修复

- Governance 图同时存在 3→1 汇入共同控制层，以及共同控制层→受保护结果的后续边。
- 原逻辑先检查多源汇聚，会把这种“汇聚后继续”的治理链误判为 `support_convergence_3_6`。
- 已改为：通用有向关系先检查 `_has_dependency_chain()`，有连续中间节点即使用 `directed_dependency_2_6`；只有无下游链的纯多源汇聚才使用 convergence。
- 显式 `supports / evidence_supports` 的专用分支未调整，Convergence 黄金页不受影响。
