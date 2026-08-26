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


def test_independent_ocr_does_not_block_multicharacter_mismatch(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path), script_text="资源与能力",
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "瓷源与能力", "confidence": .649, "bbox": [[1, 2], [3, 4]]}
        ],
    )
    assert result["valid"] is True


def test_independent_ocr_ignores_shifted_neighbors_and_divider_marks(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path),
        script_text=(
            "行业级连接、可信使用和服务运营成为必要支撑\n"
            "需求升级｜业务变化扩大跨主体协同范围\n"
            "供给缺口｜分散资源难以形成稳定服务"
        ),
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "需求升级I", "confidence": .70, "bbox": []},
            {"text": "需求升级丨", "confidence": .70, "bbox": []},
            {"text": "同供给缺口1", "confidence": .72, "bbox": []},
        ],
    )
    assert result["valid"] is True


def test_independent_ocr_does_not_infer_interior_glyph_substitution(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path),
        script_text="可信接入、资源目录和接口衔接降低资源发现与技术对接成本",
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "接口街接降低资源发现", "confidence": .91, "bbox": [[1, 2], [3, 4]]}
        ],
    )
    assert result["valid"] is True


def test_independent_ocr_ignores_short_neighbor_slice(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path),
        script_text="资源供给",
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "与供给", "confidence": .75, "bbox": [[1, 2], [3, 4]]}
        ],
    )
    assert result["valid"] is True


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
