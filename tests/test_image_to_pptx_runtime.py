from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from PIL import Image

from scripts.image_to_pptx_runtime import assert_internal_runtime
from scripts.image_to_pptx_runtime.graphic_text_policy import validate_graphic_text_policy
from scripts.image_to_pptx_runtime.clean_base_policy import (
    SCHEMA as CLEAN_BASE_SCHEMA,
    validate_clean_base,
)
from scripts.image_to_pptx_runtime.quick import create_quick_project
from scripts.image_to_pptx_runtime.review import ReviewIssue, write_review
from scripts.image_to_pptx_runtime.stage02_adapter import run_stage02_reconstruction
from scripts.presentation_qa.text_content import pptx_texts


def test_runtime_is_self_contained_and_importable() -> None:
    from scripts.image_to_pptx_runtime.svg_quality.checker import SVGQualityChecker
    from scripts.image_to_pptx_runtime.svg_to_pptx.pptx_package.builder import create_pptx_with_native_svg

    assert_internal_runtime()
    assert SVGQualityChecker.__name__ == "SVGQualityChecker"
    assert callable(create_pptx_with_native_svg)


def test_quick_project_archives_source_and_rejects_whole_page_review(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (40, 20), "white").save(source)
    project = create_quick_project(tmp_path / "quick", pages=[(1, source)], text_by_page={1: ["结论"]})
    assert project.roster[0].source_path.is_file()
    assert project.roster[0].normalized_path.is_file()
    review = write_review(project, [ReviewIssue(1, "layout", "whole_page", "需要重新设计")])
    assert review["valid"] is False
    assert review["requires_rebuild"] is True


