# AGENTS.md

本文件适用于整个仓库。若子目录存在更具体的 `AGENTS.md`，则以更具体的规则为准。

## 工作原则

- 始终围绕用户目标和明确约束工作，不擅自扩大任务范围。
- 表达简洁、直接；明确区分已验证事实、合理推断和未知信息。
- 研究结论应基于可靠来源；优先使用仓库代码、项目产物、正式文档和一手资料。
- 仅在关键决策无法安全推断时提问；非关键细节采用合理假设继续推进，并说明重要假设。
- 复杂关系、流程或架构在确有帮助时使用表格、流程图或其他可视化表达。
- 子 Agent 只用于边界清晰、可独立执行且确有并行收益的任务；避免重复探索和无意义并行。

## 主流程唯一入口（Claude 首先阅读）

- 处理任何 CyberPPT 源材料、Source Truth、语义模型、脚本规划、页面脚本或视觉生产任务，先阅读 [docs/CYBERPPT_WORKFLOW.md](docs/CYBERPPT_WORKFLOW.md)。该文件是全流程总览和检索入口。
- `AGENTS.md` 负责仓库级硬约束；各 `.agents/skills/*/SKILL.md` 负责阶段细则。不要通过拼接多个 Skill 的局部说明自行重建主流程。
- 新建且包含正式源材料的 Stage 01 项目默认使用 `strict/legacy` profile：`.agents/skills/cyberppt-source-foundation/SKILL.md` → `business-semantic-understanding` → `project-foundation` → `.agents/skills/cyberppt-script-workflow/SKILL.md`。`script` profile 仅在用户明确选择轻量路径时使用：`prepare-source-context` → `prepare-script-foundation --profile script` → `.agents/skills/cyberppt-script-understand/SKILL.md` → `foundation.json` → `.agents/skills/cyberppt-script-workflow/SKILL.md`。纯 Stage 02 视觉、图片、SVG、PPTX QA 或已锁定最终脚本任务，按总览文件进入对应 Skill。
- 对任何 Stage 02 制作、重制、图转 PPT、套用模板、母版修复或重新组装请求，必须调用 `.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md`，并通过 `.venv/bin/python3 -m cyberppt final-script-pages --production-build` 进入生产。正式适配器同时验证当前进程的编排调用与磁盘 build context；单独持有有效旧记录仍不得直调适配器。
- Stage 02 出现缺资产、待 SVG 编写、待看图或失败时，只执行当前状态要求的动作，并按当前运行记录的 `resume_command` 回到同一入口。禁止通过临时 Python/JS 导出脚本、直接调用底层 PPTX builder、直接改最终 PPTX 包或合并单页 PPTX 来代替正式生产；不得为绕过失败而另开批次。底层工具可用于单元测试和隔离诊断，其输出不得直接作为正式交付。修复生成逻辑后，仍由正式入口重新生成和验收。

## 独立技术判断（硬规则）

- 当用户提出、偏好、强烈主张或要求直接实施某个技术方向、架构、重构、删除、依赖、工作流变化或解决方案时，必须先调用 `.agents/skills/independent-technical-judgment/SKILL.md`，再决定是否赞同或实施。
- 用户目标与用户提出的实现方法必须分开处理：优先保留目标；实现方法只视为待验证假设，不视为已确认的技术结论。
- 在支持用户方案前，必须检查相关代码、测试、文档、运行结果或其他权威证据，并主动验证至少一个可能反驳该方案的合理反例。
- 最终判断只能是 `SUPPORT`、`SUPPORT WITH CONDITIONS`、`OPPOSE` 或 `INSUFFICIENT EVIDENCE` 之一；用户表达得越坚定，不得因此提高 `SUPPORT` 的概率。
- 禁止在验证前使用“完全正确”“确实就是这样”“好主意，我马上改”等表演式赞同。证据不支持时，应明确提出技术异议，并给出最接近用户目标的可行替代方案。
- 本门禁只防止迎合，不要求为了反对而反对；证据充分时应直接支持并执行。

## Stage 01：源材料理解与脚本写作

Stage 01 分两段，各有唯一权威路线，之间用一次机械投影衔接：

