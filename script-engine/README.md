# CyberPPT Script Engine

> Independent Stage 01 script-generation subsystem for CyberPPT.

This directory is intentionally self-contained and is designed to be split into a standalone repository later.

## Responsibility

The Script Engine owns only:

1. source understanding;
2. deck planning;
3. script authoring and rewrite;
4. validation of the final script contract.

It does not own image generation, visual rendering, SVG reconstruction, editable PPTX assembly, or Stage 02 QA.

## Stable output boundary

The only required downstream artifact is:

- `dist/final-script.md`

Optional machine-readable companion:

- `dist/final-script.json`

Stage 02 must consume the final-script contract and must not depend on Script Engine internal workbench files.

## Internal pipeline

```text
SOURCE
  ↓
UNDERSTAND
  ↓
foundation.json
  ↓
PLAN
  ↓
deck-plan.json
  ↓
AUTHOR
  ↓
critique + rewrite
  ↓
final-script.md / final-script.json
```

## Authority model

Only three content artifacts are authoritative inside this subsystem:

- `foundation.json`
- `deck-plan.json`
- `final-script.md`

All other files are cache, reports, diagnostics, or derived projections.

## Loose coupling with CyberPPT Stage 02

Stage 02 receives a final script by file path. It must not require Script Engine-specific schemas, approval states, source-truth projections, or intermediate semantic artifacts.

A compatibility adapter may translate `final-script.json` or `final-script.md` into the current CyberPPT Stage 02 handoff format. The adapter belongs at the boundary and must not become part of the authoring workflow.
