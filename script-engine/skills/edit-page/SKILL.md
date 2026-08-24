---
name: cyberppt-script-edit-page
description: Edit or rewrite one or a small number of pages inside an existing Script Engine final script while preserving whole-deck narrative, source fidelity, adjacent-page boundaries, and the final-script contract. Use for targeted revision after whole-deck authoring; do not use as the default full-deck generation path.
---

# EDIT PAGE

## Mission

Repair or improve targeted pages without allowing local optimization to damage the deck-level narrative.

## Inputs

- current `final-script.md` or `final-script.json`;
- corresponding `deck-plan.json` page entries;
- `foundation.json` evidence needed by the target pages;
- previous and next page contracts;
- user revision instruction.

## Procedure

1. Read the target page and both adjacent pages when available.
2. Restate internally what the target page receives from the previous page and must hand to the next page.
3. Diagnose the root weakness: message, argument, evidence, hierarchy, wording, onscreen density, or semantic visual thesis.
4. Rewrite the page in context.
5. Re-check source fidelity and cross-page duplication.
6. Update both canonical Markdown and the JSON mirror when both are maintained.

## Boundary

Do not silently change chapter structure or the mission of other pages. When the requested edit exposes an upstream deck-plan defect, report that defect and make only the smallest necessary upstream adjustment.

Do not add renderer-specific styling, image prompts, or PPTX geometry.
