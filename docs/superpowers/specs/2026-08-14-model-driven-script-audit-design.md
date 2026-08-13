# 模型驱动的页面脚本审计设计

## 目标

让 Stage 01 页面脚本审计理解作者在权威 Outline 中选定的语义表达模型，区分“必须逐字锁定的结论”和“可在来源边界内压缩的可见判断”，从而既避免机械锚点比对，也不削弱来源忠实、关系强度、状态和边界约束。

本设计仅覆盖 `script-audit`、其输入契约和 P04/P05 的局部修订；不进入 Stage 02、视觉生成、PPTX 或重新运行上游语义理解、Source Truth 编译和 Outline 候选编译。

## 问题与根因

当前审计将以下两种场景混为一类：

1. Outline 已锁定 `onscreen_conclusion` 的页面，脚本必须展示同一结论；
2. Outline 只有作者 `core_message` 的页面，脚本可以把该判断压缩为受众可读的上屏结论。

因此第二种场景被报为 `SCRIPT_JUDGMENT_INTRODUCED`。同时，`ONSCREEN_CONTENT_UNIT_GAP` 只以锚点子串是否出现作判断，无法识别 SCQA 等模型已把相同来源事项压缩、重组为可读模块的情况。`NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC` 也不知道某个“缺口”是模型的论证证据，而不是页面的最终主张。

## 非目标

- 不根据页面类型、标题关键词或 Source Truth 顺序自动猜测表达模型。
- 不允许模型生成来源没有支持的新事实、因果、状态、优先级或承诺。
- 不取消字面锚点校验；未选择模型的页面仍使用现有锚点规则。
- 不放宽 P05 的边界引用、完整稿段落映射和 Stage 01 视觉结构边界。
- 不把表达模型作为受众上屏文字或 Stage 02 图形指令。

## 契约设计

### 1. 可见判断模式

内容页可在权威 Outline 使用 `onscreen_judgment_mode`：

| 值 | 含义 | 脚本审计行为 |
|---|---|---|
| `locked` | 已批准结论是严格展示契约 | 脚本 `上屏结论` 必须逐字等于 `onscreen_conclusion` 或 `onscreen_judgment` |
| `semantic_alignment` | 核心判断需要展示，但允许作者在来源边界内压缩 | 脚本必须有 `上屏结论`，并与 `core_message` 达到现有语义相似度下限；不得触发“新增判断” |
| `hidden` | 当前页关系模块已完整表达判断，或判断不宜单独展示 | 脚本不得出现独立 `上屏结论` |

兼容规则：已有 `onscreen_conclusion` 或 `onscreen_judgment` 的页面默认为 `locked`；未声明模式且无锁定判断的遗留页面维持当前行为，即不强制结论，也不允许新增独立结论。新作者页面只有在明确设为 `semantic_alignment` 后，才能展示压缩结论。

### 2. 模型化上屏内容单元覆盖

仅当 `expression_model_selection.fit == "selected"` 且模型存在于 `references/semantic-expression-models.md` 时启用模型化校验。

- 审计读取 `source_mapping` 中的槽位、来源引用和 `implicit` 标记。
- 非隐含槽位的每一组来源引用，必须至少由一个上屏模块或上屏结论承担；证明方法为：来源单元的业务特征与可见文字存在足够语义重叠，或该单元既有锚点出现在可见文字中。
- `implicit: true` 的槽位不要求以原文事实逐字上屏，但其 `statement` 若展示，必须保留为问题、归纳或待解事项，不能被写成来源直接断言。
- 对模型选中并通过槽位覆盖的来源单元，不再叠加 `ONSCREEN_CONTENT_UNIT_GAP` 的逐锚点失败；对没有进入模型槽位的必要内容单元，保留原有锚点校验。
- 模型不改变 `full_prose_required` 的完整稿覆盖校验。

### 3. 缺口证据的前景化规则

当选定模型的槽位包含 `complication`、`problem`、`gap` 或等价的问题证据时：

- 该槽位可出现在上屏的证据模块中；
- 页面标题、上屏结论、完整稿首段、演讲者备注首段和视觉结构的阅读出口，仍不得把问题、缺口或边界作为最终主张；
- 审计应检查页面的回答/落点槽位（如 SCQA 的 `answer`）是否进入上屏或核心模块。未出现时，问题页仍失败；
- 没有选定表达模型的页面继续使用现有负面前景化规则。

