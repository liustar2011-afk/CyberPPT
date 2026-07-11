from pathlib import Path

from PIL import Image, ImageDraw

from scripts.dual_image_overlay.rebuild_engine.text_style_evidence import infer_line_style


def test_infers_deterministic_visual_attributes(tmp_path: Path) -> None:
    image = Image.new("RGB", (120, 40), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 100, 20), fill=(20, 80, 140))
    catalog = tmp_path / "fonts.txt"
    catalog.write_text("Test Sans\nFallback Serif\n", encoding="utf-8")
    line = {
        "bbox": [10, 10, 100, 20],
        "line_height_px": 10,
        "items": [
            {"text": "ABC", "bbox": [10, 10, 45, 20]},
            {"text": "DEF", "bbox": [49, 10, 100, 20]},
        ],
    }
    style = infer_line_style(image, line, font_catalog=catalog)
    assert style["color"] == "#14508c"
    assert style["line_height_px"] == 10
    assert style["font_weight"] == "700"
    assert style["similar_fonts"] == ["Test Sans", "Fallback Serif"]
    assert style["font_family"] is None
    assert style["confidence"]["font_family"] == 0.0
    assert "image" not in style["evidence"]["font_family"].lower() or "exact" in style["evidence"]["font_family"].lower()
