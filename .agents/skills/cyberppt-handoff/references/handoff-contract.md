# CyberPPT Handoff Contract

## Purpose

`cyberppt-handoff` is the adapter between the high-quality Source Material Foundation front-end and CyberPPT's page-authoring / SCRIPT-FINAL / Stage 02 back-end. It exists to satisfy the downstream file contract without re-running CyberPPT's upstream interpretation pipeline.

## Required inputs

Foundation directory:

- `structure.json`
- `fact-base.json`

Semantic directory:

- `normalized-facts.json`
- `concept-base.json`
- `relation-graph.json`
- `argument-chain.json`
- `semantic-report.json` with `status: ok`

Outline directory:

- `deck-brief.json`
- `page-plan.json`
- `outline-report.json` with `status: ok`

When the layer-four Outline declares `editorial_authoring_mode=author_driven`, both `deck-brief.json` and `page-plan.json` must declare `editorial_authoring_status=author_edited`. A structural `status: ok` candidate with `mechanical_draft` status is not handoff-eligible and is rejected with `OUTLINE_AUTHORING_INCOMPLETE`.

Optional outline authority:

- `outline-workpack.json`; when present, its `planning_policy` is projected unchanged into `outline.json`. The file may be absent for legacy projects.

## Output tree

```text
<cyberppt-project>/
├── workbench/stages/00-source-map/
│   ├── source-registry.json
│   ├── source-units.jsonl
│   └── source-heading-tree.json
├── workbench/stages/00-semantic-understanding/
│   ├── semantic-argument-model.json
│   └── semantic-understanding.md
├── workbench/stages/01-analysis/
│   ├── source-truth.json
│   ├── outline.json
│   └── outline-human-review.md
└── integration/
    ├── authority-map.json
    └── cyberppt-handoff-report.json
```

## Authority model

The files above are compatibility projections. `authority-map.json` binds projected IDs back to authoritative Source Material Foundation IDs. The adapter must not create a second reasoning truth source.

## Source-unit projection

Each layer-two heading becomes a `cyberppt.source_unit.v1` heading unit. Each content block becomes a projected source unit. The locator retains Markdown line range and original source metadata. The adapter does not pretend a Markdown line is an original Word paragraph; `projection_locator_mode=markdown_line` makes the distinction explicit.

## Source Truth projection

Each normalized fact maps to exactly one ST record. Its statement, verification status and source evidence are preserved. Fact type → CyberPPT evidence type is a fixed lookup, not model judgment. Page usage can mechanically lift presentation priority (`high→P0`, `medium→P1`, `low/unused→P2`) without changing factual meaning or verification status.

## Semantic-model projection

The projected `cyberppt.semantic_argument_model.v1` is an interoperability view. Reconstructed argument nodes remain the page-consumable semantic nodes; source chain remains provenance context; concepts and relations are copied from layer three; inferred relations remain inferred with rationale intact; and no new MECE, causal, status, actor or scope inference is performed.

## Outline projection

Layer-four content pages become `cyberppt.outline.v2` content pages. The adapter maps audience question, page mission, key judgment, non-substitutable value, page boundaries, governing argument chain, evidence roles, content units, visual intent and transitions without re-planning page order.

When the layer-four page declares `source_heading_ids`, `primary_source_heading_id`, or `subtitle_policy`, those fields are preserved unchanged. A locked planning policy therefore remains machine-readable downstream; it is not inferred again from the projected title or prose.

## Relationship authority

`page-plan.json.evidence.relation_ids` is the page-level relationship selector. Each selected ID must resolve to one existing `relation-graph.json` record. The adapter projects that record's `subject`, `relation`, `objects`, `direction`, `condition`, `modality`, `basis`, `confidence`, source references, and authority ID without changing its semantic type or factual strength.

If a page declares no relationship IDs, `content_relations` is an empty array. The adapter must not insert a generic `contains` relationship or derive a replacement from prose, titles, or visual suggestions.

The projected relationship list remains authoritative through Stage 02:

1. `outline.json.pages[].content_relations`
2. `stage02-handoff.json.pages[].stage02_visual_input.business_relationships`
3. `deck-visual-spec.json.pages[].semantic_graph.business_relationships`
4. `PageArtifactSpec.relationships`

Each transition requires exact equality before the next projection is built. Stage 02 `connectors` and `semantic_graph.edges` are visual-composition decisions only; they may encode reading order but never replace, broaden, or modify the authoritative business relationships.

`PageArtifactSpec` retains the semantic relationship fields needed by the image model and deliberately removes audit-only `source_refs` and `authority_ref`. The final nine-part prompt must contain neither those relationship identifiers nor Source Truth, evidence, text-lock, or region identifiers. Provenance remains available in the bound source artifacts and hashes.

## Validation levels

Adapter projection validation always runs. CyberPPT runtime validation only runs with `--cyberppt-root`, using the actual lightweight `outline-audit`. A local adapter green suite does not imply CyberPPT runtime compatibility.

## Forbidden behavior

The adapter must not re-read the original source to reinterpret content, create new normalized facts, upgrade `unverified`, convert inferred relations to explicit, choose a new deck thesis, split/merge/reorder/add pages, generate page prose, or rerun CyberPPT upstream reasoning.

## Page fact-consumption invariant

`page-plan.json.evidence.normalized_fact_ids` is the page-level fact authority. The projected CyberPPT `page.source_refs` must be exactly the mapped ST records for those normalized facts. Relation IDs and argument-node IDs remain semantic context and may not broaden page fact consumption.

## CyberPPT content-unit duty mapping

Layer-four authoring roles are deterministically mapped into downstream structural duties: premise/background→premise; cause/driver→driver; problem/gap→gap; response/recommendation/implementation→response; condition/constraint/boundary→boundary; consequence/judgment/conclusion→consequence; claim/reason/instance/mechanism/support/evidence→support; detail/other→detail.

## Coordinate-system rule

Layer-two evidence lines refer to the normalized Markdown, so projected source units and Source Truth line locators use `structure.json.input_markdown` as their coordinate file. The original Office/PDF file is retained separately as `original_source_file`; the adapter never represents a Markdown line as a native Word paragraph.
