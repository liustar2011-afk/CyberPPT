# Task 7 report: single-image high-fidelity text extractor

## Result

Added `extract_text_info(image_path, *, backend="paddleocr-local", runtime_dir=None, scale=1.0, correction=True)` in `scripts/dual_image_overlay/rebuild_engine/high_fidelity_text_extractor.py`.

The facade accepts exactly one image and returns only `image`, `lines`, `quality`, `artifacts`, and `provenance`. It composes the local PaddleOCR adapter, line-level OCR evidence/crops, dominant-fill and line-height style evidence, and deterministic protected-term correction. It does not call `full_image_ppt`, background/page logic, scripts, manifests, expected lines, or remote Vision for the local backend.

## Tests

```text
pytest -q tests/test_high_fidelity_text_extractor.py
3 passed, 1 warning
```

Coverage includes one-image input and complete line output, explicit rejection of page-specific arguments, and a patched remote Vision function proving the local facade does not invoke it.

## Impact analysis

GitNexus upstream impact was run before editing. The current index could not resolve `build_line_evidence`, `attach_correction_evidence`, or `text_forensics.py`; each returned `risk: UNKNOWN`, `impactedCount: 0` (index-resolution limitation, not evidence of zero callers).

Pre-commit `detect_changes(scope=all)` reported 8 changed files in the already-dirty worktree, 0 indexed changed symbols, 0 affected processes, and `risk_level: low`. Only the three Task 7 files were staged and committed.

## Commit

`a2fa1b18 feat: add single-image high-fidelity text extractor`
