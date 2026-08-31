# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch G2 — Grammar 边界回归测试
- 总体状态：进行中
- 已完成：Step 0、Batch A–F、Batch G1、Batch G2.1a
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch G2.1b，让 8 个 `visual_structure` 经 Stage2 adapter 后直接进入 `topology_resolver`，验证与 fixture 预期 topology 一致

## 剩余任务

- [ ] Batch G2.1b：Adapter → topology 8 类跨层回归
- [ ] Batch G2.2：Grammar 边界与禁止误读回归
- [ ] Batch H：全量验证与收口

## G2.1a 修复

- `stage02_relationship_adapter` 使用 `high / medium / low` 字符串表达置信度。
- `topology_resolver` 之前对 `confidence` 直接执行 `float(...)`，导致 adapter 派生关系无法稳定进入 semantic topology 层。
- 新增 `_confidence_value()`：同时支持 0–1 数值、数字字符串和 `high / medium / low`。
- 归一值：high=1.0、medium=0.7、low=0.4；未知值安全降为 0.0。
- 只修输入兼容，不改变 topology 排名规则和语义分类规则。

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 下一恢复点 |
|---|---|---|---|---|
| Step 0 / Batch A–F | 完成 | 见历史提交 | 黄金页、Visual Structure Contract 与 Runtime 基础适配完成 | 完成 |
| Batch G1 | 完成 | `34d74e57...`、`7ac8fda1...` | fixtures 与黄金页对齐，并建立文件级一致性约束 | 完成 |
| Batch G2.1a | 完成 | `1bc20328db175de17bae040119142a9946777d26` | topology resolver 兼容 adapter 风格 confidence | G2.1b 8 类跨层 topology 回归 |

## 当前验证状态

- Adapter → topology 的类型兼容已修复，尚需用 8 类黄金 fixture 验证语义结果。
- 尚未触发远端 CI；Batch H 统一执行全量测试。
