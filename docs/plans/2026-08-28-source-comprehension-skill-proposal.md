# 材料理解自检方案（在 business-semantic-understanding 内部改造）

> 修订说明 v4：按用户反馈精简。这是单人单机小工具，不是多人协作或对外交付的审计系统，因此：
> 1. 去掉版权引用的硬性字数限制（不涉及版权风险场景）；
> 2. 大幅降低来源追溯的严格度——追溯的唯一目的是"防止源材料在后续写作脚本时丢失"，不是做可审计的证据链。凡是不服务这个目的的强制字段、强制校验、强制反例，本版一律去掉或改成建议性质。

## 结论

独立技术判断：`SUPPORT`。

v3 版本的设计思路（四类 `basis`、`counter_case`、五字段 `citation`、`validate.py` 硬阻断）是按"可审计、可复现"的标准设计的，那套标准适用于多人协作或需要对外证明结论可靠性的系统。用户已经说明这是单人单机小工具，唯一诉求是"别把源材料和推断/外部信息混在一起，导致后面写脚本时分不清哪句话是材料原文"。按这个更小的目标重新设计，能砍掉大部分强制校验，只保留一个轻量标签。

一点保留意见：完全不留痕迹是不行的——这正是用户最初抱怨的"机械映射"问题的反面（无痕迹的自由发挥 = 又一种失真，只是方向相反）。所以最小值仍然是"每条非原文内容打一个标签"，这个不能再削。

## 设计：在 `business-semantic-understanding` 内新增一道轻量 Pass

不新建 Skill，不新建目录结构。在现有 Skill 的 Workflow 里插入一步，产出一个新文件放进同一个语义目录：

```
<semantic-dir>/
  semantic-workpack.json   （已有）
  chunks/                  （已有）
  comprehension-brief.json （新增，轻量）
  normalized-facts.json    （已有）
  concept-base.json        （已有）
  relation-graph.json      （已有）
  argument-chain.json      （已有）
  semantic-report.json     （已有）
```

### Pass 0 — 整体理解（轻量版）

1. 通读全篇，写一段 `overview`（自由文本）：这份材料在说什么、写给谁看、要解决什么问题。不要求逐节复述、不要求 100% 覆盖 outline——只在遇到"这段到底在说什么我拿不准"的地方才单独写一条，其余段落默认已读懂，不必逐条留痕。
2. 拿不准/讲不通/证据不足的地方，写进 `open_questions`（自由文本列表，不再要求 `blocking`/`related_section_ids` 结构化字段，就是一句话说清楚疑问是什么、大致在哪一节）。
3. 需要用行业常识或联网核实来理解材料时，直接用，用完在 `external_notes` 里补一条：说了什么、（如果查了网）大致来源是什么。不强制要求 URL、访问时间、可信度说明——这些字段留空也可以，能写就写，没有不算不合规。

Pass 1（现有的逐 section/chunk 抽取）保持原样，唯一变化：正式产出（`normalized-facts.json`/`relation-graph.json`/`concept-base.json`/`argument-chain.json`）里，**任何不是直接来自源材料原文的内容，`basis` 必须标注**，取值三选一：

- `source`——源材料原文写出的内容（原 `explicit`，改名更直观）。
- `inferred`——由源材料内部证据推出的判断，写一句 `why`（原 `inference_rationale`，字段名简化）即可，不要求反例。
- `external`——依赖源材料之外的信息（不管是模型自带常识还是联网查的），写一句 `why` 说明依据是什么；能标来源就标（URL 或"行业常识"之类的说明都行），不强制结构化引用。

三类原来的四类合并为三类：`domain_knowledge` 和 `external_verified` 合并为 `external`，因为对单人工具而言，"是不是来自材料本身"是唯一要紧的区分，"外部信息具体是常识还是网页"没必要再分——真要细究可以直接在 `why` 里写清楚，不需要单独的 schema 字段。

### 输出：`comprehension-brief.json`（轻量 Schema）

```json
{
  "overview": "自由文本：材料是什么、写给谁看、要解决什么问题",
  "open_questions": [
    "自由文本：哪里讲不通/证据不足/拿不准，大致在哪一节"
  ],
  "external_notes": [
    "自由文本：用了什么行业常识或查了什么信息来理解材料，来源写多细随意"
  ]
}
```

不再要求 `schema_version`、`artifact_type`、哈希字段、`section_comprehension` 覆盖率。这份文件是给人（或下一步的自己）看的笔记，不参与哈希链校验，也不作为验证器的强制输入——`business-semantic-understanding` 现有的 `validate.py` 不需要为它新增检查项，写不写、写多细，不影响 `semantic-report.json` 能否 `ok`。

### `basis: external` 在正式产物里怎么写

不新增 schema 结构，直接复用 `relation-graph.json`/`normalized-facts.json` 现有的 `basis` 字段，多一个可选值：

```json
{ "basis": "external", "why": "行业惯例通常按季度结算，材料没写但常见做法如此" }
```

或：

```json
{ "basis": "external", "why": "查了对方官网，2025年报显示该数字量级一致", "source": "https://..." }
```

`source` 字段可选，写不写都行。

## 下游消费契约变更清单（本方案范围，尚未落地）

