# Proof Point Focus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Separate main proof from boundary-only material and remove off-topic evidence from P09.

**Architecture:** Extend the existing page contract with `boundary_refs`, split the page authoring input, and validate source partitioning in the existing audits.

**Tech Stack:** Python 3, JSON, Markdown, pytest.

## Global Constraints

- No new workflow stage or external dependency.
- Keep canonical `snake_case` names across machine artifacts.
- Boundary material never defaults into the main prose evidence block.

### Task 1: Contract and preparation

- [ ] Add and validate `boundary_refs`.
- [ ] Split `evidence_text` from `boundary_constraints`.
- [ ] Include `boundary_refs` in hidden receipts.

### Task 2: Current project

- [ ] Remove S059 from P09 Outline, Source Truth mapping, prose, and script evidence.
- [ ] Regenerate inputs and canonical script.
- [ ] Run focused tests and Stage 01 audits.
- [ ] Commit the validated scope.
