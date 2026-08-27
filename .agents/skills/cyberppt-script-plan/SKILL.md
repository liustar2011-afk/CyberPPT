---
name: cyberppt-script-plan
description: Convert foundation.json into a source-constrained PPT deck plan. Preserve the source chapter set/order by default, project source sections into pages, select defensible analysis models, plan proof responsibility and page-to-page continuity, and run internal source/analysis audits before presenting the planning gate.
---

# PLAN

## Mission

Design the strongest PPT expression that can be produced from the source without silently changing its content strategy.

Output one authoritative `deck-plan.json`.

Read:

- `docs/SOURCE_FIDELITY_AND_ANALYSIS.md`;
- `references/storyline-planning.md`;
- `references/analysis-models.md`;
- `references/evidence-architecture.md`;
- `references/argument-patterns.md`.

## Pass 1 — Lock structural mode

For ordinary Word-to-PPT work:

`source_structure_mode: preserve`

Map plan chapters to `foundation.source_structure` chapter IDs in the same order.

Use `user_authorized_restructure` only after an explicit user request to reorder, remove, front-load or otherwise change source chapter strategy.

Audience, communication goal, audience_start/end and thesis may guide explanation depth and emphasis inside pages; they do not override source chapter order in preserve mode.

## Pass 2 — Source section to page projection

For each source chapter, decide how source sections become PPT pages.

Allowed default structural operations:

- `preserve`;
- `split`;
- `merge_within_chapter`.

Cross-chapter movement uses `user_authorized_cross_chapter` and requires user authorization.

Every page should record `source_scope` when source mapping is available.

## Pass 3 — Analytical deepening

For each candidate page:

1. identify source facts and explicit relations;
2. test relevant models from `analysis-models.md`;
3. select the smallest model that improves explanatory depth;
4. classify the main relation as `explicit` or `inferred`;
5. for inferred relations, record support fact IDs and confidence;
6. reject speculative links.

A taxonomy/classification is a valid analytical result. Do not manufacture arrows merely to avoid a parallel structure.

## Pass 4 — Page plan

Required fields remain:

- `question`;
- `message`;
- `logic`;
- `content`;
- `next`.

Recommended v0.4 fields:

- `source_scope`;
- `structural_operation`;
- `analysis_basis`;
- `proof`;
- `page_role`;
- `content_load`;
- `must_include`;
- `reserved_for_later`;
- `visibility_decision` when internal/restricted evidence is involved.

For internal reports, an author may add optional `content_route` to a content
page. It is an organization hint rather than a new page type, argument role, or
evidence source:

- `primary`: `state`, `diagnosis`, `system`, `action`, or `source_native`;
- optional `facets`: `background`, `current`, `progress`, `comparison`, `risk`,
  `boundary`, `coordination`, `next_step`;
- `basis` and `rationale`: the declared semantic evidence for the route.

Prefer an explicit route when the page mission is clear. Otherwise retain
`source_native`; do not infer a route from title keywords. The route defines a
default authoring sequence of **结论 → 证据 → 解读 → 含义 → 来源**. It does not
require five visible modules: “含义” is an evidence-based internal impact,
attention point, work requirement, coordination item, risk reminder, or next
arrangement, and “来源” remains a traceability field outside onscreen copy.
`page_type` continues to classify structural pages, `argument_role` continues to
control claim authority, and `page_logic_contract` remains authoritative for
page propositions, nodes, edges, and visible relation carriers.

When the page-level relationship calls for evidence to carry the visible weight,
add optional `onscreen_composition`:

- `mode: evidence_first` for taxonomy, object inventory, scene coverage, and
  other peer-evidence pages. Keep the judgment in `core_message`; modules use
  headings and evidence items without individual `text` leads.
- `mode: selective_lead` for diagnosis, mechanism, or boundary pages where a
  limited number of distinct module judgments improves reading. Declare a
  positive integer `lead_budget` equal to the maximum permitted module leads.

This policy controls the hierarchy of a page, while `onscreen_contract` controls
module semantics and `expression_mode` controls language form. It has no default
module count, word count, or required number of lead lines. Omit the field when
the plan has no reason to constrain module leads.

