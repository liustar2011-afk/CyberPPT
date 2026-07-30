from scripts.dual_image_overlay.scene_graph.image_assets import asset_id_for_source, image_asset_manifest, register_image_asset, validate_image_asset_contract


def test_same_source_reuses_one_asset_id_and_tracks_crop_variants():
    registry = {}
    first = register_image_asset(registry, source="images/scene.png", role="icon", crop={"x": 0, "y": 0, "width": 20, "height": 20})
    second = register_image_asset(registry, source="images/scene.png", role="illustration", crop={"x": 10, "y": 10, "width": 20, "height": 20})
    assert first == second == asset_id_for_source("images/scene.png")
    assert registry[first]["uses"] == 2
    assert len(registry[first]["crop_variants"]) == 2
    assert image_asset_manifest(registry)["gate"]["valid"] is True


def test_background_asset_cannot_be_text_bearing():
    registry = {}
    register_image_asset(registry, source="images/background.png", role="complex_visual_background", text_bearing=True)
    gate = validate_image_asset_contract(registry)
    assert gate["valid"] is False
    assert gate["issues"][0]["code"] == "background_text_bearing_forbidden"

