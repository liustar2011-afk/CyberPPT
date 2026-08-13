# 输出合同

## 目录

- 输出文件
- Markdown合同
- JSON合同
- 内容锁定
- 生图执行摘要
- 文件命名

## 输出文件

默认输出三份文件：

1. `*_视觉结构设计.md`
2. `*_视觉结构设计.json`
3. `*_视觉结构校验.json`

Markdown用于人工预审和生图脚本组装，JSON用于自动校验、批处理和后续执行器。

## Markdown合同

文档开头必须包含：

```markdown
# <项目名称>视觉结构设计脚本

## 整套视觉设计总则
### 汇报对象与使用场景
### 整套核心叙事
### 内容锁定范围
### 视觉签名
### 整套节奏与页面差异化
### 全局禁止事项
```

每页固定包含以下章节，顺序不可改变：

```markdown
## 第N页｜<页面标题>

### 页面角色
### 页面使命
### 核心结论
### 内容锁定
### 证据单元与语义关系
### 视觉意图
### 页面草图
### 页面构图
### 实景锚点与图文融合
### 元素与空间关系
### 箭头与连接关系
### 标题与文字渲染
### 终稿文字
### 生图执行摘要
### 禁止事项
```

### 视觉意图章节

必须写明：

- 视觉意图类型。
- 视觉主张。
- 决策关系。
- 语义焦点及其类型。
- 空间语法。
- 主结构与次级结构所引用的语义节点。
- P0证据的文字归属。
- 阅读路径。

旧版“主视觉载体、单一视觉中心”字段仅用于读取`1.0`合同，不作为`1.1`结构真值。

### 页面草图

使用简洁ASCII草图说明主区域、主链和视觉中心。草图用于结构理解，不追求像素级坐标。

### 页面构图

可使用百分比或1280×720参考坐标。必须说明：

- 内容区边界。
- 主视觉载体位置和占比。
- 核心结论、证据、结果和辅助说明的从属关系。
- 非对称权重和留白方向。

### 终稿文字

写出完整可上屏文字。禁止“略、同上、沿用前页、参考原文”等占位。

## JSON合同

整套JSON顶层字段：

- `schema_version`
- `deck_id`
- `deck_title`
- `deck_context`
- `global_profile`
- `content_lock`
- `pages`
- `deck_rhythm`
- `capacity_suggestions`
- `qa_summary`

每页字段：

- `page_id`
- `page_number`
- `page_title`
- `page_role`
- `page_mission`
- `core_judgment`
- `content_lock`
- `evidence_units`
- `semantic_graph`
- `structural_decision`
- `visual_decision`
- `text_integration`
- `geometry`
- `image_plan`
- `expression_contract`
- `connectors`
- `final_text`
- `generation_handoff`
- `avoid`
- `qa`

具体类型以`assets/page-visual-spec.schema.json`和`assets/deck-visual-spec.schema.json`为准。

CyberPPT工作台候选的`expression_fit`必须包含：

```json
{
  "form": "framework_4",
  "constraint_status": "default_profile",
  "satisfied_constraints": ["four_peer_nodes", "peer_balance"],
  "reading_relation": "four parallel capability groups are read as peers",
  "balance_strategy": "comparable prominence and text capacity",
  "changed_constraints": [],
  "deviation_reason": ""
}
```

`deck-visual-spec.json`的`expression_contract`只保留选择追溯：`form`、`constraints_sha256`、`selected_candidate_id`、`fit_status`、`reading_relation`、`balance_strategy`与`deviation_reason`。它不得包含候选的内部证据解释、提示词或任何固定布局指令。

`schema_version: 1.1`必须包含`structural_decision`：

