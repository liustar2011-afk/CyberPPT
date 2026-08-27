# CyberPPT 主流程总览

本文件是 CyberPPT 的流程总入口，供 Claude、Codex 及其他协作 Agent 首先阅读。

各阶段 Skill 只负责本阶段的操作细则；`AGENTS.md` 负责仓库级约束。三者发生表述差异时，先以 `AGENTS.md` 的硬性约束为准，再以本文件确定阶段顺序，最后阅读对应 Skill 的详细规则。

## 一、任务入口判断

收到任务后，先按任务类型选择入口：

1. 涉及源材料、Source Truth、语义模型、Outline、page plan、源材料重跑或 Outline 审计：先阅读并调用 `cyberppt-source-foundation`。
2. 只涉及已锁定最终脚本的单页写作：进入 `cyberppt-write-single-page`。
3. 只涉及视觉结构、图片、SVG、ImageGen 或 PPTX QA：可以从对应 Stage 02 Skill 开始，不重复建立 Source Foundation。
4. 涉及旧项目但已有已验证 Foundation 产物：先核对产物状态，再复用；不得因为项目已存在而跳过 `cyberppt-source-foundation`。

正式项目默认使用单人轻量流程。除非用户明确提供 `autonomous_lightweight` 任务合同，不使用自主运行例外。

## 二、唯一正式路线

### Stage 01

`cyberppt-source-foundation` → `business-semantic-understanding` → `project-foundation` → `cyberppt-script-workflow`（PLAN/AUTHOR）

### 全流程

源材料 → Source Foundation → 业务语义理解 → 交流目标 → Outline 与页面计划 → Handoff → 逐页脚本 → 最终全稿 → Stage 02 视觉生产 → PPTX QA 与交付

旧版 Outline/Handoff 命令仅用于历史项目迁移的内部兼容，不是新项目或已验证 Source Truth 项目的第二条路线。

## 三、Stage 01 详细步骤

### 1. 建立 Source Foundation

输入源材料，运行源材料解析和语义准备，建立：

- `source.md`
- 结构和事实基础
- `normalized-facts.json`
- `concept-base.json`
- `relation-graph.json`
- `argument-chain.json`
- `semantic-report.json`

主责 Skill：`cyberppt-source-foundation`、`business-semantic-understanding`。

### 2. 形成业务语义理解

围绕业务对象、主体、动作、关系、条件、状态、数字、问题和判断，完成语义归并和论证链整理。事实强度、责任边界和来源归属必须保留。

语义理解完成后运行验证；`semantic-report.json` 必须达到 `status: ok`，才能进入页面规划。

### 3. 提出交流目标

先基于语义结果提出一个忠于源材料的交流目标方向，再交给用户修改或确认。

交流目标中的受众、场景和行动要求，只有得到源材料直接支持时，才可以升级为源事实、源判断或页面结论。

### 4. 投影 Script Foundation

语义模型验证通过后，运行 `.venv/bin/python3 -m cyberppt project-foundation <project>`，将 Source Truth 机械投影到脚本引擎的 `script/foundation.json`。该步骤只搬运已确认字段，不重新分析源材料。

产物：

- `script/foundation.json`

### 5. 规划与编写脚本

依据已确认的交流目标和 `script/foundation.json`，按 `cyberppt-script-workflow` 的 `UNDERSTAND → PLAN → AUTHOR → CRITIQUE → REWRITE → DELIVER` 路线形成：

- `script/deck-plan.json`
- `script/dist/final-script.md`

规划阶段的每个内容页至少明确：

- 一个受众问题
- 一个页面使命
- 一个核心判断
- 一个不可替代价值
- 一条主论证链
- 证据职责
- 不上屏内容
- 后续保留内容
- 拆页风险
- 前后页衔接

主责 Skill：`cyberppt-script-workflow`。

规划确认是对话中的人工停点；审核稿必须以 Markdown 等可读格式展示，不直接把 JSON 作为审核材料。

### 6. 汇总与交付最终全稿

以当前项目的 Outline、Source Truth、source units、目标页和相邻页契约为依据，一次处理一张内容页。

页面脚本依次完成：

1. 页面设计简报
2. 主论证链
3. 证据架构
4. 完整文字稿
5. 上屏文字
6. 视觉语法
7. 演讲者备注

写作前运行 `page-preflight --page <page_id>`，读取本页的锚点策略、短语上限和语义拓扑。required 模式必须达到 `contract_status: ready`；门禁依据显式主链、卫星、边界、分组、同级集合、禁止合并边和可见性预算生成写作约束。每页完成后运行 `page-lint --page <page_id>`；状态分为 `passed`、`passed_with_warnings` 和 `rewrite_required`，后者阻断提交。`page-lint` 复用 `script-audit` 的页面规则，跨页关系和最终全稿格式继续在第 8 步统一确认。