这使 P04 可呈现供给断点，但以“统一的连接、可信使用和服务运营基础”形成正向收束。

### 4. 不上屏模型字段

`compile-page-script-authoring` 已产生 `### 表达模型（不上屏）`。该字段继续只从 Outline 的 `expression_model_selection` 派生：显示模型名、匹配理由、槽位映射、隐含推导说明；不得由页面作者在脚本中自行声明另一套模型。

`script_quality_contract.parse_script_markdown` 将忽略该字段对上屏文本、模块、视觉结构和来源消费的影响，使其成为可审阅的作者上下文而非受众内容。

## 实现边界与文件职责

| 文件 | 变更职责 |
|---|---|
| `cyberppt/script_quality_contract.py` | 解析判断模式、选择锁定/语义对齐/隐藏三种结论校验；新增模型槽位可见覆盖；修正模型页的缺口证据前景化规则 |
| `cyberppt/semantic_expression_models.py` | 提供模型槽位名称和隐含许可的只读访问；不引入关键词自动选模 |
| `cyberppt/stage01_compiler.py` | 仅在必要时补充权威 Outline 的默认 `onscreen_judgment_mode`；不得改写作者选择 |
| `tests/test_script_quality_contract.py` | 覆盖三种判断模式、SCQA 槽位覆盖、隐含问题限制、缺口证据与回答收束 |
| `tests/test_stage01_compiler.py` | 覆盖作者显式模式的保留与遗留默认兼容 |
| 当前项目 `outline.json` | P04 标记 `semantic_alignment`；P05 标记 `semantic_alignment` 并将 ST0015 明确为 `boundary_refs` |
| 当前项目 `workbench/scripts/drafts/c1.md` | 改稿以满足边界依据、段落合并理由、非版式化视觉结构和模型语义审计 |
| `.agents/skills/cyberppt-write-single-page/SKILL.md` | 将不存在的 `script-audit --lightweight` 示例改为实际 CLI 入口 |

## P04/P05 验收表达

### P04 建设背景

- 模型：SCQA，模式：`semantic_alignment`。
- S 为行业基础与政策路径，C 为运行经营协同需求与分散资源供给断点，Q 为已标明的隐含问题，A 为统一连接、可信使用和服务运营基础。
- 可见结论以 A 收束；C 仅为支撑模块。
- 模型化槽位校验通过后，不再要求所有原始锚点逐字出现在上屏。

### P05 总体定位

- 模式：`semantic_alignment`；保持 `source_native`，不强行套用模型。
- ST0015 同时作为页面边界依据，脚本的“边界依据”字段与 Outline 一致。
- 完整稿段落映射中，对 ST0010/ST0011、ST0012/ST0013 的合并分别写明共同论证职责与保留结论；也可拆为独立段落。
- 视觉结构只写业务节点、关系、阅读方向和出口，不写左右、上下、底部、栏位或容器。

## 验收与回归

1. 针对新增逻辑先写失败测试，再实现最小代码。
2. 运行：

   ```bash
   PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py tests/test_stage01_compiler.py tests/test_compile_page_script_authoring.py
   ```

3. 修改当前项目 P04/P05 后运行：

   ```bash
   PYTHONPATH=. python3 -m cyberppt script-audit projects/power-data-infrastructure-cooperation-v16-20260813 --input projects/power-data-infrastructure-cooperation-v16-20260813/workbench/scripts/drafts/c1.md
   ```

4. 通过标准：P04/P05 没有 `rewrite_required` 级错误；无来源漂移、关系升级、状态升级、边界引用错误、完整稿段落映射错误或 Stage 01 固定版式错误。
5. 运行 `git diff --check` 和 `npx --no-install graft build && npx --no-install graft check`。

## 风险与防护

- 风险：语义相似度阈值被用于掩盖新判断。防护：只允许 `semantic_alignment`，且必须有明确的作者模式与页面 `core_message`；继续执行来源强度和关系审计。
- 风险：模型槽位映射错配来源。防护：复用 Outline 审计中“槽位引用必须是当前页 Source Truth 子集”的约束；脚本审计只消费已审计的映射。
- 风险：模型变成通用模板。防护：未选模型时完全保持现有规则；模型库仅提供候选与槽位，选择和映射必须由作者显式完成。