1. **`business-semantic-understanding/SKILL.md`**：
   - Workflow 加一句：通读全篇后，先写 `comprehension-brief.json`（自由笔记，覆盖 overview/open_questions/external_notes），再进入现有的逐 chunk 抽取。
   - 删除"不得浏览、检索外部资料"一条，替换为一句话：可以使用行业常识或联网核实辅助理解，但产出里凡不是源材料原文的内容，`basis` 标 `external` 并写一句 `why`。
   - 工具边界补一句：可调用 `WebSearch`/`WebFetch`（如环境提供）。

2. **`business-semantic-understanding/references/semantic-contract.md`**：
   - `basis` 由两类改为三类：`source`（原 `explicit`）、`inferred`、`external`。
   - `external` 类要求一句 `why`，`source` 字段可选。
   - 不新增 `counter_case`、不新增强制的 `open_question` 交叉引用检查。

3. **`business-semantic-understanding/scripts/validate.py`**：不改，或最多加一条最宽松的检查——`basis` 取值必须是 `source`/`inferred`/`external` 三者之一（防止拼写错误），不做其他新增门禁。

4. **`docs/CYBERPPT_WORKFLOW.md`**：语义理解一节补一句"可使用行业常识和联网核实辅助理解，非源材料内容需标注 `basis: external`"。不需要新增产物清单条目（`comprehension-brief.json` 是笔记性质，不算权威产物）。

这一版的改动量比 v3 小很多：一个字段改名、一个新枚举值、一份非强制的笔记文件。改完之后，写脚本时只要看一眼 `basis` 就知道这句话是不是材料原文，达到用户说的最小目的；不再有校验器阻断、不再有五字段引用、不再有反例要求。

## 关于版权引用限制

去掉硬性字数限制，按你的说明处理：这是单人单机小工具，产物不对外发布，不涉及版权风险。

但有一点需要说明清楚，不是这个仓库的规则问题，是我自己执行时的通用限制：当我（agent）在对话中直接向你复述从网页抓取的内容时，我自己仍然要遵守"不大段逐字复制"的通用限度——这条约束不是这个仓库能配置掉的项目规则，而是我在任何场合处理网页内容时的固定做法。但这只影响我在聊天里怎么转述给你看，不影响 `comprehension-brief.json`/`external_notes` 这类中间笔记文件本身要不要设字数上限——笔记文件不设限制，你可以随意保留任意长度的原文摘录，不会有人为设限。

## 风险（精简后仍需留意的两点）

- **`external` 类信息可能是错的或过时的**：不做验证、不强制留痕来源，出错了也难以事后排查。对单人工具而言这是可接受的取舍——你自己写的东西，自己知道哪里没底。
- **合并 `domain_knowledge`/`external_verified` 之后，丢失了"是否联网查证过"这个区分**：如果之后发现这个区分对你有用（比如想知道哪些结论没有查证过，风险更高），随时可以在 `why` 里用一个约定俗成的前缀（比如"联网核实："开头）来标记，不需要现在就改 schema。

## 落地状态

已实现，改动如下：

- [`SKILL.md`](../../.agents/skills/business-semantic-understanding/SKILL.md)：新增 Pass 0（`comprehension-brief.json`，非强制、不参与校验）；`Evidence and inference rules` 移除外部知识禁令，`basis` 改为 `source`/`inferred`/`external` 三选一说明。
- [`semantic-contract.md`](../../.agents/skills/business-semantic-understanding/references/semantic-contract.md)：规则 7 改为三类 `basis`；`Output files` 一节补充 `comprehension-brief.json` 的非权威说明。
- [`validate.py`](../../.agents/skills/business-semantic-understanding/business_semantic_understanding/validate.py)：`RELATION_BASIS` 改为 `{"source", "inferred", "external"}`；`inference_rationale` 校验扩展到 `external`；新增 `external` 关系的提示性 warning。
- [`prepare.py`](../../.agents/skills/business-semantic-understanding/business_semantic_understanding/prepare.py)：workpack/chunk 的 `semantic_policy.external_enrichment` 由 `forbidden` 改为 `allowed_with_basis_label`。
- [`cyberppt/source_foundation_projection.py`](../../cyberppt/source_foundation_projection.py)：**新发现的下游依赖**——Source Truth 投影和 `page_logic_contract.py` 的 `_VALID_BASES` 仍然只认 `explicit`/`inferred` 两个值。为避免新的 `source`/`external` 值undetected 破坏下游校验，在投影边界做了映射：`source→explicit`，`external→inferred`（`external` 不是源材料原文，按下游现有"非源文承诺"的语义最接近 `inferred`）。这不违反"投影层只搬字段、不建第二权威"的既有约束——语义层内部仍然是完整的三分类，只是投影到下游时收窄回两个下游已知的值。
- `docs/CYBERPPT_WORKFLOW.md`：语义理解一节补充可使用行业知识/联网核实及 `basis: external` 标注要求。
- 相关测试（`test_source_foundation_projection.py`、`test_business_semantic_fact_types.py`、`test_page_logic_contract.py`、`test_foundation_projection.py`、`test_stage01_compiler.py`）全部通过，未受影响。

未改动：`cyberppt/page_logic_contract.py` 的 `_VALID_BASES`（继续保持两值，因为投影层已经做了映射，下游不需要知道三分类）；未修改任何存量项目数据。
