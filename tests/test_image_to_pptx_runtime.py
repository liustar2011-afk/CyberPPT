from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from scripts.image_to_pptx_runtime import assert_internal_runtime
from scripts.image_to_pptx_runtime.quick import create_quick_project
from scripts.image_to_pptx_runtime.review import ReviewIssue, write_review
from scripts.image_to_pptx_runtime.stage02_adapter import run_stage02_reconstruction


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
    manifest.write_text(json.dumps({"production_mode": "image-to-editable-svg", "output_variants": ["full"], "source_script": str(script), "pairs": [{"page_number": 1, "full": {"path": str(source), "status": "Generated", "text_audit": {"valid": True}}}]}, ensure_ascii=False), encoding="utf-8")
    try:
        run_stage02_reconstruction(project=tmp_path, manifest_path=manifest, output_dir=tmp_path / "out", requested_pages=[1])
    except ValueError as exc:
        assert "hand-authored SVG" in str(exc)
    else:
        raise AssertionError("production adapter must not fall back to OCR coordinate authoring")
