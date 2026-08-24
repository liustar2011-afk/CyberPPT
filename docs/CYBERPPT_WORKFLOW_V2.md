# CyberPPT Workflow v2 — Script Engine / Stage 02 Loose Coupling

## 1. Architecture

CyberPPT v2 separates content authoring from visual production through one stable file boundary.

```text
┌──────────────────────────┐
│ Script Engine            │
│                          │
│ UNDERSTAND                │
│   ↓                       │
│ PLAN                      │
│   ↓                       │
│ AUTHOR + CRITIC + REWRITE │
└────────────┬─────────────┘
             │
             │ final-script.md
             ▼
┌──────────────────────────┐
│ CyberPPT Stage 02        │
│                          │
│ handoff                   │
│ visual structure          │
│ style                     │
│ ImageGen                  │
│ reconstruction            │
│ PPTX QA                   │
└──────────────────────────┘
```

The two systems share no internal authoring state.

## 2. New default content route

For a new source-to-PPT-script task:

`source -> script-engine UNDERSTAND -> PLAN -> AUTHOR -> final-script.md`

Script Engine owns three authoritative content artifacts:

1. `foundation.json`
2. `deck-plan.json`
3. `final-script.md`

`final-script.json` is an optional machine-readable mirror.

All extraction caches, critique drafts, diagnostics, reports, and compatibility outputs are derived artifacts.

## 3. Script Engine stages

### UNDERSTAND

Purpose: understand the complete source and preserve facts, relationships, responsibilities, boundaries, numbers, terminology, argument chains, and provenance.

Output: `foundation.json`.

No slide planning or PPT copy is written here.

### PLAN

Purpose: define communication goal, audience path, narrative arc, chapters, page sequence, and the proof logic for each page.

Output: `deck-plan.json`.

Each content page is planned through five primary questions:

- What audience question does this page answer?
- What judgment should the audience reach?
- What logic establishes that judgment?
- What source-critical content is required?
- Why does the next page follow?

### AUTHOR

Purpose: write the whole deck as one narrative, then refine sections and pages.

Required authoring order:

1. whole-deck narrative;
2. section-level continuous argument;
3. page writing;
4. whole-deck critic;
5. rewrite;
6. final contract validation.

Output: `final-script.md` and optional `final-script.json`.

### EDIT PAGE

Purpose: targeted revision after whole-deck authoring.

This is an editor, not the default deck-generation path.

## 4. Human gates

The default workflow has two fixed human gates.

### Gate A — Deck Plan

Review:

- communication goal;
- chapter structure;
- page sequence;
- page-level core messages.

### Gate B — Final Script

Review the complete rewritten script before visual production.

Detailed page review is invoked only when useful.

## 5. Stage 01 → Stage 02 contract

The only required content artifact crossing the boundary is:

```text
final-script.md
```

The final script contains renderer-independent information such as:

- page ID and page type;
- title;
- page mission;
- core message;
- full prose;
- onscreen copy;
- semantic visual thesis;
- semantic relationships;
- speaker notes;
- source trace references when available.

It does not contain:

- image-generation prompts;
- visual style presets;
- fonts or colors;
- PPTX coordinates;
- Stage 02 build state;
- Script Engine Foundation or Plan internals.

## 6. Stage 02 entry

The existing Stage 02 implementation accepts a final script from any path:

```bash
python -m cyberppt prepare-stage02-handoff <project> --script <final-script.md>
```

After this command, Stage 02 owns the process.

The subsequent registered Stage 02 routes remain unchanged:

- `stage02.high_fidelity_quick_editable` -> editable PPTX assembly;
- `stage02.picture_ppt` -> image-based PPTX assembly;
- `stage02.dual_delivery` -> both outputs.

Stage 02 must not read `foundation.json`, `deck-plan.json`, authoring critique state, or Script Engine Skill names.

## 7. Legacy Stage 01

The existing Stage 01 route remains available during migration:

`cyberppt-source-foundation -> business-semantic-understanding -> ppt-outline-planning -> cyberppt-handoff -> cyberppt-write-single-page`

Its role is limited to:

- existing projects already bound to legacy artifacts;
- regression comparison;
- diagnostics that explicitly require old Source Truth / Outline contracts.

It is not the default content-authoring route for new projects under Workflow v2.

## 8. Migration principle

Migration should preserve mature source-fidelity and QA capabilities while moving them behind the authoring surface.

The authoring model should primarily reason about:

`source meaning -> communication goal -> narrative -> argument -> presentation copy`

Compatibility projections, caches, receipts, and renderer-specific requirements remain implementation details outside the author's main reasoning path.
