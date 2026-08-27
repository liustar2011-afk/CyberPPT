# Stage 01 脚本到 Stage 02 送图 Prompt 链路诊断

## 一、诊断结论

技术判断：`SUPPORT WITH CONDITIONS`

支持修复 Stage 01 成果消费缺口，也支持降低 Stage 02 默认视觉设计复杂度。实施时需保留精确上屏文字、业务关系方向、并列与顺序边界、禁止结构、画布契约和风格锁。建议继续使用 `python -m cyberppt final-script-pages` 作为唯一正式入口，在现有 artifact-spec 链上升级，不切换到旁路编排。

当前链路同时存在两类问题：

1. **权威内容投影不完整**：Stage 01 正式脚本中的页面使命、主论证链和内容来源没有被 Markdown 解析器完整读取；完整文字稿虽然进入视觉设计输入，最终送图 Prompt 只接收其派生结果，缺少关键含义已被消费的确定性证明。
2. **视觉职责前置过多**：视觉结构阶段已经决定候选方案、语义焦点、拓扑、场景、业务载体、空间组织、阅读路径、主次焦点、文字贴附和连接方式。最终 Prompt 继续逐项发送这些决定，ImageGen 的主要自由度集中在表现细节。

因此，问题一属于真实接口缺陷，优先级为 P0；问题二属于职责边界偏重，优先级为 P1。两者应在同一轮架构调整中处理，避免只补字段后继续由复杂构图层放大错误。

## 二、正式生产链路

正式入口为：

```text
python -m cyberppt final-script-pages
```

当前内容链为：

```text
final-script.md
  → parse_script_markdown
  → stage02-handoff.json
  → visual-design-input.json
  → visual-design-decisions.json
  → deck-visual-spec.json
  → PageArtifactSpec
  → FinalPromptIR
  → ImageGen Prompt
```

正式 Prompt 编译器在 `cyberppt/commands/final_script_pages.py:730-850` 固定使用 `artifact-spec-v2`，核心投影位于 `cyberppt/page_artifact_spec.py:418-661`、`scripts/imagegen_pipeline/artifact_prompt.py:447-524` 和 `scripts/imagegen_pipeline/final_prompt_renderer.py:34-100`。

## 三、问题一：Stage 01 成果消费存在字段断层

### 3.1 当前项目实测

对当前 21 页正式脚本执行 `parse_script_path → _page_record(page, None)`，结果如下：

| 检查项 | 结果 |
|---|---:|
| 完整文字稿进入 handoff | 21/21 |
| 上屏文字进入 handoff | 21/21 |
| 演讲者备注进入 handoff | 21/21 |
| 业务关系进入 handoff | 21/21 |
| 页面使命等于核心结论 | 21/21 |
| source_refs 非空 | 0/21 |
| argument_role 非空 | 0/21 |
| consumed_content_unit_ids 非空 | 0/21 |
| must_not_include 非空 | 0/21 |

这说明链路并非完全没有消费 Stage 01，实际问题是“主要正文进入，规划边界和溯源字段丢失”。

### 3.2 页面使命丢失

Stage 01 正式 Markdown明确写出 `- 页面使命：...`。`parse_script_markdown` 构造 `ScriptPage` 时没有对应字段。`_page_record` 的页面使命取值顺序为：

```text
contract receipt.page_mission
→ outline.page_mission
→ page.main_message
```

`build_stage02_handoff` 又固定调用 `_page_record(page, None)`，当前正式脚本旁没有提供可用的逐页 contract receipt，最终 21 页全部退化为“页面使命等于核心结论”。这会把“本页要完成什么沟通任务”和“本页要表达什么判断”合并成一个字段。

### 3.3 内容来源丢失

Stage 01 正式 Markdown使用 `### 内容来源`，并写入 `SU-...` 来源单元。当前解析器的标题别名不包含“内容来源”，`source_refs` 只从“证据”和“边界依据”读取；来源正则只识别 `Sxxx` 或 `STxxx`。因此当前脚本 21 页的来源追踪全部为空。

来源编号不应进入可见画面，但必须保留在审计链和消费回执中，用于证明送图上下文来自正确页面材料。

### 3.4 主论证链和 Deck Plan 页面角色丢失

正式 Markdown写出了 `- 主论证链：...`，解析器没有对应字段；Deck Plan 使用 `page_role`、`argument_chain`、`source_refs`、`must_not_include` 等页面合同字段，handoff 构建阶段没有读取 Deck Plan，且 `_page_record` 接收的 outline 固定为空。

结果是 `argument_role`、`must_not_include`、`consumed_content_unit_ids` 均为空。Stage 02 随后主要依赖上屏文字和“视觉结构”段重新推断页面关系，削弱了 Stage 01 规划成果的权威性。

