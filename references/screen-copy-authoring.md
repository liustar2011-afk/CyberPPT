# Onscreen Copy Authoring

For a reading deck, detail items retain the source-backed object, action, role,
responsibility, condition, result, or boundary. A label row such as
`术语概念、参考架构、标识目录` is an index of concepts, not explanatory detail.
Write an independently readable unit such as
`参考架构：明确与国家总体架构的映射关系`. Declare
`detail_policy.label_only_allowed: true` only when the approved source itself is
an intentionally label-only taxonomy.

## Purpose

Translate a complete page argument into presentation language without losing the page's judgment, proof logic, distinctions, or source boundaries.

## 1. Write in the correct order

Use this order:

1. complete page argument;
2. information hierarchy;
3. onscreen copy;
4. speaker notes.

Do not start by compressing source paragraphs into short labels. Premature compression is a major cause of generic, repetitive PPT copy.

### Page rewrite loop

Onscreen copy is an editorial selection from the complete page argument. Use
this loop:

1. finish the page argument and proof chain;
2. select the minimum sufficient visible propositions and evidence;
3. for dense, money, conclusion or Critic-priority pages, write one
   judgment-led candidate and one evidence-led candidate;
4. compare main-judgment visibility, ten-second comprehension, density,
   repetition, relation visibility and semantic completeness;
5. rewrite the whole information organization when the preferred candidate is
   still weak.

Choose modules from the real relationship among retained meanings. Preserve the
business object or actor, action or state, and the material result, role,
condition or boundary. Source paragraph adjacency and bullet count do not
establish a visible group.

This loop is an AUTHOR responsibility, not a new artifact or authority. Keep
candidate copy and selection reasoning internal and deliver only the repaired
script.

### Visible-payload test

A visible line passes when its wording and parent heading together let the
reader answer what the item is, what it does or what state it is in, and why the
item matters on this page. A bare name, year range, number range, keyword or
generic management verb cannot carry a module's meaning by itself.

Bind dates and numbers to their business meaning:

```text
Weak: 三阶段目标：2026年至2029年
Readable: 2026年：完成标准体系框架研究和首批标准布局
Readable: 2027—2028年：推进重点标准研制并开展应用验证
Readable: 2029年：形成覆盖建设、运营和服务的标准体系
```

The examples illustrate semantic completeness; they do not prescribe a fixed
three-item layout.

### Internal-report composition order

For internal reports, organize each content page in this authoring order:

`结论 → 证据 → 解读 → 含义 → 来源`

- **结论**: the bounded page judgment in `core_message` or a readable lead line.
- **证据**: source-grounded facts, numbers, responsibilities, status, conditions, or explicit relations that prove the judgment.
- **解读**: the page's approved relationship among the evidence; it may be a comparison, mechanism, taxonomy, boundary, or consequence.
- **含义**: the evidence-based internal impact, attention point, work requirement, coordination item, risk reminder, or next arrangement. It must stay within the source boundary and must not manufacture an action conclusion.
- **来源**: `source_refs` and evidence mappings remain in their traceable machine fields or the delivery source section, outside audience-facing onscreen wording.

This is an authoring sequence, not a mandate to add five separate cards. A thin or source-special page may combine adjacent steps, and a source-native structure may retain its own organization after the same five questions have been answered.

## 2. Separate title, judgment, and support

A page may use a topical title or a judgmental title depending on context. Do not force one title style for every page.

Regardless of title style:

- `core_message` must contain the page's complete answer or judgment;
- module headings must organize the proof or explanation;
- supporting copy must add differentiated information;
- the title, core message, and first module must not repeat the same sentence in three forms.

## 3. Build a readable semantic hierarchy

A content page normally contains:

- page title;
- optional lead / conclusion line when it materially improves comprehension;
- a small number of semantic groups;
- within each group, a short business heading and differentiated supporting copy;
- selected numbers, labels, annotations, examples, or boundary notes when needed.

Choose semantic groups by argument role, such as:

