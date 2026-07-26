# Argument Flow Semantic Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add repository-wide semantic contracts that reject mixed Source Truth claims, premature page conclusions, invalid argument order, and Source Truth/Outline mapping drift.

**Architecture:** Introduce a focused `argument_flow_contract` module containing role vocabularies, compatibility rules, dependency-graph validation, and cross-stage checks. Keep Source Truth record validation in `source_truth_contract`, invoke the new module from `outline_contract`, and make the outline command load the authoritative Source Truth artifact in strict mode. Preserve legacy behavior through an explicit `argument_contract_mode`.

**Tech Stack:** Python 3.11+, standard library (`dataclasses`, `json`, `re`, `pathlib`), `unittest`, existing CyberPPT CLI and audit-report conventions.

## Global Constraints

- Do not hard-code the power-supply project or reject words such as “首期” by themselves.
- New formal solution projects default to `argument_contract_mode: "strict"`.
- Legacy projects may use `argument_contract_mode: "legacy"` and retain the prior audit behavior.
- Audit failure must return a changed-direction retry strategy and must not abandon the project.
- Preserve source status and boundaries; recommendations, boundaries, and unresolved items cannot become unconditional facts.
- Use TDD: every behavior change begins with a failing test.

---

## File Structure

- Create `cyberppt/argument_flow_contract.py`: shared role vocabulary, compatibility matrix, dependency graph, and cross-stage audit.
- Modify `cyberppt/source_truth_contract.py`: validate semantic units, claim roles, and record dependencies.
- Modify `cyberppt/outline_contract.py`: validate page argument fields and delegate semantic flow checks.
- Modify `cyberppt/commands/outline_audit.py`: resolve/load Source Truth and include semantic audit metadata.
- Modify `cyberppt/cli.py`: expose `--source-truth`.
- Modify `cyberppt/commands/init_project.py`: scaffold strict contract guidance for new projects.
- Modify `tests/test_source_truth_contract.py`: Source Truth semantic regression tests.
- Create `tests/test_argument_flow_contract.py`: page-role, ordering, cycle, and cross-stage tests.
- Modify `tests/test_outline_contract.py`: integration of argument-flow issues into outline audit.
- Modify `tests/test_outline_audit_command.py`: Source Truth resolution, strict/legacy behavior, reports, and retries.
- Modify `tests/test_cli.py`: CLI option coverage.
- Modify current project Stage 01 JSON artifacts only after the general code passes: migrate evidence/page roles and prove the original failure/revised pass.

---

### Task 1: Shared Role Vocabulary and Compatibility Contract

**Files:**
- Create: `cyberppt/argument_flow_contract.py`
- Create: `tests/test_argument_flow_contract.py`

**Interfaces:**
- Produces: `CLAIM_ROLES`, `PAGE_ARGUMENT_ROLES`, `DEFAULT_ALLOWED_CLAIMS`
- Produces: `ArgumentFlowIssue(code, message, pages=(), source_ids=(), failed_edges=(), retry_strategy="rebuild_argument_sequence")`
- Produces: `validate_page_role_fields(outline: dict[str, object]) -> list[ArgumentFlowIssue]`

- [ ] **Step 1: Write failing vocabulary and page-field tests**

```python
from cyberppt.argument_flow_contract import validate_page_role_fields


def test_strict_content_page_requires_argument_role_fields() -> None:
    payload = {
        "argument_contract_mode": "strict",
        "pages": [{"page_id": "p04", "page_type": "content", "argument_role": "foundation"}],
    }
    codes = {issue.code for issue in validate_page_role_fields(payload)}
    assert "ARGUMENT_FIELDS_MISSING" in codes


def test_legacy_outline_does_not_require_argument_fields() -> None:
    payload = {
        "argument_contract_mode": "legacy",
        "pages": [{"page_id": "p04", "page_type": "content"}],
    }
    assert validate_page_role_fields(payload) == []
```

- [ ] **Step 2: Run the tests and verify import failure**

Run:

```powershell
python -m unittest tests.test_argument_flow_contract -v
```

Expected: FAIL because `cyberppt.argument_flow_contract` does not exist.

- [ ] **Step 3: Implement the minimal vocabulary and field validator**

Implement these exact constants:

```python
CLAIM_ROLES = frozenset(
    {"fact", "change", "problem", "judgment", "recommendation", "boundary", "unresolved"}
)
PAGE_ARGUMENT_ROLES = frozenset(
    {
        "foundation", "change", "gap", "necessity", "positioning",
        "solution", "scope", "implementation", "assurance", "decision",
    }
)
DEFAULT_ALLOWED_CLAIMS = {
    "foundation": frozenset({"fact"}),
    "change": frozenset({"fact", "change", "judgment"}),
    "gap": frozenset({"fact", "change", "problem", "judgment"}),
    "necessity": frozenset({"fact", "change", "problem", "judgment", "boundary"}),
    "positioning": frozenset({"fact", "judgment", "recommendation", "boundary"}),
    "solution": frozenset({"fact", "judgment", "recommendation", "boundary"}),
    "scope": frozenset({"fact", "judgment", "recommendation", "boundary", "unresolved"}),
    "implementation": frozenset({"fact", "recommendation", "boundary"}),
    "assurance": frozenset({"fact", "judgment", "recommendation", "boundary"}),
    "decision": frozenset({"fact", "judgment", "boundary", "unresolved"}),
}
```

In strict mode require `argument_role`, `allowed_claim_roles`, `prerequisite_pages`, and `forbidden_claim_roles` on content pages. Reject unknown role values with `ARGUMENT_ROLE_INVALID`.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m unittest tests.test_argument_flow_contract -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Before committing, run `detect_changes({scope: "staged"})`. Expected scope: one new contract module and its tests; no existing execution flow affected yet.

```powershell
git add cyberppt/argument_flow_contract.py tests/test_argument_flow_contract.py
git commit -m "feat: add argument role contract"
```

---

### Task 2: Source Truth Semantic Atomicity

**Files:**
- Modify: `cyberppt/source_truth_contract.py`
- Modify: `tests/test_source_truth_contract.py`

**Interfaces:**
- Consumes: `CLAIM_ROLES`, `PAGE_ARGUMENT_ROLES`
- Produces: existing `audit_source_truth(payload)` with new issue codes
- Produces: updated `source_truth_retry_directive(issues, previous_strategy="")`

- [ ] **Step 1: Run upstream impact analysis**


```text
impact({target: "_record_issues", direction: "upstream"})
impact({target: "audit_source_truth", direction: "upstream"})
impact({target: "source_truth_retry_directive", direction: "upstream"})
```

Record direct callers, affected processes, and risk. Stop if risk is HIGH or CRITICAL.

- [ ] **Step 2: Extend the valid fixture**

Add to the valid `S001` record:

```python
"claim_role": "fact",
"semantic_units": [
    {"text": "已形成月度统计基础。", "claim_role": "fact"}
],
"allowed_page_roles": ["foundation", "necessity"],
"forbidden_page_roles": ["solution"],
"depends_on": [],
```

Add `"argument_contract_mode": "strict"` at the Source Truth root.

- [ ] **Step 3: Write failing semantic tests**

```python
def test_flags_mixed_semantic_claims(self) -> None:
    payload = valid_payload()
    payload["records"][0]["semantic_units"] = [
        {"text": "已经形成统计基础。", "claim_role": "fact"},
        {"text": "首期建议从全国总盘入手。", "claim_role": "recommendation"},
    ]
    codes = {item.code for item in audit_source_truth(payload)}
    self.assertIn("SOURCE_RECORD_MIXED_CLAIMS", codes)


def test_fact_record_cannot_carry_recommendation_unit(self) -> None:
    payload = valid_payload()
    payload["records"][0]["semantic_units"] = [
        {"text": "首期建议从全国总盘入手。", "claim_role": "recommendation"}
    ]
    codes = {item.code for item in audit_source_truth(payload)}
    self.assertIn("SOURCE_FACT_CONTAINS_RECOMMENDATION", codes)


def test_recommendation_requires_resolvable_dependency(self) -> None:
    payload = valid_payload()
    record = payload["records"][0]
    record["type"] = "R"
    record["claim_role"] = "recommendation"
    record["semantic_units"] = [
        {"text": "建议从全国总盘入手。", "claim_role": "recommendation"}
    ]
    record["depends_on"] = ["S404"]
    codes = {item.code for item in audit_source_truth(payload)}
    self.assertIn("SOURCE_DEPENDENCY_MISSING", codes)
```

