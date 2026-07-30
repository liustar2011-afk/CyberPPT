from scripts.dual_image_overlay.scene_graph.builder import build_page_scene_graph
from scripts.dual_image_overlay.scene_graph.layout_reference_adapter import adapt_layout_reference


def _context():
    return {
        "image_size": {"width": 1600, "height": 900},
        "coordinate_space": {"width": 1672, "height": 941},
    }


def test_layout_reference_adapter_converts_xywh_zones_and_contract_relations():
    adapted = adapt_layout_reference(
        {
            "version": "2.0",
            "layout_grammar": {"page_type_hint": "custom"},
            "zones": [
                {"id": "title_zone", "role": "title", "bbox_px": [100, 50, 600, 80]},
                {"id": "visual_zone", "role": "semantic_image", "bbox_px": [800, 200, 600, 500]},
            ],
            "structure_contract": {
                "relations": [
                    {"type": "supports", "source_id": "title_zone", "target_id": "visual_zone"}
                ]
            },
            "geometry_locks": [{"id": "visual_zone", "axis": "center"}],
        },
        coordinate_context=_context(),
    )

    assert adapted["metadata"]["consumed"] is True
    assert adapted["metadata"]["layout_grammar"]["page_type_hint"] == "custom"
    assert adapted["metadata"]["geometry_locks"][0]["id"] == "visual_zone"
    assert [node.node_id for node in adapted["visual_nodes"]] == ["title_zone", "visual_zone"]
    assert adapted["visual_nodes"][0].bbox.as_list() == [104.5, 52.278, 731.5, 135.922]
    assert adapted["relations"][0].type == "supports"


def test_builder_adds_recognized_layout_without_replacing_existing_nodes():
    graph = build_page_scene_graph(
        page_number=16,
        script_sections={},
        semantic_plan={"containers": [], "image_size": {"width": 1600, "height": 900}},
        visual_registry={"elements": [], "blueprint_canvas_px": {"width": 1600, "height": 900}},
        image_size={"width": 1600, "height": 900},
        layout_reference={
            "version": "2.0",
            "zones": [{"id": "recognized_visual", "role": "semantic_image", "bbox_px": [800, 200, 600, 500]}],
        },
    )

    assert graph.visual_nodes[0].node_id == "recognized_visual"
    assert graph.visual_nodes[0].source["kind"] == "layout_reference"
    assert graph.metadata["layout_reference"]["consumed"] is True
