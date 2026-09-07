# Step 7B — CI baseline comparison and compatibility repair

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`
Draft PR: #28

Status: completed; next CI cycle pending.

## Baseline comparison

Repository CI is not green on `main` before this refactor.

- Current main comparison run: `33980308704`
- Main Python 3.12 pytest result: 63 failures
- First faithful-refactor branch run: `34074847903`
- First branch Python 3.12 pytest result: 98 failures
- Net new failures introduced by the first branch implementation: 35

Scope rule for this refactor:

- repair the 35 branch-introduced regressions;
- do not widen P0 into unrelated repair of the 63 pre-existing main failures;
- consider P0 regression-neutral when the branch failure set is no larger than the main baseline and no new Stage1 failures remain.

Wheel smoke on both macOS and Windows passed in the first branch CI run. OfficeCLI smoke failed; this must be compared with the main baseline before treating it as a refactor regression.

## Compatibility strategy adopted

The first implementation used a minimal faithful example everywhere. That correctly demonstrated the new contract, but many existing tests use `examples/final-script.example.json` as a generic structured fixture and directly access optional fields.

The compatibility repair therefore separates two concepts:

1. **Minimal faithful page** — valid with `full_copy`, `onscreen`, `source_refs` plus common page fields; no `core_message` or `argument` is required.
2. **Structured opt-in page** — when a page voluntarily declares `core_message` or `argument`, the structured bundle is completed and its internal structural-quality checks remain active.

This preserves the new product rule while avoiding unnecessary breakage of existing structured-page consumers.

## Completed repairs

### Final Script schema

`contracts/final-script.schema.json`

- faithful content minimum remains `full_copy + onscreen + source_refs`;
- if `core_message` or `argument` is declared, schema requires the complete structured bundle (`core_message`, `argument`, `full_copy`, `onscreen`, `visual_thesis`, `speaker_notes`);
- this is an opt-in consistency rule, not a global faithful requirement.

### Deterministic author/full-copy/onscreen checks

- `script_engine/author_contracts.py`
  - minimal faithful stays relaxed;
  - structured opt-in faithful pages retain topology/visual consistency checks;
  - duplicate lint-level `source_refs` requirement removed because schema owns that contract.
- `script_engine/full_copy_contracts.py`
  - judgment/sub-conclusion checks run only when the page explicitly opts into a core/argument structure or is analytical;
  - minimal faithful definitions/tasks/taxonomies remain source-native.
- `script_engine/onscreen_contracts.py`
  - faithful semantic parent remains `full_copy` in all cases;
  - optional `core_message` is checked only as an additional consistency constraint when present;
  - structured opt-in pages retain heading/detail quality checks, while minimal faithful pages remain label-friendly.

### Default examples

`examples/foundation.example.json`

- restored compatibility IDs `C1` and `R1`, but both are now source-closed;
- `R1` is `basis: explicit` and supported only by F3;
- A1 is also source-explicit.

`examples/deck-plan.example.json`

- restored legacy page identity (`数据服务形成机制`, page role `mechanism`) for test compatibility;
- kept neutral faithful question/logic and removed transformation/value framing.

`examples/final-script.example.json`

- restored optional structured fields for compatibility;
- every restored field is bound to F1–F4 or the explicit F3 support relation;
- removed all hallucinated catalog/lineage/API/operation/value-loop detail;
- removed delivery navigation language `后续页面`; boundary is now expressed as `具体技术能力清单不在本页展开`.

A separate regression test continues to prove that a minimal faithful page with no `core_message`, `argument`, `visual_thesis`, or `speaker_notes` validates and lints successfully.

### Test contract repairs

- `tests/script_engine/test_natural_language_entry.py`
  - removed the obsolete expectation that the default faithful workflow is conclusion-first;
  - now asserts `full_copy` precedes `onscreen` and analytical conclusion-first methods stay behind explicit analytical mode.
- `tests/test_flow_convergence_contracts.py`
  - added `source_refs` to a Final Script schema fixture rather than weakening the production source-boundary requirement.

## Next

Run/inspect the newest PR CI cycle and calculate the remaining failure delta against the 63-failure main baseline. Repair only branch-introduced failures.
