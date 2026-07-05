from __future__ import annotations

from scripts.dual_image_overlay.semantic_typography_qa import apply_semantic_typography_qa


def test_semantic_typography_qa_unifies_parallel_title_and_body_weights() -> None:
    boxes = [
        {
            "text": "目录管理",
            "bbox": [280, 70, 350, 88],
            "semantic_role": "ability_title",
            "bold": True,
        },
        {
            "text": "身份认证",
            "bbox": [480, 70, 550, 88],
            "semantic_role": "ability_title",
            "bold": False,
        },
        {
            "text": "指标/能力目录",
            "bbox": [350, 105, 440, 116],
            "semantic_role": "body",
            "bold": False,
        },
        {
            "text": "主体身份管理",
            "bbox": [550, 105, 640, 116],
            "semantic_role": "body",
            "bold": True,
        },
    ]

    corrected, report = apply_semantic_typography_qa(boxes)

    by_text = {box["text"]: box for box in corrected}
    assert by_text["目录管理"]["bold"] is True
    assert by_text["身份认证"]["bold"] is True
    assert by_text["指标/能力目录"]["bold"] is False
    assert by_text["主体身份管理"]["bold"] is False
    assert report["valid"] is True
    assert report["correction_count"] == 2
    assert {item["text"] for item in report["corrections"]} == {"身份认证", "主体身份管理"}


def test_semantic_typography_qa_infers_ocr_roles_without_using_initial_bold_as_truth() -> None:
    boxes = [
        {"text": "1", "bbox": [297, 76, 304, 88], "bold": False},
        {"text": "2", "bbox": [496, 76, 503, 88], "bold": False},
        {"text": "目录管理", "bbox": [338, 76, 410, 91], "bold": False},
        {"text": "身份认证", "bbox": [537, 76, 609, 91], "bold": False},
        {"text": "指标/能力目录", "bbox": [348, 104, 430, 115], "bold": True},
        {"text": "主体身份管理", "bbox": [547, 104, 629, 115], "bold": True},
    ]

    corrected, report = apply_semantic_typography_qa(boxes)

    by_text = {box["text"]: box for box in corrected}
    assert by_text["1"]["bold"] is True
    assert by_text["2"]["bold"] is True
    assert by_text["目录管理"]["bold"] is True
    assert by_text["身份认证"]["bold"] is True
    assert by_text["指标/能力目录"]["bold"] is False
    assert by_text["主体身份管理"]["bold"] is False
    assert report["checks"]["ocr_initial_bold_not_used_as_truth"] is True
