---
name: cyberppt-script-understand
description: Build the unified source foundation for PPT script generation. Preserve source hierarchy, atomic facts, strength, responsibilities, numbers, boundaries and provenance; then run a latent-logic pass to record defensible explicit/inferred relationships. Do not plan slides or rewrite chapter strategy.
---

# UNDERSTAND

## Mission

Create a compact, complete semantic foundation that preserves what the source says and exposes source-supported relationships that the Word text may leave implicit.

Output: `foundation.json`.

Read:

- `docs/SOURCE_FIDELITY_AND_ANALYSIS.md`;
- `references/analysis-models.md`;
- `references/evidence-architecture.md`.

## Pass 1 — Source structure

Recover the document hierarchy before semantic compression:

- front matter;
- chapters;
- sections/subsections;
- appendices/closing;
- explicit ordering and section boundaries.

When `source_extract.txt` is available, build `.cache/source-index.json` and use it to seed `source_structure`. The cache is derived; `foundation.json.source_structure` is the downstream semantic authority.

Prefer project-relative source paths and retain source identity/hash when available.

## Pass 2 — Atomic facts

Extract facts at a granularity that allows later recombination without silently upgrading a whole group.

Preserve:

- statement strength;
- numbers and dates;
- status and maturity;
- actors and responsibilities;
- conditions and exclusions;
- rights and authorization boundaries;
- explicit relations.

Use `group_id` to associate related atomic facts instead of merging several materially different claims into one oversized fact.

Assign `visibility` when the source clearly distinguishes internal-only, restricted or external-safe material.

## Pass 3 — Explicit relations

Record relationships directly stated by the source, such as:

- sequence;
- dependency;
- maturity transition;
- role assignment;
- classification;
- authorization;
- cause/effect when explicitly stated.

Use `basis: explicit`.

## Pass 4 — Latent Logic Mining

Use `references/analysis-models.md` as reasoning lenses. Test whether source facts support deeper relationships that are useful for PPT expression:

- problem/tension;
- causal or enabling chain;
- problem-to-response mapping;
- resource transformation;
- actor collaboration;
- capability layering;
- maturity progression;
- risk-control-protection;
- value formation;
- evidence synthesis.

For every accepted inferred relation:

- set `basis: inferred`;
- record supporting fact IDs in `support`;
- record `confidence`;
- keep the wording no stronger than its support.

If the relationship needs a new external premise, treat it as speculative and do not write it into authoritative `relations` or `arguments`.

## Pass 5 — Group-strength and inference validation

Before delivery, test:

- does a group-wide claim hold for every member or need an exception?
- did classification become sequence without evidence?
- did correlation become causality without a mechanism?
- did a sufficient condition become a necessary condition?
- did a plan become a completed fact?
- did internal-only information lose its visibility marker?

## Pass 6 — Completeness

Compare Foundation against source structure and critical content. Record unresolved contradictions or missing evidence as `open_questions`.

Run:

```bash
cyberppt-script validate foundation <foundation.json>
cyberppt-script audit-foundation <foundation.json>
```

## Hard rules

- Do not create PPT chapters or pages.
- Do not rewrite source chapter order.
- Do not draft final presentation copy.
- Do not upgrade fact strength or policy/commitment status.
- Do not include speculative relationships as authoritative relations.
- Source completeness has priority over early compression.
