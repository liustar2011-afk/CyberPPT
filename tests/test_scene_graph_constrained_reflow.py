from scripts.dual_image_overlay.scene_graph.constrained_reflow import (
    apply_recognized_constrained_reflow,
)
from scripts.dual_image_overlay.scene_graph.layout import build_layout_plan_from_scene_graph
from scripts.dual_image_overlay.scene_graph.schema import BBox, PageSceneGraph, TextNode, VisualNode


def test_reflow_matches_semantic_roles_and_becomes_layout_source():
    graph = PageSceneGraph(
        page=16,
        coordinate_context={
            "coordinate_space": {"width": 1600, "height": 900},
            "normalized_canvas": {"width": 1600, "height": 900},
        },
        truth_sources={"script": {"authority": "text_truth"}},
        visual_nodes=[
            VisualNode(
                "recognized_title",
                "layout_zone",
                "title",
                BBox(100, 50, 900, 120),
                {"kind": "layout_reference"},
                attributes={"recognized_layout": True},
            ),
            VisualNode(
                "recognized_body",
                "layout_zone",
                "body",
                BBox(100, 180, 650, 300),
                {"kind": "layout_reference"},
                attributes={"recognized_layout": True},
            ),
        ],
        text_nodes=[
            TextNode("text_body", "这是可靠的正文内容，需要根据实际长度重新换行。", {"kind": "script"}, "body"),
            TextNode("text_title", "可靠标题", {"kind": "script"}, "title"),
        ],
        metadata={
            "layout_reference": {
                "layout_grammar": {"page_type_hint": "custom", "composition": "judgment_evidence"}
            }
        },
    )

    updated, report = apply_recognized_constrained_reflow(graph, strict=True)
    plan = build_layout_plan_from_scene_graph(updated)
    by_id = {item["node_id"]: item for item in plan["items"]}

    assert report["valid"] is True
    assert report["assigned_count"] == 2
    assert by_id["text_title"]["target_id"] == "recognized_title"
    assert by_id["text_title"]["layout_source"] == "recognized_layout_reflow"
    assert by_id["text_body"]["target_id"] == "recognized_body"
    assert by_id["text_body"]["bbox"] != [100.0, 180.0, 650.0, 300.0]
    assert report["expression_pattern_preserved"] is True


def test_strict_reflow_blocks_when_text_has_no_recognized_region():
    graph = PageSceneGraph(
        page=16,
        coordinate_context={"coordinate_space": {"width": 1600, "height": 900}},
        truth_sources={},
        text_nodes=[TextNode("text_1", "无法分配", {"kind": "script"}, "body")],
    )

    _, report = apply_recognized_constrained_reflow(graph, strict=True)

    assert report["valid"] is False
    assert report["unassigned_count"] == 1
