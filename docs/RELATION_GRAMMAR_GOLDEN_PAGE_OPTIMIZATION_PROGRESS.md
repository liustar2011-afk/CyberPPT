# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch G2 — Grammar 边界回归测试
- 总体状态：进行中
- 已完成：Step 0、Batch A–F、Batch G1、Batch G2.1a–G2.1b
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch G2.2，补 Relation Grammar 边界与禁止误读回归

## 剩余任务

- [ ] Batch G2.2：Grammar 边界与禁止误读回归
- [ ] Batch H：全量验证与收口

## G2.1 完成结果

- G2.1a：`topology_resolver` 同时兼容数值和 `high / medium / low` confidence。
- G2.1b：8 个 positive fixtures 的 `visual_structure` 统一先经 `derive_business_relationships()`，再送入 `resolve_semantic_topology()`；预期必须与各自黄金页 semantic topology 一致。
- 该回归同时覆盖：Parallel structural fallback、Flow feedback、Causal causes、Convergence supports、Mapping problem_response、Comparison non-directional vs、Roadmap sequence、Governance generic directed chain。

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 下一恢复点 |
|---|---|---|---|---|
| Step 0 / Batch A–F | 完成 | 见历史提交 | 黄金页、Visual Structure Contract 与 Runtime 基础适配完成 | 完成 |
| Batch G1 | 完成 | `34d74e57...`、`7ac8fda1...` | fixture 对齐 + Golden Page ↔ fixture 文件级回归 | 完成 |
| Batch G2.1a | 完成 | `1bc20328db175de17bae040119142a9946777d26` | topology confidence 兼容修复 | 完成 |
| Batch G2.1b | 完成 | `4ab121ed0c5ed7e1cfd965dfa363449fd32a4c0a` | 新增 8 类 Adapter → topology 跨层回归 | G2.2 Grammar 边界 |

## 当前验证状态

- 新增回归已写入既有 `test_cross_layer_regressions.py`。
- 尚未执行全量测试；Batch H 统一执行并修复实际失败。
