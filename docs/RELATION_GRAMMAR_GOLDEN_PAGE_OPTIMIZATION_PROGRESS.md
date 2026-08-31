# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A–E、Batch F1–F7、Batch F8a
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F8b，归一 Comparison 五项视觉结构合同并使用 `A vs B：对照比较`

## 剩余任务

- [ ] Batch F8b：Comparison 五项视觉结构合同
- [ ] Batch F9：Roadmap 五项视觉结构合同
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 下一恢复点 |
|---|---|---|---|---|
| Step 0 / Batch A–E | 完成 | 见历史提交 | 基线、Relation Grammar 重构、微语法与 Notes 增量化 | 完成 |
| Batch F1 | 完成 | `6f07e780...` | 新增 Visual Structure 五项合同 | 完成 |
| Batch F2 | 完成 | `2b9930d1...`、`a2b75c91...` | Comparison 无方向解析及回归 | 完成 |
| Batch F3 | 完成 | `f363d256...`、`9a0d3ef1...`、`920a789e...` | Governance 原子边、reading-contract 修复及回归 | 完成 |
| Batch F4–F7 | 完成 | `2be66f90...`、`309200d9...`、`3c59189a...`、`05269ec6...` | Parallel / Flow / Causal / Convergence 五项合同 | 完成 |
| Batch F8a | 完成 | `be44bc545ac1f4a76abe38d5ea47c6b42d0c93e7` | Mapping 五项合同；保留 `Problem → Response`、真实 Cardinality、四条独立 `问题回应` 原子边 | F8b Comparison |

## 当前验证状态

- Mapping 继续走现有显式箭头解析，不需要 Runtime 新逻辑。
- Comparison `vs` 与 Governance 链均已有专门跨层回归。
- 尚未触发远端 CI；Batch H 统一执行全量测试。
