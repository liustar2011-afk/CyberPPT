# CyberPPT 主流程总览

本文件是 CyberPPT 的流程总入口，供 Claude、Codex 及其他协作 Agent 首先阅读。

各阶段 Skill 只负责本阶段的操作细则；`AGENTS.md` 负责仓库级约束。三者发生表述差异时，先以 `AGENTS.md` 的硬性约束为准，再以本文件确定阶段顺序，最后阅读对应 Skill 的详细规则。

## 一、任务入口判断

收到任务后，先按任务类型选择入口：

1. 新脚本项目涉及源材料、页面规划或脚本写作：使用 `script` profile，先建立确定性来源索引，再调用 `cyberppt-script-understand` 生成 `foundation.json`。
2. 涉及合同/监管逐事实核验、Source Truth、完整语义模型或旧项目迁移：使用 `strict/legacy` profile，先调用 `cyberppt-source-foundation`。
3. 只涉及已锁定最终脚本的单页写作：进入 `cyberppt-write-single-page`。
4. 只涉及视觉结构、图片、SVG、ImageGen 或 PPTX QA：可以从对应 Stage 02 Skill 开始，不重复建立 Source Foundation。
5. 涉及旧项目但已有已验证 Foundation 产物：先核对产物状态，再复用；不得因项目已存在而跳过 profile 与产物有效性检查。

正式项目默认使用单人轻量流程。除非用户明确提供 `autonomous_lightweight` 任务合同，不使用自主运行例外。

## 二、唯一正式路线

### Stage 01

默认：`来源索引 → cyberppt-script-understand → cyberppt-script-workflow（PLAN/AUTHOR）`

严格/兼容：`cyberppt-source-foundation → business-semantic-understanding → project-foundation → cyberppt-script-workflow（PLAN/AUTHOR）`

### 全流程

默认：源材料 → 来源索引 → 一次 UNDERSTAND/Foundation → 轻量 Deck Plan → AUTHOR 逐页写作 → 最终全稿 → Stage 02 视觉生产 → PPTX QA 与交付

严格/兼容：源材料 → Source Foundation → 一次业务语义理解 → 机械投影 Foundation → Deck Plan → AUTHOR → Stage 02

旧版 Outline/Handoff 命令仅用于历史项目迁移的内部兼容，不是新项目或已验证 Source Truth 项目的第二条路线。

## 三、Stage 01 详细步骤

### 1. 建立脚本 Foundation

默认 `script` profile 只建立 `script/.cache/source-index.json` 和
`script/foundation.json`。来源转换采用直接解析优先、按格式回退；OCR 显式启用。

执行入口：

```bash
.venv/bin/python3 -m cyberppt prepare-source-context <project>
.venv/bin/python3 -m cyberppt prepare-script-foundation <project> --profile script
```

`prepare-source-context` 原生提取 DOCX、文本、PPTX 及安装了可选
`openpyxl` 时的 XLSX，统一保留来源哈希、标题结构和稳定 source units。
需要原生 XLSX 提取时安装 `openpyxl>=3.1,<4`；未安装时保留二进制来源登记并
给出明确警告，不静默丢弃工作表。
读取规模不超过 45 页且估算不超过 60,000 tokens 时使用 direct；超过任一
阈值时进入 long。long 保留全部标题和 source units，模型上下文先展示完整
论点骨架、mapped 预览与关键单元 deep read；精确数字、日期、责任、状态、
条件和边界只能由 deep-read 单元支撑。

`prepare-script-foundation` 输出 authoring task，由 UNDERSTAND 直接写入现有
`script/foundation.json`。任务不会生成 Source Truth、完整语义 sidecar 或新增
内容权威。Foundation 完成后，`audit-foundation` 会将 `reading_strategy` 与同级
`.cache/source-index.json` 交叉校验。

`strict/legacy` profile 保留以下完整 Source Foundation 产物：