上屏文字的分组与结构化压缩由 Stage 01 完成。内部汇报的内容页可在 Deck Plan 中声明可选 `content_route`：`state`、`diagnosis`、`system`、`action` 或 `source_native`，并以 `background`、`current`、`progress`、`comparison`、`risk`、`boundary`、`coordination`、`next_step` 等侧面细化。它只提供作者化组织提示，不增加页面类型，不替代 `argument_role` 的论证权限，也不替代 `page_logic_contract` 的命题、节点和关系约束。作者按“结论 → 证据 → 解读 → 含义 → 来源”组织页面：含义必须表现为有来源依据的内部影响、关注点、工作要求、协同事项、风险提示或后续安排；来源保留在可追溯字段中，不写成上屏模块。路由不明确时使用 `source_native`，不得仅凭标题关键词猜测。

内部汇报默认采用内部专家视角，以集团、企业、业务部门、项目团队或行业职责为真实主体。客户、市场、成交、价值实现、增长和商业化属于正常经营议题，只要来源或已确认交流目标提供支撑即可进入页面。质量检查聚焦叙述身份、责任主体、证据和行动依据；不得以这些经营词汇本身作为违规条件。面向内部或混合受众时，`建议贵司`、外部咨询顾问身份和无依据的泛化企业建议构成语气漂移。

Deck Plan 完成后运行 `cyberppt-script review-plan <deck-plan.json> <foundation.json>`，生成只读 Markdown 页面判断带，连续展示标题、核心判断、页面职责、证据状态和前后页承接。该输出只用于“脚本规划待确认”的人工阅读，不新增权威内容产物、确认文件或审批状态。

页面信息密度不使用固定字数或固定模块数门槛。Stage 01 审计依据页面已声明的来源证据、页面命题、`onscreen_contract` 与 `content_route.meaning_signals` 检查应保留的业务信息；来源本身较薄且没有额外业务职责时可标记 `content_load: light`。需要为后续视觉生产预先锁定的完整判断句、业务容器或表格文字角色，写入可选 `stage02_readiness`。该字段只定义 Stage 02 必须保留的语义预期；实际换行、越界、碰撞和字号仍由 Stage 02 对生成结果核验。

页面可按 `onscreen_contract.expression_mode` 选择 `phrase_led`、`sentence_led` 或默认的 `mixed` 表达方式；完整判断句用于承载模块命题，短语或短分句用于承载具体证据。数字编号只表达来源支持的流程、阶段、时间、优先级、门控或其他真实顺序；普通并列分类使用无编号业务标题。共享标题、谓词、对象、限定语或结果只在父级表达一次，子项分别承载差异信息，避免为追求短语形式制造同义重复。

项目定位、能力、任务、职责和验证场景等功能性模块的明细项，来源或已批准页面关系提供了对象、作用、任务或边界时，应采用“业务标签：细化说明”，如“绿色低碳：检验标准在该类业务中的适用性”，末尾不加句号。来源只列分类名称且没有项目级细节时，可以在 Plan 的 `onscreen_contract.detail_policy` 中声明 `label_only_allowed: true`，保留标签式列举；不得为满足形式补写无来源说明。`page-lint`、`script-audit` 和 Script Engine 的 PLAN→AUTHOR 审计共同检查 `ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL`。

将已完成页面汇总为最终脚本，执行全稿审计，检查来源覆盖、事实强度、页面关系、标题层级、上屏文字、重复表达和脚本契约。

`script-audit` 是 Stage 01 的编辑质量门。Stage 02 以已确认脚本为唯一内容输入；项目内脚本和外部脚本均可通过 `prepare-stage02-handoff --script <path>` 进入独立的视觉生产链。

## 四、Stage 01 的四个人工停点

| 停点 | 必须展示 | 用户反馈后的动作 |
|---|---|---|
| 交流目标 | 基于源材料提出的一个方向 | 修改现有权威方向后继续 |
| 章节和页面提纲 | 章节结构、页面顺序、页面使命和核心判断 | 修改现有权威 Outline 后继续 |
| 页面详细内容 | 目标页完整稿、上屏文字和视觉结构 | 只修改目标页及必要上游契约 |
| 最终全稿 | 全套页面脚本和全稿审计结果 | 等待最终确认，不自行跳过 |

这四个停点发生在对话中，不新增 approval、receipt、attempt、manifest、哈希绑定或平行审阅目录。

## 五、Stage 02 视觉生产步骤

### Stage 02 正式路线注册表

