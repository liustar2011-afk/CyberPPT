from scripts.dual_image_overlay.scene_graph.constrained_reflow import (
    apply_recognized_constrained_reflow,
)
from scripts.dual_image_overlay.scene_graph.layout import build_layout_plan_from_scene_graph
from scripts.dual_image_overlay.scene_graph.schema import (
    BBox,
    PageSceneGraph,
    TextBinding,
    TextNode,
    VisualNode,
)


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


def test_reflow_wraps_left_body_inside_illustration_safe_boundary():
    graph = PageSceneGraph(
        page=16,
        coordinate_context={"coordinate_space": {"width": 1600, "height": 900}},
        truth_sources={"script": {"authority": "text_truth"}},
        visual_nodes=[
            VisualNode(
                "left_body",
                "layout_zone",
                "body",
                BBox(100, 180, 760, 260),
                {"kind": "layout_reference"},
                attributes={"recognized_layout": True},
            ),
            VisualNode(
                "middle_illustration",
                "visual_anchor",
                "illustration",
                BBox(650, 160, 900, 300),
                {"kind": "layout_reference"},
                attributes={"recognized_layout": True},
            ),
        ],
        text_nodes=[
            TextNode(
                "body",
                "• 这是一段需要在插图区之前自动换行的可靠正文内容，不能越过识别出的正文安全区。",
                {"kind": "script"},
                "body",
                binding=None,
            )
        ],
    )

    updated, report = apply_recognized_constrained_reflow(graph, strict=True)

    node = updated.text_nodes[0]
    assert report["valid"] is True
    assert node.binding is not None
    assert node.binding.safe_bbox is not None
    assert node.binding.safe_bbox.x2 <= 650 - 12
    assert "\n" in node.text


def test_reflow_uses_exact_bound_container_and_readable_diagram_font():
    graph = PageSceneGraph(
        page=16,
        coordinate_context={"coordinate_space": {"width": 1600, "height": 900}},
        truth_sources={"script": {"authority": "text_truth"}},
        visual_nodes=[
            VisualNode(
                "diagram_a",
                "layout_zone",
                "diagram_body",
                BBox(900, 300, 1100, 370),
                {"kind": "layout_reference"},
                attributes={"recognized_layout": True},
            ),
            VisualNode(
                "diagram_b",
                "layout_zone",
                "diagram_body",
                BBox(1150, 300, 1350, 370),
                {"kind": "layout_reference"},
                attributes={"recognized_layout": True},
            ),
        ],
        text_nodes=[
            TextNode(
                "label",
                "内部事件\n状态变更通知",
                {"kind": "script"},
                "diagram_body",
                binding=TextBinding(type="container_text", target_id="diagram_b"),
                style={"font_size": 9},
            )
        ],
    )

    updated, _ = apply_recognized_constrained_reflow(graph, strict=True)

    node = updated.text_nodes[0]
    assert node.binding is not None
    assert node.binding.target_id == "diagram_b"
    assert node.style["font_size"] == 11.0


def test_reflow_preserves_explicit_non_breaking_label_distribution():
    graph = PageSceneGraph(
        page=16,
        coordinate_context={"coordinate_space": {"width": 1600, "height": 900}},
        truth_sources={"script": {"authority": "text_truth"}},
        visual_nodes=[
            VisualNode(
                "gateway_controls",
                "layout_zone",
                "diagram_body",
                BBox(800, 150, 1450, 200),
                {"kind": "layout_reference"},
                attributes={"recognized_layout": True},
            )
        ],
        text_nodes=[
            TextNode(
                "controls",
                "认证   签名   幂等   版本   错误码   限流   追踪   模型",
                {"kind": "script"},
                "diagram_body",
                binding=TextBinding(type="container_text", target_id="gateway_controls"),
                style={"font_size": 9},
            )
        ],
    )

    updated, _ = apply_recognized_constrained_reflow(graph, strict=True)

    assert updated.text_nodes[0].text.count("\n") == 0


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


def test_strict_reflow_blocks_empty_text_graph():
    graph = PageSceneGraph(
        page=16,
        coordinate_context={"coordinate_space": {"width": 1600, "height": 900}},
        truth_sources={},
    )

    _, report = apply_recognized_constrained_reflow(graph, strict=True)

    assert report["valid"] is False
    assert report["issues"][0]["code"] == "missing_text_nodes"
