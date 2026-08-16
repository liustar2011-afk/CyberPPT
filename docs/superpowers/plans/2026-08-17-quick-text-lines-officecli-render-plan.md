# Quick Text Lines and Office CLI Render Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with reviewable checkpoints.

**Goal:** Preserve source-image visual line breaks as independent editable PPTX text objects and make Office CLI plus `/Applications/obscura` the default visual rendering backend with a bounded LibreOffice fallback.

The production PPTX conversion route is fixed to `stage02-quick-image-to-pptx`.
The former OCR/coordinate reconstruction entry point is retired and fails
closed; it cannot publish a PPTX.

**Architecture:** The Stage 02 Quick adapter will use the existing positional-tspan lowering path in split mode so authored SVG visual rows become independent native text boxes. The presentation QA renderer will use Office CLI to export one-slide HTML, add its headless viewer mode, and use `/Applications/obscura fetch --screenshot` for the browser capture; it retains the existing LibreOffice/Poppler path as an explicit backend and runtime fallback while preserving the current PNG output contract.

**Tech Stack:** Python 3.12, `python-pptx`, Office CLI 1.0.144, SVG-to-DrawingML exporter, unittest.

## Global Constraints

- Do not alter unrelated dirty-worktree files.
- Do not change the global default text wrapping behavior for existing SVG consumers.
- Keep the existing `render_to_png(...) -> list[Path]` contract and `slide-*.jpg`/PNG-compatible downstream behavior.
- Office CLI plus `/Applications/obscura` is the default renderer; LibreOffice remains available through explicit selection and bounded fallback when either tool cannot produce screenshots.
- Verification must inspect actual PPTX text-object count, rendered output, and geometry.

### Task 1: Preserve Quick visual rows as separate native text objects

**Files:**
- Modify: `scripts/image_to_pptx_runtime/stage02_adapter.py:99-101`
- Test: `tests/test_image_to_pptx_runtime.py` or the nearest existing Stage 02 runtime test module

**Interfaces:**
- Consumes: hand-authored SVG files containing positional `tspan` rows.
- Produces: a Stage 02 export whose positional rows are emitted as separate editable PPTX text boxes.

- [x] Pass `text_flow="split"` to `create_pptx_with_native_svg(...)` only in the Quick Stage 02 adapter.
- [x] Add a focused test using two positioned `tspan` rows and assert the exported PPTX contains two native text boxes with the original strings.
- [x] Preserve the current text-content QA and SVG quality gates.

### Task 2: Make Office CLI the default visual renderer

**Files:**
- Modify: `scripts/presentation_qa/render_page.py`
- Modify: `scripts/presentation_qa/office_render.py` only if shared discovery helpers are needed
- Test: `tests/test_presentation_qa.py`

**Interfaces:**
- Consumes: a PPTX path, output directory, DPI, and optional renderer name.
- Produces: the same ordered rendered-page path list consumed by `cyberppt.commands.production_qa.render_and_compare`.

- [x] Add `renderer="officecli"` to `render_to_png(...)` and a CLI `--renderer` choice of `officecli` or `soffice`.
- [x] Use `officecli view <pptx> stats --json` plus one-slide HTML export, then use `/Applications/obscura fetch --screenshot` for each slide.
- [x] Normalize Obscura's fixed viewport capture back to the slide aspect and requested pixel dimensions without changing downstream comparison semantics.
- [x] If Office CLI or Obscura is unavailable, record the failure and fall back to the existing LibreOffice/Poppler renderer; explicit `--renderer soffice` skips both.
- [x] Add tests for default Office CLI selection, explicit SOFFICE selection, Obscura invocation, and fallback after an Office CLI failure.

### Task 3: Run the real page-4 regression and verify

**Files:**
- Create: task-local output under `/private/tmp/cyberppt-fork-quick-page04-20260816/`

- [x] Update the temporary page-4 authored SVG so each body paragraph uses the source image's explicit visual rows.
- [x] Run the Stage 02 adapter and assert SVG quality, text QA, and PPTX export pass.
- [x] Run Office CLI HTML export plus Obscura rendering; verify the fallback remains available.
- [x] Inspect the PPTX XML and rendered page to confirm each visual row remains editable and does not overflow its card.

### Task 4: Final verification

- [x] Run focused unit tests for SVG export and presentation QA.
- [x] Run `officecli validate` and `officecli view <pptx> stats --json` on the regenerated PPTX.
- [x] Report changed files, exact artifacts, test results, renderer used, and any environment limitation.

### Route lock

- [x] Main `final-script-pages --production-build` records and invokes only `stage02-quick-image-to-pptx`.
- [x] The legacy `scripts.image_to_editable_svg` production entry point returns an error and publishes no PPTX.

---
