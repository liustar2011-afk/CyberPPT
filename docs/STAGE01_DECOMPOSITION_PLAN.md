# Stage 01 大模块拆分计划

本计划用于控制 Stage 01 语义核心继续膨胀，并规定后续行为保持型拆分顺序。

## 原则

1. 先拆纯函数、常量、渲染器和只读 projection，再拆语义校验核心。
2. 一次提交只移动一个职责域，并用原有 golden/contract tests 证明行为不变。
3. 不在“改变业务语义规则”的同一提交中进行大规模文件搬迁。
4. 不新增平行 authority；模块拆分只改变代码所有权，不改变 Stage 01 Authority Map。
5. 大模块可以自由缩小；超过 `config/architecture_module_budgets.json` 的增长必须在同一 PR 中说明为何无法先拆分。

## 当前优先级

### A. `script_engine/contracts.py`

已开始拆分：主观修辞/口播启发式已迁出 Hard Gate，独立为 `script_engine/advisory_lint.py` + `contracts/advisory-phrasing.json`。

后续 seams：

- JSON schema loading/validation → `script_engine/schema_validation.py`；
- source-ref coverage → `script_engine/source_ref_validation.py`；
- audience-visible hard phrasing → `script_engine/hard_phrasing.py`；
- onscreen deterministic structure checks → `script_engine/onscreen_contracts/`。

### B. `cyberppt/stage01_compiler.py`

按输出消费者拆：

- Source Truth projection；
- Outline compatibility projection；
- page-group/source-order projection；
- projection-only constants/mappings。

任何新模块都必须声明 `authority = false`；它们只能消费已验证 SemanticIR。

### C. `cyberppt/source_argument_model.py`

按模型生命周期拆：

- model schema/default construction；
- corruption/evidence-ref validation；
- review Markdown rendering；
- node indexes and source coverage helpers。

优先拆渲染和机械验证，不先动跨章节语义推理。

### D. `cyberppt/visual_structure_contract.py`

按职责拆：

- topology vocabulary；
- composition/visual grammar constraints；
- artifact contract validation；
- deterministic projection/rendering helpers。

Stage 02 仍只消费 Final Script + 自身派生视觉关系，不回读 Stage 01 authority。

## 本轮为何不直接重写 60–90KB 核心

本轮同时修复 Style 可复现性、Stage 02 状态机、兼容 seam、lint severity 和 packaging。若在同一批次继续搬迁 60–90KB 的语义核心，回归原因会混杂，无法判断失败来自行为变化还是文件移动。

因此本轮采取：

1. 先完成一个低风险职责抽取（advisory lint）；
2. 加入模块增长预算；
3. 用 CI 固定现有行为；
4. 后续按 A→B→C→D 单独 PR/阶段继续物理拆分。

这属于 `SUPPORT WITH CONDITIONS` 下的风险控制，不代表放弃拆分目标。
