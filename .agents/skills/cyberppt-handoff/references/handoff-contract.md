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
