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