| 路线标识 | 常用检索词 | 正式入口 | 组装分支 | 权威细则 |
|---|---|---|---|---|
| `stage02.high_fidelity_quick_editable` | 高保真+Quick、高保真 Quick、无字底图+文字 SVG、图片转可编辑 PPT、authored SVG、Quick editable | `.venv/bin/python3 -m cyberppt final-script-pages ... --production-build --production-mode image-to-editable-svg --assembly-mode editable` | `editable` | `.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md` |
| `stage02.picture_ppt` | 图片型 PPT、整页图片 PPT | `.venv/bin/python3 -m cyberppt final-script-pages ... --production-build --production-mode image-to-editable-svg --assembly-mode image` | `image` | `.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md` |
| `stage02.dual_delivery` | 图片型+可编辑、双份交付 | 同一正式入口并使用 `--assembly-mode both` | `both` | `.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md` |

路由规则：出现“高保真+Quick”“无字底图+文字 SVG”或同义需求时，固定进入 `stage02.high_fidelity_quick_editable`，随后读取 `cyberppt-stage02-editable-pptx`。不要把它路由到图片型 PPT，也不要从 `scripts/image_to_editable_svg/` 的退役入口推断当前流程。正式代码编排位于 `cyberppt/commands/final_script_pages.py`，Quick 组装适配位于 `scripts/image_to_pptx_runtime/stage02_adapter.py`，内置运行时说明位于 `scripts/image_to_pptx_runtime/UPSTREAM.md`。

### 1. 最终脚本和页面生产入口

使用已确认的项目内或外部脚本，先运行 `prepare-stage02-handoff --script <path>`，再进入视觉结构与 `final-script-pages`。页面生产前必须具备当前脚本绑定的 Stage 02 handoff 和视觉结构审计。

外部脚本进入项目后，仓库会将其保留到项目标准路径 `workbench/scripts/final/script-final.md`；后续 handoff、视觉结构、manifest 和生产续跑均绑定该项目内副本，同时在 handoff 的 `source_bindings.script.external_path` 保留外部来源路径。外部来源暂时不可用时，仅当现有 handoff 能证明路径和副本字节仍匹配，才允许使用项目副本续跑。

### 2. Stage 02 handoff

运行 `prepare-stage02-handoff`，核对当前最终脚本、项目绑定、脚本版本和页面范围。脚本发生变化后，必须重新生成 handoff，不得沿用旧绑定。

### 3. 视觉结构

运行 `prepare-visual-structure`，按视觉结构 Skill 生成视觉决策及其编译产物，再运行视觉结构审计。

视觉结构 Skill 只决定视觉承载、关系表达、空间语法和视觉层级，不重新解释源材料事实，不新增页面结论。

### 4. 选择并锁定视觉风格

风格选择仍然存在，是 Stage 02 的正式前置步骤，发生在脚本合同建立后、`final-script-pages` 和 Prompt/Manifest 编译前。

执行要求：

1. 向用户展示可选风格样张并完成确认。
2. 从默认风格 1-8 中选择，或在明确使用扩展风格时选择 9-10。
3. 使用 `--style-id`、`--style-name` 或已有的 JSON `--style-lock` 固化选择。
4. 风格锁必须是 `cyberppt.visual_style_lock.v1` JSON；Markdown 确认文件不能替代风格锁。
5. 后续页面生产、Prompt 编译和图片生成必须消费同一份风格锁，不得临时替换外部预设。

`prepare-visual-structure` 只负责视觉关系、承载方式、空间语法和视觉决策，明确不选择视觉风格。风格选择完成后，才能进入最终页面生产和 Prompt 编译。

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

1. 生成并审计 full 图，作为可见表面与文字对照证据；
2. 从 full 图准备无文字底图，清除计划以 SVG 原生文字重建的区域；
3. 当前 Codex 主 Agent 直接查看归一化 full 图、无字底图、锁定上屏文字和已注册局部图层，在同一画布坐标系中编写完整 authored SVG；缺少 authored SVG 时生产编排停在该页，完成编写后用同一 build 续跑；
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

### Source Foundation 权威产物

`normalized-facts.json`、`concept-base.json`、`relation-graph.json`、`argument-chain.json`、`deck-brief.json` 和 `page-plan.json` 是上游权威输入。

### CyberPPT 投影产物

`semantic-argument-model.json`、`source-truth.json` 和 `outline.json` 是下游兼容投影，不得反向成为第二套语义权威。

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

1. Source Foundation 和语义验证通过。
2. Outline 已完成作者化、审计和人工提纲停点。
3. Handoff 投影验证通过。
4. Stage 02 已建立当前脚本绑定的 handoff，脚本可以来自本项目或外部路径。
5. 风格已由用户确认，并生成有效的 JSON 风格锁。
6. 视觉结构审计和实际提示词检查通过。
7. 图片、PPTX、渲染和交付 QA 通过。
8. 最终回复提交实际产物的绝对路径链接，并明确未验证事项。
