# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A–E、Batch F1–F7
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F8，归一 Mapping / Comparison 五项视觉结构合同

## 剩余任务

- [ ] Batch F8：Mapping / Comparison 五项视觉结构合同
- [ ] Batch F9：Roadmap 五项视觉结构合同
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 下一恢复点 |
|---|---|---|---|---|
| Step 0 / Batch A–E | 完成 | 见历史提交 | 基线、Relation Grammar 重构、微语法与 Notes 增量化 | 完成 |
| Batch F1 | 完成 | `6f07e780...` | 新增 Visual Structure 五项合同 | 完成 |
| Batch F2 | 完成 | `2b9930d1...`、`a2b75c91...` | Comparison `A vs B` 无方向解析及回归 | 完成 |
| Batch F3 | 完成 | `f363d256...`、`9a0d3ef1...`、`920a789e...` | Governance 原子边、reading-contract 修复及回归 | 完成 |
| Batch F4 | 完成 | `2be66f90...` | Parallel 五项合同 | 完成 |
| Batch F5 | 完成 | `309200d9...` | Flow 五项合同 | 完成 |
| Batch F6 | 完成 | `3c59189a...` | Causal 五项合同 | 完成 |
| Batch F7 | 完成 | `05269ec60c4db325fc59289153aebb7c7a3d8047` | Convergence 五项合同；明确纯 N→1 汇聚、共同结果为终点、输入间无关系 | F8 Mapping / Comparison |

## 当前验证状态

- Convergence 保留显式 `共同支撑` 关系，走专用 support relation 分支，不受 Governance generic-chain 优先级修复影响。
- Comparison / Governance 新跨层回归已写入既有测试文件。
- 尚未触发远端 CI；Batch H 统一执行全量测试。
