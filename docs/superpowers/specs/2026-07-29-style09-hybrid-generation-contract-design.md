# Style 09 混合生成合同改造方案

日期：2026-07-29  
状态：**已确认设计，待实现**  
适用范围：`cyberppt` 脚本解析、ImageGen 提示词编译、模板文字锁与 editable-overlay 重建链。  

---

## 1. 问题与目标

当前内容页以 `视觉结构` 描述业务关系，以 `上屏文字` 同时承担生成图中的可见文字与最终 PPT 的完整正文。编译器会把全文作为页面语义送入 ImageGen，但没有稳定的版式母题、场景角色或跨页变化约束。

这会带来两个问题：

1. 同一风格下，模型容易反复采用“上部关系区 + 中部工作场景 + 右侧结论区 + 底部支撑区”的安全构图；
2. 长正文、数字、边界和条件进入生成图后，字体偏小、中文不可控，且与 editable-overlay 的文字能力重复。

本期目标是在不改变既有内容、证据、边界和页面关系合同的前提下：

1. 将 Style 09 的统一审美与页面构图变化分离；Style 09 只锁定优雅、沉稳、正式的政企气质，不锁定单一版式；
2. 将生成图的短标签与最终 PPT 的完整可编辑正文分离；
3. 为旧脚本提供确定性默认值，不要求一次性重写项目脚本；
4. 让现有 editable-overlay 路径可消费完整正文，而不是要求 ImageGen 承担全部中文正文。

非目标：不引入服务、数据库、全局编排系统或新的项目生命周期；不更改证据审计、页面主判断和现有生产模式。

---

## 2. 合同模型

内容页新增三个可选字段：

```text
- 版式母题：<layout_motif>
- 场景角色：<scene_role>
- 生图锁定文字：<image_locked_text>
```

字段均可省略。省略时由编译器从现有 `视觉结构`、页面关系、文字密度和本批次已选母题推导建议值；它不是固定模板映射。

### 2.0 Style 09 不变项与可变项

| 类别 | 不变项 | 可变项 |
|---|---|---|
| 气质 | 优雅、沉稳、克制、正式、业务清晰 | 页面叙事方式与视觉重心 |
| 视觉语言 | 象牙白、深蓝、浅灰细线、适度纵深、现代中文无衬线字 | 场景是否出现、场景面积、信息区位置 |
| 信息品质 | 中高密度、层级清楚、关系可读、无装饰性图标堆砌 | 分层、边界、景观、流程、证据或闭环表达 |
| 内容纪律 | 关键判断、条件、边界不可丢失 | 哪些信息由生成图承载，哪些由 editable-overlay 承载 |

默认 Style 09 样张与“能力框架”页面都是合格表达之一：前者偏“工作场景 + 流程与发布闭环”，后者偏“分层支撑 + 局部行业场景”。二者均不得被固化为全套页面的唯一版式。

### 2.1 版式母题

允许值：

| 值 | 用途 |
|---|---|
| `control_room_bridge` | 场景为主、关系标注嵌入；适用于运营闭环、预警、协同发布。 |
| `evidence_landscape` | 行业景观或空间剖面托举证据；适用于现状、环境、范围收敛。 |
| `decision_canvas` | 判断和边界为主，场景仅为证据；适用于定位、原则、范围、准入。 |
| `process_atlas` | 证据或任务链贯穿页面；适用于研究任务、实施路线、生产闭环。 |
| `layered_system` | 纵深分层与支撑关系为主；适用于能力框架、治理、平台支撑。 |

编译器先按页面关系提供**候选母题**，再从本批次已选母题中避开相邻重复：

| 既有页面关系 | 优先候选 |
|---|---|
| `boundary_guardrail`、`decision_admission`、`comparison` | `decision_canvas`、`evidence_landscape` |
| `hierarchy_support`、`capability_relationship` | `layered_system`、`control_room_bridge` |
| `phase`、`causal` | `process_atlas`、`evidence_landscape` |
| `closed_loop`、`scenario_application` | `control_room_bridge`、`process_atlas` |
| `judgment_evidence`、`multi_semantic_foundation` | `evidence_landscape`、`decision_canvas` |

