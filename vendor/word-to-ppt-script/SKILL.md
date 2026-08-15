---
name: word-to-ppt-script
description: Use when a formal Word report, proposal, research report, work report, briefing material, or government/SOE document must be compiled into a source-grounded PPT outline, page-by-page on-screen text, speaker notes, visual design specification, image-generation-ready script, and quality report. The skill reconstructs argument and page ownership before writing copy, and validates page boundaries, cross-page duplication, logical parallelism, classification dimensions, density, source fidelity, and visual executability.
---

# Word to PPT Script Compiler

## 1. Purpose

Compile a `.docx` source into a complete, auditable and visually executable PPT script repository.

The workflow is:

```text
Word extraction
→ source truth compilation
→ argument reconstruction
→ deck outline
→ page ownership and boundary lock
→ on-screen text compilation
→ speaker-note compilation
→ visual structure design
→ final script assembly
→ deterministic and semantic quality audit
```

The primary product is a production-ready complete Markdown script. It is designed as the upstream contract for a downstream assembly repository: template pages are rendered by code as editable SVG/PPT elements, while content pages are compiled into single-page ImageGen contracts and inserted into the PPT body area. The skill itself does not require direct image or PPTX generation.

## 2. Core principles

1. **The Word document is evidence, not a ready-made slide outline.** Use source headings as clues, not as binding slide pages.
2. **Every content page owns one primary question.** A fact, mechanism or conclusion has one primary home unless a brief cross-reference is required.
3. **Page boundary precedes page copy.** Do not draft on-screen text before the page ownership matrix is approved or internally validated.
4. **Relationships precede modules.** Determine cause, process, support, hierarchy, input-output, closed loop, branching, classification or control before selecting modules and visuals.
5. **On-screen text is final copy, not report prose.** It must be concise, source-faithful, logically connected and directly usable.
6. **Visual design is part of compilation.** Every content page must translate its semantic relationship into a visual contract.
7. **Validation is blocking.** Do not deliver a script with page leakage, unsupported claims, wrong parallelism, mixed classification dimensions, unresolved duplicates or missing visual contracts.

## 3. Invocation modes

Choose the narrowest mode that satisfies the task:

| Mode | Input | Main output |
|---|---|---|
| `lite` | Word source | Page boundary sketch, locked on-screen text, speaker notes and final script — no hash-gated intermediate artifacts |
| `full` | Word source | All intermediate artifacts, final script and audit |
| `outline` | Word source | Storyline, chapter contracts, slide outline and page boundary matrix |
| `text` | Approved outline or page contracts | Transition script, final on-screen text and speaker notes |
| `visual` | Approved page script | Page visual contracts and image-generation handoff |
| `compile` | Approved text and visual artifacts | Final assembled script and machine-readable manifests |
| `revise` | Word source plus existing script | Corrected script while preserving authorized filename and format |
| `audit` | Word source plus existing script | Source, logic, boundary, text, visual and output audit |

**Default to `lite`** when a single person is compiling one Word document into
one script in one sitting and the document's own structure (chapters,
sections, argument flow) is already clear — this covers most single-project
requests. See "Gate L — Lite pipeline" below.

Use `full` instead only when at least one holds: multiple people will edit
the source or outline over time and need hash-verified staleness detection;
the deliverable needs a durable, replayable, multi-round audit trail; or the
source document's argument structure is genuinely contested and needs
`outline-audit`-style structural checks. Do not default to `full` merely
because the source document is long or the deck is large — page count alone
is not a reason to run the hash-gated cascade.

In `revise` mode, preserve the input filename, page order and field format unless the user explicitly authorizes changes. Do not insert explanatory notes into the replacement artifact.

## 4. Mandatory compilation pipeline

Gates 0–7 below define `full` mode. `lite` mode is the default (§3) and
compresses them into the four steps in **Gate L**, immediately below. Read
Gate L first; fall through to Gates 0–7 only when the task has actually
switched to `full` mode.

