from scripts.image_to_editable_svg.contracts import NormalizedFrame, build_inventory, page_gate


def test_manual_required_region_blocks_page_gate():
    gate = page_gate([{"id": "chart", "realization": "manual_required"}])
    assert gate["valid"] is False
    assert gate["blocking_errors"][0]["code"] == "manual_required"


def test_inventory_is_json_safe_and_retains_frame():
    frame = NormalizedFrame(4, "/source.png", "abc", "/frame.png", (80, 40))
    inventory = build_inventory(frame, [{"id": "shape", "family": "simple_geometry", "bbox": [0, 0, 10, 10]}])
    assert inventory["frame"]["pixel_size"] == [80, 40]
    assert inventory["regions"][0]["id"] == "shape"
