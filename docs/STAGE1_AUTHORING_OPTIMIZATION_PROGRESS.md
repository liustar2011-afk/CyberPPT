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

1. Relation Unit 仅作为教学层工作方法，不新增持久化字段或独立权威文件。
2. `authoring-contract.md` 已使用 independent arguments / reasoning unit、claim–argument–evidence chain 表达同一职责，不再固化第二套同义 ontology。
3. Authoring grammar 与 machine semantic topology 通过明确映射衔接，不继续增加近义 topology。
4. Golden Examples 作为参考/回归样例，不成为第四套内容规范。
5. Critic/Lint 只新增可机械判定规则；作者判断继续由生成式 AUTHOR/CRITIQUE/REWRITE 承担。
6. 每批先做最小范围核对再提交；发现架构冲突时优先收敛而非扩张。

## 3. 批次计划

| 批次 | 优先级 | 范围 | 状态 |
|---|---|---|---|
| 0 | P0 | 建立持续进度台账与开发边界 | 已完成 |
| 1 | P0 | AUTHOR Contract：主推理链、Relation Unit 语义职责、Evidence Binding 审计 | 已完成（基线已满足） |
| 2 | P0 | AUTHOR Contract：Onscreen、Speaker Notes、Critic/Rewrite 审计 | 已完成（基线已满足） |
| 3 | P1 | Golden Examples：8 类索引并拆出 Parallel / Flow | 已完成 |
| 4 | P1 | Golden Examples：补齐 6 类完整样例 | 已完成 |
| 5 | P1 | Critic / Script Quality：覆盖审计 + 数字对象机械底线 | 已完成 |
| 6 | P1 | Critic / Script Quality：方向关系审计 + Roadmap completeness | 已完成 |
| 7 | P1 | Topology：Authoring grammar ↔ machine semantic topology 映射与一致性 | 已完成 |
| 8 | P2 | Stage1 authoring fixtures：8 类正确案例与典型错误案例 | 进行中 |
| 9 | P2 | 回归测试：Critic/Lint/topology/Stage1→Stage2 结构保持 | 待开始 |
| 10 | P2 | 全量验证、文档收口、剩余兼容性问题清理 | 待开始 |

> 批次允许根据仓库实际结构进一步拆小；任何拆分都必须及时更新本表。

## 4. 已完成记录

### Batch 0 — 进度台账初始化

完成：建立本文件、固化基线和硬边界、拆分小批次。

提交：`b057bc56972be2e58ac0991cea159524e9f1c75c`。

### Batch 1–2 — P0 AUTHOR Contract 差距审计

结论：当前基线已经覆盖 source meaning → `core_message` → independent arguments + evidence → Full Copy → Onscreen，以及 proposition headings、relation grammar、Speaker Notes 增量规则和 Critic/Rewrite 最早失败点回退，因此不对 71KB 单一运行权威做重复改写。

Relation Units 只作黄金示例教学标签，映射到 Contract 的 independent arguments / reasoning units，不形成 schema 或第二套 ontology。

提交：`624f6f8e1d827f9edf5a0cf3c5c2d7d76f32706b`。

### Batch 3 — 黄金示例索引与既有样例拆分

完成：`golden-page-script-example.md` 改为 8 类索引；拆出 `golden-page-parallel.md`、`golden-page-flow.md`；统一补齐页面使命、核心结论、主论证链、Argument Topology、Relation Units、Full Copy、Onscreen、视觉结构、Speaker Notes、作者自检。

提交：`82b03204cee5aea82ac25c82c3f7b97e48e9459c`。

### Batch 4 — 补齐六类黄金关系页面

新增 Causal、Convergence、Mapping、Comparison、Roadmap、Governance 六类完整黄金页面，与既有 Parallel / Flow 共同形成 8 类核心示例。

提交：`33489f0172da1c24764d7cb1b3c14a884b287cc7`。

### Batch 5 — 正式 Final Script lint 覆盖审计与数字对象底线

正式 lint 链路确认使用 `script_engine.final_quality` → `script_engine.lint_contracts`。现有规则已经覆盖抽象/名词式标题、标题缺业务对象、Full Copy/Onscreen 层级、Evidence 层缺失、Core Message 投影偏离、隐藏中间步骤等项目。

