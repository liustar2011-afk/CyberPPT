# Lightweight Page Traceability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce Stage 01 provenance to forward, page-level references while preventing unsupported claims and removing source metadata from Stage 02 visual inputs.

**Architecture:** Source Truth remains the authoritative record registry; atomic records retain source-unit locations. Outline and scripts retain forward `source_refs` and `boundary_refs`, resolved against Source Truth. Stage 02 binds the approved script and outline, then passes only page semantics and locked content to visual design.

**Tech Stack:** Python 3.12, stdlib `unittest`, CyberPPT CLI, JSON artifacts.

## Global Constraints

- Do not modify source registration, `source_unit_refs`, or claim/source validation.
- Do not create a workflow, approval artifact, or parallel project output.
- Preserve compatibility with existing Source Truth payloads containing legacy reverse fields.
- Keep source identifiers out of visual-design input, decisions, and image-generation prompts.
- Preserve unrelated uncommitted files.

---

### Task 1: Make Source Truth forward-only

**Files:**

- Modify: `cyberppt/source_truth_contract.py:427-517`
- Modify: `tests/test_source_truth_contract.py:173-205`

**Interfaces:**

- Consumes: `records[*].id`, `records[*].source_unit_refs`, and `pages[*].source_refs`.
- Produces: `audit_source_truth(payload) -> list[SourceTruthIssue]`, rejecting only missing forward references from pages/conclusions to records.

- [ ] **Step 1: Write failing forward-only tests**

```python
def test_accepts_legacy_reverse_fields_without_requiring_them(self) -> None:
    payload = valid_payload()
    payload["records"][0].pop("page_refs", None)
    payload["records"][0].pop("supports", None)
    self.assertNotIn("SOURCE_TRACEABILITY_BROKEN", {item.code for item in audit_source_truth(payload)})

def test_rejects_unknown_forward_page_source_ref(self) -> None:
    payload = valid_payload()
    payload["pages"][0]["source_refs"] = ["S404"]
    self.assertIn("SOURCE_TRACEABILITY_BROKEN", {item.code for item in audit_source_truth(payload)})
```

- [ ] **Step 2: Run the focused test to verify the first assertion fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_source_truth_contract.py`

Expected: the legacy-reverse-fields test fails because `_traceability_issues` still requires a reverse mapping.

- [ ] **Step 3: Implement forward-reference-only traceability**

Replace `_traceability_issues` with:

```python
def _traceability_issues(records, conclusions, pages):
    record_ids = {str(item.get("id") or "") for item in records}
    broken = {
        str(item.get("id") or "")
        for item in conclusions + pages
        if any(ref not in record_ids for ref in _refs(item, "source_refs"))
    }
    if not broken:
        return []
    return [SourceTruthIssue(
        "SOURCE_TRACEABILITY_BROKEN",
        "Conclusion and page source references must resolve to Source Truth records.",
        tuple(sorted(broken)),
        "traceability_rebuild",
    )]
```

Keep `supports` and `page_refs` tolerated as legacy payload fields; do not read or require them.

- [ ] **Step 4: Run focused tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_source_truth_contract.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add cyberppt/source_truth_contract.py tests/test_source_truth_contract.py
git commit -m "refactor(stage01): use forward source traceability"
```

### Task 2: Remove provenance from visual-production contracts

**Files:**

- Modify: `cyberppt/stage02_handoff.py:265-317`
- Modify: `cyberppt/commands/visual_structure_stage.py:244-312`
- Modify: `tests/test_stage02_handoff.py:11-107`
- Modify: `tests/test_visual_structure_stage.py:25-43`

**Interfaces:**

- Consumes: approved script and outline bindings plus handoff pages.
- Produces: `build_stage02_handoff(...) -> dict[str, Any]` with `source_bindings` for `script` and `outline` only; `_write_visual_design_input(...) -> Path` with no `source_refs` key per visual page.

- [ ] **Step 1: Write failing Stage 02 and visual-input tests**

