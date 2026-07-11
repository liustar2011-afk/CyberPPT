# Task 6 report: golden fixtures, render verification, and documentation

## Changes

- Added `tests/test_ocr_golden_contract.py` with schema, correction-audit, and
  no-credential/no-remote-service checks.
- Added `tests/fixtures/ocr_golden/README.md` and an explicitly `synthetic`
  contract fixture. No approved GPT page image was available in the repository,
  so no production image or fabricated golden OCR data was added.
- Documented legacy/advanced-only OCR use, offline runtime/model provenance,
  mandatory forensic artifacts, recovery behavior, and the verification command
  in `SKILL.md`, `docs/repository-layout.md`, and the high-fidelity design spec.

## Verification

```text
python3 -m pytest tests/test_ocr_golden_contract.py -q
2 passed in 0.01s

python3 -m pytest tests/test_paddleocr_runtime_manifest.py tests/test_paddleocr_local.py tests/test_ocr_text_locator.py tests/test_text_forensics.py tests/test_controlled_correction.py tests/test_ocr_quality_gate.py tests/test_ocr_golden_contract.py -q
31 passed, 14 warnings in 0.14s

python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py -q
27 passed, 1 skipped in 1.17s
```

The legacy integration suite exercises the temporary rebuild path and its
render/QA hooks without network OCR. The synthetic fixture has no page image,
so a production-image visual inspection was not claimed; this remains the
follow-up needed when an approved GPT page image is curated.

## Concerns

- The synthetic record validates only the contract shape, not OCR accuracy.
- Before promoting `paddleocr-local` as a golden-backed default for legacy
  rebuilds, add an approved GPT page image, human line annotations, and a
  recorded render inspection.
