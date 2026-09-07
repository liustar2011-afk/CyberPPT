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
- page-bound `source_refs`;
- adjacent-page boundary;
- source chapter heading and relevant source structure;
- delivery mode and audience exposure boundary.

The Deck Plan defines the available evidence scope. It does not authorize AUTHOR to
invent a stronger question, conclusion, mechanism, or value thesis.

### Step 2 — Resolve exact source evidence

Read the Foundation records named by the page's `source_refs` and, where source-unit
references are available, read the exact underlying source text before drafting.

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

Finish and review `full_copy` before writing `onscreen`.

Every visible proposition must have a direct semantic parent in `full_copy`.

Allowed onscreen operations:

- select;
- merge equivalent nearby source-backed statements;
- lightly rephrase;
- shorten wording while preserving protected payload;
- use source-native labels when their parent/child structure keeps the meaning clear.

Forbidden onscreen operations:

- add a new conclusion;
- add a new relation;
- add a mechanism, capability, result, value, or implication;
- strengthen status or modality;
- remove a condition that changes meaning;
- change the speaking position;
- turn a source label into an invented business judgment.

When safe shortening is uncertain, copy the relevant `full_copy` passage verbatim.
Longer visible text is preferable to semantic drift.

### Step 7 — Run Full-copy <-> Onscreen Critic

For each heading, lead, text line, and item:

- identify its parent passage in `full_copy`;
- confirm no new actor, object, number, date, status, responsibility, condition,
  relation, or claim strength appears;
- confirm source-native parallel structures remain parallel;
- confirm source-defined process or stage order is retained;
- confirm formal instrument identity is unchanged.

A visible line without a defensible `full_copy` parent must be removed or rewritten
from the parent passage.

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

## 8. Safe compression policy

Compression is successful only when meaning is unchanged.

Prefer, in order:

1. remove repetition;
2. remove non-material modifiers;
3. merge equivalent source-backed statements;
4. move subordinate examples to notes when they do not change the visible claim;
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
