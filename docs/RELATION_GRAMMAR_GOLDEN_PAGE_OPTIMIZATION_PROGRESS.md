# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch G1 — Golden Page ↔ fixture 映射
- 总体状态：进行中
- 已完成：Step 0、Batch A–F
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch G1.1，更新 `tests/stage1_authoring/fixtures.py`，让 8 个 executable positive fixtures 与当前黄金页关系语义逐一一致

## 剩余任务

- [ ] Batch G1.1：8 个正向 fixture 对齐黄金页
- [ ] Batch G1.2：补 Golden Page ↔ fixture 一致性断言
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## Batch F 完成结果

- F1：建立统一 Visual Structure 五项合同：视觉对象、关系语义、方向/Cardinality、分组/层级、禁止误读。
- F2：Stage2 adapter 支持无方向 `A vs B：对照比较`，并补 Comparison 回归。
- F3：Governance 增加原子责任/控制边；修正通用有向关系“汇聚后继续”时的 reading-contract 优先级；补治理链回归。
- F4：Parallel 五项合同完成。
- F5：Flow 五项合同完成。
- F6：Causal 五项合同完成。
- F7：Convergence 五项合同完成。
- F8a：Mapping 五项合同完成。
- F8b：Comparison 五项合同完成。
- F9：Roadmap 五项合同完成。

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 下一恢复点 |
|---|---|---|---|---|
| Step 0 / Batch A–E | 完成 | 见历史提交 | 基线、Relation Grammar 重构、微语法与 Notes 增量化 | 完成 |
| Batch F1 | 完成 | `6f07e780691b6b880a6777e30e69157fe9fcf2d4` | Visual Structure 五项合同 | 完成 |
| Batch F2 | 完成 | `2b9930d117507c0df553c9c8b46773b4d484f95a`、`a2b75c91bc7feaf57eec8721fc5aeb48009e9295` | Comparison `vs` 无方向解析及回归 | 完成 |
| Batch F3 | 完成 | `f363d256a849ef07eba6559f42382976e30fca65`、`9a0d3ef12a80641ac17e4b88fee14648e828f548`、`920a789ed6bec51dad72f467254ade0814e7baa6` | Governance 原子边、reading-contract 修复及回归 | 完成 |
| Batch F4 | 完成 | `2be66f90abc528ea70cb2bfed46b61543b37319e` | Parallel 五项合同 | 完成 |
| Batch F5 | 完成 | `309200d98c28d8f75e876f26942ceb072ec2e8c7` | Flow 五项合同 | 完成 |
| Batch F6 | 完成 | `3c59189afd2803c004727144c612411ee6f2131f` | Causal 五项合同 | 完成 |
| Batch F7 | 完成 | `05269ec60c4db325fc59289153aebb7c7a3d8047` | Convergence 五项合同 | 完成 |
| Batch F8a | 完成 | `be44bc545ac1f4a76abe38d5ea47c6b42d0c93e7` | Mapping 五项合同 | 完成 |
| Batch F8b | 完成 | `8111c0bfc615f5d9f1fb70a3f554510ed4949ea8` | Comparison 五项合同；使用 non-directional `A vs B` | 完成 |
| Batch F9 | 完成 | `d3fe7414dbdd80e50340bf32006fa8c52255e880` | Roadmap 五项合同；S0–S3、进入条件、状态跃迁和禁止误读全部显式化 | G1 fixture 对齐 |

## 当前验证状态

- 8 类黄金页均已完成统一 Relation Contract、上屏微语法、增量 Speaker Notes 和五项 Visual Structure Contract。
- Comparison、Governance 已新增专门跨层回归；其余关系仍由现有 fixtures 覆盖，但 fixtures 与最新黄金页存在业务语义漂移，Batch G1 开始对齐。
- 尚未触发远端 CI；Batch H 统一执行全量测试并处理历史兼容问题。
