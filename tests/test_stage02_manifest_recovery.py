from __future__ import annotations

from PIL import Image

from cyberppt.stage02_production.image_stage import _apply_local_edit, _text_audit_error_crops
from cyberppt.stage02_production.manifest_stage import _retain_audited_prior_pairs


def test_partial_recovery_retains_only_audited_prior_pages(tmp_path):
    passed_image = tmp_path / "page-004.png"
    passed_image.write_bytes(b"png")
    prior = {
        "source_script_sha256": "script-hash",
        "production_mode": "image-to-editable-svg",
        "pairs": [
            {
                "page_number": 4,
                "full": {
                    "path": str(passed_image),
                    "text_audit": {"valid": True},
                },
            },
            {
                "page_number": 5,
                "full": {
                    "path": str(tmp_path / "page-005.png"),
                    "text_audit": {"valid": False},
                },
            },
        ],
    }
    recovery = {
        "source_script_sha256": "script-hash",
        "production_mode": "image-to-editable-svg",
        "pairs": [{"page_number": 5, "full": {"path": str(tmp_path / "page-005.png")}}],
    }

    _retain_audited_prior_pairs(manifest=recovery, prior_manifest=prior)

    assert [pair["page_number"] for pair in recovery["pairs"]] == [4, 5]
    assert recovery["content_page_numbers"] == [4, 5]


def test_text_correction_writes_audited_error_region_crops(tmp_path):
    failed_image = tmp_path / "page-005.attempt-01-text-audit-failed.png"
    Image.new("RGB", (200, 100), "white").save(failed_image)

    crops = _text_audit_error_crops(
        failed_image,
        {"image_size": [200, 100], "issues": [{"bbox": [80, 30, 120, 50]}]},
        attempt=1,
    )

    assert len(crops) == 1
    assert crops[0].is_file()
    assert Image.open(crops[0]).size == (104, 82)


def test_local_edit_composite_preserves_pixels_outside_declared_box(tmp_path):
    source, candidate, result = (tmp_path / name for name in ("source.png", "candidate.png", "result.png"))
    Image.new("RGB", (100, 60), "white").save(source)
    Image.new("RGB", (100, 60), "black").save(candidate)
    receipt = _apply_local_edit(source, candidate, result, {"image_size": [100, 60], "issues": [{"bbox": [40, 20, 60, 40]}]})
    assert receipt["outside_changed_pixels"] == 0
    assert Image.open(result).getpixel((0, 0)) == (255, 255, 255)
    assert Image.open(result).getpixel((50, 30)) == (0, 0, 0)
