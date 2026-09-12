---
name: cyberppt-script-workflow
description: Natural-language router for CyberPPT-Script. Generate or revise PPT scripts from formal source materials while preserving source chapter structure by default and allowing source-supported analytical deepening inside that structure. Never require the user to know internal stages, schemas, or CLI commands.
---

# CyberPPT Script Engine — Natural-Language Workflow

## 1. Routing principle

The source controls viewpoints, content boundary and default chapter order. The
engine controls semantic understanding, page decomposition and PPT expression.
Default to source-faithful pagination (`authoring_mode: faithful`). Use analytical
deepening (`authoring_mode: analytical`) only when the user explicitly asks for
analysis, insight, argument reconstruction or strategic deepening.
Do not reply by asking the user to choose an internal stage when the route can
be inferred from the request and current project artifacts.

Read:

1. `AGENTS.md`;
2. `docs/SOURCE_FIDELITY_AND_ANALYSIS.md`;
3. the stage Skill needed for the current route.

### Mandatory mode-specific authoring reference

Before `AUTHOR`, `CRITIQUE`, `REWRITE`, targeted page revision or whole-deck
script review, resolve the approved `authoring_mode` first. Absence means
`faithful`.

- `faithful`: read
  [`references/faithful-authoring-contract.md`](references/faithful-authoring-contract.md)
  completely;
- `analytical`: read
  [`references/authoring-contract.md`](references/authoring-contract.md)
  completely.

Exactly one mode-specific contract is operational for each action. Do not blend
the analytical judgment-first methods into faithful authoring. The local
`AGENTS.md` defines this mode-specific specialization; repository-level
`AGENTS.md` retains all other hard constraints.

### Current Final Script authoring contract

New AUTHOR output uses **Final Script 1.2**. For a content page, Stage 01 authors
`full_copy + fidelity_text` and does **not** author `onscreen`.

- `full_copy` is the complete semantic manuscript for the page.
- `fidelity_text` contains only the small set of exact literals whose wording must
  remain exact when rendered; each item declares `required` or `if_rendered`.
- Stage 02 derives runtime `onscreen_text` from `full_copy` for internal scripts
  and may select, rewrite, merge, shorten, split and reorder ordinary content.
- Stage 02 carries `fidelity_text` on a separate exact-copy path. Ordinary
  `full_copy` wording never becomes exact-copy authority merely because it is
  visible in a prompt.
- Final Script 1.0/1.1 remains read-compatible for existing projects, including
  their authored `onscreen`, but new authoring and substantive rewrites target
  1.2 unless an existing project must remain on its legacy contract.

## 2. New source-to-script

Internal route:

`UNDERSTAND -> PLAN -> Gate A -> AUTHOR -> CRITIQUE -> REWRITE -> DELIVER`

Automatically:

1. scaffold `projects/<slug>/` and retain source files;
2. extract and index source structure;
3. build a lightweight Foundation with source structure, facts, explicit relations and boundaries once per deck;
4. preserve source chapters and plan PPT pages within that structure;
5. present **脚本规划待确认**;
6. after ordinary approval, resolve `authoring_mode` and execute the matching mandatory authoring reference;
7. for each faithful `script`-profile page, require a current `cyberppt.source_index.v2`, generate the derived `page-source` packet, and pass Author Preflight before drafting; missing, stale, invalid or partially resolved exact-source evidence blocks AUTHOR;
8. author Final Script 1.2 `full_copy + fidelity_text`, then run Critic, rewrite, deterministic audits and delivery validation;
9. report **最终脚本已生成**.

For every new project, PLAN writes a v2 lean `deck-plan.json` containing deck
purpose, chapter grouping, page allocation, tentative topic titles, page
questions, missions and source boundaries. The Foundation profile remains
independent: strict/legacy keeps Source Truth and its stronger source-fidelity
surface, while `script` uses the lightweight UNDERSTAND route. Neither route
pre-authors judgments, modules, evidence dispositions, visible-copy contracts,
visual relations or speaker threads in PLAN. v1 strict Deck Plans must be
migrated to v2 lean before entering this workflow.

### Faithful AUTHOR

#### Mission and judgment ownership

PLAN writes a concrete mission for every content page in the existing `logic`
field: the business scope, the page's communication duty and its distinction from
adjacent pages. Do not introduce a second PLAN `mission` field or pre-author a
`core_message`. The page-source packet carries `page_mission` as a disposable copy
of `logic` so AUTHOR reads the mission together with exact evidence.

During AUTHOR, check that `full_copy` actually fulfils this mission. A Final
Script `mission`, when supplied, is a review-only restatement of PLAN `logic`;
repair PLAN first if the page duty changes. A wording difference is a review hint,
not proof of a semantic conflict. Do not copy the mission into `full_copy` or
`fidelity_text` unless it is independently supported source content.

