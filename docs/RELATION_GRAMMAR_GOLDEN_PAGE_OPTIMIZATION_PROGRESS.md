# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A–E、Batch F1、Batch F2、Batch F3、Batch F4
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F5，归一 Flow 五项视觉结构合同

## 剩余任务

- [ ] Batch F5：Flow 五项视觉结构合同
- [ ] Batch F6：Causal 五项视觉结构合同
- [ ] Batch F7：Convergence 五项视觉结构合同
- [ ] Batch F8：Mapping / Comparison 五项视觉结构合同
- [ ] Batch F9：Roadmap 五项视觉结构合同
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 下一恢复点 |
|---|---|---|---|---|
| Step 0 / Batch A–E | 完成 | 见历史提交 | 基线、Relation Contract、重点页重构、微语法与 Notes 增量化 | 完成 |
| Batch F1 | 完成 | `6f07e780...` | 新增 Visual Structure 五项合同 | 完成 |
| Batch F2 | 完成 | `2b9930d1...`、`a2b75c91...` | Comparison `A vs B` 无方向解析及回归 | 完成 |
| Batch F3 | 完成 | `f363d256...`、`9a0d3ef1...`、`920a789e...` | Governance 原子边、reading-contract 优先级修复及回归 | 完成 |
| Batch F4 | 完成 | `2be66f90abc528ea70cb2bfed46b61543b37319e` | Parallel `视觉结构` 归一为五项合同；明确 peer classification、兄弟无方向、N→1 上位支撑和禁止流程化 | F5 Flow |

## 当前验证状态

- Comparison 与 Governance 新跨层回归已写入既有测试文件。
- Parallel 保留“并列分类 / 同级 / 相互独立”等现有 adapter 可识别关键词，不制造方向箭头。
- 尚未触发远端 CI；Batch H 统一执行全量测试。
