from scripts.dual_image_overlay.scene_graph.builder import build_page_scene_graph
from scripts.dual_image_overlay.scene_graph.gate import build_scene_graph_gate
from scripts.dual_image_overlay.scene_graph.schema import BBox, LayoutIntent, PageSceneGraph, TextBinding, TextNode, VisualNode


def test_gate_blocks_ocr_as_final_text_truth():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        visual_nodes=[
            VisualNode(
                node_id="card_1",
                node_type="container",
                semantic_role="card",
                bbox=BBox(100, 100, 180, 140),
                source={"kind": "semantic_plan"},
            )
        ],
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="OCR内容",
                truth_source={"kind": "ocr"},
                semantic_role="body",
                binding=TextBinding(type="container_text", target_id="card_1"),
            )
        ],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is False
    assert gate["issues"][0]["code"] == "script_truth_mismatch"


def test_gate_allows_arrow_label_without_container():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        visual_nodes=[
            VisualNode(
                node_id="arrow_1",
                node_type="flow_arrow",
                semantic_role="feedback_arrow",
                bbox=BBox(100, 100, 180, 110),
                source={"kind": "visual_element_registry"},
            )
        ],
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="反馈更新",
                truth_source={"kind": "script"},
                semantic_role="arrow_label",
                binding=TextBinding(type="edge_label", target_id="arrow_1"),
            )
        ],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is True
    assert gate["blocking_count"] == 0


def test_gate_blocks_registry_text_zone_without_bound_text():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        visual_nodes=[
            VisualNode(
                node_id="text_zone_1",
                node_type="text_zone",
                semantic_role="application_text_zone",
                bbox=BBox(100, 100, 180, 140),
                source={"kind": "visual_element_registry"},
            )
        ],
        text_nodes=[],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is False
    assert gate["issues"][0]["code"] == "registry_container_without_text"


def test_gate_treats_honor_text_zone_intent_as_text_zone_bound():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        visual_nodes=[
            VisualNode(
                node_id="card_1",
                node_type="container",
                semantic_role="application_card",
                bbox=BBox(80, 80, 240, 180),
                source={"kind": "semantic_plan"},
            ),
            VisualNode(
                node_id="text_zone_1",
                node_type="text_zone",
                semantic_role="application_text_zone",
                bbox=BBox(130, 100, 230, 170),
                source={"kind": "visual_element_registry"},
            ),
        ],
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="企业应用",
                truth_source={"kind": "script"},
                semantic_role="application_card_text",
                binding=TextBinding(type="container_text", target_id="card_1"),
            )
        ],
        layout_intents=[LayoutIntent(type="honor_text_zone", node_id="text_1", target_id="text_zone_1")],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is True


def test_gate_passes_builder_output_with_text_zone_intent():
    graph = build_page_scene_graph(
        page_number=6,
        script_sections={
            "右侧｜结果应用方": [{"title": "企业应用", "lines": ["画像管理、投标预审、融资保险"]}]
        },
        semantic_plan={
            "image_size": {"width": 1920, "height": 941},
            "containers": [{"id": "application_1", "role": "application_card", "bbox": [1344, 134, 1586, 281]}],
            "items": [],
        },
        visual_registry={
            "blueprint_canvas_px": {"w": 1920, "h": 941},
            "elements": [
                {
                    "element_id": "p6_app_text_zone_1",
                    "element_type": "text_zone",
                    "blueprint_bbox_px": {"x": 1420, "y": 175, "w": 145, "h": 70},
                }
            ],
        },
        image_size={"width": 1920, "height": 941},
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is True
