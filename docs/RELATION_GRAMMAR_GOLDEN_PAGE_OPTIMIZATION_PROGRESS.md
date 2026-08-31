# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch G2 — Grammar 边界回归测试
- 总体状态：进行中
- 已完成：Step 0、Batch A–F、Batch G1.1–G1.2
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch G2.1，验证 Stage2 adapter 派生关系可继续进入 topology_resolver，并修复 confidence 表达兼容问题

## 剩余任务

- [ ] Batch G2.1：Adapter → topology_resolver 跨层兼容
- [ ] Batch G2.2：8 类 Grammar 边界与禁止误读回归
- [ ] Batch H：全量验证与收口

## G1 完成结果

- G1.1：8 个 positive fixtures 已逐页对齐最新黄金页关系节点与 visual relation surface。
- G1.2：新增黄金页文件映射，测试直接读取 8 个 Markdown，检查：
  - `Argument Topology` 与 fixture 一致；
  - `视觉结构` 均含五项合同；
  - directed / mapping / convergence / roadmap / governance / comparison 的 fixture 关系行仍存在于对应黄金页；
  - Parallel 通过并列关键词、无方向与三个兄弟节点检查。

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 下一恢复点 |
|---|---|---|---|---|
| Step 0 / Batch A–F | 完成 | 见历史提交 | 黄金页、Visual Structure Contract 与 Runtime 基础适配完成 | 完成 |
| Batch G1.1 | 完成 | `34d74e5799796cea75c77415f843051842e8a18b` | 8 个正向 fixture 对齐最新黄金页业务关系 | 完成 |
| Batch G1.2 | 完成 | `7ac8fda1311d2586e1f8f86d1c228d39aeb79ba4` | `test_cross_layer_regressions.py` 增加 Golden Page ↔ fixture 文件级一致性回归 | G2 跨层边界 |

## 当前验证状态

- 文档与 executable fixture 已建立自动一致性约束。
- 已知待处理跨层问题：Stage2 adapter 的 `confidence` 使用 `high/medium/low` 字符串，而 `topology_resolver` 当前按 float 直接转换；G2.1 修复这一兼容点后，再让 adapter 派生关系直接跑 semantic topology。
- 尚未触发远端 CI；Batch H 统一执行全量测试。
