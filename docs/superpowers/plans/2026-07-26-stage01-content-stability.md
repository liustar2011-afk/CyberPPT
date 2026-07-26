# Stage 01 Content Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make strict outlines express each page's unique contribution and prevent script audits from reporting full success before semantic content review is confirmed.

**Architecture:** Extend the existing Outline JSON contract and deterministic audits; do not add a new workflow stage. Store one hash-bound content-review receipt beside existing script audits, then migrate the current project and rerun the existing commands.

**Tech Stack:** Python 3, JSON, pytest, existing CyberPPT CLI.

## Global Constraints

- Do not add a workflow engine, provider integration, multi-agent platform, or database.
- Preserve non-strict Outline compatibility.
- Do not change Source Truth, Stage 02, visual styles, or ImageGen contracts.
- Preserve unrelated dirty-worktree changes.

---

### Task 1: Strict Outline page contribution contract

**Files:**
- Modify: `cyberppt/outline_contract.py`
- Modify: `cyberppt/argument_flow_contract.py`
- Test: `tests/test_outline_contract.py`
- Test: `tests/test_outline_audit_command.py`

**Interfaces:**
- Consumes: existing `cyberppt.outline.v1` page dictionaries.
- Produces: strict validation for `page_job`, `proof_points`, `new_value_vs_previous`, and `reserved_for_later`.

- [x] Add failing tests showing strict content pages reject absent/empty contribution fields while legacy outlines remain valid.
- [x] Add failing tests showing `proof_points` must bind a non-empty claim to valid page `source_refs`.
- [x] Implement minimal field validation inside the existing strict argument audit.
- [x] Add a deterministic overlap check for pages with the same evidence set and highly similar page jobs; report `PAGE_CONTRIBUTION_OVERLAP`.
- [x] Run `PYTHONPATH=. pytest -q tests/test_outline_contract.py tests/test_outline_audit_command.py`.

### Task 2: Hash-bound semantic content review

**Files:**
- Modify: `cyberppt/commands/script_audit.py`
- Modify: `cyberppt/script_quality_contract.py`
- Test: `tests/test_script_audit_command.py`
- Test: `tests/test_script_quality_contract.py`

**Interfaces:**
- Consumes: `workbench/scripts/audits/content-review.json` with `script_sha256`, four boolean review decisions, and optional page notes.
- Produces: `content_review_required` when structural checks pass but the receipt is absent, incomplete, or stale; `passed` only when all decisions are true and the hash matches.

- [x] Add failing tests for missing, incomplete, valid, and stale review receipts.
- [x] Implement a small receipt loader and validator in `script_audit.py`.
- [x] Keep structural errors as `rewrite_required`; attach the existing communication review in all states.
- [x] Update the Markdown audit summary so it distinguishes structural success from pending content review.
- [x] Run `PYTHONPATH=. pytest -q tests/test_script_audit_command.py tests/test_script_quality_contract.py`.

### Task 3: Current-project migration and verification

**Files:**
- Modify: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/01-analysis/outline.json`
- Modify: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/stages/01-analysis/outline-contract.json`
- Modify affected script pages only if migration exposes overlap.
- Create: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/scripts/audits/content-review.json`

**Interfaces:**
- Consumes: approved design and current project artifacts.
- Produces: migrated strict Outline, current script audit, and review receipt bound to the final script hash.

- [x] Add the four fields to all 24 content pages; make P10/P11/P12 overview-only and reserve detailed material for their later pages.
- [x] Run Outline audit and correct only reported page-contribution problems.
- [x] Review the current final script against the four semantic decisions and record page-specific exceptions before marking each decision true.
- [x] Run Script audit and confirm final status is `passed`.
- [x] Run the focused test set plus `git diff --check`.
- [x] Commit only code, tests, and current-project artifacts changed by this implementation.

