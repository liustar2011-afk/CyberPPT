---
name: cyberppt-script-workflow
description: Use as the single navigation entry for the standalone CyberPPT Script Engine. Route source-to-script work through UNDERSTAND, PLAN, and AUTHOR; route targeted revisions to EDIT PAGE. Keep Stage 02 and PPTX production outside this repository.
---

# CyberPPT Script Engine Workflow

## Purpose

This is the single routing Skill for the standalone Script Engine.

The canonical content pipeline is:

`SOURCE -> UNDERSTAND -> PLAN -> AUTHOR -> FINAL SCRIPT`

Targeted revision after whole-deck authoring uses `cyberppt-script-edit-page`.

## Route selection

### New source-to-script task

1. `cyberppt-script-understand`
2. `cyberppt-script-plan`
3. Gate A — Deck Plan
4. `cyberppt-script-author`
5. Gate B — Final Script

### Existing final script, targeted page revision

Use `cyberppt-script-edit-page` with the current final script, target page plan, relevant foundation evidence, and adjacent pages.

### Stage 02 / image / PPTX task

Stop at the final-script boundary. This repository does not route or execute visual production.

## Authority

The only authoritative content artifacts are:

- `foundation.json`
- `deck-plan.json`
- `dist/final-script.md`

`dist/final-script.json` is an optional machine-readable mirror.

Do not create Source Truth projections, alternate Outline authorities, page approval ledgers, or renderer-specific state as part of this workflow.

## Delivery boundary

The required downstream output is `dist/final-script.md` using the parser-compatible format defined by `cyberppt-script-author`.

The host CyberPPT repository may receive this file by absolute path. No Script Engine internal artifact is part of the downstream API.
