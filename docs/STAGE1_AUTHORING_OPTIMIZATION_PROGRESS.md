# Stage1 作者化写作优化开发进度

> 开发依据：`CyberPPT Stage1 作者化写作优化开发方案（新版）`
>
> 工作方式：按小批次落地；每完成一个批次立即提交；本文件持续记录完成内容、验证结果、提交和剩余工作，确保任意时点中断后可从仓库恢复。

## 1. 基线与硬边界

- 开发基线：`main@f2316f83aa9f5735f6780760a63e3189a7426835`。
- 保持 Stage1 三个正式权威产物：`script/foundation.json`、`script/deck-plan.json`、`script/dist/final-script.md`。
- Deck Plan 继续保持 v2 lean，不增加 Relation Units、Argument Topology、Onscreen Contract 等预写字段。
- Final Script 保持现有字段，不新增第四套 Stage1 authoritative IR。
- AUTHOR/CRITIQUE/REWRITE 的操作性作者规则继续集中在 `authoring-contract.md`。
- Stage2 继续消费锁定后的最终 `onscreen` 及关系，不承担业务文案重写。
- 确定性代码只做机械底线检查，不替代 AUTHOR 的语义与论证判断。

## 2. 技术判断

结论：`SUPPORT WITH CONDITIONS`，本轮按收敛式实现完成。

实施口径：

1. Relation Unit 仅作为教学层工作方法，不新增持久化字段或独立权威文件。
2. `authoring-contract.md` 已使用 independent arguments / reasoning unit、claim–argument–evidence chain 表达同一职责，不再固化第二套同义 ontology。
3. Authoring grammar 与 machine semantic topology 通过明确映射衔接，不继续增加近义 topology。
4. Golden Examples 作为参考/回归样例，不成为第四套内容规范。
5. Critic/Lint 只新增可机械判定规则；作者判断继续由生成式 AUTHOR/CRITIQUE/REWRITE 承担。
6. 发现架构冲突时优先收敛、复用和修兼容，不为满足计划条目重复造规则。

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
| 8 | P2 | Stage1 authoring fixtures：8 类正确案例与典型错误案例 | 已完成 |
| 9 | P2 | 回归测试：Critic/Lint/topology/Stage1→Stage2 结构保持 | 已完成 |
| 10 | P2 | 全量验证、文档收口、剩余兼容性问题清理 | 已完成 |

## 4. 已完成记录

### Batch 0 — 进度台账初始化

完成：建立本文件、固化基线和硬边界、拆分小批次。

提交：`b057bc56972be2e58ac0991cea159524e9f1c75c`。

### Batch 1–2 — P0 AUTHOR Contract 差距审计

当前基线已经覆盖 source meaning → `core_message` → independent arguments + evidence → Full Copy → Onscreen，以及 proposition headings、relation grammar、Speaker Notes 增量规则和 Critic/Rewrite 最早失败点回退，因此未对单一运行权威做重复改写。

Relation Units 只作黄金示例教学标签，映射到 Contract 的 independent arguments / reasoning units，不形成 schema 或第二套 ontology。

提交：`624f6f8e1d827f9edf5a0cf3c5c2d7d76f32706b`。

### Batch 3 — 黄金示例索引与既有样例拆分

完成：`golden-page-script-example.md` 建立 8 类索引；拆出 `golden-page-parallel.md`、`golden-page-flow.md`；统一补齐页面使命、核心结论、主论证链、Argument Topology、Relation Units、Full Copy、Onscreen、视觉结构、Speaker Notes、作者自检。

提交：`82b03204cee5aea82ac25c82c3f7b97e48e9459c`。

兼容修复：GitHub Actions 后续发现既有 `tests/test_onscreen_group_hierarchy.py` 仍把 `golden-page-script-example.md` 当作可解析的两页示例。纯索引版本造成 `script contains no page headings`。已在保留 8 类导航的同时恢复原入口两页可解析兼容内容，不撤回独立示例结构。

兼容修复提交：`c3d215c373319564aa61cc43100b564dc365b930`。

### Batch 4 — 补齐六类黄金关系页面

新增 Causal、Convergence、Mapping、Comparison、Roadmap、Governance 六类完整黄金页面，与既有 Parallel / Flow 共同形成 8 类核心示例。

提交：`33489f0172da1c24764d7cb1b3c14a884b287cc7`。

### Batch 5 — 正式 Final Script lint 覆盖审计与数字对象底线

正式 lint 链路确认使用 `script_engine.final_quality` → `script_engine.lint_contracts`。现有规则已经覆盖抽象/名词式标题、标题缺业务对象、Full Copy/Onscreen 层级、Evidence 层缺失、Core Message 投影偏离、隐藏中间步骤等项目。

新增 `script_engine/authoring_quality_contracts.py` 与 `ONSCREEN_NUMBER_WITHOUT_OBJECT`，只拦截无语义标签的近似纯数量；规则接入正式 `lint_final_script()` 并新增回归测试。

提交链：`be2a768cc1928e1e793949a8a97301aa36ee1793`、`d5277ce7d69fc9337bda5ba492938346fd5485ea`、`f5a805ac1877f7694c00ae43e79afd138fee5235`、台账 `fc557be3e0466632158f268669b296801bb90093`。

### Batch 6 — Roadmap completeness 与方向关系覆盖审计

新增确定性规则，仅作用于明确的 `roadmap`、`pyramid-roadmap`、`governance-roadmap`：`ROADMAP_STAGE_LAYER_MISSING`、`ROADMAP_TRIGGER_MISSING`、`ROADMAP_NEW_STATE_MISSING`。普通 `progression` 不强制套 Roadmap 规则。

