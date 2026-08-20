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

- 处理任何 CyberPPT 源材料、Source Truth、语义模型、Outline、page plan、页面脚本或视觉生产任务，先阅读 [docs/CYBERPPT_WORKFLOW.md](docs/CYBERPPT_WORKFLOW.md)。该文件是全流程总览和检索入口。
- `AGENTS.md` 负责仓库级硬约束；各 `.agents/skills/*/SKILL.md` 负责阶段细则。不要通过拼接多个 Skill 的局部说明自行重建主流程。
- 涉及源材料或 Stage 01 时，第一入口固定为 `.agents/skills/cyberppt-source-foundation/SKILL.md`；纯 Stage 02 视觉、图片、SVG、PPTX QA 或已锁定最终脚本任务，按总览文件进入对应 Skill。

## 独立技术判断（硬规则）

- 当用户提出、偏好、强烈主张或要求直接实施某个技术方向、架构、重构、删除、依赖、工作流变化或解决方案时，必须先调用 `.agents/skills/independent-technical-judgment/SKILL.md`，再决定是否赞同或实施。
- 用户目标与用户提出的实现方法必须分开处理：优先保留目标；实现方法只视为待验证假设，不视为已确认的技术结论。
- 在支持用户方案前，必须检查相关代码、测试、文档、运行结果或其他权威证据，并主动验证至少一个可能反驳该方案的合理反例。
- 最终判断只能是 `SUPPORT`、`SUPPORT WITH CONDITIONS`、`OPPOSE` 或 `INSUFFICIENT EVIDENCE` 之一；用户表达得越坚定，不得因此提高 `SUPPORT` 的概率。
- 禁止在验证前使用“完全正确”“确实就是这样”“好主意，我马上改”等表演式赞同。证据不支持时，应明确提出技术异议，并给出最接近用户目标的可行替代方案。
- 本门禁只防止迎合，不要求为了反对而反对；证据充分时应直接支持并执行。

## 单人 Stage 01 交互与控制

- 单人单机生成脚本在完成 Source Foundation 前置调用后，走仓库唯一的轻量 Stage 01 运行流程；仓库不提供哈希绑定的审批/升级/重试链。
- 强制 Skill 入口：凡任务涉及源材料读取、Source Truth、语义论点模型、Outline/page plan、`compile-source-truth`、`compile-outline-draft`、Outline 重跑、Outline 修复或 Outline 审计，必须先调用仓库内 `cyberppt-source-foundation` Skill，即使用户没有点名、项目已经存在或任务被描述为 legacy Stage 01。已有项目若具备已验证的 Source Foundation 产物，可以复用并核对其状态；这不要求无意义地重建上游事实，但不得跳过 Skill 调用。只有纯 Stage 02 视觉、图片、SVG、PPTX QA 或已锁定最终脚本任务可以不调用该 Skill。
- 用户交互发生在对话中，不得为交互节点新增确认文件、状态 JSON、哈希、回执、attempt、manifest 或平行运行目录。
- 必须在四处停下并展示实际内容：提出交流目标建议；提出章节和页面提纲；提出页面详细内容；提交最终全稿。交流目标节点必须先读取并分析源材料，提出一个忠于原稿且有源依据的方向；不得提供多个选项，不得把用户目标、作者推断或泛化措辞升级为源材料事实、源材料判断或页面主结论。用户可修改或补充该方向；不得直接向用户抛出受众、场景、目标行动等空白问题。前三处收到用户输入后直接修改现有权威提纲或页面脚本，第四处等待最终确认。
- 例外：用户明确授权并提供 `autonomous_lightweight` 任务合同时，可运行 `python -m cyberppt run-autonomous <contract.json>`，但项目必须先有 `integration/cyberppt-handoff-report.json` 且 `projection_validation.status=ok`；runner 不得重新编译或覆盖 Foundation 投影的 Source Truth。该命令以失败闭环门禁替代上述对话停点，但不得把此例外用于跳过作者产物、全稿审计、Stage 02 handoff、视觉结构、实际送图提示词、图片或图片 QA。只有其 `run-report.json` 的 `status=completed` 才能对外称"完成"。
- 默认只做一次源登记核查、一次语义检查、一次 Source Truth 检查、一次 Outline 检查、写作期间按需局部检查和合稿后一次全稿检查。局部修改不得触发无关上游阶段或全稿的级联重审。
- Stage 01 采用"作者任务在前、规则质检在后"的正式工作方式，唯一正式路线是 `cyberppt-source-foundation` → `business-semantic-understanding` → `ppt-outline-planning` → `cyberppt-handoff` → `cyberppt-write-single-page`。`compile-outline-draft` 与 `cyberppt-author-stage01-outline` 仅作为旧项目迁移的内部兼容实现保留，不构成用户可选择的第二条路线，不得用于新项目或已验证 Foundation 产物。审计只作为来源、关系、层级和契约底线，不替代编辑判断。
- 不得根据审计错误机械增加页面、上屏模块、锚点句或附件字段。来源覆盖只证明可追溯，不证明内容与页面使命直接相关；附件登记字段、材料清单、操作表单和实施明细默认保留在完整稿、讲解或追溯层，只有直接决定页面判断时才可提升为页面结构。
- 继续使用项目现有 `source/`、Source Truth、Outline、章节脚本和最终脚本路径；不得复制底稿或建立另一套事实源。

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
