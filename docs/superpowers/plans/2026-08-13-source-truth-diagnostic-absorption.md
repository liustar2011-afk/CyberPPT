# Source Truth Non-Blocking Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add actionable Source Truth warnings and a compact repair summary without changing Stage 01 audit status, exit codes, authority, or approvals.

**Architecture:** Keep inference pure in `source_truth_contract.py`, separate from `audit_source_truth()`. `run_source_truth_audit()` exposes warnings and summary only; its existing blocking issues remain the sole status and return-code source.

**Tech Stack:** Python 3.12, stdlib `unittest`, existing CyberPPT Stage 01 JSON contracts.

## Global Constraints

- Do not change `audit_source_truth()` output, `run_source_truth_audit()` status semantics, or command exit codes.
- Consume only Source Truth structural fields and `SU-*` references; no text similarity, keyword thresholds, source-text copying, or control artifacts.
- Diagnostic output contains IDs, codes, counts, and repair strategies only.

---

### Task 1: Add pure structural diagnostic functions

**Files:**

- Modify: `cyberppt/source_truth_contract.py:520-541`
- Test: `tests/test_source_truth_contract.py:276-307`

**Interfaces:**

- Produces: `source_truth_diagnostic_warnings(payload: dict[str, object]) -> list[SourceTruthIssue]`.
- Codes: `SOURCE_RECORD_MULTI_DUTY_WARNING`, `SOURCE_PRIORITY_NARRATIVE_WARNING`.

- [ ] **Step 1: Write failing multi-duty and priority-warning tests**

```python
def test_diagnostics_flag_incompatible_semantic_responsibilities(self) -> None:
    payload = valid_payload()
    record = payload["records"][0]
    record["semantic_units"] = [
        {"claim_role": "fact", "argument_duty": "premise", "source_unit_refs": ["SU-001"]},
        {"claim_role": "recommendation", "argument_duty": "response", "source_unit_refs": ["SU-002"]},
    ]
    warning = next(item for item in source_truth_diagnostic_warnings(payload) if item.code == "SOURCE_RECORD_MULTI_DUTY_WARNING")
    self.assertEqual(warning.source_ids, ("S001",))
    self.assertEqual(warning.retry_strategy, "split_semantic_units")
```

- [ ] **Step 2: Run the focused test**

Run: `PYTHONPATH=. pytest -q tests/test_source_truth_contract.py -k diagnostics`

Expected: FAIL because the function does not exist.

- [ ] **Step 3: Implement the pure function**

```python
def source_truth_diagnostic_warnings(payload: dict[str, object]) -> list[SourceTruthIssue]:
    warnings = source_truth_atomicity_warnings(payload)
    for record in _items(payload, "records"):
        units = [item for item in record.get("semantic_units", []) if isinstance(item, dict)]
        duties = {str(item.get("argument_duty") or "") for item in units}
        roles = {str(item.get("claim_role") or "") for item in units}
        if len(duties) > 1 or len(roles) > 1:
            warnings.append(SourceTruthIssue("SOURCE_RECORD_MULTI_DUTY_WARNING", "One record carries independently repairable semantic responsibilities.", (str(record.get("id") or ""),), "split_semantic_units"))
    return sorted((item for item in warnings if item.source_ids), key=lambda item: (item.code, item.source_ids))
```

Implement priority warnings only for record pairs sharing `semantic_node_ids` or `source_unit_refs`, where a `premise`/`driver`/`consequence`/`gap` record has lower priority than an associated `boundary`/`metadata`/`detail` record. Never compare statements.

- [ ] **Step 4: Run contract regression tests**

Run: `PYTHONPATH=. pytest -q tests/test_source_truth_contract.py tests/test_stage01_compiler.py`

Expected: PASS; `audit_source_truth()` remains unchanged.

- [ ] **Step 5: Commit Task 1**

Run: `git add cyberppt/source_truth_contract.py tests/test_source_truth_contract.py && git commit -m "feat(stage01): add source truth diagnostic warnings"`

### Task 2: Expose report-only diagnostics and repair summary

**Files:**

- Modify: `cyberppt/commands/source_truth_audit.py:20-131`
- Test: `tests/test_source_truth_audit_command.py`

**Interfaces:**

- Produces: report fields `warnings`, `warning_count`, `repair_summary`.
- Preserves: `(0, report)` for warning-only data and `(4, report)` for blocking issues.

- [ ] **Step 1: Write a failing warning-only command test**

