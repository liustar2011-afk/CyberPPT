# Step 7D — Last net-new P0 regression repair

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`
Draft PR: #28

Status: completed; differential CI rerun pending.

## State before this step

Latest analyzed Python 3.12 run after the semantic-predicate repair:

- main baseline: 63 failing tests
- branch: 64 failing tests
- net-new branch failures: 1

The single net-new failure was:

`tests/script_engine/test_cli.py::test_cli_lint_declared_count_mismatch_is_a_warning_not_a_failure`

## Root cause

The test's purpose is to verify that `onscreen_expected_peer_count=5` with four visible modules is a warning rather than a hard failure.

However, the test replaced the entire `onscreen` layer with synthetic filler while leaving `full_copy` unchanged. Under the new faithful authority chain, that payload correctly fails before count comparison because the visible propositions have no semantic parent in `full_copy`.

Weakening the production `full_copy -> onscreen` validator merely to preserve this synthetic fixture would violate the refactor goal.

## Repair

Updated the test fixture instead of production behavior:

- builds the four synthetic modules once;
- assigns those modules to `onscreen`;
- constructs a four-paragraph `full_copy` from the same heading/text/items;
- changes the synthetic `core_message` to use the same ordinal anchors (`第一项` through `第四项`).

The test now isolates exactly the behavior it claims to test: declared peer-count mismatch. Semantic parentage is valid first, so the expected remaining finding is only the count warning.

Commit: `326129b6ecae86a987533bb1ba8ed9fb05450dfc`

## Acceptance target

The next Python 3.12 CI result should contain no branch-only failures relative to the 63-test main baseline. Any remaining failures must be verified as pre-existing on `main` before P0 is marked regression-neutral.
