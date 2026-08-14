from scripts.dual_image_overlay.scene_graph.page_svg_ir import compile_scene_graph_to_page_svg_ir
from scripts.dual_image_overlay.scene_graph.qa_fusion import build_qa_fusion_report
from scripts.dual_image_overlay.scene_graph.schema import BBox, PageSceneGraph, TextBinding, TextNode, VisualNode


def _ir():
    graph = PageSceneGraph(
        page=2,
        coordinate_context={"normalized_canvas": {"width": 1672, "height": 941}, "coordinate_space": {"width": 1672, "height": 941}},
        visual_nodes=[VisualNode("card", "container", "card", BBox(20, 20, 500, 300), {"kind": "semantic_plan"})],
        text_nodes=[TextNode("title", "标题", {"kind": "script"}, "title", TextBinding("container_text", "card", safe_bbox=BBox(50, 50, 400, 100)))],
    )
    return graph, compile_scene_graph_to_page_svg_ir(graph)


def test_qa_fusion_requires_all_internal_gates_and_allows_deferred_checker():
    graph, ir = _ir()
    report = build_qa_fusion_report(scene_graph_gate=ir["scene_graph_gate"], page_svg_ir=ir)
    assert report["valid"] is True
    assert report["components"]["ppt_master_svg"]["status"] == "deferred"


def test_qa_fusion_blocks_when_ppt_master_checker_is_required_but_missing():
    graph, ir = _ir()
    report = build_qa_fusion_report(scene_graph_gate=ir["scene_graph_gate"], page_svg_ir=ir, require_ppt_master=True)
    assert report["valid"] is False
    assert any(item["component"] == "ppt_master_svg" for item in report["blocking_errors"])

