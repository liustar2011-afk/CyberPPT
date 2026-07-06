from __future__ import annotations

from copy import deepcopy
import math

from scripts.dual_image_overlay.text_block_group import build_text_block_group


def test_text_block_group_preserves_relative_line_offsets_under_scale() -> None:
    group = build_text_block_group(
        {
            "id": "stage_6_flow",
            "final_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
            "bbox": [630.0, 464.0, 709.0, 506.0],
            "line_boxes": [
                [630.0, 464.0, 708.0, 475.0],
                [643.0, 480.0, 704.0, 491.0],
                [646.0, 496.0, 708.0, 506.0],
            ],
            "style": {"font_size": 8.5, "font_weight": "700", "line_height": 1.36},
        },
        fit={"scale": 0.8, "fitted_style": {"font_size": 6.8, "line_height": 1.36}},
    )

    assert group["group_id"] == "group_stage_6_flow"
    assert group["text_block_id"] == "stage_6_flow"
    assert group["edit_behavior"] == "move_and_scale_as_group"
    assert group["scale"] == 0.8
    assert group["transform"]["scale_x"] == 0.8
    assert group["transform"]["scale_y"] == 0.8
    assert group["members"][0]["relative_bbox"] == [0.0, 0.0, 78.0, 11.0]
    assert group["members"][1]["relative_bbox"] == [13.0, 16.0, 74.0, 27.0]
    assert group["members"][2]["relative_bbox"] == [16.0, 32.0, 78.0, 42.0]
    assert group["members"][0]["style"]["font_size"] == 6.8
    assert [member["text"] for member in group["members"]] == ["融资申请→风控审核", "→放款→还款", "全流程线上化"]
    assert group["metadata"]["review_required"] is False


def test_text_block_group_missing_line_boxes_falls_back_with_review_metadata() -> None:
    group = build_text_block_group(
        {
            "id": "missing_boxes",
            "final_text": "第一行\n第二行",
            "bbox": [10.0, 20.0, 90.0, 60.0],
            "style": {"font_size": 12.0},
        }
    )

    assert group["members"][0]["relative_bbox"] == [0.0, 0.0, 80.0, 20.0]
    assert group["members"][1]["relative_bbox"] == [0.0, 20.0, 80.0, 40.0]
    assert group["metadata"]["review_required"] is True
    assert "missing_line_boxes" in group["metadata"]["review_reasons"]
    assert all(member["metadata"]["line_box_source"] == "fallback" for member in group["members"])


def test_text_block_group_mismatched_line_boxes_falls_back_without_crashing() -> None:
    group = build_text_block_group(
        {
            "id": "mismatch",
            "final_text": "第一行\n第二行\n第三行",
            "bbox": [0.0, 0.0, 90.0, 45.0],
            "line_boxes": [[0.0, 0.0, 80.0, 12.0]],
            "style": {"font_size": 10.0},
        }
    )

    assert [member["text"] for member in group["members"]] == ["第一行", "第二行", "第三行"]
    assert len(group["members"]) == 3
    assert group["members"][1]["relative_bbox"] == [0.0, 15.0, 90.0, 30.0]
    assert group["metadata"]["review_required"] is True
    assert "line_box_count_mismatch" in group["metadata"]["review_reasons"]


def test_text_block_group_does_not_mutate_input() -> None:
    text_block = {
        "id": "immutable",
        "final_text": "A\nB",
        "bbox": [1.0, 2.0, 11.0, 22.0],
        "line_boxes": [[1.0, 2.0, 10.0, 8.0], [1.0, 10.0, 10.0, 18.0]],
        "style": {"font_size": 14.0, "fill": "#333333"},
    }
    fit = {"scale": 0.75, "fitted_style": {"font_size": 10.5, "fill": "#333333"}}
    original_text_block = deepcopy(text_block)
    original_fit = deepcopy(fit)

    build_text_block_group(text_block, fit=fit)

    assert text_block == original_text_block
    assert fit == original_fit


def test_text_block_group_uses_uniform_style_and_scale_for_all_members() -> None:
    group = build_text_block_group(
        {
            "id": "uniform",
            "final_text": "One\nTwo",
            "bbox": [100.0, 100.0, 200.0, 140.0],
            "line_boxes": [[100.0, 100.0, 180.0, 116.0], [110.0, 122.0, 190.0, 138.0]],
            "style": {"font_size": 20.0, "font_weight": "700"},
        },
        fit={
            "scale": 0.625,
            "fitted_style": {"font_size": 12.5, "font_weight": "700", "line_height": 1.2},
        },
    )

    assert {member["scale"] for member in group["members"]} == {0.625}
    assert [member["style"] for member in group["members"]] == [
        {"font_size": 12.5, "font_weight": "700", "line_height": 1.2},
        {"font_size": 12.5, "font_weight": "700", "line_height": 1.2},
    ]
    assert group["members"][0]["relative_bbox"] == [0.0, 0.0, 80.0, 16.0]
    assert group["members"][1]["relative_bbox"] == [10.0, 22.0, 90.0, 38.0]


