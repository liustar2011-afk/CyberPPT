# OCR forensic golden fixtures

This directory stores the reviewable contract for the legacy/advanced OCR
forensics path. A fixture may contain an approved GPT-generated page image
reference, expected line geometry/text, and the correction audit records used
by the rebuild and render checks. It must not contain credentials, remote OCR
service configuration, or an unversioned model download.

The repository currently carries a **synthetic** contract fixture only. It is
deliberately marked `fixture_status: "synthetic"` because no page image has
been approved for the golden set yet; it is not evidence that OCR quality has
passed on a production image. When an image is approved, add it under this
directory (or reference an immutable repository path) and change only the
fixture metadata and expected records after human review.

Each JSON record must include:

- `schema_version`, `fixture_id`, and `fixture_status` (`approved` or
  `synthetic`);
- image provenance and dimensions (never a secret or external-service URL);
- expected `lines` with `observed_text`, `final_text`, geometry, and a
  reversible `correction` audit object;
- enough model/config provenance to reproduce the local, offline run.

Verify the contract with:

```bash
python3 -m pytest tests/test_ocr_golden_contract.py -q
```

The fixture contract is not a license to make OCR part of the default
`full_image_ppt` flow. OCR fixtures are consumed only when a user explicitly
chooses legacy/advanced editable rebuild or diagnostic text forensics.
