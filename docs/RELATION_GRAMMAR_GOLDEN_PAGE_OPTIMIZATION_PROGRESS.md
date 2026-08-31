# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A–E、Batch F1、Batch F2、Batch F3.1–F3.2b
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F4，归一 Parallel 视觉结构五项合同

## 剩余任务

- [ ] Batch F4：Parallel 五项视觉结构合同
- [ ] Batch F5：Flow 五项视觉结构合同
- [ ] Batch F6：Causal 五项视觉结构合同
- [ ] Batch F7：Convergence 五项视觉结构合同
- [ ] Batch F8：Mapping / Comparison 五项视觉结构合同
- [ ] Batch F9：Roadmap 五项视觉结构合同
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
| Batch F3.2a | 完成 | `9a0d3ef12a80641ac17e4b88fee14648e828f548` | 通用有向关系有连续中间节点时优先 `directed_dependency_2_6` | 完成 |
| Batch F3.2b | 完成 | `920a789ed6bec51dad72f467254ade0814e7baa6` | 新增 Governance 回归：7 条边、3 条入控制层、1 条出控制层、reading contract 为 `directed_dependency_2_6` | 下一步：F4 Parallel |

## 当前验证状态

- Comparison 与 Governance 的新跨层用例已写入既有回归文件。
- 尚未触发远端 CI；Batch H 统一执行全量测试并处理可能的历史兼容问题。
