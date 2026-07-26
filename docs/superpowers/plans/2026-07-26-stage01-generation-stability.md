# Stage 01 Generation Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Add deterministic generation inputs and stronger semantic review to the existing single-machine tool.

**Architecture:** Two read-only preparation commands compile existing project artifacts into Markdown. Existing audits gain evidence-consumption, page-level review, atomicity warnings, and a compact quality table.

**Tech Stack:** Python 3, JSON, Markdown, pytest.

## Global Constraints

- No new workflow stage, database, provider, or agent framework.
- Preserve legacy inputs where practical.
- `script-final.md` is the sole canonical final manuscript.

### Task 1: Preparation commands

- [x] Add reusable input-pack compiler.
- [x] Register `prepare-outline-input` and `prepare-page-script-input`.
- [x] Test all-page and single-page outputs.

### Task 2: Semantic contracts

- [x] Validate evidence consumption roles and single primary ownership.
- [x] Expand overlap review beyond adjacent pages.
- [x] Validate page-level hash-bound content review.
- [x] Warn on compound Source Truth semantic units.

### Task 3: Canonical manuscript and reporting

- [x] Make assembly write the complete manuscript to `script-final.md`.
- [x] Add compact page-quality Markdown table.
- [x] Migrate and verify the current project.
- [x] Run focused and repository tests, then commit the validated scope.
