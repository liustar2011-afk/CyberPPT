from scripts.map_text_coordinates import (
    AffineTransform,
    check_safe_area,
    map_lines,
)
from scripts.models import BBox, TextLine


def test_affine_translation_and_scale():
    transform = AffineTransform(a=1.01, b=0, c=3, d=0, e=0.99, f=-2)
    result = transform.apply_bbox(BBox(100, 200, 300, 40))
    assert result == BBox(104, 196, 303, 40)


def test_safe_area_requires_full_containment():
    assert check_safe_area(BBox(110, 110, 80, 20), BBox(100, 100, 100, 40)) is True
    assert check_safe_area(BBox(90, 110, 80, 20), BBox(100, 100, 100, 40)) is False


def test_map_lines_preserves_mapping_provenance_and_corrections():
    line = TextLine(
        line_id="line-1",
        group_id="group-1",
        line_index=0,
        text="Mapped",
        bbox=BBox(10, 20, 30, 10),
        polygon=((10, 20), (40, 20), (40, 30), (10, 30)),
        confidence=0.98,
    )
    transform = AffineTransform(c=5, f=-2, transform_id="approved-global")
    containers = [
        {
            "container_id": "body",
            "safe_bbox": BBox(0, 0, 100, 100),
            "corrections": {"font_scale": 0.98},
        }
    ]

    result = map_lines([line], transform, containers)

    assert result[0].line is line
    assert result[0].source_bbox == BBox(10, 20, 30, 10)
    assert result[0].mapped_bbox == BBox(15, 18, 30, 10)
    assert result[0].transform_id == "approved-global"
    assert result[0].container_id == "body"
    assert result[0].within_safe_area is True
    assert result[0].corrections == {"font_scale": 0.98}


def test_map_lines_does_not_select_a_container_for_partial_overlap():
    line = TextLine(
        line_id="line-1",
        group_id="group-1",
        line_index=0,
        text="Overflow",
        bbox=BBox(90, 10, 20, 10),
        polygon=((90, 10), (110, 10), (110, 20), (90, 20)),
        confidence=0.98,
    )

    result = map_lines(
        [line],
        AffineTransform(transform_id="approved-global"),
        [{"container_id": "body", "safe_bbox": BBox(0, 0, 100, 100)}],
    )

    assert result[0].container_id is None
    assert result[0].within_safe_area is False
    assert result[0].corrections == {}


def test_line_correction_changes_source_bbox_before_global_mapping():
    line = TextLine(
        line_id="line-1", group_id="group-1", line_index=0, text="Corrected",
        bbox=BBox(10, 20, 30, 10),
        polygon=((10, 20), (40, 20), (40, 30), (10, 30)), confidence=0.99,
    )
    correction = {
        "dx": 2, "dy": -3, "width_delta": 4, "height_delta": 5,
        "font_scale": 0.98, "reason": "visual alignment", "source": "manual",
    }

    mapped = map_lines(
        [line], AffineTransform(a=2, e=2, transform_id="approved"),
        [{"container_id": "canvas", "safe_bbox": BBox(0, 0, 200, 200)}],
        {"line-1": correction},
    )[0]

    assert mapped.source_bbox == BBox(10, 20, 30, 10)
    assert mapped.corrected_bbox == BBox(12, 17, 34, 15)
    assert mapped.mapped_bbox == BBox(24, 34, 68, 30)
    assert mapped.manual_correction == correction
