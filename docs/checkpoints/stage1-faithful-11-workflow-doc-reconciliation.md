# Checkpoint — Master workflow reconciled with faithful Stage1

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`

Status: completed.

## Landed

- `docs/CYBERPPT_WORKFLOW.md` now consistently declares `script` as the default Stage1 profile.
- `strict/legacy` remains an explicit route for contracts, regulations, per-fact verification, full Source Truth, and legacy compatibility.
- AUTHOR contract routing is mode-specific and mutually exclusive:
  - faithful -> `faithful-authoring-contract.md`
  - analytical -> `authoring-contract.md`
- Faithful AUTHOR requires exact page-source resolution when a v2 source index exists.
- Faithful page sequence is source scope -> exact source -> source-native structure -> `full_copy` -> fidelity critic -> `onscreen` -> projection critic -> optional supporting fields.
- `self_read` no longer forces a source-free core judgment on faithful pages.
- PLAN human review includes short source anchors.
- Faithful Final Script relationships must be source-explicit; analytical mode may retain source-supported inferred relationships.
- `.cache/page-source/*.json` is documented as derived runtime context, not a fourth authority.

## Unchanged boundary

Stage2 remains downstream of the locked final script and does not become a Stage1 content authority.
