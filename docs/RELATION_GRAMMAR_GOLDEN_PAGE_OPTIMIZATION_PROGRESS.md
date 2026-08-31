# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 记录规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件记录实现 commit、结果、遗留问题和下一恢复点。

## 当前状态

- 当前阶段：Batch F — 统一视觉结构合同
- 总体状态：进行中
- 已完成：Step 0、Batch A–E、Batch F1、Batch F2.1–F2.2、Batch F3.1
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把生成式 AUTHOR / CRITIQUE 判断硬编码成低精度 lint
- 下一恢复点：Batch F3.2，为 Governance 原子关系边增加跨层回归

## 剩余任务

- [ ] Batch F3.2：Governance 原子边回归测试
- [ ] Batch F4–F9：其余黄金页视觉结构五项合同归一
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 关键文件

- 黄金页：`.agents/skills/cyberppt-script-workflow/references/golden-page-*.md`
- 五项合同：`.agents/skills/cyberppt-script-workflow/references/golden-page-visual-structure-contract.md`
- 跨层回归：`tests/stage1_authoring/test_cross_layer_regressions.py`
- Stage2 adapter：`cyberppt/stage02_relationship_adapter.py`

## 进度记录

| 步骤 | 状态 | 实现 commit | 完成结果 | 遗留 / 下一恢复点 |
|---|---|---|---|---|
| Step 0 | 完成 | `98d43c27...`、`7e585307...` | 建立分支、台账并完成跨层基线映射 | 完成 |
| Batch A–E | 完成 | 见历史提交 | Relation Contract、重点页面重构、微语法与 Notes 增量化完成 | 完成 |
| Batch F1 | 完成 | `6f07e780691b6b880a6777e30e69157fe9fcf2d4` | 新增五项 Visual Structure Contract | 完成 |
| Batch F2.1 | 完成 | `2b9930d117507c0df553c9c8b46773b4d484f95a` | Adapter 新增 non-directional `A vs B` Comparison 解析 | 完成 |
| Batch F2.2 | 完成 | `a2b75c91bc7feaf57eec8721fc5aeb48009e9295` | 新增 Comparison 跨层回归 | 完成 |
| Batch F3.1 | 完成 | `f363d256a849ef07eba6559f42382976e30fca65` | Governance `视觉结构` 归一为五项合同；增加 7 条 Actor→Responsibility→Control→Outcome 原子边 | 下一步：F3.2 回归 |

## F3.1 验收

- 三个 Actor 各自绑定责任对象，责任对象 3→1 汇入共同控制机制，共同控制机制 1→1 指向受保护结果。
- 原子边使用现有显式箭头解析能力，不新增 relation ontology。
- 控制层与 Actor 层通过五项合同明确分层，禁止被画成四个同级主体。
