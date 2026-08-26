# Formal Outline Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an official `ppt-outline-planning` generator that produces a source-locked candidate Outline by default and compiles a structured authoring input into a validated authored Outline without relying on project-specific scripts.

**Architecture:** The generator consumes only the validated layer-three semantic directory and its `outline-workpack.json`. It deterministically maps source headings, normalized facts, and source argument nodes into a candidate `deck-brief.json` / `page-plan.json`; an optional authoring spec overlays only explicit editorial decisions. The generator never promotes a candidate to `author_edited` unless an authoring spec is supplied, and the existing validator remains the final contract gate.

**Tech Stack:** Python 3.12, standard library JSON/CLI, existing `ppt_outline_planning.prepare`, `validate`, and `render` modules, pytest.

## Global Constraints

- Use the canonical route `cyberppt-source-foundation → business-semantic-understanding → ppt-outline-planning → cyberppt-handoff → cyberppt-write-single-page`.
- Do not call or depend on `compile-outline-draft`, `cyberppt-author-stage01-outline`, or `scripts/author_v16_outline.py` for the new project.
- Preserve source heading title/order and normalized-fact traceability; do not invent source facts, relations, modalities, or maturity.
- Candidate output must remain `editorial_authoring_status: mechanical_draft`; only explicit authoring input may request `author_edited`.
- Do not create approval, hash, receipt, attempt, ledger, or parallel workflow artifacts.
- Preserve all unrelated dirty-worktree changes.

### Task 1: Define generator behavior with failing tests

**Files:**
- Create: `tests/test_ppt_outline_generator.py`
- Reference: `.agents/skills/ppt-outline-planning/ppt_outline_planning/prepare.py`
- Reference: `.agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py`

**Interfaces:**
- Expected `generate_outline(semantic_dir, outline_dir, authoring_spec=None, force=False)` returns a dict containing `deck`, `plan`, `status`, and `authoring_status`.
- Candidate mode must create source-locked pages and stay `mechanical_draft`.
- Authoring mode must apply page decisions by `source_heading_id`; unknown headings must raise `ValueError`.

- [ ] Write tests for candidate generation, authoring-spec overlay, and unknown-heading rejection.
- [ ] Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /Volumes/DOC/CyberPPT/.venv/bin/pytest -q tests/test_ppt_outline_generator.py` and confirm failure because the generator does not exist.

### Task 2: Implement the official generator

**Files:**
- Create: `.agents/skills/ppt-outline-planning/ppt_outline_planning/generate.py`
- Create: `.agents/skills/ppt-outline-planning/scripts/generate.py`
- Modify: `.agents/skills/ppt-outline-planning/ppt_outline_planning/__init__.py`

**Interfaces:**
- `generate_outline(semantic_dir: Path | str, outline_dir: Path | str, *, authoring_spec: dict[str, Any] | None = None, force: bool = False) -> dict[str, Any]`.
- `build_candidate_outline(...)` maps source heading hierarchy into cover, agenda, section dividers, content pages, and closing template.
- `authoring_spec.pages` is keyed by `source_heading_id`; its values overlay explicit page fields only.

- [ ] Implement source-heading ownership and nearest-fact mapping.
- [ ] Implement source-fact argument-chain fallback using fact statements, never heading-only chains.
- [ ] Implement candidate root metadata and explicit `mechanical_draft` status.
- [ ] Implement authoring-spec validation and overlay without accepting unknown source headings.
- [ ] Write `deck-brief.json` and `page-plan.json` only through the official generator.

### Task 3: Document and verify the workflow

**Files:**
- Modify: `.agents/skills/ppt-outline-planning/SKILL.md`
- Modify: `.agents/skills/ppt-outline-planning/references/outline-contract.md`
- Modify: `tests/test_skill_contract.py`

- [ ] Document candidate and authored invocation commands.
- [ ] State that the generator is the only official Outline generation entry for Foundation projects.
- [ ] Run focused and regression tests.
- [ ] Run the generator against the V16 Foundation project, validate, and render the actual Outline artifacts.

## Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /Volumes/DOC/CyberPPT/.venv/bin/pytest -q tests/test_ppt_outline_generator.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /Volumes/DOC/CyberPPT/.venv/bin/pytest -q tests/test_ppt_outline_generator.py tests/test_ppt_outline_planning_defaults.py tests/test_outline_review.py tests/test_skill_contract.py tests/test_source_foundation_integration.py tests/test_stage01_compiler.py
PYTHONPATH=. /Volumes/DOC/CyberPPT/.venv/bin/python .agents/skills/ppt-outline-planning/scripts/generate.py <semantic-dir> -o <outline-dir> --force
PYTHONPATH=. /Volumes/DOC/CyberPPT/.venv/bin/python .agents/skills/ppt-outline-planning/scripts/validate.py <semantic-dir> <outline-dir> --report
PYTHONPATH=. /Volumes/DOC/CyberPPT/.venv/bin/python .agents/skills/ppt-outline-planning/scripts/render.py <outline-dir> --force
```