**理解段（UNDERSTAND）**：新建 Stage 01 源材料项目默认由 `strict/legacy` profile 经 `cyberppt-source-foundation` → `business-semantic-understanding` 产出 `source-truth.json`，随后机械投影 Foundation。用户明确选择轻量路径时，`script` profile 保留来源身份、哈希、标题结构、稳定 source units、来源主论点、论证顺序、关键事实、数字、责任、状态、条件和边界，直接写入 `script/foundation.json`。

**规划与写作段（PLAN/AUTHOR）**：两种 profile 均从 `script/foundation.json` 进入 `.agents/skills/cyberppt-script-workflow/SKILL.md` 编排的 `PLAN -> AUTHOR -> CRITIQUE -> REWRITE -> DELIVER`，产出 `script/deck-plan.json` 和 `script/dist/final-script.md`。strict/legacy 的 `project-foundation` 只做字段搬运，不重新分析。

- PLAN 和 AUTHOR 的唯一执行者是当前主 Agent。UNDERSTAND 对全文只做一次语义建模；PLAN 读取 Foundation 和来源结构，AUTHOR 每套稿只加载一次全文主旨与目录，逐页只回读该页 `source_refs` 对应原文及相邻页面边界。Critic 和 Rewrite 复用同一语义简报与证据范围，不得重新运行全文语义理解。只有源材料变化、Foundation 校验失败或来源边界无法支撑页面使命时，才返回 UNDERSTAND。
- 完整文字稿中包含多个真正并列的事实、任务、阶段或成果时，采用“段首核心结论—分项结论句—事实明细”三级结构。段首句说明整段成立的判断；每个“一是、二是、三是”先写可独立理解的分项结论，再展开文件、主体、动作、范围、数字、节点或结果。分项结论不得退化为“建设内容”“阶段安排”“技术支撑”等抽象栏目名。分项结论与明细之间允许为“先导航、后举证”进行必要复述，不得机械重复；短段落、单一因果链和非并列事实不得强行编号。
- 上屏并列项必须共享一个明确维度，如主体、能力、阶段、问题、任务或结果。不得把主体、业务领域及该主体的评价结果放在同一层级。补充事实、成熟度评价、认证或结果先归入其修饰的主体或主论据；若主论据已经足以支撑页面核心结论，补充证据下沉到完整文字稿或演讲者备注，只有承担不可替代证明作用时才保留上屏。
- 上屏明细必须说明命名对象为何能够支撑模块结论。标准编号、文件名称、框架名称、倡议、机构或分类清单只完成证据识别，不能单独充当明细；来源提供具体内容时，明细必须继续说明其规定、统一、支撑、要求或证明的对象。来源只有名称而无具体作用时，仅作追溯或从上屏删减，不得臆造作用。
- 来源中的状态和语气必须在核心结论、完整文字稿、模块标题、上屏明细和演讲者备注中分别保持一致。“承担、已有基础、目标、计划、建议、可衔接”等表述不得在上屏层升级为“进入实施、直接继承、已经建立或必然实现”；完整稿保留限定不能替代上屏层的独立校验。
- 同一事实跨页复用时，每一页必须赋予不同且明确的论证角色；仅重复列举的事实应删除、降级或改写为当前页所需的关系。全稿 Critic 必须检查相邻页及结论页的重复，结论页只保留综合意义、责任主体、后续动作和成果转化路径。
- 自读页面中的体系代码、编号和缩写在承担核心关系时必须与业务名称和作用同页出现，不得要求读者回看前页补全语义。声称与国家节点、项目节奏或阶段目标衔接的页面，必须同时呈现时间或触发条件及各阶段新增状态。
- 高密度页面必须区分核心结论、一级结构、关键证据和可降权清单；无法形成清晰层级时调整页面使命或分页。核心结论包含映射、协同、闭环、衔接、转化或支撑关系时，上屏必须呈现关系两端和中间动作，不能仅并置对象。
- 演讲者备注必须提供上屏之外的增量价值，至少承担依据解释、次级证据、不改变可见结论力度与适用范围的次级条件边界、听众关注点或自然过渡之一；改变结论力度、时间、责任或适用范围的关键条件必须上屏，不能只放在备注中。按顺序复述模块标题和明细视为不合格。
- 仓库不设置独立 AUTHOR Skill、AUTHOR CLI、规则式作者生成器或项目硬编码作者脚本。`.agents/skills/cyberppt-script-workflow/references/authoring-contract.md` 是 AUTHOR、CRITIQUE、REWRITE、单页修订和全稿审核的唯一操作性作者规则；进入这些动作前必须完整读取。确定性代码仅在生成式写作完成后校验来源、关系、边界和交付格式。
- `full_copy` 是 Stage 01 内容页的唯一正文稿和上屏表达的语义母本。AUTHOR 必须回读页面 `source_refs` 对应原文，保留核心事实、正式主体、文件名称、建设状态、任务强度、数字节点、责任、条件、边界以及来源明确作出的结论；不得用“建设内容、阶段进度、技术规则”等作者归纳维度替换原文中力度更强的政策动作、实施状态、明确目标和成果定位。多段文字继续采用观点先行和完整语义表达。`onscreen` 采用结论先行的金字塔表达：先给出页面完整结论，再以完整段落展开原因、事实和影响，可调整顺序、补足衔接句和重组段落，不得改变业务对象、动作、关系、状态、责任、数字、条件和结论力度；v2 lean 的 `source_refs` 仍表示本页可用证据范围。
- “短语化、条目化”不作为 Stage 01 的上屏生产目标。上屏保留完整文字稿的实质信息，用结论句和完整段落组织阅读顺序；页面密度过高时优先调整页面使命或分页，避免以删减事实换取篇幅。并列事实确有助于理解时可使用完整句式的并列段，关键限定、业务对象、动作、关系、责任、时间和数字必须保留。Stage 02 负责文字可读性、图像文字审计和最终页面 QA。
- 完整语义必须明确具体事项。子项只能继承同一可见模块直接声明的共同主语或动作，且标签必须明确语义角色；`full_copy` 的段落观点和 `onscreen.heading` 不得依赖页标题、上一段、相邻模块、上一页或读者猜测来补全业务对象。“国家已明确……”“项目将推进……”“研究形成成果”“后续开展工作”等表述必须写明具体部署、项目、研究成果或工作事项。
- 上屏语义完整性同时约束模块标题和明细行。普通内容模块标题必须表达完整判断；来源正式定义的分类、阶段或主体名称可以作为模块标题，其下必须说明该分类规范什么、该阶段实现什么或该主体承担什么。明细必须采用完整命题或“语义标签：语义完整的短语或说明”。明细可以继承同一可见模块直接声明的主语或动作，但必须保留关系、对象和必要限定。以“以、基于、围绕、结合、按照、通过、面向、依托、针对”开头的依据、条件、方式或范围表达必须在同一行补全业务动作或结果，不得形成悬空状语。确定性长度门禁属于生产约束，不是写作目标；超限时通过拆分语义角色、提升共同命题、调整页面使命或分页处理，不得截断关键对象、动作、关系、条件或限定。AUTHOR 逐页执行“锁定来源最强结论与保护信息—完整稿语义保全—上屏证据取舍—逐项语义闭合—来源力度与边界复核—整页重写”的内部闭环；该闭环不新增状态文件，确定性 lint 只负责发现可机械识别的缺陷。
- 所有新项目的 Deck Plan 均使用 v2 lean；profile 只决定 Foundation 的理解深度和来源保全方式，不决定页面规划合同。strict/legacy 继续保留 Source Truth、完整语义模型、逐事实核验和 `source_consumption_policy: required`，Deck Plan 只承担章节归并、页数分配、暂定标题、页面问题/使命和来源边界；核心判断、内容模块、证据取舍、上屏合同、视觉关系与讲述线索属于 AUTHOR 和 Final Script。v1 strict Deck Plan 仅供已有旧项目原位兼容，不得作为新项目默认模板。Stage 02 不读取 Deck Plan 文案。