- reason;
- mechanism;
- evidence;
- stage;
- actor;
- capability;
- application;
- output;
- value;
- boundary.

Do not use parallel boxes merely because several source bullets exist.

## 4. Compression rules

- Preserve the claim, object, action, qualifier, and result that carry meaning.
- Shared predicates or qualifiers should appear once at the parent level when possible.
- Child items should carry differentiated information.
- Keep exact numbers, units, time periods, status, responsibilities, and conditions when material.
- Avoid mechanically converting every source bullet into one visual module.
- Avoid turning background details, form fields, attachment lists, or operational minutiae into equal-weight onscreen blocks.
- Numerical ordering may be used only when the source supports real sequence, phase, priority, timing, dependency, or gating.
- If a boundary controls how a claim may be understood, do not compress it away solely to make the page shorter.
- Character limits diagnose layout risk. When shortening removes the subject,
  action, state, result or boundary, split the line, promote a real proposition
  to a permitted module lead, or repair the page structure.

## 5. Relationship-first expression

Before finalizing onscreen copy, identify the page's dominant semantic relationship:

- progression;
- causality;
- hierarchy;
- comparison;
- actor interaction;
- input-output transformation;
- decision criteria;
- closed loop;
- evidence-to-conclusion.

The copy should make this relationship legible before Stage 02 decides how to visualize it.

### 5c. Internal-report content routes

`content_route` is an optional Deck Plan field for the authoring organization of a content page. It does not replace `page_type`, `argument_role`, `source_scope`, or `page_logic_contract`; those fields retain their existing structural, authority, evidence, and relationship responsibilities.

- `state`: present background, current state, progress, or review as **conclusion → factual state/progress → interpretation → attention point**.
- `diagnosis`: present a source-supported issue as **conclusion → observed evidence → cause/impact interpretation → priority or risk reminder**.
- `system`: present a principle, architecture, scope, or mechanism as **conclusion → components and boundaries → operating relationship → implementation concern**.
- `action`: present a source-supported target, arrangement, task, or safeguard as **conclusion → work basis → responsibilities/measures → coordination, checkpoint, or next step**.
- `source_native`: retain the source's special structure when the page does not have one clear route. Do not infer a route from title words alone.

Facets such as `background`, `current`, `progress`, `comparison`, `risk`, `boundary`, `coordination`, and `next_step` refine the route. They do not create a new page type or require every page to cover every facet.

## 6. Language quality

Prefer concrete institutional, business, technical, and operational wording.

Generic verbs such as “加强、提升、推动、赋能、打造、构建” require a concrete object, mechanism, or result; remove them when they add no information.

Avoid:

- empty management language;
- duplicated labels;
- slogans used as evidence;
- artificial symmetry;
- explanatory meta-language addressed to the author or operator;
- source citations replacing actual explanation;
- `source_refs` / citation codes / the word "证据" appearing inside onscreen wording. Traceability is a separate machine field rendered in its own section; the audience never reads it.

Before delivery, apply these silent-reading questions:

- Can a reader state the page's main content after roughly ten seconds?
- Does every visible line add a fact, distinction, condition, role or result?
- Can dates and numbers be interpreted without consulting the full copy?
- Does every child directly answer the question implied by its parent heading?
- Would deleting a line leave the page's explanation unchanged? If yes, remove
  it or replace it with missing evidence.

## 7. Expression modes and density

Do not impose one universal character count on every page. Density should follow the page's role and evidence burden.

Use optional page-level `onscreen_composition` to decide where module lead lines
belong before declaring a module-level `expression_mode`:

- `evidence_first`: for taxonomy, object inventory, scene coverage, evidence,
  and peer-category pages. Put the page judgment in `core_message`; every
  onscreen module uses its heading and evidence `items`, with no module `text`.
- `selective_lead`: for diagnosis, mechanism, boundary, or other pages where a
  limited number of module judgments materially improves independent reading.
  Set `lead_budget` to the exact maximum number of modules allowed to use `text`.

