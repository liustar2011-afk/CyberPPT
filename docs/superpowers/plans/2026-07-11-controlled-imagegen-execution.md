# Controlled ImageGen Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permit only hash-bound, one-page image generation from the approved page manifest.

**Architecture:** A new executor reads one `pairs[]` entry verbatim, invokes the repository image client, then writes a project-local ledger record. Image approval reads that ledger and the page QA result rather than trusting a file’s presence.

**Tech Stack:** Python 3, JSON, SHA-256, Pillow, `unittest`.

## Global Constraints

- `imagegen-run` accepts project, one page and optional model only.
- It reads the manifest prompt and output path verbatim; no free prompt, prompt-file, output or batch flags exist.
- Each run records manifest hash, prompt hash, model, requested and actual size, output hash, status and timestamps.
- Template-only pages, multi-page requests, stale hashes and non-passed QA are blocking errors.

---

### Task 1: Implement sealed one-page execution

**Files:**

- Create: `cyberppt/commands/imagegen_run.py`
- Modify: `cyberppt/cli.py`
- Test: `tests/test_imagegen_run.py`

- [ ] Write failing tests asserting that page 4 uses `pair["full"]["prompt"]` and `pair["full"]["path"]` exactly; page 1 and range `4-5` raise `ValueError`.
- [ ] Run `python3 -m unittest tests.test_imagegen_run -v` and confirm RED.
- [ ] Add `run_imagegen_page(project, pages_raw, model=None)`. It resolves the current manifest, accepts exactly one content-page pair, hashes the manifest and prompt, calls the existing image client with that exact prompt and output path, validates actual image dimensions, and writes `imagegen_runs/page_<n>.json`.
- [ ] Register `cyberppt imagegen-run <project> --pages <one-page> [--model <model>]`; do not expose prompt or output override arguments.
- [ ] Run `python3 -m unittest tests.test_imagegen_run -v` and confirm GREEN.

### Task 2: Gate approval on run-record freshness and page QA

**Files:**

- Modify: `cyberppt/commands/blueprint_gate.py`
- Modify: `cyberppt/commands/image_text_qa.py`
- Test: `tests/test_imagegen_run.py`
- Test: `tests/test_produce.py`

- [ ] Write failing tests for prompt-hash drift, manifest-hash drift and `review_required` image-text QA rejection.
- [ ] Run `python3 -m unittest tests.test_imagegen_run tests.test_produce -v` and confirm RED.
- [ ] Add `assert_controlled_imagegen_ready(project, manifest_path)`: every pair requires a passed run record whose manifest hash, prompt hash and output hash match current inputs. Set a run to `passed` only after its generated page receives passed image-text QA.
- [ ] Call this assertion from blueprint-image review before it records approval.
- [ ] Run `python3 -m unittest tests.test_imagegen_run tests.test_produce -v` and confirm GREEN.

### Task 3: Protect the public command surface

**Files:**

- Modify: `tests/test_cli.py`
- Test: `tests/test_final_script_pages.py`

- [ ] Add CLI tests rejecting `--prompt`, `--prompt-file`, `--out` and multi-page ranges.
- [ ] Run `python3 -m unittest tests.test_imagegen_run tests.test_cli tests.test_final_script_pages tests.test_produce -v`.
- [ ] Run `python3 -m unittest discover -s tests -p 'test*.py'` before committing only the task files.
