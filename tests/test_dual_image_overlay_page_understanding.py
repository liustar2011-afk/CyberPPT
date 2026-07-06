from __future__ import annotations

import math

import pytest

from scripts.dual_image_overlay.page_understanding import (
    build_implicit_text_containers,
    build_page_understanding,
    write_page_understanding,
)


def test_page_understanding_builds_business_truth_contract() -> None:
    payload = build_page_understanding(
        page_number=13,
        full_image=None,
        background_image=None,
        registration={"valid": True, "transform": "identity"},
        text_blocks=[
            {
                "id": "text_block_001",
                "ocr_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
                "final_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
                "bbox": [630.0, 464.0, 709.0, 506.0],
                "line_boxes": [
                    [630.0, 464.0, 708.0, 475.0],
                    [643.0, 480.0, 704.0, 491.0],
                    [646.0, 496.0, 708.0, 506.0],
                ],
                "style": {"font_size": 8.5, "font_weight": "700", "fill": "#0B1F3D", "align": "left"},
                "truth": {"status": "script_verified", "similarity": 1.0},
            }
        ],
        explicit_containers=[
            {"id": "stage_6_card", "bbox": [624.0, 420.0, 714.0, 530.0], "source": "background_image"}
        ],
        implicit_containers=[],
        visual_elements=[],
        canvas={"width": 1280.0, "height": 720.0},
    )

    assert payload["schema"] == "cyberppt.dual_image.page_understanding.v1"
    assert payload["valid"] is True
    assert payload["registration"]["valid"] is True
    assert payload["text_blocks"][0]["truth"]["status"] == "script_verified"
    assert payload["containers"][0]["kind"] == "explicit_container"
    assert payload["container_text_bindings"][0]["text_block_id"] == "text_block_001"
    assert payload["container_text_bindings"][0]["container_id"] == "stage_6_card"
    assert payload["review_items"] == []


def test_page_understanding_rejects_non_finite_bboxes() -> None:
    payload = build_page_understanding(
        page_number=13,
        full_image=None,
        background_image=None,
        registration={"valid": True},
        text_blocks=[
            {"id": "bad_text", "final_text": "bad", "bbox": [0.0, 0.0, math.nan, 20.0]},
            {"id": "good_text", "final_text": "good", "bbox": [10.0, 10.0, 20.0, 20.0]},
        ],
        explicit_containers=[
            {"id": "bad_container", "bbox": [0.0, 0.0, math.inf, 40.0]},
        ],
        implicit_containers=[],
        visual_elements=[],
        canvas={"width": 1280.0, "height": 720.0},
    )

    assert [block["id"] for block in payload["text_blocks"]] == ["good_text"]
    assert payload["containers"] == []
    assert payload["review_items"] == [
        {
            "type": "unbound_text_block",
            "text_block_id": "good_text",
            "text": "good",
            "severity": "warning",
        }
    ]


def test_page_understanding_rejects_missing_and_partial_geometry_dicts() -> None:
    payload = build_page_understanding(
        page_number=1,
        full_image=None,
        background_image=None,
        registration={"valid": True},
        text_blocks=[
            {"id": "missing_geometry", "final_text": "missing"},
            {"id": "partial_geometry", "final_text": "partial", "x": 1.0, "y": 2.0, "width": 10.0},
            {"id": "good_geometry", "final_text": "good", "x": 10.0, "y": 20.0, "width": 30.0, "height": 12.0},
        ],
        explicit_containers=[
            {"id": "missing_container_geometry"},
            {"id": "partial_container_geometry", "x": 0.0, "y": 0.0, "w": 10.0},
            {"id": "good_container_geometry", "x": 8.0, "y": 18.0, "w": 36.0, "h": 18.0},
        ],
        implicit_containers=[],
        visual_elements=[],
        canvas={"width": 1280.0, "height": 720.0},
    )

    assert [block["id"] for block in payload["text_blocks"]] == ["good_geometry"]
    assert [container["id"] for container in payload["containers"]] == ["good_container_geometry"]
    assert payload["text_blocks"][0]["bbox"] == [10.0, 20.0, 40.0, 32.0]
    assert payload["containers"][0]["bbox"] == [8.0, 18.0, 44.0, 36.0]


