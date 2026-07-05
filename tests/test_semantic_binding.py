from scripts.dual_image_overlay.semantic_binding import build_semantic_binding, semantic_binding_to_plan


def test_builds_binding_from_ocr_boxes_and_scene_graph_containers():
    scene_graph = {
        "visual_nodes": [
            {
                "node_id": "left_card",
                "element_type": "container",
                "semantic_role": "source_card",
                "bbox": [0, 0, 200, 100],
            },
            {
                "node_id": "right_card",
                "element_type": "container",
                "semantic_role": "application_card",
                "bbox": [300, 0, 500, 100],
                "aliases": ["application_1"],
            },
        ]
    }
    ocr_items = [
        {"text": "企业与业务数据", "bbox": [20, 20, 160, 50]},
        {"text": "企业应用", "bbox": [320, 20, 460, 50]},
    ]

    binding = build_semantic_binding(
        page_number=6,
        script_sections={},
        ocr_items=ocr_items,
        scene_graph=scene_graph,
        source_capture_page=None,
        visual_registry=None,
    )

    assert binding["schema"] == "cyberppt.semantic_binding.v1"
    assert binding["page_number"] == 6
    assert binding["checks"]["unassigned_text_count"] == 0
    assert {item["container_id"] for item in binding["items"]} == {"left_card", "right_card"}

    plan = semantic_binding_to_plan(binding)
    assert plan["schema"] == "cyberppt.explicit_semantic_plan.v1"
    assert len(plan["containers"]) == 2
    assert len(plan["items"]) == 2


def test_binding_preserves_aliases_for_governance_safety_strip():
    scene_graph = {
        "visual_nodes": [
            {
                "node_id": "safety_1",
                "element_type": "container",
                "semantic_role": "governance_step",
                "bbox": [1174, 160, 1260, 199],
                "aliases": ["governance_1"],
            }
        ]
    }
    binding = build_semantic_binding(
        page_number=6,
        script_sections={},
        ocr_items=[{"text": "分类分级", "bbox": [1182, 166, 1252, 193]}],
        scene_graph=scene_graph,
        source_capture_page=None,
        visual_registry=None,
    )
    container = binding["containers"][0]
    assert container["id"] == "safety_1"
    assert "governance_1" in container["aliases"]
    assert binding["items"][0]["container_id"] == "safety_1"
