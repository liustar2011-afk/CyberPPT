# Checkpoint — Strict projection preserves conclusion basis

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`

Status: completed.

## Root cause fixed

`cyberppt/foundation_projection.py` previously treated the presence of conclusion `source_refs` as proof that the conclusion itself was source-explicit. That conflated evidence support with claim origin and could promote an inferred conclusion to `basis: explicit`.

## Landed

- Added `_conclusion_basis()`.
- Explicit `basis` on the Source Truth conclusion takes precedence.
- Otherwise `claim_origin: source_explicit` maps to `explicit`; all other origins map to `inferred`.
- Source refs/support never determine explicitness.
- Existing valid confidence is preserved; otherwise explicit defaults to high and inferred to medium.

## Regression tests

Added `tests/test_foundation_projection_basis.py` covering:

1. inferred conclusion with source refs remains inferred;
2. source-explicit claim origin becomes explicit;
3. explicit basis is respected even without refs;
4. inferred basis wins even when refs and an explicit-looking claim origin are present.