输入源材料，运行源材料解析和语义准备，建立：

- `source.md`
- 结构和事实基础
- `normalized-facts.json`
- `concept-base.json`
- `relation-graph.json`
- `argument-chain.json`
- `semantic-report.json`

主责 Skill：默认 `cyberppt-script-understand`；严格/兼容为
`cyberppt-source-foundation`、`business-semantic-understanding`。

### 2. 形成 strict/legacy 业务语义理解

围绕业务对象、主体、动作、关系、条件、状态、数字、问题和判断，完成语义归并和论证链整理。事实强度、责任边界和来源归属必须保留。可以使用行业常识或主动联网核实辅助理解材料；非源材料本身给出的内容，`relation-graph.json` 中须标注 `basis: external` 并写明依据，不得升级为 `basis: source`。

语义理解完成后运行验证；`semantic-report.json` 必须达到 `status: ok`，才能进入页面规划。

### 3. 将交流目标纳入规划停点

基于 Foundation 提出一个忠于源材料的交流目标方向，并与章节和页面提纲一并放入 **脚本规划待确认**。普通流程不设置独立的交流目标确认节点。

交流目标中的受众、场景和行动要求，只有得到源材料直接支持时，才可以升级为源事实、源判断或页面结论。

### 4. 投影 strict/legacy Script Foundation

语义模型验证通过后，运行 `.venv/bin/python3 -m cyberppt project-foundation <project>`，将 Source Truth 机械投影到脚本引擎的 `script/foundation.json`。该步骤只搬运已确认字段，不重新分析源材料。

正式投影同时写入 `source_consumption_policy: required` 和 `source_consumption_contract_version: 2`，并保留后续忠实度检查所需的 `semantic_units`、`coverage_anchors`、条件、原文定位以及事实与主体/数字的显式绑定。版本 2 要求严格内容页在 `source_consumption.unit_dispositions` 中逐项声明语义单元进入完整稿、上屏、后续页面、追溯或有理由删减。历史 Foundation 缺少版本字段时继续使用兼容路径。历史项目重新运行 `project-foundation` 会单向进入严格模式；命令在覆盖旧 Foundation 前输出非交互警告，随后必须补齐 Deck Plan 的来源消费合同并重新通过 PLAN Gate。

产物：

- `script/foundation.json`

### 5. 规划与编写脚本

依据已确认的交流目标和 `script/foundation.json`，按 `cyberppt-script-workflow` 的 `PLAN → AUTHOR → CRITIQUE → REWRITE → DELIVER` 路线形成：

- `script/deck-plan.json`
- `script/dist/final-script.md`

Deck Plan 是 AUTHOR 之前的轻量过渡产物，只负责确定：

- 汇报对象与交流目标；
- 汇报章节、章节使命、源章节映射和内容页预算；
- 页面顺序、页面类型、暂定标题、受众问题和页面使命；
- 每个内容页允许使用的来源范围；
- 确有必要时，相邻页面不得重复或越界的内容。

核心判断、完整论证链、内容模块、证据取舍、上屏结构、视觉关系、讲述线索和
阅读密度均由 AUTHOR 在完整读取来源后形成，不得在 Deck Plan 中提前编写。

来源章节与汇报章节分层处理。Foundation 保留全部来源章节身份、边界与顺序；
Deck Plan 默认将相邻来源章节按受众问题、论证角色和承接关系归并为汇报章节，
展开全部 `source_chapter_ids` 后必须与来源顺序完全一致。正式汇报通常控制在
4 个以内，6 个为默认上限；超过 6 个必须记录无法继续归并的具体理由。
多章节汇报采用“封面—目录—逐章过渡页—内容页—封底”序列，每个汇报章节
恰有一个过渡页并位于该章内容之前；单章节汇报仍不设置章节页。

