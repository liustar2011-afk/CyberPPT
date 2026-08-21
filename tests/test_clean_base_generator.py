from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from scripts.image_to_pptx_runtime.clean_base_generator import _post_clean_ocr, prepare_clean_bases


def _policy(*, bbox: list[int]) -> dict[str, object]:
    return {
        "schema": "cyberppt.image_to_pptx.graphic_text_policy.v1",
        "status": "complete",
        "empty_container_check": "passed",
        "items": [{"id": "label-1", "text": "登记编目", "bbox": bbox, "treatment": "native_text"}],
    }


def test_generator_creates_flat_surface_clean_base_and_manifest_contract(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "white")
    ImageDraw.Draw(image).rectangle((80, 60, 179, 99), fill="#0B3B78")
    image.save(full)
    manifest: dict[str, object] = {
        "pairs": [
            {
                "page_number": 1,
                "full": {"path": str(full)},
                "graphic_text_policy": _policy(bbox=[80, 60, 180, 100]),
            }
        ]
    }

    with patch(
        "scripts.image_to_pptx_runtime.clean_base_generator._post_clean_ocr",
        return_value=(True, []),
    ):
        report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")

    assert report["status"] == "complete"
    pair = manifest["pairs"][0]  # type: ignore[index]
    clean = pair["clean_base"]  # type: ignore[index]
    assert clean["status"] == "complete"
    assert Path(clean["path"]).is_file()
    assert clean["cleaned_text_regions"][0]["method"] == "flat-surface-rebuild"


def test_generator_blocks_non_uniform_background_for_review(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(image)
    for x in range(70, 191):
        draw.line((x, 40, x, 120), fill=(x, 100, 180))
    image.save(full)
    manifest: dict[str, object] = {
        "pairs": [
            {
                "page_number": 1,
                "full": {"path": str(full)},
                "graphic_text_policy": _policy(bbox=[80, 60, 180, 100]),
            }
        ]
    }

    report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")

    assert report["status"] == "manual_required"
    assert "clean_base" not in manifest["pairs"][0]  # type: ignore[index]


def test_generator_blocks_when_post_clean_ocr_finds_residual_text(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "white")
    ImageDraw.Draw(image).rectangle((80, 60, 179, 99), fill="#0B3B78")
    image.save(full)
    manifest: dict[str, object] = {
        "pairs": [
            {
                "page_number": 1,
                "full": {"path": str(full)},
                "graphic_text_policy": _policy(bbox=[80, 60, 180, 100]),
            }
        ]
    }

    with patch(
        "scripts.image_to_pptx_runtime.clean_base_generator._post_clean_ocr",
        return_value=(False, [{"policy_id": "label-1", "observed_text": "登记编目"}]),
    ):
        report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")

    assert report["status"] == "manual_required"
    assert report["pages"][0]["post_clean_ocr"][0]["policy_id"] == "label-1"  # type: ignore[index]
    assert "clean_base" not in manifest["pairs"][0]  # type: ignore[index]


def test_post_clean_ocr_checks_a_real_blank_asset(tmp_path: Path) -> None:
    clean = tmp_path / "clean.png"
    Image.new("RGB", (400, 200), "white").save(clean)

    passed, residual = _post_clean_ocr(
        clean,
        [{"policy_id": "label-1", "text": "登记编目", "bbox": (80, 60, 180, 100)}],
    )

    assert passed is True
    assert residual == []
