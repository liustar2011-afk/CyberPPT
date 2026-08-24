# Script Engine Architecture

## Goal

Provide a focused, high-quality PPT script-generation engine with a small authority surface and a stable downstream contract.

## Design principles

### 1. Authoring complexity belongs in AUTHOR

The subsystem keeps source understanding and planning compact. Narrative construction, argument design, page writing, critique, and rewrite carry the creative complexity.

### 2. Internal schemas are private

`foundation.json` and `deck-plan.json` are implementation details of Script Engine. Downstream systems must not parse them.

### 3. One stable delivery contract

`final-script.md` is the human-readable canonical delivery artifact. `final-script.json` is an optional machine-readable mirror.

### 4. Compatibility is an adapter concern

Any conversion needed by the existing CyberPPT Stage 02 is implemented as a boundary adapter. Compatibility projections must not become authoring stages.

### 5. Whole-deck first, page editing second

The default authoring order is:

1. whole-deck narrative;
2. section-level continuous writing;
3. page-level refinement;
4. whole-deck critique;
5. rewrite;
6. final contract validation.

Single-page writing is an editing capability, not the primary generation path.

## Module boundaries

```text
script-engine/
├─ skills/
│  ├─ understand/
│  ├─ plan/
│  ├─ author/
│  └─ edit-page/
├─ contracts/
│  ├─ foundation.schema.json
│  ├─ deck-plan.schema.json
│  └─ final-script.schema.json
├─ references/
│  ├─ argument-patterns.md
│  ├─ script-quality-rubric.md
│  └─ screen-copy-authoring.md
├─ adapters/
│  └─ cyberppt-stage02/
├─ docs/
├─ tests/
└─ dist/
```

## Two human gates

### Gate A — Deck Plan

Review communication goal, chapters, page sequence, and page-level core messages in one pass.

### Gate B — Final Script

Review the complete rewritten script before visual production.

Detailed single-page review is optional and invoked only when needed.
