# 源材料忠实策略与业务关系无损贯通设计

## 一、建设目标

本批次对 CyberPPT 从 Source Material Foundation 提纲成果到 GPT Image 2 送图提示词的主数据链进行加固，解决两个根本问题：

1. 已在提纲工作包中确定的政府公文式写作、源标题锁定、源顺序锁定和源内容保留策略，在适配、脚本、视觉设计和送图阶段缺少连续传递；
2. 语义层已经识别的业务关系在 `cyberppt-handoff` 中被统一改写为 `contains`，后续又被压缩为一句关系摘要，导致最终提示词虽然具备九段式结构，但没有完整使用前期关系数据。

本批次完成后，默认主链应符合以下原则：源材料和经审定的提纲是内容权威；下游只进行确定性投影和视觉实现，不重新规划标题、顺序、事实强度或业务关系。

## 二、实施范围

### （一）源材料忠实策略贯通

`ppt-outline-planning` 已产生的 `planning_policy` 继续作为权威策略，不再在下游重新判断。`cyberppt-handoff` 将下列字段原样投影至 `cyberppt.outline.v2`：

- `writing_style_mode`
- `source_structure_mode`
- `source_title_mode`
- `source_order_mode`
- `source_content_mode`
- `capacity_split_allowed`
- `duplicate_content_merge_allowed`
- `reframing_requires_explicit_user_request`
- `agenda_mode`

内容页同时保留 `source_heading_ids`、`primary_source_heading_id` 和已经审定的 `subtitle_policy`。适配器不得生成新标题、副标题或章节名称；源结构锁定模式下，没有上游副标题就继续保持无副标题。

Stage 01 → Stage 02 handoff 在根级继续携带同一 `planning_policy`，在页面级携带源标题归属。Stage 02 和 PageArtifactSpec 只消费这些字段形成约束，不改变其值。

### （二）结构化业务关系贯通

以 `page-plan.json.evidence.relation_ids` 为页面关系选择权威，以 `relation-graph.json` 和 `concept-base.json` 为关系语义权威。每一项页面业务关系使用以下结构：

```json
{
  "subject": "项目建设",
  "relation": "has_goal",
  "objects": ["统一服务入口"],
  "direction": "subject_to_objects",
  "condition": "",
  "modality": "",
  "basis": "explicit",
  "confidence": "high",
  "source_refs": ["ST0002"],
  "authority_ref": "rel-0001"
}
```

字段处理规则如下：

1. `subject` 和 `objects` 使用概念库中的正式名称；不得使用页面标题代替业务主体；
2. `relation` 原样保留关系图谱中的 `relation_type`；不得统一改写为 `contains`、`supports` 或其他通用关系；
3. `basis`、`confidence`、`condition`、`modality` 等有值字段原样保留；源数据没有的字段保持空值，不进行推断；
4. `source_refs` 只能映射该页已经获得授权的规范事实，不得通过关系引用扩大页面事实范围；
5. `authority_ref` 只用于审计和跨层一致性检查，不得进入 ImageGen 提示词。

对没有 `relation_ids` 的页面，适配器输出空业务关系列表，不再以“页面标题包含若干论证句”伪造业务关系。下游可以根据页面核心判断选择无显式连接线的视觉表达，但不得把构图顺序当作来源业务关系。

### （三）视觉结构层的职责分离

Stage 02 视觉结构规格同时保留两类信息：

- `semantic_graph.business_relationships`：从 Stage 01 无损继承的业务关系，属于内容权威；
- `connectors`：Stage 02 为实现阅读路径选择的视觉连接线，属于构图决策。

两者不得相互替代。视觉连接线可以根据所选载体和阅读方向调整，但 `type`、`label` 或空间顺序不得反向覆盖 `business_relationships`。现有 `decision_relationship` 可继续作为供人工审阅的一句摘要，但不再是 PageArtifactSpec 的唯一关系来源。

### （四）GPT Image 2 九段式提示词对接

`PageArtifactSpec.relationships` 从字符串元组升级为结构化 `RelationshipSpec`。结构化对象进入第四段 `Evidence & relationships` 时，按以下顺序稳定渲染：

1. 主体；
2. 关系类型；
3. 客体；
4. 条件、情态、依据和置信度等存在值。

提示词不得包含 `rel-*`、`ST*`、`NF-*`、页面文字 ID 或其他后台标识。第四段负责告诉模型“对象之间是什么关系”，第六段 `Composition` 继续负责告诉模型“这些关系如何在画面中组织”，避免内容关系和视觉连接线混为一体。