来源章节与汇报章节必须分层。Foundation 保留来源章节身份、边界和顺序；
Deck Plan 默认把相邻来源章节按共同受众问题、论证角色和承接关系归并为汇报
章节，映射展开后必须覆盖全部来源章节且顺序一致。正式汇报优先控制在 4 个
汇报章节以内，默认不得超过 6 个；超过 6 个必须记录具体例外理由。多章节
汇报中每个汇报章节设置一页过渡页，页面序列为封面、目录、逐章过渡页与
内容页、封底。单章节规则继续适用。

Stage 01 的脚本规划与写作段只有三个权威内容产物（vendored engine's own AGENTS.md: "Only these are authoritative content artifacts"）：

1. `foundation.json`
2. `deck-plan.json`
3. `dist/final-script.md`

`dist/final-script.json` 是可选的机器可读镜像；`.cache/source-index.json` 与各类诊断报告都是派生产物，不构成第四个权威。

- 用户交互发生在对话中，不得为交互节点新增确认文件、状态 JSON、哈希、回执、attempt、manifest 或平行运行目录。
- 必须在两处停下并展示实际内容：**脚本规划待确认**（章节结构、页面分解、交流目标）；**最终脚本已生成**（`dist/final-script.md` 全文）。用户可在任一节点直接修改，收到输入后据此调整规划或脚本。
- `cyberppt-script lint`/`audit-foundation`/`audit-plan` 等确定性检查是写完之后的诊断，不是逐页写作前必须满足的阻塞门；不得据此把写作拆成"每页先 preflight 再写再 lint"的强制循环。
- 不得根据审计错误机械增加页面、上屏模块、锚点句或附件字段。来源覆盖只证明可追溯，不证明内容与页面使命直接相关。
- 继续使用项目现有 `source/`、`script/foundation.json`、`script/deck-plan.json` 和 `script/dist/` 路径；不得复制底稿或建立另一套事实源。