When Stage 02 needs a precise later QA target, add optional `stage02_readiness`.
It remains a Stage 01 preservation expectation, not a visual-layout decision:

- `continuous_sentence_signals`: complete on-screen propositions that must not
  be split into unrelated text frames;
- `containers`: semantic modules or table regions identified by stable `id`,
  visible `heading`, and `role` (`module`, `table`, or `shared`);
- `tables`: a declared container plus header-row count and `header` / `body` /
  `note` text roles.

Declare only expectations supported by the approved page argument. The plan
audit checks the declaration; final-script audit checks that its sentence
signals and container headings survive authoring. Actual wrapping, geometry,
and font-size verification remains Stage 02 work.

When a content page's visible modules can be confused as a sequence, mix different
business dimensions, or absorb a page-level conclusion, add an optional
`onscreen_contract`. Keep it source-constrained and small:

- `relation`: `parallel`, `sequence`, `hierarchy`, `matrix` or `mixed`;
- `detail_axis`: the common question answered by peer modules, such as
  `gap_manifestation` or `service_capability`;
- `expression_mode`: `phrase_led`, `sentence_led` or `mixed`; choose the
  permitted language form after `onscreen_composition` has set the lead policy;
- `modules`: the approved module headings, each with `evidence_refs` and at least
  one visible `required_signals`, plus `forbidden_signals` when useful;
- `scope_mode: exclusive` when a module must not carry another module's issue;
- `detail_policy` when role boundaries need machine checking. Declare
  `allowed_roles`, `forbidden_roles`, and regex `role_markers` for roles such as
  `gap`, `evidence`, `measure`, `outcome` or `summary`. Set
  `label_only_allowed: true` only when the approved source intentionally offers
  a label-only taxonomy and no item-level object, role, task, condition or
  boundary is available.

Use this contract to preserve the page's semantic axis and expression choice, not
to force equal item counts or identical sentence patterns. A parallel page may
legitimately have different numbers of source-grounded details in different
modules. Module headings, selective readable leads, and compact evidence details
may coexist when the page's declared composition policy permits them.

Set top-level `evidence_fit_review_mode: strict` for every source-grounded Deck
Plan. There is no legacy compatibility path. Before accepting a page judgment or visible module,
write its structured `evidence_fit_review` inside the same `deck-plan.json`.
This is an internal contract field, not a fourth authority or a separate review
artifact. Answer these questions from Foundation evidence, not from paragraph
adjacency or title keywords:

1. What one question does the module heading ask?
2. Does every evidence record answer that question directly?
3. Are the records peers on one semantic axis and at comparable granularity?
4. Are their roles compatible: institution, policy action, scenario, task,
   capability, measure, state, result or boundary?
5. Which evidence ref proves each answer?
6. Is the grouping based only on records occurring in the same paragraph?
7. What is the strongest plausible alternative parent, move or split?

Use this shape at page level and within every `onscreen_contract.modules[]`
entry that has evidence:

```json
{
  "question": "What exact page or module question is being tested?",
  "items": [
    {
      "evidence_ref": "ST0053",
      "fit": "direct",
      "role": "policy_action",
      "reason": "The source states the application requirement carried by this module."
    }
  ],
  "counter_case": "The strongest alternative grouping or boundary",
  "verdict": "keep"
}
```

Allowed `fit` values are `direct`, `indirect`, `topic_only`, `no` and
`uncertain`. A page-level indirect fit is allowed only for an explicitly
declared inferred relation. Module evidence must be `direct`: every child must
answer its visible parent question. `topic_only`, `no` and `uncertain` block
AUTHOR. A verdict of `rename`, `move`, `split` or `reject` records unfinished
repair and also blocks AUTHOR; apply the repair and reassess until the current
plan can honestly use `keep`. Every assigned evidence ref must appear exactly
once, and `counter_case` must state a concrete alternative or boundary rather
than `无` or `不适用`.

