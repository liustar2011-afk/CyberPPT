from scripts.dual_image_overlay.scene_graph.page_svg_ir import compile_scene_graph_to_page_svg_ir, validate_page_svg_ir
from scripts.dual_image_overlay.scene_graph.schema import BBox, PageSceneGraph, Relation, TextBinding, TextNode, VisualNode


def _graph() -> PageSceneGraph:
    return PageSceneGraph(
        page=3,
        coordinate_context={"normalized_canvas": {"width": 1672, "height": 941}, "coordinate_space": {"width": 1672, "height": 941}},
        visual_nodes=[
            VisualNode("card", "container", "application_card", BBox(100, 100, 500, 400), {"kind": "semantic_plan"}),
            VisualNode("icon", "icon", "application_icon", BBox(130, 140, 190, 200), {"kind": "registry"}),
        ],
        text_nodes=[
            TextNode("title", "业务应用", {"kind": "script", "authority": "text_truth"}, "card_title", TextBinding("container_text", "card", safe_bbox=BBox(220, 140, 460, 210))),
        ],
        relations=[Relation("contains", "card", "icon")],
    )


def test_compile_scene_graph_to_page_svg_ir_separates_layers_and_preserves_truth():
    ir = compile_scene_graph_to_page_svg_ir(_graph(), background_href="images/page_003_background.png")
    assert ir["schema"] == "cyberppt.page_svg_ir.v1"
    assert ir["root_attributes"]["data-pptx-bounds"] == "0 0 1672.0 941.0"
    assert [layer["id"] for layer in ir["layers"]] == ["background", "visuals", "editable_information"]
    text = ir["layers"][2]["elements"][0]
    assert text["editable"] is True
    assert text["truth_source"]["kind"] == "script"
    assert ir["layers"][0]["elements"][0]["text_bearing"] is False
    assert ir["page_svg_ir_gate"]["valid"] is True
    assert ir["image_assets"]["assets"][0]["uses"] == 1


def test_validate_page_svg_ir_rejects_duplicate_ids():
    ir = {"canvas": {"width": 100, "height": 100}, "layers": [{"elements": [{"id": "x", "kind": "shape", "bbox": {"x": 0, "y": 0, "width": 10, "height": 10}}, {"id": "x", "kind": "shape", "bbox": {"x": 0, "y": 0, "width": 10, "height": 10}}]}]}
    gate = validate_page_svg_ir(ir)
    assert gate["valid"] is False
    assert gate["issues"][0]["code"] == "duplicate_or_missing_element_id"
