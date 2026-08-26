# Stage 2 内容结构保真改造——P3 验收报告

本报告收尾 `CyberPPT_Stage2_Content_Integrity_Development_Plan.md` 的 P0→P3 四阶段改造。P0/P1/P2 分别交付于以下提交：

| 阶段 | 内容 | commit |
|---|---|---|
| P0 | Content Integrity Contract（根模块/父子树/顺序，哈希校验） | `a4db7e0f` |
| P1 | 禁止跨根合并、禁止 detail 升格为焦点（编译期 + 审计期双闸门） | `51bf39cf` |
| P2 | FinalPromptIR 按内容根模块分组，取消四组硬上限 | `a63601b0` |
| P3 | 本报告：真实项目回归、CI 指标、文档 | 本次 |

## 一、原方案第24节九项指标对照

| 指标 | 状态 | 依据 |
|---|---|---|
| Exact text fidelity = 100% | 已保证 | `stage02_handoff.py` 既有 `LOCKED_TEXT_ORDER_DRIFTED` 审计（P0 之前已存在，未改动） |
| Root module fidelity = 100% | 已保证 | `content_integrity.structure_hash` 自洽校验，[stage02_handoff.py:539](cyberppt/stage02_handoff.py:539) `CONTENT_STRUCTURE_HASH_INVALID` + [:513](cyberppt/stage02_handoff.py:513) `CONTENT_ROOT_INVALID` |
| Parent-child fidelity = 100% | 已保证 | [stage02_handoff.py:504,509](cyberppt/stage02_handoff.py:504) `CONTENT_PARENT_INVALID` |
| Source-order fidelity = 100% | 已保证 | [stage02_handoff.py:523,527](cyberppt/stage02_handoff.py:523) `CONTENT_ORDER_INVALID` |
| Source-role promotion count = 0 | 已保证 | [stage02_handoff.py:533,536](cyberppt/stage02_handoff.py:533) `CONTENT_ROLE_INVALID`/`CONTENT_PROMOTION_POLICY_INVALID`（handoff 层）+ [visual_structure_contract.py:431](cyberppt/visual_structure_contract.py:431) `CONTENT_FOCUS_PROMOTION`（Visual Structure 层）+ 编译期 `_build_executable_page()` 硬性 `_fail()` 守卫 |
| Cross-root semantic merge count | **真实值 14/23（见下）**，非合成断言的 0 | [visual_structure_contract.py:413](cyberppt/visual_structure_contract.py:413) `CONTENT_CROSS_ROOT_GROUPING` + 编译期硬性守卫；真实基线见 [test_content_structure_real_project_regression.py](tests/test_content_structure_real_project_regression.py) |
| Unauthorized semantic edge count | **不可测——能力未建设** | P1 推迟的语义边溯源审计（`reading_sequence` 与 `semantic_graph.edges` 解耦、`SEMANTIC_EDGE_UNGROUNDED`）。当前 `graph_edges`/`connectors` 仍由阅读顺序推导，未做业务关系溯源校验。 |
| Page-judgment drift count | **不可测——能力未建设** | 未建模独立 `page_judgment` 节点（P1 推迟的 semantic_anchor/composition_anchor/page_judgment 拆分）。 |
| Final-prompt grouping drift = 0（合规页面） | 已保证 | P2 `_semantic_groups()` 按 `root_id` 分组；真实数据实测见下 |

**"Unauthorized semantic edge count" 和 "Page-judgment drift count" 目前无法测量**——不是因为它们不重要，而是因为支撑这两项指标的能力本身在 P1 就被有意识地推迟了（详见 P1 的"明确不做的事"）。把它们标记为"0"会是一句谎言；如实标记为"不可测"，等这两项能力建设后再回填真实数字。

## 二、真实项目端到端回归

用仓库内已有的真实项目 `projects/power-data-infrastructure-cooperation-v16-20260815-foundation/`（真实 `script-final.md`、真实 Stage 01 `outline.json`/`source-truth.json`、真实历史 `visual/visual-design-decisions.json`）做了一次完整只读回归：用当前代码重新构建 Stage 02 handoff（获得全新 `content_integrity`），把**历史真实、未经修改**的 Visual Designer 决策原样喂给当前的 `_build_executable_page()`（P1 编译期守卫）与 `build_final_prompt_ir()`（P2 分组）。测试固化在 [tests/test_content_structure_real_project_regression.py](tests/test_content_structure_real_project_regression.py)。

### 抽样六页（对应原方案第22节场景类型）

| 页面 | 场景类型 | 结果 |
|---|---|---|
| P04 | 多因素共同支撑统一基础设施 | 通过，3 根模块 → 3 个 Prompt 语义组 |
| P05 | 四模块+边界内容防误判 | 通过，2 根模块 → 2 个 Prompt 语义组 |
| P06 | 五层+贯穿项 | **被拦截**：`CONTENT_CROSS_ROOT_GROUPING` |
| P12 | 三组方向+边界 | **被拦截**：`CONTENT_CROSS_ROOT_GROUPING` |
| P17 | 生命周期/演进关系 | **被拦截**：`CONTENT_CROSS_ROOT_GROUPING` |
| P31 | 六步流程 | 通过，3 根模块 → 3 个 Prompt 语义组 |

### 核实这不是误报

