from scripts.dual_image_overlay.scene_graph.layout import build_layout_plan_from_scene_graph
from scripts.dual_image_overlay.scene_graph.schema import BBox, LayoutIntent, PageSceneGraph, TextBinding, TextNode, VisualNode


def test_layout_places_container_text_inside_text_zone_and_after_icon():
    graph = PageSceneGraph(
        page=6,
        coordinate_context={"coordinate_space": {"width": 1280, "height": 720}},
        truth_sources={},
        visual_nodes=[
            VisualNode("application_1", "container", "application_card", BBox(896, 100, 1058, 220), {"kind": "semantic_plan"}),
            VisualNode("icon_1", "icon", "application_icon", BBox(904, 120, 940, 160), {"kind": "visual_element_registry"}),
            VisualNode("text_zone_1", "text_zone", "application_text_zone", BBox(946, 132, 1044, 188), {"kind": "visual_element_registry"}),
        ],
        text_nodes=[
            TextNode(
                "text_1",
                "企业应用\n• 画像管理\n• 投标预审",
                {"kind": "script"},
                "application_card_text",
                TextBinding("container_text", target_id="application_1"),
            )
        ],
        layout_intents=[
            LayoutIntent("honor_text_zone", "text_1", "text_zone_1"),
            LayoutIntent("avoid_reserved_zone", "text_1", "icon_1"),
        ],
    )

    plan = build_layout_plan_from_scene_graph(graph)
    item = plan["items"][0]

    assert item["bbox"] == [946.0, 132.0, 1044.0, 188.0]
    assert item["text"] == "企业应用\n• 画像管理\n• 投标预审"
    assert "honor_text_zone" in item["layout_intents"]
    assert "avoid_reserved_zone" in item["layout_intents"]


def test_layout_places_edge_label_above_arrow():
    graph = PageSceneGraph(
        page=7,
        coordinate_context={"coordinate_space": {"width": 1280, "height": 720}},
        truth_sources={},
        visual_nodes=[
            VisualNode("arrow_1", "flow_arrow", "feedback_arrow", BBox(500, 300, 620, 320), {"kind": "visual_element_registry"})
        ],
        text_nodes=[
            TextNode("text_1", "反馈更新", {"kind": "script"}, "arrow_label", TextBinding("edge_label", target_id="arrow_1"))
        ],
        layout_intents=[LayoutIntent("label_on_arrow", "text_1", "arrow_1")],
    )

    plan = build_layout_plan_from_scene_graph(graph)
    item = plan["items"][0]

    assert item["bbox"] == [500.0, 274.0, 620.0, 296.0]
    assert item["binding_type"] == "edge_label"
