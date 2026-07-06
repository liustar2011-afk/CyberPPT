from __future__ import annotations

from scripts.dual_image_overlay.text_truth import verify_text_blocks_against_script


def test_text_truth_corrects_ocr_typo_using_script_truth() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "text_block_001",
                "ocr_text": "融资申请→风控审孩\n→放款→还款\n全流程线上化",
                "bbox": [630.0, 464.0, 709.0, 506.0],
                "line_boxes": [
                    [630.0, 464.0, 708.0, 475.0],
                    [643.0, 480.0, 704.0, 491.0],
                    [646.0, 496.0, 708.0, 506.0],
                ],
                "style": {"font_size": 8.5, "font_weight": "700"},
                "source": "full_image_ocr",
            }
        ],
        ["融资申请→风控审核→放款→还款，全流程线上化"],
    )

    assert result[0]["final_text"] == "融资申请→风控审核\n→放款→还款，\n全流程线上化"
    assert result[0]["truth"]["status"] == "script_verified"
    assert result[0]["truth"]["source"] == "script_truth"
    assert result[0]["truth"]["matched_text"] == "融资申请→风控审核→放款→还款，全流程线上化"
    assert result[0]["truth"]["similarity"] >= 0.8
    assert result[0]["bbox"] == [630.0, 464.0, 709.0, 506.0]
    assert result[0]["line_boxes"][1] == [643.0, 480.0, 704.0, 491.0]
    assert result[0]["style"] == {"font_size": 8.5, "font_weight": "700"}
    assert result[0]["source"] == "full_image_ocr"


def test_text_truth_marks_unmatched_block_for_review() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "text_block_002",
                "ocr_text": "资产证券化",
                "bbox": [10.0, 20.0, 90.0, 40.0],
                "line_boxes": [[10.0, 20.0, 90.0, 40.0]],
                "style": {"font_size": 12},
            }
        ],
        ["融资申请→风控审核→放款→还款，全流程线上化"],
        match_threshold=0.9,
    )

    assert result[0]["final_text"] == "资产证券化"
    assert result[0]["truth"]["status"] == "review_required"
    assert result[0]["truth"]["source"] == "ocr_candidate"
    assert result[0]["truth"]["reason"] == "script_truth_match_below_threshold"
    assert result[0]["line_boxes"] == [[10.0, 20.0, 90.0, 40.0]]


def test_text_truth_uses_script_truth_for_single_line_match() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "headline",
                "ocr_text": "全流程上化",
                "bbox": [100.0, 100.0, 220.0, 126.0],
                "line_boxes": [[100.0, 100.0, 220.0, 126.0]],
                "style": {"font_size": 18, "fill": "#0B1F3D"},
            }
        ],
        ["全流程线上化"],
    )

    assert result[0]["final_text"] == "全流程线上化"
    assert result[0]["truth"]["status"] == "script_verified"
    assert result[0]["truth"]["similarity"] >= 0.8
    assert result[0]["line_boxes"] == [[100.0, 100.0, 220.0, 126.0]]


def test_text_truth_preserves_script_punctuation_when_splitting_lines() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "flow",
                "ocr_text": "A授信\n→B放款",
                "bbox": [0.0, 0.0, 120.0, 40.0],
                "line_boxes": [[0.0, 0.0, 80.0, 18.0], [0.0, 22.0, 120.0, 40.0]],
                "style": {},
            }
        ],
        ["A：授信→B：放款"],
    )

    assert result[0]["final_text"] == "A：授信\n→B：放款"
    assert result[0]["truth"]["status"] == "script_verified"


def test_text_truth_preserves_existing_multiline_script_truth() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "existing_multiline",
                "ocr_text": "A\nB",
                "bbox": [0.0, 0.0, 40.0, 40.0],
                "line_boxes": [[0.0, 0.0, 20.0, 18.0], [0.0, 22.0, 20.0, 40.0]],
                "style": {},
            }
        ],
        ["A\nB"],
    )

    assert result[0]["final_text"] == "A\nB"
    assert result[0]["truth"]["status"] == "script_verified"


def test_text_truth_preserves_monetary_commas_and_parentheses_single_line() -> None:
    script_text = "金额1,000万元，政策（试点）推进"
    result = verify_text_blocks_against_script(
        [
            {
                "id": "money_policy",
                "ocr_text": "金额1000万元政策试点推进",
                "bbox": [0.0, 0.0, 180.0, 20.0],
                "line_boxes": [[0.0, 0.0, 180.0, 20.0]],
                "style": {},
            }
        ],
        [script_text],
    )

    assert result[0]["final_text"] == script_text
    assert result[0]["truth"]["status"] == "script_verified"


def test_text_truth_marks_close_script_matches_as_ambiguous() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "ambiguous",
                "ocr_text": "数据治理能力",
                "bbox": [0.0, 0.0, 80.0, 20.0],
                "line_boxes": [[0.0, 0.0, 80.0, 20.0]],
                "style": {},
            }
        ],
        ["数据治理能力建设", "数据治理能力提升"],
        match_threshold=0.6,
    )

    assert result[0]["final_text"] == "数据治理能力"
    assert result[0]["truth"]["status"] == "review_required"
    assert result[0]["truth"]["reason"] == "script_truth_match_ambiguous"


def test_text_truth_verifies_contained_script_substring() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "report_title",
                "ocr_text": "成果价值评估报告",
                "bbox": [0.0, 0.0, 120.0, 20.0],
                "line_boxes": [[0.0, 0.0, 120.0, 20.0]],
                "style": {},
            }
        ],
        ["场景二产出的成果价值评估报告"],
    )

    assert result[0]["final_text"] == "成果价值评估报告"
    assert result[0]["truth"]["status"] == "script_verified"
    assert result[0]["truth"]["matched_text"] == "场景二产出的成果价值评估报告"


def test_text_truth_corrects_substring_ocr_typo_from_script_span() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "report_title_typo",
                "ocr_text": "成果价値评估报告",
                "bbox": [0.0, 0.0, 120.0, 20.0],
                "line_boxes": [[0.0, 0.0, 120.0, 20.0]],
                "style": {},
            }
        ],
        ["场景二产出的成果价值评估报告"],
    )

    assert result[0]["final_text"] == "成果价值评估报告"
    assert result[0]["truth"]["status"] == "script_verified"
    assert result[0]["truth"]["similarity"] >= 0.82


def test_text_truth_keeps_repeated_single_digit_ambiguous() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "digit",
                "ocr_text": "1",
                "bbox": [0.0, 0.0, 12.0, 12.0],
                "line_boxes": [[0.0, 0.0, 12.0, 12.0]],
                "style": {},
            }
        ],
        ["1. 数据底座", "1. 评估报告"],
    )

    assert result[0]["final_text"] == "1"
    assert result[0]["truth"]["status"] == "review_required"
    assert result[0]["truth"]["reason"] == "script_truth_containment_ambiguous"


def test_text_truth_preserves_punctuation_inside_contained_script_span() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "punctuated_span",
                "ocr_text": "成果价值评估报告2026版",
                "bbox": [0.0, 0.0, 120.0, 20.0],
                "line_boxes": [[0.0, 0.0, 120.0, 20.0]],
                "style": {},
            }
        ],
        ["场景二产出的成果价值评估报告（2026）版正式发布"],
    )

    assert result[0]["final_text"] == "成果价值评估报告（2026）版"
    assert result[0]["truth"]["status"] == "script_verified"