def test_page_understanding_rejects_zero_area_and_reversed_bboxes() -> None:
    payload = build_page_understanding(
        page_number=1,
        full_image=None,
        background_image=None,
        registration={"valid": True},
        text_blocks=[
            {"id": "zero_width", "final_text": "zero", "bbox": [10.0, 10.0, 10.0, 20.0]},
            {"id": "zero_height", "final_text": "zero", "bbox": [10.0, 10.0, 20.0, 10.0]},
            {"id": "reversed", "final_text": "reversed", "bbox": [20.0, 20.0, 10.0, 30.0]},
            {"id": "negative_size_dict", "final_text": "negative", "x": 0.0, "y": 0.0, "w": -1.0, "h": 10.0},
            {"id": "valid", "final_text": "valid", "bbox": [1.0, 2.0, 3.0, 4.0]},
        ],
        explicit_containers=[
            {"id": "zero_area_container", "bbox": [0.0, 0.0, 0.0, 10.0]},
        ],
        implicit_containers=[],
        visual_elements=[],
        canvas={"width": 1280.0, "height": 720.0},
    )

    assert [block["id"] for block in payload["text_blocks"]] == ["valid"]
    assert payload["containers"] == []


def test_page_understanding_preserves_zero_confidence() -> None:
    payload = build_page_understanding(
        page_number=1,
        full_image=None,
        background_image=None,
        registration={"valid": True},
        text_blocks=[{"id": "text", "final_text": "text", "bbox": [1.0, 1.0, 2.0, 2.0]}],
        explicit_containers=[{"id": "container", "bbox": [0.0, 0.0, 3.0, 3.0], "confidence": 0.0}],
        implicit_containers=[],
        visual_elements=[],
        canvas={"width": 1280.0, "height": 720.0},
    )

    assert payload["containers"][0]["confidence"] == 0.0


def test_unbound_text_review_is_warning_without_invalidating_page() -> None:
    payload = build_page_understanding(
        page_number=1,
        full_image=None,
        background_image=None,
        registration={"valid": True},
        text_blocks=[{"id": "orphan", "final_text": "orphan text", "bbox": [10.0, 10.0, 30.0, 30.0]}],
        explicit_containers=[],
        implicit_containers=[],
        visual_elements=[],
        canvas={"width": 1280.0, "height": 720.0},
    )

    assert payload["valid"] is True
    assert payload["warning_count"] == 1
    assert payload["error_count"] == 0
    assert payload["review_items"][0]["type"] == "unbound_text_block"
    assert payload["review_items"][0]["severity"] == "warning"


def test_text_block_line_boxes_none_builds_as_empty_list() -> None:
    payload = build_page_understanding(
        page_number=1,
        full_image=None,
        background_image=None,
        registration={"valid": True},
        text_blocks=[
            {
                "id": "text_with_none_lines",
                "final_text": "text",
                "bbox": [10.0, 10.0, 20.0, 20.0],
                "line_boxes": None,
            }
        ],
        explicit_containers=[],
        implicit_containers=[],
        visual_elements=[],
        canvas={"width": 1280.0, "height": 720.0},
    )

    assert payload["text_blocks"][0]["line_boxes"] == []


def test_visual_element_without_supported_bbox_does_not_get_bogus_zero_bbox() -> None:
    payload = build_page_understanding(
        page_number=1,
        full_image=None,
        background_image=None,
        registration={"valid": True},
        text_blocks=[{"id": "text", "final_text": "text", "bbox": [10.0, 10.0, 20.0, 20.0]}],
        explicit_containers=[],
        implicit_containers=[],
        visual_elements=[
            {
                "id": "blueprint_only",
                "kind": "icon",
                "blueprint_bbox_px": [1.0, 2.0, 3.0, 4.0],
                "render_bbox_px": [5.0, 6.0, 7.0, 8.0],
            }
        ],
        canvas={"width": 1280.0, "height": 720.0},
    )

    visual = payload["visual_elements"][0]
    assert "bbox" not in visual
    assert visual["blueprint_bbox_px"] == [1.0, 2.0, 3.0, 4.0]
    assert visual["render_bbox_px"] == [5.0, 6.0, 7.0, 8.0]


def test_write_page_understanding_rejects_non_standard_json(tmp_path) -> None:
    with pytest.raises(ValueError):
        write_page_understanding(tmp_path / "page_understanding.json", {"bad": math.nan})


def test_builds_implicit_container_when_background_has_no_visible_box() -> None:
    implicit = build_implicit_text_containers(
        text_blocks=[
            {
                "id": "text_block_note",
                "final_text": "可信机制贯穿全程",
                "bbox": [120.0, 630.0, 310.0, 654.0],
                "line_boxes": [[120.0, 630.0, 310.0, 654.0]],
                "style": {"font_size": 14},
            }
        ],
        explicit_containers=[],
        visual_elements=[{"id": "shield_icon", "bbox": [60.0, 615.0, 105.0, 665.0], "kind": "icon"}],
    )

    assert len(implicit) == 1
    assert implicit[0]["id"] == "implicit_text_block_note"
    assert implicit[0]["kind"] == "implicit_text_container"
    assert implicit[0]["source"] == "full_image_text_block"
    assert implicit[0]["role"] == "text_safe_zone"
    assert implicit[0]["text_block_id"] == "text_block_note"
    assert implicit[0]["bbox"][0] >= 108.0
    assert implicit[0]["bbox"][1] <= 626.0
    assert implicit[0]["bbox"][2] >= 322.0
    assert implicit[0]["bbox"][3] >= 658.0


