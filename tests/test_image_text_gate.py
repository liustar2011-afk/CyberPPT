from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from cyberppt.image_text_gate import audit_generated_image_text


def _image(tmp_path: Path) -> Path:
    path = tmp_path / "raw.png"
    Image.new("RGB", (100, 50), "white").save(path)
    return path


def _vision(issues=None):
    return lambda **_kwargs: json.dumps(
        {"observed_text": [], "issues": issues or [], "summary": "passed"}, ensure_ascii=False
    )


def test_text_gate_accepts_clean_text(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path), script_text="数据产品\n数据服务", vision_runner=_vision(),
        ocr_runner=lambda _path: [{"text": "数据产品", "confidence": .99, "bbox": []}],
    )
    assert result["valid"] is True


def test_text_gate_rejects_vision_typo(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path), script_text="数据产品",
        vision_runner=_vision([{"type": "typo", "expected": "数据产品", "observed": "数据产晶"}]),
        ocr_runner=lambda _path: [],
    )
    assert result["valid"] is False


def test_text_gate_ignores_findings_outside_scope(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path), script_text="数据产品",
        vision_runner=_vision([{"type": "missing"}, {"type": "unexpected_text"}, {"type": "unreadable"}]),
        ocr_runner=lambda _path: [],
    )
    assert result["valid"] is True


def test_independent_ocr_rejects_pseudo_chinese_resource_glyph(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path), script_text="资源与能力",
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "瓷源与能力", "confidence": .649, "bbox": [[1, 2], [3, 4]]}
        ],
    )
    assert result["valid"] is False
    assert result["issues"][0]["expected"] == "资源与能力"
    assert result["issues"][0]["detector"] == "rapidocr_onnxruntime"


def test_text_gate_uses_six_overlapping_tiles(tmp_path: Path) -> None:
    image_counts: list[int] = []
    prompts: list[str] = []

    def runner(**kwargs):
        image_counts.append(len(kwargs["image_paths"]))
        prompts.append(kwargs["prompt"])
        return json.dumps({"observed_text": [], "issues": []})

    audit_generated_image_text(
        _image(tmp_path), script_text="资源与能力", vision_runner=runner,
        ocr_runner=lambda _path: [],
    )
    assert image_counts == [6]
    assert "不得依据上下文" in prompts[0]