def test_stage02_adapter_requires_audited_hand_authored_svg(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (40, 20), "white").save(source)
    script = tmp_path / "script.md"
    script.write_text("## 第1页：结论\n结论\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"production_mode": "image-to-editable-svg", "output_variants": ["full"], "content_page_numbers": [1], "source_script": str(script), "pairs": [{"page_number": 1, "full": {"path": str(source), "status": "Generated", "text_audit": {"valid": True}}}]}, ensure_ascii=False), encoding="utf-8")
    try:
        run_stage02_reconstruction(project=tmp_path, manifest_path=manifest, output_dir=tmp_path / "out", requested_pages=[1])
    except ValueError as exc:
        assert "final-script-pages orchestration evidence" in str(exc)
    else:
        raise AssertionError("production adapter must reject direct invocation")


def _graphic_text_policy(*, items: list[dict[str, object]] | None = None, empty_container_check: str = "passed") -> dict[str, object]:
    return {
        "schema": "cyberppt.image_to_pptx.graphic_text_policy.v1",
        "status": "complete",
        "empty_container_check": empty_container_check,
        "items": items or [],
    }


def _policy_svg(tmp_path: Path, *, text: str = "登记编目") -> Path:
    svg = tmp_path / "page_001.svg"
    svg.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#FFFFFF"/>
  <text x="40" y="80" font-family="Arial" font-size="20" fill="#0B3B78">{text}</text>
</svg>
''',
        encoding="utf-8",
    )
    return svg


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _clean_base_contract(full: Path, clean: Path, *, text: str = "登记编目") -> dict[str, object]:
    return {
        "schema": CLEAN_BASE_SCHEMA,
        "status": "complete",
        "path": str(clean),
        "source_sha256": _hash(full),
        "sha256": _hash(clean),
        "cleaned_text_regions": [{"id": "label-1", "text": text}],
        "visual_diff_report": {"status": "passed"},
    }


def _official_context(manifest: Path, script: Path, *, assembly_mode: str = "editable") -> None:
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data["source_script_sha256"] = _hash(script)
    manifest.write_text(json.dumps(manifest_data, ensure_ascii=False), encoding="utf-8")
    (manifest.parent / "build_context.json").write_text(
        json.dumps(
            {
                "schema": "cyberppt.build_context.v1",
                "production_mode": "image-to-editable-svg",
                "assembly_mode": assembly_mode,
                "source_script_sha256": _hash(script),
                "artifacts": {"page_image_pairs": {"path": str(manifest), "sha256": _hash(manifest)}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_graphic_text_policy_requires_native_reconstruction_for_cleared_text(tmp_path: Path) -> None:
    svg = _policy_svg(tmp_path)
    report = validate_graphic_text_policy(
        _graphic_text_policy(items=[{"id": "label-1", "text": "登记编目", "treatment": "native_text"}]),
        authored_svg=svg,
        page_number=1,
    )
    assert report["valid"] is True


def test_graphic_text_policy_is_required_even_when_no_embedded_text_is_declared(tmp_path: Path) -> None:
    report = validate_graphic_text_policy(None, authored_svg=_policy_svg(tmp_path), page_number=1)
    assert report["valid"] is False
    assert {error["code"] for error in report["errors"]} >= {
        "missing_or_invalid_schema",
        "policy_not_complete",
        "empty_container_check_failed",
        "invalid_items",
    }


def test_graphic_text_policy_blocks_missing_native_text_and_empty_containers(tmp_path: Path) -> None:
    svg = _policy_svg(tmp_path, text="其他文字")
    report = validate_graphic_text_policy(
        _graphic_text_policy(
            items=[{"id": "label-1", "text": "登记编目", "treatment": "native_text"}],
            empty_container_check="failed",
        ),
        authored_svg=svg,
        page_number=1,
    )
    assert report["valid"] is False
    assert {error["code"] for error in report["errors"]} == {"empty_container_check_failed", "invalid_item"}


def test_graphic_text_policy_requires_evidence_for_preserved_image_text(tmp_path: Path) -> None:
    svg = _policy_svg(tmp_path)
    report = validate_graphic_text_policy(
        _graphic_text_policy(items=[{"id": "label-1", "text": "登记编目", "treatment": "preserved_in_image"}]),
        authored_svg=svg,
        page_number=1,
    )
    assert report["valid"] is False
    assert report["errors"][0]["code"] == "invalid_item"


def test_graphic_text_policy_accepts_preserved_text_with_local_image_evidence(tmp_path: Path) -> None:
    asset = tmp_path / "wordmark.png"
    Image.new("RGB", (20, 20), "white").save(asset)
    svg = _policy_svg(tmp_path)
    svg.write_text(
        svg.read_text(encoding="utf-8").replace(
            "</svg>",
            '<image href="wordmark.png" x="200" y="20" width="40" height="40"/>\n</svg>',
        ),
        encoding="utf-8",
    )
    report = validate_graphic_text_policy(
        _graphic_text_policy(
            items=[
                {
                    "id": "wordmark-1",
                    "text": "示例",
                    "treatment": "preserved_in_image",
                    "asset_ref": "wordmark.png",
                }
            ]
        ),
        authored_svg=svg,
        page_number=1,
    )
    assert report["valid"] is True


def test_clean_base_policy_rejects_full_page_as_preserved_text_asset(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    Image.new("RGB", (400, 200), "white").save(full)
    authored = _policy_svg(tmp_path)
    authored.write_text(
        authored.read_text(encoding="utf-8").replace("</svg>", '<image href="full.png" x="0" y="0" width="400" height="200"/>\n</svg>'),
        encoding="utf-8",
    )
    report = validate_clean_base(
        _clean_base_contract(full, full),
        full_image=full,
        authored_svg=authored,
        graphic_text_policy=_graphic_text_policy(
            items=[{"id": "wordmark", "text": "登记编目", "treatment": "preserved_in_image", "asset_ref": "full.png", "identity_integral": True}]
        ),
        page_number=1,
    )
    assert report["valid"] is False
    assert {error["code"] for error in report["errors"]} >= {"full_image_as_clean_base", "preserved_text_uses_page_layer"}


def test_stage02_adapter_records_graphic_text_policy_qa_before_delivery(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (400, 200), "white").save(source)
    clean = tmp_path / "clean-base.png"
    Image.new("RGB", (400, 200), "#E8F0F8").save(clean)
    script = tmp_path / "script.md"
    script.write_text("## 第1页：标题\n结论\n", encoding="utf-8")
    authored = _policy_svg(tmp_path)
    authored.write_text(
        authored.read_text(encoding="utf-8").replace(
            "</svg>",
                '<image href="clean-base.png" x="0" y="0" width="400" height="200"/>\n<text x="40" y="150" font-family="Arial" font-size="20" fill="#000000">结论</text>\n</svg>',
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "production_mode": "image-to-editable-svg",
                "output_variants": ["full"],
                "source_script": str(script),
                "content_page_numbers": [1],
                "pairs": [
                    {
                        "page_number": 1,
                        "full": {"path": str(source), "status": "Generated", "text_audit": {"valid": True}, "debug_receipt": {"visible_text": ["结论", "登记编目"]}},
                        "authoring_svg": str(authored),
                        "clean_base": _clean_base_contract(source, clean),
                        "graphic_text_policy": _graphic_text_policy(
                            items=[{"id": "label-1", "text": "登记编目", "treatment": "native_text"}]
                        ),
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _official_context(manifest, script)

    result = run_stage02_reconstruction(
        project=tmp_path,
        manifest_path=manifest,
        output_dir=tmp_path / "out",
        requested_pages=[1],
    )

    assert result["status"] == "production_ready"
    assert result["reports"]["graphic_text_policy"]["valid"] is True
    assert result["reports"]["native_text_style"]["valid"] is True
    style_qa = Path(result["artifacts"]["native_text_style_qa"])
    assert style_qa.is_file()
    styled_svg = Path(result["artifacts"]["svg_output"]) / "01.svg"
    assert 'data-cyberppt-native-text-style="editorial-source-text-v1"' in styled_svg.read_text(encoding="utf-8")
    assert Path(result["artifacts"]["graphic_text_policy_qa"]).is_file()
    assert "登记编目" in pptx_texts(Path(result["artifacts"]["exported_pptx"]))


def test_quick_split_text_flow_keeps_visual_tspan_rows_editable(tmp_path: Path) -> None:
    from scripts.image_to_pptx_runtime.svg_to_pptx.pptx_package.builder import create_pptx_with_native_svg

    svg = tmp_path / "page_001.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#FFFFFF"/>
  <text x="40" y="80" font-family="Arial" font-size="20" fill="#000000">
    <tspan>第一行</tspan>
    <tspan x="40" dy="28">第二行</tspan>
  </text>
</svg>
""",
        encoding="utf-8",
    )
    output = tmp_path / "editable.pptx"

    assert create_pptx_with_native_svg(
        [svg],
        output,
        verbose=False,
        use_compat_mode=False,
        use_native_shapes=True,
        pptx_structure="flat",
        text_flow="split",
    )
    assert pptx_texts(output) == ["第一行", "第二行"]