def test_text_block_group_invalid_root_bbox_fails_closed_and_ignores_supplied_line_boxes() -> None:
    group = build_text_block_group(
        {
            "id": "invalid_root",
            "final_text": "第一行\n第二行",
            "bbox": None,
            "line_boxes": [[100.0, 100.0, 180.0, 116.0], [110.0, 122.0, 190.0, 138.0]],
            "style": {"font_size": 12.0},
        }
    )

    assert group["bbox"] == [0.0, 0.0, 0.0, 0.0]
    assert group["metadata"]["status"] == "invalid_geometry"
    assert group["metadata"]["review_required"] is True
    assert "invalid_or_missing_root_bbox" in group["metadata"]["review_reasons"]
    assert all(member["bbox"] == [0.0, 0.0, 0.0, 0.0] for member in group["members"])
    assert all(member["relative_bbox"] == [0.0, 0.0, 0.0, 0.0] for member in group["members"])
    assert all(member["metadata"]["line_box_source"] == "invalid_root_bbox_fallback" for member in group["members"])


def test_text_block_group_non_finite_root_bbox_fails_closed() -> None:
    group = build_text_block_group(
        {
            "id": "non_finite_root",
            "final_text": "Only line",
            "bbox": [0.0, 0.0, math.nan, 20.0],
            "line_boxes": [[0.0, 0.0, 100.0, 20.0]],
        }
    )

    assert group["bbox"] == [0.0, 0.0, 0.0, 0.0]
    assert group["metadata"]["status"] == "invalid_geometry"
    assert group["members"][0]["relative_bbox"] == [0.0, 0.0, 0.0, 0.0]
    assert group["members"][0]["metadata"]["line_box_source"] == "invalid_root_bbox_fallback"


def test_text_block_group_reversed_root_bbox_fails_closed() -> None:
    group = build_text_block_group(
        {
            "id": "reversed_root",
            "final_text": "Only line",
            "bbox": [200.0, 200.0, 100.0, 100.0],
            "line_boxes": [[100.0, 100.0, 200.0, 120.0]],
        }
    )

    assert group["bbox"] == [0.0, 0.0, 0.0, 0.0]
    assert group["metadata"]["status"] == "invalid_geometry"
    assert group["metadata"]["review_required"] is True
    assert "invalid_or_missing_root_bbox" in group["metadata"]["review_reasons"]
    assert group["members"][0]["relative_bbox"] == [0.0, 0.0, 0.0, 0.0]
    assert group["members"][0]["metadata"]["line_box_source"] == "invalid_root_bbox_fallback"


def test_text_block_group_count_matched_invalid_line_geometry_falls_back_for_bad_member() -> None:
    group = build_text_block_group(
        {
            "id": "bad_line_geometry",
            "final_text": "First\nSecond",
            "bbox": [10.0, 20.0, 110.0, 60.0],
            "line_boxes": [[10.0, 20.0, 90.0, 36.0], [10.0, 40.0, math.inf, 56.0]],
        }
    )

    assert group["metadata"]["status"] == "ok"
    assert group["metadata"]["review_required"] is True
    assert "invalid_line_box_geometry" in group["metadata"]["review_reasons"]
    assert group["members"][0]["metadata"]["line_box_source"] == "text_block.line_boxes"
    assert group["members"][0]["relative_bbox"] == [0.0, 0.0, 80.0, 16.0]
    assert group["members"][1]["metadata"]["line_box_source"] == "fallback"
    assert group["members"][1]["relative_bbox"] == [0.0, 20.0, 100.0, 40.0]


def test_text_block_group_reversed_count_matched_line_bbox_falls_back_for_bad_member() -> None:
    group = build_text_block_group(
        {
            "id": "reversed_line_geometry",
            "final_text": "First\nSecond",
            "bbox": [10.0, 20.0, 110.0, 60.0],
            "line_boxes": [[10.0, 20.0, 90.0, 36.0], [90.0, 56.0, 10.0, 40.0]],
        }
    )

    assert group["metadata"]["status"] == "ok"
    assert group["metadata"]["review_required"] is True
    assert "invalid_line_box_geometry" in group["metadata"]["review_reasons"]
    assert group["members"][0]["metadata"]["line_box_source"] == "text_block.line_boxes"
    assert group["members"][1]["metadata"]["line_box_source"] == "fallback"
    assert group["members"][1]["relative_bbox"] == [0.0, 20.0, 100.0, 40.0]


def test_text_block_group_deep_copies_nested_styles_for_input_and_members() -> None:
    fit = {
        "scale": 0.5,
        "fitted_style": {
            "font_size": 6.0,
            "effects": {"shadow": {"blur": 4.0}},
        },
    }
    group = build_text_block_group(
        {
            "id": "nested_style",
            "final_text": "One\nTwo",
            "bbox": [0.0, 0.0, 100.0, 40.0],
            "line_boxes": [[0.0, 0.0, 80.0, 16.0], [0.0, 20.0, 80.0, 36.0]],
            "style": {"font_size": 12.0},
        },
        fit=fit,
    )

    group["members"][0]["style"]["effects"]["shadow"]["blur"] = 99.0

    assert fit["fitted_style"]["effects"]["shadow"]["blur"] == 4.0
    assert group["members"][1]["style"]["effects"]["shadow"]["blur"] == 4.0
