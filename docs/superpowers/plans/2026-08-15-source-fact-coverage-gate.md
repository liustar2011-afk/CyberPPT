# Source Fact Coverage Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the authoritative PPT outline validator reject silently dropped important normalized facts and make the CyberPPT handoff stop before projection when the current page plan fails that gate.

**Architecture:** Extend the existing layer-three-to-layer-four validator with a deterministic fact-coverage report. It derives direct page consumption from `page-plan.json`, derives source-heading ownership from normalized-fact evidence lines and `outline-workpack.json`, and accepts explicit fact-level dispositions for detail/trace, later-page deferral, intentional omission, and cross-page/shared ownership. The handoff input loader re-runs this validator in memory before requiring `outline-report.json` to be `ok`, so a stale passing report cannot authorize projection.

**Tech Stack:** Python 3, `unittest`/pytest-compatible repository tests, JSON artifacts, repository-local `.agents/skills` packages.

## Global Constraints

- Keep the authoritative Source Material Foundation and page plan unchanged; do not rerun semantic or Source Truth authoring.
- Do not create confirmation files, receipts, hashes, manifests, attempts, or parallel run directories.
- Preserve the existing outline validator API and report shape; add coverage details/errors without weakening existing checks.
- Treat all non-metadata normalized facts as important unless an explicit future fact type marks them as trace/attachment metadata.
- Handoff must validate the current semantic and outline inputs before projection and must not repair or rewrite the page plan.
- Preserve unrelated dirty-worktree changes and do not commit.

---

### Task 1: Add failing coverage-gate tests

**Files:**
- Modify: `tests/test_ppt_outline_planning_defaults.py`
- Modify: `tests/test_source_foundation_integration.py`

**Interfaces:**
- Consume: `ppt_outline_planning.validate.validate_outline_outputs` and `cyberppt_handoff.io.load_inputs`.
- Produce: Regression cases proving missing `nf-005` fails, p05-only `nf-007` needs explicit cross-page ownership, valid deferred/shared dispositions pass, and handoff rejects a stale passing report.

- [ ] **Step 1: Write tests for missing and cross-page fact coverage**

  Extend the outline-planning fixture with a semantic fact whose evidence line maps to a different source heading, then assert:

  ```python
  result = validate_outline_outputs(semantic_dir, outline_dir)
  assert result["status"] == "error"
  assert "uncovered_important_normalized_fact" in {item["code"] for item in result["errors"]}
  ```

  For a fact assigned only to a later page with a different source heading, assert `cross_page_fact_ownership_missing` is reported until a `fact_dispositions` entry declares that page as its owner with a rationale.

- [ ] **Step 2: Write tests for explicit deferred/shared dispositions**

  Add one test where an unassigned fact has:

  ```json
  {"normalized_fact_id":"NF-0003","disposition":"deferred_to","deferred_to":"P05","rationale":"后页承接该能力边界。"}
  ```

  and another where a fact appears on two pages with:

  ```json
  {"normalized_fact_id":"NF-0002","disposition":"shared","page_ids":["P04","P05"],"rationale":"两页分别承担背景与平台回应。"}
  ```

  Both must pass coverage and appear as resolved items in the report.

- [ ] **Step 3: Write a handoff regression test**

  Copy the handoff fixture to a temporary directory, remove one direct fact from the current `page-plan.json` while leaving its old `outline-report.json` as `ok`, call `load_inputs`, and assert it raises before projection with the coverage error code in the message.

- [ ] **Step 4: Run only the new tests and verify they fail for the missing production behavior**

  Run: `PYTHONPATH=. pytest -q tests/test_ppt_outline_planning_defaults.py tests/test_source_foundation_integration.py`

  Expected: FAIL because the validator has no fact coverage report/gate and handoff trusts the stale report.

### Task 2: Implement deterministic source-fact coverage

