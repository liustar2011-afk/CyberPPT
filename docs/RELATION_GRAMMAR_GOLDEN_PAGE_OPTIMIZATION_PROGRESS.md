# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 维护规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件追加一条进度记录，写明完成内容、改动文件、实现 commit、测试结果、已发现问题、剩余任务和下一恢复点。

## 总体状态

- 当前阶段：Batch A — 统一模板与 Relation Contract
- 总体状态：进行中
- 已完成：开发分支建立；独立进度台账初始化；8 类黄金页与跨层关系链路完成基线映射
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把 AUTHOR/CRITIQUE 的生成式判断硬编码成低精度 lint
- 下一恢复点：更新黄金页索引与 8 页模板，增加 Relation Contract 和 Grammar 横向边界表

## 已确认的现状映射

- 黄金页索引：`.agents/skills/cyberppt-script-workflow/references/golden-page-script-example.md`
- 8 个黄金页：同目录 `golden-page-parallel.md`、`golden-page-flow.md`、`golden-page-causal.md`、`golden-page-convergence.md`、`golden-page-mapping.md`、`golden-page-comparison.md`、`golden-page-roadmap.md`、`golden-page-governance.md`
- AUTHOR 操作权威：`.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`
- 正向 fixture：`tests/stage1_authoring/fixtures.py`
- 跨层回归：`tests/stage1_authoring/test_cross_layer_regressions.py`
- semantic topology：`cyberppt/topology_resolver.py`
- relation expression：`cyberppt/relation_semantics.py`
- Stage2 relationship adapter：`cyberppt/stage02_relationship_adapter.py`

## 任务清单

- [x] Step 0：仓库基线盘点与映射
- [ ] Batch A：统一黄金页面模板与 Relation Contract
- [ ] Batch B1：Governance 重构
- [ ] Batch B2：Comparison 重构
- [ ] Batch B3：Causal 收紧真实因果
- [ ] Batch C1：Parallel 同层尺度统一
- [ ] Batch C2：Convergence 输入角色优化
- [ ] Batch D1：Flow 增加真实业务交接物
- [ ] Batch D2：Roadmap 增加状态化进入条件与起终点
- [ ] Batch D3：Mapping 修正方向与 Cardinality
- [ ] Batch E：Onscreen 微语法与 Speaker Notes 去重
- [ ] Batch F：统一视觉结构合同
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 进度记录

### Step 0.1 — 初始化本轮开发台账

- 状态：完成
- 完成内容：
  - 建立独立开发分支 `agent/relation-grammar-golden-page-20260831`。
  - 新建本进度文件，固定“小步骤、立即提交、立即记录”的恢复机制。
  - 将开发任务拆分到可单独验证的最小步骤。
- 改动文件：
  - `docs/RELATION_GRAMMAR_GOLDEN_PAGE_OPTIMIZATION_PROGRESS.md`
- 实现 commit：`98d43c2750f0f8b96682d39b1fad5d59e350d534`
- 测试结果：无代码改动，不适用。
- 已发现问题：初始化时尚未完成仓库文件映射。
- 剩余任务：见“任务清单”。
- 下一恢复点：读取仓库目录与关键入口，形成黄金页 → fixture → topology → Stage2 expression → tests 的现状映射。

### Step 0.2 — 完成 Relation Grammar 跨层基线映射

- 状态：完成
- 完成内容：
  - 定位全部 8 类黄金页及索引文件。
  - 定位现有正向 fixture 和跨层回归入口。
  - 确认 `resolve_semantic_topology()` 位于 `cyberppt/topology_resolver.py`。
  - 确认 Stage2 从 `visual_structure` 恢复关系的入口为 `derive_business_relationships()`。
  - 确认现有 fixture 已覆盖 8 类 Grammar，但文档与 fixture 仍存在语义漂移：Comparison fixture 仍使用方向箭头；Governance fixture 使用通用 dependency chain，未对应黄金页的 Actor/Responsibility/Control/Outcome；Convergence fixture 与黄金页业务输入不同。
- 改动文件：
  - `docs/RELATION_GRAMMAR_GOLDEN_PAGE_OPTIMIZATION_PROGRESS.md`
- 实现 commit：只读盘点，无代码实现 commit；本条由进度记录提交承载。
- 测试结果：完成静态链路核对；尚未执行代码测试。
- 已发现问题：
  - `stage02_relationship_adapter.py` 当前主要依赖显式 `A → B：关系标签` 或少量结构关键词；新的五项视觉合同需要在 Batch G/F 期间验证不会丢关系。
  - 文档示例与 executable fixture 尚未建立直接一致性约束。
- 剩余任务：Batch A–H。
- 下一恢复点：Batch A，先更新索引和统一 Relation Contract，再逐页补齐模板。
