from __future__ import annotations

from copy import deepcopy

from scripts.dual_image_overlay.block_fit import fit_text_block_to_container


def test_fit_text_block_uses_uniform_scale_and_review_threshold() -> None:
    result = fit_text_block_to_container(
        {
            "id": "text_block_001",
            "final_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
            "bbox": [630.0, 464.0, 709.0, 506.0],
            "line_boxes": [
                [630.0, 464.0, 708.0, 475.0],
                [643.0, 480.0, 704.0, 491.0],
                [646.0, 496.0, 708.0, 506.0],
            ],
            "style": {"font_size": 8.5, "line_height": 1.36},
        },
        {"id": "stage_6_card", "text_safe_bbox": [626.0, 458.0, 714.0, 512.0]},
    )

    assert result["mode"] == "uniform_block_scale"
    assert result["scale"] <= 1.0
    assert result["status"] == "auto_pass"
    assert result["fitted_style"]["font_size"] <= 8.5
    assert result["review_required"] is False


def test_fit_text_block_reports_warning_threshold() -> None:
    result = fit_text_block_to_container(
        {
            "final_text": "ABCDEFGHIJ",
            "bbox": [0.0, 0.0, 100.0, 20.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 80.0, 30.0]},
    )

    assert result["scale"] == 0.8
    assert result["status"] == "warning"
    assert result["review_required"] is False
    assert result["fitted_style"]["font_size"] == 8.0


def test_fit_text_block_reports_scale_without_crossing_auto_pass_threshold() -> None:
    result = fit_text_block_to_container(
        {
            "final_text": "ABCDEFGHIJ",
            "bbox": [0.0, 0.0, 10000.0, 20.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 8496.0, 30.0]},
    )

    assert result["scale"] == 0.8496
    assert result["status"] == "warning"
    assert result["review_required"] is False


def test_fit_text_block_reports_review_threshold() -> None:
    result = fit_text_block_to_container(
        {
            "final_text": "ABCDEFGHIJ",
            "bbox": [0.0, 0.0, 100.0, 20.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 65.0, 30.0]},
    )

    assert result["scale"] == 0.65
    assert result["status"] == "review_recommended"
    assert result["review_required"] is True


def test_fit_text_block_reports_scale_without_crossing_warning_threshold() -> None:
    result = fit_text_block_to_container(
        {
            "final_text": "ABCDEFGHIJ",
            "bbox": [0.0, 0.0, 10000.0, 20.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 6996.0, 30.0]},
    )

    assert result["scale"] == 0.6996
    assert result["status"] == "review_recommended"
    assert result["review_required"] is True


def test_fit_text_block_blocks_below_minimum_threshold() -> None:
    result = fit_text_block_to_container(
        {
            "final_text": "ABCDEFGHIJ",
            "bbox": [0.0, 0.0, 100.0, 20.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 55.0, 30.0]},
    )

    assert result["scale"] == 0.55
    assert result["status"] == "blocked_too_small"
    assert result["review_required"] is True


def test_fit_text_block_reports_scale_without_crossing_review_threshold() -> None:
    result = fit_text_block_to_container(
        {
            "final_text": "ABCDEFGHIJ",
            "bbox": [0.0, 0.0, 10000.0, 20.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 5996.0, 30.0]},
    )

    assert result["scale"] == 0.5996
    assert result["status"] == "blocked_too_small"
    assert result["review_required"] is True


def test_fit_text_block_does_not_use_independent_per_line_scaling() -> None:
    text_block = {
        "final_text": "短\nABCDEFGHIJ",
        "bbox": [0.0, 0.0, 100.0, 30.0],
        "line_boxes": [
            [0.0, 0.0, 10.0, 10.0],
            [0.0, 15.0, 100.0, 25.0],
        ],
        "style": {"font_size": 10.0, "line_height": 1.5},
    }

    result = fit_text_block_to_container(text_block, {"text_safe_bbox": [0.0, 0.0, 80.0, 30.0]})

    assert result["scale"] == 0.8
    assert "line_scales" not in result
    assert result["fitted_style"]["block_scale"] == result["scale"]
    assert result["fitted_style"]["internal_offset_scale"] == result["scale"]
    assert text_block["final_text"] == "短\nABCDEFGHIJ"


def test_fit_text_block_uses_container_bbox_when_text_safe_bbox_is_absent() -> None:
    result = fit_text_block_to_container(
        {
            "final_text": "ABCDEFGHIJ",
            "bbox": [0.0, 0.0, 100.0, 20.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"bbox": [0.0, 0.0, 90.0, 30.0]},
    )

    assert result["scale"] == 0.9
    assert result["status"] == "auto_pass"


def test_fit_text_block_fails_closed_for_invalid_container_geometry() -> None:
    result = fit_text_block_to_container(
        {
            "final_text": "OK",
            "bbox": [0.0, 0.0, 20.0, 10.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 0.0, 10.0]},
    )

    assert result["mode"] == "uniform_block_scale"
    assert result["scale"] == 0.0
    assert result["status"] == "invalid_container"
    assert result["review_required"] is True


def test_fit_text_block_preserves_style_and_does_not_mutate_input() -> None:
    text_block = {
        "final_text": "ABCDEFGHIJ",
        "bbox": [0.0, 0.0, 100.0, 20.0],
        "style": {"font_size": 10.0, "line_height": 1.2, "color": "#333333"},
    }
    original = deepcopy(text_block)

    result = fit_text_block_to_container(text_block, {"text_safe_bbox": [0.0, 0.0, 80.0, 30.0]})

    assert text_block == original
    assert result["fitted_style"]["color"] == "#333333"
    assert text_block["style"] == original["style"]


def test_fit_text_block_estimates_chinese_wider_than_ascii() -> None:
    ascii_result = fit_text_block_to_container(
        {
            "final_text": "AA",
            "bbox": [0.0, 0.0, 1.0, 10.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 15.0, 30.0]},
    )
    chinese_result = fit_text_block_to_container(
        {
            "final_text": "中中",
            "bbox": [0.0, 0.0, 1.0, 10.0],
            "style": {"font_size": 10.0, "line_height": 1.2},
        },
        {"text_safe_bbox": [0.0, 0.0, 15.0, 30.0]},
    )

    assert ascii_result["scale"] == 1.0
    assert chinese_result["scale"] == 0.75


def test_fit_text_block_accounts_for_multiline_height() -> None:
    single_line = fit_text_block_to_container(
        {
            "final_text": "A",
            "bbox": [0.0, 0.0, 1.0, 1.0],
            "style": {"font_size": 10.0, "line_height": 1.5},
        },
        {"text_safe_bbox": [0.0, 0.0, 100.0, 20.0]},
    )
    multiline = fit_text_block_to_container(
        {
            "final_text": "A\nB\nC",
            "bbox": [0.0, 0.0, 1.0, 1.0],
            "style": {"font_size": 10.0, "line_height": 1.5},
        },
        {"text_safe_bbox": [0.0, 0.0, 100.0, 20.0]},
    )

    assert single_line["scale"] == 1.0
    assert multiline["scale"] == 0.5
