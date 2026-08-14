---
name: ppt-script
description: Use when formal Chinese source materials, existing PPT scripts, or slide outlines need source interpretation, storyline and chapter planning, page-by-page script writing, quality evaluation, optimization, comparison, or visual-production handoff.
---

# PPT Script V3

## Overview

Use one traceable workflow to turn formal materials into internal-reporting PPT scripts. Preserve the existing project lifecycle, page templates, semantic-diagram rules, and Stage 2 image-generation handoff while enforcing source fidelity, chapter planning, weighted evaluation, and optimization regression checks.

Before execution, run `route`, `state`, and `context-pack` in `deep` mode for formal source materials. Read every file in `source/` as well as the generated `analysis/00-active-context.md`; the active context is a grounded working set, not a substitute for the sources. `context-pack` embeds repository methodology from `config/prompt-modules.yaml` → `methodology_references` (profile + stage `references/*.md`) into the「仓库方法论」section; do not skip those rules. New formal projects must generate `analysis/00-semantic-understanding.md` and pass `semantic-check` before building the Source Truth Map, then rerun `state` and `context-pack deep`. [Stage 1](system-prompt/stage1.md) and [Stage 2](system-prompt/stage2.md) are compact compatibility routers; `config/prompt-modules.yaml` selects the detailed modules required by the current stage.

The authoritative registry for page fields, density thresholds, semantic-diagram types, and render-strategy names is [`config/rules.yaml`](config/rules.yaml). Do not redefine these values elsewhere.

## Government and SOE formal reporting

New projects use `government-soe-formal` and must declare `report_subtype`, `decision_intent`, `audience_level`, and `project_phase` in `project.json`. Resolve these fields through `config/reporting-modes.yaml`; missing or unknown values are errors. Read the applicable `references/government-soe-*.md` rules and run `style-check` before final assembly. Profile files supplement, but never redefine, `config/rules.yaml`.

## Modes

Choose one explicit mode:

| Mode | Use |
|---|---|
| `source-interpret` | Interpret sources and build the Source Truth Map without writing slides |
| `script-from-source` | Build storyline, chapter plan, page plan, and complete page scripts from sources |
| `chapter-structure-review` | After a chapter’s pages exist: review intra-chapter flow, onscreen↔diagram isomorphism, cross-page redundancy; write `review/*-structure-review.md` then consume into page edits. See also `.agents/skills/chapter-structure-review/SKILL.md` (Codex/Cursor; markdown authority, not Cursor Canvas) |
| `evaluate-script` | Evaluate an existing script against source materials and the 100-point rubric |
| `optimize-script` | Revise an existing script while preserving source coverage, states, and boundaries |
| `compare-scripts` | Compare two script versions for coverage, unsupported claims, structure, and expression |
| `full-pipeline` | Run interpretation, planning, writing, evaluation, optimization, and traceability review |

## Mandatory hierarchy

The source-grounding prefix remains `源材料 → 全文语义理解 → Source Truth Map`; the complete editorial sequence is:

```text
全文语义理解 → Source Truth → 独立认知 → 语义规划合同
→ 总编独立判断 → 多结构竞争 → 总编结构裁决
→ 章节页面规划 → 总编提纲审稿 → 反方审稿 → 页面脚本
→ quality evaluation
→ optimization
→ traceability regression
→ Stage 2 visual handoff
```

Do not write pages directly from raw source paragraphs. Chapter planning is a required layer between storyline and page planning. A failed 总编闸门 overrides `plan-check` and must 阻断页面 generation. For gate-enabled projects, `new-page`, page approval, and `assemble` all enforce the same authority; `MERGE` and `REJECT` are not approvals.

### Human authoring hard stop (formal projects)

For `editorial_gate_required: true` projects, machine editorial approval is not enough to write pages:

1. After `EDITORIAL_APPROVED`, open and wait for human review of `decision/01-decision.md`, `outline/02-outline.md`, and `decision/02-expression-logic.md`.
2. The user must run fresh `approve` for `decision`, `outline`, and `expression` (SHA-bound). Only then may you run `new-page` or fill pages.
3. Before any page write, run `python scripts/project_manager.py authoring-check <project>` (or rely on `new-page`, which fails the same way).
4. After intentional human edits to decision/outline/contracts, run `python scripts/project_manager.py provenance-sync <project> [all|storyline|outline|red-team]` then re-run the matching `editorial-check`. Sync refreshes digests from `scripts/ppt_script/provenance_bindings.py` and by default auto-runs `context-pack` (disable with `PPT_SCRIPT_NO_AUTO_CONTEXT=1`). Do not hand-edit audit verdict fields.
5. For formal projects, `plan-check` blocks conclusion-first openings. `approve expression` requires a PASS `outline/02-plan-audit.json` whose `outline_sha256` matches the current outline.
6. Never bypass `new-page` by creating or editing `pages/*.md` with file-write tools. Retire drafts with `retire-page` into `archive/obsolete-pages/`; `pages-check` warns if `_obsolete*` remain under `pages/`.
7. In `interaction_mode: gated`, stop at every major gate; do not enter page authoring without explicit user approval. `authoring-check` / `new-page` also fail when `00-active-context.json` artifact digests are stale.
8. Editing decision/outline/expression invalidates the matching approval until re-approved.

## Five quality gates

1. **源材料理解闸门** — source type, state, subject, numbers, dates, conditions, conflicts, and boundaries are represented accurately.
2. **认知增强闸门** — two isolated readings, reconciliation, claim confidence, counter-evidence, and evidence-graph traceability are complete.
3. **故事线、章节与页面规划闸门** — the deck storyline, chapter contracts, page contracts, and P0/P1 allocation are complete.
4. **逐页脚本编写闸门** — each page has one mission, a supported conclusion, suitable on-slide text, and executable visual logic. After each page batch, run `quality-check` (see On-slide writing checks).
5. **优化后追溯回归闸门** — P0 coverage remains 100%, P1 coverage does not decline, boundaries remain intact, and no unsupported numbers or core claims are added.

A failed gate overrides the weighted score. Do not label a script execution-ready while any gate fails.

## On-slide writing checks

Authority remains [`config/rules.yaml`](config/rules.yaml), including **`page_composition`** (each page’s content zones, module band, count alignment, anti-repeat). Run:

```bash
python3 scripts/project_manager.py quality-check <project>
```

Hard rules when filling `上屏文字` (ERROR blocks `quality-check`):

- **Reading-autonomous on-screen text.** Viewers must understand this page’s intent, module relations, and key facts by reading alone (`onscreen_text.reading_autonomous`). Speaker notes may expand orally, chart reading, and boundaries—they must **not** carry a thesis, causal chain, or contrast that is missing from on-screen text.
- **No process, self-talk, self-explanation, or backend meta on screen.** Forbidden examples include `正式引用前核验`, `待核验`, `须核验`, `仅后台`, `逻辑顺序`, `非并列`, `阅读路径`, `内容关系`, `论证组织`, `材料把`, `这里按`, `按这个结构`, `供审稿`, `写作说明`, plus the full list in `rules.yaml`. Put those only in backend fields or speaker-note boundaries. Business status words like `待审定` / `拟建` may stay on screen.
- **Content pages default to `落图策略建议：高密度专项`.** Fully use source论点 / 论证 / 论据 (subjects, mechanisms, rules, boundaries, numbers). Do not ship skeleton module titles. Meet `density_levels.high` floors and stay within max. `new-page` scaffolds this single value; never leave `标准 / 高密度专项 / …` placeholders.
- If `落图策略建议` is `高密度专项` or `超高密度专项`, on-screen text must meet the bound `density_levels` floor (`min_chars` / `min_modules`) and stay within the page-type / density max.
- **Composition ceiling:** content pages use 2–5 business modules (default ≤3); more than 5 is ERROR except `超高密度专项`. Module relation must be readable from on-screen titles and subtitle, not only from backend drawing notes.
- **Count isomorphism:** if backend/`页面形态` claims `N项/N类`, on-screen must have N modules (or N circled markers, or subtitle short labels joined by `·`/`、`). Writing only the words `五项`/`四类` in the subtitle does **not** count.

