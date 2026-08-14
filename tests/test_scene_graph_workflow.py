from scripts.dual_image_overlay.scene_graph.gate import build_scene_graph_gate
from scripts.dual_image_overlay.scene_graph.schema import BBox, PageSceneGraph, TextBinding, TextNode, VisualNode


def test_strict_scene_graph_blocks_export_on_unbound_text():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="孤立文本",
                truth_source={"kind": "script"},
                semantic_role="body",
                binding=TextBinding(type="container_text", target_id="missing_container"),
            )
        ],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is False
    assert gate["blocking_count"] == 1
    assert gate["issues"][0]["code"] == "missing_truth_binding"


def test_strict_scene_graph_allows_edge_label_without_container():
    graph = PageSceneGraph(
        page=1,
        coordinate_context={"warnings": []},
        truth_sources={},
        visual_nodes=[
            VisualNode("arrow_1", "flow_arrow", "feedback_arrow", BBox(10, 10, 100, 20), {"kind": "visual_element_registry"})
        ],
        text_nodes=[
            TextNode("text_1", "反馈更新", {"kind": "script"}, "arrow_label", TextBinding("edge_label", target_id="arrow_1"))
        ],
    )

    gate = build_scene_graph_gate(graph)

    assert gate["valid"] is True