新增：

- `script_engine/authoring_quality_contracts.py`；
- `ONSCREEN_NUMBER_WITHOUT_OBJECT`，只拦截 `80%`、`30家`、`3项` 等无语义标签的近似纯数量；
- 合法日期、有标签数字及带完整业务对象的数字表达保持通过；
- 规则接入正式 `lint_final_script()`；
- 新增数字对象回归测试。

提交链：

- `be2a768cc1928e1e793949a8a97301aa36ee1793`
- `d5277ce7d69fc9337bda5ba492938346fd5485ea`
- `f5a805ac1877f7694c00ae43e79afd138fee5235`
- 台账：`fc557be3e0466632158f268669b296801bb90093`

验证限制：GitHub 未为这些 push commits 返回可用 workflow/status；测试代码已入仓，P2 统一纳入可执行回归。

### Batch 6 — Roadmap completeness 与方向关系覆盖审计

新增确定性规则，仅作用于明确的 `roadmap`、`pyramid-roadmap`、`governance-roadmap`：

- `ROADMAP_STAGE_LAYER_MISSING`
- `ROADMAP_TRIGGER_MISSING`
- `ROADMAP_NEW_STATE_MISSING`

普通 `progression` 不强制套 Roadmap 规则。方向关系审计确认既有 relationship visibility、page logic carrier、端点与隐藏中间步骤检查已经覆盖 directed flattening 的机械底线，因此未增加第三套低精度判定器。

提交链：

- `067930d3b7fde735374e6927b248d9a688034be3`
- `dfaee1d134dca8d2406888eb4d1059cd8be5064b`
- `87358bc5b06056dcde4a15bdc504a9b727b6edb3`
- 台账：`2ac18dca4723c2adb0d060e887564bbb88a7d12e`

### Batch 7 — Authoring grammar 与 machine semantic topology 一致性

审计发现：`cyberppt.topology_resolver` 可以产出 `comparison`、`containment`、`matrix`，但粗粒度 `CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY` 原先缺少这三个键；同时 `cyberppt.onscreen_expression` 已有三类详细表达，因此属于 semantic topology → carrier family 映射缺口，不需要增加新视觉类型。

完成：

- `comparison → parallel_set`
- `containment → layered_architecture`
- `matrix → parallel_set`
- 明确 candidate map 只是粗粒度 render-carrier family，详细 Stage2 expression 仍由 `onscreen_expression` 决定；
- 新增 `tests/test_topology_semantic_coverage.py`，对 peer、feedback、convergence、sequence、dependency、causal、mapping、layered、comparison、containment、matrix 的代表性 resolver 输出逐一检查候选映射非空；
- 黄金示例索引新增教学映射表：Authoring grammar → semantic relationship → semantic topology → coarse carrier family；
- Governance chain 与 bounded decision package 明确按真实关系解析，不强制绑定单一机器 topology；
- 未在 `script_engine` 引入 Stage2 resolver 依赖，继续保持 Stage1/Stage2 解耦。

提交链：

- `dc37e3abafa184ab4d7fdc79a3bc0d6ced46a83b`：补齐 resolver candidate mapping；
- `2e2380b9e894a363219211f3fcb4f6921abe50ab`：新增 semantic topology coverage tests；
- `910e8fa86865131e260cbc91aead7a5fc43619d0`：补教学映射表；
- 当前提交：更新进度台账。

## 5. 当前剩余工作

下一恢复点：Batch 8。围绕 8 类黄金页面建立 `tests/stage1_authoring/` fixtures / regression cases，优先复用现有 Final Script example 与正式 schema，覆盖：正确案例、方向关系被错误扁平化、假 MECE、孤立 Evidence、模块标题与明细重复、Mapping 两端缺失、Roadmap 只有阶段名无新状态、Governance 责任主体错位。

随后：Batch 9 汇总 Critic/Lint/topology/Stage1→Stage2 结构保持回归；Batch 10 做全量验证、兼容性清理和最终收口。