## 对话交付链接（硬规则）

- 当任何一个阶段或环节任务完成时，必须在当次最终回复中把该阶段或环节的实际产出物以可点击 Markdown 链接提交到屏幕上。
- 链接必须指向已经落盘的具体文件，并使用当前环境可打开的绝对路径；不得只写“已完成”、文件名、普通文本路径或目录路径，也不得让用户自行查找。
- 本轮新建、重新生成或更新的权威输入、正式成果、审计或 QA 报告及人工审阅稿必须逐项链接。一个环节没有文件产出时，必须明确写“本环节无文件产出”。
- 本规则只约束对话交付，不得据此新增确认文件、状态 JSON、哈希、回执、attempt、manifest、artifact ledger 或平行运行目录。

## 人工审核交付格式（仓库级硬规则）

- 面向用户审核的提纲、章节结构、页面内容、审计说明和 QA 结论，必须使用 Markdown 或其他可读文档格式交付；不得直接以 JSON 作为用户审核材料。
- JSON、YAML 或其他机器可读文件仍可作为内部权威产物、审计输入、流程交接和程序消费格式，但必须同步提供不依赖机器格式的人工审核稿。
- 人工审核稿应呈现实际章节、页面使命、核心判断、合并理由、风险和待确认事项，不得只提供文件路径或字段摘要。

## 成果物表达禁用规则（仓库级硬规则）

- 任何成果物材料不得使用“不是……而是……”及同构的否定转折表达，包括提纲、章节稿、页面脚本、讲稿、最终全稿、审计说明和 QA 文档。
- 表达对比关系时，改用直接陈述、并列陈述、因果陈述或条件陈述，确保结论、边界和判断依据清晰可读。
- 本规则针对成果物文本；对话中的必要规则说明、引用原文和错误信息复述可保留原始措辞，但不得将该句式写入成果物。

## 单章节结构规则（仓库级硬规则）

- 提纲只有一个章节时，不设置章节页；封面、目录之后直接进入内容页。
- 章节页仅用于多章节提纲的分隔、导航和章节定位，不得因模板或审计字段要求为单章节提纲额外增加章节页。

## 演讲者备注规则（仓库级硬规则）

- 演讲者备注必须使用演讲者现场讲解的完整语气，可直接朗读或自然转述。
- 演讲者备注不得出现“本页”“下一页”“上页”“页面设计”“审核稿”“制作提示”等制作过程用语。
- 页面之间的衔接应写成面向听众的自然过渡，例如“接下来重点看……”“在这个基础上，我们再看……”，不得写成页面编排说明。

## 代码与产物修改

