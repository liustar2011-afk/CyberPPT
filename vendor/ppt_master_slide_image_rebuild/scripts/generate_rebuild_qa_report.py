#!/usr/bin/env python3
"""
PPT Master - Rebuild QA Report

Generate a compact qa_report.md for the 复刻流程 / layout-reference-rebuild
workflow. The report summarizes editability, text fit, icon/text fit, and
image/icon usage signals.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

try:
    from crop_intake_summary import summarize_intake, summarize_crop_candidates
except ImportError:  # pragma: no cover
    from scripts.crop_intake_summary import summarize_intake, summarize_crop_candidates  # type: ignore

SVG_NS = "{http://www.w3.org/2000/svg}"


def _resolve_rms_paths(project: Path) -> tuple[Path | None, Path | None]:
    ref_candidates = [
        project / "images/reference_layout.png",
        project / "images/reference_layout.normalized.png",
    ]
    ref = next((path for path in ref_candidates if path.is_file()), None)
    if ref is None:
        page_refs = sorted((project / "images/reference_pages").glob("*.png"))
        ref = page_refs[0] if page_refs else None

    cand: Path | None = None
    preview_dir = project / "exports/preview_qa"
    if preview_dir.is_dir():
        previews = sorted(preview_dir.glob("*.preview.png"))
        cand = previews[0] if previews else None
    if cand is None:
        page_previews = sorted(project.glob("pages/*/exports/preview_qa/*.preview.png"))
        cand = page_previews[0] if page_previews else None
    return ref, cand


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _run_json(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"valid": False, "errors": [result.stdout.strip(), result.stderr.strip()]}
    return {"valid": result.returncode == 0, "errors": [result.stderr.strip()] if result.stderr.strip() else []}


def _latest_pptx(project: Path) -> Path | None:
    exports = project / "exports"
    if not exports.is_dir():
        return None
    pptxs = sorted(
        (path for path in exports.glob("*.pptx") if not path.name.startswith("~$")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return pptxs[0] if pptxs else None


def _svg_stats(svg_path: Path) -> dict:
    if not svg_path.exists():
        return {"exists": False}
    root = ET.parse(svg_path).getroot()
    paragraphs = []
    text_chars = 0
    for elem in root.iter():
        if _strip_ns(elem.tag) != "text":
            continue
        text_chars += len("".join(elem.itertext()).strip())
        line_height = elem.get("data-paragraph-line-height")
        tspans = [child for child in list(elem) if _strip_ns(child.tag) == "tspan"]
        if line_height is not None or len(tspans) > 1:
            paragraphs.append({
                "label": elem.get("data-fit-label") or "".join(elem.itertext()).strip()[:32],
                "lines": max(1, len(tspans)),
                "line_height": line_height or "",
            })
    return {
        "exists": True,
        "text": sum(1 for elem in root.iter() if _strip_ns(elem.tag) == "text"),
        "images": sum(1 for elem in root.iter() if _strip_ns(elem.tag) == "image"),
        "library_icons": sum(1 for elem in root.iter() if elem.get("data-icon")),
        "planned_icons": sum(1 for elem in root.iter() if elem.get("data-icon-id")),
        "paragraphs": paragraphs,
        "text_chars": text_chars,
    }


def _layout_density(layout_path: Path, svg_stats: dict, paragraph_count: int) -> dict[str, object]:
    try:
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        layout = {}
    zone_count = len([zone for zone in layout.get("zones", []) if isinstance(zone, dict)])
    explicit = layout.get("dense_rebuild_mode", {})
    text_elements = int(svg_stats.get("text", 0) or 0)
    text_chars = int(svg_stats.get("text_chars", 0) or 0)
    enabled = (
        bool(isinstance(explicit, dict) and explicit.get("enabled"))
        or zone_count >= 8
        or text_elements >= 55
        or paragraph_count >= 20
        or text_chars >= 900
    )
    return {
        "enabled": enabled,
        "zone_count": zone_count,
        "svg_text_elements": text_elements,
        "svg_text_chars": text_chars,
        "paragraph_blocks": paragraph_count,
    }


def _paragraph_warnings(density: dict[str, object], paragraph_count: int) -> list[str]:
    text_elements = int(density.get("svg_text_elements", 0) or 0)
    text_chars = int(density.get("svg_text_chars", 0) or 0)
    if paragraph_count:
        return []
    if text_elements >= 18 or text_chars >= 360:
        return [
            "text-heavy rebuild has zero paragraph blocks; check whether body copy was split into too many line-level textboxes"
        ]
    return []


def _pptx_text_counts(pptx: Path | None) -> dict[str, int]:
    if not pptx:
        return {"tx_body": 0, "runs": 0}
    try:
        with ZipFile(pptx) as package:
            slide_names = [name for name in package.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
            tx_body = 0
            runs = 0
            for name in slide_names:
                xml = package.read(name).decode("utf-8", errors="ignore")
                tx_body += xml.count("<p:txBody>")
                runs += xml.count("<a:t>")
            return {"tx_body": tx_body, "runs": runs}
    except (OSError, BadZipFile):
        return {"tx_body": 0, "runs": 0}


def _latest_trace(project: Path, pptx: Path | None) -> dict:
    if not pptx:
        return {}
    direct = Path(str(pptx) + ".trace.json")
    candidates = [direct] if direct.exists() else []
    candidates.extend(sorted((project / "exports").glob("*.trace.json"), key=lambda path: path.stat().st_mtime, reverse=True))
    if not candidates:
        return {}
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _trace_source_svg(project: Path, pptx: Path | None) -> Path | None:
    trace = _latest_trace(project, pptx)
    slides = trace.get("slides", []) if isinstance(trace, dict) else []
    if not slides:
        return None
    raw = slides[0].get("svg", "")
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path if path.exists() else None


def _export_strategy(project: Path, pptx: Path | None, paragraph_count: int) -> dict[str, object]:
    trace = _latest_trace(project, pptx)
    preprocess = []
    for slide in trace.get("slides", []) if isinstance(trace, dict) else []:
        preprocess.extend(slide.get("preprocess", []))
    merge_paragraphs = any(item.get("merge_paragraphs") is True for item in preprocess if isinstance(item, dict))
    flattened_positional = any(item.get("action") == "flatten-positional-tspans" for item in preprocess if isinstance(item, dict))
    source = ""
    slides = trace.get("slides", []) if isinstance(trace, dict) else []
    if slides:
        source = str(slides[0].get("svg", ""))
    status = "paragraph-editable" if merge_paragraphs else "pixel-fidelity"
    warnings = []
    if paragraph_count and not merge_paragraphs:
        warnings.append("paragraph blocks found but latest trace does not show --merge-paragraphs")
    if paragraph_count and "/svg_final/" in source:
        warnings.append("paragraph-editable exports should prefer svg_output to avoid finalize flatten-text side effects")
    return {
        "status": status,
        "merge_paragraphs": merge_paragraphs,
        "flattened_positional_tspans": flattened_positional,
        "source": source,
        "warnings": warnings,
    }


def _is_rebuild2_project(layout_path: Path) -> bool:
    if not layout_path.exists():
        return False
    try:
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    try:
        from layout_reference_rebuild2_lib import is_rebuild2
    except ImportError:
        from scripts.layout_reference_rebuild2_lib import is_rebuild2  # type: ignore
    return is_rebuild2(layout)


def _intake_markdown(project: Path, manifest: dict[str, Any] | None) -> list[str]:
    if not manifest:
        return []
    intake = summarize_intake(project, manifest)
    lines = [
        "## Intake",
        "",
    ]
    quality = intake.rebuild_quality_mode or "(not set)"
    rebuild = intake.rebuild_mode or "(not set)"
    export = intake.pptx_export_mode or "(not set)"
    lines.append(
        f"- Quality mode: `{quality}` → rebuild_mode=`{rebuild}`, pptx_export_mode=`{export}`"
        + (" (resolved from alias)" if intake.resolved_from_quality_mode else "")
    )
    if intake.preprocess_enabled:
        meta_status = "present" if intake.source_meta_present else "missing"
        norm_status = "present" if intake.normalized_image_present else "missing"
        lines.append(f"- Preprocess: enabled; source_meta.json {meta_status}; normalized reference {norm_status}")
    else:
        lines.append("- Preprocess: not enabled in manifest")
    if intake.precrop_candidates_enabled:
        lines.append("- Precrop candidates: enabled in manifest (Phase 3 script not yet available)")
    for warning in intake.warnings:
        lines.append(f"- Warning: {warning}")
    lines.append("")
    return lines


def _crop_candidates_markdown(project: Path, layout_data: dict[str, Any]) -> list[str]:
    if not layout_data:
        return []
    summary = summarize_crop_candidates(layout_data, project=project)
    if summary.total == 0:
        return []
    lines = [
        "## Crop candidates",
        "",
        "| id | intent | needs_review | precrop |",
        "|---|---|---|---|",
    ]
    raw = layout_data.get("crop_candidates", [])
    if isinstance(raw, list):
        for candidate in raw:
            if not isinstance(candidate, dict):
                continue
            precrop = candidate.get("precrop", {}) if isinstance(candidate.get("precrop"), dict) else {}
            precrop_label = "enabled" if precrop.get("enabled") else "disabled"
            lines.append(
                f"| {candidate.get('id', '')} | {candidate.get('editability_intent', '')} | "
                f"{'yes' if candidate.get('needs_review') else 'no'} | {precrop_label} |"
            )
    lines.extend([
        "",
        (
            f"- Summary: {summary.total} total, {summary.needs_review_count} need review, "
            f"{summary.precrop_missing_file_count} precrop enabled without file, "
            f"{summary.precrop_file_present_count} precrop file(s) present"
        ),
        "",
    ])
    return lines


def build_report(project: Path, *, rebuild2: bool = False) -> str:
    script_dir = Path(__file__).resolve().parent
    layout = project / "layout_reference.json"
    use_rebuild2 = rebuild2 or _is_rebuild2_project(layout)
    svg_candidates = sorted((project / "svg_final").glob("*.svg")) or sorted((project / "svg_output").glob("*.svg"))
    svg = svg_candidates[0] if svg_candidates else project / "svg_final" / "missing.svg"
    pptx = _latest_pptx(project)
    export_source_svg = _trace_source_svg(project, pptx) or svg

    readiness_cmd = [
        sys.executable,
        str(script_dir / "verify_rebuild_readiness.py"),
        str(project),
        "--stage",
        "pre-export",
    ]
    if use_rebuild2:
        readiness_cmd.append("--rebuild2")
    readiness_result = _run_json(readiness_cmd)
    layout_cmd = [sys.executable, str(script_dir / "validate_layout_reference.py"), str(layout)]
    if use_rebuild2:
        mapping = project / "content_mapping.json"
        layout_cmd.append("--rebuild2")
        if mapping.exists():
            layout_cmd.extend(["--mapping", str(mapping)])
    layout_result = _run_json(layout_cmd) if layout.exists() else {"valid": False, "errors": ["layout_reference.json missing"]}
    contract_result = (
        _run_json([sys.executable, str(script_dir / "verify_layout_executor_contract.py"), str(project)])
        if use_rebuild2
        else {"valid": True, "errors": [], "warnings": []}
    )
    icon_cmd = [sys.executable, str(script_dir / "verify_icon_text_fit.py"), str(layout)]
    if svg.exists():
        icon_cmd.extend(["--svg", str(svg)])
    if use_rebuild2:
        icon_cmd.append("--strict")
    icon_result = _run_json(icon_cmd) if layout.exists() else {"valid": False, "errors": ["layout_reference.json missing"]}
    try:
        from render_backend_resolve_lib import resolve_project_render_backend
    except ImportError:  # pragma: no cover
        from scripts.render_backend_resolve_lib import resolve_project_render_backend  # type: ignore
    render_backend, _backend_warnings = resolve_project_render_backend(project, hard_gate=True)
    visual_cmd = [
        sys.executable,
        str(script_dir / "verify_reference_similarity.py"),
        str(project),
        "--render",
        "--render-backend",
        render_backend,
        "--hard-gate",
    ]
    visual_result = (
        _run_json(visual_cmd)
        if use_rebuild2
        else {"valid": True, "errors": [], "warnings": [], "mean_diff": None}
    )
    rms_result: dict[str, Any] | None = None
    if use_rebuild2:
        ref_path, cand_path = _resolve_rms_paths(project)
        if ref_path and cand_path:
            rms_result = _run_json([
                sys.executable,
                str(script_dir / "verify_reference_preview_rms.py"),
                str(project),
                "--reference",
                str(ref_path.relative_to(project)),
                "--candidate",
                str(cand_path.relative_to(project)),
            ])
    text_result = _run_json([sys.executable, str(script_dir / "verify_text_fit.py"), str(svg)]) if svg.exists() else {"valid": False, "errors": ["SVG missing"]}
    spacing_result = _run_json([sys.executable, str(script_dir / "verify_svg_spacing.py"), str(svg)]) if svg.exists() else {"valid": False, "errors": ["SVG missing"]}
    editable_result = (
        _run_json([
            sys.executable,
            str(script_dir / "verify_editable_pptx.py"),
            str(pptx),
            "--write-report",
            "--project",
            str(project),
        ])
        if pptx
        else {"valid": False, "errors": ["No exported PPTX found"]}
    )
    editability_score = editable_result.get("editable_score")
    stats = _svg_stats(svg)
    export_stats = _svg_stats(export_source_svg)
    paragraphs = stats.get("paragraphs", []) if isinstance(stats.get("paragraphs"), list) else []
    export_paragraphs = export_stats.get("paragraphs", []) if isinstance(export_stats.get("paragraphs"), list) else paragraphs
    pptx_text = _pptx_text_counts(pptx)
    export_strategy = _export_strategy(project, pptx, len(export_paragraphs))
    density = _layout_density(layout, export_stats, len(export_paragraphs))
    paragraph_warnings = _paragraph_warnings(density, len(export_paragraphs))

    def status(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    structure_ok = bool(contract_result.get("valid")) if use_rebuild2 else True
    planned_icons = int(stats.get("planned_icons", 0) or 0)
    layout_icons = 0
    if layout.exists():
        try:
            layout_data = json.loads(layout.read_text(encoding="utf-8"))
            icons = layout_data.get("icon_reconstruction", {}).get("icons", [])
            layout_icons = len(icons) if isinstance(icons, list) else 0
        except (OSError, json.JSONDecodeError):
            layout_icons = 0
    icon_coverage_ok = planned_icons >= layout_icons if layout_icons else True
    visual_ok = bool(visual_result.get("valid")) if use_rebuild2 else True
    overall_fail = not (
        bool(readiness_result.get("valid"))
        and structure_ok
        and icon_coverage_ok
        and bool(icon_result.get("valid"))
        and visual_ok
        and bool(editable_result.get("valid"))
    )

    def _flat_notes(result: dict) -> str:
        if result.get("results"):
            nested = result.get("results", [])
            if isinstance(nested, list):
                parts: list[str] = []
                for row in nested:
                    if isinstance(row, dict):
                        parts.extend(row.get("errors", []) or [])
                        parts.extend(row.get("warnings", []) or [])
                return "; ".join(str(item) for item in parts)
        return "; ".join(str(item) for item in (result.get("errors", []) or []))

    readiness_summary = readiness_result.get("summary", {}) if isinstance(readiness_result.get("summary"), dict) else {}
    workflow_label = "复刻流程2" if use_rebuild2 else "复刻流程"
    overall_status = "FAIL" if overall_fail else "PASS"
    layout_notes = "; ".join(layout_result.get("errors", []) + layout_result.get("warnings", []))
    icon_notes = "; ".join(icon_result.get("errors", []) + icon_result.get("warnings", []))
    contract_notes = "; ".join(contract_result.get("errors", []) + contract_result.get("warnings", []))
    visual_notes = "; ".join(visual_result.get("errors", []) + visual_result.get("warnings", []))
    mean_diff = visual_result.get("mean_diff")
    mean_threshold = visual_result.get("mean_threshold")
    visual_detail = ""
    if mean_diff is not None and mean_threshold is not None:
        visual_detail = f"mean_diff={mean_diff}, threshold={mean_threshold}"
    elif visual_notes:
        visual_detail = visual_notes
    else:
        visual_detail = "n/a"

    lines = [
        "# Rebuild QA Report",
        "",
        f"- Workflow: {workflow_label}",
        f"- Overall: **{overall_status}**",
        f"- Project: {project}",
        f"- SVG: {svg}",
        f"- Export source SVG: {export_source_svg}",
        f"- Preview render backend: {visual_result.get('render_backend', render_backend)}",
    ]
    lines.append(f"- PPTX: {pptx}" if pptx else "- PPTX: not found")
    manifest = {}
    manifest_path = project / "slide_image_rebuild_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
    layout_data: dict[str, Any] = {}
    if layout.exists():
        try:
            layout_data = json.loads(layout.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            layout_data = {}
    lines.extend(_intake_markdown(project, manifest if manifest else None))
    lines.extend(_crop_candidates_markdown(project, layout_data))
    lines.extend([
        "",
        "## Checks",
        "",
        "| Check | Status | Notes |",
        "|---|---|---|",
        (
            f"| Workflow readiness | {status(bool(readiness_result.get('valid')))} | "
            f"errors={readiness_summary.get('error_count')}, warnings={readiness_summary.get('warning_count')} |"
        ),
        f"| Layout reference | {status(bool(layout_result.get('valid')))} | {layout_notes} |",
        f"| Icon/text fit | {status(bool(icon_result.get('valid')))} | {icon_notes} |",
        f"| SVG spacing | {status(bool(spacing_result.get('valid')))} | {_flat_notes(spacing_result)} |",
        f"| Text fit | {status(bool(text_result.get('valid')))} | {_flat_notes(text_result)} |",
        (
            f"| PPTX editability | {status(bool(editable_result.get('valid')))} | "
            f"score={editability_score if editability_score is not None else 'n/a'}, "
            f"shapes={editable_result.get('shapes')}, text_shapes={editable_result.get('text_shapes')}, "
            f"full_slide_pictures={editable_result.get('full_slide_pictures')} |"
        ),
    ])
    if use_rebuild2:
        lines.extend([
            f"| Executor contract | {status(structure_ok)} | {contract_notes} |",
            f"| Icon marker coverage | {status(icon_coverage_ok)} | planned_in_svg={planned_icons}, planned_in_layout={layout_icons} |",
            f"| Reference visual similarity | {status(visual_ok)} | {visual_detail} |",
        ])
        if rms_result:
            rms_notes = f"rms={rms_result.get('rms')}, verdict={rms_result.get('verdict')}"
            rms_warnings = rms_result.get("warnings", [])
            if isinstance(rms_warnings, list) and rms_warnings:
                rms_notes = f"{rms_notes}; {_flat_notes(rms_result)}"
            lines.append(
                f"| Reference RMS fallback | {status(bool(rms_result.get('valid')))} | {rms_notes} |"
            )
    lines.append("")
    lines.append("## Paragraph / Export Strategy")
    lines.append("")
    lines.append(f"- Strategy: {export_strategy.get('status')}")
    lines.append(f"- Latest trace uses --merge-paragraphs: {export_strategy.get('merge_paragraphs')}")
    lines.append(f"- Latest trace flattened positional tspans: {export_strategy.get('flattened_positional_tspans')}")
    lines.append(f"- Latest traced SVG source: {export_strategy.get('source') or ''}")
    lines.append(f"- Export-source paragraph blocks: {len(export_paragraphs)}")
    lines.append(f"- PPTX text bodies: {pptx_text.get('tx_body') or 0}")
    lines.append(f"- PPTX text runs: {pptx_text.get('runs') or 0}")
    for item in export_paragraphs[:12]:
        lines.append(
            f"- Paragraph {item.get('label')}: lines={item.get('lines')}, line_height={item.get('line_height')}"
        )
    for warning in export_strategy.get("warnings", []):
        lines.append(f"- Warning: {warning}")
    for warning in paragraph_warnings:
        lines.append(f"- Warning: {warning}")
    lines.append("")
    lines.append("## Dense Rebuild Mode")
    lines.append("")
    lines.append(f"- Enabled: {density.get('enabled')}")
    lines.append(f"- Zones: {density.get('zone_count')}")
    lines.append(f"- SVG text elements: {density.get('svg_text_elements')}")
    lines.append(f"- SVG text characters: {density.get('svg_text_chars')}")
    lines.append(f"- Paragraph blocks: {density.get('paragraph_blocks')}")
    lines.append(
        "- Dense rule: prioritize readable/editable text; simplify or omit repeated low-value micro-icons before shrinking line spacing."
    )
    lines.append("")
    lines.append("## SVG Signals")
    lines.append("")
    lines.append(f"- Text elements: {stats.get('text') or 0}")
    lines.append(f"- Image elements: {stats.get('images') or 0}")
    lines.append(f"- Repository icon placeholders remaining: {stats.get('library_icons') or 0}")
    lines.append(f"- Planned semantic icons found: {stats.get('planned_icons') or 0}")
    lines.append("")
    lines.append("## Manual Review Prompts")
    lines.append("")
    lines.append("- Check whether key titles are complete and not clipped.")
    lines.append("- Check whether icon scale and position feel paired with nearby text.")
    lines.append("- Check whether repeated icons are intentional by semantic level.")
    lines.append("- Check whether card edges, dividers, and bottom bands have enough breathing room.")
    if rms_result:
        lines.append(
            "- Reference RMS fallback is Pillow-only QA; it does not replace verify_reference_similarity --render."
        )
    crop_summary = summarize_crop_candidates(layout_data, project=project) if layout_data else None
    if crop_summary and crop_summary.needs_review_count > 0:
        ids = ", ".join(crop_summary.ids_needing_review) or "(unnamed)"
        lines.append(f"- Confirm crop_candidates marked needs_review before export: {ids}.")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate qa_report.md for a rebuilt PPT project.")
    parser.add_argument("project_path", type=Path)
    parser.add_argument("--rebuild2", action="store_true", help="复刻流程2 QA (executor contract + strict icons)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = args.project_path / "qa_report.md"
    out.write_text(build_report(args.project_path, rebuild2=args.rebuild2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
