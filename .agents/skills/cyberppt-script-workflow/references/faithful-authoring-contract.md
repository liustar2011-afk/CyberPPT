# CyberPPT Faithful AUTHOR Contract

This file is the single operational authority for `AUTHOR`, `CRITIQUE`, `REWRITE`,
targeted page revision, and whole-deck script review when the approved
`authoring_mode` is `faithful` or absent.

Read this file completely before those actions. Do not read or blend the analytical
`authoring-contract.md` into a faithful action. Repository-level `AGENTS.md` remains a
hard constraint; `.agents/skills/cyberppt-script-workflow/AGENTS.md` selects the active
mode-specific contract.

## 1. Product responsibility

Faithful authoring is **source-native editorial transduction**.

Its job is to convert source material into page-ready complete copy and reader-facing
onscreen copy while preserving the source's viewpoints, speaking position, facts,
status, responsibilities, numbers, conditions, boundaries, formal instruments, claim
strength, and explicit relationships.

A faithful page is successful even when it has:

- no author-created page conclusion;
- no argument chain;
- no inferred relationship;
- no visual thesis;
- no speaker notes;
- parallel facts, tasks, categories, stages, or responsibilities that remain parallel.

Do not add analytical depth merely to make a page look more like a consulting slide.

## 2. Required page sequence

Run these steps in order for every faithful content page.

### Step 1 — Load the approved page scope

Read:

- page title and page role;
- the approved page mission in Deck Plan `logic` (also carried as `page_mission`
  in the derived page-source packet);
- page-bound `source_refs`;
- adjacent-page boundary;
- source chapter heading and relevant source structure;
- delivery mode and audience exposure boundary.

The Deck Plan defines the available evidence scope. It does not authorize AUTHOR to
invent a stronger question, conclusion, mechanism, or value thesis.

PLAN `logic` owns the page mission: state the specific business scope, communication
duty and division of work with adjacent pages. Check the completed full copy against
that duty. An optional Final Script `mission` only restates the approved duty for
review; update PLAN first if scope changes. Neither mission field is audience copy
or evidence for a business judgment.

### Step 2 — Resolve exact source evidence

For the default `script` profile, exact per-page source resolution is mandatory whenever
`script/.cache/source-index.json` exists and has schema `cyberppt.source_index.v2`.
Before drafting the page, run:

```bash
.venv/bin/python3 -m script_engine.cli page-source \
  script/deck-plan.json \
  script/foundation.json \
  <PAGE_ID> \
  --output script/.cache/page-source/<PAGE_ID>.json
```

Use the resulting packet as disposable AUTHOR runtime context. It is marked
`authority: derived_runtime_context`; it does not become a fourth semantic authority and
does not change the chain `source -> foundation -> deck_plan -> final_script`.

The packet must be regenerated when the page `source_refs`, Foundation, or source index
changes. If it returns `status: rewrite_required`, stop that page and repair the source
boundary before drafting. Do not author around an unknown page reference. Warnings about
missing exact unit bindings must be treated explicitly: use the Foundation surface only
when the project/profile genuinely lacks a resolvable v2 source unit, and do not infer
precise wording that the available evidence does not support.

For `strict/legacy`, use the strongest exact source context available through the
projected Foundation / Source Truth bindings. If a compatible v2 source index is present,
use the same `page-source` command; otherwise resolve the page's source units through the
strict source-consumption bindings rather than reconstructing meaning from memory.

Read the Foundation records named by the page's `source_refs` and the exact underlying
source text resolved for those records before drafting.

Record the protected payload:

- actor / issuer / responsible party;
- source predicate and direction;
- action or status;
- exact business object;
- formal document or instrument and its type;
- number and date;
- responsibility;
- condition and qualifier;
- scope and boundary;
- modality and claim strength;
- source-explicit relationship.

Do not treat adjacency, shared vocabulary, or professional common sense as an explicit
relationship.

### Step 3 — Classify the source-native page structure

Use the smallest structure actually present in the source. Typical faithful structures
are:

1. `definition` — one or more source definitions;
2. `parallel_facts` — independent facts on one source-defined topic;
3. `parallel_tasks` — independent tasks or work items;
4. `classification` — source-defined categories, types, actors, or layers;
5. `process` — a sequence explicitly stated by the source;
6. `stages` — source-defined phases or milestones;
7. `status` — completed / ongoing / planned / pending states;
8. `responsibility` — actors and their source-defined duties;
9. `explicit_relation` — source explicitly states support, dependency, mapping, flow,
   cause, condition, or another relationship;
10. `explicit_argument` — source itself states a conclusion and its supporting reasons.