def test_does_not_build_implicit_container_when_explicit_container_covers_text() -> None:
    implicit = build_implicit_text_containers(
        text_blocks=[
            {
                "id": "covered_text",
                "final_text": "已有卡片承载",
                "bbox": [200.0, 200.0, 260.0, 224.0],
            }
        ],
        explicit_containers=[
            {
                "id": "visible_card",
                "bbox": [180.0, 180.0, 280.0, 250.0],
                "text_safe_bbox": [190.0, 190.0, 270.0, 240.0],
                "source": "background_image",
            }
        ],
        visual_elements=None,
    )

    assert implicit == []


def test_implicit_container_clamps_to_non_default_canvas() -> None:
    implicit = build_implicit_text_containers(
        text_blocks=[
            {
                "id": "edge_text",
                "final_text": "edge",
                "bbox": [94.0, 74.0, 99.0, 79.0],
            }
        ],
        explicit_containers=[],
        visual_elements=[],
        canvas={"width": 100.0, "height": 80.0},
    )

    assert implicit[0]["bbox"] == [82.0, 68.0, 100.0, 80.0]
    assert implicit[0]["text_safe_bbox"] == [82.0, 68.0, 100.0, 80.0]


def test_implicit_container_skips_text_outside_canvas_horizontally() -> None:
    implicit = build_implicit_text_containers(
        text_blocks=[
            {
                "id": "outside_right",
                "final_text": "outside",
                "bbox": [150.0, 50.0, 160.0, 60.0],
            }
        ],
        explicit_containers=[],
        visual_elements=[],
        canvas={"width": 100.0, "height": 80.0},
    )

    assert implicit == []


def test_implicit_container_skips_text_outside_canvas_vertically() -> None:
    implicit = build_implicit_text_containers(
        text_blocks=[
            {
                "id": "outside_bottom",
                "final_text": "outside",
                "bbox": [50.0, 150.0, 60.0, 160.0],
            }
        ],
        explicit_containers=[],
        visual_elements=[],
        canvas={"width": 100.0, "height": 80.0},
    )

    assert implicit == []


def test_implicit_container_skips_near_edge_text_fully_outside_canvas() -> None:
    for block_id, bbox in [
        ("outside_left", [-5.0, 10.0, -1.0, 20.0]),
        ("outside_right", [101.0, 10.0, 105.0, 20.0]),
        ("outside_top", [10.0, -5.0, 20.0, -1.0]),
        ("outside_bottom", [10.0, 81.0, 20.0, 85.0]),
    ]:
        implicit = build_implicit_text_containers(
            text_blocks=[
                {
                    "id": block_id,
                    "final_text": "outside",
                    "bbox": bbox,
                }
            ],
            explicit_containers=[],
            visual_elements=[],
            canvas={"width": 100.0, "height": 80.0},
        )

        assert implicit == []


def test_implicit_container_allows_partial_canvas_overlap() -> None:
    implicit = build_implicit_text_containers(
        text_blocks=[
            {
                "id": "partial_left",
                "final_text": "partial",
                "bbox": [-5.0, 10.0, 5.0, 20.0],
            }
        ],
        explicit_containers=[],
        visual_elements=[],
        canvas={"width": 100.0, "height": 80.0},
    )

    assert len(implicit) == 1
    assert implicit[0]["bbox"] == [0.0, 4.0, 17.0, 26.0]
    assert implicit[0]["text_safe_bbox"] == [0.0, 4.0, 17.0, 26.0]


def test_implicit_text_containers_ignore_malformed_inputs() -> None:
    assert (
        build_implicit_text_containers(
            text_blocks=[
                {"id": "bad", "final_text": "bad", "bbox": [0.0, 0.0, math.nan, 10.0]},
                {"id": "bbox_only", "bbox": [0.0, 0.0, 10.0, 10.0]},
                None,
            ],
            explicit_containers=None,
            visual_elements=[{"id": "bad_visual", "bbox": [0.0, math.inf, 1.0, 2.0]}],
        )
        == []
    )
