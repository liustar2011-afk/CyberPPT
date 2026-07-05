import pytest

from scripts.dual_image_overlay.scene_graph.schema import (
    BBox,
    GateIssue,
    LayoutIntent,
    PageSceneGraph,
    Relation,
    TextBinding,
    TextNode,
    VisualNode,
    scene_graph_from_dict,
    scene_graph_to_dict,
)


def test_scene_graph_round_trip_preserves_binding_and_nodes():
    graph = PageSceneGraph(
        page=6,
        coordinate_context={"normalized_canvas": {"width": 1280, "height": 720}},
        truth_sources={"script": {"path": "script.md", "authority": "text_truth"}},
        gates={"binding": {"status": "pending"}},
        gate_issues=[
            GateIssue(
                severity="error",
                code="missing_truth_binding",
                node_id="text_1",
                source={"kind": "scene_graph_gate"},
                evidence={"text": "企业应用"},
                recommended_action="Bind the text node.",
                blocking=True,
            )
        ],
        visual_nodes=[
            VisualNode(
                node_id="card_1",
                node_type="container",
                semantic_role="application_card",
                bbox=BBox(100, 80, 280, 180),
                source={"kind": "visual_element_registry"},
                confidence=1.0,
                component_id="p6_result_apps",
            )
        ],
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="企业应用",
                truth_source={"kind": "script", "path": "script.md"},
                semantic_role="card_title",
                binding=TextBinding(type="container_text", target_id="card_1", placement="inside"),
            )
        ],
    )

    payload = scene_graph_to_dict(graph)
    restored = scene_graph_from_dict(payload)

    assert payload["schema"] == "cyberppt.page_scene_graph.v1"
    assert payload["gates"] == {"binding": {"status": "pending"}}
    assert payload["gate_issues"][0]["code"] == "missing_truth_binding"
    assert restored.gates == {"binding": {"status": "pending"}}
    assert restored.gate_issues[0].blocking is True
    assert restored.text_nodes[0].binding.type == "container_text"
    assert restored.visual_nodes[0].bbox.as_list() == [100.0, 80.0, 280.0, 180.0]


def test_gate_issue_shape_contains_required_fields():
    issue = GateIssue(
        severity="error",
        code="missing_truth_binding",
        node_id="text_1",
        source={"kind": "scene_graph_gate"},
        evidence={"text": "反馈迭代"},
        recommended_action="Bind the text node to a container, edge, anchor, region, title chrome, or legend.",
        blocking=True,
    )

    assert issue.to_dict() == {
        "severity": "error",
        "code": "missing_truth_binding",
        "node_id": "text_1",
        "source": {"kind": "scene_graph_gate"},
        "evidence": {"text": "反馈迭代"},
        "recommended_action": "Bind the text node to a container, edge, anchor, region, title chrome, or legend.",
        "blocking": True,
    }


def test_relation_emits_type_and_metrics_contract():
    graph = PageSceneGraph(
        page=6,
        relations=[Relation(type="contains", source_id="card_1", target_id="text_1", metrics={"distance": 0})],
    )

    payload = scene_graph_to_dict(graph)
    relation = payload["relations"][0]
    restored = scene_graph_from_dict(payload)

    assert relation["type"] == "contains"
    assert relation["metrics"] == {"distance": 0}
    assert relation["confidence"] == 1.0
    assert "relation_type" not in relation
    assert restored.relations[0].type == "contains"


def test_layout_intent_round_trip_uses_type_node_and_parameters():
    graph = PageSceneGraph(
        page=6,
        layout_intents=[LayoutIntent(type="honor_text_zone", node_id="text_1", target_id="zone_1")],
    )

    payload = scene_graph_to_dict(graph)
    intent = payload["layout_intents"][0]
    restored = scene_graph_from_dict(payload)

    assert intent == {
        "type": "honor_text_zone",
        "node_id": "text_1",
        "target_id": "zone_1",
        "parameters": {},
    }
    assert restored.layout_intents[0].type == "honor_text_zone"


def test_text_binding_safe_bbox_round_trips_as_list():
    graph = PageSceneGraph(
        page=6,
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="企业应用",
                truth_source={"kind": "script"},
                semantic_role="card_title",
                binding=TextBinding(
                    type="container_text",
                    target_id="card_1",
                    placement="inside",
                    safe_bbox=BBox(120, 100, 260, 150),
                ),
            )
        ],
    )

    payload = scene_graph_to_dict(graph)
    restored = scene_graph_from_dict(payload)

    assert payload["text_nodes"][0]["binding"]["safe_bbox"] == [120.0, 100.0, 260.0, 150.0]
    assert restored.text_nodes[0].binding.safe_bbox.as_list() == [120.0, 100.0, 260.0, 150.0]