This is a page-composition policy, not a fixed density target. Keep the budget at
zero when facts are already legible as peer evidence, and retain a lead only when
it adds a distinct source-grounded judgment that the page-level conclusion cannot
carry alone. A plan without this optional field remains compatible with existing
authoring.

In `evidence_first`, do not move a former module judgment into the first item
and leave shorter labels below it. The renderer gives every item the same visual
level, so this creates a hidden hierarchy that readers cannot parse. Within one
module, write peer evidence at the same granularity: objects, requirements,
stages, actors, conditions, or source-supported facts answering one shared
question. Keep a needed module judgment in `core_message`, or choose
`selective_lead` and declare its budget.

When a page has an `onscreen_contract`, declare `expression_mode` as:

- `mixed` as the normal choice for explanatory pages that combine readable
  propositions with compact supporting evidence;
- `sentence_led` for judgments, problem responses, mechanisms, and boundary explanations;
- `phrase_led` only for a genuine taxonomy, metric set, object inventory, exact
  source-label set or short sequence; a sequence relation by itself does not
  justify phrase-only writing.

Under `mixed`, use a complete source-grounded proposition for a permitted module
lead when it improves independent reading, then use compact clauses or phrases for
differentiated evidence. Under `sentence_led`, every permitted lead module should
carry at least one readable proposition. `evidence_first` takes precedence over
these expression modes and keeps module `text` empty. A parallel page may use
complete sentences without becoming a progression chain.

Do not repeat one mode across the deck for visual consistency. Choose the mode
from the reading duty of each page. Diagnosis, mechanism, implementation,
responsibility, comparison and conclusion pages usually need normal sentence
syntax somewhere in the visible hierarchy.

Visible module copy must not end with a period, comma, semicolon, enumeration mark, or other punctuation/symbol. The module boundary already provides the visual pause: use `heading` + complete lead `text` without a terminal glyph, then compact supporting items without terminal glyphs. Keep internally meaningful notation such as `GB/T 13016`, `A3` and `IEC 61970`; the renderer's `标题：说明` separator is structural and remains outside the authored text.

A strong page can be concise or dense. The requirement is that hierarchy stays readable and every visible line performs a distinct semantic job.

Default toward a populated hierarchy rather than a flat one. For a page whose `content_load` is `standard` or `dense`, a module built from a single `heading` + one-line `text` and nothing else is the exception, not the default — most modules on such a page should carry an `items` list of concrete sub-points (named entities, numbers, roles, conditions) so the module proves something rather than just naming a topic. Reserve the flat single-line form for `light` pages, transitions, or a module that is genuinely atomic (one number, one relationship, one decision).

When a page is overloaded, first decide whether to:

1. remove non-essential material;
2. move explanation to speaker notes;
3. merge redundant statements;
4. split independent audience questions into separate pages.

