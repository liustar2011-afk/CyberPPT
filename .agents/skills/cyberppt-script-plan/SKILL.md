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

## Pass 5 — Audience visibility

Set top-level `audience_scope` when determinable: internal / external / mixed / unspecified.

For external audiences, `internal_only` facts may support internal reasoning but cannot enter final-facing copy unless the user explicitly approves exposure. Record the decision on affected pages.

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

Repair the same plan. Reordering across chapters is not a default repair for weak continuity.

Then run:

```bash
cyberppt-script validate plan <deck-plan.json>
cyberppt-script audit-plan <deck-plan.json> <foundation.json>
```

## Gate A

Present **脚本规划待确认** in reader-friendly form:

- preserved source chapters;
- page allocation inside each chapter;
- page question / message;
- important split/merge decisions;
- meaningful inferred logic;
- source conflicts or visibility decisions requiring user input.

Do not dump internal JSON unless requested.