### 3.5 完整文字稿只产生间接影响

`visual-design-input.json` 将完整文字稿写入 `semantic_context`，视觉结构 Skill 可以阅读它；但 `PageArtifactSpec` 没有完整文字稿或等效语义摘要字段，`FinalPromptIR` 也不接收完整文字稿。最终 Prompt 消费的是 Stage 02 重新提炼的视觉论点、证据单元、关系、载体和构图决定。

这套设计可以控制 Prompt 长度，但缺少一项关键保证：完整文字稿中未进入上屏文字的业务对象、条件、边界或含义，是否已被 Stage 02 提炼并保留。现有测试还明确要求完整文字稿原文不进入紧凑送图脚本，因此当前行为具有设计意图，缺口集中在“消费证明”和“语义保真”，不能用简单拼接全文解决。

## 四、问题二：视觉结构层已成为第二套构图引擎

### 4.1 当前视觉结构阶段的决定范围

视觉结构 Skill 和编译器目前要求或生成：

- 一至三个候选方案及选择理由
- 证据单元、焦点节点和语义拓扑
- 视觉论点、视觉意图和空间语法
- 阅读顺序、方向和主次焦点
- 场景或非场景、场景类型和具体业务载体
- 文字贴附方式、空间组织和关系编码
- 视觉预算、辅助视觉数量和作用域
- 连接边、连接方向和连接标签

`PageArtifactSpec.CompositionSpec` 继续固化 `spatial_organization`、`reading_path`、`primary_focus`、`secondary_focus`、`relationship_encoding`、`text_integration_method`、`spatial_grammar`、`connectors` 和 `topology`。这些字段随后进入最终 Prompt。

这已经超过“告诉模型业务关系和禁止误读”的范围，形成一套先于 ImageGen 的页面构图方案。虽然没有固定像素坐标，模型仍然收到较完整的空间答案。

### 4.2 过度前置带来的风险

1. **错误放大**：上游页面使命或关系推断发生偏差后，场景、载体、拓扑、连接边会把偏差固化为执行指令。
2. **视觉同质化**：受控拓扑、焦点和空间语法反复出现，容易形成模板化关系图、卡片墙和机械箭头。
3. **模型能力闲置**：ImageGen 已具备结合业务语义和风格锁进行整体构图的能力，当前链路只给它留下材质、细节和局部表现选择。
4. **指令竞争**：页面级空间方案、Style 09/10 视觉系统和最终硬约束可能同时指导构图。现有实现已经为 Style 09/10 特判移除部分场景与辅助视觉预算，说明职责冲突在代码中真实存在。
5. **维护成本偏高**：候选、决策、可执行规格、artifact spec 和 final IR 多层表达同一视觉意图，任何字段升级都需要跨层同步。

### 4.3 不能删除的必要边界

以下信息仍应由确定性代码保留：

- 精确上屏文字及模块层级
- 页面使命、核心判断和非渲染语义上下文
- Stage 01 明示的主体、对象、动作、方向、条件和边界
- 并列、顺序、因果、反馈、层级等语义关系
- 禁止伪造流程、因果、中心枢纽和对等关系
- 标题外置、正文入图、画布尺寸和文字审计要求
- Style lock、禁止新增业务事实和禁止渲染后台字段

合理反例是具有真实先后顺序、因果链、反馈闭环或层级结构的页面。若完全撤掉关系约束，ImageGen 可能把并列事项画成流程，或把相关性画成因果。因此目标应为“轻构图、强语义边界”。

## 五、建议的职责边界

| 信息 | 默认责任方 | 最终 Prompt 策略 |
|---|---|---|
| 页面使命、核心判断 | Stage 01 | 非渲染语义上下文，必须进入 |
| 完整文字稿 | Stage 01 | 生成可追溯的非渲染语义摘要，不直接作为可见文字 |
| 上屏文字、模块层级 | Stage 01 | 精确锁定，逐项进入 |
| 来源编号、消费单元 | Stage 01 | 审计和回执保留，不进入画面提示正文 |
| 主体、对象、动作、条件、边界 | Stage 01 | 语义关系和禁止误读约束 |
| 并列、顺序、因果、反馈、层级 | Stage 01 + 确定性校验 | 只声明真实关系，不指定视觉形状 |
| 场景或非场景 | ImageGen 默认决定 | 特殊页面或重试时才锁定 |
| 具体视觉载体 | ImageGen 默认决定 | 可给业务对象候选，不给唯一答案 |
| 空间组织、阅读路径视觉实现 | ImageGen 默认决定 | 仅保留语义阅读关系 |
| 主次视觉焦点 | ImageGen 默认决定 | 只声明必须突出哪个业务结论 |
| 文字贴附方式 | ImageGen 默认决定 | 保留可读性和语义邻近要求 |
| 辅助视觉数量、连接表现 | ImageGen 默认决定 | 由风格锁和硬约束控制上限 |

