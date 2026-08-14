---
name: cyberppt-handoff
description: Use when validated Source Material Foundation semantics and a validated PPT page plan must enter an existing CyberPPT page-authoring or production workflow without letting CyberPPT reinterpret the source material.
---

# CyberPPT Handoff

## Overview

Project the validated Source Material Foundation front-end into CyberPPT-compatible Stage 00/01 files, then hand control to CyberPPT's downstream page authoring and production flow. This Skill is a deterministic compatibility compiler, not a reasoning stage.

## Authority rule

The authoritative inputs are the layer-two `structure.json` / `fact-base.json`, layer-three `normalized-facts.json` / `concept-base.json` / `relation-graph.json` / `argument-chain.json`, and layer-four `deck-brief.json` / `page-plan.json`. CyberPPT files generated here must declare `projection_only` and must preserve trace-back mappings.

**Do not infer, summarize, merge, reprioritize, upgrade status, invent relations, or redesign pages in this Skill.** If a required CyberPPT field cannot be derived mechanically, stop with an adapter error instead of guessing.

Read `references/handoff-contract.md` before export. Read `references/cyberppt-patterns-adopted.md` when changing the adapter contract.

## Workflow

1. Require `semantic-report.json` and `outline-report.json` with `status: ok`.
2. Validate the in-memory projection:

```bash
python scripts/validate.py <foundation-dir> <semantic-dir> <outline-dir>
```

3. Export a CyberPPT-compatible project tree:

```bash
python scripts/export.py <foundation-dir> <semantic-dir> <outline-dir> -o <cyberppt-project>
```

The export writes projected source units, semantic model, Source Truth, `cyberppt.outline.v2`, human review Markdown, `authority-map.json`, and `cyberppt-handoff-report.json`.

4. If a real local CyberPPT checkout is available, run its actual lightweight outline audit during export:

```bash
python scripts/export.py <foundation-dir> <semantic-dir> <outline-dir> -o <cyberppt-project> --cyberppt-root <CyberPPT-repo>
```

Without that option, `runtime_validation.status` must remain `not_run`. Local adapter tests never count as CyberPPT runtime validation.

## CyberPPT boundary

After handoff, use CyberPPT's mature downstream authoring/production mechanisms such as `cyberppt-write-single-page`, final script assembly to SCRIPT-FINAL, and Stage 02 visual/production flow.

Do not run `prepare-semantic-understanding` on the projection. Do not run `compile-source-truth` on the projection. Do not run `compile-outline-draft` on the projection. Those commands would reactivate CyberPPT's upstream reasoning chain and overwrite the quality decisions made by the authoritative front-end.

## Projection semantics

- Source units are mechanical projections of layer-two sections/blocks.
- Source Truth records are one-to-one projections of normalized facts.
- Inferred layer-three relations remain inferred and can never become `source_explicit`.
- CyberPPT content units are mechanical projections of the validated layer-four `argument_chain` and `evidence_roles`. Their `argument_duties` are mapped only into CyberPPT's structural duty vocabulary (`premise`, `driver`, `gap`, `response`, `support`, `consequence`, `boundary`, `detail`).
- Page `source_refs` are exactly the Source Truth projections of that page's explicit `normalized_fact_ids`. Relations and argument nodes may explain structure but may not broaden page fact consumption.
- A broad argument node is kept only as context when it contains facts outside the current page; it is not promoted to `primary_argument_node_id`.
- `trace_only` evidence remains traceability evidence; it is not promoted into a required onscreen module.
- Page order, audience question, page mission, core judgment, exclusions, reservations and transitions come directly from `page-plan.json`.

## Stop boundary

This Skill stops at a validated compatibility projection. It does not write page prose, onscreen copy, speaker notes, image prompts, SVG, PPTX, or visual composition.
