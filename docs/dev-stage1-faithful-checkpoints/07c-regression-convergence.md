# Step 7C — Stage1 regression convergence

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`
Draft PR: #28

Status: completed; final differential CI verification pending.

## CI convergence

Using Python 3.12 pytest as the deterministic comparison surface:

- `main` baseline: 63 failing tests
- first refactor run: 98 failing tests -> 35 net-new failures
- compatibility run at commit `67fc068...`: 79 failing tests -> 16 net-new failures
- next run at commit `b13aae2...`: 74 failing tests -> 11 net-new failures

The 11 remaining net-new failures in the `b13aae2...` run were all one cascade: the default structured faithful example had one heading rejected by the semantic predicate detector. CLI lint/render/sync tests all consume that same clean example, so one lint finding produced 11 test failures.

## Root cause and repair

The source-explicit heading:

`可信使用机制控制授权、安全和审计`

was incorrectly treated as a category label because shared `SEMANTIC_PREDICATES` did not contain the normal business predicate `控制`.

Repair:

- added `控制` to `script_engine/semantic_text_primitives.py::SEMANTIC_PREDICATES`;
- did not rewrite the source statement into a different verb merely to satisfy lint;
- kept the example's faithful meaning unchanged.

## Additional repairs included before final differential run

- `examples/final-script.example.json`
  - removed audience-facing page meta such as `本页`;
  - uses source-explicit complete headings;
  - retains only source-backed optional structured fields.
- `tests/script_engine/fixtures/curated/power-industry-data-infrastructure-final-script.json`
  - moved existing onscreen semantic details into `full_copy` so the curated fixture now obeys `full_copy -> onscreen` inheritance rather than weakening the new validator.
- `tests/script_engine/test_natural_language_entry.py`
  - workflow assertions are whitespace-stable and verify faithful `full_copy -> onscreen` routing.
- `script_engine/full_copy_contracts.py`
  - flat multi-step structure regression remains active only for explicit 3+ node argument chains; concise structured pages can still be checked without affecting minimal faithful pages.

## OfficeCLI and packaging comparison

- refactor branch macOS wheel smoke: pass
- refactor branch Windows wheel smoke: pass
- a completed refactor OfficeCLI smoke run: pass
- current `main` comparison run OfficeCLI smoke: fail

Therefore OfficeCLI failure in the first branch run was not evidence of a persistent Stage1 regression; subsequent branch smoke is green.

## Next acceptance check

Inspect the CI run triggered by commit `dfd44e042df3776551a5e9f93aab55e87777e21d` and later head commits. P0 is regression-neutral when no failing test exists on the branch that is absent from the 63-test main baseline.
