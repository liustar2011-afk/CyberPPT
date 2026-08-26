# CyberPPT project workflow override

This file applies to `projects/**` and describes the current source-material-to-PPT route for work under this directory.

## Default source-material route

**Understand** (unchanged, mandatory first step for any task reading source material or creating/regenerating/repairing/auditing Source Truth or the semantic argument model):

1. `cyberppt-source-foundation` — source extraction, chapter structure, `source-truth.json`.
2. `business-semantic-understanding` — whole-document semantic argument model.

This is mandatory even for existing projects or a task described as legacy Stage 01.

**Plan and author** (vendored `script_engine`, replaces the old `ppt-outline-planning` → `cyberppt-handoff` → `cyberppt-write-single-page` route):

3. `python -m cyberppt project-foundation <project>` — mechanical projection of the validated Source Truth into `script/foundation.json`; adds nothing the Source Truth did not already establish.
4. `.agents/skills/cyberppt-script-workflow/SKILL.md` — `UNDERSTAND -> PLAN -> AUTHOR -> CRITIQUE -> REWRITE -> DELIVER`, producing `script/deck-plan.json` and `script/dist/final-script.md`.
5. existing Stage 02 pipeline (`prepare-stage02-handoff`, image/SVG/PPTX).

### Canonical route

The only formal route is `cyberppt-source-foundation` → `business-semantic-understanding` → `project-foundation` → `cyberppt-script-workflow` (PLAN/AUTHOR).

## Default writing and structure policy

默认采用政府公文式、央企正式交流语体，默认按源材料内容写作并保留章节标题、内容标题和先后顺序。只允许因 PPT 单页容量进行连续拆页，或在不改变主题归属、事实强度、责任、条件、状态和源顺序的前提下合并重复内容。

不得自行增加"问题路径""交流路径"、咨询式金句、营销标题或源材料没有的章节逻辑。目录使用源材料目录标题，源材料没有明确目录标题时使用"目录"。只有用户明确要求重构叙事、咨询化、路演化、改名、重排或压缩重组时，才可解除默认锁定；一般的领导汇报、合作交流或高端交流用途不构成重构授权。

For an existing project with approved source-foundation outputs, reuse and validate those outputs before downstream work; do not rebuild them merely to satisfy the invocation.

## Authority

Three authoritative content artifacts for the plan/author segment: `script/foundation.json`, `script/deck-plan.json`, `script/dist/final-script.md`. `script/dist/final-script.json` is an optional machine-readable mirror; `script/.cache/source-index.json` and diagnostic reports are derived, non-authoritative.

## Human gates

Two conversational gates: **脚本规划待确认** (deck plan — chapter structure, page decomposition, communication goal) and **最终脚本已生成** (the full `final-script.md`). `cyberppt-script lint`/`audit-foundation`/`audit-plan` run after writing as diagnostics; they are not a per-page blocking precondition.