源结构锁定模式在第九段形成明确硬约束：不得改变经审定的标题归属、对象、关系、条件、状态和事实强度；但标题和副标题仍由 PPT 外部文字层渲染，不进入正文图像。

## 三、数据流与权威边界

主数据链调整为：

```text
outline-workpack.planning_policy
           ↓ 原样写入
deck-brief / page-plan
           ↓ 确定性投影
cyberppt.outline.v2
           ↓ 原样交接
stage02-handoff.json
           ↓ 内容关系与构图决策分离
deck-visual-spec.json
           ↓ 交叉校验
PageArtifactSpec
           ↓ 稳定序列化
GPT Image 2 九段式提示词
```

各层权威划分如下：

- 源标题、顺序、内容和事实强度：源材料、工作包和经验证提纲；
- 页面关系选择：`page-plan.json.evidence.relation_ids`；
- 关系语义：`relation-graph.json` 与 `concept-base.json`；
- 页面可见正文：经审计的 `generation_handoff.required_text`；
- 视觉载体、空间组织和连接线：Stage 02 视觉设计结果；
- 视觉风格：不可变 Style lock；
- 最终提示词：上述权威数据的确定性序列化结果，不是新的内容权威。

## 四、校验与错误处理

新增以下阻断性校验：

1. 页面声明的 `relation_ids` 在关系图谱中不存在；
2. 关系引用的概念在概念库中不存在或没有正式名称；
3. 关系映射使用了该页授权事实之外的 `source_refs`；
4. `cyberppt.outline.v2`、Stage 02 handoff 和视觉结构规格之间的结构化关系发生增删或字段漂移；
5. PageArtifactSpec 中的业务关系与 handoff 权威关系不一致；
6. 最终提示词出现后台 ID、未经授权的对象或关系。

旧项目兼容规则：没有 `planning_policy` 的既有 Outline 仍可进入原流程；没有结构化业务关系的既有视觉规格可读取原 `decision_relationship`，但新主链和新增端到端测试不得再使用该兼容路径。

## 五、测试方案

### （一）单元测试

- 验证 handoff 按 `relation_ids` 投影正式概念名称和原始关系类型；
- 验证无关系页不再生成 `contains`；
- 验证策略、源标题归属和副标题策略逐层保持一致；
- 验证视觉规格同时保留业务关系和构图连接线；
- 验证 PageArtifactSpec 拒绝关系漂移；
- 验证提示词稳定输出结构化关系且不包含后台 ID。

### （二）中文政企端到端回归样例

在现有 Source Foundation 中文样例基础上，覆盖以下链路：

```text
关系图谱 + 概念库 + 页面计划
→ cyberppt.outline.v2
→ Stage 02 handoff 页面输入
→ deck-visual-spec 页面
→ PageArtifactSpec
→ 九段式提示词
```

样例至少断言：

- 页面标题和顺序未变化；
- 默认策略仍为政府公文式和源结构锁定；
- `has_goal` 等正式业务关系没有被改写为 `contains`；
- 条件、依据和事实强度没有升级；
- 可见正文与审核结果完全一致；
- 九个提示词段落顺序固定；
- 提示词无后台 ID；
- 对同一组输入重复编译得到相同文本和相同 SHA-256。

## 六、本批次不实施事项

为控制回归风险，本批次不处理以下事项：

- 删除或归档旧双图、模板重建和兼容代码；
- 清理 Git 历史、运行产物、临时文件和大体积资产；
- 拆分 `script_quality_contract.py` 等大型模块；
- 一次性修复全部历史测试、依赖和 CI；
- 修改 Style09、Style10 的具体视觉内容；
- 新增审批文件、状态文件、哈希确认文件或平行运行目录。

上述事项在本批次主数据链稳定并通过回归后，分别进入后续开发批次。

## 七、验收标准

1. `planning_policy` 从经验证提纲连续传递至 Stage 02，默认政府公文式和源结构锁定语义不丢失；
2. 标题、顺序、源标题归属和上游副标题决策保持原样，下游不重新命名；
3. 页面业务关系来自页面已选择的关系 ID，并保留正式主体、关系、客体、条件、依据和置信度；
4. 无显式关系的页面不再伪造 `contains`；
5. Stage 02 业务关系与视觉连接线职责分离；
6. PageArtifactSpec 和九段式提示词使用结构化业务关系，不依赖单句关系摘要；
7. 中文政企端到端样例和相关主链回归测试全部通过；
8. 主分支不受开发过程影响，所有修改保留在独立分支中。
