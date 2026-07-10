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


def test_consumes_semantic_layout_neighbors_and_text_style():
    graph = build_page_scene_graph(
        page_number=6,
        script_sections={
            "右侧｜结果应用方": [{"title": "企业应用", "lines": ["画像管理、投标预审"]}]
        },
        semantic_plan={
            "image_size": {"width": 1280, "height": 720},
            "containers": [
                {
                    "id": "application_1",
                    "role": "application_card",
                    "bbox": [700, 160, 1040, 360],
                    "text_safe_bbox": [820, 190, 1010, 330],
                }
            ],
            "items": [
                {
                    "display_text": "企业应用\n• 画像管理\n• 投标预审",
                    "container_id": "application_1",
                    "font_size": 18,
                    "fill": "#123456",
                    "font_family": "Microsoft YaHei",
                    "font_weight": "700",
                    "align": "left",
                    "word_wrap": True,
                }
            ],
        },
        visual_registry={
            "blueprint_canvas_px": {"w": 1280, "h": 720},
            "elements": [
                {
                    "element_id": "app_icon_1",
                    "element_type": "icon",
                    "blueprint_bbox_px": {"x": 730, "y": 210, "w": 70, "h": 70},
                },
                {
                    "element_id": "app_text_zone_1",
                    "element_type": "text_zone",
                    "blueprint_bbox_px": {"x": 820, "y": 190, "w": 190, "h": 140},
                },
            ],
        },
        image_size={"width": 1280, "height": 720},
        semantic_layout_plan={
            "container_relations": [
                {
                    "container_id": "application_1",
                    "element_id": "app_icon_1",
                    "element_type": "icon",
                    "relation": "contained_or_component_matched",
                }
            ],
            "text_neighbors": [
                {
                    "text": "企业应用",
                    "container_id": "application_1",
                    "nearest": {
                        "left": {"element_id": "app_icon_1", "element_type": "icon", "distance": 12},
                        "overlapping": [
                            {"element_id": "app_text_zone_1", "element_type": "text_zone", "overlap_area": 2600}
                        ],
                    },
                }
            ],
        },
    )

    text = graph.text_nodes[0]
    assert text.style["font_size"] == 18
    assert text.style["fill"] == "#123456"
    assert text.binding.safe_bbox.as_list() == [820.0, 190.0, 1010.0, 330.0]
    assert any(rel.type == "contains" and rel.source_id == "application_1" and rel.target_id == "app_icon_1" for rel in graph.relations)
    assert any(intent.type == "neighbor_context" and intent.target_id == "app_icon_1" for intent in graph.layout_intents)
    assert any(intent.type == "avoid_reserved_zone" and intent.target_id == "app_icon_1" for intent in graph.layout_intents)
    assert any(intent.type == "honor_text_zone" and intent.target_id == "app_text_zone_1" for intent in graph.layout_intents)


def test_builder_attaches_semantic_layout_item_bbox_to_text_node():
    graph = build_page_scene_graph(
        page_number=6,
        script_sections={},
        semantic_plan={
            "image_size": {"width": 1280, "height": 720},
            "containers": [{"id": "ability_1", "role": "ability_card", "bbox": [300, 100, 520, 260]}],
            "items": [{"display_text": "目录管理", "role": "ability_title", "container_id": "ability_1"}],
        },
        visual_registry={"blueprint_canvas_px": {"w": 1280, "h": 720}, "elements": []},
        image_size={"width": 1280, "height": 720},
        semantic_layout_plan={
            "schema": "cyberppt.dual_image.semantic_layout_plan.v1",
            "items": [
                {
                    "text": "目录管理",
                    "container_id": "ability_1",
                    "bbox": [380.0, 121.0, 450.0, 140.0],
                    "layout_strategy": "ability_card_slots",
                }
            ],
        },
    )

    assert graph.text_nodes[0].style["layout_bbox"] == [380.0, 121.0, 450.0, 140.0]
    assert graph.text_nodes[0].style["layout_strategy"] == "ability_card_slots"
    assert graph.text_nodes[0].style["layout_source"] == "semantic_layout_plan"


def test_builder_attaches_semantic_layout_item_bbox_to_multiline_child_text():
    graph = build_page_scene_graph(
        page_number=6,
        script_sections={"右侧｜结果应用方": [{"title": "目录管理", "lines": ["指标/能力目录", "评估维度管理"]}]},
        semantic_plan={
            "image_size": {"width": 1280, "height": 720},
            "containers": [{"id": "application_1", "role": "ability_card", "bbox": [300, 100, 520, 260]}],
            "items": [],
        },
        visual_registry={"blueprint_canvas_px": {"w": 1280, "h": 720}, "elements": []},
        image_size={"width": 1280, "height": 720},
        semantic_layout_plan={
            "items": [
                {
                    "text": "目录管理",
                    "container_id": "application_1",
                    "bbox": [380.0, 121.0, 450.0, 140.0],
                    "layout_strategy": "ability_card_slots",
                }
            ],
        },
    )

    assert graph.text_nodes[0].text.startswith("目录管理")
    assert graph.text_nodes[0].style["layout_bbox"] == [380.0, 121.0, 450.0, 140.0]