内容页标题在 PLAN 阶段只是简洁正式的主题占位，AUTHOR 可以在完整写作后调整。
副标题和核心判断属于最终脚本内容，不由 PLAN 锁定。标题覆盖检查只判断暂定标题
能否标识页面讨论对象，不把判断句回灌到标题。

新项目默认使用 Deck Plan v2 lean。v1 strict 仅用于合同、监管逐事实核验和旧项目
兼容；不得把 strict 的来源消费、上屏合同或证据质询复制到普通脚本项目。

主责 Skill：`cyberppt-script-workflow`。

该 Skill 由当前主 Agent 直接执行。仓库不另设 AUTHOR CLI 或规则式作者生成器；
“调用 Skill”要求主 Agent 实际读取 Foundation、来源正文、整份 Deck Plan 与相邻
页面合同，完成生成式写作、Critic 和整页重写。仅生成合法字段、运行审计或引用
Skill 名称均不构成 AUTHOR 执行。

进入 AUTHOR、CRITIQUE、REWRITE、单页修订或全稿审核前，主 Agent 必须完整读取
`.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`。该文件是
操作性作者规则的唯一权威；`cyberppt-script-workflow/SKILL.md` 只负责路由和阶段边界，
不得在两处维护重复作者规则。

规划确认是对话中的人工停点；审核稿必须以 Markdown 等可读格式展示，不直接把 JSON 作为审核材料。

### 6. 汇总与交付最终全稿

以当前项目的 Foundation、轻量 Deck Plan、目标页来源证据和相邻页边界为依据，一次处理一张内容页。全文主旨和目录每套稿只加载一次；逐页仅回读当前页 `source_refs` 对应证据。strict/legacy 项目可以通过 Foundation 追溯 Source Truth，不在 AUTHOR 阶段重新运行语义理解。

页面脚本依次完成：

1. 页面设计简报
2. 主论证链
3. 证据架构
4. 完整文字稿
5. 上屏文字
6. 视觉语法
7. 演讲者备注

上屏写作执行“完整页面论证 → 上屏信息选择 → 候选表达 → 定性评审 →
整页重写”。高密度页、高潮页、结论页和 Critic 重点页生成判断主导与
证据主导两个内部候选，只保留胜出结果。候选和评审理由不形成新增权威
产物、checkpoint、gate 或 receipt。

AUTHOR 写作前直接读取 Foundation、轻量 Deck Plan 和对应来源证据，理解本页的来源边界与页面使命。论证关系、完整稿、上屏结构和讲述方式由 AUTHOR 在写作中形成。逐页完成作者化写作后，再运行确定性审计；审计只负责发现问题，不代替 AUTHOR 生成或改写页面。

上屏文字的分组与结构化压缩由 AUTHOR 完成。作者按页面使命和来源证据组织“结论、证据、解读与含义”，并在 Final Script 中保留来源追溯；Deck Plan 不声明 `content_route`、`onscreen_contract`、`onscreen_composition` 或视觉准备字段。所有项目默认采用 `deck.delivery_mode: self_read`；只有用户明确要求演讲辅助型、低文字密度稿件时，才使用 `presented`。

`self_read` 内容页必须形成可独立阅读的页面闭环：明确页面主题，给出核心判断，解释判断依据，并保留理解所需的事实、范围、条件或结果。上屏文字按“语义锚点—完整核心语义—必要细项”组织；模块标题用于定位，解释句承载业务含义。数字需要说明所指对象和结论，清单需要说明归组依据和共同作用。压缩过程中保留对象、动作或判断以及必要限定，避免只剩抽象口号、分类名称和依赖讲解的提示词。

内部汇报默认采用内部专家视角，以集团、企业、业务部门、项目团队或行业职责为真实主体。客户、市场、成交、价值实现、增长和商业化属于正常经营议题，只要来源或已确认交流目标提供支撑即可进入页面。质量检查聚焦叙述身份、责任主体、证据和行动依据；不得以这些经营词汇本身作为违规条件。面向内部或混合受众时，`建议贵司`、外部咨询顾问身份和无依据的泛化企业建议构成语气漂移。

