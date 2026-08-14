# Source Chapter Placement Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, non-blocking Stage 01 diagnostic that recommends source-unit placement without changing source materials, Source Truth, or Outline.

**Architecture:** A pure function in `semantic_cross_audit.py` joins source-unit heading paths, Source Truth semantic-node bindings, semantic claim roles, and optional Outline chapter topic scopes. `source_truth_audit.py` consumes it as an advisory report field and repair-summary count; blocking issue collection, exit code, and mutation behavior remain unchanged.

**Tech Stack:** Python 3.12, standard-library `unittest`, existing CyberPPT Stage 01 JSON contracts.

## Global Constraints

- Never write to source materials, Source Truth, the semantic model, or Outline.
- Never change Source Truth audit status, retry directive, or exit code because of placement suggestions.
- Do not infer a target chapter without a valid existing Outline chapter scope.
- Use only identifiers and structured fields in diagnostic output; do not copy source prose.
- Do not use headings, text length, keywords, or generic similarity as standalone evidence.

---

### Task 1: Define deterministic placement recommendations

**Files:**
- Modify: `cyberppt/semantic_cross_audit.py:18-378`
- Test: `tests/test_semantic_cross_audit.py`

**Interfaces:**
- Consumes: `source_units: list[dict[str, Any]]`, semantic model, Source Truth, and optional Outline payload.
- Produces: `source_chapter_placement_suggestions(model, source_truth, *, source_units, outline=None) -> list[dict[str, Any]]`.

- [ ] **Step 1: Write failing semantic placement tests**

```python
suggestions = source_chapter_placement_suggestions(
    model, truth, source_units=[{"unit_id": "SU-A", "heading_path": ["实施保障"]}], outline=outline,
)
assert suggestions[0]["outcome"] == "suggest_reporting_rehome"
assert suggestions[0]["suggested_chapter_ids"] == ["mechanism"]
assert "semantic_node_scope_match" in suggestions[0]["reason_codes"]
```

Add tests for cross-chapter reference, heading-only differences, and a missing Outline.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m unittest -v tests.test_semantic_cross_audit`

Expected: import failure for `source_chapter_placement_suggestions`.

- [ ] **Step 3: Implement the pure function**

```python
def source_chapter_placement_suggestions(
    model: dict[str, Any], source_truth: dict[str, Any], *,
    source_units: list[dict[str, Any]], outline: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    # derive source-unit and semantic-node bindings; return sorted,
    # identifier-only recommendations without mutating inputs.
```

Use chapter IDs only from `storyline.chapter_missions` with non-empty `topic_categories`. Emit the specified outcomes and sort by `unit_id` and outcome.

- [ ] **Step 4: Run semantic diagnostic tests**

Run: `PYTHONPATH=. .venv/bin/python -m unittest -v tests.test_semantic_cross_audit`

Expected: all tests pass.

### Task 2: Surface suggestions in the existing Source Truth audit report

**Files:**
- Modify: `cyberppt/commands/source_truth_audit.py:1-162`
- Test: `tests/test_source_truth_audit_command.py`

**Interfaces:**
- Consumes: project source-unit map, semantic model, Source Truth, and canonical `workbench/stages/01-analysis/outline.json` only when present.
- Produces: `report["source_chapter_placement_diagnostics"]` and `repair_summary["chapter_placement_suggestions"]`.

- [ ] **Step 1: Write failing command-level regression test**

```python
code, report = run_source_truth_audit(project, truth_path)
assert code == 0
assert report["status"] == "passed"
assert report["repair_summary"]["chapter_placement_suggestions"] == 1
assert report["source_chapter_placement_diagnostics"][0]["outcome"] == "suggest_reporting_rehome"
```

Assert the Source Truth, model, and Outline bytes remain unchanged.

- [ ] **Step 2: Run the command regression test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m unittest -v tests.test_source_truth_audit_command`

Expected: missing report field assertion.

- [ ] **Step 3: Integrate the advisory payload**

```python
outline_path = project / "workbench/stages/01-analysis/outline.json"
outline = load_outline(outline_path, lightweight=True) if outline_path.is_file() else None
placement = source_chapter_placement_suggestions(
    argument_model, payload, source_units=load_source_units(project), outline=outline,
)
```

Attach `placement` after existing blocking `issues` and `directive` calculations. Count it in `repair_summary`; do not append it to `issues` or `warnings`.

- [ ] **Step 4: Run command and no-mutation tests**

Run: `PYTHONPATH=. .venv/bin/python -m unittest -v tests.test_source_truth_audit_command`

Expected: all tests pass and existing status expectations remain unchanged.

### Task 3: Run focused regressions and inspect the diff

**Files:**
- Modify: `cyberppt/semantic_cross_audit.py`
- Modify: `cyberppt/commands/source_truth_audit.py`
- Modify: `tests/test_semantic_cross_audit.py`
- Modify: `tests/test_source_truth_audit_command.py`

- [ ] **Step 1: Run both focused suites**

Run: `PYTHONPATH=. .venv/bin/python -m unittest -v tests.test_semantic_cross_audit tests.test_source_truth_audit_command`

Expected: all tests pass.

- [ ] **Step 2: Check formatting and scope**

Run: `git diff --check`

Expected: no output; diff contains only implementation files and focused tests.

- [ ] **Step 3: Commit the implementation boundary**

```bash
git add cyberppt/semantic_cross_audit.py cyberppt/commands/source_truth_audit.py tests/test_semantic_cross_audit.py tests/test_source_truth_audit_command.py
git commit -m "feat(stage01): suggest source chapter placement"
```
