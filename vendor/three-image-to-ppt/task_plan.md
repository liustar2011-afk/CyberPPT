# Task Plan

## Goal

Replace CyberPPT's non-editable single-FULL body-image path with a CyberPPT-compatible two-/three-image body enhancement path: BACKGROUND plus OCR JSON becomes native editable text inside the existing `template_image_ppt_export` template assembly.

## Status

- [x] Inspect current CLI and QA flow.
- [x] Implement local input modes and batch manifest runner.
- [x] Trace CyberPPT's existing `page_image_pairs.json` to `template_image_ppt_export` contract and extend that contract in place, preserving its body-region canvas, 2x request, normalization, and drift guards. The adapter writes `cyberppt.editable_text_batch.v1` and the exporter consumes the resulting `cyberppt.editable_text_result.v1` manifest.
- [x] Make CyberPPT template export consume BACKGROUND and editable-text JSON within the body region. The template layer keeps title, page number, logo, footer, and other shared chrome while rendering native text over the BACKGROUND asset.
- [x] Route CyberPPT batch production through the replacement adapter and add contract/regression tests. `produce editable-text`, `produce assemble`, and `produce verify` are mode-aware; vendor pages remain independently isolated in batch mode.

## Verification

- CyberPPT test suite: 264 passed, 16 subtests passed.
- Vendored three-image test suite: 55 passed.
- PptxGenJS renderer: 79 native text boxes, no overflow reported by `slides_test.py`.