v1 strict 兼容路线可以继续声明结构化证据合同。v2 lean 只保留页面来源范围和必要的暴露边界，完整证据取舍由 AUTHOR 完成，最终审计直接对照 Foundation 与 Final Script。

Deck Plan 完成后运行 `cyberppt-script review-plan <deck-plan.json> <foundation.json>`，生成简洁 Markdown 审阅稿，只展示章节、页面分配、暂定标题、页面问题、页面使命和来源范围。该输出只用于“脚本规划待确认”的人工阅读，不新增权威内容产物、确认文件或审批状态。

v1 strict Foundation 的 `source_consumption_policy: required` 继续服务严格兼容路线。v2 lean 不在 Deck Plan 逐记录声明消费方式；完整稿与上屏选择由 AUTHOR 在来源边界内完成，机器审计直接检查引用、数字、责任、状态、条件与边界。

AUTHOR 对严格页面逐条验证完整稿锚点，并专门检查数字、日期、条件、责任主体、状态和分类层级。上屏审计验证代表来源的模块映射和可见特征。严格 Foundation 缺合同或只使用宽泛主题词时均失败关闭；历史 Foundation 保留原有兼容逻辑。

页面信息密度不使用固定字数或固定模块数门槛。Final Script 默认声明 `deck.delivery_mode: self_read`，内容页可在自身声明 `content_load`；最终审计依据实际上屏模块和语义信息单元检查阅读自洽性。用户明确选择演讲辅助型稿件时可声明 `presented`。Plan 不承担信息密度设计。

页面关系由 AUTHOR 基于来源和完整稿形成，并写入 Final Script。`audit-final` 直接对照 Foundation 检查无来源关系、数字、责任、状态和边界，不再要求关系先在轻量 Plan 中获批。

项目定位、能力、任务、职责和验证场景等明细项，来源提供对象、作用、任务或边界时，应采用“业务标签：细化说明”；来源只列分类名称且没有细节时可以保留标签式列举。`audit-final` 与 `lint` 继续检查明细退化、同段误分组和来源边界问题。

将已完成页面汇总为最终脚本后，执行真实存在的全稿检查，检查来源覆盖、事实强度、页面关系、标题层级、上屏文字、重复表达和脚本契约：

```bash
.venv/bin/python3 -m script_engine.cli audit-final <final-script.json> <deck-plan.json> <foundation.json>
.venv/bin/python3 -m script_engine.cli lint <final-script.json>
.venv/bin/python3 -m script_engine.cli check-sync <final-script.json> <final-script.md>
```

`audit-final` 与 `lint` 是 Stage 01 的确定性编辑质量检查；存在 JSON 镜像时再用 `check-sync` 校验 Markdown 同步。Stage 02 以已确认脚本为唯一内容输入；项目内脚本和外部脚本均通过正式编排入口进入独立视觉生产链。

## 四、Stage 01 的两个人工停点

| 停点 | 必须展示 | 用户反馈后的动作 |
|---|---|---|
| 脚本规划待确认 | 交流目标、章节结构、页面顺序、暂定标题、页面问题/使命和来源范围 | 修改现有 Deck Plan 后继续 |
| 最终全稿 | 全套页面脚本和全稿审计结果 | 等待最终确认，不自行跳过 |

这两个停点发生在对话中，不新增 approval、receipt、attempt、manifest、哈希绑定或平行审阅目录。单页内容仅在用户主动要求逐页审核时展示，不构成默认流程停点。

## 五、Stage 02 视觉生产步骤

### Stage 02 正式路线注册表

