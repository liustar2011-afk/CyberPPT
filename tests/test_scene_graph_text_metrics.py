from scripts.dual_image_overlay.scene_graph.schema import BBox
from scripts.dual_image_overlay.scene_graph.text_metrics import avoid_reserved_zones, fit_text_to_safe_bbox, measure_text


def test_measure_text_is_cjk_conservative_and_multiline_aware():
    result = measure_text("业务应用\n数据治理", 12)
    assert result["line_count"] == 2
    assert result["width"] >= 48
    assert result["height"] > 12


def test_fit_wraps_before_reducing_and_reports_readability_floor():
    result = fit_text_to_safe_bbox("业务应用与数据治理", BBox(0, 0, 70, 40), 14, min_font_size=7)
    assert result["status"] in {"fit", "fit_after_scale"}
    assert result["font_size"] >= 7
    blocked = fit_text_to_safe_bbox("一段很长的不可压缩文本", BBox(0, 0, 10, 8), 14, min_font_size=7)
    assert blocked["status"] == "blocked_overflow"


def test_avoid_reserved_zone_shifts_inside_safe_bbox():
    result = avoid_reserved_zones(BBox(10, 10, 50, 30), BBox(0, 0, 100, 100), [BBox(10, 10, 50, 30)])
    assert result["status"] == "shifted"
    assert result["bbox"][1] > 30

