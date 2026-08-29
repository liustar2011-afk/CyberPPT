---
name: ppt-visual-structure-designer
description: 将PPT原始内容、逐页脚本或既有页面方案转化为可执行的通用视觉结构规格与整页生图结构交接。用于页面使命判断、核心结论提炼、语义关系建模、语义焦点选择、空间语法设计、图文归属、页面构图重构、单页修复、整套视觉节奏设计和视觉脚本质量审查。适用于“设计PPT脚本的视觉结构”“重构页面构图”“解决图是图文字是文字”“按内容决定页面怎么画”“形成Codex生图脚本”等任务；不预设行业、媒介或具体载体，不直接生成图片、HTML、SVG或PPTX。
---

# PPT视觉结构设计

把内容脚本转换为可审查、可校验、可交给整页生图或后续PPT执行器的视觉结构规格。先判断页面表达任务，再决定视觉结构；禁止从模板、卡片数量或图标库反推内容。

## 职责边界

执行以下工作：

- 完整读取整套材料、逐页脚本、上下页关系和用户锁定约束。
- 识别整套汇报目的、受众、叙事主线和每页页面使命。
- 提取页面核心判断、证据单元、业务主体、业务关系和约束边界。
- 将业务关系转换为空间关系、阅读路径、视觉层级和连接关系。
- 为每页选择视觉意图类型、语义焦点、空间语法、图文归属和结构退化禁项。
- 在CyberPPT工作台模式只输出候选决策回执；仓库执行器负责生成Markdown视觉脚本和机读JSON视觉规格。
- 不在工作台模式生成生图提示模块；正式审计器在当前合同通过后重建该模块。
- 为决策回执运行所需的确定性自检，仓库审计器负责最终结构规格校验。

禁止执行以下工作：

- 不直接调用图像生成工具。
- 不直接生成HTML、SVG、PPTX或页面图片。
- 不擅自改变事实、数字、单位、专有名词、主体关系和政策口径。
- 不默认拆页、并页、改页序或减少上屏文字。
- 不把复杂关系降级为等权卡片墙、图标阵列或装饰性左右分栏。
- 不用预设行业对象、媒介或载体名词代替结构决策，也不建立具体载体黑名单。
- 不在结构层规定颜色、字体、边框、箭头外观、材质或其他风格实现细节。
- 不默认推荐双图法或三图法；优先优化单次整页生成的构图稳定性。
- 不得把来自不同根模块（一级模块）的锁定正文合并进同一个证据单元；跨根合并会被 Stage 2 编译器拒绝。
- 不得让完全由细节行组成、不包含其根模块正文的证据单元成为本页语义焦点（`semantic_focus`/唯一 `judgment` 节点）；细节行升格为页面结果或判断会被 Stage 2 编译器拒绝。

## 任务模式

按输入状态选择模式：

| 模式 | 适用输入 | 主要输出 |
|---|---|---|
| `deck-design` | 完整材料、提纲或逐页内容 | 整套视觉总则、逐页视觉规格、整套节奏检查 |
| `script-redesign` | 已有PPT生图脚本 | 保留终稿文字和业务关系，重做页面视觉结构 |
| `page-design` | 单页内容或单页脚本 | 单页视觉规格和生图执行摘要 |
| `page-repair` | 页面效果差、图文分离、卡片化、图标化 | 缺陷诊断、结构重构、替换后的完整页面脚本 |
| `visual-audit` | 已完成的视觉脚本或JSON规格 | 闸门结果、风险项、修复后的规格 |
| `workbench-handoff` | `ppt-script`已验证项目 | 继承Source Truth和页面合同，输出`visual/`阶段产物 |

缺少非关键背景时，结合材料和默认配置作出可逆假设并标注；不得因可推断信息中断任务。只有完全缺失页面内容时才说明无法设计。

## 资源读取规则

所有任务先读取以下文件：

- `references/semantic-model.md`：建立页面使命、证据单元和语义图。
- `references/visual-intent-router.md`：按语义关系选择视觉意图，不按版式名称选择。
- `references/output-contract.md`：严格使用固定输出合同。
- `references/quality-gates.md`：执行阻断式质量闸门。