| 路线标识 | 常用检索词 | 正式入口 | 组装分支 | 权威细则 |
|---|---|---|---|---|
| `stage02.high_fidelity_quick_editable` | 高保真+Quick、高保真 Quick、无字底图+文字 SVG、图片转可编辑 PPT、authored SVG、Quick editable | `.venv/bin/python3 -m cyberppt final-script-pages ... --production-build --production-mode image-to-editable-svg --assembly-mode editable` | `editable` | `.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md` |
| `stage02.picture_ppt` | 图片型 PPT、整页图片 PPT | `.venv/bin/python3 -m cyberppt final-script-pages ... --production-build --production-mode image-to-editable-svg --assembly-mode image` | `image` | `.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md` |
| `stage02.dual_delivery` | 图片型+可编辑、双份交付 | 同一正式入口并使用 `--assembly-mode both` | `both` | `.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md` |

路由规则：出现“高保真+Quick”“无字底图+文字 SVG”或同义需求时，固定进入 `stage02.high_fidelity_quick_editable`，随后读取 `cyberppt-stage02-editable-pptx`。不要把它路由到图片型 PPT，也不要从 `scripts/image_to_editable_svg/` 的退役入口推断当前流程。正式代码编排位于 `cyberppt/commands/final_script_pages.py`，Quick 组装适配位于 `scripts/image_to_pptx_runtime/stage02_adapter.py`，内置运行时说明位于 `scripts/image_to_pptx_runtime/UPSTREAM.md`。

### 1. 最终脚本和页面生产入口

使用已确认的项目内或外部脚本，Stage 02 直接接收 `--script <path>` 指向的最终脚本文件，并在自身工作区建立输入快照。Stage 02 不读取 Stage 01 的 Foundation、Deck Plan、Source Truth、Outline 或流程状态。

Stage 02 不区分项目内脚本、外部脚本或人工脚本。所有输入均按普通 `script_file` 处理，并复制到 Stage 02 自有路径 `workbench/inputs/final-script.md` 作为运行快照；原始文件路径仅用于来源记录和变更检测，不改变运行分支。原始文件暂时不可用时，仅在 Stage 02 已有快照及其字节哈希仍有效时允许续跑。

### 2. Stage 02 script input

Stage 02 以传入脚本文件为唯一跨阶段输入，并在自身工作区记录脚本快照与 SHA-256。脚本文件发生变化后，Stage 02 自行判定已有视觉产物失效。`business_relationships`、`content_load` 等字段如果出现在输入文件中，Stage 02 将其视为文件合同的一部分；semantic verifier 只校验输入文件内部关系是否自洽，并派生 `render_topology` 供视觉布局使用。对 hard/strong 关系出现 rejected 或 unresolved 时，Stage 02 拒绝当前输入文件，不推测其上游生产过程，也不修改关系后继续。`content_load` 未显式声明时按 `standard` 处理。

### 3. 视觉结构

运行 `prepare-visual-structure`，按视觉结构 Skill 生成视觉决策及其编译产物，再运行视觉结构审计。

视觉结构 Skill 只决定视觉承载、关系表达、空间语法和视觉层级，不重新解释源材料事实，不新增页面结论。

### 4. 自动锁定统一视觉风格

Stage 02 主流程统一使用风格 09。运行 `final-script-pages` 时无需人工选择；未提供锁文件时自动创建风格 09 的 `cyberppt.visual_style_lock.v1` JSON。

如需断点续跑，可通过 `--style-lock` 指定已有风格锁；该锁必须为风格 09，后续页面生产、Prompt 编译和图片生成消费同一份锁。

`prepare-visual-structure` 只负责视觉关系、承载方式、空间语法和视觉决策。

### 5. Prompt 和 Manifest

编译每页实际送图提示词和 manifest，并检查以下内容彼此分离：

- 页面完整文字稿
- 可编辑正文
- 图片中的严格上屏文字
- 视觉设计上下文

PNG 文件存在不等于提示词、批次或 QA 成功。必须检查实际落盘的 `prompts/pXX.txt`、manifest 和运行记录。

### 6. 图片生成和 QA

