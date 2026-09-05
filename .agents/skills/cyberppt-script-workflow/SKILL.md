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

### Mandatory authoring reference

Before `AUTHOR`, `CRITIQUE`, `REWRITE`, targeted page revision or whole-deck
script review, read
[`references/authoring-contract.md`](references/authoring-contract.md) completely.
That file is the single operational authority for authoring behavior. This
`SKILL.md` owns routing and stage boundaries; `AGENTS.md` retains repository hard
constraints. Do not reconstruct author rules from summaries in other files.

## 2. New source-to-script

Internal route:

`UNDERSTAND -> PLAN -> Gate A -> AUTHOR -> CRITIQUE -> REWRITE -> DELIVER`

Automatically:

1. scaffold `projects/<slug>/` and retain source files;
2. extract and index source structure;
3. build a lightweight Foundation with source structure, facts, explicit relations and boundaries once per deck;
4. preserve source chapters and plan PPT pages within that structure;
5. present **脚本规划待确认**;
6. after ordinary approval, execute the mandatory authoring reference;
7. run Critic, rewrite, deterministic audits and delivery validation;
8. report **最终脚本已生成**.

For every new project, PLAN writes a v2 lean `deck-plan.json` containing deck
purpose, chapter grouping, page allocation, tentative topic titles, page
questions, missions and source boundaries.  The Foundation profile remains
independent: strict/legacy keeps Source Truth and its stronger source-fidelity
surface, while `script` uses the lightweight UNDERSTAND route.  Neither route
pre-authors judgments, modules, evidence dispositions, onscreen contracts,
visual relations or speaker threads in PLAN.  v1 strict Deck Plans must be
migrated to v2 lean before entering this workflow.

AUTHOR writes `full_copy` as the semantic source for each page, then authors
`onscreen` as its conclusion-first, reader-facing expression. This is a
semantic-preserving editorial projection: it opens with the page conclusion,
then uses complete paragraphs to unfold the supporting reasons, facts and
implications. It may reorder and clarify the complete copy while retaining
every material fact, condition, responsibility, number and claim strength.
The writing order is strict: finish and review `full_copy` first; only then
select its core conclusion and decisive supporting content for `onscreen`.
Every onscreen proposition must be traceable to a proposition already written
in `full_copy`. When the author cannot shorten a passage without risking a
change of actor, action, object, status, responsibility, number, time,
condition, boundary or claim strength, copy the relevant complete-copy passage
into `onscreen` verbatim as the safe fallback. Never invent a new summary merely
to make the visible layer shorter.
Stage 01 uses neither mechanical shortening nor phrase-led condensation;
dense material is resolved through page mission or pagination rather than
deleting substantive content.
In the default faithful mode, a page conclusion restates or lightly consolidates
source-explicit propositions. Parallel source propositions may remain parallel;
AUTHOR must not manufacture a causal chain, necessity claim, implication,
priority or value judgment to satisfy a framework. Analytical relations may enter
the authoritative script only under an explicitly approved analytical mode.
The default route does not search for latent logic or reconstruct a stronger
source thesis.
High-risk pages compare judgment-led and evidence-led candidates and retain only
the rewritten winner. These passes occur inside the existing three authoritative
artifacts; they create no Content Plan, checkpoint, gate receipt or review
manifest.

The current main agent is the AUTHOR executor. There is no separate AUTHOR Skill, CLI,
deterministic generator or project-specific author script. Loading this router,
creating schema-valid output or passing lint does not execute AUTHOR.

Every deck defaults to `deck.delivery_mode: self_read`. Use `presented` only when
the user explicitly requests a presenter-led sparse deck.

## 3. Re-plan

### Expression or pagination re-plan

Requests such as `重新做分页`, `第3章页数太多` or `整套PPT表达逻辑再优化`
keep `source_structure_mode: preserve`. Re-plan page split or merge,
chapter-internal logic, analysis model and page arguments.

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

Read the mandatory authoring reference, target page and adjacent pages, matching
Deck Plan entry, `source_scope`, relevant Foundation facts and relations, and
`analysis_basis` where present. Preserve source chapter boundaries unless the user
explicitly authorizes structural change.

## 6. Whole-deck review / rewrite

Read the mandatory authoring reference, then run Critic and Rewrite against
Foundation, Deck Plan and current script. Review source structure, inference
boundary, analytical depth, claim strength, classification or progression,
optionality, visibility, compression loss, formal register and every whole-deck
check in the authoring contract.

Repair the smallest affected page scope and rerun adjacent-page review. Do not
expose Critic self-dialogue; return the rewritten result and a concise summary of
material changes.

## 7. Planning gate

Show a readable **脚本规划待确认** containing:

- source chapter structure;
- page allocation by presentation chapter;
- each page's tentative title, question, mission and source boundary;
- material split or merge decisions;
- inferred relationships or source conflicts that merit attention;
- restricted or internal material needing an exposure decision.

Do not dump internal JSON. Run
`cyberppt-script review-plan <deck-plan.json> <foundation.json>` and present its
Markdown reading strip. This is a derived review view, not a new authoritative
artifact or approval state.

Before presenting that reading strip, compare every content page's `title`,
`question` and `logic` with the Foundation items named by its `source_refs`.
Remove unsupported certainty, completion, coordination, causality and actor-role
language. Preserve recommendation, proposal, pending-confirmation and planned
status in the planning wording. Deterministic PLAN checks provide a high-
confidence lexical floor; the current main agent still performs the qualitative
entailment and page-boundary review.

For internal and mixed audiences, preserve an internal-expert voice. Enterprise
operating topics remain valid; external-consultant address and unsupported generic
advice fail review.

## 8. Stage 02 boundary and formal handoff

Stage 01 owns three authoritative script artifacts:

- `script/foundation.json`;
- `script/deck-plan.json`;
- `script/dist/final-script.md`.

After the final script is locked, Stage 02 uses one formal orchestration entry:

`.venv/bin/python3 -m cyberppt final-script-pages --production-build ...`

`final-script-pages` consumes the locked final script and current Stage 02
handoff and visual contracts before image generation, image-text audit and PPTX
assembly. High-fidelity editable reconstruction uses
`--production-mode image-to-editable-svg` with the `editable` branch; picture and
dual delivery use the same orchestrator with their declared assembly branches.
Do not call a Stage 02 adapter directly or create a parallel production route.

The Stage 01/Stage 02 boundary is the locked `script/dist/final-script.md` plus
its validated handoff. Stage 02 may derive prompts, manifests and QA records, but
does not rewrite Stage 01 authority artifacts or become a second content
authority.
