---
name: cyberppt-source-foundation
description: Use when converting source documents into a trustworthy CyberPPT outline and page-authoring handoff, especially when the legacy CyberPPT source analysis or semantic stages are too mechanical or unreliable.
---

# CyberPPT Source Foundation

## Purpose

Use the repository's high-quality source-material front end before CyberPPT page authoring. This is the default route for new source-material-to-PPT work unless the user explicitly requests the legacy Stage 00/early Stage 01 flow.

Authoritative chain:

`source -> source.md -> structure/fact base -> semantic outputs -> deck brief/page plan -> CyberPPT projection -> cyberppt-write-single-page`

The projection is a compatibility artifact only. It must never become a second semantic authority.

## Required sequence

1. Run `scripts/source_foundation_pipeline.py <source> -o <project>/workbench/source-foundation --prepare-semantic --report`.
2. Use `business-semantic-understanding` to author the four semantic outputs in the prepared semantic directory, then run its validator with `--report`.
3. Before planning pages, derive 2-3 source-supported communication-goal candidates from the semantic outputs and recommend one. After the user chooses or edits the goal, continue.
4. Run `scripts/source_foundation_outline.py <semantic-dir> -o <outline-dir> --request-text "<selected communication goal and constraints>"`.
5. Use `ppt-outline-planning` to author `deck-brief.json` and `page-plan.json`; validate them and render `ppt-outline.md`. Present the outline to the user for the existing human gate.
6. After outline approval, run `scripts/source_foundation_handoff.py <foundation-dir> <semantic-dir> <outline-dir> -o <project> --cyberppt-root . --force`.
7. Read `integration/cyberppt-handoff-report.json`. Proceed only when projection validation is `ok`; runtime audit must be recorded when the local CyberPPT checkout is available.
8. Continue with the existing `cyberppt-write-single-page` skill. Do not rerun legacy semantic understanding, Source Truth authoring, or mechanical outline compilation over the approved foundation outputs.

## Authority rules

- `normalized-facts.json`, `concept-base.json`, `relation-graph.json`, `argument-chain.json`, `deck-brief.json`, and `page-plan.json` are upstream authorities.
- Projected `semantic-argument-model.json`, `source-truth.json`, and `outline.json` exist only to satisfy CyberPPT downstream consumers.
- Handoff code may map IDs and fields but may not invent claims, merge facts, add page evidence, infer responsibilities, or raise maturity/status.
- CyberPPT page `source_refs` must equal the page's explicitly authorized normalized-fact set after deterministic ID projection.

## Page planning discipline

Every content page must define one audience question, one page mission, one core judgment, one non-substitutable value, one governing argument chain, evidence roles, `must_not_include`, `reserved_for_later`, split risk, and page-to-page transitions. Related evidence is not automatically onscreen evidence.

## Do not use

Do not use this skill for an already approved `script-final.md`, isolated Stage 02 visual work, image generation, SVG reconstruction, or PPTX QA.
