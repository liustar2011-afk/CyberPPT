from pathlib import Path

from PIL import Image

from scripts.dual_image_overlay.scene_graph.illustration_assets import (
    materialize_recognized_illustration_assets,
)
from scripts.dual_image_overlay.scene_graph.layout_reference_adapter import adapt_layout_reference
from scripts.dual_image_overlay.scene_graph.schema import PageSceneGraph


def test_materializes_recognized_semantic_image_as_movable_asset(tmp_path: Path):
    background = tmp_path / "background.png"
    Image.new("RGB", (200, 100), "#336699").save(background)
    context = {
        "image_size": {"width": 200, "height": 100},
        "coordinate_space": {"width": 200, "height": 100},
        "normalized_canvas": {"width": 200, "height": 100},
    }
    adapted = adapt_layout_reference(
        {
            "zones": [
                {
                    "id": "illustration_01",
                    "role": "semantic_image",
                    "bbox_px": [50, 20, 100, 60],
                }
            ]
        },
        coordinate_context=context,
    )
    graph = PageSceneGraph(
        page=16,
        coordinate_context=context,
        truth_sources={},
        visual_nodes=adapted["visual_nodes"],
    )

    updated, manifest = materialize_recognized_illustration_assets(
        graph,
        background_image=background,
        output_dir=tmp_path / "assets",
    )

    node = updated.visual_nodes[0]
    assert node.node_type == "image"
    assert node.attributes["preserve_internal_text"] is True
    assert node.attributes["movable"] is True
    assert node.attributes["fit_mode"] == "contain"
    assert Path(node.attributes["source_ref"]).is_file()
    with Image.open(node.attributes["source_ref"]) as crop:
        assert crop.size == (100, 60)
    assert manifest["count"] == 1
