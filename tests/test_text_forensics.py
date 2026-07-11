from pathlib import Path

from PIL import Image

from scripts.dual_image_overlay.rebuild_engine.text_forensics import build_line_evidence


def make_test_image(tmp_path: Path) -> Path:
    path = tmp_path / "slide.png"
    image = Image.new("RGB", (1000, 600), "white")
    image.save(path)
    return path


def test_build_line_evidence_merges_adjacent_words_on_one_baseline(tmp_path):
    layout = {"image_size": {"width": 1000, "height": 600}, "items": [
        {"text": "经营", "bbox": [10, 20, 60, 50], "confidence": .98},
        {"text": "管理", "bbox": [64, 20, 114, 50], "confidence": .97},
    ]}
    result = build_line_evidence(layout, make_test_image(tmp_path), evidence_dir=tmp_path / "evidence")
    assert result["lines"][0]["observed_text"] == "经营管理"
    assert Path(result["lines"][0]["glyph_crop"]).is_file()


def test_build_line_evidence_orders_lines_top_to_bottom_and_words_left_to_right(tmp_path):
    layout = {"image_size": {"width": 1000, "height": 600}, "items": [
        {"text": "下", "bbox": [100, 120, 130, 145]},
        {"text": "上右", "bbox": [80, 20, 130, 48]},
        {"text": "上左", "bbox": [10, 20, 60, 48]},
    ]}
    result = build_line_evidence(layout, make_test_image(tmp_path), evidence_dir=tmp_path / "evidence")
    assert [line["observed_text"] for line in result["lines"]] == ["上左上右", "下"]
    assert [line["reading_order"] for line in result["lines"]] == [1, 2]


def test_build_line_evidence_records_scale_and_polygon(tmp_path):
    layout = {"image_size": {"width": 500, "height": 300}, "backend": "vision-json", "items": [
        {"text": "证据", "bbox": [10, 20, 60, 50], "polygon": [[10, 20], [60, 20], [60, 50], [10, 50]]},
    ]}
    result = build_line_evidence(layout, make_test_image(tmp_path), evidence_dir=tmp_path / "evidence")
    assert result["image"]["scale"] == {"x": 2.0, "y": 2.0}
    assert result["lines"][0]["polygon"] == [[10, 20], [60, 20], [60, 50], [10, 50]]
