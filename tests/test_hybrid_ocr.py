import subprocess

import pytest

from scripts.dual_image_overlay.rebuild_engine.hybrid_ocr import merge_hybrid_ocr, run_vision_ocr


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
    paddle_line = _line("同比增长 5.0%", [10, 10, 180, 40])
    paddle_line["runs"] = [{"text": "同比增长 5.0%", "font_size": 30, "bold": True}]
    paddle = _payload(paddle_line)
    vision = _payload(
        _line("同比增长", [10, 16, 90, 24]),
        _line("5.0%", [112, 8, 70, 36]),
    )

    result = merge_hybrid_ocr(paddle, vision, (240, 100))

    merged = result["canonical"]["lines"]
    assert [line["text"] for line in merged] == ["同比增长", "5.0%"]
    assert [line["bbox"] for line in merged] == [[10, 16, 90, 24], [112, 8, 70, 36]]
    assert [[run["text"] for run in line["runs"]] for line in merged] == [["同比增长"], ["5.0%"]]
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


def test_vision_adapter_parses_canonical_json(tmp_path, monkeypatch):
    image = tmp_path / "text.png"
    image.write_bytes(b"png")
    script = tmp_path / "vision.swift"
    script.write_text("// fixture", encoding="utf-8")

    def fake_run(command, **kwargs):
        assert command == ["swift", str(script), str(image.resolve())]
        assert kwargs["timeout"] == 180
        return subprocess.CompletedProcess(command, 0, '{"canonical":{"lines":[]}}', "")

    monkeypatch.setattr("scripts.dual_image_overlay.rebuild_engine.hybrid_ocr.subprocess.run", fake_run)
    assert run_vision_ocr(image, script_path=script) == {"canonical": {"lines": []}}


def test_vision_adapter_rejects_invalid_output(tmp_path, monkeypatch):
    image = tmp_path / "text.png"
    image.write_bytes(b"png")
    script = tmp_path / "vision.swift"
    script.write_text("// fixture", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.dual_image_overlay.rebuild_engine.hybrid_ocr.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 1, "", "Vision failed"),
    )

    with pytest.raises(RuntimeError, match="Vision failed"):
        run_vision_ocr(image, script_path=script)