读取了 P06（[script-final.md:178-260](projects/power-data-infrastructure-cooperation-v16-20260815-foundation/workbench/scripts/final/script-final.md:178)）、P12（[:594-668](projects/power-data-infrastructure-cooperation-v16-20260815-foundation/workbench/scripts/final/script-final.md:594)）、P07（[:265-340](projects/power-data-infrastructure-cooperation-v16-20260815-foundation/workbench/scripts/final/script-final.md:265)）等页面原文。它们共享同一个作者写作模式：若干编号模块（①②③…）之后，跟着一到两条 0 缩进的独立边界/贯穿句。作者在"锚点覆盖说明"字段里**逐页明确写出**这些句子被有意从相邻模块中"下移出"，理由是"避免暗示虚假从属关系"（P06 原话）。而历史 Visual Designer 决策恰恰把这些句子重新合并进了相邻模块的证据单元——正是作者试图阻止的问题,只是在 P0/P1 之前没有任何机制能检测到。

### 全量扫描（23 个真实内容页,而非仅抽样 6 页）

对该项目全部 23 个有历史决策记录的内容页做了同样的扫描（`test_full_deck_cross_root_violation_baseline`）：

```
通过（9 页）：p04 p05 p08 p13 p18 p21 p22 p28 p31
跨根合并违规（14 页）：p06 p07 p10 p11 p12 p15 p16 p17 p20 p23 p24 p26 p27 p29
detail-only 焦点升格违规：0 页
```

**这是一个如实的、比原方案抽样预期更大的发现**：跨根合并不是这份真实文档里一两页的孤立缺陷,而是贯穿全文档 61%（14/23）页面的系统性历史模式——上面提到的"编号模块+独立边界句"是这份脚本从第一页到最后一页反复使用的写作规范,而旧版 Visual Designer/编译器在 P1 之前完全没有能力尊重这条边界。

**这 14 个页面目前处于"Stage 02 handoff 通过（P0 无异议）,但现有 Visual Structure 决策不再满足 P1 编译门禁"的状态**——不是内容或事实错误,是历史决策阶段的结构判断需要重新做一次。**修复这 14 页需要重新执行 Visual Structure Designer Skill 并重新生成该项目的 `visual-design-decisions.json`/`deck-visual-spec.json`/`generation-prompts.md`**，这属于仓库内另一份独立计划文档 [docs/superpowers/plans/2026-08-18-visual-structure-fidelity.md](docs/superpowers/plans/2026-08-18-visual-structure-fidelity.md) 的 Task 6（"重新生成项目产物并完成结构抽样复核"）范畴——本次 P3 只读验证,不执行该 Task 6（重新生成需要真正运行 Skill 和图像生成资源,是量级不同的工作,不应被本次静默接管）。

## 三、Legacy compatibility（向后兼容路径）

以下每一处都在 P0/P1/P2 的落地过程中被显式验证过，是"旧数据/未升级数据不会被新逻辑破坏"的完整保证清单：

| 缺失的数据 | 降级行为 | 代码位置 |
|---|---|---|
| Stage 02 handoff 里没有 `content_integrity`（旧版本产物） | `audit_stage02_handoff` 报 `CONTENT_STRUCTURE_MISSING`，明确阻断而非静默放行 | [stage02_handoff.py:495](cyberppt/stage02_handoff.py:495) |
| `visual-design-input.json` 页面没有 `content_integrity`（P1 之前生成的输入） | 编译期两条守卫（跨根合并、detail 升格）直接跳过，不阻断——因为 `content_nodes` 为空 | [visual_structure_stage.py](cyberppt/commands/visual_structure_stage.py) `_build_executable_page` |
| `page_spec` 没有 `content_integrity`（P1 之前编译的规格） | `_audit_content_integrity_alignment` 直接返回，不产生 `CONTENT_CROSS_ROOT_GROUPING`/`CONTENT_FOCUS_PROMOTION` | [visual_structure_contract.py](cyberppt/visual_structure_contract.py) |
| `EvidenceSpec.root_id` 为空（旧证据单元，或 `text_bindings` 缺失） | `_semantic_groups()` 退回按 `kind` 分组，与 P2 改造前的行为逐字节一致 | [artifact_prompt.py](scripts/imagegen_pipeline/artifact_prompt.py) `_semantic_groups` |

四层降级路径分别对应 handoff / design-input / page-spec / final-prompt 四个阶段，任一阶段数据缺失时不会向下游传播为崩溃或静默错误行为。

## 四、明确不做的事（沿用 P1/P2 的既有推迟项，本次不新增）

- 语义边溯源审计（`SEMANTIC_EDGE_UNGROUNDED`）——P1 推迟。
- `semantic_anchor`/`composition_anchor`/`page_judgment` 概念拆分——P1 推迟。
- `MAX_SEMANTIC_GROUPS` 动态化为页面根模块数量 + `CONTENT_STRUCTURE_CAPACITY_EXCEEDED`——P2 推迟。
- `final_prompt_contract.py` 的 Prompt-Artifact 交叉校验（`FINAL_PROMPT_GROUPING_DRIFT`）——P2 推迟。
- 重新生成 `power-data-infrastructure-cooperation-v16-20260815-foundation` 项目产物、修复 14 个被拦截页面——属于 [docs/superpowers/plans/2026-08-18-visual-structure-fidelity.md](docs/superpowers/plans/2026-08-18-visual-structure-fidelity.md) Task 6，本次不执行。

## 五、验证记录

- `pytest tests/test_content_structure_real_project_regression.py -q` — 4 项全部通过。
- 全量可采集测试套件（排除本仓库 Python 3.9 开发环境下已知的预置采集问题模块）：与 P2 完成时的失败清单逐条 diff 完全一致，零净新增失败，新增 4 个通过用例（820 → 824）。