Keep this question-and-answer pass inside PLAN Critic. A narrow parent such as
`能源制度` cannot absorb an application/action requirement merely because the
two source facts share a paragraph. A supported umbrella such as `能源政策要求`
may carry both when they answer that broader question.

For role-bearing groups such as project positioning, capabilities, tasks or
validation scenarios, plan each visible item as `label: source-grounded detail`
whenever the source or approved page relation provides an object, role, task or
boundary. A bare label does not prove what that item contributes to the page.
Do not invent differentiation when the source supplies names only; use the
explicit `label_only_allowed` exception and keep the shared relationship at the
parent level.

When a page's assigned sources are rich enough that silent compression would be
risky, add optional `source_consumption` with `mode: strict`:

- the page's `source_refs` are the complete assigned inventory;
- `detail_refs` retain structural or trace-only records that need not be narrated
  one by one;
- `intentional_omissions` identifies deliberately unused records and gives a
  specific editorial reason;
- `full_prose_anchors` protects source-specific numbers, conditions, duties,
  objects, table-row details, and other facts that broad paraphrase may erase;
- `onscreen_refs` selects the representative source records that must reach the
  audience layer and maps each one through
  `onscreen_contract.modules[].evidence_refs`.

Every assigned ref outside `detail_refs` and `intentional_omissions` must be
consumed by `full_copy`. `onscreen_refs` are a deliberate subset, never a demand
to place every full-prose fact onscreen. Use this contract to make editorial
selection auditable; do not derive a word floor, item quota, or module count from
the number of source records.

## Pass 5 — Audience visibility

Set top-level `audience_scope` when determinable: internal / external / mixed / unspecified.

For external audiences, `internal_only` facts may support internal reasoning but cannot enter final-facing copy unless the user explicitly approves exposure. Record the decision on affected pages.

## Pass 6 — Internal-expert voice

For `internal`, `mixed`, or unspecified audiences, plan from the position of an
internal business expert who understands the organisation's responsibilities,
operating conditions, evidence and implementation boundaries. Customer, market,
transaction, value realisation, growth and commercialisation are normal enterprise
topics and remain available whenever the source or confirmed communication goal
supports them.

Do not address the organisation as `贵司`, adopt an external consultant identity,
or turn a factual state, diagnosis, system description or operating issue into a
generic advisory call. Work requirements and action conclusions must identify a
source-supported responsibility, problem, condition or approved objective. Judge
voice and evidence position; do not ban business vocabulary.

## Split / merge test

Split a page when it contains independent questions or proof chains that cannot remain legible together.

Merge material only inside the same source chapter when it supports one page question and source distinctions remain intact.

## Internal PLAN Critic

Run:

1. Source-structure test;
2. Section-coverage test;
3. Single-question test;
4. Relation-basis test;
5. Inference-boundary test;
6. Group-strength test;
7. Classification-vs-progression test;
8. Optionality-preservation test;
9. Audience-exposure test;
10. Analysis-depth test;
11. Evidence-strength and compression tests;
12. Continuity test.
13. Internal-expert voice test: valid enterprise topics remain available, while
    external-adviser address, viewpoint and unsupported generic advice are removed.
14. Evidence-fit challenge: every page judgment and evidence-bearing module has
    a source-bound `evidence_fit_review`; every parent exhaustively covers its
    children, siblings share one answer axis, source co-location is not used as
    hierarchy, and a counter-grouping has been considered.

Repair the same plan. Reordering across chapters is not a default repair for weak continuity.

Then run:

```bash
cyberppt-script validate plan <deck-plan.json>
cyberppt-script audit-plan <deck-plan.json> <foundation.json>
cyberppt-script review-plan <deck-plan.json> <foundation.json>
```

## Gate A

Present **脚本规划待确认** in reader-friendly form:

- preserved source chapters;
- page allocation inside each chapter;
- page question / message;
- important split/merge decisions;
- meaningful inferred logic;
- source conflicts or visibility decisions requiring user input.

Use the `review-plan` Markdown projection as the default reading strip. It is a
non-authoritative view printed for review; do not save it as a new approval,
receipt, status artifact or content authority.

Do not dump internal JSON unless requested.