执行图片生成、图片文字检查、尺寸检查、视觉 QA 和批次结果核对。请求尺寸、模型返回尺寸、标准化尺寸和幻灯片画布尺寸必须分别记录。

Stage 02 采用逐页检查点和同批次恢复：

- 每页生成或文字审计结束后，立即把状态、图像路径和审计回执写入当前 manifest；
- 单页失败时保留其他已通过页面，后续使用同一 `build_id`、输出目录和生产参数继续运行；
- 恢复时只跳过“图像存在且文字审计通过”的页面，失败页、缺失页和无有效审计回执的页面必须重新处理；
- 普通恢复不得使用 `--force-images`，该参数只用于用户明确要求的整批重绘；
- 恢复命令必须保留 `--generate-images`、`--production-build` 和原 `--assembly-mode`，确保补齐页面后继续完成 PPTX 组装。

`image-to-editable-svg` 是 Stage 02 唯一生产模式，`editable` 是默认 PPTX 组装分支。高保真 Quick 路线使用 `final-script-pages --production-build --assembly-mode editable`；它与图片型 PPT 的 `--assembly-mode image` 是两条独立组装分支。对每个内容页按以下固定顺序执行：

1. 生成并审计 full 图；可编辑重建分支将通过文字审计的 full 图写入 `reconstruction_visual_source` SHA-256 绑定，作为后续重建的视觉来源。后续阶段可以拆层、清字和重建原生文字，不重新设计已接受的视觉构图；
2. 从 full 图准备无文字底图，清除计划以 SVG 原生文字重建的区域；
3. 当前 Codex 主 Agent 直接查看已绑定的归一化 full 图、无字底图、锁定上屏文字和已注册局部图层，在同一画布坐标系中编写完整 authored SVG；该步骤承担高保真重建，不承担第二轮视觉设计。缺少 authored SVG 时生产编排停在该页，完成编写后用同一 build 续跑；
4. 仅对当前页运行可编辑页策略、原生文字坐标、文字样式和 SVG 质量检查，生成该页包装 SVG、单页 Quick PPTX、OfficeCLI PNG 与几何报告；
5. 渲染前检查 `<text>` 及其全部 `<tspan>` 的坐标连续性；同一文字节点跨列或跨视觉区域跳转时直接阻断。渲染后立即以 `rendered_pending_visual_review` 写回检查点；主 Agent 必须查看该页实际 OfficeCLI PNG，逐项核对布局、字号字重、颜色、换行、中文残留和可读性，机器几何检查不得自动代替看图；
6. 使用 `.venv/bin/python3 -m cyberppt review-quick-page ...` 把审核结论写入同一个检查点；回执绑定预览 PNG 哈希，预览变化后自动失效。续跑只复用输入未变化、预览仍存在且视觉审核通过的页面；
7. 请求范围内全部页面通过逐页检查点后，统一组装整套可编辑 PPTX，并执行全稿文字与 OfficeCLI 交付 QA。

逐页检查点用于失败隔离、视觉审核和续跑。审核回执写在现有 manifest 中，不新增审批文件或平行运行目录，也不得把每页单独发布的 PPTX 再合并成最终文件。页面输入摘要仅用于判断是否需要自动重验；不匹配时直接重验该页，不触发 full 图重绘或整批失效。

文字 QA 分为两个阶段，门禁对象必须区分：

1. full 图进入 Quick 前，检查错中文字和伪中文；忽略标点、孤立数字和英文。未通过时只重绘该 full 图。
2. 清图阶段的 OCR 仅记录文字清除诊断，不以“零残留”单独阻断。可编辑分支消费已经完成的高保真 authored SVG；生产编排不得根据 OCR 框自动合成文字 SVG。
3. 清图模型只提供声明文字掩膜内的局部背景；掩膜外必须逐像素保留 audited full 图。进入 Quick 前重新计算掩膜外差异，禁止仅依据 manifest 中的自报通过字段放行。
4. SVG 回写和 PPTX 渲染后，检查最终可见文字。残留的真实中文、错中文字或伪中文会阻断交付；仅存在于中间清图 OCR 结果中的残留不得触发重绘。