按需读取：

- 设计空间结构时读取 `references/composition-grammar.md`。
- 使用实景图、彩色插图或行业场景时读取 `references/scene-and-image-integration.md`。
- 生成整页生图提示模块时读取 `references/prompt-assembly.md`。
- 政企、央企、中电联和领导汇报默认读取 `references/cec-government-enterprise-profile.md`。
- 输入来自既有`ppt-script`工作台时读取 `references/ppt-script-integration.md`。
- 需要参考完整案例时读取 `references/examples.md`。
- 页面的`expression_constraints.reading_requirement`为`parallel`（`key_points_3`、`framework_4`），或上游 Outline 已把本页匹配到某个论证模型时，读取仓库根目录 `references/semantic-expression-models.md`：该模型的`forbidden_inferences`（例如`pyramid_principle`的"不得把并列事实提升为结论"）同样约束本阶段的视觉关系编码，不得在视觉设计阶段重新引入论证阶段已经排除的因果或先后关系。

机器可用资源：

- `assets/default-profile-cec.yaml`：可选的中电联政企外部风格配置示例，不属于通用结构合同。
- `assets/visual-intent-registry.yaml`：视觉意图机器注册表。
- `assets/page-visual-spec.schema.json`：单页JSON合同。
- `assets/region-graph.schema.json`：Region Graph语义空间合同；记录区域角色、锚点、相对权重与区域关系，不记录像素模板。
- `assets/visual-medium-policy.schema.json`：独立视觉媒介合同；媒介选择与relationship topology分离。
- `assets/deck-visual-spec.schema.json`：整套JSON合同。
- `assets/page-visual-spec-template.md`：Markdown输出模板。
- `assets/domain-neutral-structure-fixtures.json`：六类跨领域通用结构回归夹具。
- `scripts/test_domain_neutral_fixtures.py`：验证正例、故障变体和外部风格切换不改变结构。

## 工作流程

### 1. 锁定内容与约束

先建立内容锁定清单：

- 标题、终稿文字、数据、单位、日期、主体和专有名词。
- 必须保留的业务流、数据流、控制流、责任关系和边界条件。
- 允许调整的换行、分组、标注位置、表达媒介和空间顺序。
- 外部风格文件、标题渲染方式、公共模板元素和项目禁用项的引用关系。

用户本轮明确要求优先于项目配置；项目配置优先于默认配置。

### 2. 建立整套设计上下文

识别：

- 汇报主题、受众、决策目标和使用场景。
- 章节逻辑、页间承接、页面密度和视觉节奏。
- 整套材料需要持续出现的业务主链、主体角色和视觉签名。
- 封面、章节页、判断页、关系页、架构页、路径页和收束页的职能差异。

先读整套，再设计单页。处理单页时也应读取相邻页；相邻页不可用时，明确采用独立页模式。

### 3. 建立页级语义模型

每页必须确定：

- 页面角色。
- 页面使命。
- 核心结论。
- 证据单元及优先级。
- 实体、关系、方向、状态和边界。
- 关系核对：在CyberPPT工作台中，`visual-design-input.json.business_relationships`是唯一权威关系来源；`stage01_relationship_features`显式保留上游已识别的主体、动作、方向、条件、分支与反馈，必须逐项核对；`author_visual_notes`始终为`advisory_only`。不得从作者备注中的行列、泳道、卡片数量、中心位置、上下左右分区或具体载体反推业务关系，也不得把这些内容继承到`decision_relationship`。其他调用方式必须提供同等结构化的实体、动作、方向、状态、结果和边界；若关系缺失、存在歧义，或锁定文字与关系相互矛盾，应退回上游补齐。

不得把原文项目符号数量直接等同于视觉模块数量。

