# Run Autonomous Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a contract-driven CLI command that fails closed at every existing Stage 01/Stage 02 gate and emits the sole machine-readable completion result.

**Architecture:** A small contract module validates the allowed source boundary and production requirements. A runner composes existing audit and production functions without duplicating their logic; it writes one report that is `completed` only after every required artifact is verified.

**Tech Stack:** Python 3.12+, argparse, existing CyberPPT command modules, unittest.

## Global Constraints

- Preserve existing Stage 01 and Stage 02 gate behavior; the runner only composes them.
- Default to `autonomous_lightweight`; do not create approval, attempt, or ledger controls.
- A missing author-authored semantic model, Outline, Markdown page draft, visual decision package, image, or QA result must stop the run.
- No Stage 02 production call may occur before the current full-script audit passes.

---

### Task 1: Validate a task contract

**Files:**
- Create: `cyberppt/autonomous_contract.py`
- Test: `tests/test_run_autonomous.py`

**Interfaces:**
- Produces: `AutonomousContract`, `load_contract(path)`, and `validate_source_boundary(contract)`.
- Consumes: JSON/YAML-free JSON contract input and concrete absolute source paths.

- [x] **Step 1: Write failing contract tests**
- [x] **Step 2: Implement strict schema, mode, source allowlist, denied-prefix and Stage 02 requirement checks**
- [x] **Step 3: Run `PYTHONPATH=. pytest -q tests/test_run_autonomous.py`**

### Task 2: Compose the fail-closed runner

**Files:**
- Create: `cyberppt/commands/run_autonomous.py`
- Test: `tests/test_run_autonomous.py`

**Interfaces:**
- Produces: `run_autonomous(contract_path, generate_images=True)` returning `(exit_code, report)`.
- Consumes: the validated contract and existing source-map, semantic, Source Truth, Outline, script, handoff, visual, and page-production gates.

- [x] **Step 1: Write failing tests for gate order, short-circuiting, and only-complete-on-image-proof behavior**
- [x] **Step 2: Implement stage checks and atomic report output**
- [x] **Step 3: Run the focused test module**

### Task 3: Expose and document the CLI contract

**Files:**
- Modify: `cyberppt/cli.py`
- Modify: `AGENTS.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `python -m cyberppt run-autonomous CONTRACT.json [--skip-image-generation]`.

- [x] **Step 1: Add a parser/handler test**
- [x] **Step 2: Register the command and render JSON only from the returned report**
- [x] **Step 3: Add the autonomous-lightweight exception to the interaction rule**
- [x] **Step 4: Run focused tests and the repository CLI help check**

### Follow-up hardening: real autonomous Stage 02

**Why:** The initial wrapper proved the CLI shape but incorrectly required a heavyweight JSON page-authoring package, did not execute the visual decision package, and only checked for one sent-prompt file.

- [x] Replace JSON page-authoring-package validation with official lightweight Markdown-draft validation.
- [x] Ignore `source/.gitkeep` consistently with source-map extraction.
- [x] Make visual decision authoring an explicit failed gate; after it exists, compile the visual spec, record execution, and audit the current package without rewriting the handoff.
- [x] Use the explicit autonomous contract—not fabricated per-page approval files—as the narrowly scoped authority for the audited current prompt chain.
- [x] Require every expected content page and every production variant to have a real image, full-image QA, and a hash-bound sent prompt/request record.
