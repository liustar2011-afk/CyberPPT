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

- [ ] Make Outline input independent of `outline.json`.
- [ ] Emit hidden page-contract receipt templates from page-script input.
- [ ] Update preparation tests.

### Task 2: Script contract audit

- [ ] Parse hidden receipts on content pages.
- [ ] Validate receipt fields and declared consumption in strict mode.
- [ ] Add focused audit tests.

### Task 3: Current project

- [ ] Add receipts to all 24 content pages and draft batches.
- [ ] Rebuild canonical script and refresh audit receipts.
- [ ] Run focused tests and project audits.
- [ ] Commit the validated scope.