After reviewing source meaning and `full_copy`, choose the faithful judgment form:
one source-supported main judgment may use optional `core_message`; multiple
parallel judgments stay in their source order within `full_copy`; a definition,
classification or task list may omit a page-wide judgment. Do not add a synthetic
conclusion to fill a field. Presence of `core_message` alone does not authorize
analytical or argument-led writing. CRITIQUE reviews mission fulfilment separately
from judgment support, qualifiers and strength.

#### Faithful full copy and fidelity selection

`faithful` is source-native editorial transduction. AUTHOR writes `full_copy` as
the complete page-ready manuscript from the source-native structure. Stage 01 then
extracts only narrow `fidelity_text`; it does not create a separate visible-copy
projection for Final Script 1.2.

Before writing a faithful content page, resolve the exact evidence for that page.
For the default `script` profile, `script/.cache/source-index.json` must be a current
`cyberppt.source_index.v2` file. Missing, stale or invalid source index state blocks
AUTHOR; do not fall back to Foundation previews or remembered source text. Run:

```bash
.venv/bin/python3 -m script_engine.cli page-source \
  script/deck-plan.json \
  script/foundation.json \
  <PAGE_ID> \
  --source-index script/.cache/source-index.json \
  --output script/.cache/page-source/<PAGE_ID>.json
```

After all required page packets are current, run `author-preflight` and require a
passed project/page state before drafting or materially rewriting content. Read the
packet before drafting. It is disposable `derived_runtime_context`, not a new content
authority. Missing, stale, invalid, partially resolved or blocked exact-source evidence
stops the action. Regenerate the packet and Preflight whenever the page source refs,
Foundation or source index changes.

A faithful page may legitimately contain a definition, parallel facts, parallel
tasks, a taxonomy, explicit stages, status statements or responsibilities without
an author-created total conclusion. Do not manufacture a conclusion, argument
chain, causality, necessity, implication, mechanism, capability, value judgment,
closed loop or progression merely to satisfy a presentation framework.

`full_copy` preserves every material fact, condition, responsibility, formal
instrument, number, date, status, boundary, claim strength and source-explicit
relationship. Dense material is handled by page-scope or pagination repair, not by
silently deleting substantive content in Stage 01.

After `full_copy` passes Source Fidelity Critic, extract `fidelity_text` conservatively:

- exact numbers with the minimum context or unit needed to identify them;
- official names of policies, plans, standards, institutions, products, models or
  user-designated fixed strings that must retain exact wording;
- `required` only when the literal must be visible on the generated page;
- `if_rendered` when the model may omit the literal but must spell it exactly if used.

Do not put ordinary conclusions, paragraphs, labels or stylistic wording into
`fidelity_text`. Each literal must be traceable to `full_copy` or an explicit
user-provided fixed-string authority. Keep the field narrow enough to avoid turning
Stage 02 back into full-text exact-copy rendering.

### Analytical AUTHOR

Only when `authoring_mode: analytical` is explicitly approved may AUTHOR use the
analytical contract to write a `core_message`, argument topology, source-supported
inferred relationships and judgment-led `full_copy`. It then extracts the same
narrow `fidelity_text` contract. Final Script 1.2 analytical AUTHOR also does not
author `onscreen`; Stage 02 performs the visible-copy rewrite from the approved
`full_copy`. Analytical mode remains source-bounded and cannot introduce new facts,
commitments, numbers or speculative relationships.

### Shared AUTHOR execution

Stage 01 uses neither blind mechanical shortening nor uncontrolled phrase-led
condensation. It establishes the complete semantic manuscript and the exact literals
that truly require fidelity. Stage 02 owns visual copy selection and rewriting.

The current main agent is the AUTHOR executor. There is no separate AUTHOR Skill,
CLI, deterministic generator or project-specific author script. The `page-source`
CLI only resolves exact evidence; it does not author prose. Loading this router,
creating schema-valid output, generating a page-source packet or passing lint does
not execute AUTHOR.

Every deck defaults to `deck.delivery_mode: self_read`. Use `presented` only when
the user explicitly requests a presenter-led sparse deck.

## 3. Re-plan

### Expression or pagination re-plan

Requests such as `重新做分页`, `第3章页数太多` or `整套PPT表达逻辑再优化`
keep `source_structure_mode: preserve`. Re-plan page split or merge and
chapter-internal pagination. In faithful mode, do not turn the re-plan into a new
argument or analytical thesis. In analytical mode, approved page questions and
arguments may be re-planned inside the source boundary.

### User-authorized source restructuring

Requests such as `把合作机会提前到第二章`, `重新安排五章顺序` or
`删掉建设背景，重点讲合作` use
`source_structure_mode: user_authorized_restructure` and record
`user_authorized_cross_chapter` only where required. A request for a better PPT
does not by itself authorize source restructuring.

