import pytest

from scripts.dual_image_overlay.scene_graph.coordinate import normalize_bbox, resolve_coordinate_context
from scripts.dual_image_overlay.scene_graph.schema import BBox


def test_uses_semantic_width_when_right_side_extends_past_image_width():
    context = resolve_coordinate_context(
        plan_size={"width": 1920, "height": 941},
        image_size={"width": 1672, "height": 941},
        registry_size={"width": 1672, "height": 941},
        semantic_extent={"width": 1847, "height": 857},
        registry_extent={"width": 1920, "height": 915},
    )

    normalized = normalize_bbox(BBox(1742, 160, 1842, 221), context["semantic_input_space"], context)

    assert context["coordinate_space"] == {"width": 1672.0, "height": 941.0}
    assert context["semantic_input_space"] == {"width": 1920.0, "height": 941.0}
    assert context["visual_registry_input_space"] == {"width": 1920.0, "height": 941.0}
    assert normalized.as_list() == [1516.992, 160.0, 1604.075, 221.0]
    assert any(warning["code"] == "semantic_coordinate_space_uses_plan_extent" for warning in context["warnings"])


def test_uses_actual_image_size_when_extents_do_not_exceed_image_width():
    context = resolve_coordinate_context(
        plan_size={"width": 1920, "height": 941},
        image_size={"width": 1672, "height": 941},
        registry_size={"width": 1672, "height": 941},
        semantic_extent={"width": 822, "height": 257},
        registry_extent={"width": 730, "height": 235},
    )

    normalized = normalize_bbox(BBox(647, 152, 818, 253), context["semantic_input_space"], context)

    assert context["semantic_input_space"] == {"width": 1672.0, "height": 941.0}
    assert normalized.as_list() == [647.0, 152.0, 818.0, 253.0]


def test_registry_extent_can_pull_semantic_space_to_plan_canvas():
    context = resolve_coordinate_context(
        plan_size={"width": 1920, "height": 941},
        image_size={"width": 1672, "height": 941},
        registry_size={"width": 1672, "height": 941},
        semantic_extent={"width": 822, "height": 257},
        registry_extent={"width": 1900, "height": 900},
    )

    assert context["semantic_input_space"] == {"width": 1920.0, "height": 941.0}
    assert context["visual_registry_input_space"] == {"width": 1920.0, "height": 941.0}
    assert [warning["code"] for warning in context["warnings"]] == [
        "visual_registry_canvas_metadata_stale",
        "semantic_coordinate_space_follows_registry_extent",
    ]


def test_normalize_bbox_rejects_missing_input_space():
    with pytest.raises(ValueError):
        normalize_bbox(BBox(0, 0, 10, 10), {}, {"coordinate_space": {"width": 1672, "height": 941}})