Overload and low density are different failure modes — do not fix one by silently causing the other. If compression starts erasing the sub-points that make a module concrete, the page needs a split (see storyline-planning.md's split test), not a thinner module.

The compact-detail threshold remains 30 meaningful (Chinese/Latin/numeric) characters for items and unstructured fragments. A single source-grounded module lead in the `text` field may exceed that threshold up to 90 meaningful characters when it carries one business claim. This distinction keeps natural sentence-led copy available while blocking paragraph-like detail.

A page has no universal character-count or module-count target. Review density through the evidence and business meaning that the page must carry: source-grounded facts, numbers, roles, conditions, boundaries, and an earned internal implication when the page route declares one. Add a line only when it carries a missing source-grounded point. Do not add filler, duplicate a claim, or create a relationship-narration module to satisfy a numerical target.

When the approved Deck Plan declares `delivery_mode: self_read`, every
`standard` or `dense` content page must carry enough visible semantic payload to
be understood without speaker notes. The deterministic audit scales the floor
with the number of approved modules and counts compact parallel taxonomy details
as separate semantic units. Cover, agenda, chapter transition and ending pages
remain exempt. This mode changes the visible explanation duty; it does not
authorize invented evidence, repeated judgments or a fixed card layout.

## 5a. Density is earned by new facts, never by restating one

Do not pad a page by adding a second `items` line that says the same thing as the first in different words. `cyberppt-script lint` catches near-duplicate lines within a module. When a module lacks proof, return to `foundation.json` and pull a sub-fact, number, role, or condition that the page is already responsible for; do not paraphrase what is already on the page. Within a module, order lines as supported by the source — chronologically for a sequence, causally for a mechanism, by stated priority for a list — rather than in the order added during drafting.

## 5b. A "relationship" module is not a density strategy

Every onscreen module must carry a concrete distinguishing fact — a number, named entity, role, condition, or boundary — that is not already stated by the other modules on the same page. A module whose entire content is commentary on how the *other* modules relate to each other ("A与B共同构成…的基础"、"C衡量…是否合理"、"D检验…能否…") adds no new fact; it just restates what the peer modules already show, wearing a "关系"/"相互关系"/"对应关系" heading. This is the multi-module version of the 5a anti-pattern (restating a point to reach the density floor) and is banned for the same reason, even though 5a's line-similarity check does not catch it (the restatement is spread across a whole module, in different words, not one duplicate line).

The dominant semantic relationship identified in section 5 belongs in `visual_thesis` (as the page's stated judgment) and in `relationships` (as the structure Stage 02 renders) — and it may thread through `full_copy`'s connective sentences. It does not need, and should not get, its own onscreen card unless that card itself introduces a fact the audience has not yet seen (e.g. a genuine dependency the audience must act on, stated as that dependency's concrete content, not as a meta-description of "the relationship"). When the source material is thin and no further evidence duty exists, plan it as `content_load: light` rather than manufacturing a relationship-narration module.

## 5c. Keep source-backed payload attached to detail labels

For groups that express positioning, capabilities, tasks, responsibilities or
validation scenarios, a child item should normally answer what the named item
does on this page:

```text
绿色低碳：检验标准在该类业务中的适用性
主体接入：支撑参与主体可信接入行业节点
```

Use one colon between the business label and its source-grounded explanation;
do not add terminal punctuation. If the approved source contains only a counted
or named taxonomy, preserve the names and declare `label_only_allowed` in PLAN.
Never fabricate item-level differentiation to satisfy this form.

## 5d. Challenge every semantic group before delivery

Indentation asserts a real parent-child relationship. For every module, answer:

1. What single question does the parent ask?
2. Does every child answer it directly?
3. Are all children peers on one semantic axis and at comparable granularity?
4. Are their semantic roles compatible?
5. Which source ref proves each placement?
6. Did the grouping arise only because facts share a paragraph?
7. What alternative parent, move or split best challenges the current choice?

Use `yes / no / uncertain` internally. `No` and `uncertain` trigger repair; they
cannot be waived by a fluent explanation. Source adjacency does not establish
taxonomy. Keep this self-review inside PLAN/AUTHOR Critic and expose only the
repaired copy or a deterministic failure such as
`ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY`.

## 6a. `full_copy` must carry the page argument

`full_copy` is the fully-argued paragraph a presenter could read verbatim and carries no fixed character floor. It must establish the page conclusion, the source-grounded proof, the approved relationship, and any declared business meaning. When any of those responsibilities is absent, pull the missing enumerated sub-point, number, named entity, condition, or synthesis sentence from `foundation.json`; do not pad by restating the same claim in different words.

For a strict `source_consumption` page, complete the source-consumption pass
before compression. Every assigned record outside declared details and specific
omissions must survive in `full_copy`; source-specific anchors protect facts that
generic wording can easily swallow. Then project only `onscreen_refs` into the
mapped visible modules. This keeps the direct relationship
`assigned source → complete argument → representative onscreen evidence` while
avoiding both silent loss and a one-source-one-card layout.

## 8. Renderer independence

Do not specify font, color, icon style, decorative treatment, image-generation model, layout coordinates, or visual-style preset in the final script. Those belong to Stage 02.
