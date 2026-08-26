# Script quality contract modularization design

## Goal

Split `cyberppt/script_quality_contract.py` by responsibility without changing
its public import path, public symbols, audit output, or CLI behavior.  The
work addresses the current 5,124-line file's mixed parsing, semantic heuristic,
rule-evaluation, and communication-review responsibilities.

## Compatibility contract

`cyberppt.script_quality_contract` remains the supported import module.  It
will become a thin re-exporting facade; every symbol currently imported by
commands, Stage 02 tooling, scripts, and tests remains importable from that
path.  No consumer migration is included in this change.

The facade must also retain test-supported underscore-prefixed helpers.  This
is deliberate: they are presently exercised as compatibility behavior and
must not disappear as a side effect of the physical move.

## Package layout

`cyberppt/script_quality/` will contain:

- `models.py`: data classes, constants, and small pure text utilities shared
  across responsibilities.
- `parser.py`: Markdown section and field parsing, sidecar loading, and
  `parse_script_markdown` / `parse_script_path`.
- `heuristics.py`: lexical, regular-expression, token, polarity, and
  classification helpers.  It contains no audit orchestration.
- `rules.py`: page and document rule functions, final-manuscript checks, retry
  directive construction, and `audit_script_quality` orchestration.
- `review.py`: `build_communication_review` and helpers used only for the
  deterministic editorial review.
- `__init__.py`: the package-level curated public surface used by the facade.

Imports must flow from models outward: parser, heuristics, rules, and review
may import models; rules and review may use parser/heuristics where required;
models may not import the other modules.  Circular imports are resolved by
moving only shared primitives into `models.py`, rather than retaining an
implicit dependency on the facade.

## Migration method

Move functions as unchanged source blocks wherever possible, retaining their
names and signatures.  Extract shared helpers before the consumers that need
them, update internal imports, and leave the facade as explicit re-exports.
Do not alter rule thresholds, regexes, issue codes, issue ordering, report
schema, or parser semantics as part of the refactor.

Existing uncommitted changes to `script_quality_contract.py` are treated as
in-scope source state and preserved in the migrated destination; unrelated
working-tree changes are not staged or modified.

## Verification

1. Import compatibility: existing commands and scripts continue importing from
   `cyberppt.script_quality_contract` without source changes.
2. Behavior compatibility: run `tests/test_script_quality_contract.py` and
   `tests/test_script_audit_command.py`, including the negated-contrast cases.
3. Consumer coverage: run the tests for final-script assembly, final-script
   pages, semantic intent, and visual proof/structure consumers.
4. Run the repository's relevant test suite with `PYTHONPATH=.` and report any
   pre-existing failures separately.
5. Rebuild the Graft graph after the structural change and check it.

## Non-goals

This change does not revise audit policy, add audit rules, change report
content, migrate import sites, or alter Stage 01/Stage 02 workflow behavior.
