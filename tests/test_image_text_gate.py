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


def _bind_stage02_fidelity(
    image_path: Path,
    *,
    fidelity_text: list[dict[str, str]],
    semantic_sha256: str = "semantic-hash",
) -> Path:
    project = image_path.parent / "project"
    intake_path = project / "workbench/stages/02-input/script-intake.json"
    intake_path.parent.mkdir(parents=True, exist_ok=True)
    intake_path.write_text(
        json.dumps(
            {
                "schema": "cyberppt.stage02_script_input.v1",
                "semantic_sha256": semantic_sha256,
                "pages": [
                    {
                        "page_number": 1,
                        "page_id": "P01",
                        "fidelity_text": fidelity_text,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest_path = image_path.parent / "page_image_pairs.json"
    manifest_path.write_text(
        json.dumps(
            {
                "stage02_script_input": {
                    "path": str(intake_path),
                    "schema": "cyberppt.stage02_script_input.v1",
                },
                "pairs": [
                    {
                        "page_number": 1,
                        "full": {"path": str(image_path)},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return intake_path


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


def test_required_fidelity_exact_match_passes(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path),
        script_text="正文可以被重新组织，不构成逐字合同。",
        fidelity_text=[{"text": "2028年", "visibility": "required"}],
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "到2028年完成", "confidence": .99, "bbox": []}
        ],
    )
    assert result["valid"] is True
    assert result["scope"] == "fidelity_and_typo_gibberish"


def test_required_fidelity_missing_fails_even_when_ordinary_script_differs(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path),
        script_text="到2028年形成稳定服务能力。",
        fidelity_text=[{"text": "2028年", "visibility": "required"}],
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "稳定服务能力", "confidence": .99, "bbox": []}
        ],
    )
    assert result["valid"] is False
    assert result["issues"][0]["type"] == "fidelity_required_missing"


def test_if_rendered_fidelity_absent_passes(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path),
        script_text="正文不要求出现这个短语。",
        fidelity_text=[{"text": "统一入口", "visibility": "if_rendered"}],
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "业务协同", "confidence": .99, "bbox": []}
        ],
    )
    assert result["valid"] is True


def test_if_rendered_fidelity_near_miss_fails(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path),
        script_text="正文不参与逐字比较。",
        fidelity_text=[{"text": "统一入口", "visibility": "if_rendered"}],
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "统一人口", "confidence": .97, "bbox": []}
        ],
    )
    assert result["valid"] is False
    assert result["issues"][0]["type"] == "fidelity_if_rendered_mismatch"


def test_ordinary_script_text_mismatch_still_does_not_create_exact_copy_failure(tmp_path: Path) -> None:
    result = audit_generated_image_text(
        _image(tmp_path),
        script_text="到2028年覆盖80%的场景并投入100万元。",
        fidelity_text=[],
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "场景服务", "confidence": .95, "bbox": []}
        ],
    )
    assert result["valid"] is True
    assert result["scope"] == "typo_and_gibberish_only"


def test_text_gate_resolves_required_fidelity_from_canonical_stage02_intake(tmp_path: Path) -> None:
    image = _image(tmp_path)
    intake = _bind_stage02_fidelity(
        image,
        fidelity_text=[{"text": "2028年", "visibility": "required"}],
        semantic_sha256="fidelity-semantic-hash",
    )

    result = audit_generated_image_text(
        image,
        script_text="普通正文不再承担逐字锁定。",
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "到2028年完成", "confidence": .99, "bbox": []}
        ],
    )

    assert result["valid"] is True
    assert result["fidelity_text"] == [{"text": "2028年", "visibility": "required"}]
    assert result["fidelity_source"]["mode"] == "canonical_stage02_intake"
    assert result["fidelity_source"]["intake"] == str(intake.resolve())
    assert result["fidelity_source"]["intake_semantic_sha256"] == "fidelity-semantic-hash"


def test_text_gate_canonical_intake_required_fidelity_blocks_existing_image_reuse(tmp_path: Path) -> None:
    image = _image(tmp_path)
    _bind_stage02_fidelity(
        image,
        fidelity_text=[{"text": "统一入口", "visibility": "required"}],
    )

    result = audit_generated_image_text(
        image,
        script_text="正文允许重新组织。",
        vision_runner=_vision(),
        ocr_runner=lambda _path: [
            {"text": "业务协同", "confidence": .99, "bbox": []}
        ],
    )

    assert result["valid"] is False
    assert result["issues"][0]["type"] == "fidelity_required_missing"
    assert result["fidelity_source"]["page_number"] == 1


def test_text_gate_does_not_silently_ignore_missing_bound_stage02_intake(tmp_path: Path) -> None:
    image = _image(tmp_path)
    missing = tmp_path / "missing-intake.json"
    (tmp_path / "page_image_pairs.json").write_text(
        json.dumps(
            {
                "stage02_script_input": {"path": str(missing)},
                "pairs": [{"page_number": 1, "full": {"path": str(image)}}],
            }
        ),
        encoding="utf-8",
    )

    try:
        audit_generated_image_text(
            image,
            script_text="正文",
            vision_runner=_vision(),
            ocr_runner=lambda _path: [],
        )
    except FileNotFoundError as exc:
        assert "fidelity intake" in str(exc)
    else:
        raise AssertionError("bound Stage 02 intake must not disappear silently")
