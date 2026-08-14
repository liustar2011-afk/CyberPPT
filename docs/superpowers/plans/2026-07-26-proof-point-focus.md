# Page-Theme Evidence Focus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make page-theme evidence selection a repository-wide Stage 01 contract instead of a one-project manual correction.

**Architecture:** Extend the existing Outline authoring instructions and `argument_flow_contract` audit. Keep evidence separation in the existing page-script input and validate the current project by regenerating through repository commands.

**Tech Stack:** Python 3, JSON, Markdown, `unittest`/pytest.

## Global Constraints

- No semantic model, automatic rewriter, new stage, external dependency, or workflow controller.
- The page theme is `page_job + business_question + main_message`.
- Boundary material remains separate from main proof and authoring evidence.

---

### Task 1: Make focus selection explicit at authoring time

**Files:**
- Modify: `cyberppt/commands/prepare_stage01_input.py`
- Test: `tests/test_prepare_stage01_input.py`

**Interfaces:**
- Consumes: Source Truth records in `prepare_outline_input(project: Path)`.
- Produces: an Outline authoring input containing the mandatory evidence-screening rules.

- [x] Add a failing test asserting that the generated input requires three-field theme screening, boundary separation, and consolidation of records with one implication.
- [x] Run `PYTHONPATH=. pytest -q tests/test_prepare_stage01_input.py` and confirm the new assertion fails.
- [x] Add the concise focus contract to `required_content_page_contract`.
- [x] Run the focused test and confirm it passes.

### Task 2: Add deterministic focus audits

**Files:**
- Modify: `cyberppt/argument_flow_contract.py`
- Test: `tests/test_argument_flow_contract.py`

**Interfaces:**
- Consumes: strict Outline pages and Source Truth records.
- Produces: `ArgumentFlowIssue` entries using retry strategy `refocus_page_evidence`.

- [x] Add failing tests for an off-topic primary proof claim, boundary/unresolved evidence used as primary proof on a non-scope page, excessive independent primary proof points, and a valid consolidated proof point.
- [x] Run `PYTHONPATH=. pytest -q tests/test_argument_flow_contract.py` and confirm the new cases fail.
- [x] Add conservative normalized n-gram focus helpers and the three audit rules inside `audit_argument_flow`.
- [x] Run the focused tests and confirm they pass.

### Task 3: Verify downstream separation and current-project regeneration

**Files:**
- Regenerate: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/01-analysis/outline-authoring-input.md`
- Regenerate: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/scripts/page-script-authoring-input.md`
- Update only if required by audit: current project Outline, Source Truth mappings, and canonical script.

**Interfaces:**
- Consumes: the approved current-project Source Truth and Outline.
- Produces: regenerated authoring inputs and passing Stage 01 receipts.

- [x] Run the focused Stage 01 and script test set.
- [x] Run `prepare-outline-input` and `prepare-page-script-input` for the current project.
- [x] Run Source Truth, Outline, and final-script audits and correct only genuine focus violations in upstream project data.
- [x] Run `git diff --check`, inspect the scoped diff, and commit the implementation and regenerated artifacts.