WARN (does not fail the gate, but fix before handoff):

- When `推荐主语义图类型` is `路径型`, on-screen text must carry order signals such as `①②③`, `→`, or `随之`. Avoid parallelizing module titles like `同步变化` / `三项并列` that contradict a path diagram.
- Backend claims of `N项/N类` that do not match on-screen module count; ≥4 equal-weight modules without hierarchy signals; intra-page / adjacent-page onscreen overlap; subtitle and 主判断 both filled.
- **Composition hygiene (WARN):** auxiliary zone over `page_composition.auxiliary.max_chars`; unlabeled blocks after ①②③ before 辅助区; module title tautology with first bullet; module-body overlap; stale visual interface claiming 主判断 when empty; cross-page fingerprints (追溯五问 / 闭环链路) expanded on multiple pages.
- After speaker notes: the core deliverable is `生图提示词` + on-screen whitelist for image models. Prompt = layout/hierarchy/arrows/bans only; force verbatim whitelist text; never invent on-screen labels. Keep review fields and gate lines (`页面类型` / `推荐主语义图类型` / `落图策略建议`) off the prompt.
- Content pages that still declare `落图策略建议：标准` without a thin-content reason should be raised to high density.
- Missing required backend `page_fields` (mission, conclusion, source IDs, relations, etc.).

## Source Truth Map

Every formal source-based task uses `full` Source Truth mode with unified `S###` IDs. Legacy `lite` projects remain readable, but new formal projects classify items as:

- `F` fact
- `P` policy requirement
- `J` judgment
- `I` inference
- `R` recommendation
- `B` boundary or condition
- `U` unresolved item

Record importance `P0/P1/P2`, state, subject, content, number/time, condition/boundary, exact source location, and conflict/unresolved note. Keep legacy `F01` references readable, but use `S###` for all new work.

## Cognitive enhancement

New formal projects use `cognitive_mode: enhanced`. After the source-understanding gate and Source Truth Map, complete two isolated readings before storyline planning:

1. `faithful` reading records only what the sources explicitly state, including structure, subjects, states, boundaries, conflicts, and prohibited inferences.
2. `decision` reading identifies the decision required from the audience, the main tension, decision-relevant content, compressible content, research gaps, and counterarguments.
3. `reconcile` compares both readings against the sources, resolves genuine conflicts, records shared gaps, and defines the final core proposition.
4. `contracts/evidence-graph.json` records each claim, supporting and counter sources, conditions, confidence, decision relevance, claim relations, and page links.

Use separate context files generated by `cognitive-pack`. A faithful-reading context must never contain the decision reading, and a decision-reading context must never contain the faithful reading. Historical cases are excluded from both independent readings. Only after `cognitive-check` passes may a new enhanced project advance to storyline planning.

Confidence values are limited to `confirmed`, `strong-inference`, `weak-inference`, `unverified`, and `conflicted`. Inference and historical experience never become current-project source facts.

## Experience enhancement

New projects use `experience_mode: enabled`. Historical cases are retrieved only after the cognitive gate; faithful and decision readings remain isolated from the case library. Run `experience-pack` before storyline or page work when approved cases are available.

Only cases with `status: approved` enter the index. Every case records the original output, accepted revision, reasons, applicable conditions, do-not-apply conditions, positive patterns, and anti-patterns. Search combines task type, audience, report subtype, issue type, tags, and text similarity, and penalizes matched negative scope.

The generated `analysis/00-experience-context.md` is reference-only. It may guide method and structure, but it may not create `S###` IDs, supply project facts, prove current capabilities, or override the current source materials and evidence graph. Use `case-capture` only after human approval.

## Chapter and page contracts

Every chapter records:

- chapter mission
- chapter conclusion
- input Source IDs
- page range
- previous-chapter link
- next-chapter link
- content boundary

Every substantive page records:

- page mission
- key message
- Source IDs
- page type
- visual form
- previous-page relationship
- next-page relationship
- page necessity
- structured speaker notes: opening bridge, core explanation, emphasis, boundary, transition, and estimated duration

Use `templates/full-page.md` for substantive pages and `templates/simple-page.md` only for cover, contents, chapter transition, and closing pages.

Before drafting pages, read [Script writing protocol](references/script-writing.md).

## 100-point evaluation

| Dimension | Points |
|---|---:|
| Source understanding, factual accuracy, and coverage | 30 |
| Storyline and chapter logic | 15 |
| Page mission, necessity, and one-message discipline | 15 |
| In-page reasoning and evidence | 10 |
| Audience and decision alignment | 8 |
| On-slide expression and density | 10 |
| Visual translation feasibility | 7 |
| Terminology, formatting, and compliance consistency | 5 |

Use `references/evaluation-framework.md` and `references/quality-gates.md` for semantic judgment. Deterministic reports are evidence, not the final score.

## Project workflow

Initialize:

```bash
python3 scripts/project_manager.py init <project>
```

Store sources in `projects/<project>/source/`. The project contains:

```text
analysis/00-analysis.md
analysis/00-semantic-understanding.md
analysis/01-source-truth-map.md
decision/01-decision.md
outline/02-outline.md
outline/02-plan-audit.md
pages/pXX-title.md
review/04-review.md
review/05-evaluation.md
review/05-machine-audit.md
comparison/
output/
```

Run deterministic checks:

```bash
python3 scripts/project_manager.py route <project>
python3 scripts/project_manager.py state <project>
python3 scripts/project_manager.py context-pack <project> deep
python3 scripts/project_manager.py source-inventory <project>
python3 scripts/project_manager.py semantic-check <project>
python3 scripts/project_manager.py understanding-check <project>
python3 scripts/project_manager.py cognitive-init <project>
python3 scripts/project_manager.py cognitive-pack <project> faithful
python3 scripts/project_manager.py cognitive-pack <project> decision
python3 scripts/project_manager.py cognitive-pack <project> reconcile
python3 scripts/project_manager.py cognitive-check <project>
python3 scripts/project_manager.py evidence-check <project>
python3 scripts/project_manager.py trace-claim <project> <C###>
python3 scripts/project_manager.py case-index
python3 scripts/project_manager.py case-search <query> [limit]
python3 scripts/project_manager.py experience-pack <project> [limit]
python3 scripts/project_manager.py case-capture <project>
python3 scripts/project_manager.py contract-check <project>
python3 scripts/project_manager.py editorial-init <project>
python3 scripts/project_manager.py editorial-pack <project> <semantic-planning|independent|storyline-candidates|storyline|outline|red-team|red-team-response>
python3 scripts/project_manager.py editorial-check <project> <semantic-planning|independent|storyline-candidates|storyline|outline|red-team-review|red-team>
python3 scripts/project_manager.py plan-check <project>
python3 scripts/project_manager.py audit <project>
python3 scripts/project_manager.py notes-check <project>
python3 scripts/project_manager.py quality-check <project>
python3 scripts/project_manager.py style-check <project>
python3 scripts/project_manager.py compare <project> <original.md> <revised.md>
python3 scripts/project_manager.py approve <project> <analysis|truth|decision|outline|expression|evaluation|review|pXX> [note]
python3 scripts/project_manager.py authoring-check <project>
python3 scripts/project_manager.py pages-check <project>
python3 scripts/project_manager.py retire-page <project> <page-file-or-stem>
python3 scripts/project_manager.py handoff <project> <decision|expression|outline|authoring|pages>
python3 scripts/project_manager.py provenance-sync <project> [storyline|outline|red-team-review|red-team|all]
```

Existing commands remain valid: `status`, `new-page`, `assemble`, `rhythm-check`, `custom-types`, `check-coverage`, `evidence-usage`, `gap-summary`, `approve`, `authoring-check`, `pages-check`, `retire-page`, `handoff`, and `provenance-sync`.

## Interaction modes

Read `project.json`:

- `interaction_mode: gated` — pause at each major gate and page batch; do not enter page authoring until the user has explicitly approved decision, outline, and expression.
- `interaction_mode: batch` — proceed in batches after the outline is approved.
- `batch_pages` — default `3`.
- `source_truth_mode: full` for new formal projects; legacy `lite` remains readable.
- `context_mode: deep|compact` — `deep` is the formal-material default; `compact` is explicit opt-in after source grounding.
- `semantic_gate_required: true` — requires whole-document business semantics before Source Truth generation.
- `understanding_gate_required: true` — prevents shallow analysis from advancing to storyline planning.
- `cognitive_gate_required: true` — requires isolated readings, reconciliation, and an evidence graph before storyline planning.
- `experience_mode: enabled|disabled` — retrieves approved method cases only after cognition; cases never become source facts.
- `editorial_gate_required: true` — activates the authoring sequence and blocks `new-page`, page approval, and `assemble` until final editorial approval, required validation, and fresh human `approve` for `decision` / `outline` / `expression`.
- `editorial_auto_rework_limit` — records unique manual/external rework attempts and escalates to user decision at the limit; it does not imply an internal model executor.

Do not pause after every page when `batch_pages` is greater than one. Do not bypass approval of the Source Truth Map or chapter/page plan in `gated` mode. Do not write `pages/` until `authoring-check` passes.

## Stage deliverable handoff (hard rule)

**After finishing any stage of work, the reply MUST present current deliverables as clickable links, including a link that opens the containing folder. A stage without links is incomplete delivery.**

Triggers include: workflow stage done, gate check done, human-review pause, page batch written/revised, or user saying “继续” when new/updated project files exist.

Required every time:

1. Run `python scripts/project_manager.py handoff <project> <decision|expression|outline|authoring|pages>`. This prints `file:///` links only; it does **not** open the OS file manager by default. Use `--reveal` or `PPT_SCRIPT_HANDOFF_REVEAL=1` only when the user asks to open the folder.
2. In the reply body, list Markdown links for **打开目录** (folder URL) plus key files, grouped by stage, with PASS/FAIL/pending. Do not auto-open Explorer/Finder.
3. Open key files in the editor when possible.

Forbidden: “done, see folder X” with no links; relative paths only; file links without a folder link; asking the user to Ctrl+P or hunt directories.

Contracts, audit reports, decision/outline/expression docs, page scripts, editorial traces, and quality-gate reports all count as deliverables. Run `pages-check` when page files exist: active `pages/pNN-*.md` must align with `page-contracts`; retire obsolete drafts to `archive/obsolete-pages/` via `retire-page`. Applies for both Codex and Cursor.

## Final outputs

`assemble` continues to produce:

- `output/script-final.md` — complete review and traceability version
- `output/script-imagegen.md` — visual-composition review version
- `output/script-imagegen-compact.md` — compact Stage 2 input
- `output/outline-index.json` — machine-readable page index
- `output/script-speaker-notes.md` — complete speaker-notes manuscript
- `output/speaker-notes.json` — structured notes payload for downstream PPT notes insertion

Speaker notes must never enter either image-generation output.

Every substantive page must have one core conclusion and one visual center that directly carries it. Keep detailed field names in `config/rules.yaml`; Stage 1 defines planning and split conditions, while Stage 2 defines visual execution and acceptance. Assembly must preserve the existing natural-language image-generation prompt style rather than emit a control-field list.

For `evaluate-script`, `optimize-script`, and `compare-scripts`, also preserve the machine report, 100-point semantic evaluation, gate verdicts, revision log, and final traceability result.

## Non-negotiable constraints