方向关系审计确认既有 relationship visibility、page logic carrier、端点与隐藏中间步骤检查已经覆盖 directed flattening 的机械底线，因此未增加第三套低精度判定器。

提交链：`067930d3b7fde735374e6927b248d9a688034be3`、`dfaee1d134dca8d2406888eb4d1059cd8be5064b`、`87358bc5b06056dcde4a15bdc504a9b727b6edb3`、台账 `2ac18dca4723c2adb0d060e887564bbb88a7d12e`。

### Batch 7 — Authoring grammar 与 machine semantic topology 一致性

补齐 `comparison → parallel_set`、`containment → layered_architecture`、`matrix → parallel_set` 三个 semantic topology → coarse carrier family 缺口；没有增加新的视觉 topology。新增 semantic topology coverage test，并在黄金示例索引加入教学映射表。

提交链：`dc37e3abafa184ab4d7fdc79a3bc0d6ced46a83b`、`2e2380b9e894a363219211f3fcb4f6921abe50ab`、`910e8fa86865131e260cbc91aead7a5fc43619d0`、台账 `b614a70950800cf7fd3a654a441e8f8c781229f1`。

### Batch 8 — Stage1 authoring fixtures

建立 `tests/stage1_authoring/` 回归包，不新增生产 schema。

正确案例：Parallel/MECE、Flow/Feedback、Causal、Convergence、Mapping、Comparison、Roadmap、Governance 共 8 类；每个 fixture 同时记录 Authoring Topology、预期 semantic topology、预期 Stage2 expression form、layout-neutral verified relationships、可解析 `visual_structure` 与模块标题。

错误案例：方向关系被扁平化、假 MECE、孤立 Evidence、父子重复、Mapping 端点缺失、Roadmap 只有阶段名、Governance 主体责任错位、数字缺少业务对象。错误案例明确区分 `lint`、`cross_layer_regression`、`critic`、`critic_existing_contracts`，避免把生成式判断误写成正则规则。

提交链：`b7f38e6a6c2380e86662718b70fb017ab9050b33`、`1097512c25a36217f802fb547f9a64f56ad2eed4`、`ffe376aa3bfc314774fc53fc3d767d17c753be3d`、台账 `092ecafee59231fb9814a225b017207cec3e0ae9`。

### Batch 9 — 跨层回归测试与显式顺序优先级修复

新增 `tests/stage1_authoring/test_cross_layer_regressions.py`，覆盖 8 类正确 fixture 的 semantic topology、relation expression、Final Script `visual_structure` → Stage2 relationship adapter 关系保持，两类稳定 lint 负例，以及 Critic-only / cross-layer fixture 的检测职责边界。

发现并修复：多阶段 Roadmap 的两条显式 `sequence_before` 会与通用 `dependency_chain` 形成同分候选，并因名称排序把 `dependency_chain` 错选为 primary。现调整为存在显式 sequence 时不再生成冗余通用 dependency candidate。

提交链：`d2dc5f499aeed44a736c62144f9d2b185321009d`、`54bf705553e6d3e638d08002970b163e35a80086`、台账 `d36899b219d799bd1f2069781a149184ef2b7f71`。

GitHub Actions run `33395908843`（run #545）整体 `success`：

- Python 3.12：`1851 passed, 8 skipped, 2 warnings, 49 subtests passed`；
- Python 3.10：pytest、wheel build、wheel import smoke 全部成功；
- Windows wheel smoke：成功；
- macOS wheel smoke：成功；
- OfficeCLI render smoke：成功。

2 条 warning 来自既有 `page_artifact_spec.py` legacy content-integrity list-order projection，与本轮 Stage1 作者化开发无直接关系。

### Batch 10 — 全量范围审计与收口

以 `f2316f83aa9f5735f6780760a63e3189a7426835` 为 base、`d36899b219d799bd1f2069781a149184ef2b7f71` 为审计 head 执行 compare：`ahead_by=24`，共 19 个 changed files。

范围审计结论：

1. 未修改 `contracts/foundation.schema.json`、`contracts/deck-plan.schema.json`、`contracts/final-script.schema.json`，没有扩大 Stage1 schema；
2. 未新增 `relation-plan.json`、`screen-copy-contract.json`、Argument Topology IR 等第四套 Stage1 authoritative artifact；
3. 生产代码只涉及 `script_engine/authoring_quality_contracts.py`、`script_engine/lint_contracts.py`、`cyberppt/topology_resolver.py` 三处，其余改动均为黄金示例、开发台账和测试；
4. 新增 deterministic lint 只覆盖无对象纯数量和显式 Roadmap completeness；假 MECE、Governance 主体责任错位等语义失败继续留给 AUTHOR/CRITIQUE；
5. topology 改动只补齐既有 semantic topology 的 coarse carrier 映射并修正显式 sequence 优先级，没有新增视觉 topology vocabulary；
6. Golden Example 历史可解析入口已恢复兼容，同时保留 8 类独立示例；
7. 正确/错误 fixture、production lint、topology resolver 与 Stage1→Stage2 relationship adapter 已形成可执行回归闭环。

最终代码与测试验证基线：`main@54bf705553e6d3e638d08002970b163e35a80086`，GitHub Actions run #545 全绿；其后的提交仅更新本进度文档。本次提交关闭 Batch 10，提交后再以 `main` workflow 状态作为仓库最终恢复状态验证。

## 5. 剩余工作

本开发计划 0–10 批已全部完成，无阻塞性剩余开发任务。

后续若继续演进，建议作为新计划单独立项，不在本轮继续扩张规则：

- 用真实项目脚本持续补充 fixture 覆盖面；
- 根据实际误报/漏报数据调整 deterministic lint，而非预先增加规则；
- 将现有 2 条 legacy content-integrity warning 作为 Stage2 兼容治理议题单独处理。