一个证据单元合并了多条锁定正文（`text_ids`长度大于1）时，必须在该证据单元中写明`grouping_reason`（这些正文为何共同构成同一个业务节点，不能写"合并"这类空话）和`loss_risk`（`low`/`medium`/`high`）。不同主体、不同阶段、不同责任、不同权利边界或不同结果类型的正文不得在没有明确理由的情况下合并；`loss_risk`为`high`的合并需要在交付前得到人工确认，仓库审计器会拦截缺失理由或未确认的高风险合并。合并前必须先确认这些`text_ids`在`visual-design-input.json.content_integrity.nodes`中的`root_id`一致——`content_integrity`是内容结构的权威来源，跨根模块（不同`root_id`）的合并会被 Stage 2 编译器直接拒绝，不受`grouping_reason`/`loss_risk`豁免。每条锁定正文都必须有明确去向：独立成为一个证据单元、被合并进某个证据单元且登记合并理由，或在`stage01_visual_note_disposition`中说明为何不进入视觉结构。

### 4. 生成并比较构图候选

候选数量按页面关系是否存在争议决定，不强制每页都写三个：

- 页面的业务关系类型（并列/主从/顺序/因果/收敛……）从内容本身和 `expression_constraints.reading_requirement` 就能唯一确定、没有第二种合理读法时，写 1 个候选即可，不需要为凑数量而编造结构上并不成立的备选方案。
- 关系类型本身存在争议或多种合理读法时（例如"这组内容到底是并列还是有主从/因果关系"——这正是本项目实际出现过判断错误的地方），必须生成 2–3 个结构上真正不同的候选，写清每个候选各自成立的理由，再选出最贴合来源的一个。
- 不管写几个候选，凡是写出来的候选都必须结构上真正不同（改变语义焦点、空间语法或阅读路径），不能只更换媒介、载体名称、颜色或模块顺序；未选候选要给出具体的 `rejection_rationale`，不能用"得分更低"这类空话。**候选数量本身不是质量信号，候选是否解决了真实的关系判断分歧才是。**

工作台输入给出`expression_constraints`时，每个候选还必须写入`expression_fit`：保留收到的`form`，说明满足的中性结构约束、阅读关系与信息均衡策略。`constraint_status`只能为`default_profile`或`adapted`；默认档案的`changed_constraints`与`deviation_reason`必须为空，适配档案必须列出改动项并说明业务理由及保留的表达核心。表达档案约束关系与阅读，不得推导为卡片、列、箭头、循环、金字塔或矩阵等固定视觉模板。`expression_constraints.reading_requirement`是权威边界，不是候选参考：为`parallel`时，任何候选都不得把`semantic_focus.kind`设为`outcome`并指向某一并列证据组（仓库审计器`CANDIDATE_PARALLEL_FORM_FALSE_OUTCOME`会拦截这类候选）——正确做法见`references/visual-intent-router.md`的`coordinate_peer_set`。

`visual_medium_policy`可由候选显式声明，包含`preferred / allowed / scene_policy / rationale`；媒介依据页面使命、可画业务对象、业务动作、信息密度和Style lock选择，不得仅因`parallel_set`、`flow`、`convergence`等topology直接决定实景、插图或关系图。

每个候选还必须写入候选自身的`visual_thesis`和`selection_rationale`：`visual_thesis`必须说明画面要证明的对象关系，不能复用页面核心结论充当占位；`selection_rationale`包含页面使命适配说明，以及由`single_focus`、`text_capacity`、`relation_clarity`、`composition_stability`、`anti_pattern_risk`五项组成的可生成性评分；每项为0–20整数，五项之和形成0–100的可生成性总分；`score`必须等于五项实际得分之和，并列出风险。未选候选必须写入相对已选方案的具体`rejection_rationale`，说明焦点、关系、容量或阅读上的实际劣势；不得只写“得分更低”“不够美观”“一般”或“不适合”。

每页必须写入`relationship_coverage`，逐项登记`business_relationships`与`stage01_relationship_features.actions`中的关键关系，标记为`primary`、`secondary`或有业务理由的`not_rendered`，并引用当前证据单元和锁定文字ID。页面使命、核心判断或P0证据所必需的关系不得标记为`not_rendered`。

