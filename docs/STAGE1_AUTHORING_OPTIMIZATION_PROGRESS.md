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

1. Relation Unit 作为教学层的工作方法，不新增持久化项目字段或独立权威文件。
2. 当前 `authoring-contract.md` 已使用 independent arguments / reasoning unit、claim–argument–evidence chain 表达同一语义职责；为避免同义 ontology 漂移，不强行把 Relation Unit 再固化成第二套正式运行时术语。
3. Authoring grammar 与 machine semantic topology 通过明确映射衔接，不继续增加近义 topology。
4. Golden Examples 作为参考/回归样例，不成为第四套内容规范；保留一个总索引，其余示例独立存放并按需读取。
5. Critic/Lint 新增规则必须可机械判定；需要作者判断的事项保留为生成式 Critic 规则。
6. 每批修改先做最小范围验证，再提交；发现架构冲突时优先收敛而非扩张。

## 3. 批次计划

| 批次 | 优先级 | 范围 | 状态 |
|---|---|---|---|
| 0 | P0 | 建立持续进度台账与开发边界 | 已完成 |
| 1 | P0 | AUTHOR Contract 现状审计：主推理链、Relation Unit 语义职责、Evidence Binding | 已完成（基线已满足，不重复改写） |
| 2 | P0 | AUTHOR Contract 现状审计：Onscreen、Speaker Notes、Critic/Rewrite 最早失败点 | 已完成（基线已满足，不重复改写） |
| 3 | P1 | Golden Examples：建立 8 类关系页面索引并拆出既有 Parallel / Flow | 已完成 |
| 4 | P1 | Golden Examples：补齐 6 类缺失完整样例与作者自检 | 待开始 |
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

提交：`b057bc56972be2e58ac0991cea159524e9f1c75c`。

### Batch 1–2 — P0 AUTHOR Contract 差距审计

结论：当前基线已经覆盖新版方案要求的主要 P0 作者方法，因此不对 71KB 的单一运行权威进行重复性重写。

已确认存在：

- 每页先锁定 source meaning，再形成 `core_message`；
- `core_message` 后构建独立 arguments，并逐项绑定证明、解释或限定它的 evidence；
- Full Copy 在论证结构稳定后生成，Onscreen 再从 Full Copy 做结构投影；
- 普通模块标题必须承担完整判断，禁止 noun-only heading 承担主判断；
- mapping、roadmap、governance、causal/convergence 等 relation grammar 已有与 semantic topology 的衔接原则；
- Speaker Notes 已限定为增量讲稿，关键条件不得从上屏迁出；
- Critic/Rewrite 已要求从最早失败的结构步骤重写，禁止只做末端逐句修补。

与新版方案的处理差异：

- 不在运行时 Contract 再增加一套 `Relation Unit` 正式术语。现有 independent arguments / reasoning unit 已承担该职责；Golden Examples 可使用 Relation Units 作为教学标签，但必须明确映射回 argument 单元，不形成 schema 或新 ontology。
- 不复制现有 Contract 已具备的规则，避免单一权威内部重复和规则漂移。

验证：

- 已完整核对 `authoring-contract.md` 的执行顺序、semantic foundation、onscreen projection、relation grammar、speaker notes、Critic/Rewrite 规则。
- 已核对 `SKILL.md`：仍只负责路由和 Stage 边界，AUTHOR 规则继续由 Contract 单一持有。
- 本批不改变 schema、运行时代码或 Stage1→Stage2 handoff。

提交：`624f6f8e1d827f9edf5a0cf3c5c2d7d76f32706b`。

### Batch 3 — 黄金示例索引与既有样例拆分

完成：

- 将 `golden-page-script-example.md` 重构为 8 类 Relation Grammar 黄金页面总索引。
- 明确 Relation Units 仅为教学标签，映射到 Contract 的 independent arguments / reasoning units，不进入 Final Script schema。
- 将原有并列分类示例拆为 `golden-page-parallel.md`。
- 将原有流程闭环示例拆为 `golden-page-flow.md`。
- 两个样例统一补齐：页面使命、核心结论、主论证链、Argument Topology、Relation Units、Full Copy、Onscreen、视觉结构、Speaker Notes、作者自检。

验证：

- 原有 Parallel / Flow 两类核心语义与上屏示例得到保留。
- 索引仍保留原兼容入口文件名，不新增运行时 authoritative artifact。
- 示例明确区分并列与有向流程，Flow 示例保留 feedback 回写，避免方向关系扁平化。

提交：本批次提交（见 Git 历史，下一批回填 SHA）。

## 5. 当前剩余工作

下一批：Batch 4，新增 `golden-page-causal.md`、`golden-page-convergence.md`、`golden-page-mapping.md`、`golden-page-comparison.md`、`golden-page-roadmap.md`、`golden-page-governance.md` 六类完整黄金页面。

随后：对 `cyberppt/script_quality/` 做实际能力审计，只实现现有规则未覆盖的机械检查；再建立 fixtures 与回归测试。
