# Hybrid OCR Geometry and Text Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic hybrid OCR path that uses macOS Vision geometry and PaddleOCR Chinese text, then validate it on page 004 without regenerating source images.

**Architecture:** A focused hybrid matcher consumes two canonical OCR payloads and emits one canonical payload with provenance and review evidence. The CyberPPT adapter exposes the backend explicitly, preserves Paddle-only behavior, and invokes the existing Vision script only when hybrid mode is selected.

**Tech Stack:** Python 3.14, macOS Vision/Swift, Pillow, pytest, existing three-image vendor pipeline.

## Global Constraints

- Reuse existing FULL, BACKGROUND, and TEXT images; do not regenerate them.
- Do not change canvas sizing or registration behavior.
- Never invent, rewrite, or silently discard OCR text.
- Validate page 004 before changing defaults or running remaining pages.
- Preserve the existing Paddle-only path as a supported fallback.

---

### Task 1: Hybrid observation matcher

**Files:**
- Create: `scripts/dual_image_overlay/rebuild_engine/hybrid_ocr.py`
- Create: `tests/test_hybrid_ocr.py`

**Interfaces:**
- Consumes: canonical Paddle and Vision dictionaries with `canonical.lines[]`.
- Produces: `merge_hybrid_ocr(paddle: dict, vision: dict, image_size: tuple[int, int]) -> dict`.

- [ ] **Step 1: Write failing one-to-one and split tests**

Create fixtures proving a Paddle line receives a Vision bbox and `同比增长 5.0%` becomes two lines only when Vision text supports the exact split. Assert `metadata.backend == "paddle-text+vision-geometry"` and provenance exists on every line.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=. pytest -q tests/test_hybrid_ocr.py`

Expected: collection fails because `hybrid_ocr.py` does not exist.

- [ ] **Step 3: Implement matching primitives**

Implement normalized-text comparison, bbox intersection/center scoring, one-to-one selection, and safe substring splitting. Use deterministic reading-order sorting and keep Paddle text authoritative.

- [ ] **Step 4: Add fallback and validation tests**

Cover unmatched Paddle lines, ambiguous split fallback, invalid Vision boxes, and out-of-bounds clipping. Assert no Paddle source text disappears when output line text is concatenated by source group.

- [ ] **Step 5: Verify GREEN and commit**

Run: `PYTHONPATH=. pytest -q tests/test_hybrid_ocr.py`

Expected: all tests pass.

Commit: `feat: merge Paddle text with Vision OCR geometry`

### Task 2: macOS Vision adapter

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/hybrid_ocr.py`
- Modify: `tests/test_hybrid_ocr.py`

**Interfaces:**
- Produces: `run_vision_ocr(image_path: Path, *, script_path: Path | None = None, timeout: int = 180) -> dict`.

- [ ] **Step 1: Write failing adapter tests**

Assert the adapter executes `swift vendor/three-image-to-ppt/scripts/vision_ocr.swift IMAGE`, parses an object, rejects invalid JSON, and reports nonzero process output.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=. pytest -q tests/test_hybrid_ocr.py -k vision_adapter`

Expected: fail because `run_vision_ocr` is absent.

- [ ] **Step 3: Implement the minimal subprocess adapter**

Resolve the existing Swift script from repository root, use `subprocess.run(..., capture_output=True, text=True, timeout=timeout)`, and validate `canonical.lines` before returning.

- [ ] **Step 4: Verify and commit**

Run: `PYTHONPATH=. pytest -q tests/test_hybrid_ocr.py`

Expected: all tests pass.

Commit: `feat: add macOS Vision geometry adapter`

### Task 3: Selectable CyberPPT OCR backend

**Files:**
- Modify: `cyberppt/commands/editable_text_three_image.py`
- Modify: `cyberppt/commands/produce.py`
- Modify: `cyberppt/cli.py`
- Modify: `tests/test_editable_text_three_image.py`
- Modify: `tests/test_produce.py`

**Interfaces:**
- Add CLI: `--ocr-backend {paddle,hybrid}` with default `paddle`.
- Add generator: `run_hybrid_ocr(image_path: Path, output_path: Path) -> Path`.

- [ ] **Step 1: Run GitNexus impact analysis**

Run upstream impact for every existing function modified in the three files. Stop and warn before editing if any result is HIGH or CRITICAL.

- [ ] **Step 2: Write failing CLI and cache tests**

Assert default Paddle behavior is unchanged, explicit hybrid mode invokes both engines, and the asset manifest records `ocr_backend` so switching backend invalidates only OCR—not FULL/BACKGROUND/TEXT.

- [ ] **Step 3: Verify RED**

Run: `PYTHONPATH=. pytest -q tests/test_editable_text_three_image.py tests/test_produce.py`

Expected: new backend assertions fail.

- [ ] **Step 4: Implement explicit routing**

Thread `ocr_backend` from CLI through `produce editable-text`, select the generator in `_ensure_editable_assets`, and include the backend in cache matching and `asset_manifest.json`.

- [ ] **Step 5: Verify and commit**

Run: `PYTHONPATH=. pytest -q tests/test_editable_text_three_image.py tests/test_produce.py`

Expected: all tests pass.

Commit: `feat: add selectable hybrid OCR backend`

### Task 4: Page 004 A/B reconstruction

**Files:**
- Existing input: `projects/power-supply-demand-forecast-0712/workbench/stages/02-blueprint-dual-image/editable_text/pages_001_019/assets/page_004/`
- Output: `projects/power-supply-demand-forecast-0712/workbench/stages/02-blueprint-dual-image/editable_text/hybrid_page_004/`

**Interfaces:**
- Consumes the existing page 004 FULL/BACKGROUND/TEXT files.
- Produces hybrid OCR JSON, `page.json`, `page.pptx`, `slide-1.png`, `qa.json`, and `text_style_qa.json`.

- [ ] **Step 1: Generate hybrid OCR only**

Run the explicit hybrid backend for page 004. Confirm source image SHA-256 values are unchanged and the OCR metadata records both engines.

- [ ] **Step 2: Check text preservation and split evidence**

Verify all Paddle source text is represented. Confirm separate geometry for `同比增长`/`5.0%` and `约占总装机`/`60%`; uncertain lines must contain review evidence.

- [ ] **Step 3: Rebuild page 004**

Run the existing vendor three-image runner with the hybrid OCR JSON and local presentations runtime environment variables.

- [ ] **Step 4: Compare against the rejected render and reference PPTX**

Render both artifacts and record whether extreme overlap is removed. Do not approve the page solely because the process exits zero.

### Task 5: Regression and handoff

**Files:**
- Modify if required: `vendor/three-image-to-ppt/references/workflow.md`

- [ ] **Step 1: Run focused suites**

Run:

`PYTHONPATH=. pytest -q tests/test_hybrid_ocr.py tests/test_editable_text_three_image.py tests/test_produce.py`

`THREE_IMAGE_TO_PPT_PRESENTATIONS_TOOLS=/Users/liuxing/.codex/plugins/cache/openai-primary-runtime/presentations/26.709.11516/skills/presentations/container_tools THREE_IMAGE_TO_PPT_PRESENTATIONS_PYTHON=/Users/liuxing/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests`

- [ ] **Step 2: Run GitNexus staged change detection**

Run `detect_changes(scope="staged")`, inspect affected flows, and stop before commit on unexpected HIGH/CRITICAL scope.

- [ ] **Step 3: Report page 004 result**

Provide links to the hybrid OCR JSON, rebuilt page 004 PPTX, render, and QA. State explicitly whether the page is visually improved, still review-only, or failed. Do not change the default or run the remaining pages without user approval.
