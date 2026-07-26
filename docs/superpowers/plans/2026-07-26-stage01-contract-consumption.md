# Stage 01 Contract Consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Close the field-level contract from Source Truth through Outline and final content-page scripts.

**Architecture:** Correct the two preparation exports, add one hidden Markdown receipt, and validate it inside the existing script audit.

**Tech Stack:** Python 3, JSON, Markdown, pytest.

## Global Constraints

- No new workflow stage or external dependency.
- HTML receipt comments never enter on-screen text or ImageGen prompts.
- Legacy-mode projects remain compatible.
- Machine-facing fields use canonical `snake_case` names end to end.

### Task 1: Preparation inputs

- [x] Make Outline input independent of `outline.json`.
- [x] Emit hidden page-contract receipt templates from page-script input.
- [x] Update preparation tests.

### Task 2: Script contract audit

- [x] Parse hidden receipts on content pages.
- [x] Validate receipt fields and declared consumption in strict mode.
- [x] Add focused audit tests.

### Task 3: Current project

- [x] Add receipts to all 24 content pages and draft batches.
- [x] Rebuild canonical script and refresh audit receipts.
- [x] Run focused tests and project audits.
- [x] Commit the validated scope.
