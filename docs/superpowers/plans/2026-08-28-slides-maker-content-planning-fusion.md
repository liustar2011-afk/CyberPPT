# Slides Maker 内容规划能力融合开发方案

> 结论：`SUPPORT WITH CONDITIONS`。融合目标成立，实施时选择性移植参考仓库的长材料分流、叙事候选差异检查、页面内容协议和成稿追踪算法；CyberPPT 继续保持单一主流程和既有权威产物，不引入第二套 Content Plan、checkpoint 或 gate 文件。

## 1. 目标与判断

本方案基于以下代码基线：

- CyberPPT 当前工作树，包含正在演进的语义论点模型、Foundation 投影和 Deck Plan 来源论点绑定。
- `addsumtech/slides_maker` commit [`0b38732543f62920f094a18c1621992068a18f57`](https://github.com/addsumtech/slides_maker/tree/0b38732543f62920f094a18c1621992068a18f57)，2026-08-27。

期望结果：

1. 长材料先做规模判断、结构映射和内容取舍，重点材料进入深读，其他部分保留诚实的阅读层级声明。
2. Deck Plan 在必要场景生成 2–3 个真正不同的叙事候选，并机械识别同构候选和陪跑方案。
3. 页面规划明确核心判断、问题、节奏、承载证据、口头讲述线索和前后承接。
4. 作者需要填写的合同字段明显减少，机器可以推导的字段由程序生成或在消费时检查。
5. 来源正确性继续作为底线能力，审核不再主导作者的页面构思过程。

独立判断的限制条件：

- 不整体移植参考仓库的 Agent Skill 工作流。
- 不新增第四个权威脚本内容产物。
- 不把全部事实做成强制 Claim Ledger。
- 不要求每一份短材料都竞争多个叙事候选。
- 不把 Stage 02 的视觉合同继续前置给 Deck Plan 作者填写。

## 2. 融合后的主流程

```text
source/
  ↓ 现有 source-to-markdown + prepare_source_map
来源规模与结构画像
  ├─ bounded：全文语义理解
  └─ long：全量结构映射 + 章节摘要 + 约 20% 承重内容深读
  ↓
source-truth.json
  - 原有事实、边界、论点
  - reading_strategy
  - source_assets（图表语义清单）
  ↓ 现有 project-foundation 机械投影
script/foundation.json
  ↓
script/deck-plan.json v2 lean
  - 叙事候选与选择结论
  - 页面核心判断、问题、beat、证据、spoken thread
  - 少量例外型来源声明
  ↓
script/dist/final-script.md
  ↓
现有 lint/audit + composed trace 重点检查
```

权威边界保持不变：

- 理解段继续以 `source-truth.json` 为统一来源基础。
- 脚本段继续只有 `foundation.json`、`deck-plan.json`、`dist/final-script.md` 三个权威内容产物。
- 长材料覆盖视图、叙事差异结果和 composed trace 均为派生诊断或人工审核视图。

## 3. 代码复用决策

| 参考仓库能力 | 处理方式 | CyberPPT 落点 | 理由 |
|---|---|---|---|
| `scripts/arc_divergence.py` | 直接改编核心算法 | 新增 `script_engine/narrative_arc.py` | 代码独立、CJK bigram 处理成熟、能检查 shape/order/ask/stance 和 strawman |
| `scripts/trace_composed.py` | 复用文本分类算法，替换 PPTX I/O | 新增 `script_engine/analysis_audits/composed_trace.py` | 保留 CJK n-gram、标识符和数字检查，直接读取现有 Final Script 与 Foundation |
| `content-plan-spec.md` 页面字段 | 映射到现有字段，少量增量 | `contracts/deck-plan.schema.json`、`cyberppt-script-plan` | `message/question/page_role/content/receives/next` 已覆盖大部分协议 |
| 长材料 map→triage→deep-read | 吸收方法，复用现有 source map 和语义分块 | `cyberppt/source_document_map.py`、`semantic_understanding.py` | CyberPPT 已有稳定提取、标题树、source unit 和 chunk 管线 |
| 图表 carrying element / wrong reading | 吸收语义合同 | Source Truth、Foundation、Deck Plan | 当前已有 caption/table unit，缺少图表的传播功能理解 |
| `extract_pdf.py` 图表定位与裁剪 | 首版暂缓，后续按需选择性移植 | 可选 `cyberppt/source_assets/pdf_figures.py` | 约数百行 PyMuPDF 逻辑，会新增依赖；首版可由 caption、表格和页码定位满足内容规划 |
| `ingest.py` | 不移植 | 继续使用 `source-to-markdown` 与 `prepare_source_map` | DOCX、表格、Office 转换功能大幅重叠 |
| `plan_wordcount.py` | 不移植 | 继续使用现有脚本质量与上屏密度检查 | 重复能力 |
| `.deck-gates.json`、checkpoint、dispatch brief | 不引入 | 使用现有对话确认、plan review 和 audit | 会形成平行状态体系和额外权威边界 |
| critic panel 多 Agent 编排 | 仅保留审阅问题框架 | AUTHOR/CRITIQUE Skill + composed trace | 常规流程维持轻量，高风险项目可显式启用独立 reviewer |

直接改编的代码需保留 MIT 版权说明，并在仓库根部增加 `THIRD_PARTY_NOTICES.md`，记录 Leo-Lyu、来源仓库、固定 commit 和改编文件。

## 4. 契约设计

### 4.1 长材料阅读策略

在现有 Source Truth 中增加 `reading_strategy`，并由 `project-foundation` 原样投影：

```json
{
  "reading_strategy": {
    "mode": "bounded | long",
    "basis": {
      "page_count": 86,
      "estimated_tokens": 73400,
      "source_count": 3,
      "threshold_reason": "aggregate_pages"
    },
    "sections": [
      {
        "section_id": "H012",
        "disposition": "deep_read | mapped | excluded",
        "reason": "直接承担交流目标中的实施路径",
        "source_unit_refs": ["U0121", "U0122"]
      }
    ],
    "deep_read_ratio": 0.21
  }
}
```

规则：

- 默认阈值沿用参考仓库经验值：总页数超过 45 页，或估算 token 无法在一次可靠语义读取中容纳时进入 `long`。
- 多文件按集合总量判断。
- `bounded` 保持现有全文严格语义覆盖。
- `long` 要求所有一级/二级结构都有 disposition；`deep_read` 才能支撑页面中的精确数字、引文和强事实判断；`mapped` 仅能支撑章节背景和选材判断；`excluded` 必须给出简短理由。
- `deep_read_ratio` 采用 15%–30% 的软范围，约 20% 是默认目标，材料结构和交流任务拥有更高优先级。
- 第一次人工停点合并展示交流目标与长材料选区，确认后进入深读。对短材料不增加交互节点。

`prepare_source_map()` 已经拥有文件 bytes、sha256、标题树和 unit 清单，只需补充：

- 每个来源的字符数、CJK 字符数、Latin word 数和估算 token。
- 可可靠取得时记录页数；无法取得时保持 `null` 并使用 token 估算。
- 集合级 `reading_load` 和推荐模式。

### 4.2 图表语义清单

Source Truth 增加 `source_assets`：

```json
{
  "id": "ASSET-007",
  "kind": "figure | table | chart | screenshot | equation",
  "caption": "图 3 业务协同机制",
  "locator": "source/report.pdf:p.18:fig.3",
  "carrying_element": "右侧闭环中的反馈回流箭头",
  "communication_function": "证明机制具备持续校正能力",
  "wrong_reading": "将流程理解为一次性交付",
  "source_refs": ["U0831", "U0832"]
}
```

首版候选来自现有 `caption`、`table_row`、图片邻接文本和页码信息。模型负责填写 `carrying_element`、`communication_function`、`wrong_reading`，校验器只验证字段完整和引用可解析。

### 4.3 Deck Plan v2 lean

新增：

```json
{
  "plan_contract_version": 2,
  "planning_profile": "lean",
  "delivery_mode": "presented | self_read",
  "narrative_design": {
    "mode": "direct | competitive",
    "chosen_id": "ARC-A",
    "candidates": [],
    "emotional_curve": "context → tension → discovery → proof → decision",
    "peak_page_id": "p07",
    "staged_reveal": "先建立问题规模，后展示核心机制"
  }
}
```

候选字段复用参考仓库的最小集合：

- `id`、`name`、`shape`
- `opening_roles`
- `audience_question`
- `objection`
- `closing_ask`
- `evidence_refs`
- `loss_reason`，仅未选候选填写

触发规则：

- 内容页少于 6 页、纯目录型汇报、用户已明确叙事结构时使用 `direct`。
- 决策汇报、方案推介、答辩、教学型长稿，或内容页达到 6 页且存在多种合理讲法时使用 `competitive`。
- `competitive` 生成 2–3 个候选；差异检查直接读取 `deck-plan.json`，不生成旁路 JSON。
- `source_structure_mode=preserve` 时，候选必须遵守来源章节集合和顺序，差异来自受众问题、论证角色、证据重心、异议处理和结尾行动。

页面继续复用现有字段：

| 内容规划语义 | 现有或新增字段 |
|---|---|
| Takeaway | 复用 `message` |
| 页面回答的问题 | 复用 `question` |
| Role | 复用 `page_role` |
| Content units | 复用 `content` |
| 前后承接 | 复用 `receives`、`next` |
| Beat | 新增 `beat` |
| Visual source | 新增 `visual_evidence` |
| Spoken Thread | 新增 `spoken_thread`，仅 presented 模式要求 |

`visual_evidence` 采用紧凑合同：

```json
{
  "kind": "asset | number | equation | none",
  "ref": "ASSET-007",
  "locator": "source/report.pdf:p.18:fig.3",
  "carrying_element": "反馈回流箭头",
  "answers": "what | how | why"
}
```

### 4.4 减少人工合同

Deck Plan v2 lean 的作者必填字段限定为：

- Deck：交流目标、受众、交付模式、主旨、叙事选择。
- Chapter：使命、问题、结论、来源论点绑定。
- Page：标题、问题、核心判断、角色、beat、内容单元、来源/证据、承接、可选视觉证据、可选 spoken thread。

下列现有字段在 v2 lean 中调整：

| 字段 | v2 处理 |
|---|---|
| `stage02_readiness` | 从 Deck Plan 作者合同移除，Stage 02 消费时派生 |
| `onscreen_contract` | 作者可显式覆盖；默认由 Final Script 上屏模块和现有编译逻辑生成 |
| `onscreen_composition` | 由最终页面内容与 Stage 02 规则派生 |
| `content_route` | 默认从 `page_role` 与内容语义推导；不确定时才要求作者填写 |
| `source_consumption.unit_dispositions` | 不再逐单元强制填写；仅对故意省略、留后、仅追溯等例外记录 |
| `evidence_fit_review` | 常规直接证据由程序检查；间接证据、推断关系和反例风险才要求人工说明 |
| `analysis_basis` | 仅在 inferred 分析或外部模型引入时要求 |
| `primary_relation` | 两个以上内容模块时要求，单判断页面自动为 `none` |

v1 的现有审计逻辑继续保留。`plan_contract_version=2 + planning_profile=lean` 才启用新规则，迁移期内 fixture 和历史项目无需立即改写。

### 4.5 选择性事实检查

不引入全量 Claim Ledger。采用三层轻量策略：

1. 来源内数字、日期、名称继续复用 `foundation.numbers/entities/facts` 和页面 `source_refs`。
2. 外部补充、时效性事实、推断结论使用页面级 `claim_checks`，包含 `claim`、`status`、`as_of`、`source_refs`。
3. composed trace 对 Final Script 中来源未出现的数字和标识符进行硬提醒，对普通改写只给审阅优先级。

这样可以保留参考仓库对可证伪内容的敏感性，同时避免每一句话进入登记表。

## 5. 分阶段实施计划

### Task 0：建立移植边界和基线

Files:

- Create: `THIRD_PARTY_NOTICES.md`
- Modify: `.agents/skills/cyberppt-source-foundation/SKILL.md`
- Modify: `.agents/skills/cyberppt-script-plan/SKILL.md`
- Modify: `.agents/skills/cyberppt-script-workflow/SKILL.md`

工作：

- 记录参考仓库固定 commit、MIT 许可和直接改编模块。
- 在 Skill 中写清单一权威链路、direct/competitive 触发条件和 lean 合同边界。
- 实施前保存当前未提交改动清单；涉及同一文件时基于现有工作树增量修改。

验收：文档没有新增 Content Plan、gate receipt、checkpoint 或平行项目目录。

### Task 1：实现来源规模画像与长材料分流

Files:

- Modify: `cyberppt/source_document_map.py`
- Modify: `cyberppt/semantic_understanding.py`
- Modify: `cyberppt/source_argument_model.py`
- Modify: `cyberppt/stage01_compiler.py`
- Modify: `cyberppt/foundation_projection.py`
- Modify: `contracts/foundation.schema.json`
- Test: `tests/test_source_document_map.py`
- Test: `tests/test_semantic_understanding.py`
- Test: `tests/test_stage01_compiler.py`
- Test: `tests/test_foundation_projection.py`

接口：

- `estimate_reading_load(units, sources) -> dict`
- `recommend_reading_mode(reading_load, *, max_pages=45, max_tokens=60_000) -> dict`
- `validate_reading_strategy(model, source_headings, source_unit_ids) -> list[issue]`
- `render_units_for_model(..., reading_strategy=...)`

实现顺序：

1. 先增加只读规模诊断，不改变现有 bounded 行为。
2. 增加 long 模式的 section disposition 校验。
3. 让模型输入包含完整骨架、mapped 摘要和 deep-read 原文。
4. 将 `reading_strategy` 投影到 Source Truth 和 Foundation。
5. 在 Source Foundation 的第一个人工停点展示选区与排除理由。

验收：

- 45 页以内 fixture 产物与当前行为一致。
- 多文件集合能按总量进入 long。
- long 模式未覆盖任一主结构、excluded 无理由、mapped 内容支撑精确数字时明确失败。
- 原始 source units 全部保留，深读范围只影响模型上下文和可用于强判断的证据范围。

### Task 2：加入图表传播语义

Files:

- Create: `cyberppt/source_assets.py`
- Modify: `cyberppt/source_document_map.py`
- Modify: `cyberppt/source_argument_model.py`
- Modify: `cyberppt/stage01_compiler.py`
- Modify: `cyberppt/foundation_projection.py`
- Modify: `contracts/foundation.schema.json`
- Test: `tests/test_source_document_map.py`
- Test: `tests/test_stage01_compiler.py`
- Test: `tests/test_foundation_projection.py`

接口：

- `asset_candidates(units, headings) -> list[dict]`
- `validate_source_assets(assets, source_unit_ids) -> list[issue]`

验收：

- Caption、表格和公式候选具有稳定 ID 和 locator。
- 每个进入页面规划的 source asset 都有 carrying element。
- `wrong_reading` 缺失时给 warning；承担 money slide 的 asset 缺失该字段时阻断。

### Task 3：移植叙事候选差异算法

Files:

- Create: `script_engine/narrative_arc.py`
- Modify: `contracts/deck-plan.schema.json`
- Modify: `script_engine/analysis_audits/deck_plan.py`
- Modify: `script_engine/plan_review.py`
- Modify: `.agents/skills/cyberppt-script-plan/SKILL.md`
- Test: `tests/script_engine/test_plan_review_and_internal_voice.py`
- Test: `tests/script_engine/test_semantic_guardrails.py`

复用范围：

- 保留参考实现的 CJK 连续区间 bigram 分词。
- 保留 shape/order/ask/stance 四轴比较。
- 保留“证据量低于最佳候选一半”的 strawman 检查。
- 将 `evidence` 改为 Foundation/Deck Plan 的 source refs 或 argument node IDs。
- 取消脚本独立 JSON 输入，直接接收 `narrative_design.candidates`。

验收：

- 中文近义候选可以得到渐进式相似度。
- 候选在三个及以上轴相同时给出 blocking issue。
- 陪跑候选和全候选无证据分别给出清晰诊断。
- direct 模式不承担多候选税。
- plan review 同屏展示候选、选择理由、落选理由、情绪曲线和 peak page。

### Task 4：落地 Deck Plan v2 lean 与页面内容协议

Files:

- Modify: `contracts/deck-plan.schema.json`
- Modify: `script_engine/contracts.py`
- Modify: `script_engine/analysis_audits/deck_plan.py`
- Modify: `script_engine/analysis_audits/final_script.py`
- Modify: `script_engine/plan_review.py`
- Modify: `cyberppt/stage02_handoff.py`
- Modify: `.agents/skills/cyberppt-script-plan/SKILL.md`
- Modify: `.agents/skills/cyberppt-script-author/SKILL.md`
- Test: `tests/script_engine/test_contract_and_render.py`
- Test: `tests/script_engine/test_plan_review_and_internal_voice.py`
- Test: `tests/script_engine/test_semantic_unit_consumption.py`

实现：

- schema 按 `plan_contract_version` 分支验证。
- v1 继续执行现有严格字段检查。
- v2 lean 只要求作者语义字段和例外型来源声明。
- `visual_evidence.ref` 必须解析到 Foundation asset/number/fact。
- presented 模式要求内容页有 `spoken_thread`；self_read 模式省略。
- `peak_page_id` 指向的页面必须承载 deck thesis 和具体证据；无单一高潮的材料允许填写 `no_single_peak_reason`。
- Stage 02 继续校验 title/message 与 Deck Plan 一致，视觉准备字段改为消费时派生。

验收：

- v1 fixtures 零回归。
- v2 每页人工字段数量相对当前正式计划减少至少 40%。
- 删除 v2 的 `stage02_readiness` 和逐 unit disposition 后，Final Script 与 Stage 02 仍能完成现有消费路径。
- plan review 可以直接支持人工判断，无需查看 JSON。

### Task 5：加入 composed trace 和聚焦型 Critic

Files:

- Create: `script_engine/analysis_audits/composed_trace.py`
- Modify: `script_engine/analysis_audits/final_script.py`
- Modify: `script_engine/cli.py`
- Modify: `.agents/skills/cyberppt-script-author/SKILL.md`
- Test: `tests/script_engine/test_semantic_guardrails.py`
- Test: `tests/script_engine/test_cli.py`

复用范围：

- 从 `trace_composed.py` 复用 `cjk_ngrams()`、`latin_tokens()`、`numbers()`。
- 使用现有 Final Script parser 和 Foundation source surface 替代 `python-pptx`。
- 来源缺失的数字、版本、路径、专名进入 hard findings。
- 普通 composed 文案只进入 Critic 优先列表，不作为机械错误。

CLI：

```bash
.venv/bin/cyberppt-script trace-composed \
  script/dist/final-script.json script/foundation.json
```

验收：

- 来源原句、自然改写、来源外数字、来源外标识符四类 fixture 结果稳定。
- source-supported inferred 分析不会被误判为来源外硬事实。
- Critic 优先审查 peak page、composed lines、外部 claim checks 和图表 wrong reading 风险。

### Task 6：真实项目验证与默认切换

Files:

- Add fixtures under: `tests/script_engine/fixtures/projects/`
- Modify: `benchmarks/run.py`
- Modify: `docs/CYBERPPT_WORKFLOW.md`
- Modify: `docs/AUTHORING_METHOD.md`

验证集：

1. 10–20 页的 bounded 正式材料。
2. 60 页以上的 long 单文件材料。
3. 三个短文件合计超过阈值的多文件材料。
4. 有图表、数字和外部时效事实的方案稿。
5. 纯综述、没有单一 peak 的材料。

运行：

```bash
.venv/bin/python3 -m pytest \
  tests/test_source_document_map.py \
  tests/test_semantic_understanding.py \
  tests/test_stage01_compiler.py \
  tests/test_foundation_projection.py \
  tests/script_engine/test_contract_and_render.py \
  tests/script_engine/test_plan_review_and_internal_voice.py \
  tests/script_engine/test_semantic_guardrails.py

.venv/bin/python3 -m pytest tests/script_engine tests/test_script_quality_contract.py
git diff --check
```

默认切换条件：

- v1 全部相关回归通过。
- 三个真实项目能完成 Foundation、Plan、Author、Stage 02 handoff。
- 盲评中，v2 在“叙事清晰、页面必要性、核心页力度、讲述连贯”四项至少三项优于 v1。
- 平均人工计划字段减少至少 40%。
- long 项目送入深读的原文字量降至全量的 15%–30%，且审阅者认可选区和排除理由。

完成上述条件后，`cyberppt-script-plan` 默认生成 v2 lean；v1 保留一个迁移周期，只读兼容继续存在。

## 6. 实施优先级

推荐顺序：

1. Task 3 叙事候选差异算法。
2. Task 4 Deck Plan v2 lean 与页面协议。
3. Task 5 composed trace。
4. Task 1 长材料分流。
5. Task 2 图表传播语义。
6. Task 6 默认切换。

这个顺序先改善用户最直接感知的内容规划质量和作者负担。长材料与图表能力随后接入，避免同时修改 Source Foundation、Deck Plan 和 Final Script 三个边界。

首个可交付里程碑由 Task 3 + Task 4 组成：用户可以看到真实叙事候选、选择理由、情绪曲线、peak page，以及更轻的逐页内容计划。该里程碑已能吸收参考仓库最有价值的内容规划能力。

## 7. 明确不做的事项

- 不复制参考仓库的完整 `skills/slide-maker` 目录。
- 不新增 `content-plan.md` 作为权威输入。
- 不新增 `.deck-gates.json`、checkpoint receipt、dispatch brief 或 review manifest。
- 不把 `extract_pdf.py` 的 PyMuPDF 依赖放进首版核心运行时。
- 不要求常规脚本必须由第二个 Agent 审稿。
- 不将 Claim Ledger 扩展为每句文本的登记制度。
- 不在本轮融合中重写 Stage 02 图像生成与 PPTX 装配。

## 8. 主要风险与控制

| 风险 | 控制 |
|---|---|
| long 模式因选区错误遗漏关键论点 | 全量结构映射、每节 disposition、选区与交流目标合并确认、mapped 内容不得支撑强事实 |
| 多候选退化成同一讲法换名字 | 四轴差异检查、证据量 strawman 检查、落选理由必填 |
| lean 合同削弱来源约束 | 保留 source refs、论点绑定、数字/标识符硬检查；省略型和推断型内容保留例外合同 |
| 新旧 schema 同时存在造成分支复杂 | 只以 `plan_contract_version` 分支，禁止另建新文件格式和新目录 |
| 图表语义依赖模型判断 | locator 与 source refs 机械校验，carrying element 进入人工 Plan review |
| 当前未提交改动与实施冲突 | 每个 Task 开始前检查目标文件 diff，基于现有语义论点绑定继续开发，不回退用户改动 |

## 9. 最终验收定义

融合完成后，一份典型正式材料应呈现以下体验：

- 短材料直接进入理解和规划，不增加流程负担。
- 长材料先展示规模、章节取舍和深读范围，用户能够及时修正选区。
- 复杂汇报能看到 2–3 个有实质差异的叙事候选和明确选择理由。
- 每页计划一眼可读：讲什么、回答什么、承担什么角色、处于什么节奏、由什么证据承载、现场如何讲、如何承接下一页。
- 作者无需填写视觉生产和逐原子事实处置的大量机械字段。
- 成稿审计把注意力集中到来源外数字、标识符、关键改写、高潮页和图表误读风险。
- 全流程仍沿用 CyberPPT 的既有目录、CLI、Source Truth、Foundation、Deck Plan、Final Script 和 Stage 02 消费链。
