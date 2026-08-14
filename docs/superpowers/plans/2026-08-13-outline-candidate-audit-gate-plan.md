# Outline Candidate Audit Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep deterministic Outline candidates out of formal quality auditing until professional authoring is complete.

**Architecture:** Add one early return in the existing outline-audit orchestration path. Keep the generator and all author-edited validations unchanged. The test fixture will exercise a candidate with enough source nodes to reproduce the prior error fan-out.

**Tech Stack:** Python 3.12, pytest, CyberPPT Stage 01 contracts.

## Global Constraints

- Preserve strict auditing for `author_edited` outlines.
- Do not create approval, receipt, manifest, or parallel workflow files.
- Preserve existing user worktree changes outside the two fix-owned files.

---

### Task 1: Gate mechanical candidates before formal checks

**Files:**

- Modify: `cyberppt/outline_contract.py:67-126`
- Test: `tests/test_stage01_compiler.py`

**Interfaces:**

- Consumes: `_author_driven_editorial_issues(outline, pages) -> list[AuditIssue]`
- Produces: `audit_outline(...) -> list[AuditIssue]`

- [ ] **Step 1: Add a failing regression test**

```python
issues = audit_outline(outline, truth, model)
assert {issue.code for issue in issues} == {"OUTLINE_AUTHOR_EDIT_REQUIRED"}
```

Use a generated candidate whose source model contains appendix/detail nodes, so the test proves the orchestration gate prevents unrelated P2 and disposition diagnostics.

- [ ] **Step 2: Run the focused test**

Run: `PYTHONPATH=. pytest -q tests/test_stage01_compiler.py -k candidate_audit_gate`

Expected: FAIL because `audit_outline()` continues into all formal validators.

- [ ] **Step 3: Add the minimal orchestration gate**

```python
author_issues = _author_driven_editorial_issues(outline, pages)
if author_issues:
    return author_issues
issues.extend(author_issues)
```

Place it immediately after deriving `pages`; do not change individual validators.

- [ ] **Step 4: Run focused and neighboring tests**

Run: `PYTHONPATH=. pytest -q tests/test_stage01_compiler.py tests/test_source_argument_model.py`

Expected: PASS. Existing author-edited-outline tests continue to exercise all formal validation.

- [ ] **Step 5: Re-run the supplied project through the candidate audit**

Run: `python3 -m cyberppt outline-audit projects/power-data-infrastructure-cooperation-v16-20260813 --input projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json`

Expected: exactly one `OUTLINE_AUTHOR_EDIT_REQUIRED` issue, with no P2, density, or disposition failures before authoring.