def test_coordinate_context_preserves_scene_graph_details():
    graph = PageSceneGraph(
        page=6,
        coordinate_context={
            "coordinate_space": {"width": 1280, "height": 720},
            "semantic_input_space": {"width": 1920, "height": 941},
            "visual_registry_input_space": {"width": 1920, "height": 941},
            "warnings": [{"code": "semantic_coordinate_space_uses_plan_extent"}],
        },
    )

    payload = scene_graph_to_dict(graph)
    restored = scene_graph_from_dict(payload)
    restored_context = restored.coordinate_context.to_dict()

    assert payload["coordinate_context"]["semantic_input_space"] == {"width": 1920, "height": 941}
    assert restored_context["visual_registry_input_space"] == {"width": 1920, "height": 941}
    assert restored_context["warnings"] == [{"code": "semantic_coordinate_space_uses_plan_extent"}]


def test_text_node_bbox_preferred_round_trips():
    graph = PageSceneGraph(
        page=6,
        text_nodes=[
            TextNode(
                node_id="text_1",
                text="企业应用",
                truth_source={"kind": "script"},
                semantic_role="card_title",
                bbox_preferred=BBox(130, 110, 250, 145),
            )
        ],
    )

    payload = scene_graph_to_dict(graph)
    restored = scene_graph_from_dict(payload)

    assert payload["text_nodes"][0]["bbox_preferred"] == [130.0, 110.0, 250.0, 145.0]
    assert "bbox" not in payload["text_nodes"][0]
    assert restored.text_nodes[0].bbox_preferred.as_list() == [130.0, 110.0, 250.0, 145.0]


def test_scene_graph_from_dict_requires_schema():
    with pytest.raises(ValueError):
        scene_graph_from_dict({"page": 6})


def test_gate_issue_from_dict_requires_boolean_blocking():
    payload = {
        "severity": "error",
        "code": "missing_truth_binding",
        "node_id": "text_1",
        "source": {"kind": "scene_graph_gate"},
        "evidence": {},
        "recommended_action": "Bind text.",
        "blocking": "false",
    }

    with pytest.raises(ValueError):
        GateIssue.from_dict(payload)


def test_gate_issue_to_dict_requires_boolean_blocking():
    issue = GateIssue(
        severity="error",
        code="missing_truth_binding",
        node_id="text_1",
        source={"kind": "scene_graph_gate"},
        evidence={},
        recommended_action="Bind text.",
        blocking="false",
    )

    with pytest.raises(ValueError):
        issue.to_dict()


def test_relation_from_dict_requires_type_not_legacy_relation_type():
    payload = {"relation_type": "contains", "source_id": "card_1", "target_id": "text_1"}

    with pytest.raises((KeyError, ValueError)):
        Relation.from_dict(payload)


def test_relation_from_dict_rejects_legacy_relation_type_even_with_type():
    payload = {
        "type": "contains",
        "relation_type": "contains",
        "source_id": "card_1",
        "target_id": "text_1",
    }

    with pytest.raises(ValueError):
        Relation.from_dict(payload)


def test_layout_intent_from_dict_requires_type_not_legacy_intent_type():
    payload = {"intent_type": "honor_text_zone", "node_id": "text_1", "target_id": "zone_1"}

    with pytest.raises((KeyError, ValueError)):
        LayoutIntent.from_dict(payload)


def test_layout_intent_from_dict_rejects_legacy_intent_type_even_with_type():
    payload = {
        "type": "honor_text_zone",
        "intent_type": "honor_text_zone",
        "node_id": "text_1",
        "target_id": "zone_1",
    }

    with pytest.raises(ValueError):
        LayoutIntent.from_dict(payload)


def test_text_node_from_dict_rejects_legacy_bbox_without_bbox_preferred():
    payload = {
        "node_id": "text_1",
        "text": "企业应用",
        "truth_source": {"kind": "script"},
        "semantic_role": "card_title",
        "bbox": [130, 110, 250, 145],
    }

    with pytest.raises(ValueError):
        TextNode.from_dict(payload)


def test_text_node_from_dict_rejects_legacy_bbox_even_with_bbox_preferred():
    payload = {
        "node_id": "text_1",
        "text": "企业应用",
        "truth_source": {"kind": "script"},
        "semantic_role": "card_title",
        "bbox": [130, 110, 250, 145],
        "bbox_preferred": [130, 110, 250, 145],
    }

    with pytest.raises(ValueError):
        TextNode.from_dict(payload)