Do not change one structure into another merely for presentation effect.

Forbidden conversions include:

- parallel facts -> causal chain;
- parallel tasks -> capability system;
- work list -> operating mechanism;
- stages -> maturity progression beyond the source;
- responsibilities -> collaboration loop;
- adjacent items -> prerequisite relationship;
- resource list -> value-transformation path;
- recommendation -> completed state;
- optional action -> mandatory action.

### Step 4 — Write `full_copy` directly from source meaning

`full_copy` is the page's complete, faithful, presentation-ready manuscript.

It is not an author-created thesis layer.

Allowed transformations:

- remove repetition;
- split long sentences;
- merge genuinely equivalent repeated wording;
- reorder locally inside the page scope when meaning and relationship direction do not
  change;
- restore an omitted subject or object only when it is directly available from the
  same source context;
- convert long source paragraphs into readable page paragraphs;
- preserve source-native numbered lists, classifications, stages, and processes;
- lightly compress modifiers without changing certainty, responsibility, scope, or
  conditions.

Do not write a synthesized lead merely because the source paragraph begins with a
list, definition, task name, category name, or stage name.

### Step 5 — Run Source Fidelity Critic on `full_copy`

For every substantive proposition in `full_copy`, independently verify:

- Is the actor supported by the page evidence?
- Is the action or predicate supported?
- Is the object the same business matter?
- Is status preserved?
- Is responsibility preserved?
- Are numbers and dates preserved exactly?
- Are material conditions and qualifiers retained?
- Is the relation explicit in the source?
- Is modality / claim strength unchanged?
- Did the sentence add mechanism, capability, value, consequence, significance, or
  professional-domain completion that the source did not state?

If any answer fails, delete the addition or restore a closer source expression. Do not
repair an unsupported statement by adding more explanation.

### Step 6 — Create `onscreen` only from approved `full_copy`

Every visible proposition must have a direct semantic parent in `full_copy`.
Preserve all substantive information while rewriting for the screen.

The current main Agent performs this task directly using language understanding:

> Rewrite the reviewed full_copy for independent reading on a PPT. Preserve all
> substantive information and change only wording and organization. Use clear
> groups, complete sentences or self-contained phrases as appropriate. Preserve
> who does what, to which object, under which conditions, with what status, numbers,
> responsibility and relationship direction. Remove only equivalent repetition and
> connective wording that carries no substantive meaning. There is no word limit.

Read the entire page's reviewed `full_copy` together before rewriting. Treat its
substantive content as already selected for this page. Do not select a smaller set
of “core” propositions, rank sentences for deletion, replace concrete actions with
umbrella labels, or move substantive examples/background into notes to save space.
Content selection belongs upstream when establishing the page scope and full copy.

Organize by a shared business dimension. A child can inherit a common actor or
condition from its own visible module heading when the meaning is unambiguous.
Use natural language judgment to preserve relationships across the whole module.
Retain complete sentences whenever phrases would obscure meaning. If density remains
high, adjust grouping/layout or propose a page-scope/pagination repair through the
existing planning route. Preserve the text until that repair is resolved.

When an equivalent rewrite is uncertain, retain the original complete expression.
Do not generate multiple candidates or run a scoring helper as a prerequisite.

Before writing the visible modules, identify the source-native grouping within the
reviewed full copy. A paragraph may contain a topic statement and several parallel
business propositions. Give the heading and body distinct jobs: when the heading
already carries the topic statement, omit only its equivalent repeated body opening.
Express independent propositions as separate items when that makes their existing
structure visible. Keep each action with its object, conditions and stated effects;
retain a shared qualifier visibly over every item it governs. Do not split on every
semicolon: punctuation can also separate dependent clauses or stages in one process.
Do not invent one-to-one problem/measure mappings or new overarching effects.

For example, two source paragraphs containing four supply conditions and three
construction actions may become two modules with four and three complete items.
This is source-native grouping, not a mandatory item count for other pages. Preserve
source numbering across pages when useful; starting at “三是” is not itself an error.
Exact copying remains valid for a self-contained passage. It does not replace the
editorial check for duplicated headings and hidden parallel structure.

### Step 7 — Compare meanings and rewrite

The current main Agent reads the complete `full_copy` and complete `onscreen`
side by side in a separate review pass, using the same page evidence. First check
whether a reader receives all substantive information from full copy; then check
whether the visible wording adds or changes any assertion. Do this comparison before
reading optional machine hints so that hints do not define the review scope.

Check responsibility, action/object, status, quantities, conditions, negation,
relationship direction and formal names in their actual context. Equivalent wording
and shared visible subjects are valid. Lexical overlap, keyword presence and zero
machine findings cannot establish semantic equivalence.