### Gate L — Lite pipeline (default mode)

Use when one person is compiling one Word document into one script in one
sitting and the document's structure is already clear (§3 default rule).

The agent must stop for user input in the conversation; do not create approval
files, checkpoint files, state JSON, receipts or manifests to represent these
interactions. User feedback edits the existing outline or page scripts
directly.

Four authoring steps, no hash-gated intermediate artifacts or persisted
per-stage audit chain. In CyberPPT, the official lightweight commands still
run one semantic, Source Truth and Outline business check before the final
script check; those commands do not write gate state:

1. **Understand and extract source.** In CyberPPT, first use
   `prepare-semantic-understanding --lightweight` and
   `semantic-check --lightweight`, then build the canonical Source Truth and
   run `source-truth-audit --lightweight`. Pull the source atoms this script
   needs (fact,
   policy/requirement, judgment, definition, proposal, action/responsibility,
   boundary/constraint, risk, background) directly from the Word document or
   from an already-produced `source-truth.json`/outline if one exists. Keep
   each atom's entity, number, date, status, condition, scope, responsibility
   and wording strength — this is the same discipline as Gate 1, just without
   writing `01-source-normalized.md`/`02-source-truth-map.md` as separate
   files. In CyberPPT, run `python -m cyberppt
   prepare-communication-strategy <project> --lightweight`, analyze its
   `source_outline` and `decision_evidence`, and present one source-faithful
   communication-goal direction. It states the concrete audience, use
   scenario, intended understanding or belief, explicit audience action, and
   supporting source unit IDs. Do not offer multiple communication-goal
   options. User wording may constrain audience, use, or delivery, but must not
   be promoted into a source fact, source judgment, or page conclusion without
   direct source support. Never ask the user to supply audience, scenario, or
   desired action from a blank slate; the user selects, revises, or supplements
   the proposed direction. This command writes no gate, approval, hash, receipt,
   attempt, manifest, or ledger file.
2. **Page boundaries.** Sketch one primary question and one owner per page
   directly (Gate 3's rules still apply: no duplicate primary ownership, no
   drafting on-screen text before boundaries are settled) without producing
   `05-page-boundary-matrix.md` or `machine/page-contracts.json` as separate
   artifacts. Present the proposed chapter and page outline to the user and
   wait for feedback before drafting detailed page content.
3. **Full manuscript, on-screen text and speaker notes.** Write 完整文字稿
   yourself from the page's source-truth records: read each record's
   statement, role and weight, then compose connected argument prose —
   background/evidence before judgment before mechanism before
   recommendation before boundary, with real transition language, not a
   restatement of the source's own enumeration markers. This is a genuine
   authoring step, not a mechanical assembly step; do it with the same
   judgment you would apply to any other paragraph you write, and do not
   introduce a claim, number or entity the records do not support.
   Two fallbacks exist for contexts where no LLM agent is authoring the
   script (a scheduled unattended regeneration, a pure-script CI run):
   `scripts/llm_draft_page.py` calls the Anthropic API to draft the same
   agent-quality prose automatically (needs `ANTHROPIC_API_KEY`), and
   `scripts/assemble_full_prose.py` (`references/18-full-prose-assembly.md`)
   is the last-resort, no-API-key deterministic fallback — normalizing
   orphaned enumeration markers and picking a role-appropriate frame sentence
   is what it can safely automate without judgment. When an agent is
   compiling the script, prefer writing the prose directly over calling
   either. Then follow the Gate 4 contract
   exactly: `references/06-on-screen-text.md`, `07-logic-and-parallelism.md`,
   `08-speaker-notes.md`, and `references/17-density-and-coverage.md` for the
   density band, coverage checklist and nested small-heading form. This step
   is not compressible — it is where quality is actually won or lost. Present
   the detailed page content to the user (chapter-sized batches are allowed),
   accept live revisions, and only then assemble the final manuscript.
   Whichever way 完整文字稿 and 上屏文字 were produced, preserve the same
   density, coverage, banned-pattern and defensive-coaching rules. In
   CyberPPT, do not run a repeated full-script validation here; run the single
   official `script-audit --lightweight` only after final assembly.