- **No conclusion-first for government / SOE / association internal reporting.** Consulting patterns (thesis-first, framework-first, claim-then-evidence, opening “direction/methodology/N-dimension” pages) are forbidden. Renaming the page or rewriting the same claim as a question does not fix it. Use work order: facts and situation → foundation and gaps → overall approach → tasks and path → safeguards → decisions requested. Judgments come only after facts and conditions.
- Never use the Chinese contrast pattern “不是……而是……” (including variants such as “并非……而是……”) in any project artifact: analysis, contracts, editorial outputs, decisions, outlines, page scripts, speaker notes, evaluations, assembled outputs, or human-readable traces. State the affirmative claim directly.
- Do not treat `analysis/00-active-context.md` as a replacement for source reading; verify conclusions against `source/` throughout Stage 1.
- Do not unload source interpretation after the Source Truth Map is created; keep checking cross-section evidence, states, subjects, and boundaries during storyline and page work.
- Do not silently change organization names, policy names, numbers, amounts, dates, responsibilities, product names, states, or compliance boundaries.
- Do not convert planned, proposed, exploratory, or conditional work into completed work.
- Do not present inference or external supplementation as source fact.
- Do not use historical cases as current-project facts, Source IDs, capability proof, or a substitute for source reading.
- Do not replace a clear formal-material structure with a generic consulting framework.
- Keep backend fields out of on-slide text. Never put `正式引用前核验` / `待核验` / `须核验` style verification meta on screen.
- Do not create an `注释文字` field inside `上屏文字`; place visible constraints in body/auxiliary text and review-only notes in backend boundary fields.
- For `路径型` pages, nail module order on screen; for `高密度专项` / `超高密度专项`, meet density floors in `config/rules.yaml`.
- Do not expose generic `模块一/模块二/模块三/模块1` prefixes in on-slide text; use the actual business heading directly.
- Strip page-contract labels such as `标题`, `副标题`, `主判断`, and `辅助区` from image-generation text whitelists; preserve only their actual content.
- Do not emit manual submission, copy/paste, batching, or workflow-orchestration instructions in assembled image-generation artifacts; downstream workflows own dispatch.
- Do not hard-code a canvas aspect ratio or pixel size in page scripts or image-generation handoff; defer canvas settings to the production environment or caller.
- Keep one primary message per page.
- Preserve the existing Stage 2 semantic-diagram and visual-translation interface.

## Role isolation (no multi-agent runtime required)

This repository uses **role-separated prompt modules and isolated context files**, not a multi-agent launcher. Enforce isolation in execution:

1. **Cognitive dual reading** — complete `faithful` and `decision` readings in separate passes (separate `cognitive-pack` / context files). Do not read the other reading’s result before finishing the current one.
2. **Editorial red team** — run red-team review as its own pass after outline approval; do not silently rewrite the deck while “reviewing.”
3. **Experience / editorial cases** — load only `approved` method cases; never promote them into Source IDs or current-project facts.
4. Platforms that can spawn subagents may map faithful vs decision (or author vs red-team) onto separate agents; the contract remains the same isolated artifacts under `analysis/readings/` and `analysis/editorial/`.

### Chapter / structure Canvas consumption

When a chapter structure review is needed (mode `chapter-structure-review` or user asks for 章结构审阅):

1. **Authority skill:** `.agents/skills/chapter-structure-review/SKILL.md` + template `templates/chapter-structure-review.md`.
2. **Always write** `projects/<name>/review/NN-*-structure-review.md` first (Codex and Cursor).
3. Diff recommendations against current `pages/` + expression logic; write `review/*-structure-consume.md`.
4. Apply page edits (onscreen + image prompt) in priority order; re-run `notes-check` / `quality-check`.
5. **Cursor only (optional):** after the markdown exists, a Canvas may visualize the same content; Canvas must not replace the markdown and never enters `assemble`.

Do not treat Cursor Canvas as the Codex deliverable.

## Skill entrypoint authority

Canonical Skill text lives at `.agents/skills/ppt-script/SKILL.md`. Root `SKILL.md` and `.claude/skills/ppt-script/SKILL.md` must stay in sync via:

```bash
python3 scripts/sync_skill_entrypoints.py
python3 scripts/sync_skill_entrypoints.py --check
```

Do not edit only one copy. `install.sh` installs the canonical ppt-script Skill (with root-relative links) and the companion `chapter-structure-review` Skill into Codex/Claude skill directories.
