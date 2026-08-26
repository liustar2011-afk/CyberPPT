# Boundary Contract: Script Engine → CyberPPT Stage 02

## Required downstream input

Stage 02 receives one canonical final script artifact by path, scoped to its project:

`projects/<slug>/dist/final-script.md`

(or `dist/final-script.md` at the repo root for a legacy pre-project task)

## Stage 02 may depend on

- stable page IDs;
- page type;
- title;
- page mission / core message;
- final onscreen copy;
- speaker notes;
- visual thesis and semantic relationships when provided;
- source trace references when provided.

## Stage 02 must not depend on

- `foundation.json` internal structure;
- `deck-plan.json` internal structure;
- semantic caches;
- audit reports;
- critique drafts;
- authoring iteration state;
- Source Truth projection files;
- Script Engine-specific Skill names.

Machine-readable delivery contract: `cyberppt.final-script@1.0`.
