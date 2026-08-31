# Stage1 作者化写作优化开发进度

> 开发依据：`CyberPPT Stage1 作者化写作优化开发方案（新版）`
>
> 工作方式：按小批次落地；每完成一个批次立即提交；本文件随每个批次同步更新，记录完成内容、验证结果、提交与剩余工作，确保中断后可直接续作。

## 1. 基线与硬边界

- 开发基线：`main`，启动时 HEAD 为 `f2316f83aa9f5735f6780760a63e3189a7426835`。
- 保持 Stage1 三个正式权威产物：`script/foundation.json`、`script/deck-plan.json`、`script/dist/final-script.md`。
- Deck Plan 继续保持 v2 lean，不增加 Relation Units、Argument Topology、Onscreen Contract 等预写字段。
- Final Script 保持现有字段，不新增第四套 Stage1 authoritative IR。
- AUTHOR/CRITIQUE/REWRITE 的操作性作者规则继续集中在 `authoring-contract.md`。
- Stage2 继续消费锁定后的最终 `onscreen`，不承担业务文案重写。
- 确定性代码只做机械底线检查，不替代 AUTHOR 的语义与论证判断。

## 2. 技术判断

结论：`SUPPORT WITH CONDITIONS`。

实施条件：

1. Relation Unit 作为 AUTHOR 的工作方法和教学语义节点，不新增持久化项目字段或独立权威文件。
2. Authoring grammar 与 machine semantic topology 通过明确映射衔接，不继续增加近义 topology。
3. Golden Examples 作为参考/回归样例，不成为第四套内容规范；优先保留总索引，独立示例按需加载。
4. Critic/Lint 新增规则必须可机械判定；需要作者判断的事项保留为生成式 Critic 规则。
5. 每批修改先做最小范围验证，再提交；发现架构冲突时优先收敛而非扩张。

## 3. 批次计划

| 批次 | 优先级 | 范围 | 状态 |
|---|---|---|---|
| 0 | P0 | 建立持续进度台账与开发边界 | 已完成 |
| 1 | P0 | AUTHOR Contract：Question → Core Message → Argument Topology → Relation Units → Evidence → Full Copy → Onscreen | 待开始 |
| 2 | P0 | AUTHOR Contract：Onscreen Projection、Speaker Notes、Critic/Rewrite 最早失败点规则 | 待开始 |
| 3 | P1 | Golden Examples：建立索引与 8 类关系页面样例骨架 | 待开始 |
| 4 | P1 | Golden Examples：补齐 8 类完整样例与作者自检 | 待开始 |
| 5 | P1 | Critic / Script Quality：抽象标题、父子重复、孤立 Evidence 等机械检查 | 待开始 |
| 6 | P1 | Critic / Script Quality：方向关系扁平化、Roadmap completeness 等检查 | 待开始 |
| 7 | P1 | Topology：Authoring grammar ↔ machine semantic topology 映射与一致性 | 待开始 |
| 8 | P2 | Stage1 authoring fixtures：8 类正确案例与典型错误案例 | 待开始 |
| 9 | P2 | 回归测试：Critic/Lint/topology/Stage1→Stage2 结构保持 | 待开始 |
| 10 | P2 | 全量验证、文档收口、剩余兼容性问题清理 | 待开始 |

> 批次允许根据仓库实际结构进一步拆小；任何拆分都必须先更新本表并在提交记录中说明。

## 4. 已完成记录

### Batch 0 — 进度台账初始化

完成：

- 建立本进度文件。
- 固化开发基线和不可破坏边界。
- 将新版方案拆为可独立提交、可回滚的小批次。

验证：

- 仓库权限已确认具备 push/admin。
- `main` 启动基线已记录。
- 尚未修改运行时代码和现有作者规则。

提交：当前提交（见 Git 历史）。

## 5. 当前剩余工作

下一批：Batch 1，先修改 `.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`，只处理作者推理主链、Argument Topology、Relation Unit、Evidence Binding，不同时改 Golden Examples 或确定性代码。

后续剩余：Batch 2–10，详见上表。