For each actual discrepancy, identify the original assertion, the visible wording
or omission, and the concrete meaning lost or changed. Rewrite the affected module,
then reread the complete page in both directions. A shorter or more polished result
cannot compensate for lost information. Do not persist internal review reasoning,
proposition ledgers, approval fields or a new workflow artifact.

`build_onscreen_critic_context` is optional diagnostic assistance after this direct
review. Its matches and findings are unverified hints; inspect them against the
complete texts. Resolve real errors and disregard false matches with a concise
explanation in an existing review summary when needed. Do not change correct wording
merely to satisfy a heuristic. Deterministic test success reports software behavior;
only the Agent's text comparison assesses the rewritten meaning.

### Step 8 — Add supporting fields only when they are source-backed and useful

The faithful minimum content-page fields are:

- `title`;
- `full_copy`;
- `onscreen`;
- `source_refs`.

The following fields are optional in faithful mode:

- `mission`;
- `core_message`;
- `argument`;
- `visual_thesis`;
- `relationships`;
- `speaker_notes`.

Do not create them simply to satisfy a template.

If `core_message` is used, it must be a source-explicit conclusion or a minimal
consolidation whose claim strength and relationship are already explicit in the
source. It cannot answer a newly invented "so what" question.

Choose the judgment form after examining the exact source and reviewing full copy:

- one source-supported main judgment: optional `core_message`;
- multiple parallel source judgments: preserve them separately in full copy and
  onscreen modules, with no required page-wide synthesis;
- definitions, classifications or tasks without a total judgment: omit
  `core_message` and preserve the source-native structure.

A source-supported `core_message` alone does not opt the page into argument-led
paragraphs or conclusion-style module headings. Explicit `argument` remains a
separate choice that must itself be supported by the source. No placeholder or
"no judgment" field is needed when the optional core is absent.

If `argument` is used, its topology must already exist in the source. Do not invent an
argument chain from parallel facts.

If `relationships` is used, each edge must be source-explicit. Do not complete an
abstract edge by inventing a mechanism.

If `visual_thesis` is used, it may describe the source-explicit structure; it is not a
license to create a new business relationship.

If `speaker_notes` is used, it may add source-grounded subordinate context or a natural
transition. It may not contain a stronger claim than the visible copy.

### Step 9 — Run whole-deck faithful Critic

Check:

- fulfilment of each PLAN mission by the actual page content, separately from
  whether the page has one, several or no source-supported judgments;
- source chapter coverage and order;
- page-bound source scope;
- adjacent-page duplication and omissions;
- title fidelity;
- issuer voice consistency;
- status and modality consistency;
- repeated facts serving no new page purpose;
- accidental relation promotion;
- accidental value / capability / mechanism synthesis;
- exposure of internal or restricted content;
- onscreen compression loss.

Do not require every page to form a conclusion peak, every chapter to culminate in a
new value thesis, or every set of facts to become a process.

### Step 10 — Run deterministic validation

After generative Critic and Rewrite, run the repository's schema, lint, semantic audit,
source-reference, and delivery checks. Deterministic success does not replace the
source-fidelity Critic.

## 3. Speaking position and issuer voice

`full_copy` and `onscreen` inherit the source's speaking position.

When the source directly defines, requires, arranges, proposes, reports, or states a
matter, the script directly states the same matter.

Do not introduce outside-narrator frames such as:

- `通知所称`;
- `材料指出`;
- `材料认为`;
- `文件认为`;
- `文件指出`;
- `原文说明`;
- `在通知中已明确`;
- `根据材料可以看出`;
- `从材料看`.

A citation that belongs to the source proposition itself remains valid. For example,
`按照《某办法》要求开展……` preserves a source-owned relation and is not an outside
narrator.

## 4. Protected semantic payload

The following payload is never optional when it materially changes meaning:

### 4.1 Actors and responsibility

Do not:

- turn one actor's state into a group-wide state;
- assign a task to an actor the source does not assign;
- replace a named actor with an umbrella group that expands responsibility;
- omit the actor when omission makes the responsibility ambiguous.

### 4.2 Status

Preserve distinctions such as:

- 已完成;
- 已形成;
- 正在推进;
- 计划开展;
- 拟开展;
- 建议;
- 可;
- 待确认;
- 尚未;
- 目标.

Do not normalize mixed status into a single stronger state.

### 4.3 Modality

Do not convert:

- `可` -> `应当` / `必须`;
- `建议` -> `要求`;
- `计划` -> `已完成`;
- `目标` -> `已实现`;
- `具备条件` -> `必然实现`.

