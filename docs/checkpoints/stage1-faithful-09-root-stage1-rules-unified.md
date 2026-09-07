# Checkpoint — Unified Stage1 root rules

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`

Status: completed.

## Landed

- New Stage1 projects consistently default to the fast, source-faithful `script` profile.
- `strict/legacy` is explicit for contracts, regulations, per-fact verification, full Source Truth, and legacy compatibility.
- Removed root-level faithful assumptions that every page needs a lead conclusion, judgment-first hierarchy, or mandatory speaker notes.
- Root AUTHOR routing is mode-specific:
  - `faithful` -> `faithful-authoring-contract.md`
  - `analytical` -> `authoring-contract.md`
- Faithful `full_copy` follows source-native structure; `onscreen` derives from approved `full_copy`.
- The v2 `page-source` exact-source gate is recorded as evidence preparation, not a new authority or quality gate.
- `.cache/source-index.json` and `.cache/page-source/*.json` are explicitly derived artifacts.

## Authority boundary

Authoritative Stage1 content artifacts remain:

1. `foundation.json`
2. `deck-plan.json`
3. `dist/final-script.md`
