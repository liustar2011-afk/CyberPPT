# AGENTS.md

本文件适用于整个仓库。若子目录存在更具体的 `AGENTS.md`，则以更具体的规则为准。

## 工作原则

- 始终围绕用户目标和明确约束工作，不擅自扩大任务范围。
- 表达简洁、直接；明确区分已验证事实、合理推断和未知信息。
- 研究结论应基于可靠来源；优先使用仓库代码、项目产物、正式文档和一手资料。
- 仅在关键决策无法安全推断时提问；非关键细节采用合理假设继续推进，并说明重要假设。
- 复杂关系、流程或架构在确有帮助时使用表格、流程图或其他可视化表达。
- 子 Agent 只用于边界清晰、可独立执行且确有并行收益的任务；避免重复探索和无意义并行。

## 单人 Stage 01 交互与控制

- 单人单机生成脚本走仓库唯一的轻量 Stage 01 流程；仓库不提供哈希绑定的审批/升级/重试链。
- 用户交互发生在对话中，不得为交互节点新增确认文件、状态 JSON、哈希、回执、attempt、manifest 或平行运行目录。
- 必须在四处停下并展示实际内容：提出交流目标建议；提出章节和页面提纲；提出页面详细内容；提交最终全稿。交流目标节点必须先读取并分析源材料，提出一个忠于原稿且有源依据的方向；不得提供多个选项，不得把用户目标、作者推断或泛化措辞升级为源材料事实、源材料判断或页面主结论。用户可修改或补充该方向；不得直接向用户抛出受众、场景、目标行动等空白问题。前三处收到用户输入后直接修改现有权威提纲或页面脚本，第四处等待最终确认。
- 例外：用户明确授权并提供 `autonomous_lightweight` 任务合同时，可运行 `python -m cyberppt run-autonomous <contract.json>`，以命令的失败闭环门禁替代上述对话停点；不得把此例外用于跳过作者产物、全稿审计、Stage 02 handoff、视觉结构、实际送图提示词、图片或图片 QA。只有其 `run-report.json` 的 `status=completed` 才能对外称"完成"。
- 默认只做一次源登记核查、一次语义检查、一次 Source Truth 检查、一次 Outline 检查、写作期间按需局部检查和合稿后一次全稿检查。局部修改不得触发无关上游阶段或全稿的级联重审。
- Stage 01 采用"作者任务在前、规则质检在后"的正式工作方式。语义理解负责还原来源论证并完成原子事项与重要级别判断；Source Truth 是该作者判断的确定性事实投影；`compile-outline-draft` 只生成完整候选清单，不得直接作为正式提纲提交或通过人工门；必须调用仓库内 `cyberppt-author-stage01-outline` 完成页面使命、不可替代价值、主论证链、证据职责和不上屏取舍后，才运行一次 Outline 轻量审计。页面脚本使用 `cyberppt-write-single-page` 逐页专业编写，审计只作为来源、关系、层级和契约底线，不替代编辑判断。
- 不得根据审计错误机械增加页面、上屏模块、锚点句或附件字段。来源覆盖只证明可追溯，不证明内容与页面使命直接相关；附件登记字段、材料清单、操作表单和实施明细默认保留在完整稿、讲解或追溯层，只有直接决定页面判断时才可提升为页面结构。
- 继续使用项目现有 `source/`、Source Truth、Outline、章节脚本和最终脚本路径；不得复制底稿或建立另一套事实源。

## 对话交付链接（硬规则）

- 当任何一个阶段或环节任务完成时，必须在当次最终回复中把该阶段或环节的实际产出物以可点击 Markdown 链接提交到屏幕上。
- 链接必须指向已经落盘的具体文件，并使用当前环境可打开的绝对路径；不得只写“已完成”、文件名、普通文本路径或目录路径，也不得让用户自行查找。
- 本轮新建、重新生成或更新的权威输入、正式成果、审计或 QA 报告及人工审阅稿必须逐项链接。一个环节没有文件产出时，必须明确写“本环节无文件产出”。
- 本规则只约束对话交付，不得据此新增确认文件、状态 JSON、哈希、回执、attempt、manifest、artifact ledger 或平行运行目录。

## 代码与产物修改

- 修改应聚焦当前任务，保持克制，不进行无关重构、清理或格式化。
- 遵循现有架构、命名、风格、仓库命令和正式生产工作流，不另建平行实现路径。
- 保护已有代码、数据、生成产物以及用户尚未提交的改动。
- 不覆盖、不删除、不回退不属于当前任务的内容；工作区不干净时只处理任务相关文件。
- 优先修复根因，避免只掩盖症状；但不要借机扩大改动范围。
- 修改生成类或编译类逻辑时，应修复上游生成器并重新生成派生产物，避免只手工修补输出文件。
- 涉及审批、哈希、清单或锁定文件时，保持绑定关系有效；源文件变化后不得沿用失效的旧审批。

## 验证要求

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