当一批页面共同编译时，选择器不得让相同母题连续出现；在任意连续四页中，`primary_scene` 最多出现两次。显式 `版式母题` 与 `场景角色` 永远优先于自动建议。单页编译则只输出首选候选与其理由，不伪造跨页上下文。

### 2.2 场景角色

| 值 | 含义 |
|---|---|
| `primary_scene` | 行业场景是主视觉，但不遮挡正文。 |
| `supporting_evidence` | 场景只作为低饱和证据或空间底图。 |
| `no_scene` | 使用结构、材料、文档、数据或抽象空间关系，不强制工作场景。 |

默认值由“页面需要何种现实锚点”决定，而非由母题强制决定。`control_room_bridge` 通常优先 `primary_scene`；`evidence_landscape` 通常优先 `supporting_evidence`；`decision_canvas` 与 `process_atlas` 默认 `no_scene`。所有母题都允许显式覆盖，且不得因为 Style 09 而强制加入控制室、人物或行业实景。

### 2.3 文字分层

`上屏文字`继续是业务表达和 editable-overlay 的权威来源。新增 `生图锁定文字`仅决定须由 ImageGen 逐字呈现的短标签。

若未给出 `生图锁定文字`，编译器默认选择：

1. 已锁定的上屏结论（仅在 `locked` 模式）；
2. 模块标题；
3. 含数字、单位或专有名词的短行。

自动选择后仍超过 7 项、任一项超过 14 个汉字、或总长度超过 84 个汉字时，进入“正文可编辑优先”模式：只保留模块标题和不可替代的数字/单位，其他内容明确写入 editable-overlay 正文合同。

---

## 3. 生成链路变更

```text
final script
  -> ScriptPage（新增可选字段）
  -> visual intent + batch-aware layout motif resolver
  -> ImageGen prompt
       - 页面关系与完整语义：用于理解
       - 版式母题与场景角色：用于内容驱动的构图变化
       - 生图锁定文字：短标签逐字呈现
       - 可编辑正文：明确不要求在生成图中渲染
  -> template_text_lock
       - 标题、短标签、完整上屏正文、文字分层策略
  -> editable-overlay rebuild
       - 完整正文作为原生可编辑文字呈现
```

`content-first-v1` 保留“完整页面内容用于视觉叙事”的要求，但删除“全文均应由生成图可见文字表达”的隐性目标。完整语义仍可通过关系、场景、结构和可编辑正文共同表达。

---

## 4. 代码边界

主要修改：

1. `cyberppt/script_quality_contract.py`
   - 扩展 `ScriptPage` 与 Markdown 解析；
   - 保持旧脚本字段和质量检查兼容。
2. `scripts/dual_image_overlay/imagegen_handoff.py`
   - 增加带批次去重的母题/场景角色解析和文字分层选择；
   - 在 `render_content_first_prompt()` 中生成明确的构图约束与文字承载边界；
   - 在提示词元数据记录实际决策。
3. `scripts/dual_image_overlay/creative_brief.py`
   - 将母题和场景角色纳入创意简报；
   - 保留“业务关系优先于固定布局”的原则。
4. `cyberppt/commands/final_script_pages.py`
   - 将完整可编辑正文和分层元数据写入 `template_text_lock`。
5. 测试
   - 扩展 `test_imagegen_creative_brief.py`、`test_imagegen_no_visual_structure.py`、`test_final_script_pages.py`；
   - 新增旧脚本兼容、默认路由、手动覆盖、文字阈值、模板锁记录测试。

不修改：项目台本内容、历史项目工件、默认生产模式、图像后端、证据与边界审计逻辑。

---

## 5. 验收标准

1. 不含新增字段的脚本可按原路径解析、编译和通过现有测试；
2. 相同 Style 09 下，定位/框架/范围/任务链可获得不同且可追溯的版式母题，但不把任一母题设为全局固定模板；
3. 长上屏正文不再被要求逐字画入 ImageGen 图，完整正文仍被写入模板文字锁；
4. 数字、单位、显式锁定短标签不会从生成提示或 editable-overlay 合同中丢失；
5. 现有 prompt diagnostics 不再报告 editable text 与位图文字的语义冲突；
6. 一批连续页面不会出现相同母题相邻重复，且四页内不超过两页使用主工作场景；
7. 聚焦测试与全量相关测试通过。
