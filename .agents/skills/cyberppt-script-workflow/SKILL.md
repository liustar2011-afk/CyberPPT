---
name: cyberppt-script-workflow
description: Natural-language router for CyberPPT-Script. Generate or revise PPT scripts from formal source materials while preserving source chapter structure by default and allowing source-supported analytical deepening inside that structure. Never require the user to know internal stages, schemas, or CLI commands.
---

# CyberPPT Script Engine — Natural-Language Workflow

## 1. Routing principle

The source controls content boundary and default chapter order. The engine controls semantic understanding, analytical deepening, page decomposition and PPT expression.

Do not reply by asking the user to choose an internal stage when the route can be inferred from the request and current project artifacts.

Read:

1. `AGENTS.md`;
2. `docs/SOURCE_FIDELITY_AND_ANALYSIS.md`;
3. the stage Skill needed for the current route.

## 2. New source-to-script

Internal route:

`UNDERSTAND -> PLAN -> Gate A -> AUTHOR -> CRITIQUE -> REWRITE -> DELIVER`

Automatically:

1. scaffold `projects/<slug>/` and retain source files;
2. extract/index source structure when possible;
3. build a Foundation with atomic facts, explicit relations and supported inferred relations;
4. preserve source chapters by default and plan PPT pages within that structure;
5. present **脚本规划待确认**;
6. after ordinary approval language, author the complete script;
7. run Critic, rewrite, deterministic audits and delivery validation;
8. report **最终脚本已生成**.

For new planning work, PLAN writes `deck-plan.json` v2 lean in two passes,
optionally compares 2–3 source-constrained narrative candidates, and performs a
whole-plan Critic rewrite before the planning stop. AUTHOR writes the complete
page argument before selecting onscreen information; high-risk pages compare
judgment-led and evidence-led candidates and keep only the rewritten winner.
These are authoring passes inside the existing three authority artifacts. They
do not create a Content Plan, checkpoint, gate receipt or review manifest.

### AUTHOR execution model

`AUTHOR` is a generative agent stage. It is not a deterministic transformation
from `deck-plan.json` fields to Markdown, and it is not completed by passing a
schema, lint or source-coverage audit.

The author agent must read the document thesis and table of contents first,
then the target page's argument node, complete source prose, adjacent-page
contracts and approved evidence boundary. It independently decides what a
silent reader must understand, which facts deserve visible weight, how related
facts should be merged, how the page should be written, which business
relationship must become visually legible, and how the presenter should explain
the argument aloud. If the inherited
module grouping is semantically invalid, it returns to PLAN and repairs the
smallest affected page contract before writing.

Deterministic code runs only after the generative pass. Its role is to detect
source loss, proposition drift, unsupported relations, broken boundaries and
delivery-format defects. It must never create onscreen copy by abbreviating
source bullets, splitting one source sentence into cards, or filling one output
field from each PLAN field. It must not synthesize `visual_thesis` by copying the
core message or synthesize `speaker_notes` by concatenating module headings and
items. An audit result proves compliance with a bounded
contract; it does not prove authorship or reading quality.

For revisions, the author agent rewrites the page from its semantic brief. It
does not patch the previous onscreen copy line by line unless the user has
explicitly requested a literal wording correction.

## 3. Re-plan

Distinguish two cases.

### Expression / pagination re-plan

Examples:

- `重新做分页`
- `第3章页数太多`
- `这几节怎么合页更好`
- `整套PPT表达逻辑再优化`

Keep `source_structure_mode: preserve`. Re-plan page split/merge, chapter-internal logic, analysis model and page arguments.

### User-authorized source restructuring

Examples:

- `把合作机会提前到第二章`
- `重新安排五章顺序`
- `删掉建设背景，重点讲合作`

Set `source_structure_mode: user_authorized_restructure` and record `user_authorized_cross_chapter` only where the request requires it.

Do not infer restructuring permission merely from a request for a better PPT.

## 4. Continue

Identify the active project and run `cyberppt-script status projects/<slug>`. Resume from the next unresolved gate. Approval language after an approved plan authorizes whole-deck writing; never ask the user to say an internal stage name.

## 5. Targeted page edit

Read:

- target page and adjacent pages;
- corresponding deck-plan entry;
- `source_scope`;
- relevant Foundation facts/relations/boundaries;
- `analysis_basis` where present.

Preserve source chapter boundaries unless the requested edit explicitly authorizes a structural change.

## 6. Whole-deck review / rewrite

Run Critic + Rewrite against Foundation, plan and current script. Review source structure, inference boundary, analytical depth, group-claim strength, classification/progression, optionality, visibility, compression loss and formal register.

Do not expose Critic self-dialogue. Return only the rewritten result and a concise summary of material changes when useful.

## 7. Planning gate

Show a readable **脚本规划待确认** containing:

- source chapter structure to be preserved;
- planned page allocation by chapter;
- each page's question, core message and dominant analysis/logic when useful;
- split/merge decisions that materially change Word-to-PPT projection;
- inferred relationships or source conflicts that merit user attention;
- any restricted/internal material requiring an exposure decision.

Do not dump internal JSON by default.

Run `cyberppt-script review-plan <deck-plan.json> <foundation.json>` and present
its Markdown reading strip at this gate. The command is a derived review view and
must not create another authoritative artifact or approval state. For internal
and mixed audiences, apply the internal-expert voice check: enterprise operating
topics remain valid, while external-consultant address and viewpoint are rejected.

## 8. Stage 02 boundary and formal handoff

Stage 01 owns the three authoritative script artifacts:

- `script/foundation.json`;
- `script/deck-plan.json`;
- `script/dist/final-script.md`.

After the final script is locked, Stage 02 remains in the CyberPPT repository and
has one formal orchestration entry:

`.venv/bin/python3 -m cyberppt final-script-pages --production-build ...`

`final-script-pages` consumes the locked final script and the current Stage 02
handoff/visual contracts before running image generation, image-text audit and
the requested PPTX assembly branch. For high-fidelity editable reconstruction,
use `--production-mode image-to-editable-svg` with the registered `editable`
assembly branch; picture and dual delivery use the same orchestrator with their
declared assembly branch. Do not call a Stage 02 adapter directly or create a
parallel image/PPTX production route.

The Stage 01/Stage 02 boundary is the locked
`script/dist/final-script.md` plus its validated handoff. Visual production may
derive runtime prompts, manifests and QA records, but it must not rewrite the
three Stage 01 authority artifacts or become a second content authority.
