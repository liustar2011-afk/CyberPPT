# Task 9 report

## Result

Implemented the legacy single-image OCR facade integration.

- `editable_overlay_rebuild.py` routes the local (`paddleocr-local`) legacy
  full-image text extraction through `extract_text_info(image_path, ...)`.
- The helper forwards exactly one image and no page/script/manifest context.
- Page pairing, background OCR/scans, script truth, quality gates, and the
  explicit `ocr_backend="none"` diagnostic return remain in the caller.
- Non-local backends retain their existing layout/forensics route.
- `template_rebuild.py` documents the delegation boundary without changing
  its subprocess contract.

## Impact analysis

GitNexus upstream impact was run before edits:

- `_layout_for_page`: LOW, 0 upstream dependents.
- `rebuild_from_manifest`: LOW, 1 direct caller, 1 affected process.
- `run_vendor_rebuild`: LOW, 2 direct callers, 1 affected process.

Pre-commit `detect_changes(scope="unstaged")` reported HIGH because the
worktree already contains unrelated generated/deleted project artifacts. The
task-specific changed execution flow is `rebuild_from_manifest` in the main
legacy rebuild path; no unrelated files were staged.

## Tests

- `pytest -q tests/test_high_fidelity_text_extractor.py tests/test_high_fidelity_text_extractor_integration.py tests/test_text_forensics.py tests/test_dual_image_overlay_template_rebuild.py`
  - 38 passed, 1 skipped.
- `PYTHONPATH=. pytest -q tests -k 'ocr or overlay or template_rebuild or text_forensics or high_fidelity'`
  - 216 passed, 1 skipped, 346 deselected.

## Follow-up duplicate-OCR fix

The full local image now goes through `_full_layout_for_page`, which calls the
facade once and derives the normalized layout consumed by overlay construction
from the same facade result. Background OCR remains a separate caller-owned
scan; vision-json and none behavior are unchanged. The integration fixture
derives `runtime_dir` from the repository root.

- Focused suite: 39 passed, 1 skipped.
- OCR/overlay suite: 216 passed, 1 skipped, 346 deselected.
- Regression coverage asserts one facade OCR call supplies both layout and
  forensic data.

The follow-up tuple-shape blocker was fixed by routing `full_future` through
`_full_layout_for_page` while leaving the background future on
`_layout_for_page`. Local full-image prefetch is explicitly disabled so the
main facade call remains the only OCR invocation per image.

- Focused suite after blocker fix: 41 passed, 1 skipped.
- OCR/overlay suite after blocker fix: 218 passed, 1 skipped, 346 deselected.

Final-review correction mapping fix: `_layout_from_facade` now applies each
line's accepted `final_text` to deterministic per-item slices while leaving
`observed_text` untouched in the forensic result. Regression covers a
multi-item corrected line; no OCR is re-run by the test.

- Focused suite: 42 passed, 1 skipped.
- OCR/overlay suite: 219 passed, 1 skipped, 346 deselected.
