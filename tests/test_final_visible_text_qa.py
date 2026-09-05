from pathlib import Path
from types import SimpleNamespace

import pytest

from PIL import Image

from scripts.image_to_pptx_runtime.final_visible_text_qa import audit_final_visible_text
from cyberppt.stage02_production.delivery_stage import _run_final_visible_text_qa


def test_final_visible_text_qa_passes_declared_svg_text_and_authorized_graphic_text(tmp_path: Path) -> None:
    image = tmp_path / "preview.png"
    Image.new("RGB", (160, 90), "white").save(image)

    report = audit_final_visible_text(
        image,
        expected_texts=["登记编目"],
        authorized_image_texts=["品牌字样"],
        ocr_runner=lambda _path: [
            {"text": "登记", "bbox": [[1, 1], [20, 1], [20, 10], [1, 10]]},
            {"text": "品牌字样", "bbox": [[30, 1], [60, 1], [60, 10], [30, 10]]},
        ],
    )

    assert report["valid"] is True
    assert report["unexpected_chinese"] == []


def test_final_visible_text_qa_accepts_dash_ocr_alias_only_at_declared_positions(tmp_path: Path) -> None:
    image = tmp_path / "preview.png"
    Image.new("RGB", (160, 90), "white").save(image)
    expected = ["技术研发—验证评测—场景应用"]
    for observed, valid in [
        ("技术研发一验证评测一场景应用", True),
        ("技术研发一验证评测—场景应用", True),
        ("技术一研发验证评测场景应用", False),
        ("技术研发一验证评测一场景应用伪字", False),
    ]:
        report = audit_final_visible_text(image, expected_texts=expected,
            ocr_runner=lambda _path: [{"text": observed}])
        assert report["valid"] is valid
    report = audit_final_visible_text(image, expected_texts=["技术研发验证评测"],
        ocr_runner=lambda _path: [{"text": "技术研发一验证评测"}])
    assert report["valid"] is False


def test_final_visible_text_qa_accepts_declared_vertical_separator_ocr_alias(tmp_path: Path) -> None:
    image = tmp_path / "preview.png"
    Image.new("RGB", (160, 90), "white").save(image)

    report = audit_final_visible_text(
        image,
        expected_texts=["工作安排｜任务填报"],
        ocr_runner=lambda _path: [{"text": "工作安排一任务填报", "confidence": 0.96}],
    )

    assert report["valid"] is True


def test_final_visible_text_qa_ignores_low_confidence_single_character_noise(tmp_path: Path) -> None:
    image = tmp_path / "preview.png"
    Image.new("RGB", (160, 90), "white").save(image)

    report = audit_final_visible_text(
        image,
        expected_texts=["登记编目"],
        ocr_runner=lambda _path: [{"text": "百", "confidence": 0.67}],
    )

    assert report["valid"] is True


def test_final_visible_text_qa_blocks_unowned_residual_chinese(tmp_path: Path) -> None:
    image = tmp_path / "preview.png"
    Image.new("RGB", (160, 90), "white").save(image)

    report = audit_final_visible_text(
        image,
        expected_texts=["登记编目"],
        ocr_runner=lambda _path: [
            {"text": "登记编目伪字", "bbox": [[1, 1], [60, 1], [60, 10], [1, 10]]},
        ],
    )

    assert report["valid"] is False
    assert report["status"] == "failed"
    assert report["unexpected_chinese"][0]["chinese_run"] == "登记编目伪字"


def test_final_visible_text_qa_fails_closed_when_ocr_is_unavailable(tmp_path: Path) -> None:
    image = tmp_path / "preview.png"
    Image.new("RGB", (160, 90), "white").save(image)

    def unavailable(_path: Path):
        raise RuntimeError("missing OCR")

    report = audit_final_visible_text(
        image,
        expected_texts=[],
        ocr_runner=unavailable,
    )

    assert report["valid"] is False
    assert report["checks"]["ocr_executed"] is False


def test_final_visible_text_qa_fails_closed_on_invalid_ocr_observations(tmp_path: Path) -> None:
    image = tmp_path / "preview.png"
    Image.new("RGB", (160, 90), "white").save(image)

    report = audit_final_visible_text(
        image,
        expected_texts=[],
        ocr_runner=lambda _path: ["self-reported pass"],  # type: ignore[list-item]
    )

    assert report["valid"] is False
    assert report["checks"]["ocr_executed"] is False


def test_delivery_final_visible_text_qa_rejects_a_passed_renderer_receipt_without_renders(tmp_path: Path) -> None:
    context = SimpleNamespace(build_dir=tmp_path, canonical_script=tmp_path / "script.md")
    manifest_result = SimpleNamespace(page_numbers=(1,), manifest={"pairs": []})

    with pytest.raises(RuntimeError, match="requires rendered pages"):
        _run_final_visible_text_qa(
            context=context,
            manifest_result=manifest_result,
            reports={
                "editable": {
                    "schema": "cyberppt.officecli_render_qa.v1",
                    "passed": True,
                    "report_path": str(tmp_path / "officecli.json"),
                }
            },
        )


def test_delivery_final_visible_text_qa_skips_unowned_text_gate_for_picture_ppt(tmp_path: Path) -> None:
    context = SimpleNamespace(build_dir=tmp_path, canonical_script=tmp_path / "script.md")
    manifest_result = SimpleNamespace(page_numbers=(1,), manifest={"pairs": []})

    result = _run_final_visible_text_qa(
        context=context,
        manifest_result=manifest_result,
        reports={
            "image": {
                "schema": "cyberppt.officecli_render_qa.v1",
                "passed": True,
                "report_path": str(tmp_path / "officecli.json"),
            }
        },
    )

    assert result == {}
