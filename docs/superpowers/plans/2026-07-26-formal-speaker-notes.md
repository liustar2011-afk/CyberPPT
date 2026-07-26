# Formal Speaker Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Replace host-style speaker notes with formal leadership-briefing narration.

**Architecture:** Extend the existing script-quality contract with a small phrase check, update the single writing reference, and regenerate the current project's notes in place.

**Tech Stack:** Python 3, Markdown, pytest.

## Global Constraints

- No new workflow stage or external dependency.
- Keep notes source-faithful and within each page boundary.
- `script-final.md` remains the canonical final manuscript.

### Task 1: Global contract

- [ ] Update the speaker-notes writing reference.
- [ ] Add host-style meta-language audit and tests.

### Task 2: Current project

- [ ] Rewrite all 24 content-page notes.
- [ ] Rebuild `script-final.md` and refresh the review receipt.
- [ ] Run focused tests and project audit.
- [ ] Commit only this task's files.
