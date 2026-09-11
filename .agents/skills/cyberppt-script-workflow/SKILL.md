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
7. for each faithful page, resolve exact page source context before drafting; when `script/.cache/source-index.json` is v2, generate the derived `page-source` packet first;
8. run Critic, rewrite, deterministic audits and delivery validation;
9. report **最终脚本已生成**.

For every new project, PLAN writes a v2 lean `deck-plan.json` containing deck
purpose, chapter grouping, page allocation, tentative topic titles, page
questions, missions and source boundaries. The Foundation profile remains
independent: strict/legacy keeps Source Truth and its stronger source-fidelity
surface, while `script` uses the lightweight UNDERSTAND route. Neither route
pre-authors judgments, modules, evidence dispositions, onscreen contracts,
visual relations or speaker threads in PLAN. v1 strict Deck Plans must be
migrated to v2 lean before entering this workflow.

### Faithful AUTHOR

#### Mission and judgment ownership

PLAN writes a concrete mission for every content page in the existing `logic`
field: the business scope, the page's communication duty and its distinction from
adjacent pages. Do not introduce a second PLAN `mission` field or pre-author a
`core_message`. The page-source packet carries `page_mission` as a disposable copy
of `logic` so AUTHOR reads the mission together with exact evidence.

During AUTHOR, check that the full copy actually fulfils this mission. A Final
Script `mission`, when supplied, is a review-only restatement of PLAN `logic`;
repair PLAN first if the page duty changes. A wording difference is a review hint,
not proof of a semantic conflict. Do not render the mission as onscreen content.

After reviewing source meaning and full copy, choose the faithful judgment form:
one source-supported main judgment may use optional `core_message`; multiple
parallel judgments stay in their source order within full copy and onscreen
modules; a definition, classification or task list may omit a page-wide judgment.
Do not add a synthetic conclusion to fill a field. Presence of `core_message`
alone does not authorize analytical or argument-led writing. CRITIQUE reviews
mission fulfilment separately from judgment support, qualifiers and strength.

#### Faithful full copy and onscreen writing

`faithful` is source-native editorial transduction. AUTHOR writes `full_copy` as
the complete page-ready manuscript from the source-native structure, then writes
`onscreen` only from the reviewed `full_copy`.

Before writing a faithful content page, resolve the exact evidence for that page.
For the default `script` profile, when `script/.cache/source-index.json` is a
`cyberppt.source_index.v2` file, run:

```bash
.venv/bin/python3 -m script_engine.cli page-source \
  script/deck-plan.json \
  script/foundation.json \
  <PAGE_ID> \
  --output script/.cache/page-source/<PAGE_ID>.json
```

Read the packet before drafting. It is disposable `derived_runtime_context`, not a
new content authority. A packet with `status: rewrite_required` blocks drafting of
that page until its source boundary is repaired. Regenerate the packet whenever the
page source refs, Foundation or source index changes.

A faithful page may legitimately contain a definition, parallel facts, parallel
tasks, a taxonomy, explicit stages, status statements or responsibilities without
an author-created total conclusion. Do not manufacture a conclusion, argument
chain, causality, necessity, implication, mechanism, capability, value judgment,
closed loop or progression merely to satisfy a presentation framework.

`full_copy` preserves every material fact, condition, responsibility, formal
instrument, number, date, status, boundary, claim strength and source-explicit
relationship. The main Agent rewrites `full_copy` into `onscreen` while retaining
all substantive information, changing only wording and organization. Remove only
equivalent repetition and non-material connective wording. Review the two complete
texts directly in both directions before consulting optional machine hints; follow
Steps 6–7 of the faithful contract. No candidate scoring or helper call is required.

When AUTHOR cannot shorten a passage without risking a change of actor, action,
object, status, responsibility, number, time, condition, boundary, relationship
or claim strength, copy the relevant complete-copy passage into `onscreen`
verbatim as the safe fallback. Never invent a new summary merely to make the
visible layer shorter.

### Analytical AUTHOR

Only when `authoring_mode: analytical` is explicitly approved may AUTHOR use the
analytical contract to write a `core_message`, argument topology, source-supported
inferred relationships, judgment-led full copy and analytical onscreen
projection. Analytical mode remains source-bounded and cannot introduce new
facts, commitments, numbers or speculative relationships.

### Shared AUTHOR execution

Stage 01 uses neither blind mechanical shortening nor uncontrolled phrase-led
condensation; dense material is resolved through source-faithful editing,
approved page scope or pagination rather than deleting substantive content.

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
In faithful mode, if a v2 source index exists, regenerate the target page's
`page-source` packet before editing so the revision uses the current exact source
units. Preserve source chapter boundaries unless the user explicitly authorizes
structural change.

In faithful mode, repair `full_copy` before `onscreen`; do not repair visible copy
by inventing a stronger page conclusion. In analytical mode, follow the
analytical contract's proposition and argument repair sequence.

## 6. Whole-deck review / rewrite

Resolve `authoring_mode`, read the matching mandatory authoring reference, then
run Critic and Rewrite against Foundation, Deck Plan and current script. Review
source structure, inference boundary, claim strength, classification or
progression, optionality, visibility, compression loss, formal register and the
whole-deck checks in the active contract.

Faithful review does not fail a page merely because it lacks an author-created
conclusion or argument chain. When exact v2 source context exists, page-level
faithful rewrites regenerate and reuse the corresponding page-source packet rather
than drafting from previews or memory. Analytical review may evaluate conclusion
and argument quality under the analytical contract.

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
assembly. High-fidelity editable reconstruction uses
`--production-mode image-to-editable-svg` with the `editable` branch; picture and
dual delivery use the same orchestrator with their declared assembly branches.
Do not call a Stage 02 adapter directly or create a parallel production route.

The Stage 01/Stage 02 boundary is the locked `script/dist/final-script.md` plus
its validated handoff. Stage 02 may derive prompts, manifests and QA records, but
does not rewrite Stage 01 authority artifacts or become a second content
authority.