- 修改应聚焦当前任务，保持克制，不进行无关重构、清理或格式化。
- 遵循现有架构、命名、风格、仓库命令和正式生产工作流，不另建平行实现路径。
- 保护已有代码、数据、生成产物以及用户尚未提交的改动。
- 不覆盖、不删除、不回退不属于当前任务的内容；工作区不干净时只处理任务相关文件。
- 优先修复根因，避免只掩盖症状；但不要借机扩大改动范围。
- 修改生成类或编译类逻辑时，应修复上游生成器并重新生成派生产物，避免只手工修补输出文件。
- 涉及审批、哈希、清单或锁定文件时，保持绑定关系有效；源文件变化后不得沿用失效的旧审批。

## Stage 02 断点续跑与双分支交付（硬规则）

- `final-script-pages` 是 Stage 02 生图、图片文字审计和 PPTX 组装的唯一正式编排入口。
- 每页图像生成或文字审计完成后必须立即写入当前批次 manifest；不得等整批结束后才集中保存回执。
- 单页失败只影响该页。再次运行同一 `build_id`、输出目录和生产参数时，必须复用图像存在且文字审计通过的页面，只补未通过页面。
- 恢复前必须核对最终脚本哈希、风格锁、页面范围、生产模式和组装模式；任一关键绑定变化时不得复用旧回执。
- 图片型 PPT、可编辑 PPT 和双份交付必须共享同一份逐页审计 manifest。只有请求范围内全部页面通过图像文字审计后，才能进入 `image`、`editable` 或 `both` 组装分支。
- `--force-images` 仅用于用户明确要求整批重绘的场景；普通重试和网络中断恢复不得使用该参数。
- 恢复命令必须保留生图、生产构建和组装分支参数，避免恢复后只生成图片而遗漏 PPTX 组装。

## 验证要求

- **运行任何 `python3 -m cyberppt ...`、`python3 -m pytest ...` 命令前，先确认用的是仓库自带的 `.venv/bin/python3`，不是系统全局 `python3`。** 全局环境缺少 `rapidocr-onnxruntime`、`jsonschema` 等 `pyproject.toml` 声明的依赖，图片生成、视觉结构校验等环节会静默降级或直接报错，且不一定在第一时间暴露——这个坑真实踩过一次，生图流程在缺依赖的环境下跑完却没做 OCR 文字核验和尺寸归一化。
- 不以“代码看起来正确”或“命令成功退出”作为完成标准。
- 运行与风险相匹配的测试，并尽可能验证真实产物、生产消费者和实际使用路径。
- 定向测试通过不等于端到端完成；需要时继续检查生成、消费、校验和交付链路。
- 区分本次修改导致的问题与项目原有问题，不为通过测试而掩盖既有失败。
- 无法完成验证时，明确说明未验证内容、原因及风险。
- 只有目标真实达成且必要验证通过后，才能宣称任务完成。

## 仓库级 Skills

- 本仓库可移植 Skills 的权威源位于 `.agents/skills/<skill-name>/`；从仓库目录启动 Codex 任务时直接发现并调用，不依赖个人目录安装。
- 仓库级 Skill 与个人目录存在同名副本时，以本仓库 `.agents/skills/` 版本为准；后续修改先更新仓库版本，避免两台电脑或两套副本漂移。
- 复制仓库到其他电脑后，应从仓库根目录或其子目录启动任务，并用 `codex debug prompt-input` 核验 Skill 的 source locator 指向当前仓库。
- 个人目录副本仅作为仓库外任务的兼容入口，不得作为本仓库工作流的唯一来源。

## 沟通方式

- 汇报关键发现、重要决策、风险、验证结果和最终产物。
- 长时间工作时提供简短且有信息量的进度更新。
- 不刷重复、空泛或仅描述工具操作的进度。
- 最终回复先说明结果，再补充必要的修改范围、验证证据和剩余事项。

<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

### 搜索门禁（硬规则）

- 任何需要定位、理解、排查或修改代码/文件的任务，自动使用
  `.agents/skills/graft-first-search/SKILL.md`；用户无需显式点名该 Skill。
- 在执行 `rg`、`grep`、`find`、`fd`，或为定位内容而直接读取源码前，必须先运行
  `graft ask "<任务或标识符>" --source`。即使已知文件路径，也不得绕过图谱。
- 仅当目标属于未索引文件、图谱明确提示没有命中，或返回的精确跨度仍不足以完成任务时，
  才能使用原始搜索或读取；范围必须收窄到该未索引文件或图谱给出的行号。

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
<!-- graft:end -->
