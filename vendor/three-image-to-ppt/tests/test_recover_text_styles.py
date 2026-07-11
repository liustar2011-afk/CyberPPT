from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont
import pytest


def _font(size: int = 34):
    return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)


def _make_color_fixture(background_color: str, text_color: str):
    from scripts.models import BBox

    size = (320, 100)
    bbox = BBox(20, 15, 280, 70)
    background = Image.new("RGB", size, background_color)
    full = background.copy()
    text = Image.new("RGB", size, "#FFFFFF")
    ImageDraw.Draw(full).text((42, 29), "103682 MW", font=_font(), fill=text_color)
    ImageDraw.Draw(text).text((42, 29), "103682 MW", font=_font(), fill="#101010")
    return full, background, text, bbox


@pytest.mark.parametrize(
    ("background_color", "text_color"),
    [
        ("#12355B", "#FFFFFF"),
        ("#FFFFFF", "#12355B"),
        ("#FFFFFF", "#2A7F2E"),
    ],
)
def test_color_recovery_uses_full_background_delta(background_color, text_color):
    from scripts.recover_text_styles import recover_line_color

    full, background, text, bbox = _make_color_fixture(background_color, text_color)

    recovered = recover_line_color(full, background, text, bbox)

    assert recovered.hex_color == text_color
    assert recovered.method == "full_background_delta"
    assert recovered.confidence >= 0.85


def test_color_recovery_falls_back_to_text_with_low_confidence():
    from scripts.recover_text_styles import recover_line_color

    full, background, text, bbox = _make_color_fixture("#FFFFFF", "#12355B")
    full = background.copy()

    recovered = recover_line_color(full, background, text, bbox)

    assert recovered.method == "text_fallback"
    assert recovered.confidence < 0.60


def test_text_mask_tracks_text_geometry():
    from scripts.recover_text_styles import build_text_mask

    _, _, text, bbox = _make_color_fixture("#FFFFFF", "#12355B")

    mask = build_text_mask(text, bbox)

    assert mask.mode == "L"
    assert mask.size == (bbox.width, bbox.height)
    assert mask.getbbox() is not None
    assert 0 < sum(1 for value in mask.get_flattened_data() if value) < bbox.width * bbox.height


def _make_font_mask(text: str, size_px: int, weight: str):
    from scripts.font_resolver import resolve_font_face
    from scripts.models import BBox

    bbox = BBox(0, 0, 420, 90)
    image = Image.new("L", (bbox.width, bbox.height), 0)
    font = ImageFont.truetype(str(resolve_font_face("Microsoft YaHei", weight)), size_px)
    ImageDraw.Draw(image).text((4, 0), text, font=font, fill=255)
    return image, bbox


@pytest.mark.parametrize("weight", ["regular", "bold"])
def test_font_fit_recovers_yahei_size_and_weight(weight):
    from scripts.recover_text_styles import fit_font_style

    mask, bbox = _make_font_mask("103682", 48, weight)

    result = fit_font_style("103682", mask, bbox, "Microsoft YaHei")

    assert result.weight == weight
    assert abs(result.font_size_px - 48) <= 2
    assert result.confidence >= 0.80


@pytest.mark.parametrize(
    ("bbox", "container", "expected"),
    [
        ((110, 20, 80, 20), (0, 0, 300, 80), "center"),
        ((16, 20, 180, 20), (0, 0, 300, 80), "left"),
        ((104, 20, 180, 20), (0, 0, 300, 80), "right"),
    ],
)
def test_recover_alignment(bbox, container, expected):
    from scripts.models import BBox
    from scripts.recover_text_styles import recover_alignment

    result = recover_alignment(BBox(*bbox), BBox(*container))

    assert result.align == expected
    assert 0 <= result.confidence <= 1


def test_mixed_run_recovery_splits_emphasized_number_and_unit():
    from scripts.font_resolver import resolve_font_face
    from scripts.models import BBox
    from scripts.recover_text_styles import recover_mixed_runs

    bbox = BBox(20, 10, 460, 80)
    background = Image.new("RGB", (500, 100), "#FFFFFF")
    full = background.copy()
    text = Image.new("RGB", (500, 100), "#FFFFFF")
    number_font = ImageFont.truetype(str(resolve_font_face("Microsoft YaHei", "bold")), 48)
    unit_font = ImageFont.truetype(str(resolve_font_face("Microsoft YaHei", "regular")), 24)
    number = "103682"
    unit = " 亿千瓦时"
    unit_x = 30 + round(ImageDraw.Draw(full).textlength(number, font=number_font)) + 8
    ImageDraw.Draw(full).text((30, 8), number, font=number_font, fill="#12355B")
    ImageDraw.Draw(full).text((unit_x, 28), unit, font=unit_font, fill="#101820")
    ImageDraw.Draw(text).text((30, 8), number, font=number_font, fill="#101010")
    ImageDraw.Draw(text).text((unit_x, 28), unit, font=unit_font, fill="#101010")

    runs = recover_mixed_runs(number + unit, full, background, text, bbox, "Microsoft YaHei")

    assert [run.text for run in runs] == [number, unit]
    assert runs[0].style["weight"] == "bold"
    assert abs(runs[0].style["font_size_px"] - 48) <= 3
    assert runs[0].style["color"] == "#12355B"
    assert runs[1].style["weight"] == "regular"
    assert abs(runs[1].style["font_size_px"] - 24) <= 3
    assert runs[1].style["color"] == "#101820"
