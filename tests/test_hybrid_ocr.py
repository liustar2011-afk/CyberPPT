from scripts.dual_image_overlay.rebuild_engine.hybrid_ocr import merge_hybrid_ocr


def _payload(*lines):
    return {"canonical": {"lines": list(lines)}}


def _line(text, bbox, score=0.99):
    return {"text": text, "bbox": bbox, "score": score}


def test_merge_uses_paddle_text_with_vision_geometry_one_to_one():
    paddle = _payload(_line("亿千瓦时", [10, 10, 100, 30]))
    vision = _payload(_line("亿千面时", [12, 12, 94, 24], 0.3))

    result = merge_hybrid_ocr(paddle, vision, (200, 100))

    merged = result["canonical"]["lines"]
    assert merged[0]["text"] == "亿千瓦时"
    assert merged[0]["bbox"] == [12, 12, 94, 24]
    assert merged[0]["hybrid_evidence"]["match_type"] == "one_to_one"
    assert result["canonical"]["metadata"]["backend"] == "paddle-text+vision-geometry"


def test_merge_splits_paddle_line_when_vision_supports_exact_substrings():
    paddle = _payload(_line("同比增长 5.0%", [10, 10, 180, 40]))
    vision = _payload(
        _line("同比增长", [10, 16, 90, 24]),
        _line("5.0%", [112, 8, 70, 36]),
    )

    result = merge_hybrid_ocr(paddle, vision, (240, 100))

    merged = result["canonical"]["lines"]
    assert [line["text"] for line in merged] == ["同比增长", "5.0%"]
    assert [line["bbox"] for line in merged] == [[10, 16, 90, 24], [112, 8, 70, 36]]
    assert {line["hybrid_evidence"]["match_type"] for line in merged} == {"one_to_many"}


def test_merge_keeps_paddle_line_and_marks_review_when_split_is_ambiguous():
    paddle = _payload(_line("23.4亿千瓦", [10, 10, 180, 40]))
    vision = _payload(
        _line("23.4公", [10, 10, 90, 35], 0.3),
        _line("干瓦", [105, 12, 70, 30], 0.3),
    )

    result = merge_hybrid_ocr(paddle, vision, (240, 100))

    merged = result["canonical"]["lines"]
    assert [line["text"] for line in merged] == ["23.4亿千瓦"]
    assert merged[0]["bbox"] == [10, 10, 180, 40]
    assert merged[0]["hybrid_evidence"]["requires_review"] is True
    assert result["canonical"]["review_items"][0]["rule"] == "hybrid_ocr_ambiguous_split"


def test_merge_preserves_unmatched_paddle_text_and_clips_bad_vision_box():
    paddle = _payload(_line("保留文字", [5, 5, 80, 20]))
    vision = _payload(_line("无关", [-20, -10, 500, 300]))

    result = merge_hybrid_ocr(paddle, vision, (200, 100))

    assert [line["text"] for line in result["canonical"]["lines"]] == ["保留文字"]
    assert result["canonical"]["lines"][0]["bbox"] == [5, 5, 80, 20]
    assert result["canonical"]["lines"][0]["hybrid_evidence"]["requires_review"] is True
