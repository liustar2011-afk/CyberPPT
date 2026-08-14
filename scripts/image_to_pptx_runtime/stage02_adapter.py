"""CyberPPT Stage 02 boundary for the imported image-to-PPTX Quick runtime."""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from scripts.dual_image_overlay.text_content_qa import build_text_content_qa
from scripts.dual_image_overlay.production_readiness import build_production_readiness

from .quick import create_quick_project
from .review import write_review
from .svg_quality.checker import SVGQualityChecker
from .svg_to_pptx.pptx_package.builder import create_pptx_with_native_svg


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _script_lines(script: Path, page_number: int) -> list[str]:
    from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks

    page = parse_page_blocks(script).get(page_number)
    if page is None:
        raise ValueError(f"final script has no page {page_number}")
    return [item for item in [page.title, *page.text.splitlines()] if item.strip()]


def _require_audited_pairs(manifest: Mapping[str, Any], requested_pages: list[int]) -> list[dict[str, Any]]:
    if manifest.get("production_mode") != "image-to-editable-svg" or manifest.get("output_variants") != ["full"]:
        raise ValueError("Stage 02 image-to-PPTX requires the audited full-image production manifest")
    pairs = [dict(item) for item in manifest.get("pairs", []) if isinstance(item, Mapping) and item.get("page_number") in requested_pages]
    if {int(item["page_number"]) for item in pairs} != set(requested_pages):
        raise ValueError("requested pages are not an exact manifest subset")
    for pair in pairs:
        full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
        source = Path(str(full.get("path") or ""))
        if full.get("status") != "Generated" or not source.is_file() or full.get("text_audit", {}).get("valid") is not True:
            raise ValueError(f"page {pair['page_number']} requires generated full image with passed text audit")
    return pairs


def _copy_relative_svg_assets(source: Path, target: Path) -> None:
    """Keep prepared SVG image layers valid inside the internal Quick project."""
    root = ET.fromstring(source.read_text(encoding="utf-8"))
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "image":
            continue
        href = node.attrib.get("href") or node.attrib.get("{http://www.w3.org/1999/xlink}href")
        if not href or href.startswith(("data:", "http:", "https:")) or Path(href).is_absolute():
            continue
        asset = (source.parent / href).resolve()
        if not asset.is_file():
            raise FileNotFoundError(f"authored SVG layer is missing: {asset}")
        destination = (target.parent / href).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, destination)


def run_stage02_reconstruction(*, project: Path | str, manifest_path: Path | str, output_dir: Path | str, requested_pages: list[int]) -> dict[str, Any]:
    """Prepare and release a faithful SVG roster; never synthesize one from OCR boxes."""
    manifest_file = Path(manifest_path).expanduser().resolve()
    manifest = _read_json(manifest_file)
    pairs = _require_audited_pairs(manifest, requested_pages)
    script = Path(str(manifest.get("source_script") or "")).expanduser().resolve()
    if not script.is_file():
        raise FileNotFoundError(f"approved source script is missing: {script}")
    output = Path(output_dir).expanduser().resolve()
    pages = [(int(pair["page_number"]), Path(str(pair["full"]["path"]))) for pair in pairs]
    quick = create_quick_project(output / "image_to_pptx_runtime", pages=pages, text_by_page={number: _script_lines(script, number) for number, _ in pages})
    svgs: list[Path] = []
    quality: list[dict[str, Any]] = []
    checker = SVGQualityChecker(quick_generate=True)
    for pair in pairs:
        authored = Path(str(pair.get("authoring_svg") or "")).expanduser()
        if not authored.is_file():
            raise ValueError(f"page {pair['page_number']} requires a hand-authored SVG from the image-to-PPTX runtime")
        target = quick.svg_path(int(pair["page_number"]))
        shutil.copy2(authored, target)
        _copy_relative_svg_assets(authored, target)
        report = checker.check_file(str(target))
        quality.append(report)
        if not report.get("passed"):
            raise ValueError(f"page {pair['page_number']} failed imported SVG quality: {report.get('errors')}")
        svgs.append(target)
    review = write_review(quick, [])
    export = output / "exports" / "editable_svg.pptx"
    export.parent.mkdir(parents=True, exist_ok=True)
    if not create_pptx_with_native_svg(svgs, export, verbose=False, use_compat_mode=False, use_native_shapes=True, pptx_structure="flat"):
        raise RuntimeError("internal image-to-PPTX SVG export failed")
    expected = [text for number, _ in pages for text in _script_lines(script, number)]
    text_qa = build_text_content_qa(export, expected, order_sensitive=False)
    if not text_qa["valid"]:
        raise ValueError("exported PPTX native text differs from the approved script")
    analysis = output / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    text_path = analysis / "text_content_qa.json"
    text_path.write_text(json.dumps(text_qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifacts = {"reconstruction_inventory": str(quick.root / "analysis" / "reconstruction_inventory.json"), "svg_output": str(quick.root / "svg_output"), "reconstruction_quality": str(analysis), "text_content_qa": str(text_path), "render_compare": str(review["path"]), "exported_pptx": str(export)}
    reports = {"reconstruction_inventory": {"valid": True}, "reconstruction_quality": {"valid": True, "pages": quality}, "svg_output": {"valid": True}, "text_content_qa": text_qa, "render_compare": {"valid": review["valid"], "review": review}, "exported_pptx": {"valid": True}}
    readiness = build_production_readiness(stage="02-production-build", artifacts=artifacts, reports=reports, required_tools=tuple(artifacts))
    result = {"schema": "cyberppt.image_to_pptx.stage02.v1", "status": readiness["status"], "runtime_project": str(quick.root), "svg_roster": [str(svg) for svg in svgs], "svg_quality": quality, "visual_review": review, "artifacts": artifacts, "reports": reports, "text_content_qa": text_qa, "release_gate": {"valid": True, "manual_adjustments": "local_only"}, "delivery_readiness": readiness}
    result_path = analysis / "image-to-pptx-result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["artifacts"]["delivery_readiness"] = str(result_path)
    return result
