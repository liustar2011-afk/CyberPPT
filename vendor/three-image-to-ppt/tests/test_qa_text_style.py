from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


def _fixture(text_color: str = "#12355B", background_color: str = "#FFFFFF"):
    size = (320, 100)
    background = Image.new("RGB", size, background_color)
    full = background.copy()
    rendered = background.copy()
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 34)
    for image in (full, rendered):
        ImageDraw.Draw(image).text((30, 25), "103682", font=font, fill=text_color)
    line = {
        "line_id": "L001",
        "text": "103682",
        "target": {"bbox_px": {"x": 20, "y": 15, "width": 200, "height": 70}},
    }
    return rendered, full, background, line


def test_text_style_qa_reports_color_and_mask_similarity():
    from scripts.qa_text_style import compare_text_line

    rendered, full, background, line = _fixture()

    report = compare_text_line(rendered, full, background, line)

    assert report["mask_iou"] >= 0.95
    assert report["color_distance_rgb"] <= 2
    assert report["contrast_ratio"] >= 3.0
    assert report["overflow"] is False
    assert report["status"] == "passed"


def test_text_style_qa_routes_low_contrast_to_review():
    from scripts.qa_text_style import compare_text_line

    rendered, full, background, line = _fixture("#404850", "#3E464E")

    report = compare_text_line(rendered, full, background, line)

    assert report["contrast_ratio"] < 3.0
    assert report["status"] == "review"


def test_text_style_qa_routes_overflow_to_failed():
    from scripts.qa_text_style import compare_text_line

    rendered, full, background, line = _fixture()

    report = compare_text_line(rendered, full, background, line, overflow=True)

    assert report["overflow"] is True
    assert report["status"] == "failed"
