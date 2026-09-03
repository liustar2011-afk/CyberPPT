from __future__ import annotations

from pathlib import Path
import shutil
from unittest.mock import patch

from PIL import Image, ImageDraw
import pytest

from scripts.image_to_pptx_runtime.clean_base_generator import (
    _post_clean_ocr,
    _reference_edit_clean_base as original_reference_edit_clean_base,
    prepare_clean_bases,
)


def _policy(*, bbox: list[int]) -> dict[str, object]:
    return {
        "schema": "cyberppt.image_to_pptx.graphic_text_policy.v1",
        "status": "complete",
        "empty_container_check": "passed",
        "items": [{"id": "label-1", "text": "登记编目", "bbox": bbox, "treatment": "native_text"}],
    }


def _draw_glyphs(draw: ImageDraw.ImageDraw, *, left: int, top: int, color: str) -> None:
    for offset in (0, 11, 22, 33):
        draw.rectangle((left + offset, top, left + offset + 5, top + 15), fill=color)


def test_generator_creates_flat_surface_clean_base_and_manifest_contract(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "#0B3B78")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((90, 55, 170, 105), radius=8, fill="#FFFFFF")
    _draw_glyphs(draw, left=110, top=72, color="#12355B")
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
    assert clean["cleaned_text_regions"][0]["method"] == "flat-surface-rebuild"
    assert clean["visual_diff_report"]["qa_origin"] == "computed"
    assert clean["visual_diff_report"]["metrics"]["changed_pixels_outside_mask"] == 0
    assert clean["visual_diff_report"]["checks"]["no_abnormal_solid_blocks"] == "passed"


def test_generator_clears_only_multiline_glyphs_in_a_wide_text_container(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (600, 300), "white")
    draw = ImageDraw.Draw(image)
    for row, top in enumerate((82, 132, 182)):
        for column in range(8):
            left = 90 + column * 42
            draw.rectangle((left, top, left + 8, top + 22), fill="#173C63")
            draw.rectangle((left + 12, top + 4, left + 20, top + 18), fill="#173C63")
    image.save(full)
    policy = {
        "status": "complete",
        "empty_container_check": "passed",
        "items": [{
            "id": "multiline-1",
            "text": "第一行文字 第二行文字 第三行文字",
            "bbox": [60, 70, 540, 230],
            "treatment": "native_text",
        }],
    }
    manifest: dict[str, object] = {
        "pairs": [{"page_number": 1, "full": {"path": str(full)}, "graphic_text_policy": policy}]
    }

    with patch(
        "scripts.image_to_pptx_runtime.clean_base_generator._post_clean_ocr",
        return_value=(True, []),
    ):
        report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")

    assert report["status"] == "complete"
    clean = manifest["pairs"][0]["clean_base"]  # type: ignore[index]
    assert clean["status"] == "complete"
    assert clean["cleaned_text_regions"][0]["method"] == "flat-surface-rebuild"
    with Image.open(clean["path"]) as result:
        assert result.getpixel((70, 75)) == (255, 255, 255)
        assert result.getpixel((10, 10)) == (255, 255, 255)


def test_generator_auto_fails_non_uniform_background(tmp_path: Path, monkeypatch) -> None:
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

    def fake_reference(*, output_path, image_paths, **_kwargs):
        shutil.copy2(image_paths[0], output_path)

    monkeypatch.setattr("scripts.image_to_pptx_runtime.clean_base_generator.run_codex_image", fake_reference)
    report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")

    assert report["status"] == "auto_failed"


def test_generator_auto_fails_when_post_clean_ocr_finds_residual_text(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "#0B3B78")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((90, 55, 170, 105), radius=8, fill="#FFFFFF")
    _draw_glyphs(draw, left=110, top=72, color="#12355B")
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
        return_value=(False, [{"policy_id": "label-1", "observed_text": "登记编目"}]),
    ):
        report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")

    assert report["status"] == "auto_failed"
    clean = manifest["pairs"][0]["clean_base"]  # type: ignore[index]
    assert clean["status"] == "failed"
    assert clean["visual_diff_report"]["post_clean_ocr"]["status"] == "residual"


def test_generator_reconstructs_near_white_surface_interrupted_by_divider(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "#F8F8F3")
    draw = ImageDraw.Draw(image)
    draw.rectangle((72, 40, 79, 120), fill="#174D7A")
    _draw_glyphs(draw, left=105, top=72, color="#174D7A")
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
    assert clean["cleaned_text_regions"][0]["method"] == "flat-surface-rebuild"
    with Image.open(clean["path"]) as result:
        assert result.getpixel((75, 80)) == image.getpixel((75, 80))


def test_generator_refuses_a_structural_frame_inside_an_ocr_text_box(tmp_path: Path, monkeypatch) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (400, 200), "#0B3B78")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 60, 179, 99), radius=6, outline="#F4F7FB", width=2)
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

    def fake_reference(*, output_path, image_paths, **_kwargs):
        shutil.copy2(image_paths[0], output_path)

    monkeypatch.setattr("scripts.image_to_pptx_runtime.clean_base_generator.run_codex_image", fake_reference)
    report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")

    assert report["status"] == "auto_failed"