```python
def test_warning_only_diagnostics_do_not_change_audit_status(self) -> None:
    project, source_truth = self._project_with_valid_semantic_model()
    payload = self._valid_source_truth()
    payload["records"][0]["semantic_units"] = self._mixed_units()
    source_truth.write_text(json.dumps(payload), encoding="utf-8")
    code, report = run_source_truth_audit(project, source_truth)
    self.assertEqual(code, 0)
    self.assertEqual(report["status"], "passed")
    self.assertGreater(report["warning_count"], 0)
```

- [ ] **Step 2: Run the focused test**

Run: `PYTHONPATH=. pytest -q tests/test_source_truth_audit_command.py -k warning_only`

Expected: FAIL because `warning_count` is absent.

- [ ] **Step 3: Add report fields while preserving status logic**

```python
warnings = source_truth_diagnostic_warnings(payload)
report["warnings"] = [item.to_dict() for item in warnings]
report["warning_count"] = len(warnings)
report["repair_summary"] = {
    "uncovered_source_units": sum(item["code"] == "SEMANTIC_SOURCE_UNIT_UNCOVERED" for item in cross_issues),
    "unresolved_core_claims": sum(item["code"] == "SEMANTIC_CORE_CLAIM_UNRESOLVED" for item in cross_issues),
    "atomic_split_suggestions": sum(item.code.startswith("SOURCE_RECORD_") for item in warnings),
    "priority_review_suggestions": sum(item.code == "SOURCE_PRIORITY_NARRATIVE_WARNING" for item in warnings),
}
```

Keep warnings out of `issues`; therefore the existing status expression remains unchanged.

- [ ] **Step 4: Validate status and privacy**

Run: `PYTHONPATH=. pytest -q tests/test_source_truth_audit_command.py tests/test_semantic_cross_audit.py`

Expected: PASS; warning-only output remains `passed`, blocking fixtures remain `rewrite_required`, and output has no record statements.

- [ ] **Step 5: Commit Task 2**

Run: `git add cyberppt/commands/source_truth_audit.py tests/test_source_truth_audit_command.py && git commit -m "feat(stage01): summarize source truth repair diagnostics"`

### Task 3: Prove non-mutation and document the report contract

**Files:**

- Modify: `tests/test_source_truth_audit_command.py`
- Modify: `docs/superpowers/specs/2026-08-13-source-truth-diagnostic-absorption-design.md`

- [ ] **Step 1: Add an authoritative-input non-mutation test**

```python
def test_warning_diagnostics_do_not_mutate_authoritative_inputs(self) -> None:
    before_truth = source_truth.read_bytes()
    before_model = (project / SEMANTIC_ARGUMENT_MODEL).read_bytes()
    code, report = run_source_truth_audit(project, source_truth)
    self.assertEqual(code, 0)
    self.assertEqual(source_truth.read_bytes(), before_truth)
    self.assertEqual((project / SEMANTIC_ARGUMENT_MODEL).read_bytes(), before_model)
    self.assertIn("repair_summary", report)
```

- [ ] **Step 2: Add the final public report example to the design**

```json
{"warning_count": 2, "warnings": [{"code": "SOURCE_RECORD_MULTI_DUTY_WARNING", "source_ids": ["S001"]}], "repair_summary": {"uncovered_source_units": 0, "unresolved_core_claims": 0, "atomic_split_suggestions": 1, "priority_review_suggestions": 1}}
```

- [ ] **Step 3: Run complete relevant validation and refresh graph**

Run: `PYTHONPATH=. pytest -q tests/test_source_truth_contract.py tests/test_source_truth_audit_command.py tests/test_semantic_cross_audit.py tests/test_stage01_compiler.py`

Expected: PASS.

Run: `git diff --check && npx --no-install graft build && npx --no-install graft check`

Expected: no format errors and graph check passes.

- [ ] **Step 4: Commit Task 3**

Run: `git add tests/test_source_truth_audit_command.py docs/superpowers/specs/2026-08-13-source-truth-diagnostic-absorption-design.md && git commit -m "test(stage01): preserve non-blocking audit diagnostics"`

## Self-Review

- Spec coverage: Task 1 implements two diagnostics; Task 2 exposes summary fields without status changes; Task 3 proves non-mutation and documents the contract.
- Placeholder scan: no prohibited placeholder markers, deferred actions, or undefined interfaces remain.
- Type consistency: all tasks use `SourceTruthIssue`, `source_truth_diagnostic_warnings(payload)`, `warnings`, `warning_count`, and `repair_summary`.