- [ ] **Step 4: Run tests and verify failures**

Run:

```powershell
python -m unittest tests.test_source_truth_contract -v
```

Expected: the three new assertions FAIL.

- [ ] **Step 5: Implement semantic validation**

Add a focused helper:

```python
def _semantic_record_issues(
    records: list[dict[str, object]],
) -> list[SourceTruthIssue]:
    ...
```

Rules:

- In `legacy` mode return no semantic issues.
- In strict mode require a valid `claim_role` and at least one semantic unit.
- All semantic units in a record must share the record `claim_role`.
- A record with multiple unit roles emits `SOURCE_RECORD_MIXED_CLAIMS`.
- Type `F` with a non-`fact` unit emits `SOURCE_FACT_CONTAINS_RECOMMENDATION`.
- Every `depends_on` value must resolve to another record ID.
- Every `allowed_page_roles` and `forbidden_page_roles` value must be valid and the two sets must not overlap.

Call the helper from `audit_source_truth`.

- [ ] **Step 6: Add changed-direction retry mapping**

Update `source_truth_retry_directive` so:

- mixed claims or fact/recommendation conflict → `split_semantic_units`;
- missing dependency → `rebuild_claim_dependencies`;
- page-role incompatibility → `reassign_claim_page_role`;
- repeated strategy advances to a different strategy.

- [ ] **Step 7: Run tests**

Run:

```powershell
python -m unittest tests.test_source_truth_contract tests.test_source_truth_audit_command -v
```

Expected: PASS.

- [ ] **Step 8: Commit**


```powershell
git add cyberppt/source_truth_contract.py tests/test_source_truth_contract.py
git commit -m "feat: audit source truth semantic claims"
```

---

### Task 3: Argument Dependency Graph and Page-Role Enforcement

**Files:**
- Modify: `cyberppt/argument_flow_contract.py`
- Modify: `tests/test_argument_flow_contract.py`

**Interfaces:**
- Produces: `audit_argument_flow(outline, source_truth) -> list[ArgumentFlowIssue]`
- Produces: `argument_graph_summary(outline, source_truth) -> dict[str, object]`

- [ ] **Step 1: Run upstream impact analysis**


- [ ] **Step 2: Write failing ordering and role tests**

Create helper fixtures containing Source Truth records and content pages. Add tests for:

```python
def test_foundation_page_rejects_recommendation_claim() -> None:
    issues = audit_argument_flow(
        strict_outline(
            content_page(
                "p04", 4, "foundation",
                refs=["S006R"],
                allowed=["fact"],
                forbidden=["recommendation"],
            )
        ),
        strict_truth(record("S006R", "recommendation", pages=["p04"])),
    )
    assert "CLAIM_ROLE_EXCEEDS_PAGE_ROLE" in {issue.code for issue in issues}


def test_prerequisite_must_appear_earlier() -> None:
    issues = audit_argument_flow(
        strict_outline(
            content_page("p04", 4, "necessity", prerequisites=["p06"]),
            content_page("p06", 6, "gap"),
        ),
        strict_truth(),
    )
    assert "PREREQUISITE_PAGE_NOT_EARLIER" in {issue.code for issue in issues}


def test_dependency_cycle_is_rejected() -> None:
    issues = audit_argument_flow(
        strict_outline(
            content_page("p04", 4, "gap", prerequisites=["p05"]),
            content_page("p05", 5, "necessity", prerequisites=["p04"]),
        ),
        strict_truth(),
    )
    assert "ARGUMENT_DEPENDENCY_CYCLE" in {issue.code for issue in issues}


def test_foundation_change_gap_necessity_sequence_passes() -> None:
    issues = audit_argument_flow(valid_four_page_sequence(), valid_sequence_truth())
    assert issues == []


def test_scope_page_may_use_first_phase_recommendation() -> None:
    issues = audit_argument_flow(valid_scope_outline(), valid_scope_truth())
    assert "CLAIM_ROLE_EXCEEDS_PAGE_ROLE" not in {issue.code for issue in issues}
```

- [ ] **Step 3: Verify failures**

Run:

```powershell
python -m unittest tests.test_argument_flow_contract -v
```

Expected: new tests FAIL because graph functions do not exist.

