# Slides Maker 内容规划能力融合开发方案

> 结论：`SUPPORT WITH CONDITIONS`。融合目标成立。当前首要任务调整为 Deck Plan 内容质量和上屏文字质量；默认 Source Foundation 同步收缩为“确定性来源索引 + 一次语义 Foundation”。实施时选择性移植参考仓库的叙事候选、页面内容规划和成稿追踪算法，不引入第二套 Content Plan、checkpoint 或 gate 文件。

## 1. 目标与判断

本方案基于以下代码基线：

- CyberPPT 可依赖基线为 commit `8726f23e97241efbf11bc59029bab55a92a2692b`（`feat(stage01): preserve source argument structure in planning`）。
- commit `f6a3745bbb08c27e35c8b6d92acf6e7c7eda826e`（`wip: checkpoint authoring workflow and power data project`）是一次未成功的试验，只作失败样本和反例证据，不作为能力、合同、代码或测试基线。
- `addsumtech/slides_maker` commit [`0b38732543f62920f094a18c1621992068a18f57`](https://github.com/addsumtech/slides_maker/tree/0b38732543f62920f094a18c1621992068a18f57)，2026-08-27。

### 1.1 可依赖基线与失败试验边界

commit `8726f23e` 已经完成以下基础能力：

- 语义模型显式保留 `document_semantics`、`document_thesis`、章节/小节论点节点和论点关系。
- `project-foundation` 将上述内容机械投影到 `foundation.json`。
- `deck-plan.json` 已增加 `source_thesis`、`source_argument_method`，章节和内容页已增加 `source_argument_node_ids`。
- Deck Plan 审计已经检查来源主论点漂移、来源论证顺序漂移、页面论点职责缺失、未知节点和证据不相交。
- Final Script 审计已经把带有来源论点职责的页面核心判断锁定到已批准的 Plan。
- projection-only 模型拥有独立校验路径，可以消费旧语义流水线的机械投影，同时避免伪装成完整的严格语义重写。

因此，本方案作出五项修订：

1. 删除“重新建立来源论点绑定”的开发工作，直接复用本次提交。
2. `source_thesis`、`source_argument_method`、章节/页面 `source_argument_node_ids` 成为 v2 lean 的必保留字段，不纳入减负删除范围。
3. 叙事候选只描述对既有来源论点链的受众化编排；候选不能改写来源主论点或覆盖来源论证顺序。
4. long 模式必须先建立完整来源论点骨架，再决定事实证据的深读层级；mapped 章节仍保留论点节点和章节责任。
5. Source Foundation 相关任务聚焦 `reading_strategy` 和 `source_assets`，不再扩建第二套论点模型。

commit `f6a3745` 增加的五步上屏写作法、silent-reader/ten-second/deletion 测试、`phrase_led_basis`、可读命题启发式检查、演讲者备注规则及其配套 schema/audit 不进入本方案的依赖集。实施时以 `8726f23e` 为语义基准逐项审查 `f6a3745` 的增量：未由独立测试和真实质量收益证明的改动不复用，与新闭环冲突的改动应移除或替换。

对该失败试验附带的 21 页真实项目复核后，得到以下反例结论：

- Deck Plan 平均每页约 23 个字段，规划工作被来源消费、表达模式、Stage 02 准备和审计说明分散。
- 18 个内容页中，多数核心判断采用“A 明确……，B 构成……，C 提供……”的来源覆盖摘要，页面完整却缺少取舍、张力和不可替代的认知收益。
- 上屏页面普遍使用 3–6 个模块和大量“标签：说明”条目；P03 的可见文字约 432 个非空白字符，P04 约 385，实际上更接近结构化文稿。
- `final-script-qa.md` 报告 0 错误、0 警告和 160 项测试通过，与实际阅读质量不一致。现有测试主要证明 schema、绑定、禁词和启发式条件有效，尚未证明页面值得存在、核心判断有力或文字可以快速阅读。

根因判断：该试验用更多提示词、字段和启发式检查代替了真正执行的“候选内容生成→定性评审→整页/整稿重写”闭环，并将平庸 Plan message 锁定为下游的质量上限。本方案用该结果定义反例和验收下限，不继承其实现路线。

### 1.2 Source Foundation 重量审计与新结论

以当前真实项目 `power-data-infrastructure-standard-system-research-20260828-003` 为样本，已验证：

- 单一 DOCX 项目生成 55 个文件，workbench 和脚本产物合计约 2.37MB。
- `fact-base.json` 约 143KB、`normalized-facts.json` 约 108KB、`semantic-argument-model.json` 约 205KB、`source-truth.json` 约 482KB、最终 `foundation.json` 约 301KB。
- 187 条结构化事实先归并为 166 条 normalized facts，随后又投影为 semantic model、166 条 Source Truth records 和 165 条 Foundation facts。
- `concept-base.json`、`relation-graph.json` 和 `argument-chain.json` 经过 `source_foundation_projection.py` 再编码，最终下游只消费 `foundation.json` 中的 concepts、relations、argument nodes 和 source refs。
- Source Foundation Skill 当前要求 source-to-markdown、结构/事实基础、四份语义权威、semantic model、Source Truth、Source Truth audit、Foundation 投影，流程成本与脚本工具的核心价值不匹配。

反例检查也成立：稳定 source unit、标题树、文件哈希和 source refs 被 Plan/Author 审计真实消费，全部移除会破坏来源定位和数字/边界回查。

据此调整为两档路线：

| Profile | 使用场景 | 路线 |
|---|---|---|
| `script`（默认） | 常规汇报、方案、研究报告、演讲脚本 | `prepare-source-context → cyberppt-script-understand → foundation.json` |
| `strict`（显式） | 合同、监管、逐事实核验、用户明确要求完整知识建模 | 保留现有 Source Foundation 全量链路，再投影 Foundation |

默认 `script` 路线只保留两个动作：

1. 确定性提取来源结构和稳定 source units，合并写入现有 `script/.cache/source-index.json` 的 v2 格式；OCR、Office 转换仅在直接解析失败时启用。
2. 使用现有 `cyberppt-script-understand` 一次生成 `script/foundation.json`，随后立即进入 PLAN。

旧项目继续读取既有 Source Truth 和 Foundation。`source_foundation_pipeline.py`、四份 business-semantic 产物、semantic model 和 Source Truth 不再是新脚本项目的默认前置条件。

### 1.3 Microsoft MarkItDown 依赖调整

已验证 MarkItDown 核心包约 0.6MB，主要重量来自当前安装脚本固定执行 `pip install 'markitdown[all]'`：

- 当前环境中，仅主要可选依赖的安装体积合计已超过约 149MiB。
- 较大的组件包括 SpeechRecognition 约 42.7MiB、pandas 约 36.9MiB、Magika 约 29.1MiB、lxml 约 18.8MiB、PDF 相关包约 8.4MiB，以及当前脚本任务通常不需要的 Azure SDK、音频和 YouTube 组件。
- MarkItDown 未列入仓库 `pyproject.toml` 核心依赖，但 Skill 安装脚本会创建完整 `[all]` 环境，形成隐性运行时。
- CyberPPT 已经原生解析 DOCX、Markdown、TXT、JSON、CSV、TSV 和 YAML；常见 DOCX 先转 Markdown再解析会重复读取和重建结构。

调整后的转换策略：

| 输入 | 默认处理 | MarkItDown |
|---|---|---|
| DOCX | 复用 `source_document_map.py` 原生 XML 提取 | 不调用 |
| MD/TXT/JSON/CSV/TSV/YAML | 直接读取 | 不调用 |
| PPTX | 优先增加基于现有 `python-pptx` 的轻量文字/备注提取 | 提取失败时按需安装 `markitdown[pptx]` |
| XLSX | 按需使用 `openpyxl` 轻量适配器 | 复杂工作簿再使用 `markitdown[xlsx]` |
| PDF | 保留格式专用回退 | 需要 PDF 时安装 `markitdown[pdf]`，扫描件再显式启用 OCR |
| HTML | 标准 HTML/Markdown 转换 | 需要时使用 MarkItDown 基础包 |
| 音频、视频、Outlook、YouTube、Azure Document Intelligence | 不属于默认 PPT 脚本来源路径 | 用户明确提供对应格式时单独安装能力 |

删除 `[all]` 安装方式。MarkItDown 保留为格式适配器，采用按格式 extras 和 Skill-local 环境，不进入默认 Source Foundation 路线，也不进入仓库核心依赖。

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
  ↓ prepare-source-context（直接解析优先，转换/OCR 按需回退）
来源规模与结构画像
  ├─ bounded：一次语义 Foundation
  └─ long：全量结构映射 + 章节摘要 + 约 20% 承重内容深读
  ↓
script/foundation.json
  - 来源结构、稳定引用、关键事实与边界
  - 来源主论点与完整论点骨架
  - reading_strategy
  - source_assets（图表语义清单）
  ↓
script/deck-plan.json v2 lean
  - 原样继承 source_thesis / source_argument_method
  - 章节与页面绑定 source_argument_node_ids
  - 叙事候选与选择结论
  - 页面存在理由、核心判断、问题、beat、证据取舍、spoken thread
  - 少量例外型来源声明
  ↓ Plan Critic（全稿定性评审与重写）
  ↓
script/dist/final-script.md
  ↑ 先写完整页面论证，再选择上屏信息
  ↓ Onscreen Critic（页内候选、静默阅读、整页重写）
  ↓
现有 lint/audit + composed trace 重点检查
```

权威边界保持不变：

- 脚本段继续只有 `foundation.json`、`deck-plan.json`、`dist/final-script.md` 三个权威内容产物。
- 默认 script profile 的理解结果直接写入 `foundation.json`；`script/.cache/source-index.json` 是唯一来源派生索引。
- strict profile 的 Source Truth 只服务严格核验和旧项目兼容，投影后的 `foundation.json` 仍是脚本规划入口。
- 长材料覆盖视图、叙事差异结果和 composed trace 均为派生诊断或人工审核视图。

## 3. 代码复用决策

| 参考仓库能力 | 处理方式 | CyberPPT 落点 | 理由 |
|---|---|---|---|
| `scripts/arc_divergence.py` | 直接改编核心算法 | 新增 `script_engine/narrative_arc.py` | 代码独立、CJK bigram 处理成熟、能检查 shape/order/ask/stance 和 strawman |
| `scripts/trace_composed.py` | 复用文本分类算法，替换 PPTX I/O | 新增 `script_engine/analysis_audits/composed_trace.py` | 保留 CJK n-gram、标识符和数字检查，直接读取现有 Final Script 与 Foundation |
| `content-plan-spec.md` 页面字段 | 映射到现有字段，少量增量 | `contracts/deck-plan.schema.json`、`cyberppt-script-plan` | `message/question/page_role/content/receives/next` 已覆盖大部分协议 |
| 长材料 map→triage→deep-read | 吸收方法，复用现有提取器和 source index | `cyberppt/source_document_map.py`、`script_engine/source_index.py`、`cyberppt-script-understand` | 标题树和 source unit 足以承担 map；无需先生成四份语义中间产物 |
| 图表 carrying element / wrong reading | 吸收语义合同 | Foundation、Deck Plan | 当前已有 caption/table unit，缺少图表的传播功能理解 |
| `extract_pdf.py` 图表定位与裁剪 | 首版暂缓，后续按需选择性移植 | 可选 `cyberppt/source_assets/pdf_figures.py` | 约数百行 PyMuPDF 逻辑，会新增依赖；首版可由 caption、表格和页码定位满足内容规划 |
| `ingest.py` | 不移植 | 复用现有直接提取器；`source-to-markdown` 仅作格式/OCR 回退 | DOCX、表格、Office 转换功能大幅重叠 |
| `plan_wordcount.py` | 不移植 | 继续使用现有脚本质量与上屏密度检查 | 重复能力 |
| `.deck-gates.json`、checkpoint、dispatch brief | 不引入 | 使用现有对话确认、plan review 和 audit | 会形成平行状态体系和额外权威边界 |
| critic panel 多 Agent 编排 | 仅保留审阅问题框架 | AUTHOR/CRITIQUE Skill + composed trace | 常规流程维持轻量，高风险项目可显式启用独立 reviewer |

直接改编的代码需保留 MIT 版权说明，并在仓库根部增加 `THIRD_PARTY_NOTICES.md`，记录 Leo-Lyu、来源仓库、固定 commit 和改编文件。

## 4. 契约设计

### 4.0 最小 Foundation 合同

默认 script profile 的 `foundation.json` 只保留下游规划和写作会消费的内容：

| 字段 | 保留原则 |
|---|---|
| `sources`、`source_structure` | 全量保留来源身份、哈希、标题层级和顺序 |
| `document_semantics`、`document_thesis` | 保留全文业务主语、目的、边界和主论点 |
| `argument_nodes`、`argument_relations` | 每个实质章节至少一个论点节点，保留来源论证骨架 |
| `facts` | 只保留支撑核心/支持论点、关键数字、责任、状态、条件、边界和图表解读的事实 |
| `constraints`、`numbers`、`open_questions` | 有实际内容时保留 |
| `concepts`、`entities`、`relations` | 只保留被论点、事实或页面规划引用的项目，不做全量知识图谱 |
| `reading_strategy`、`source_assets` | 按材料需要保留 |

默认审计从“每个源段落都必须进入一条 atomic assignment”调整为：

1. 每个实质一级/二级标题都有论点节点或明确的 `trace_only/excluded` disposition。
2. 每个 Foundation 事实都有稳定 source refs。
3. 每个 Deck Plan 核心判断都绑定论点节点和实际证据。
4. 数字、日期、主体、责任、状态、条件和边界在进入页面时可回查。
5. 未进入 Foundation 的普通说明段落无需建立 omission record。

strict profile 保留逐事实 normalization、atomic items、全 source-unit disposition 和 Source Truth cross-audit。材料很长不会自动触发 strict；严格模式由用户要求、合同/监管场景或明确的逐事实核验目标触发。

### 4.1 长材料阅读策略

默认 script profile 直接在 `foundation.json` 中写入 `reading_strategy`；strict profile 允许从 Source Truth 原样投影同一字段：

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
- `bounded` 一次读取 source units，直接生成 Foundation。
- `long` 先根据标题树建立完整的 `document_thesis`、章节论点节点和 `argument_method`，随后对事实证据分配 disposition。
- `long` 要求所有一级/二级结构都有 disposition；`deep_read` 才能支撑页面中的精确数字、引文和强事实判断；`mapped` 保留章节论点、结构位置和选材判断；`excluded` 必须给出简短理由。
- `reading_strategy.sections[].argument_node_ids` 必须解析到当前语义模型；进入 Deck Plan 的论点节点至少拥有一组 deep-read 证据，只有 mapped 支撑的节点不能承担页面核心判断。
- `foundation.document_semantics.argument_method` 始终保留来源论证顺序。阅读层级不会裁剪或重排该数组。
- `deep_read_ratio` 采用 15%–30% 的软范围，约 20% 是默认目标，材料结构和交流任务拥有更高优先级。
- 第一次人工停点合并展示交流目标与长材料选区，确认后进入深读。对短材料不增加交互节点。

`source_document_map.py` 的现有提取逻辑已经拥有文件 bytes、sha256、标题树和 unit 清单，只需补充：

- 每个来源的字符数、CJK 字符数、Latin word 数和估算 token。
- 可可靠取得时记录页数；无法取得时保持 `null` 并使用 token 估算。
- 集合级 `reading_load` 和推荐模式。

### 4.2 图表语义清单

Foundation 增加 `source_assets`：

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
- `argument_focus_node_ids`，必须是 `source_argument_method` 的子集
- `evidence_refs`，必须与聚焦论点节点的 `source_refs` 相交
- `loss_reason`，仅未选候选填写

触发规则：

- 内容页少于 6 页、纯目录型汇报、用户已明确叙事结构时使用 `direct`。
- 决策汇报、方案推介、答辩、教学型长稿，或内容页达到 6 页且存在多种合理讲法时使用 `competitive`。
- `competitive` 生成 2–3 个候选；差异检查直接读取 `deck-plan.json`，不生成旁路 JSON。
- `source_structure_mode=preserve` 时，候选必须遵守来源章节集合和顺序，差异来自受众问题、论证角色、证据重心、异议处理和结尾行动。
- 每个候选共享同一份 `source_thesis` 和 `source_argument_method`。候选只能选择强调哪些节点、用什么页面角色展开以及如何面向受众收束。
- 用户明确授权重构时，授权只影响 Deck 的展示顺序；Foundation 中的来源论点图保持原样，Plan 另行记录展示顺序与来源顺序的映射。

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

每页规划先完成一个内容决策，然后填写机器字段。必须回答：

1. 这页解决听众的哪一个问题？
2. 这页希望听众记住的唯一判断是什么？
3. 删除这页后，整个论证会缺失什么？
4. 哪些证据直接证明该判断，哪些来源内容需要主动不上屏？
5. 这页相对前后页推进了哪一步？

`message` 写有争辩价值的结论，避免把页内模块逐项串联成摘要。`content` 只收纳建立判断所需的信息单元，不承担来源全覆盖。

PLAN 采用两次生成：

- 第一次只生成全稿论证脊柱、页面必要性、money slide 和页间推进；
- 第二次再写页面问题、`message`、证据选择、内容单元和口头讲述线索。

完成后执行一次全稿 Plan Critic，至少评判页面必要性、核心判断力度、相邻重复、证据充分性、叙事连续性和高潮页。Critic 产出内部问题清单并直接重写 `deck-plan.json`，不新增权威文件。

### 4.3.1 上屏内容生成闭环

AUTHOR 先根据已批准 Plan 写完整页面论证，再做语义压缩。上屏内容只保留两类单元：可独立理解的命题、直接支撑命题的证据。

对高密度页、money slide、结论页和 Critic 评为弱的页面，内部生成两个上屏候选：

- 判断主导：用少量完整命题承担主要认知；
- 证据主导：用数字、分类、对比、流程或关系作为主视觉载体。

Onscreen Critic 使用页面任务、完整文字稿和候选文案做定性选择，评分主判断可见性、10 秒理解、文字密度、信息重复、关系可见性和语义完整性。失败时重写整页的信息组织，避免逐句打补丁。现有 deterministic lint 只阻断明显泄漏、虚假层级、来源越界和极端密度问题。

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

- Deck：交流目标、受众、交付模式、来源主论点、来源论证顺序、全稿主旨、叙事选择。
- Chapter：使命、问题、结论、`source_argument_node_ids`。
- Page：标题、问题、核心判断、角色、beat、内容单元、`source_argument_node_ids`、来源/证据、承接、可选视觉证据、可选 spoken thread。

commit `8726f23e` 形成的四项来源论点字段属于 lean 核心，不允许自动省略：

| 层级 | 必保留字段 | 作用 |
|---|---|---|
| Deck | `source_thesis` | 精确复制 `foundation.document_thesis.statement` |
| Deck | `source_argument_method` | 精确保留来源论点节点顺序 |
| Chapter | `source_argument_node_ids` | 声明章节承担哪些来源论点 |
| Page | `source_argument_node_ids` | 声明内容页的不可替代论点职责 |

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
- Modify: `AGENTS.md`
- Modify: `docs/CYBERPPT_WORKFLOW.md`
- Modify: `docs/MIGRATION_FROM_LEGACY_STAGE01.md`
- Modify: `.agents/skills/cyberppt-source-foundation/SKILL.md`
- Modify: `.agents/skills/cyberppt-script-understand/SKILL.md`
- Modify: `.agents/skills/cyberppt-script-plan/SKILL.md`
- Modify: `.agents/skills/cyberppt-script-workflow/SKILL.md`
- Modify: `.agents/skills/source-to-markdown/SKILL.md`
- Modify: `.agents/skills/source-to-markdown/scripts/install.sh`
- Modify: `.agents/skills/source-to-markdown/scripts/install.ps1`
- Modify: `.agents/skills/source-to-markdown/references/usage.md`
- Create: `benchmarks/stage01_content_quality/README.md`
- Create: `benchmarks/stage01_content_quality/rubric.json`
- Create: `benchmarks/stage01_content_quality/cases/`

工作：

- 记录参考仓库固定 commit、MIT 许可和直接改编模块。
- 将新项目默认路线改为 `prepare-source-context → cyberppt-script-understand → foundation.json → PLAN/AUTHOR`。
- 将现有 `source_foundation_pipeline → business-semantic-understanding → Source Truth → project-foundation` 标记为 strict/legacy 路线，只在显式 profile 或旧项目迁移时运行。
- 删除 `markitdown[all]` 默认安装，改为基础包和 `pdf/pptx/xlsx` 等格式级按需安装；OCR 继续保持显式启用。
- 在 Skill 中写清 direct/competitive 触发条件和 lean 合同边界。
- 将 commit `8726f23e` 作为来源论点结构基线；任何后续 schema 和 audit 修改都必须保留其测试语义。
- 对 `8726f23e..f6a3745` 的代码、Skill、schema 和测试差异建立一次性处置清单：`remove`、`replace`、`independently_revalidate`。默认处置为 `remove`，只有脱离该项目后仍能证明价值的增量才能进入 `independently_revalidate`。
- 将 commit `f6a3745` 的真实项目作为首个失败反例，抽取不含敏感信息的页面级 fixture；当前 Plan/Final Script 只是 before 样本，不是期望输出。
- 建立人工可读评分表：Deck Plan 评页面必要性、核心判断、证据选择、叙事推进；上屏文字评静默阅读、10 秒理解、密度、重复和语义完整。
- 实施前检查未跟踪的真实项目目录，只修改代码、合同、Skill、测试和明确的 fixture。

验收：默认新项目不生成 normalized facts、concept base、relation graph、argument chain、semantic model 或 Source Truth；strict/legacy 项目仍可完整运行；文档没有新增 Content Plan、gate receipt、checkpoint 或平行项目目录；`f6a3745` 的增量完成处置分类，新能力测试不引用该提交的期望值；现有电力项目完成一次盲评基线记录，不再使用“lint 全通过”代表内容质量通过。

### Task 1：实现来源规模画像与长材料分流

Files:

- Modify: `cyberppt/source_document_map.py`
- Modify: `script_engine/source_index.py`
- Create: `cyberppt/source_extractors.py`
- Create: `cyberppt/foundation_authoring.py`
- Modify: `cyberppt/cli.py`
- Modify: `contracts/foundation.schema.json`
- Modify: `script_engine/analysis_audits/foundation.py`
- Modify: `.agents/skills/cyberppt-script-understand/SKILL.md`
- Test: `tests/test_source_document_map.py`
- Test: `tests/test_source_context.py`
- Test: `tests/test_foundation_authoring.py`
- Test: `tests/test_foundation_projection.py`

接口：

- `estimate_reading_load(units, sources) -> dict`
- `recommend_reading_mode(reading_load, *, max_pages=45, max_tokens=60_000) -> dict`
- `prepare_source_context(project) -> script/.cache/source-index.json`
- `extract_pptx_units(path) -> units, headings, warnings`
- `extract_xlsx_units(path) -> units, headings, warnings`（仅在 optional `openpyxl` 可用时）
- `prepare_script_foundation(project, *, profile="script") -> dict`
- `validate_reading_strategy(foundation, source_headings, source_unit_ids) -> list[issue]`
- `render_source_context(..., reading_strategy=...)`

实现顺序：

1. 从 `source_document_map.py` 提取纯解析函数，并将现有 `script_engine/source_index.py` 升级为 v2：同一文件容纳 sources、hashes、source_structure、stable units 和 reading load。
2. 使用现有 `python-pptx` 增加 PPTX 文字、表格和 speaker notes 提取；XLSX 使用可选 `openpyxl`，PDF 继续走格式级 MarkItDown 回退。
3. `prepare-source-context` 默认只写 `script/.cache/source-index.json`；strict profile 的 `prepare_source_map` 复用同一解析结果并继续写展开式诊断文件。
4. 增加只读规模诊断，不改变现有 bounded 行为。
5. `prepare-script-foundation` 直接输出 `foundation.json` 的 authoring task，复用现有 Foundation schema、`cyberppt-script-understand` 和 `audit-foundation`。
6. 将 Foundation completeness 改成结构覆盖、论点覆盖和页面可用证据覆盖，不再要求普通段落逐项登记。
7. 增加 long 模式的 section disposition 校验。
8. 让模型输入包含完整论点骨架、mapped 摘要和 deep-read 原文。
9. 在第一个人工停点展示交流目标、选区与排除理由。

验收：

- 45 页以内 fixture 产物与当前行为一致。
- 多文件集合能按总量进入 long。
- long 模式未覆盖任一主结构、excluded 无理由、mapped 内容支撑精确数字时明确失败。
- 原始 source units 全部保留，深读范围只影响模型上下文和可用于强判断的证据范围。
- long 模式的 `document_thesis` 和 `argument_method` 仍覆盖完整来源结构；深读取舍不会改变来源论证顺序。
- 原有 `SOURCE_ARGUMENT_THESIS_DRIFT`、`SOURCE_ARGUMENT_METHOD_DRIFT`、`SOURCE_ARGUMENT_BINDING_MISSING` 回归全部通过。
- 默认 script profile 从源文件到可审计 Foundation 只新增 `script/.cache/source-index.json` 和 `script/foundation.json`。
- 全新核心环境未安装 MarkItDown 时，DOCX、文本类和 PPTX 来源仍可进入 Foundation。
- 安装 PDF 支持不会同时安装音频、YouTube、Outlook 和 Azure extras。
- strict profile 的 `project-foundation` 投影结果仍通过现有 schema 和回归测试。

### Task 2：加入图表传播语义

Files:

- Create: `cyberppt/source_assets.py`
- Modify: `cyberppt/source_document_map.py`
- Modify: `contracts/foundation.schema.json`
- Modify: `.agents/skills/cyberppt-script-understand/SKILL.md`
- Test: `tests/test_source_document_map.py`
- Test: `tests/test_foundation_authoring.py`

接口：

- `asset_candidates(units, headings) -> list[dict]`
- `validate_source_assets(assets, source_unit_ids) -> list[issue]`

验收：

- Caption、表格和公式候选具有稳定 ID 和 locator。
- 每个进入页面规划的 source asset 都有 carrying element。
- 每个进入页面规划的 source asset 至少绑定一个 `argument_node_id`，其 source refs 与论点节点证据相交。
- `wrong_reading` 缺失时给 warning；承担 money slide 的 asset 缺失该字段时阻断。

### Task 3：建立叙事候选和 Plan Critic 重写闭环

Files:

- Create: `script_engine/narrative_arc.py`
- Create: `script_engine/source_arguments.py`（从现有 Deck Plan 审计提取共享索引和证据相交 helper）
- Modify: `contracts/deck-plan.schema.json`
- Modify: `script_engine/analysis_audits/deck_plan.py`
- Modify: `script_engine/plan_review.py`
- Modify: `.agents/skills/cyberppt-script-plan/SKILL.md`
- Create: `script_engine/plan_quality.py`
- Modify: `.agents/skills/chapter-structure-review/SKILL.md`
- Test: `tests/script_engine/test_plan_review_and_internal_voice.py`
- Test: `tests/script_engine/test_semantic_guardrails.py`

复用范围：

- 保留参考实现的 CJK 连续区间 bigram 分词。
- 保留 shape/order/ask/stance 四轴比较。
- 保留“证据量低于最佳候选一半”的 strawman 检查。
- 将候选的内容责任拆成 `argument_focus_node_ids` 与 `evidence_refs`；前者比较论点重心，后者检查实际证据投入。
- 取消脚本独立 JSON 输入，直接接收 `narrative_design.candidates`。
- 从当前 `_source_argument_binding_issues()` 提取共享的节点索引与证据相交 helper；原审计和叙事候选检查共同调用，避免新增第二套节点解析器。
- PLAN Skill 改为两次写作：先论证脊柱和页面必要性，再页面内容简报。
- Plan Critic 一次读取整份计划，对弱判断、“覆盖 A/B/C”型摘要、重复页、无证据页、无高潮页和断裂承接做定性评审。
- Critic 必须重写失败页和受影响的前后页，完成后再运行确定性 audit。内部评论不落盘为第四个权威产物。

验收：

- 中文近义候选可以得到渐进式相似度。
- 候选在三个及以上轴相同时给出 blocking issue。
- 陪跑候选和全候选无证据分别给出清晰诊断。
- direct 模式不承担多候选税。
- plan review 同屏展示候选、选择理由、落选理由、情绪曲线和 peak page。
- 修改任一候选都不能改变 `source_thesis` 或 `source_argument_method`；相应漂移测试必须继续阻断。
- 内容质量 fixture 中的摘要型 message 必须触发 Critic 重写，改写后页面必要性和核心判断的人工盲评中位数至少提升 1 档。

### Task 4：落地 Deck Plan v2 lean 和上屏内容重写闭环

Files:

- Modify: `contracts/deck-plan.schema.json`
- Modify: `script_engine/contracts.py`
- Modify: `script_engine/analysis_audits/deck_plan.py`
- Modify: `script_engine/analysis_audits/final_script.py`
- Modify: `script_engine/plan_review.py`
- Modify: `cyberppt/stage02_handoff.py`
- Modify: `.agents/skills/cyberppt-script-plan/SKILL.md`
- Modify: `.agents/skills/cyberppt-script-author/SKILL.md`
- Modify: `references/screen-copy-authoring.md`
- Modify: `references/script-quality-rubric.md`
- Create: `script_engine/onscreen_quality.py`
- Test: `tests/script_engine/test_contract_and_render.py`
- Test: `tests/script_engine/test_plan_review_and_internal_voice.py`
- Test: `tests/script_engine/test_semantic_unit_consumption.py`

实现：

- schema 按 `plan_contract_version` 分支验证。
- v1 继续执行现有严格字段检查。
- v2 lean 只要求作者语义字段和例外型来源声明。
- v2 lean 强制保留 `source_thesis`、`source_argument_method` 和章节/页面 `source_argument_node_ids`，并复用现有来源论点审计。
- `visual_evidence.ref` 必须解析到 Foundation asset/number/fact。
- presented 模式要求内容页有 `spoken_thread`；self_read 模式省略。
- `peak_page_id` 指向的页面必须承载 deck thesis 和具体证据；无单一高潮的材料允许填写 `no_single_peak_reason`。
- Stage 02 继续校验 title/message 与 Deck Plan 一致，视觉准备字段改为消费时派生。
- AUTHOR 严格执行“完整页面论证→上屏信息选择→候选表达→定性评审→整页重写”。
- 对高密度、money slide、结论和评审失败页内部生成“判断主导/证据主导”两个候选，只保留胜出结果。
- `onscreen_quality.py` 只负责组装评审上下文、计算密度/重复度和记录评分；它不用正则生成上屏文案。
- Plan message 仍是批准边界。AUTHOR 发现 Plan message 无法形成强页面时，回到 PLAN 重写该页和相关承接，再重新确认，避免在平庸判断上继续压缩。

验收：

- v1 fixtures 零回归。
- v2 每页人工字段数量相对当前正式计划减少至少 40%。
- 删除 v2 的 `stage02_readiness` 和逐 unit disposition 后，Final Script 与 Stage 02 仍能完成现有消费路径。
- plan review 可以直接支持人工判断，无需查看 JSON。
- 现有 `test_semantic_foundation_requires_deck_plan_argument_bindings`、`test_semantic_foundation_accepts_connected_deck_plan_argument_bindings` 和 Final Script proposition drift 测试在 v2 下同样成立。
- 电力样本 P03/P04 的上屏非空白字符显著下降，同时关键任务、责任、数字和边界无丢失；盲评中 10 秒理解和语义完整性中位数至少提升 1 档。

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
  tests/test_source_context.py \
  tests/test_foundation_authoring.py \
  tests/test_foundation_projection.py \
  tests/script_engine/test_contract_and_render.py \
  tests/script_engine/test_plan_review_and_internal_voice.py \
  tests/script_engine/test_semantic_guardrails.py

# strict/legacy compatibility
.venv/bin/python3 -m pytest \
  tests/test_semantic_understanding.py \
  tests/test_business_semantic_fact_types.py \
  tests/test_source_foundation_projection.py \
  tests/test_stage01_compiler.py \
  tests/test_foundation_projection.py

.venv/bin/python3 -m pytest tests/script_engine tests/test_script_quality_contract.py
git diff --check
```

默认切换条件：

- v1 全部相关回归通过。
- 三个真实项目能完成 Foundation、Plan、Author、Stage 02 handoff。
- 默认 script profile 的来源理解阶段只新增 `script/.cache/source-index.json` 和 `script/foundation.json`，且不产生四份 business-semantic 产物、semantic model 和 Source Truth。
- 同一材料的默认结构化产物总体积不超过 strict profile 的 40%。
- Foundation 人工审核能直接看到来源结构、主论点、论点链、关键事实、数字、边界、图表和 open questions，不依赖中间 JSON 才能理解。
- 对同一批材料双跑 script/strict profile；script profile 的关键数字、责任、条件、边界召回率不得下降，Plan/Final Script 来源错误数不得增加。
- 若 strict profile 在某类材料上稳定产生可见质量收益，将该类材料记录为 strict 路由条件；不能据单个样例把 strict 恢复为默认。
- 盲评中，v2 在“叙事清晰、页面必要性、核心页力度、讲述连贯”四项至少三项优于 v1。
- 平均人工计划字段减少至少 40%。
- long 项目送入深读的原文字量降至全量的 15%–30%，且审阅者认可选区和排除理由。

完成上述条件后，`cyberppt-script-plan` 默认生成 v2 lean；v1 保留一个迁移周期，只读兼容继续存在。

## 6. 实施优先级

推荐顺序：

1. Task 0 建立真实内容质量基线，同时明确默认路线与 strict/legacy 分流。
2. Task 3 叙事候选、两次 PLAN 写作和 Plan Critic 重写闭环。
3. Task 4 Deck Plan v2 lean 和上屏内容重写闭环。
4. Task 1 直接 Foundation authoring 与长材料分流。
5. Task 5 composed trace。
6. Task 2 图表传播语义。
7. Task 6 默认切换。

这个顺序先修复用户直接看到的内容质量，并用真实样本防止“增加规则即改善质量”的错误归因。Source Foundation 减重仍是确定方向，放在第一轮质量改造之后实施，降低同时修改上下游时的归因难度。

首个可交付里程碑由 Task 0 + Task 3 + Task 4 组成：用电力项目完成 Deck Plan 和上屏文字 before/after 盲评，交付真实叙事候选、更轻的逐页内容计划和可执行的重写闭环。第二个里程碑由 Task 1 组成：新项目从 source map 直接生成可审计 Foundation，旧全量链路只在 strict/legacy profile 运行。

## 7. 明确不做的事项

- 不复制参考仓库的完整 `skills/slide-maker` 目录。
- 不新增 `content-plan.md` 作为权威输入。
- 不新增 `.deck-gates.json`、checkpoint receipt、dispatch brief 或 review manifest。
- 不为默认 script profile 生成 `normalized-facts.json`、`concept-base.json`、`relation-graph.json`、`argument-chain.json`、`semantic-argument-model.json` 或 `source-truth.json`。
- 不删除 strict/legacy 兼容代码；先停止默认调用，完成真实项目对照后再评估长期维护范围。
- 不再安装或推荐 `markitdown[all]`。
- 不为偶发格式把 Azure、音频、YouTube、Outlook 等 extras 放入默认环境。
- 不把 `extract_pdf.py` 的 PyMuPDF 依赖放进首版核心运行时。
- 不要求常规脚本必须由第二个 Agent 审稿。
- 不将 Claim Ledger 扩展为每句文本的登记制度。
- 不在本轮融合中重写 Stage 02 图像生成与 PPTX 装配。

## 8. 主要风险与控制

| 风险 | 控制 |
|---|---|
| 轻量 Foundation 漏掉后续页面需要的事实 | 保留完整标题树和 source units；Foundation 覆盖核心/支持论点、数字、责任、状态、条件、边界和图表，PLAN 可按 source refs 回读局部原文 |
| 默认路线和 strict 路线产生语义差异 | 两条路线共享同一 Foundation schema、source refs 和下游 audits；用同一批材料做 Foundation/Plan/Final Script 对照测试 |
| 移除 MarkItDown 默认调用后少数复杂文件解析退化 | 原始文件始终保留；直接提取稀疏或失败时按格式启用 MarkItDown extra，并在 source index 记录 converter 和 warning |
| strict/legacy 代码长期形成维护负担 | 首阶段仅降级路由并冻结功能；收集实际 strict 使用率后再决定保留期限，不在本轮直接删除 |
| long 模式因选区错误遗漏关键论点 | 全量结构映射、每节 disposition、选区与交流目标合并确认、mapped 内容不得支撑强事实 |
| long 模式裁剪了 `8726f23e` 保留的来源论点链 | 完整构建 `document_thesis` 和 `argument_method` 后再分配阅读层级；mapped 节点保留结构责任，页面判断只使用 deep-read 证据 |
| 新实现无意中继承 `f6a3745` 的失败假设 | 开发和测试均以 `8726f23e` 和参考仓库固定 commit 为依据；`f6a3745` 仅作反例 fixture，差异增量逐项移除、替换或独立复验 |
| 多候选退化成同一讲法换名字 | 四轴差异检查、证据量 strawman 检查、落选理由必填 |
| Critic 只重复 Skill 规则，没有改善文案 | 强制输出重写结果，用真实项目 before/after 盲评验收；定向测试只作回归底线 |
| 压缩字数导致关键语义丢失 | 先完成页面论证，再在命题/证据两类单元中选择；密度与关键事实召回同时验收 |
| 弱 Plan message 被 proposition drift 审计锁定 | AUTHOR 评审失败时回到 PLAN 重写并重新确认；审计继续阻止未批准漂移 |
| 叙事候选覆盖来源主论点或论证顺序 | 所有候选共享只读 `source_thesis/source_argument_method`，仅允许改变受众问题、强调节点和页面角色 |
| lean 合同削弱来源约束 | 保留 source refs、论点绑定、数字/标识符硬检查；省略型和推断型内容保留例外合同 |
| 新旧 schema 同时存在造成分支复杂 | 只以 `plan_contract_version` 分支，禁止另建新文件格式和新目录 |
| 图表语义依赖模型判断 | locator 与 source refs 机械校验，carrying element 进入人工 Plan review |
| 未跟踪真实项目被测试或迁移脚本触碰 | 测试只使用临时目录和 fixtures，保留 `projects/power-data-infrastructure-standard-system-research-20260828-003/` |

## 9. 最终验收定义

融合完成后，一份典型正式材料应呈现以下体验：

- 短材料通过 source map 和一次 Foundation authoring 直接进入规划。
- 长材料先展示规模、章节取舍和深读范围，用户能够及时修正选区。
- 常规脚本项目不再生成四份 business-semantic 权威、semantic model 和 Source Truth。
- Foundation 本身即可人工审核全文主旨、论点结构、关键事实、边界和来源引用。
- 复杂汇报能看到 2–3 个有实质差异的叙事候选和明确选择理由。
- 每页计划一眼可读：为何需要这页、回答什么、希望听众记住什么、由什么证据建立、主动舍弃什么、如何推进到下一页。
- 上屏文字能在无讲解时传达主判断和证据关系，高密度页经过候选比较和整页重写。
- 作者无需填写视觉生产和逐原子事实处置的大量机械字段。
- 成稿审计把注意力集中到来源外数字、标识符、关键改写、高潮页和图表误读风险。
- 默认流程沿用 CyberPPT 的项目目录、source index、Foundation、Deck Plan、Final Script 和 Stage 02 消费链；strict/legacy 流程继续兼容 Source Truth 投影。
- 机器审计通过代表可追溯、合同和边界底线通过；内容质量通过由真实样本盲评和定性 Critic 的重写结果共同证明。
