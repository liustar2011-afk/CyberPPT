# Script Engine Agent Contract

## Scope

This subtree owns PPT script generation only.

Allowed responsibilities:

- understand source materials;
- preserve facts, boundaries, terminology, numbers, and provenance;
- define the deck communication goal;
- plan chapters and pages;
- construct whole-deck narrative and page arguments;
- write full page content, onscreen copy, and speaker notes;
- critique and rewrite scripts;
- validate the final-script delivery contract.

Forbidden responsibilities:

- image generation;
- visual style selection;
- SVG generation;
- editable PPTX assembly;
- image-to-PPT reconstruction;
- Stage 02 visual QA.

## Canonical workflow

`UNDERSTAND -> PLAN -> AUTHOR -> CRITIQUE -> REWRITE -> DELIVER`

Do not insert compatibility projections or renderer-specific work into this workflow.

## Authoritative artifacts

Only these are authoritative content artifacts:

1. `foundation.json`
2. `deck-plan.json`
3. `final-script.md`

`final-script.json` is a machine-readable mirror of the canonical Markdown delivery.

Diagnostics, caches, reports, temporary drafts, and adapter outputs are derived artifacts.

## Writing priority

Optimize for:

1. source fidelity and completeness;
2. clear deck-level narrative;
3. page-level argument quality;
4. concise and readable onscreen copy;
5. continuity across adjacent pages;
6. renderer-independent semantic visual guidance.

Schema completion is never a substitute for professional authoring judgment.