- [ ] **Step 4: Implement graph validation**

Implementation requirements:

- Index pages by `page_id` and numeric `sequence`.
- Build directed edges `prerequisite_page -> current_page`.
- Emit `PREREQUISITE_PAGE_MISSING` for unresolved IDs.
- Emit `PREREQUISITE_PAGE_NOT_EARLIER` when the source sequence is not lower.
- Detect cycles with deterministic depth-first traversal and return the cycle as `failed_edges`.
- Compare each referenced record `claim_role` against the page’s explicit allowed/forbidden sets and repository defaults.
- Emit `PREMATURE_SOLUTION_CLAIM` when a `foundation`, `change`, or `gap` page uses a recommendation as its main supporting claim.
- Do not inspect individual words to decide pass/fail.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m unittest tests.test_argument_flow_contract -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add cyberppt/argument_flow_contract.py tests/test_argument_flow_contract.py
git commit -m "feat: validate argument flow dependencies"
```

Run `detect_changes({scope: "staged"})` first; expected scope remains isolated to the new semantic contract.

---

### Task 4: Cross-Stage Mapping and Status Preservation

**Files:**
- Modify: `cyberppt/argument_flow_contract.py`
- Modify: `tests/test_argument_flow_contract.py`

**Interfaces:**
- Extends: `audit_argument_flow(outline, source_truth)`

- [ ] **Step 1: Impact-check `audit_argument_flow`**


- [ ] **Step 2: Add failing cross-stage tests**

Add exact cases:

- Source Truth `S004` maps to `p04`, but Outline `p04` references `S002` → `PAGE_EVIDENCE_MAPPING_MISMATCH`.
- Outline refers to `S404` → `PAGE_SOURCE_MISSING`.
- A `boundary` or `unresolved` record supports a page whose `main_claim_status` is `confirmed` → `SOURCE_STATUS_UPGRADED`.
- A recommendation depends on evidence not covered by the same page or its transitive prerequisites → `EVIDENCE_PREREQUISITE_UNCOVERED`.

The page fixture must include:

```python
"main_claim_status": "confirmed"
```

and recommendation/boundary pages must use:

```python
"main_claim_status": "proposed"
```

- [ ] **Step 3: Verify failures**

Run focused tests and expect the four new codes to be absent before implementation.

- [ ] **Step 4: Implement bidirectional reconciliation**

Rules:

- Compare `record.page_refs` to actual Outline page references in both directions.
- Report missing record IDs separately from mapping drift.
- Preserve status using a normalized status class, not raw Chinese keyword equality:
  - `confirmed`
  - `proposed`
  - `conditional`
  - `unresolved`
- Require each record dependency to be covered on the current page or a transitively reachable prerequisite page.

- [ ] **Step 5: Run focused tests**

Expected: all cross-stage tests PASS.

- [ ] **Step 6: Commit**

```powershell
git add cyberppt/argument_flow_contract.py tests/test_argument_flow_contract.py
git commit -m "feat: reconcile outline evidence mappings"
```

Run staged detect-changes before commit.

---

### Task 5: Integrate Semantic Flow into Outline Contract

**Files:**
- Modify: `cyberppt/outline_contract.py`
- Modify: `tests/test_outline_contract.py`

**Interfaces:**
- Changes: `audit_outline(outline, source_truth: dict[str, object] | None = None) -> list[AuditIssue]`
- Consumes: `validate_page_role_fields`, `audit_argument_flow`

- [ ] **Step 1: Impact analysis**

Run:

```text
impact({target: "audit_outline", direction: "upstream"})
impact({target: "retry_directive", direction: "upstream"})
```

Report callers and risk before editing.

- [ ] **Step 2: Add failing integration tests**

Extend the `page()` fixture with optional:

```python
argument_role: str = ""
allowed_claim_roles: list[str] | None = None
prerequisite_pages: list[str] | None = None
forbidden_claim_roles: list[str] | None = None
main_claim_status: str = "confirmed"
```

Add tests proving:

- strict outline missing argument fields fails;
- `audit_outline(outline, source_truth)` returns semantic issues;
- legacy mode preserves old tests;
- retry directive maps premature claims to `reassign_claim_to_later_page`;
- repeated semantic retry changes to `rebuild_argument_sequence`.

- [ ] **Step 3: Verify failures**

Run:

```powershell
python -m unittest tests.test_outline_contract -v
```

- [ ] **Step 4: Implement integration**

Convert each `ArgumentFlowIssue` to existing `AuditIssue` without losing page IDs or retry strategy. Keep `audit_outline(payload)` backward compatible for legacy callers. In strict mode, missing Source Truth must emit `SOURCE_TRUTH_REQUIRED`, not silently skip semantic checks.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m unittest tests.test_outline_contract tests.test_argument_flow_contract -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add cyberppt/outline_contract.py tests/test_outline_contract.py
git commit -m "feat: enforce semantic outline audit"
```

