# Authoring Method v0.4

## Goal

Convert mature formal Word material into analytically stronger PPT scripts while preserving the source's content boundary and chapter structure.

The authoritative workflow remains:

`foundation.json -> deck-plan.json -> final-script.md`

## 1. Source first

The source document determines what the material covers and, by default, the chapter order in which it is covered. Script Engine does not silently redesign the source's business emphasis.

`foundation.json.source_structure` records this hierarchy for PLAN.

## 2. Analytical understanding

UNDERSTAND performs two distinct tasks:

1. preserve atomic facts, numbers, responsibilities, status, constraints and explicit relations;
2. run a Latent Logic pass using `references/analysis-models.md` to identify source-supported inferred relationships.

Relations are classified as `explicit` or `inferred`. Speculative relationships are excluded from authoritative relations.

## 3. Source-constrained planning

PLAN projects the source hierarchy into PPT pages.

Each page keeps the compact planning surface:

- `question`
- `message`
- `logic`
- `content`
- `next`

v0.4 adds source-control fields when useful:

- `source_scope`
- `structural_operation`
- `analysis_basis`

Existing optional fields such as `proof`, `content_load`, `must_include` and `reserved_for_later` remain available.

## 4. Allowed structural transformation

Without separate user authorization, PLAN may:

- preserve a source section as one page;
- split a dense source section into multiple pages;
- merge closely related content within the same source chapter.

Cross-chapter movement or a new chapter strategy requires explicit user authorization.

## 5. Analytical page construction

AUTHOR follows:

`source facts -> selected analysis model -> bounded interpretation -> page judgment -> proof chain -> full copy -> onscreen copy`

The engine should expose latent logic when the source supports it. It should also recognize that classification, taxonomy and parallel dimensions are valid analytical structures and do not need artificial process arrows.

## 6. Inference discipline

A useful analysis can be stronger than the source's surface wording while remaining inside its semantic evidence.

Allowed: explain how several facts fit together.

Disallowed: create a new fact, unsupported causal mechanism, group-wide overgeneralization, necessary condition, current numeric gap, ranking, forecast or commitment.

## 7. Audience visibility

Audience scope controls exposure, not default chapter order. `internal_only` content remains available to the internal proof process but stays out of external-facing script prose unless explicitly approved.

## 8. Critic tests

The v0.4 Critic prioritizes:

- source structure;
- section coverage;
- single-question pages;
- relation basis;
- inference boundary;
- group-claim strength;
- classification vs progression;
- optionality preservation;
- audience exposure;
- analytical depth;
- compression loss;
- presentation hierarchy.

## 9. Stable user experience

The natural-language entry remains:

`根据这个 Word 生成 PPT 脚本。`

The user-facing gates remain:

1. `脚本规划待确认`;
2. `最终脚本已生成`.

The deeper analysis stays inside the existing agent workflow.
