from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PIL import Image

from cyberppt.stage02_production.image_stage import (
    _generate_manifest_images,
    _normalize_user_approved_full_image,
)


def test_passed_page_is_reused_while_failed_page_is_retried(tmp_path: Path) -> None:
    passed = tmp_path / "p01.png"
    failed = tmp_path / "p02.png"
    Image.new("RGB", (2048, 1024), "white").save(passed)
    manifest = {
        "production_mode": "image-to-editable-svg",
        "pairs": [
            {
                "page_number": 1,
                "image_text_truth": {"script_text": "已通过"},
                "full": {
                    "path": str(passed),
                    "prompt": "p1",
                    "canvas": "2048x1024",
                    "prompt_sha256": "new",
                    "generated_prompt_sha256": "old",
                    "text_audit": {"valid": True, "image_size": [2048, 1024]},
                },
            },
            {
                "page_number": 2,
                "full": {
                    "path": str(failed),
                    "prompt": "p2",
                    "canvas": "2048x1024",
                },
            },
        ],
    }
    with (
        patch(
            "cyberppt.stage02_production.image_stage.run_codex_image",
            side_effect=BrokenPipeError(32, "Broken pipe"),
        ) as generate,
        patch("cyberppt.stage02_production.image_stage.ensure_output_size"),
    ):
        result = _generate_manifest_images(
            manifest,
            model="gpt-image-2",
            quality="high",
            timeout=600,
            force=False,
            dry_run=False,
        )
    assert result["skipped"] == [str(passed)]
    assert len(result["failed"]) == 1
    assert result["failed"][0]["page_number"] == 2
    assert generate.call_count == 1
    assert manifest["pairs"][0]["full"]["status"] == "Generated"
    assert manifest["pairs"][1]["full"]["status"] == "Failed"


def test_reusing_normalized_audited_full_image_does_not_rewrite_pixels(tmp_path: Path) -> None:
    passed = tmp_path / "p01.png"
    Image.new("RGB", (2048, 1024), "white").save(passed)
    manifest = {
        "production_mode": "image-to-editable-svg",
        "pairs": [{
            "page_number": 1,
            "image_text_truth": {"script_text": "已通过"},
            "full": {
                "path": str(passed),
                "prompt": "p1",
                "canvas": "2048x1024",
                "prompt_sha256": "prompt",
                "generated_prompt_sha256": "prompt",
                "text_audit": {"valid": True, "image_size": [2048, 1024]},
            },
        }],
    }
    with patch("cyberppt.stage02_production.image_stage.ensure_output_size") as normalize:
        result = _generate_manifest_images(
            manifest,
            model="gpt-image-2",
            quality="high",
            timeout=600,
            force=False,
            dry_run=False,
        )
    assert result["skipped"] == [str(passed)]
    normalize.assert_not_called()


def test_user_approved_image_normalization_does_not_use_enhancement(tmp_path: Path) -> None:
    image = tmp_path / "approved.png"
    Image.new("RGB", (1774, 887), "white").save(image)
    _normalize_user_approved_full_image(image, "2048x1024")
    assert Image.open(image).size == (2048, 1024)
