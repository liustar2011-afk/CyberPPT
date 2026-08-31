# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A、Batch B1–B3、Batch C1–C2、Batch D1–D3、Batch E1–E8、Batch F1
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F2，增强 Stage2 adapter 对 `A vs B：对照比较` 的无方向 Comparison 解析

## 剩余任务

- [ ] Batch F2：Comparison 无方向关系解析
- [ ] Batch F3：Governance 原子关系边与解析保真
- [ ] Batch F4–F9：其余黄金页视觉结构五项合同归一
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 已确认链路

`Golden Page → Final Script 视觉结构 → stage02_relationship_adapter → topology_resolver / relation_semantics → Stage2 expression`

关键文件：
- 黄金页：`.agents/skills/cyberppt-script-workflow/references/golden-page-*.md`
- 视觉结构五项合同：`.agents/skills/cyberppt-script-workflow/references/golden-page-visual-structure-contract.md`
- AUTHOR 权威：`.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`
- 正向 fixture：`tests/stage1_authoring/fixtures.py`
- 跨层回归：`tests/stage1_authoring/test_cross_layer_regressions.py`
- Semantic topology：`cyberppt/topology_resolver.py`
- Relation expression：`cyberppt/relation_semantics.py`
- Stage2 adapter：`cyberppt/stage02_relationship_adapter.py`

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 遗留 / 下一恢复点 |
|---|---|---|---|---|
| Step 0.1 初始化台账 | 完成 | `98d43c2750f0f8b96682d39b1fad5d59e350d534` | 建立开发分支和单一进度文件 | 下一步：仓库映射 |
| Step 0.2 跨层基线映射 | 完成 | 只读盘点；进度提交 `7e585307f34f444d5d05eb388a195ca6abe3d5b9` | 定位 8 类黄金页、fixture、topology、Stage2 adapter、测试入口 | 发现文档与 fixture 存在语义漂移 |
| Batch A 统一 Relation Contract | 完成 | 索引 `1c949e0c...`；Parallel `4b09b5de...`；Flow `97bc03b4...`；Causal `36895005...`；Convergence `6b95c21f...`；Mapping `75a4d44e...`；Comparison `c234a92e...`；Roadmap `1b192d4c...`；Governance `fbd4493c...` | 8 页统一六项 Relation Contract；索引增加横向 Grammar 边界 | 下一步：逐页修正文档与 Contract 不一致处 |
| Batch B1 Governance | 完成 | `1b26d08fdde93e456b7633f1327c6a1d45a53445` | Actor 分别绑定责任对象，共同控制层与受保护结果独立 | Batch G1 对齐 fixture |
| Batch B2 Comparison | 完成 | `df4b65c47753a758a33878557c939cf6c2baccd7` | 固定双列与共同评价维度；移除方向箭头 | Batch F/G 修正 Stage2 恢复 |
| Batch B3 Causal | 完成 | `b14788dd4d887161419b30c9f20b0f2a17dd8721` | 收紧为逐边可证明因果链 | Batch G1 对齐 fixture |
| Batch C1 Parallel | 完成 | `bd323d56afa606ae68d6c12e8f63586dd6e87fa8` | 同层维度统一为研判范围 / 周期规则 / 运行机制 | Batch G1 对齐 fixture |
| Batch C2 Convergence | 完成 | `3ce2b3e5c53677c17ad1bc1dcdf2d1e04dd4faa6` | 输入角色统一为供给边界 / 需求压力 / 互济缓释 / 波动扰动 | Batch G1 对齐 fixture |
| Batch D1 Flow | 完成 | `b85a5b702f77dc43c88811589fa4d47cd7093ee9` | 增加真实交接物与反馈回写物 | Batch G1 对齐 fixture |
| Batch D2 Roadmap | 完成 | `a404c1a253b96ea5e4bc053c9b4b50f635dd53f8` | 固定 S0–S3 状态链、进入条件和目标状态 | Batch G1 对齐 fixture |
| Batch D3 Mapping | 完成 | `519f0f22bce685e21c6f2583e9a4641be58cff1a` | 固定 Problem → Response，显式 1:1 Cardinality | Batch F/G 对齐 |
| Batch E1–E8 | 完成 | `5531a74a...`、`72018cef...`、`09a18ca0...`、`5bef322a...`、`f8c7af32...`、`e0b0ff58...`、`47d3f122...`、`65cc4da9...` | 8 页形成对应 Grammar 的上屏微语法；Speaker Notes 改为增量判别信息 | 下一步：视觉结构合同与 Runtime 恢复 |
| Batch F1 Visual Structure Contract | 完成 | `6f07e780691b6b880a6777e30e69157fe9fcf2d4` | 新增五项视觉结构合同：视觉对象、关系语义、方向/Cardinality、分组/层级、禁止误读；规定原子边和 Comparison `vs` 无方向表达 | 下一步：F2 adapter 无方向 Comparison 解析 |

## Batch F1 详细验收

- 新参考文件明确属于黄金页教学表达，不新增 Runtime 字段或 authoritative IR。
- 五项合同与 AUTHOR Contract 3.9 的 visual-structure / atomic relationship-edge 方法一致。
- 明确有方向关系使用 `Source → Target：关系标签`；无方向 Comparison 使用 `A vs B：对照比较`，禁止为了适配解析器虚构箭头。
- 规定 Stage2 应增强关系恢复能力，而不是反向要求 Stage1 制造错误方向。
