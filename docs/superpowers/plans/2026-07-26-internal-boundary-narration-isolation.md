# Internal Boundary and Narration Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep internal boundary controls out of coaching tips and speaker notes unless the page theme is itself a substantive constraint.

**Architecture:** Preserve existing boundary data and receipts, but label them internal-only in authoring inputs. Extend the existing script parser and quality audit with a small theme-aware narration-leak rule.

**Tech Stack:** Python 3, Markdown, regular expressions, pytest.

## Global Constraints

- No new workflow stage, model call, semantic service, or automatic rewriting engine.
- `boundary_refs`, `boundary_constraints`, and `reserved_for_later` remain internal controls.
- Ordinary page narration contains judgment, support, and implication rather than defensive boundary coaching.

---

### Task 1: Correct the authoring contract

**Files:**
- Modify: `references/script-quality.md`
- Modify: `cyberppt/commands/prepare_stage01_input.py`
- Test: `tests/test_prepare_stage01_input.py`

**Interfaces:**
- Consumes: Outline theme fields and boundary controls.
- Produces: page-script authoring input that explicitly prohibits visible consumption of internal controls.

- [x] Add a failing assertion for the internal-only narration rule.
- [x] Run `PYTHONPATH=. pytest -q tests/test_prepare_stage01_input.py`.
- [x] Remove mandatory boundary closure from the writing reference and add the internal-only rule to generated input.
- [x] Re-run the focused test and confirm it passes.

### Task 2: Audit coaching and speaker-note leakage

**Files:**
- Modify: `cyberppt/script_quality_contract.py`
- Test: `tests/test_script_quality_contract.py`

**Interfaces:**
- Consumes: parsed `讲解提示`, speaker notes, and Outline theme fields.
- Produces: `NARRATION_BOUNDARY_COACHING` issues for ordinary pages.

- [x] Add failing parser and audit tests for "反复区分", "避免听众误解", "不要讲成", and "不是承诺".
- [x] Add a passing test for a page whose own theme is scope or decision conditions.
- [x] Parse `讲解提示` into `ScriptPage.coaching_tip`.
- [x] Add a theme-aware leakage audit and retry guidance.
- [x] Run the focused tests.

### Task 3: Regenerate and clean the current project

**Files:**
- Regenerate: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/scripts/page-script-authoring-input.md`
- Update: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/scripts/final/script-final.md`
- Update: current-project script audit receipts.

**Interfaces:**
- Consumes: the corrected global authoring and audit contracts.
- Produces: a canonical script without defensive boundary coaching on ordinary pages.

- [x] Regenerate the page-script input.
- [x] Scan every content page for matching coaching and speaker-note leakage.
- [x] Rewrite all matching ordinary-page narration around business content.
- [x] Run the focused test suite and current-project Source Truth, Outline, and script audits.
- [x] Inspect and commit only the scoped changes.