**Files:**
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py`
- Modify: `.agents/skills/ppt-outline-planning/references/outline-contract.md`

**Interfaces:**
- Consume: layer-three normalized facts, page-level evidence/evidence roles, optional `fact_dispositions`, and `outline-workpack.source_heading_outline`.
- Produce: `coverage` report details, blocking error codes, and preserved existing validator behavior.

- [ ] **Step 1: Add helpers for fact IDs, page roles, and source-heading mapping**

  Use normalized facts as the fact authority. Exclude only metadata/trace/attachment reference types from the important set. Map each fact's evidence line to the latest workpack heading line not after that evidence line, retaining `source_assertion_ids`, block IDs, and source heading IDs in the report.

- [ ] **Step 2: Add fact-disposition parsing and validation**

  Accept a top-level `fact_dispositions` array. Require `normalized_fact_id`, a supported disposition (`page`, `shared`, `detail`, `trace`, `deferred_to`, or `intentional_omission`), and a rationale for deferred/omitted/cross-page declarations. Validate page IDs and later-page ordering for `deferred_to`; validate declared page ownership against direct page references for `page`/`shared`.

- [ ] **Step 3: Build the coverage report and errors**

  For every important fact, emit status, page IDs, roles, source heading IDs, direct evidence state, disposition, target page, and rationale. Block an unassigned fact without an explicit disposition. Block a fact used across pages or outside its source heading page without explicit page/shared ownership. Keep detail/trace as resolved non-onscreen consumption and do not require every fact to become a peer visual module.

- [ ] **Step 4: Attach coverage to the existing result and write it with `outline-report.json`**

  Add `coverage` to the existing report, preserve `errors`, `warnings`, `counts`, and `status`, and ensure `--report` writes the same result. Add the contract documentation for the new fact-level disposition shape.

- [ ] **Step 5: Run the focused validator tests and verify green**

  Run: `PYTHONPATH=. pytest -q tests/test_ppt_outline_planning_defaults.py`

  Expected: PASS, including the new missing/cross-page/deferred/shared cases and existing valid outline fixtures.

### Task 3: Block handoff before projection

**Files:**
- Modify: `.agents/skills/cyberppt-handoff/cyberppt_handoff/io.py`
- Modify: `tests/test_source_foundation_integration.py`

**Interfaces:**
- Consume: current `semantic_dir`, `outline_dir`, and the repository-local planning validator.
- Produce: a pre-projection validation failure when current page-plan coverage is invalid, even if `outline-report.json` is stale and says `ok`.

- [ ] **Step 1: Invoke the planning validator read-only from `load_inputs`**

  Resolve the sibling repository skill package, call `validate_outline_outputs(..., write_report=False)`, and raise a `ValueError` containing the blocking codes before checking the old report or building any projection.

- [ ] **Step 2: Keep the existing report contract check**

  Continue requiring the supplied `outline-report.json` to be an `ok` report after current-input validation; do not rewrite it during handoff and do not mutate page-plan inputs.

- [ ] **Step 3: Run handoff-focused tests**

  Run: `PYTHONPATH=. pytest -q tests/test_source_foundation_integration.py tests/test_source_faithful_artifact_chain.py`

  Expected: PASS, with the new stale-report coverage case proving projection is blocked.

### Task 4: Validate the active project and graph

**Files:**
- Generated only by the existing validator: `projects/power-data-infrastructure-cooperation-v16-20260815/workbench/outline-planning/outline-report.json`

- [ ] **Step 1: Run the planning validator with `--report` for the active project**

  Run the existing validator against the active semantic and outline directories with `--report`; do not edit `page-plan.json`.

- [ ] **Step 2: Run related focused tests and the full relevant outline/handoff checks**

  Run the focused test files, the related outline/handoff test modules, and distinguish any pre-existing unrelated failures.

- [ ] **Step 3: Rebuild Graft and inspect the final diff/status**

  Run `npx --no-install graft build`, then confirm only the intended code/tests/plan/report paths changed and no code is committed.