## 六、建议的目标架构

建议形成轻量的 `artifact-spec-v3`，继续沿用正式入口和 manifest，不新增平行生产路径。

### 6.1 两级提示模式

**默认模式：semantic-brief**

面向绝大多数内容页，只发送：页面任务、核心判断、非渲染语义摘要、精确上屏文字、明示业务关系、关系边界、禁止结构、画布和风格锁。场景、载体、空间组织和视觉实现由 ImageGen 综合判断。

**升级模式：directed-composition**

仅在以下条件触发：

- 来源明确要求真实顺序、因果、反馈或层级
- 页面包含必须保持方向的复杂映射
- 同页首次生图经 QA 证明存在结构误读
- 人工明确指定构图

升级模式才允许发送 topology、reading path、primary focus、spatial organization、connectors 等强构图字段。触发原因必须记录在 manifest 或调试回执中。

这两个模式属于提示强度，不增加页面类型数量，能够避免分类器因类型过多而判断不稳。

### 6.2 Stage 01 消费回执

每页应建立确定性的消费映射：

```text
page_mission      → communication_goal
core_message      → page_judgment
full_prose        → semantic_brief + semantic_brief_source_hash
onscreen_text     → exact_visible_text
argument_chain    → semantic_relationship_boundary
source_refs       → audit_trace_only
must_not_include  → hard_constraints
speaker_notes     → delivery_only，默认不进入送图 Prompt
```

`semantic_brief` 应保留完整文字稿中的业务对象、关系、条件、范围和含义，禁止加入新事实。其消费校验应检查关键语义单元是否进入摘要、精确上屏文字、关系约束或排除边界中的至少一处。

## 七、建议的分阶段修复方案

### 第一阶段：修复权威字段投影（P0）

1. 扩展 canonical Markdown parser，读取页面使命、主论证链和内容来源。
2. 对 `SU-...` 来源单元采用独立、可扩展的 provenance 解析器；保留现有 `S/ST` Source Truth 解析兼容性。
3. 让 handoff 明确消费 Deck Plan 页面合同，或将 Deck Plan 必要字段在 Stage 01 渲染时形成稳定的逐页 contract receipt。两条方案中优先选择单一权威投影，避免 Markdown 与 Deck Plan 静默互相覆盖。
4. 禁止 `page_mission` 无提示退化为 `core_message`。兼容旧脚本时可降级并产生 warning，新正式脚本应阻塞。
5. 将 `argument_chain`、`page_role`、`must_not_include`、来源和消费单元写入 handoff，并补充来源追踪 QA。

### 第二阶段：建立完整文字稿消费证明（P0）

1. 在 handoff 到 artifact spec 之间增加 `semantic_brief` 和消费回执。
2. 完整文字稿保留为非渲染权威上下文；最终 Prompt 接收受控语义摘要，不复制来源编号和后台标签。
3. 审计“完整文字稿独有关键含义”是否已进入语义摘要、关系边界或精确上屏文字。
4. 演讲者备注保持交付用途，默认不参与构图，避免过渡语和讲解修辞污染画面。

### 第三阶段：降低默认构图强度（P1）

1. 将 `scene_type`、唯一 `business_object`、`spatial_organization`、`secondary_focus`、`text_integration_method`、`visual_budget` 和具体 connectors 改为默认可空或建议字段。
2. 默认 Prompt 渲染器不输出空缺的强构图章节，不用通用占位句补齐九段。
3. 只保留必须的语义关系、突出对象和禁止误读约束。
4. 为严格关系页和失败重试页保留 directed-composition 升级路径。
5. 保持 Style 09/10 作为视觉表面和总体语言的唯一风格权威。

### 第四阶段：清理重复权威（P1）

1. 候选比较改为按需执行；关系清晰页不再为了满足格式生成候选。
2. `visual-design-decisions`、`deck-visual-spec`、`PageArtifactSpec` 各自只保留一个职责，避免同一空间决定跨三层重复。
3. debug receipt 记录每个最终 Prompt 字段来自 Stage 01、Stage 02 确定性投影、人工指定或重试升级中的哪一类。

## 八、必须补充的回归测试