## 4. Continue

Identify the active project and run `cyberppt-script status projects/<slug>`.
Resume from the next unresolved gate. Approval language after an approved plan
authorizes whole-deck writing; do not ask the user to name an internal stage.

## 5. Targeted page edit

Resolve the page/deck `authoring_mode` and read only the matching mandatory
authoring reference. Then read the target page and adjacent pages, matching Deck
Plan entry, `source_refs`, relevant Foundation records and exact page source text.
In faithful `script` mode, require the current v2 source index, regenerate the target
page's `page-source` packet, and rebuild Author Preflight before editing so the revision
uses current exact source units. Missing, stale, invalid or blocked exact-source state
stops the edit instead of falling back to previews or memory. Preserve source chapter
boundaries unless the user explicitly authorizes structural change.

For Final Script 1.2, repair `full_copy` first and then re-evaluate `fidelity_text`.
Do not author a replacement `onscreen` field. In analytical mode, follow the
analytical contract's proposition and argument repair sequence before refreshing
fidelity literals.

## 6. Whole-deck review / rewrite

Resolve `authoring_mode`, read the matching mandatory authoring reference, then
run Critic and Rewrite against Foundation, Deck Plan and current script. Review
source structure, inference boundary, claim strength, classification or progression,
formal register, full-copy completeness, fidelity-literal provenance and the
whole-deck checks in the active contract.

Faithful review does not fail a page merely because it lacks an author-created
conclusion or argument chain. For `script`-profile faithful pages, page-level
rewrites require current v2 exact-source packets and a passed Author Preflight;
regenerate and reuse them rather than drafting from previews or memory. Missing,
stale, invalid or blocked exact-source state stops the rewrite. Analytical review
may evaluate conclusion and argument quality under the analytical contract.

For Final Script 1.2, review that ordinary prose has not been promoted into
`fidelity_text`, required literals are genuinely mandatory, `if_rendered` literals
remain optional to display, and no authored `onscreen` survives on content pages.

Repair the smallest affected page scope and rerun adjacent-page review. Do not
expose Critic self-dialogue; return the rewritten result and a concise summary of
material changes.

## 7. Planning gate

Show a readable **脚本规划待确认** containing:

- source chapter structure;
- page allocation by presentation chapter;
- each page's tentative title, question, mission and source boundary;
- compact source anchors for each page so the reviewer can see what the cited Foundation refs actually state;
- material split or merge decisions;
- inferred relationships or source conflicts that merit attention;
- restricted or internal material needing an exposure decision.

Do not dump internal JSON. Run
`cyberppt-script review-plan <deck-plan.json> <foundation.json>` and present its
Markdown reading strip. This is a derived review view, not a new authoritative
artifact or approval state.

Before presenting that reading strip, compare every content page's `title`,
`question` and `logic` with the Foundation items named by its `source_refs`.
Under faithful mode, treat `question` and `logic` as neutral source-scope and
pagination metadata: remove unsupported `why`, `so what`, transformation,
mechanism, value, certainty, completion, coordination, causality and actor-role
language. Preserve recommendation, proposal, pending-confirmation and planned
status in the planning wording. Deterministic PLAN checks provide a
high-confidence lexical floor; the current main agent still performs the
qualitative entailment and page-boundary review.

For internal and mixed audiences, preserve an internal-expert voice. Enterprise
operating topics remain valid; external-consultant address and unsupported generic
advice fail review.

## 8. Stage 02 boundary and formal handoff

Stage 01 owns three authoritative script artifacts:

- `script/foundation.json`;
- `script/deck-plan.json`;
- `script/dist/final-script.md`.

`script/.cache/page-source/*.json` remains derived runtime context and is not added
to the authoritative artifact list.

After the final script is locked, Stage 02 uses one formal orchestration entry:

`.venv/bin/python3 -m cyberppt final-script-pages --production-build ...`

`final-script-pages` consumes the locked final script and current Stage 02
handoff and visual contracts before image generation, image-text audit and PPTX
assembly. For Final Script 1.2, the Stage 02 intake derives runtime `onscreen_text`
from `full_copy` while carrying `fidelity_text` independently through handoff,
manifest, prompt compilation, reuse identity and image-text QA. It may rewrite
ordinary content; only fidelity literals receive exact-copy semantics.

High-fidelity editable reconstruction uses `--production-mode image-to-editable-svg`
with the `editable` branch; picture and dual delivery use the same orchestrator
with their declared assembly branches. Do not call a Stage 02 adapter directly or
create a parallel production route.

The Stage 01/Stage 02 boundary is the locked `script/dist/final-script.md` plus
its validated handoff. Stage 02 may derive runtime copy, prompts, manifests and QA
records, but does not rewrite Stage 01 authority artifacts or become a second
content authority.
