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
    assert result["lines"][0]["polygon"] == [[20.0, 40.0], [120.0, 40.0], [120.0, 100.0], [20.0, 100.0]]
    assert result["lines"][0]["source_polygon"] == [[10, 20], [60, 20], [60, 50], [10, 50]]


def test_build_line_evidence_maps_declared_geometry_to_actual_pixels(tmp_path):
    layout = {"image_size": {"width": 500, "height": 300}, "items": [
        {"text": "缩放", "bbox": [10, 20, 60, 50]},
    ]}
    result = build_line_evidence(layout, make_test_image(tmp_path), evidence_dir=tmp_path / "evidence")
    assert result["lines"][0]["bbox"] == [17, 37, 123, 103]
    assert result["lines"][0]["source_bbox"] == [[10.0, 20.0, 60.0, 50.0]]


def test_build_line_evidence_is_invariant_to_ocr_item_permutation(tmp_path):
    items = [{"text": "左", "bbox": [10, 20, 40, 50]}, {"text": "右", "bbox": [45, 20, 75, 50]}, {"text": "下", "bbox": [10, 100, 40, 130]}]
    image = make_test_image(tmp_path)
    first = build_line_evidence({"image_size": {"width": 1000, "height": 600}, "items": items}, image, evidence_dir=tmp_path / "a")
    second = build_line_evidence({"image_size": {"width": 1000, "height": 600}, "items": list(reversed(items))}, image, evidence_dir=tmp_path / "b")
    assert [line["observed_text"] for line in first["lines"]] == [line["observed_text"] for line in second["lines"]]


def test_dominant_fill_excludes_colored_background(tmp_path):
    path = tmp_path / "colored.png"
    image = Image.new("RGB", (100, 60), "#204060")
    for x in range(20, 50):
        for y in range(20, 35):
            image.putpixel((x, y), (245, 245, 245))
    image.save(path)
    result = build_line_evidence({"image_size": {"width": 100, "height": 60}, "items": [{"text": "字", "bbox": [20, 20, 50, 35]}]}, path, evidence_dir=tmp_path / "evidence")
    assert result["lines"][0]["dominant_fill"] == "#f5f5f5"