### 4.4 Numbers and dates

Do not add, round, infer, normalize, or silently omit a protected number or date.

### 4.5 Conditions and boundaries

A condition, exclusion, scope, time qualifier, authority boundary, or applicability
limit that changes the claim must remain in the visible layer when the visible claim
would otherwise be misleading.

### 4.6 Formal instruments

Preserve the actual identity of:

- policy guideline;
- action plan;
- management measure;
- trial technical document;
- national standard;
- industry standard;
- group standard;
- initiative;
- task statement;
- contract or agreement.

Do not merge distinct instruments into author-created terms such as `国家规则` or
`统一规范` unless the source itself uses that collective term.

## 5. Source-native page structures

### 5.1 Definition page

A definition may remain a definition. Do not prepend a significance judgment unless the
source states it.

Valid:

`业务场景是指……`

Invalid source-free upgrade:

`业务场景是释放数据要素价值的核心载体。`

### 5.2 Parallel facts page

Parallel facts may remain peer facts. A common topic title is sufficient when the
source has no total thesis.

### 5.3 Parallel tasks page

A numbered source task list may remain:

`一是数据目录梳理。……`

Do not force:

`一是数据目录梳理夯实统一管理基础。……`

unless that effect is explicit in the source.

### 5.4 Classification page

A source taxonomy may use noun headings or codes when the meaning is visible. Do not
turn categories into a maturity path or sequence.

### 5.5 Explicit process / stage page

Preserve the order only when the source states an order. Temporal adjacency alone is
not causality.

### 5.6 Status page

Mixed statuses remain mixed. Do not synthesize them into `全面推进` or `已形成`.

### 5.7 Explicit relationship page

When the source explicitly states a relationship, show both endpoints and the source
predicate. Do not strengthen `支撑` into `决定`, `可衔接` into `形成闭环`, or `在此基础上`
into `缺一不可` unless the source uses that strength.

## 6. Title rules

Default to the source heading as the faithful title anchor.

When one source section is split across several pages, retain the heading and append
only the minimum page-specific scope needed to distinguish the pages.

Rewrite a title more freely only when:

- the source has no usable heading; or
- the user explicitly requested analytical / conclusion-led titles.

A faithful title cannot introduce a stronger relationship, achieved state, value
judgment, or actor role than the page evidence.

## 7. PLAN boundary

In the current v2 lean plan, `question` and `logic` are planning metadata, not source
truth.

Under faithful mode:

- treat `question` as a neutral statement of what source content the page covers;
- treat `logic` as pagination / organization duty;
- do not inherit unsupported `why`, `so what`, transformation, mechanism, value, or
  conclusion language from PLAN into Final Script;
- if PLAN wording exceeds the page evidence, repair PLAN before AUTHOR or ignore the
  unsupported framing and report the mismatch.

## 8. Meaning-preserving expression policy

Readability improvements must retain all substantive information from `full_copy`.

Stage 01 imposes no character-count limit on onscreen headings, text, or items.
Do not shorten protected meaning to meet a phrase or sentence length target.
Resolve readability through grouping, complete short sentences, layout or page scope;
semantic and structural checks still apply.

Prefer, in order:

1. remove repetition;
2. remove non-material modifiers;
3. merge equivalent source-backed statements;
4. retain substantive examples and background already selected into `full_copy`;
5. paginate when the page remains too dense.

Do not solve density by:

- inventing umbrella concepts;
- replacing concrete tasks with generic dimensions;
- collapsing named objects into labels;
- dropping conditions;
- replacing several source propositions with one stronger author summary.

## 9. Critic failure and rewrite policy

When a page fails, rewrite from the earliest failed semantic layer:

- wrong source scope -> repair PLAN/page scope;
- unresolved page-source packet -> repair `source_refs` or source bindings before prose;
- unsupported full-copy proposition -> repair `full_copy` first;
- onscreen drift -> regenerate `onscreen` from the repaired `full_copy`;
- optional supporting-field drift -> delete or repair the optional field;
- whole-deck duplication -> repair the smallest affected page boundary.

Do not line-edit a downstream sentence while leaving its unsupported semantic parent in
place.

## 10. Analytical escalation is explicit

A sparse or parallel faithful page is not evidence that analytical mode is needed.

Switch to `analytical` only when the user explicitly requests analysis, insight,
argument reconstruction, strategic deepening, or another analytical transformation and
the approved Deck Plan records `authoring_mode: analytical`.

At that point stop using this contract and load `authoring-contract.md` as the single
active analytical authority.
