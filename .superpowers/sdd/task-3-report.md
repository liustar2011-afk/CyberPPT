# Task 3 report: line-level OCR forensic evidence

## Status

Implemented and verified. The implementation consumes the normalized `image_size` / `items` OCR contract and adds deterministic line clustering, reading order, bounded glyph crops, dominant-fill sampling, scale metadata, and preserved polygons.

## Commit

`fec99f4a` — `feat: record line-level OCR forensic evidence`.
`c1c8cc6d` — `fix: normalize OCR forensic evidence geometry` (review fixes).

## Files

- `scripts/dual_image_overlay/rebuild_engine/text_forensics.py` — new line clustering and evidence extraction implementation.
- `scripts/dual_image_overlay/rebuild_engine/ocr_text_locator.py` — preserves optional OCR polygons during normalization.
- `tests/test_text_forensics.py` — tests for same-line merging, reading order, crop paths, scale, and polygon evidence.

## Verification

- `python3 -m pytest tests/test_text_forensics.py -q` — **3 passed** (4 Pillow deprecation warnings for `Image.getdata`).
- `python3 -m pytest tests/test_ocr_text_locator.py -q` — **6 passed**.
- `python3 -m pytest tests/test_text_forensics.py tests/test_ocr_text_locator.py -q` — **12 passed**, 14 Pillow deprecation warnings.
- GitNexus `impact(normalize_layout, upstream)` — LOW risk, 5 impacted symbols; existing callers remain covered by the focused OCR tests.
- GitNexus `detect_changes(scope=all)` before commit — medium aggregate worktree risk due to unrelated pre-existing changes; the task diff is limited to the requested files.

## Concerns

Pillow currently emits a deprecation warning for `Image.getdata`; behavior is unchanged and the warning does not fail tests. The evidence schema uses version `1.0`, maps declared OCR geometry into actual image pixels, preserves source geometry separately, and records x/y scale. Clustering is permutation-invariant and dominant-fill sampling excludes the most frequent background color.
