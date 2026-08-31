# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch H — 全量验证与收口
- 总体状态：进行中
- 已完成：Step 0、Batch A–G
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch H1，拉取当前分支并执行 relation-grammar 聚焦测试；根据实际失败逐项修复

## 剩余任务

- [ ] Batch H1：聚焦回归实际执行
- [ ] Batch H2：相关 Stage1 / Stage2 测试执行
- [ ] Batch H3：全量测试与最终收口

## G2.2 边界回归

新增四组跨层边界断言：

1. Parallel ↔ Convergence：peer classification 与 pure N→1 support convergence 必须保持不同 topology，Convergence 不具备 peer-set eligibility。
2. Flow ↔ Causal ↔ Roadmap：分别保留 feedback/交接、causes、进入条件驱动 sequence；检查 `交接物 / 因果导致 / 进入条件` 不互相串用。
3. Mapping ↔ Comparison：Mapping 保持 `subject_to_objects` 的 `problem_response`；Comparison 保持 `direction=unspecified` 的 `comparison` 与 `vs` 表面。
4. Governance ↔ Convergence ↔ Parallel：Governance 必须存在“既有入边又有出边”的共同控制中间节点；Convergence 共同结果只能作为终点；Parallel 保持单一 peer-classification 关系。

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 下一恢复点 |
|---|---|---|---|---|
| Step 0 / Batch A–F | 完成 | 见历史提交 | 黄金页与 Visual Structure Runtime 合同完成 | 完成 |
| Batch G1 | 完成 | `34d74e57...`、`7ac8fda1...` | fixture 对齐 + 文档↔fixture 文件级回归 | 完成 |
| Batch G2.1 | 完成 | `1bc20328...`、`4ab121ed...` | confidence 兼容 + 8 类 Adapter→topology 回归 | 完成 |
| Batch G2.2 | 完成 | `f7b33c35f4788c77ee16a4804303cc459af52d00` | 四组 Relation Grammar 混淆边界回归 | H 实际测试 |

## 当前验证状态

- 所有计划内测试代码已经写入仓库，但尚未实际执行。
- Batch H 开始执行真实测试；任何失败均按“小修复 → 立即记录”继续处理。