Run staged detect-changes first and inspect affected outline-audit flows.

---

### Task 6: Load Source Truth in the Outline Audit Command and CLI

**Files:**
- Modify: `cyberppt/commands/outline_audit.py`
- Modify: `cyberppt/cli.py`
- Modify: `tests/test_outline_audit_command.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Changes: `run_outline_audit(project, input_path, max_attempts=3, source_truth_path: Path | None = None)`
- CLI: `outline-audit ... --source-truth <path>`

- [ ] **Step 1: Impact analysis**

Run upstream impact for `run_outline_audit`, `_outline_audit_command`, and `build_parser`. Warn before HIGH/CRITICAL edits.

- [ ] **Step 2: Add failing command tests**

Add tests for:

- explicit `source_truth_path`;
- default resolution at `workbench/stages/01-analysis/source-truth.json`;
- strict mode without a Source Truth file returns an audit failure;
- legacy mode without Source Truth preserves prior behavior;
- report contains `argument_contract_mode`, `checked_source_truth`, `argument_graph`, `failed_edges`, and `retry_scope`;
- CLI help contains `--source-truth`.

- [ ] **Step 3: Verify failures**

Run:

```powershell
python -m unittest tests.test_outline_audit_command tests.test_cli -v
```

- [ ] **Step 4: Implement source resolution and report metadata**

Resolution order:

1. explicit `source_truth_path`;
2. project standard path;
3. no artifact.

Load with existing `load_source_truth`. Pass the payload to `audit_outline`. Store a project-relative path in `checked_source_truth` where possible. Add semantic report fields even on failure so retry tooling has structured evidence.

- [ ] **Step 5: Implement CLI option**

Add:

```python
outline_audit.add_argument(
    "--source-truth",
    help="Optional Source Truth JSON; defaults to the project Stage 01 artifact.",
)
```

and pass `Path(args.source_truth) if args.source_truth else None`.

- [ ] **Step 6: Run focused tests**

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add cyberppt/commands/outline_audit.py cyberppt/cli.py tests/test_outline_audit_command.py tests/test_cli.py
git commit -m "feat: cross-audit outline source truth"
```

Run staged detect-changes first; review CLI and audit execution flows.

---

### Task 7: Scaffold Strict Contracts for New Projects

**Files:**
- Modify: `cyberppt/commands/init_project.py`
- Modify: `tests/test_init_project.py`
- Modify: `tests/test_outline_audit_command.py`

**Interfaces:**
- Existing: `init_project(project, force=False)`

- [ ] **Step 1: Impact-check `init_project`**


- [ ] **Step 2: Add failing scaffold tests**

Assert newly generated instructions contain:

```text
argument_contract_mode: strict
foundation → change → gap → necessity
outline-audit ... --source-truth
```

Also assert the text says the sequence is an example dependency chain, not a mandatory chapter template.

- [ ] **Step 3: Verify failures**

Run init-project tests and expect the new assertions to fail.

- [ ] **Step 4: Update scaffold guidance**

Add the strict-mode contract and cross-stage audit command to generated README/config guidance. Do not create a second authoritative role matrix outside Python; link to the generated schema/example instead.