```python
def test_handoff_binds_script_and_outline_without_source_truth(project: Path) -> None:
    payload = build_stage02_handoff(project, lightweight_stage01_confirmed=True)
    assert set(payload["source_bindings"]) == {"script", "outline"}

def test_visual_design_input_omits_internal_source_references(self) -> None:
    # Use the existing handoff fixture, adding source_refs to its content page.
    page = json.loads(output.read_text(encoding="utf-8"))["pages"][0]
    self.assertNotIn("source_refs", page)
```

- [ ] **Step 2: Run focused Stage 02 tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_stage02_handoff.py tests/test_visual_structure_stage.py`

Expected: the new assertions fail because Stage 02 binds `source_truth` and visual design input copies `source_refs`.

- [ ] **Step 3: Remove internal provenance fields from Stage 02 production input**

```python
bindings = {
    "script": _file_binding(script),
    "outline": _source_binding(project, OUTLINE_PATH),
}
```

Delete this entry from each visual-design page dictionary:

```python
"source_refs": page.get("source_refs") or [],
```

Do not alter `_page_record`'s source refs: the handoff remains a complete internal Stage 01 audit record. Only bindings and the visual interface are narrowed.

- [ ] **Step 4: Run focused Stage 02 tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_stage02_handoff.py tests/test_visual_structure_stage.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add cyberppt/stage02_handoff.py cyberppt/commands/visual_structure_stage.py tests/test_stage02_handoff.py tests/test_visual_structure_stage.py
git commit -m "refactor(stage02): isolate visual inputs from provenance"
```

### Task 3: Make evidence mapping advisory and verify the production chain

**Files:**

- Modify: `cyberppt/script_quality_contract.py:2687-2902,4657-5147`
- Modify: `tests/test_script_quality_contract.py:998-1021,1562-3050`

**Interfaces:**

- Consumes: `ScriptPage.source_refs`, `ScriptPage.boundary_source_refs`, outline page contracts, and Source Truth records.
- Produces: `audit_script_quality(...) -> list[ScriptQualityIssue]` that requires resolvable forward source refs but does not require `evidence_map` or `evidence_map_refs`.

- [ ] **Step 1: Write the failing script-audit regression test**

```python
def test_script_quality_does_not_require_evidence_map_when_forward_refs_resolve(self) -> None:
    page, outline = _consumption_fixture(None)
    page = replace(page, evidence_map="", evidence_map_refs=())
    issues = audit_script_quality(
        ScriptDocument((page,)), outline, source_truth({"id": "S001", "statement": "来源事实"}),
    )
    self.assertNotIn("SOURCE_EVIDENCE_MAP_MISSING", {issue.code for issue in issues})
```

- [ ] **Step 2: Run the focused script-contract tests to verify failure**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_script_quality_contract.py`

Expected: the new test fails if evidence-map completeness remains a blocking issue.

- [ ] **Step 3: Downgrade evidence-map-only validation to advisory behavior**

In `audit_script_quality`, retain checks that resolve `page.source_refs`, `boundary_source_refs`, content-unit refs, and relation refs to the approved outline/Source Truth. Remove only the branch that emits a blocking issue solely because `page.evidence_map_refs` is empty or incomplete. Keep `parse_script_markdown` reading `证据映射` when authors supply it.

- [ ] **Step 4: Run targeted and end-to-end regression tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_source_truth_contract.py tests/test_stage02_handoff.py tests/test_visual_structure_stage.py tests/test_script_quality_contract.py`

Expected: PASS.

Then run: `PYTHONPATH=. .venv/bin/python -m pytest -q`

Expected: all existing tests pass, or any pre-existing failure is reported separately with its exact test name.

- [ ] **Step 5: Rebuild and validate repo context graph**

Run: `npx --no-install graft build && npx --no-install graft check`

Expected: graph rebuild succeeds and `graft check` reports `OK`.

- [ ] **Step 6: Commit Task 3**

```bash
git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py
git commit -m "refactor(stage01): make evidence mapping advisory"
```

## Self-review

- Spec coverage: Task 1 preserves source-to-record location while removing reverse mapping; Task 2 removes provenance from Stage 02 bindings and visual input; Task 3 keeps forward claim checks while making evidence mapping optional.
- Placeholder scan: no deferred requirements or unspecified test expectations remain.
- Interface consistency: all later tasks retain `source_refs` and `boundary_source_refs`; only Stage 02 visual pages lose `source_refs`.
