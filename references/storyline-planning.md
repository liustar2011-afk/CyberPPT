# Source-Preserving Storyline Planning

## Purpose

Convert the source document's existing chapter structure into a coherent PPT
page chain. Preserve source chapter identity, coverage and order while grouping
adjacent source chapters into audience-readable presentation chapters.

Read `docs/SOURCE_FIDELITY_AND_ANALYSIS.md` first.

## 1. Source structure comes first

Before allocating pages, read `foundation.json.source_structure` and identify:

- chapter order;
- section hierarchy;
- source-defined emphasis;
- explicit sequences, classifications and boundaries;
- sections that are too dense or too small for one PPT page.

Default mode is `presentation_grouping`.

Map every presentation chapter to one or more adjacent source chapters. The
flattened mapping must reproduce the source chapter sequence exactly. Do not
reorder, front-load, delete or duplicate source chapters unless the user
explicitly authorizes restructuring.

## 2. Recover the source's narrative continuity

A formal Word document may express its logic implicitly. PLAN should identify the relationship already present across chapters and sections, for example:

- background -> mechanism -> service -> cooperation -> implementation;
- requirement -> capability -> application -> safeguard;
- current condition -> response -> operation -> result.

This recovered continuity explains the source order. It does not authorize a new order.

Audience start/end and a deck thesis guide how adjacent source chapters are
grouped for oral comprehension. They do not authorize source reordering or loss.

## 3. Use analysis models inside structural boundaries

Read `.agents/skills/cyberppt-script-understand/references/analysis-models.md`.

Within each chapter, test whether the source supports a deeper analytical structure such as:

- tension / diagnosis;
- cause / mechanism;
- problem-to-response mapping;
- actor interaction;
- resource transformation;
- maturity progression;
- risk-to-control logic;
- evidence synthesis.

The goal is analytical depth, not a new content strategy.

## 4. Build presentation chapters and the page chain

Target no more than four presentation chapters for a normal formal deck and no
more than six without a documented exception. Group by adjacent argument roles,
audience questions and handoffs; lexical similarity alone is insufficient.

For multi-chapter formal decks, use cover, agenda, one transition page before
each presentation chapter, content pages and ending. Single-chapter decks omit
the transition page.

For every page, answer:

- `source_scope` — which source section(s) this page is derived from;
- `structural_operation` — preserve / split / merge_within_chapter / user_authorized_cross_chapter;
- `question` — what audience question is resolved here;
- `message` — what answer or bounded judgment the source supports;
- `logic` — which analytical or presentational relationship organizes the page;
- `content` — which source-critical material must survive;
- `next` — how the next source-derived page follows.

Optional fields may add `page_role`, `proof`, `content_load`, `receives`, `must_include`, `reserved_for_later`, and `analysis_basis`.

## 5. Split / merge rules

Split when one source section contains:

- multiple independent questions;
- multiple proof chains;
- incompatible dominant relationships;
- too much information to preserve distinctions on one page.

Merge source material into one content page only within the same source chapter when:

- adjacent or closely related sections answer the same page question;
- distinctions and boundaries remain intact;
- source order remains legible.

Cross-chapter merge or movement requires explicit user authorization.

Grouping adjacent source chapters under one presentation chapter is a navigation
operation and does not merge their facts into one page. Record it with
`group_adjacent_source_chapters` and retain each page's source scope.

## 6. One page, one primary question

A page may carry several source facts, but they must serve one primary question. If a secondary item has no role in the page argument, defer it, merge it elsewhere inside the same chapter, or keep it in appendix/supporting material.

## 7. Evidence and relation basis

Every material page message should know:

- proof method;
- evidence fact IDs;
- relation basis: `explicit` or `inferred`;
- material boundaries / qualifiers;
- visibility constraints.

An inferred relationship is acceptable when source facts support it without an external premise. Record the supporting fact IDs and confidence.

## 8. Content-load rhythm

Use `light / standard / dense` only as a content-planning signal. Do not use density pressure to reorder source chapters or delete important source material.

## 9. PLAN self-review tests

### Source-structure test

Does the presentation-chapter mapping cover every source chapter exactly once
and preserve source order unless the user authorized restructuring?

### Section-coverage test

Is each source-critical section assigned to one or more pages, intentionally reserved, or explicitly excluded for a user-approved reason?

### Single-question test

Does each content page resolve one primary question?

### Relation-basis test

Can every analytical relation be labeled `explicit` or `inferred` with support? Remove speculative links.

### Analytical-depth test

Has the page improved on raw Word structure when a defensible classification, tension, mechanism, mapping, synthesis or value relationship is available?

### Evidence-strength test

Does wording strength match the supporting facts and their qualifiers?

### Audience-exposure test

For external or mixed audiences, has `internal_only` or `restricted` material been kept out unless explicitly approved?

### Cross-chapter leakage test

Has content moved across source chapters without explicit authorization?

### Coverage and compression test

Have material numbers, responsibilities, conditions, rights, status and distinctions survived planning?

### Continuity test

Do adjacent pages explain the source's existing progression? If the relation is weak, improve the bridge or page structure before considering reordering.

## 10. Plan rewrite rule

PLAN drafts and then repairs the same `deck-plan.json`. Do not create a second outline authority or expose internal critique by default.
