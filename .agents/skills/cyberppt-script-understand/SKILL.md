---
name: cyberppt-script-understand
description: Build the unified source foundation for PPT script generation. Preserve source hierarchy, atomic facts, strength, responsibilities, numbers, boundaries and provenance; then run a latent-logic pass to record defensible explicit/inferred relationships. Do not plan slides or rewrite chapter strategy.
---

# UNDERSTAND

## Mission

Create a compact, complete semantic foundation that preserves what the source says and exposes source-supported relationships that the Word text may leave implicit.

Output: `foundation.json`.

This is the default `script` profile for ordinary PPT script work. It consumes
the deterministic `.cache/source-index.json` plus selected source text and
writes the semantic result directly into the existing Foundation authority.
Use the full Source Truth route only for `strict/legacy` projects.

This is the first of the three authoritative Stage 01 script artifacts. The
following `deck-plan.json` and `dist/final-script.md` are produced by PLAN/AUTHOR
after the semantic foundation and the planning gate; this Skill does not create
or replace either of them.

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

From the CyberPPT repository root, run:

```bash
.venv/bin/python3 -m cyberppt prepare-source-context <project>
.venv/bin/python3 -m cyberppt prepare-script-foundation <project> --profile script
```

The first command uses native DOCX, text, PPTX and optional XLSX extraction and
writes only `script/.cache/source-index.json`. The second prints the direct
Foundation authoring task. The cache is derived;
`foundation.json.source_structure` is the downstream semantic authority.
Install `openpyxl>=3.1,<4` when native XLSX row extraction is required.

The derived cache also groups caption, native table, formula, image and chart
units into stable `asset_candidates`. Treat these as review prompts only. When
an asset can materially carry an argument, promote it into Foundation
`source_assets` while preserving its candidate ID, kind, locator and complete
`source_unit_refs`. Author its meaning, bind one or more `argument_node_ids`
whose evidence intersects those refs, and record `wrong_reading` so later
planning cannot turn a chart correlation, table row or formula into a stronger
claim. Set `presentation_role: money_slide` only for an intended peak argument;
that role makes a missing `wrong_reading` blocking.

For `reading_recommendation.mode: long`, keep every source heading in the
argument skeleton, record each section as `deep_read`, `mapped` or `excluded`,
and give every exclusion a reason. Mapped previews support routing and section
understanding. Deep-read the cited source units before authoring exact numbers,
dates, responsibilities, status, conditions, exclusions or strong conclusions.
Before authoring a long-mode Foundation, show the proposed communication goal,
mapped/deep-read selection and exclusion reasons in the conversation. Apply the
user's changes to `reading_strategy`; do not create a confirmation artifact.

Prefer project-relative source paths and retain source identity/hash when available.

## Pass 2 — Atomic facts

Extract the facts that carry the document thesis and supporting argument,
including key numbers, dates, responsibilities, states, conditions, boundaries
and figure interpretation. Ordinary explanatory paragraphs may remain available
through source units without becoming one authored fact each.

Preserve:

- statement strength;
- numbers and dates;
- status and maturity;
- actors and responsibilities;
- conditions and exclusions;
- rights and authorization boundaries;
- explicit relations.

Use `group_id` to associate related atomic facts instead of merging several materially different claims into one oversized fact.

For `source_consumption_contract_version: 2`, a fact or constraint that cites a
compound paragraph, multiple table rows, or multiple list items must expose one
`semantic_units[]` entry for every independently preservable payload. Each unit
must retain its text and exact `source_unit_ref(s)`. Short, genuinely atomic
facts may remain lightweight. A category label cannot replace source-backed
objects, actions, responsibilities, conditions, outputs, or boundaries.

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

The audit automatically cross-checks `reading_strategy` against the sibling
`.cache/source-index.json` when that v2 cache exists.

## Hard rules

- Do not create PPT chapters or pages.
- Do not rewrite source chapter order.
- Do not draft final presentation copy.
- Do not upgrade fact strength or policy/commitment status.
- Do not include speculative relationships as authoritative relations.
- Source completeness has priority over early compression.