每个候选还必须声明`topology`，取值必须是以下九种之一：`parallel_set`（并列）、`causal_convergence`（多路证据汇聚成一个判断）、`layered_architecture`（分层依赖）、`directed_flow`（有向流程）、`lifecycle_loop`（含回流的生命周期）、`governance_boundary`（边界与管控）、`ecosystem_map`（多方生态关系）、`allocation_flow`（角色到价值去向的分配）、`conclusion_anchor`（收束到单一结论）。`topology`必须与该候选自己的`spatial_grammar`、`reading_sequence`和证据间关系一致——例如声明`lifecycle_loop`就必须存在回流的关系边，声明`causal_convergence`就必须有至少两路证据汇入同一焦点；不得只为了候选比较而随意标注，仓库编译器和审计器会据此校验（缺失或与实际关系边不符会被拒绝，见`references/output-contract.md`）。语义图的`nodes`、`edges`、`focus_node`和`forbidden_structures`由仓库编译器从候选与证据单元推导生成，本Skill不需要、也不应在决策JSON中手写这些字段。

按以下权重比较：

- 页面使命匹配度：25。
- 业务关系保真度：20。
- 单一视觉中心：15。
- 阅读路径清晰度：15。
- 图文融合度：10。
- 整页生图稳定性：10。
- 与整套节奏的差异化：5。

只输出最高分方案。用户明确要求备选时，再输出候选及取舍。

### 5. 形成视觉结构决策

为每页给出：

- `visual_intent_type`。
- `visual_thesis`。
- `decision_relationship`（继承第3步核对的上游关系，不独立创设）。
- `semantic_focus`。
- `focus_policy`：取 `single_anchor`、`paired_focus`、`peer_field`、`distributed_focus` 或 `sequence_focus`；它描述整页视觉重心组织方式，不等同于某个固定版式。未显式声明时由仓库编译器按 topology 生成兼容默认值。
- `spatial_grammar`。
- `primary_refs`与`secondary_refs`。
- `text_bindings`：除证据与语义节点外，还要用`text_ids`显式引用精确锁定正文；不复制证据解释文字替代锁定正文。
- `representation_freedom`。
- `dominant_visual_carrier`仅作为旧合同兼容字段，不作为语义真值。
- `industry_scene_anchor`仅在页面明确选择实景媒介时使用。
- `spatial_organization`。
- `reading_path`。
- `text_integration_method`。
- `relationship_encoding`。
- `visual_hierarchy`。
- `avoid_on_this_page`。

当页面`prompt_mode`为`semantic_brief`时，本阶段锁定语义焦点、来源支持的关系边界、证据分组、精确文字绑定和由`focus_policy`约束的宏观关系场；编译器写入`scene_policy: auto`，使业务场景、对象插图或结构表达继续由页面语义和Style lock共同判断。ImageGen保留区域内部的对象细节、镜头、光影与微观摆位自由。当页面`prompt_mode`为`directed_composition`时，本阶段进一步选定承载主关系的业务对象或关系场，并写清对象如何通过动作、接口、边界或结果形成画面。

语义焦点必须承载核心结论，辅助关系不得形成第二套主结构。`decision_relationship`只写业务实体、动作、方向、状态和结果，不写页面几何或阅读版式。具体载体和媒介由内容、外部风格与最终执行器共同决定。

### 6. 输出双合同

默认同时输出：

- `<原文件名>_视觉结构设计.md`：人工预审和直接组装生图脚本。
- `<原文件名>_视觉结构设计.json`：机器校验和后续自动化。
- `<原文件名>_视觉结构校验.json`：校验结果。