1. **真实 canonical roundtrip**：`render_stage02_markdown → parse_script_markdown → _page_record`，断言页面使命、主论证链、来源、角色、排除边界不丢失。
2. **独有语义哨兵测试**：完整文字稿加入一个未出现在上屏文字中的条件或业务含义，断言其进入非渲染语义摘要或明确记录为有意不消费。
3. **可见文字隔离测试**：来源编号、speaker notes、字段名和消费回执不得进入可见文字白名单。
4. **默认轻构图测试**：普通并列页的 Prompt 不包含具体场景类型、空间方案、辅助视觉数量和连接标签。
5. **严格关系保真测试**：真实流程、因果和反馈页仍保留方向、条件和禁止伪造关系。
6. **模式升级测试**：首次 QA 结构误读后，仅目标页升级为 directed-composition，其他页面保持 semantic-brief。
7. **正式入口端到端测试**：从 Stage 01 正式 Markdown 经 `final-script-pages` 生成 manifest 和最终 Prompt，检查权威字段来源与编译器版本。
8. **Style 09/10 终端锁测试**：恢复终端执行锁的唯一性和绝对末尾位置。

## 九、现有测试结果

执行：

```text
.venv\Scripts\python.exe -m pytest \
  tests/test_stage02_cyberppt_script_adapter.py \
  tests/test_page_artifact_spec.py \
  tests/test_artifact_prompt.py \
  tests/test_final_prompt_renderer.py -q
```

结果：`37 passed, 4 failed`。

四项失败均与 Style 09 终端执行锁有关：当前渲染结果没有保留测试要求的终端句，或没有将它放在 Prompt 的绝对末尾。这组失败与字段断层相互独立，但表明最终 Prompt 的测试契约和当前实现已经发生漂移，实施修复时应一并厘清并恢复一致性。

## 十、最终建议

优先修复 canonical parser 与 handoff 的字段投影，再引入可追溯 `semantic_brief`，随后降低默认视觉结构强度。保留 artifact-spec 作为单一正式编译链，升级其字段职责和提示强度即可。历史 `content-first-v1` 可吸收“内容优先、构图少干预”的原则，但其自身也依赖语义推断，直接回切会重新引入隐式关系推断和双链维护问题。

完成后的理想分工为：Stage 01 决定说什么、依据什么、关系是否成立；Stage 02 确保文字、边界、风格和生产契约可靠；ImageGen 决定如何把这些内容组织成具有整体感的视觉画面。

## 十一、开发落地结果

本方案已完成代码落地，正式编译器名称继续使用 `artifact-spec-v2`，内部提示词中间表示升级为 `FinalPromptIR v2`。

1. canonical Markdown 解析器已读取页面使命、主论证链和内容来源，并将 `SU-...` 来源单元与 `S/ST` Source Truth 引用分开保存。
2. Stage 02 handoff 已消费项目自身的 `deck-plan.json`，投影页面角色、来源范围、排除边界和论证链；Deck Plan 与最终脚本标题或核心判断不一致时直接阻断。
3. 完整文字稿已进入非渲染语义上下文并保存内容哈希，来源编号、后台 ID 和演讲者备注不进入正式送图 Prompt。
4. 默认提示强度已调整为 `semantic_brief`。该模式只锁定页面使命、核心判断、语义上下文、真实关系边界和精确上屏文字，场景、载体、空间组织、阅读实现与辅助细节由 ImageGen 决定。
5. `directed_composition` 仅在来源明确、关系权威为 hard，且拓扑属于顺序、依赖、因果、反馈、分层或汇聚时自动启用；也允许逐页显式指定。
6. 视觉结构 Skill、编译器、schema、校验器和审计器均已按两级模式调整。语义简报页允许省略 `execution_design`，定向构图页继续严格校验场景、载体、空间组织和文字融合字段。
7. Style 09 从 `references/visual-system.md` 实时读取终端执行锁，锁文本唯一且位于最终 Prompt 绝对末尾；测试不再绑定已经失效的旧终端句快照。

真实项目只读投影结果为 21 个内容页全部取得独立页面使命、主论证链、来源引用、来源单元和排除边界，21 页当前均为 `semantic_brief`。这些页面的关系权威来自脚本视觉结构推导，等级为 soft，因此未升级为强构图。另以来源明确的 hard 顺序关系验证了 `directed_composition` 自动升级路径。

定向回归结果：`210 passed`；补充 Stage 02 语义回归结果：`64 passed`。视觉结构 Skill 自测结果：`SELF TEST PASS`，领域中性夹具为 `6 valid, 78 invalid, 18 style variants`。全仓测试结果为 `1457 passed, 12 failed, 8 skipped`；剩余失败集中于历史基线、旧 Prompt 快照、Windows 路径和本地 Skill 虚拟环境，与本次 Stage 02 两级提示链无直接关系。