def test_generator_rejects_a_small_bright_patch_on_dark_surface(tmp_path: Path, monkeypatch) -> None:
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

    def fake_reference(*, output_path, image_paths, **_kwargs):
        shutil.copy2(image_paths[0], output_path)

    monkeypatch.setattr("scripts.image_to_pptx_runtime.clean_base_generator.run_codex_image", fake_reference)
    report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")

    assert report["status"] == "auto_failed"


def test_post_clean_ocr_checks_a_real_blank_asset(tmp_path: Path) -> None:
    clean = tmp_path / "clean.png"
    Image.new("RGB", (400, 200), "white").save(clean)

    passed, residual = _post_clean_ocr(
        clean,
        [{"policy_id": "label-1", "text": "登记编目", "bbox": (80, 60, 180, 100)}],
    )

    assert passed is True
    assert residual == []


def test_reference_edit_reconstructs_only_inside_declared_mask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.png"
    destination = tmp_path / "clean.png"
    source_image = Image.new("RGB", (100, 60), "white")
    ImageDraw.Draw(source_image).rectangle((25, 20, 50, 30), fill="black")
    source_image.save(source)

    monkeypatch.setattr(
        "scripts.image_to_pptx_runtime.clean_base_generator._assess_text_clearability",
        lambda *_args, **_kwargs: {"status": "rejected"},
    )
    def fake_reference(*, output_path, image_paths, **_kwargs):
        with Image.open(image_paths[0]) as image:
            edited = image.convert("RGB")
        ImageDraw.Draw(edited).rectangle((20, 15, 60, 40), fill="#00AAFF")
        edited.save(output_path)

    monkeypatch.setattr("scripts.image_to_pptx_runtime.clean_base_generator.run_codex_image", fake_reference)
    original_reference_edit_clean_base(
        source,
        destination,
        [{"policy_id": "text-1", "text": "标题", "bbox": (20, 15, 60, 40)}],
    )
    with Image.open(destination) as result:
        assert result.getpixel((10, 10)) == (255, 255, 255)
        assert result.getpixel((15, 10)) == (255, 255, 255)
        assert result.getpixel((30, 20)) == (0, 170, 255)


def test_generator_handles_dark_sidebar_white_card_and_border_without_rectangular_whiteout(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    image = Image.new("RGB", (512, 256), "#F7F7F3")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 140, 256), fill="#123A63")
    draw.rounded_rectangle((180, 35, 470, 210), radius=8, fill="#FFFFFF", outline="#2B5B84", width=3)
    for offset in (0, 12, 24, 36):
        draw.rectangle((28 + offset, 72, 34 + offset, 90), fill="#FFFFFF")
        draw.rectangle((230 + offset, 92, 236 + offset, 110), fill="#173C63")
    image.save(full)
    policy = {
        "status": "complete",
        "empty_container_check": "passed",
        "items": [
            {"id": "sidebar", "text": "侧栏文字", "bbox": [20, 60, 90, 105], "treatment": "native_text"},
            {"id": "card", "text": "卡片标题", "bbox": [220, 80, 300, 125], "treatment": "native_text"},
        ],
    }
    manifest = {"pairs": [{"page_number": 1, "full": {"path": str(full)}, "graphic_text_policy": policy}]}
    with patch("scripts.image_to_pptx_runtime.clean_base_generator._post_clean_ocr", return_value=(True, [])):
        report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")
    assert report["status"] == "complete"
    clean = manifest["pairs"][0]["clean_base"]  # type: ignore[index]
    assert clean["visual_diff_report"]["metrics"]["changed_pixels_outside_mask"] == 0
    with Image.open(clean["path"]) as result:
        assert result.getpixel((182, 35)) == image.getpixel((182, 35))
        assert result.getpixel((0, 0)) == image.getpixel((0, 0))


def test_generator_rejects_reference_edit_that_creates_a_large_solid_text_container(tmp_path: Path, monkeypatch) -> None:
    full = tmp_path / "full.png"
    Image.new("RGB", (512, 256), "#173C63").save(full)
    policy = _policy(bbox=[40, 40, 470, 210])
    manifest = {"pairs": [{"page_number": 1, "full": {"path": str(full)}, "graphic_text_policy": policy}]}

    def fake_reference(*, output_path, **_kwargs):
        Image.new("RGB", (512, 256), "#FFFFFF").save(output_path)

    monkeypatch.setattr("scripts.image_to_pptx_runtime.clean_base_generator.run_codex_image", fake_reference)
    monkeypatch.setattr(
        "scripts.image_to_pptx_runtime.clean_base_generator._assess_text_clearability",
        lambda *_args, **_kwargs: {"status": "rejected", "reason": "complex"},
    )
    with patch("scripts.image_to_pptx_runtime.clean_base_generator._post_clean_ocr", return_value=(True, [])):
        report = prepare_clean_bases(manifest, output_dir=tmp_path / "authoring" / "assets")
    assert report["status"] == "auto_failed"
    assert manifest["pairs"][0]["clean_base"]["status"] == "failed"  # type: ignore[index]
    assert manifest["pairs"][0]["clean_base"]["visual_diff_report"]["checks"]["no_abnormal_solid_blocks"] == "failed"  # type: ignore[index]