4. **Final script assembly.** Produce the single deliverable file (the
   project's own `10-script-final.md` equivalent) using the field format in
   `templates/10-script-final.md`: page type, page title, source chapter,
   main judgment, complete draft, text-selection explanation, evidence
   mapping, locked on-screen text, logic skeleton, and speaker notes.
   Do not create a script-hash-bound `page-contracts.json` sidecar in lite
   mode; do not embed `cyberppt-page-contract` metadata in the formal
   human-readable script.
   Draft comments may be accepted only as a legacy assembly input. Visual structure/`visual_intent_type`
   fields are only required when visual design is in scope for this task.
   When it is not, state so explicitly, once, in the script's own header —
   include the exact line `视觉设计范围：不含视觉设计` (the fixed string
   `scripts/validate_script.py` searches the document for). Without it, the
    validator has no way to distinguish "visual design intentionally out of
   scope" from "visual design forgotten," and will correctly keep failing
   every content page on `MISSING_VISUAL`/`MISSING_VISUAL_INTENT`/
    `TITLE_LAYER_UNCLEAR`. After the one final validation, present the whole
    script to the user and wait for final confirmation.

**Mandatory quality gate for lite mode** (this is what replaces Gates 0–7's
hash-bound audit trail — do not skip it):

```bash
python -m cyberppt script-audit <project> --input <final-script>.md --lightweight
```

When the skill is used outside CyberPPT, use
`python scripts/validate_script.py <final-script>.md --strict` instead. Both
forms perform one final content check; neither creates a per-stage retry chain
in lite mode.

Reconcile every `error`; reconcile or consciously accept every `warning`
before treating the script as done. A project-local pre-check script may
duplicate a fast subset of these rules for immediate feedback while drafting,
but `scripts/validate_script.py` and its `config/quality-rules.yaml` /
`config/cec-formal.yaml` thresholds are the authoritative source of truth —
if a local pre-check and this validator ever disagree, this validator wins.

After any stage or step completes, the same response must show every actual
output file as a clickable Markdown link to its absolute path. Do not report
only completion, a filename, a plain-text path or a directory and make the
user search for the deliverable. If the step produced no file, say so
explicitly. This display rule must not create checkpoint, approval, state,
hash, receipt, attempt, manifest or ledger files.

Switch mid-task to `full` mode (Gates 0–7) if, while working, it becomes
clear the outline is genuinely contested, multiple authors will keep editing
the source over time, or the deliverable needs a hash-verified audit trail —
do not silently keep compressing steps once that threshold is crossed.

### Gate 0 — Task contract

Read `references/01-task-contract.md` and create `00-task-brief.md`.

Lock:

- audience and decision task;
- presentation purpose;
- source hierarchy;
- fixed chapter/page requirements;
- target page range and density;
- template pages;
- output filename rules;
- visual profile;
- prohibited wording and content.

When page count is unspecified, choose a reasonable range from source complexity. Avoid both excessive fragmentation and low-density pages.

### Gate 1 — Source truth compilation

Read `references/02-source-compilation.md`.

Create:

- `01-source-normalized.md`;
- `02-source-truth-map.md`;
- `machine/source-truth-map.json`.

Classify source atoms as:

- fact;
- policy or superior requirement;
- source judgment;
- definition;
- proposal or recommendation;
- action or responsibility;
- boundary or compliance constraint;
- risk or unresolved item;
- explanatory background.

Assign `P0`, `P1` or `P2`. Preserve entity, number, date, status, condition, scope, responsibility and wording strength.

Do not continue when a P0 item is contradictory, ambiguous or unsupported.

### Gate 2 — Argument reconstruction

Read `references/03-argument-reconstruction.md` and create `03-argument-map.md`.

Distinguish:

- source writing order;
- underlying reasoning order;
- presentation order required by the audience.

Reconstruct the argument as claims, evidence, conditions, mechanisms and outcomes. Remove repeated explanation while retaining evidence traceability.

### Gate 3 — Outline and page ownership

Read:

- `references/04-outline-and-granularity.md`;
- `references/05-page-boundary-and-ownership.md`.

Create:

- `04-deck-outline.md`;
- `05-page-boundary-matrix.md`;
- `machine/page-contracts.json`.

The fixed order is:

```text
presentation task
→ storyline
→ chapter contracts
→ page sequence
→ page question
→ page-owned content
→ page exclusions
→ adjacent-page handoff
```

Every content page contract must state:

- `本页只回答`;
- `本页核心判断`;
- `本页主要依据`;
- `本页不得包含`;
- previous-page input;
- next-page handoff;
- unique content ownership tags.

Do not proceed while the same important content has multiple primary pages.

Template pages include cover, agenda, chapter transition and back cover. Template pages contain no business body text.

### Gate 4 — On-screen text and notes

Read:

- `references/06-on-screen-text.md`;
- `references/07-logic-and-parallelism.md`;
- `references/08-speaker-notes.md`;
- `references/17-density-and-coverage.md` — on-screen text density band, coverage
  checklist against 完整文字稿, and the nested small-heading form for items
  that bundle two or more parallel facts.
- `references/18-full-prose-assembly.md` — writing 完整文字稿 as connected
  argument prose (background/evidence before judgment before mechanism
  before recommendation before boundary) instead of naive string
  concatenation. Do this yourself when an LLM agent is compiling the script;
  `scripts/assemble_full_prose.py` is the deterministic fallback for
  contexts with no agent present, not the default path.

Create:

- `06-transition-script.md`;
- `07-on-screen-text.md`;
- `08-speaker-notes.md`.

#### On-screen text contract

Every content page must include:

- page type;
- page title;
- page mission;
- core judgment;
- logic skeleton;
- final on-screen text;
- source IDs.

When modules are used, the canonical form is:

```markdown
### 一、上位模块｜模块作用

- **小标题**
  - 完整、精炼的正文。
```

Rules:

- each module must have a logical role, not merely a topic label;
- subordinate items under the same module must be genuinely parallel;
- causes, stages, classifications, safeguards and results may not be presented as equal siblings without an explicit relationship;
- service categories may not be mixed with fee categories;
- service types may not be mixed with deployment modes, access methods, processing locations or service cycles;
- numbers in titles such as “三类、四项、五层、六个” must match the actual visible items;
- avoid adversarial binary sentence frames, including `不是……而是……`, `不能只……还要……` and equivalent contrast templates; use direct positive judgments;
- do not repeat the same full explanation on multiple pages;
- one page must remain understandable without depending on hidden text from another page;
- when this page's relationship (per `07-logic-and-parallelism.md`) is causal, sequential, procedural, hierarchical or closed-loop, and the page has more than three top-level modules, the module headings or locked on-screen text must carry an explicit order/relationship signal (①②③④, 一/二/三/四, `→`/`->`, 随之) — a role-suggestive label alone (e.g. 业务演进/协同需求/现实制约/基础需求 with no numbering or connector) is not sufficient; a reader must see the sequence without reading 逻辑骨架 or waiting for Gate 5 visual design;
- the relationship recorded in this page's 逻辑骨架 must be verifiable directly from the locked on-screen text; do not let a causal or sequential chain exist only inside 逻辑骨架 while the visible module titles read as flat, order-free parallel topics.

#### Density and granularity

- prefer a medium granularity for formal reports;
- one page carries one complete argument unit, not one minor bullet;
- avoid pages with only a judgment and two short fragments unless the page type requires it;
- do not reduce font size to solve content overload; repair ownership or structure first.

#### Speaker notes

Speaker notes must:

- explain the reasoning behind the visible text;
- add evidence, transition and boundary clarification without duplicating the visible copy;
- preserve source status and responsibility wording;
- avoid introducing unsupported claims;
- not enter image-generation text.

### Gate 5 — Visual structure compilation

Read:

- `references/09-visual-design.md`;
- `references/10-visual-intent-router.md`;
- `references/11-scene-and-image-integration.md`;
- `references/15-imagegen-handoff.md`;
- `references/16-single-page-imagegen-contract.md`.

Create:

- `09-visual-design-spec.md`;
- `machine/visual-spec.json`.

`decision_relationship` must be inherited from this page's Gate 4 `逻辑骨架`, not independently (re)judged — Gate 5 only translates an already-locked relationship into spatial/visual form. If 逻辑骨架 is missing, empty or ambiguous, return to Gate 4 and fix the on-screen text and logic skeleton together rather than inventing a relationship at Gate 5.

Every content page must define:

- `visual_intent_type`;
- `visual_thesis`;
- `decision_relationship` (inherited from 逻辑骨架, see above);
- `dominant_visual_carrier`;
- `spatial_organization`;
- `reading_path`;
- `relationship_encoding`;
- `text_integration_method`;
- `industry_scene_anchor`;
- `visual_hierarchy`;
- `avoid_on_this_page`;
- title/text-layer handling;
- image-generation execution summary.

Visual decisions follow semantic relationships, not template names or bullet counts.

Mandatory visual rules:

- one clear visual center;
- the dominant carrier must express the core judgment;
- text must attach to the business structure, not sit in a detached text column;
- real industry scenes may be used when they clarify the judgment, but may not become decorative evidence-free imagery;
- no front-facing identifiable person unless explicitly required;
- no equal card wall, icon array, one-image-per-bullet or repetitive page skeleton by default;
- title, subtitle, page number and logo are handled by the PPT template/text layer unless explicitly requested;
- do not recommend multi-image reconstruction workflows by default; optimize the single full-page generation contract first.

### Gate 6 — Final assembly

Read `references/12-output-contract.md`.

Create:

- `10-script-final.md`;
- `machine/final-manifest.json`;
- optional `12-imagegen-review.md` when a separate ImageGen review/handoff is requested.

Every page in `10-script-final.md` must include the exact fields defined in `templates/10-script-final.md`.

The final script must include:

- cover, contents, chapter transition and closing template pages;
- content pages with page type, page title, source chapter, main judgment, complete draft, text-selection explanation, evidence mapping, locked on-screen text, logic skeleton, visual structure, visual intent and speaker notes;
- a separate, script-hash-bound `page-contracts.json` carrying each page's `page_mission`, `core_message`, source references, consumed units and `must_not_include`;
- no `cyberppt-page-contract` HTML metadata inside the formal human-readable script; legacy comments are accepted only as assembly input;
- no process commentary or compilation explanation inside the artifact;
- no source-tracking IDs inside visible on-screen text;
- no unsupported fields or legacy `overlay` sections.

The complete script is the formal primary artifact. A downstream ImageGen review script may be compiled from it, but never replaces it.

### Gate 7 — Quality audit

Read `references/13-quality-gates.md` and create:

- `11-quality-review.md`;
- `machine/quality-report.json`.

Run when local execution is available:

```bash
python scripts/validate_script.py 10-script-final.md --strict
python scripts/validate_project.py . --strict
# when 12-imagegen-review.md exists:
python scripts/validate_imagegen_contract.py 12-imagegen-review.md --strict
```

Blocking conditions include:

- P0 source coverage below 100%;
- unsupported number, entity, status, responsibility, scope or commitment;
- page mission and visible content mismatch;
- content assigned outside its primary page;
- high cross-page duplication without an explicit handoff purpose;
- mixed parallel dimensions;
- service and service-fee categories presented as siblings;
- service type, access method, deployment mode, data-processing location and service cycle mixed as one classification;
- title count inconsistent with visible item count;
- banned contrast sentence frames;
- template page containing business body text;
- content page missing speaker notes or visual contract;
- repeated equal-card visual skeletons;
- unresolved visual overflow or unreadable text density;
- final filename or format changed contrary to user instruction.

## 5. Output contract

Full mode produces:

```text
00-task-brief.md
01-source-normalized.md
02-source-truth-map.md
03-argument-map.md
04-deck-outline.md
05-page-boundary-matrix.md
06-transition-script.md
07-on-screen-text.md
08-speaker-notes.md
09-visual-design-spec.md
10-script-final.md
11-quality-review.md
machine/source-truth-map.json
machine/page-contracts.json
machine/visual-spec.json
machine/final-manifest.json
machine/quality-report.json
optional 12-imagegen-review.md
```

The primary delivery artifact is `10-script-final.md`. When the user requires direct replacement, write to the exact requested filename after validation.

## 6. Downstream page-generation and assembly contract

The downstream repository must identify page type from the complete script:

- `cover / contents / chapter / closing`: do not enter ImageGen; generate template SVG and write editable PPT elements;
- `content`: compile the locked visible text into a single-page ImageGen contract, generate the body image, write the page title through the PPT text layer, then place the image in the content area.

The single-page ImageGen contract has a fixed field order. Page-specific visual structure is compiled separately from the global style:

```text
locked key text
complete on-screen content
conclusion-sentence handling rule
page mission
core meaning
output size
template-layer no-draw rule
runtime visual style injected from `visual/ACTIVE-STYLE.md`
```

Do not pass evidence IDs, speaker notes, selection explanations, logic skeletons, visual-intent fields or page-contract JSON into ImageGen. See `references/16-single-page-imagegen-contract.md`. Excluding the raw 逻辑骨架 field from the ImageGen payload does not excuse dropping the relationship it records: by the time a page reaches this stage, the same relationship must already be legible in the locked on-screen text (Gate 4) and encoded spatially in `reading_path`/`relationship_encoding` (Gate 5). If it is not, the page is not ready for ImageGen — fix Gate 4/5, do not paper over the gap by adding decorative arrows only inside the image prompt.

## 7. Default CEC formal profile

Use `config/cec-formal.yaml` for Chinese government, industry-association, central-SOE and formal internal reporting unless another profile is requested.

Defaults:

- formal, restrained and decision-oriented language;
- chapter structure may follow the Word source when explicitly requested, while page ownership still requires validation;
- medium information density;
- white background, deep blue and neutral gray;
- 16:9, reference canvas 1280×720;
- Microsoft YaHei or a visually close Chinese sans-serif font;
- title hierarchy greater than module hierarchy, body and annotations;
- no logo, page number or decorative bars in the generated body image;
- real industry scene anchors when useful;
- no front-facing people;
- clean arrows and consistent direction;
- no `不是……而是……` construction;
- no unexplained English visual jargon in visible copy.

## 8. Stop and repair conditions

Stop the current gate and repair rather than fabricate when:

- the Word file is unreadable or incomplete;
- a P0 item conflicts across sources;
- the requested conclusion is absent from the source;
- page ownership cannot be resolved without changing the approved outline;
- a page can only be completed by inventing facts or responsibilities;
- visible content and visual design encode different relationships.

Minor ambiguity may be marked `待核`; the remaining compilation may continue.


## Runtime visual style boundary

The PPT script owns page mission, locked text and page-specific visual structure. It does not own the reusable palette, material, scene richness or general aesthetic prose. The downstream compiler loads those rules from `visual/ACTIVE-STYLE.md`. Therefore changing the active style does not require rewriting `SCRIPT-FINAL`.