因此，已有通过 full 图文字审计的页面在可编辑分支失败时，优先复用 full 图并继续“清图 + SVG 回写 + 最终可见结果 QA”。只有最终可见结果仍有错中文字、伪中文或未被 SVG 覆盖的真实中文，才重绘该页图像。

进入图片转可编辑 PPTX 前，对配图内部的可读文字逐项分类：

- 需要编辑或属于信息表达的文字，清底后必须回写为原生 SVG 文字；
- 作为图形本体一部分且应保持原样的字样，可以随经过核验的局部图片层保留；
- OCR 误识别出的伪文字、图标笔画或无业务语义字形，可以登记为 `decorative_glyph` 并保留在局部图形内；必须有坐标和通过的局部视觉审阅，且不得回写为 SVG 文字；
- 未分类、清底后未回写或形成空白容器的文字区域，阻断导出。

每页必须在 pairs[*].graphic_text_policy 中声明分类完成状态、文字处理方式和空白容器检查结果。该策略由 Stage 02 Quick 适配器在 PPTX 导出前执行机器门禁。

### 7. PPTX 组装和交付 QA

完成 PPTX 组装后，检查文字可读性、图片质量、版式、溢出、可编辑性、渲染结果和交付状态，并确认配图文字策略 QA 与空白容器门禁通过。所有关键门禁通过后，才能称为完成。

PPTX 组装支持三个正式分支：`editable` 为默认输出，`image` 输出图片型 PPT，`both` 同时输出两类文件。图片型和双份交付只在用户明确要求时选择。三个分支必须消费同一份逐页审计 manifest，且仅在请求范围内全部页面通过审计后启动。

## 六、权威产物与边界

### 默认 script profile

`script/foundation.json` 是统一语义 Foundation；
`script/.cache/source-index.json` 是唯一来源派生索引。

### Strict/legacy Source Foundation 权威产物

`normalized-facts.json`、`concept-base.json`、`relation-graph.json`、`argument-chain.json`、`deck-brief.json` 和 `page-plan.json` 是上游权威输入。

### CyberPPT 投影产物

`semantic-argument-model.json`、`source-truth.json` 和 `outline.json` 是
strict/legacy 下游兼容投影，不得反向成为第二套语义权威。

### 页面脚本权威

最终脚本及其审计结果是 Stage 02 的内容输入。修改脚本后必须重新执行受影响的 handoff、manifest、提示词和 QA 环节。

## 七、禁止事项

- 不从旧项目、旧脚本或隐藏目录复制事实源。
- 不在已验证 Foundation 产物上重新运行旧版语义理解、Source Truth 编译或机械 Outline 编译。
- 不因审计覆盖不足机械增加页面、模块、锚点句或附件字段。
- 不把附件登记、清单、表单和实施明细默认提升为主文页面结论。
- 不把视觉提示词中的设计上下文写成新的业务判断。
- 不以 PNG 存在、命令退出码为零或局部测试通过，替代端到端产物验证。

## 八、完成判定

只有同时满足以下条件，才能对外称为完成：

1. 当前 profile 的 Foundation 和语义验证通过；strict/legacy 另需 Source Truth 验证通过。
2. 轻量 Deck Plan 已完成章节、页数、页面使命和来源边界检查，并经过人工规划停点。
3. AUTHOR 已完成整页上屏重写闭环并通过 Final Script 审计。
4. Stage 02 已建立当前脚本绑定的 handoff，脚本可以来自本项目或外部路径。
5. 风格已由用户确认，并生成有效的 JSON 风格锁。
6. 视觉结构审计和实际提示词检查通过。
7. 图片、PPTX、渲染和交付 QA 通过。
8. 最终回复提交实际产物的绝对路径链接，并明确未验证事项。
