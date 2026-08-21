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
    image = Image.new("RGB", (400, 200), "#0B3B78")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((90, 55, 170, 105), radius=8, fill="#FFFFFF")
    draw.rectangle((110, 72, 149, 86), fill="#12355B")
    image.save(full)
    manifest: dict[str, object] = {
        "pairs": [
            {
                "page_number": 1,
                "full": {"path": str(full)},
                "graphic_text_policy": _policy(bbox=[100, 65, 160, 95]),
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
    assert clean["cleaned_text_regions"][0]["method"] == "masked-inpainting"
    with Image.open(clean["path"]) as result:
        assert result.getpixel((110, 72)) == (255, 255, 255)
        assert result.getpixel((95, 65)) == (255, 255, 255)
        assert result.getpixel((75, 55)) == (11, 59, 120)


def test_generator_auto_fails_non_uniform_background(tmp_path: Path) -> None:
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

    assert report["status"] == "auto_failed"
    assert "clean_base" not in manifest["pairs"][0]  # type: ignore[index]


def test_generator_reuses_seeded_baseline_after_current_policy_is_located(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    clean = tmp_path / "clean.png"
    Image.new("RGB", (400, 200), "white").save(full)
    Image.new("RGB", (400, 200), "#FEFEFE").save(clean)
    manifest: dict[str, object] = {
        "pairs": [
            {
                "page_number": 1,
                "full": {"path": str(full)},
                "clean_base": {
                    "status": "complete",
                    "path": str(clean),
                    "baseline_seed": True,
                    "baseline_provenance": {"source_schema": "cyberppt.stage02.clean_base.v1"},
                },
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
    clean_contract = manifest["pairs"][0]["clean_base"]  # type: ignore[index]
    assert clean_contract["schema"] == "cyberppt.stage02.clean_base.v2"
    assert clean_contract["cleaned_text_regions"][0]["method"] == "legacy-reviewed-baseline"


def test_generator_auto_fails_when_post_clean_ocr_finds_residual_text(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 60, 179, 99), fill="#0B3B78")
    draw.rectangle((105, 72, 145, 86), fill="#FFFFFF")
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

    assert report["status"] == "auto_failed"
    assert report["pages"][0]["post_clean_ocr"][0]["policy_id"] == "label-1"  # type: ignore[index]
    assert "clean_base" not in manifest["pairs"][0]  # type: ignore[index]


def test_generator_reconstructs_near_white_surface_interrupted_by_divider(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "#F8F8F3")
    draw = ImageDraw.Draw(image)
    draw.rectangle((72, 40, 79, 120), fill="#174D7A")
    draw.rectangle((105, 72, 145, 86), fill="#174D7A")
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
    clean = manifest["pairs"][0]["clean_base"]  # type: ignore[index]
    assert clean["cleaned_text_regions"][0]["method"] == "masked-inpainting"


def test_generator_rejects_a_small_bright_patch_on_dark_surface(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "#164B78")
    ImageDraw.Draw(image).rectangle((72, 56, 187, 57), fill="#F7FAFC")
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

    assert report["status"] == "auto_failed"
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