- `semantic_focus`：引用语义图中的实体、动作、状态、关系或结果。
- `spatial_grammar`：描述关系如何空间化，不指定具体媒介。
- `semantic_tags`：记录可组合的次级语义标签。
- `primary_refs`与`secondary_refs`：形成唯一主结构和从属关系。
- `reading_sequence`：使用语义图节点ID记录阅读顺序。
- `text_bindings`：将证据单元绑定到语义节点；CyberPPT工作台模式还必须用`text_ids`逐项引用`locked_text_items`中的精确正文ID。所有正文ID必须被绑定且只能出现一次，不得引用未知ID。
- `representation_freedom`：记录载体和媒介是否受来源约束。

`representation_freedom`只记录上游是否限制选择，并不把选择责任交给生图模型。Stage02必须在`image_plan`和`visual_decision`中选定可执行方案：

- `image_plan.business_object`必须是本页选定的、承载关系的具体业务对象或关系场；不得写页面标题、抽象概念、`语义节点/动作/关系`、`可选媒介`等渲染占位语。
- `visual_hierarchy.primary`必须与该对象或关系场一致，并能说明为何它承载核心结论。
- `spatial_organization`与`relationship_encoding`必须说清对象、动作、接口、边界或结果如何构成主关系，不能只写`path`、`主链`、`聚焦`等关系标签。
- `text_integration_method`必须说明每组正文贴附到哪个对象、动作、接口、边界或结果；“逐项绑定语义节点”不是可执行设计。
- 选择`use_scene: false`时，仍须用具体业务对象及其关系构成图义场；选择场景时，场景必须直接解释该关系，不能作为装饰背景。

## 内容锁定

`content_lock`必须明确：

- `mode`：`strict`、`semantic`或`open`。
- `locked_items`：原始终稿文字和来源。
- `allowed_transformations`：允许的换行、分组或不改义压缩。
- `forbidden_transformations`：禁止修改的数字、状态、主体和边界。

已有逐页脚本默认`strict`。

## 生图执行摘要

`generation_handoff`至少包含：

- `structural_guidance`：引用`structural_decision`并只补充结构性约束。
- `required_text`
- `required_text_ids`：CyberPPT工作台模式必填，顺序必须与`required_text`和`final_text`完全一致。
- `style_source_ref`：指向唯一权威风格来源，不复制风格正文。
- `title_exclusion_instruction`

`schema_version: 1.0`仍可读取`composition_guidance`、`style_guidance`和`negative_constraints`，但这些字段已废弃。`1.1`不得再出现这些字段。

CyberPPT工作台的`visual-design-input.json`使用以下权威边界：

- `business_relationships`：业务关系真值；`decision_relationship`只能由此继承和组织。
- `stage01_relationship_features`：Stage 01已经识别的主体、动作、方向、条件、分支与反馈；必须逐项核对并在最终结构中落位，或明确说明调整、舍弃理由。
- `author_visual_notes`：低权重作者备注，固定版式和载体描述不得进入关系真值。
- `locked_text_items`：带稳定`text_id`的正文唯一来源。

工作台中Skill只要求生成`visual-design-decisions.json`，保存每页至少三个结构候选、候选完整证据覆盖、评分维度与总分、选中候选、输入哈希，以及`stage01_visual_note_disposition`。`trace_refs`仅用于审计追溯，执行器可将其写为证据单元的`source_ref`，但提示词构建器不得读取它。仓库`execute-visual-structure`唯一生成规格JSON和Markdown；正式执行回执由仓库命令生成并绑定执行器、模型、Skill包、决策回执和编译产物哈希。编译产物的`qa`与`qa_summary`初始为`draft`且未评分，实际审计结果以`validation-report.json`为准。

结构指令不得在画面中显示。标题与副标题默认由外部PPT文字层处理，正文按用户指定的生图模式执行。字体、字号、颜色、线条、边框、形状、人物外观和媒介质感由`style_source_ref`对应的风格文件负责。

## 文件命名

- 整套：`<原文件名>_视觉结构设计.md/.json`
- 单页：`<原文件名>_第N页_视觉结构设计.md/.json`
- 修复：`<原文件名>_第N页_视觉修复.md/.json`
- 校验：对应主文件名后加`_校验.json`
