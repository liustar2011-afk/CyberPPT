"""Production assembly for the audited full-image -> editable-SVG Stage 02 route."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks
from scripts.imagegen_pipeline.production_readiness import build_production_readiness
from scripts.presentation_qa.render_page import check_pptx_geometry, render_to_png
from scripts.image_to_pptx_runtime.svg_to_pptx.pptx_package.builder import create_pptx_with_native_svg
from scripts.presentation_qa.text_content import build_text_content_qa

from .reconstruct import author_page_svg, inspect_page, write_inspection
from .roster import build_roster
from .svg_quality import check_page_svg


REQUIRED_ARTIFACTS = (
    "reconstruction_inventory", "svg_output", "reconstruction_quality",
    "text_content_qa", "render_compare", "exported_pptx",
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _mapping_or_file(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and Path(value).expanduser().is_file():
        return _read_json(Path(value).expanduser())
    return None


def load_and_require_audited_full_manifest(manifest_path: Path | str) -> dict[str, Any]:
    path = Path(manifest_path).expanduser().resolve()
    manifest = _read_json(path)
    if manifest.get("production_mode") != "image-to-editable-svg":
        raise ValueError("manifest must use production_mode image-to-editable-svg")
    if manifest.get("output_variants") != ["full"]:
        raise ValueError("manifest must contain exactly one full image variant")
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("manifest has no page pairs")
    for pair in pairs:
        if not isinstance(pair, Mapping) or not isinstance(pair.get("page_number"), int):
            raise ValueError("manifest contains an invalid page pair")
        full = pair.get("full")
        image = Path(str(full.get("path") or "")) if isinstance(full, Mapping) else Path()
        if not isinstance(full, Mapping) or full.get("status") != "Generated" or not image.is_file():
            raise ValueError(f"page {pair.get('page_number')} lacks a generated full image")
        if not isinstance(full.get("text_audit"), Mapping) or full["text_audit"].get("valid") is not True:
            raise ValueError(f"page {pair.get('page_number')} full image lacks a passed text audit")
    return manifest


def _truth_lines(script: Path, page_number: int) -> list[str]:
    block = parse_page_blocks(script).get(page_number)
    if block is None:
        raise ValueError(f"approved script has no page {page_number}")
    return [value for value in [block.title, *block.text.splitlines()] if value.strip()]


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _render_report(pptx: Path, output_dir: Path, expected_count: int) -> tuple[dict[str, Any], Path]:
    render_dir = output_dir / "rendered"
    geometry = check_pptx_geometry(pptx)
    try:
        pages = render_to_png(pptx, render_dir)
        render_error = None
    except Exception as exc:  # rendering is a required delivery gate
        pages, render_error = [], str(exc)
    report = {
        "schema": "cyberppt.image_to_editable_svg.render_compare.v1",
        "valid": bool(geometry.get("valid") and len(pages) == expected_count),
        "geometry": geometry,
        "rendered_pages": [str(page) for page in pages],
        "expected_page_count": expected_count,
        "error": render_error,
    }
    return report, _write_json(output_dir / "analysis" / "render_compare.json", report)


def run_image_to_editable_svg(*, project: Path | str, manifest_path: Path | str, output_dir: Path | str | None = None, requested_pages: list[int] | None = None) -> dict[str, Any]:
    """Reconstruct all requested audited pages, and export only after every gate passes."""
    project_path = Path(project).expanduser().resolve()
    manifest_path = Path(manifest_path).expanduser().resolve()
    manifest = load_and_require_audited_full_manifest(manifest_path)
    output = Path(output_dir or manifest_path.parent / "editable_svg_build").expanduser().resolve()
    script = Path(str(manifest.get("source_script") or "")).expanduser().resolve()
    if not script.is_file():
        raise FileNotFoundError(f"approved source script not found: {script}")
    pairs = [dict(pair) for pair in manifest["pairs"]]
    if requested_pages is not None:
        requested = set(requested_pages)
        pairs = [pair for pair in pairs if pair["page_number"] in requested]
        if {pair["page_number"] for pair in pairs} != requested:
            raise ValueError("requested pages are not an exact subset of the manifest")
    frames = build_roster(pages=[(pair["page_number"], Path(pair["full"]["path"])) for pair in pairs], output_dir=output / "canonical_frames")
    pages: list[dict[str, Any]] = []
    for pair, frame in zip(pairs, frames, strict=True):
        full = dict(pair["full"])
        inspection = inspect_page(
            frame,
            script_text=_truth_lines(script, frame.page_number),
            ocr_layout=_mapping_or_file(full.get("ocr_layout")) or _mapping_or_file(pair.get("ocr_layout")),
            regions=pair.get("regions") if isinstance(pair.get("regions"), list) else None,
            visual_registry=_mapping_or_file(pair.get("visual_registry")),
            authoring_svg_path=pair.get("authoring_svg"),
        )
        inspection_path = write_inspection(inspection, output / "analysis" / f"p{frame.page_number:02d}-inventory.json")
        page: dict[str, Any] = {"page_number": frame.page_number, "inventory": str(inspection_path), "page_gate": inspection["page_gate"], "manual_required": inspection["manual_required"], "svg": None, "svg_quality": None}
        if inspection["page_gate"].get("valid"):
            svg = author_page_svg(inspection, output / "svg_output")
            quality = check_page_svg(svg, inspection)
            quality_path = _write_json(output / "analysis" / f"p{frame.page_number:02d}-reconstruction-quality.json", quality)
            page.update(svg=str(svg), svg_quality=quality, reconstruction_quality=str(quality_path))
        pages.append(page)

    page_valid = all(page["page_gate"].get("valid") and isinstance(page["svg_quality"], Mapping) and page["svg_quality"].get("valid") for page in pages)
    artifacts: dict[str, str | None] = {
        "reconstruction_inventory": str(output / "analysis") if pages else None,
        "svg_output": str(output / "svg_output") if page_valid else None,
        "reconstruction_quality": str(output / "analysis") if pages else None,
        "text_content_qa": None, "render_compare": None, "exported_pptx": None,
    }
    reports: dict[str, dict[str, Any]] = {
        "reconstruction_inventory": {"valid": bool(pages)},
        "reconstruction_quality": {"valid": page_valid, "pages": pages},
        "svg_output": {"valid": page_valid},
    }
    if page_valid:
        pptx = output / "exports" / "editable_svg.pptx"
        pptx.parent.mkdir(parents=True, exist_ok=True)
        assembled = create_pptx_with_native_svg([Path(str(page["svg"])) for page in pages], pptx, verbose=False, use_compat_mode=False, use_native_shapes=True)
        if assembled and pptx.is_file():
            expected = [text for page in pages for text in _truth_lines(script, int(page["page_number"]))]
            text_qa = build_text_content_qa(pptx, expected, order_sensitive=False)
            text_path = _write_json(output / "analysis" / "text_content_qa.json", text_qa)
            render_report, render_path = _render_report(pptx, output, len(pages))
            artifacts.update(text_content_qa=str(text_path), render_compare=str(render_path), exported_pptx=str(pptx))
            reports.update(text_content_qa=text_qa, render_compare=render_report, exported_pptx={"valid": True})
        else:
            reports["exported_pptx"] = {"valid": False, "status": "assembly_failed"}
    readiness = build_production_readiness(stage="02-production-build", artifacts=artifacts, reports=reports, required_tools=REQUIRED_ARTIFACTS)
    if not readiness["valid"]:
        artifacts["exported_pptx"] = None
    result = {"schema": "cyberppt.image_to_editable_svg.run.v1", "status": readiness["status"], "project": str(project_path), "manifest": str(manifest_path), "artifacts": artifacts, "reports": reports, "pages": pages, "delivery_readiness": readiness}
    result_path = _write_json(output / "analysis" / "delivery_readiness.json", result)
    result["artifacts"]["delivery_readiness"] = str(result_path)
    return result
