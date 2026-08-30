# Stage 01 Authority Map

本文件定义 CyberPPT Stage 01 的内容权威边界。目标是让 Agent、CLI、审计器和维护者对“哪个产物可以写、哪个产物只是投影、发生冲突时以谁为准”使用同一套规则。

## 1. 核心原则

Stage 01 只允许四层可写内容 authority：

1. `Source Evidence`：原始来源及其确定性抽取结果。
2. `SemanticIR`：对来源的业务语义理解。
3. `DeckPlanIR`：汇报结构和页面边界。
4. `FinalScriptIR`：最终页面内容合同。

除这四层外的 Source Truth、Outline、review、report、receipt、audit、projection、cache 和 handoff 文件均为派生产物，不得成为第二套可写内容权威。

## 2. Authority 层级

| 层级 | 逻辑 Authority | 正式产物 | 谁可以写 | 下游可以做什么 |
|---|---|---|---|---|
| Source Evidence | 来源原文与确定性来源索引 | 原始文件、source map/source units、结构与事实抽取 | extractor / source-foundation | 引用、定位、验证；不得改写来源事实 |
| SemanticIR | 来源语义的唯一解释层 | strict/legacy：`normalized-facts.json`、`concept-base.json`、`relation-graph.json`、`argument-chain.json` 组成一个逻辑 SemanticIR；script：`script/foundation.json` 直接承载轻量 SemanticIR | UNDERSTAND | 归并、解释、保留冲突和边界；不得写页面文案 |
| FoundationIR | PLAN/AUTHOR 的统一语义入口 | `script/foundation.json` | strict/legacy 仅由机械 projection 写入；script profile 由 UNDERSTAND 一次写入 | PLAN/AUTHOR 读取；不得反向修改 SemanticIR |
| DeckPlanIR | 汇报结构权威 | `script/deck-plan.json` | PLAN | 决定受众、交流目标、章节、页序、页面使命和 source 范围；不得提前成为最终页面表达 |
| FinalScriptIR | 页面内容权威 | `script/dist/final-script.md`；存在 JSON 镜像时 JSON 仅作为同内容机器表示并必须 `check-sync` | AUTHOR / CRITIQUE / REWRITE | Stage 02 唯一跨阶段业务输入 |

说明：FoundationIR 是 SemanticIR 到脚本写作的稳定接口，因此在运行链上单列；它不能成为 strict/legacy 的第二套独立语义作者空间。

## 3. strict/legacy profile

### 3.1 可写权威

strict/legacy 的业务语义由以下四个文件共同组成一个逻辑 `SemanticIR`：

- `normalized-facts.json`：来源事实、状态、数字、责任、条件及其 evidence coordinates。
- `concept-base.json`：业务对象、概念、定义、别名和边界。
- `relation-graph.json`：对象关系及 `basis: source | inferred | external`。
- `argument-chain.json`：document thesis、document semantics、source chain、reconstructed chain 和 diagnostics。

四个文件按字段职责分区，不允许同一语义字段在多个文件中独立维护相互竞争的版本。

### 3.2 机械 projection

以下文件如被 strict/legacy 兼容链生成，均属于 derived projection：

- `semantic-argument-model.json`
- `source-truth.json`
- `outline.json`
- 其他为旧消费者生成的 handoff/projection 文件

规则：

1. projection 可以改 ID、字段形状和消费者所需的数据布局。
2. projection 不得新建事实、关系、责任、状态、数字或结论。
3. projection 不得反向覆盖 SemanticIR。
4. 维护者不得通过手工编辑 projection 修复语义问题；必须回到对应 SemanticIR authority 修复并重新投影。
5. `project-foundation` 即使消费 `source-truth.json` 作为机械运输格式，也只能把已经验证的语义搬入 `script/foundation.json`，不得重新分析。

## 4. script lightweight profile

轻量 profile 不建立 strict/legacy 的四文件 SemanticIR，也不创建第二套 Source Truth authority。

正式链：

`source-index/source units → UNDERSTAND → script/foundation.json → DeckPlanIR → FinalScriptIR`

其中：

- `script/.cache/source-index.json` 是来源派生索引，不是语义作者空间。
- `script/foundation.json` 是一次 UNDERSTAND 后的统一 SemanticIR/FoundationIR。
- 后续 PLAN/AUTHOR 不得重新建立全文语义模型。

## 5. 冲突处理顺序

发生内容冲突时按以下顺序处理：

### 来源事实冲突

回到 Source Evidence 和 SemanticIR。Final Script、Deck Plan、Source Truth 或 Outline 不能覆盖来源证据。

### strict SemanticIR 内部冲突

按字段所有权处理：

- 事实与 evidence coordinates → `normalized-facts.json`
- 概念定义和别名 → `concept-base.json`
- 关系和 basis → `relation-graph.json`
- thesis / argument order / diagnostics → `argument-chain.json`

如果冲突跨字段，必须在 UNDERSTAND 阶段统一修复后重新验证，不允许在 projection 中选一个“方便的版本”。

### Foundation 与 strict SemanticIR 冲突

strict/legacy 以已验证 SemanticIR 为准，重新运行机械 projection。

### Deck Plan 与 Foundation 冲突

以 Foundation 的来源边界和事实强度为准，修改 Deck Plan。

### Final Script 与 Foundation/Deck Plan 冲突

以 Foundation 的证据边界和 Deck Plan 的页面职责为约束，重写 Final Script。

### Stage 02 与 Final Script 冲突

Final Script 是业务内容 authority。Stage 02 可以派生视觉结构、空间拓扑和渲染决策，但不得修改页面事实、结论力度、责任和边界。

## 6. 文件分类标签

新代码和新文档引用 Stage 01 产物时，统一使用以下术语：

- `authority`：可以直接修复内容的权威产物。
- `projection`：从 authority 机械生成的消费者格式。
- `receipt`：运行或 QA 回执，只记录发生了什么。
- `review`：面向人工阅读的派生展示。
- `cache`：可删除重建的性能或检索产物。
- `snapshot`：冻结的输入字节副本，不改变其内容 authority 身份。

禁止继续使用含糊的“canonical artifact”“source truth authority”“semantic authority”等词而不注明所属层级和 profile。

## 7. 跨阶段边界

Stage 02 只接收 `FinalScriptIR` 文件快照：

`FinalScriptIR → Stage 02 input snapshot → VisualBuildIR → DeliveryIR`

Stage 02 不读取 Stage 01 的 SemanticIR、FoundationIR、DeckPlanIR、Source Truth、Outline 或 approval 状态来补充业务含义。

## 8. 迁移规则

历史项目不要求一次性删除旧 projection。迁移时执行：

1. 标记其 `authority = false` 或在文档/代码中明确其 derived 身份。
2. 新功能不得新增对 projection 的反向写入。
3. 新审计器优先直接验证 authority 与其直接消费者，避免形成“projection 再审计 projection”的链式权威。
4. 历史兼容代码只允许单向适配到当前 authority model。

该 Authority Map 是 Stage 01 权威命名的统一入口；具体操作步骤仍由 `docs/CYBERPPT_WORKFLOW.md` 和对应 Skill 定义。
