from scripts.dual_image_overlay.scene_graph.builder import build_page_scene_graph


def test_builds_container_text_binding_from_script_and_registry():
    graph = build_page_scene_graph(
        page_number=6,
        script_sections={
            "右侧｜结果应用方": [{"title": "企业应用", "lines": ["画像管理、投标预审、融资保险"]}]
        },
        semantic_plan={
            "image_size": {"width": 1920, "height": 941},
            "containers": [
                {"id": "application_1", "role": "application_card", "bbox": [1344, 134, 1586, 281]}
            ],
            "items": [],
        },
        visual_registry={
            "blueprint_canvas_px": {"w": 1920, "h": 941},
            "elements": [
                {
                    "element_id": "p6_app_card_1",
                    "element_type": "application_card",
                    "source_component_id": "p6_result_apps",
                    "blueprint_bbox_px": {"x": 1340, "y": 130, "w": 250, "h": 155},
                },
                {
                    "element_id": "p6_app_icon_1",
                    "element_type": "icon",
                    "source_component_id": "p6_result_apps",
                    "blueprint_bbox_px": {"x": 1355, "y": 160, "w": 54, "h": 54},
                },
                {
                    "element_id": "p6_app_text_zone_1",
                    "element_type": "text_zone",
                    "source_component_id": "p6_result_apps",
                    "blueprint_bbox_px": {"x": 1420, "y": 175, "w": 145, "h": 70},
                },
            ],
        },
        image_size={"width": 1920, "height": 941},
    )

    assert graph.text_nodes[0].text == "企业应用\n• 画像管理\n• 投标预审\n• 融资保险"
    assert graph.text_nodes[0].binding.type == "container_text"
    assert graph.text_nodes[0].binding.target_id == "application_1"
    assert any(intent.type == "honor_text_zone" for intent in graph.layout_intents)
    assert any(rel.type == "contains" and rel.source_id == "application_1" for rel in graph.relations)


def test_builds_edge_label_binding_without_container():
    graph = build_page_scene_graph(
        page_number=7,
        script_sections={"箭头关系": [{"title": "", "lines": ["右侧应用反馈 → 中部核心空间，表示结果应用反馈更新"]}]},
        semantic_plan={
            "image_size": {"width": 1280, "height": 720},
            "containers": [],
            "items": [
                {
                    "display_text": "反馈更新",
                    "source_text": "反馈更新",
                    "role": "arrow_label",
                    "target_id": "arrow_1",
                }
            ],
        },
        visual_registry={
            "blueprint_canvas_px": {"w": 1280, "h": 720},
            "elements": [
                {
                    "element_id": "arrow_1",
                    "element_type": "flow_arrow",
                    "blueprint_bbox_px": {"x": 500, "y": 300, "w": 120, "h": 20},
                }
            ],
        },
        image_size={"width": 1280, "height": 720},
    )

    assert graph.text_nodes[0].binding.type == "edge_label"
    assert graph.text_nodes[0].binding.target_id == "arrow_1"
    assert any(intent.type == "label_on_arrow" for intent in graph.layout_intents)
