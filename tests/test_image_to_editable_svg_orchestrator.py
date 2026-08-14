import json
from pathlib import Path

from PIL import Image

from scripts.image_to_editable_svg.orchestrator import run_image_to_editable_svg


def _manifest(tmp_path: Path, *, regions=None) -> tuple[Path, Path]:
    project = tmp_path / "project"
    project.mkdir()
    script = project / "final-script.md"
    script.write_text("## 第1页：核心结论\n正文\n", encoding="utf-8")
    image = project / "full.png"
    Image.new("RGB", (200, 100), "white").save(image)
    payload = {
        "production_mode": "image-to-editable-svg",
        "output_variants": ["full"],
        "source_script": str(script),
        "pairs": [{
            "page_number": 1,
            "full": {"path": str(image), "status": "Generated", "text_audit": {"valid": True}, "ocr_layout": {"items": [{"text": "核心结论", "bbox": [1, 1, 50, 10]}, {"text": "正文", "bbox": [1, 20, 50, 10]}]}},
            "regions": regions or [],
        }],
    }
    manifest = project / "page_image_pairs.json"
    manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return project, manifest


def test_production_build_runs_audited_svg_pptx_and_readback(tmp_path, monkeypatch):
    project, manifest = _manifest(tmp_path)

    def assemble(_svgs, output, **_kwargs):
        output.write_bytes(b"pptx")
        return True

    monkeypatch.setattr("scripts.image_to_editable_svg.orchestrator.create_pptx_with_native_svg", assemble)
    monkeypatch.setattr("scripts.image_to_editable_svg.orchestrator.build_text_content_qa", lambda *_args, **_kwargs: {"valid": True})
    monkeypatch.setattr("scripts.image_to_editable_svg.orchestrator._render_report", lambda _pptx, output, _count: ({"valid": True}, output / "analysis" / "render_compare.json"))

    result = run_image_to_editable_svg(project=project, manifest_path=manifest, output_dir=project / "out")

    assert result["status"] == "production_ready"
    assert Path(result["artifacts"]["exported_pptx"]).is_file()
    assert result["reports"]["text_content_qa"]["valid"] is True


def test_manual_required_page_prevents_pptx_assembly(tmp_path, monkeypatch):
    project, manifest = _manifest(tmp_path, regions=[{"id": "chart", "type": "chart", "bbox": [50, 20, 30, 30]}])
    monkeypatch.setattr("scripts.image_to_editable_svg.orchestrator.create_pptx_with_native_svg", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not assemble")))

    result = run_image_to_editable_svg(project=project, manifest_path=manifest, output_dir=project / "out")

    assert result["status"] == "production_rework_required"
    assert result["artifacts"]["exported_pptx"] is None