- [ ] **Step 5: Run tests**

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add cyberppt/commands/init_project.py tests/test_init_project.py tests/test_outline_audit_command.py
git commit -m "feat: scaffold strict argument contracts"
```

Run staged detect-changes and review affected initialization flows.

---

### Task 8: Migrate the Current Project and Add End-to-End Regression

**Files:**
- Modify: `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/source-truth.json`
- Modify: `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/outline.json`
- Regenerate: `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/00-source-analysis.md`
- Regenerate: `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/source-truth-audit.json`
- Regenerate: `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/outline-contract.json`
- Regenerate: `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/outline-audit.json`
- Modify: `projects/power-supply-demand-forecast-early-warning/workbench/artifact-ledger.json`
- Create: `tests/fixtures/argument_flow/power_p04_original.json`
- Create: `tests/fixtures/argument_flow/power_c1_revised.json`
- Modify: `tests/test_argument_flow_contract.py`

**Interfaces:**
- Consumes all completed audit interfaces.

- [ ] **Step 1: Create the failing original fixture**

Fixture must preserve the original defect:

- one fact record combines organizational foundation and a first-phase recommendation;
- `p04` has role `foundation`;
- `p04` uses the recommendation as its main claim.

Add a test asserting the fixture returns:

```text
SOURCE_RECORD_MIXED_CLAIMS
```

or, after split but before page repair:

```text
CLAIM_ROLE_EXCEEDS_PAGE_ROLE
```

- [ ] **Step 2: Create the passing revised fixture**

Represent:

```text
p04 foundation → p05 change → p06 gap → p07 necessity
```

Keep the first-phase recommendation as a separate recommendation record mapped to the later scope page. Assert no semantic issues.

- [ ] **Step 3: Run fixture tests**

Expected: original FAILS the semantic gate; revised fixture PASSES.

- [ ] **Step 4: Migrate Source Truth**

For every record:

- add `claim_role`, `semantic_units`, page-role permissions, and dependencies;
- split mixed records while preserving exact quote and locator;
- update all `supports`, `source_refs`, `page_refs`, fingerprints, and coverage references;
- retain proposal, boundary, and unresolved statuses.

Do not mechanically relabel all records from their existing `type`; review each record’s semantics.

- [ ] **Step 5: Migrate Outline**

Add strict argument fields to every content page. For chapter one enforce:

- `p04`: `foundation`, facts only;
- `p05`: `change`, depends on `p04` only if its conclusion uses the established baseline;
- `p06`: `gap`, depends on `p04` and `p05`;
- `p07`: `necessity`, depends on `p06`.

Move first-phase scope conclusions to the existing scope chapter/page rather than deleting them.

- [ ] **Step 6: Run both audits**

```powershell
python -m cyberppt source-truth-audit projects/power-supply-demand-forecast-early-warning --input projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/source-truth.json
python -m cyberppt outline-audit projects/power-supply-demand-forecast-early-warning --input projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/outline.json --source-truth projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/source-truth.json
```

Expected: both exit `0`, report `passed`, and contain no failed edges.

- [ ] **Step 7: Regenerate readable artifacts and ledger hashes**

Use the audit commands as the only writer for rendered audit artifacts. Recalculate SHA-256 for all changed project artifacts and update only matching ledger entries.

- [ ] **Step 8: Run focused and full tests**

```powershell
python -m unittest tests.test_source_truth_contract tests.test_argument_flow_contract tests.test_outline_contract tests.test_source_truth_audit_command tests.test_outline_audit_command tests.test_cli tests.test_init_project -v
python -m unittest discover -s tests -v
```

Expected:

- focused suite: all PASS;
- full suite: no new failures relative to the recorded baseline; pre-existing unrelated failures remain separately identified.

- [ ] **Step 9: Final impact and commit**

Run:

```text
detect_changes({scope: "compare", base_ref: "main"})
```

Confirm only Source Truth, outline-audit, CLI, project scaffold, tests, and the selected project’s Stage 01 flows are affected.

```powershell
git add cyberppt tests projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis projects/power-supply-demand-forecast-early-warning/workbench/artifact-ledger.json
git commit -m "feat: enforce semantic argument flow audits"
```

---

## Final Verification Checklist

- [ ] Original `S006 + p04` defect is deterministically rejected.
- [ ] Revised chapter-one chain passes.
- [ ] A legitimate first-phase recommendation on a `scope` page passes.
- [ ] Source Truth and Outline mapping drift fails.
- [ ] Status upgrades fail.
- [ ] Dependency cycles fail with explicit edges.
- [ ] Audit reports contain actionable retry scope and changed-direction strategy.
- [ ] New projects default to strict mode.
- [ ] Legacy mode preserves historical behavior.
- [ ] No unrelated working-tree files are staged or committed.
