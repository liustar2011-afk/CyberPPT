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

## Review follow-up

The contract test now checks image provenance/dimensions, local model/runtime
provenance, line bbox/polygon geometry, and complete reversible correction
audit fields. Synthetic fixtures additionally require
`fixture_status=synthetic`, `approved_image=false`, `image.path=null`, and
`artifacts.render_check=not_run_synthetic_fixture`.

Synthetic legacy rebuild/render harness (no network, no repository writes):

```text
tmp=$(mktemp -d /tmp/cyberppt-task6-render-XXXX)
python3 -c '... build_line_evidence -> attach_correction_evidence -> evaluate_ocr_quality -> render_overlay_svg ...' "$tmp"
```

Result: `quality: passed`; artifacts were written to
`/tmp/cyberppt-task6-render-7NTX/synthetic_page.png`,
`/tmp/cyberppt-task6-render-7NTX/text_forensics.json`,
`/tmp/cyberppt-task6-render-7NTX/legacy_rebuild.svg`, and
`/tmp/cyberppt-task6-render-7NTX/evidence/line_001.png`. The SVG render was
inspected for canvas, image, and text geometry; `rsvg-convert`/ImageMagick is
not installed, so no raster visual claim is made. This remains synthetic and
does not establish production OCR accuracy.

## Final rework: committed executable harness

Added `tests/run_synthetic_legacy_e2e.py`. It creates the synthetic page,
runs line forensics and the legacy correction/quality path, writes the SVG,
and rasterizes it with the repository-available `cairosvg` runtime. Missing
`cairosvg` is a hard error.

Command and result:

```text
out=$(mktemp -d /tmp/cyberppt-task6-final-XXXX)
python3 tests/run_synthetic_legacy_e2e.py "$out"
quality: passed
```

Artifacts:
`/tmp/cyberppt-task6-final-XiTs/synthetic_page.png`,
`/tmp/cyberppt-task6-final-XiTs/text_forensics.json`,
`/tmp/cyberppt-task6-final-XiTs/legacy_rebuild.svg`,
`/tmp/cyberppt-task6-final-XiTs/legacy_rebuild.png`, and
`/tmp/cyberppt-task6-final-XiTs/evidence/line_001.png`.

The raster output was visually inspected: the 1672x941 canvas contains the
synthetic legacy title and expected `经营管理` text at the recorded line
location. This is a synthetic smoke test only and does not establish
production OCR accuracy.