CyberPPT工作台模式只输出`visual/visual-design-decisions.json`，schema固定为`cyberppt.visual_design_decisions.v3`，保留每页按"生成并比较构图候选"一节规则确定数量的候选（无争议页 1 个，有争议页 2–3 个）、每项候选自己的`visual_thesis`、完整证据覆盖、候选评分维度、`selection_rationale`、未选候选的`rejection_rationale`、`relationship_coverage`、选中候选、`expression_fit`及输入哈希。`semantic_brief`页的`execution_design`可省略；编译器仅生成不进入正式Prompt的兼容字段。`directed_composition`页必须提供完整`execution_design`，写明`business_object`、`visual_focus`、`semantic_role`、`scene_policy`、`scene_type`、`text_integration_method`、`spatial_organization`和`relationship_encoding`。`scene_policy`只允许`required`、`allowed`、`forbidden`、`auto`；`use_scene`仅作为旧项目兼容字段。每页必须包含`stage01_visual_note_disposition`，分别记录`inherited`、`adjusted`、`rejected`的上游视觉特征及专业理由；不得用一句“已参考”代替逐项处置。`trace_refs`仅用于审计追溯，不得进入结构提示或上屏文字。随后由仓库`execute-visual-structure`命令唯一生成`deck-visual-spec.json`与`script-visual-structure.md`，并由仓库命令记录执行器、模型、Skill包和编译产物哈希；仅生成调用说明不视为执行完成。

只处理单页时，可输出单页Markdown和单页JSON。

### 7. 生成生图执行模块

运行：

```bash
python3 scripts/build_generation_prompt.py <视觉规格.json> --output <生图提示.md>
```

该脚本只为独立Skill调用或旧项目生成结构预览，不是CyberPPT正式生产提示词。结构预览必须先给结构指令，再给上屏文字和外部风格来源引用；字段名和指令文字不得成为画面文字。结构模块本身不得复制风格规则。

在CyberPPT工作台模式中，`visual-structure-audit`重建的`generation-prompts.md`仅用于结构预览和兼容诊断；不得把它追加、替换或提升为正式ImageGen prompt。正式提示词由仓库`artifact-spec-v2`编译器从已审计的Stage 02 handoff、`deck-visual-spec.json`和style lock投影为`FinalPromptIR v2`。`semantic_brief`不消费具体载体、场景和空间方案；`directed_composition`消费完整执行设计。审批、canonical和manifest链路复用同一编译结果。

### 8. 校验并修复

运行：

```bash
python3 scripts/validate_visual_spec.py <视觉结构设计.md> --strict
python3 scripts/validate_visual_spec.py <视觉结构设计.json> --strict
```

出现错误必须修正并复跑。警告项逐项判断，不得机械忽略。

## 默认结构约束

未提供项目配置时只采用以下结构约束；颜色、字体、线条、边框、形状、人物、媒介质感和其他表现规则由外部风格文件决定：

- 16:9，参考画布1280×720。
- 标题和副标题默认由PPT文字层处理，整页生图不绘制标题区文字。
- 每页保持一种主关系和一个整体主结构；视觉重心数量由 `focus_policy` 决定。`single_anchor` 保持单一锚点，`peer_field` 保持同权节点共同主表达，不得人为制造唯一结果或最大节点。
- 每个P0证据必须归属于语义节点、关系、状态或结果。
- 连接只记录起点、终点、方向和业务含义，不规定外观。
- 场景、图表、图形或对象均为可选媒介，不设默认优先级。

## 失败判定

出现任一项即判定失败：

- 只有文案改写，没有视觉结构决策。
- 使用“左文右图、简洁现代、科技感”等空泛描述替代构图。
- 一条文字对应一个图标、一项内容对应一张图或等权卡片墙。
- 页面存在两个及以上相互竞争的视觉中心。
- 文字、图像或图形与业务逻辑没有空间或语义连接。
- `decision_relationship`复制上游的泳道、矩阵、行列、方位、中心框或收束条等固定版式配方。
- 主结构之外另设第二套流程、结果链、总结链或独立解释区。
- 用不在语义图中的抽象中心、通用枢纽或装饰性中心框替代真实业务关系。
- 文字区和图形/场景区各自完整表达同一内容，删除视觉部分后业务逻辑不受影响。
- 核心结论与语义焦点不一致。
- 结构决策只有载体名称，没有焦点、关系、层级和文字归属。
- 结构字段混入颜色、字体、边框或箭头外观等风格实现要求。
- 业务流、数据流、控制流和责任关系被混淆。
- 终稿文字使用“略、同上、沿用前页”等占位表达。
- 出现`overlay`字段或依赖跨页文字才能独立生成。
- 连续三页使用同一视觉意图和近似空间骨架且没有叙事理由。
- 未运行校验即交付。
