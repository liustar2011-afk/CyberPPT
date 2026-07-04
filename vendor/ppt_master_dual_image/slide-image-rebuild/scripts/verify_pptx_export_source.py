#!/usr/bin/env python3
"""
PPT Master - PPTX Export Source Verifier

Confirm exported PPTX came from the SVG finalize path with trace and compatibility
artifacts present. Blocks full-slide raster bypass exports.

Usage:
    python3 scripts/verify_pptx_export_source.py <project_path>
    python3 scripts/verify_pptx_export_source.py <project_path> --strict --write-report

Examples:
    python3 scripts/verify_pptx_export_source.py projects/demo --strict

Dependencies:
    python-pptx (optional shape counts); stdlib zip/xml for package checks
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

try:
    from pptx import Presentation
except ImportError:  # pragma: no cover
    Presentation = None  # type: ignore[misc, assignment]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _is_snapshot_mode(project: Path) -> bool:
    """text-editable-snapshot deliberately exports one full-slide background
    picture (the approved non-editable underlay) -- exempt it from the
    full-slide-raster-bypass guard meant for vector-hifi exports."""
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    if not manifest:
        return False
    try:
        from rebuild_quality_mode import resolve_rebuild_modes
    except ImportError:  # pragma: no cover
        from scripts.rebuild_quality_mode import resolve_rebuild_modes  # type: ignore
    resolved = resolve_rebuild_modes(manifest)
    rebuild_mode = resolved.rebuild_mode or manifest.get("rebuild_mode")
    return rebuild_mode == "text-editable-snapshot"


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_conversion_trace(project: Path, pptx: Path) -> Path | None:
    canonical = project / "exports" / "pptx" / "conversion_trace.json"
    if canonical.is_file():
        return canonical
    legacy = pptx.with_name(pptx.name + ".trace.json")
    if legacy.is_file():
        return legacy
    return None


def _pptx_picture_stats(pptx: Path) -> dict[str, Any]:
    stats = {
        "picture_count": 0,
        "full_slide_picture_count": 0,
        "shape_count": 0,
        "text_frame_count": 0,
    }
    if Presentation is None:
        stats["warning"] = "python-pptx unavailable; shape counts skipped."
        return stats
    try:
        prs = Presentation(str(pptx))
    except (OSError, ValueError) as exc:
        stats["error"] = str(exc)
        return stats
    slide_w = int(prs.slide_width)
    slide_h = int(prs.slide_height)
    stats["slide_width_emu"] = slide_w
    stats["slide_height_emu"] = slide_h
    for slide in prs.slides:
        for shape in slide.shapes:
            stats["shape_count"] += 1
            if shape.has_text_frame:
                stats["text_frame_count"] += 1
            if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                stats["picture_count"] += 1
                try:
                    if shape.width >= slide_w * 0.9 and shape.height >= slide_h * 0.9:
                        stats["full_slide_picture_count"] += 1
                except AttributeError:
                    pass
    return stats


def verify_project(
    project: Path,
    *,
    pptx_path: Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    svg_final = project / "svg_final"
    if not svg_final.is_dir() or not any(svg_final.glob("*.svg")):
        errors.append({
            "level": "error",
            "code": "missing_svg_final",
            "message": "svg_final/ must exist with at least one SVG page before export verification.",
            "path": str(svg_final),
        })

    pptx = pptx_path or _latest_pptx(project)
    if pptx is None or not pptx.is_file():
        errors.append({
            "level": "error",
            "code": "missing_exported_pptx",
            "message": "No exported PPTX found under exports/.",
            "path": str(project / "exports"),
        })
        pptx = pptx or (project / "exports" / "missing.pptx")

    compat_path = pptx.with_name(pptx.name + ".compat_report.json")
    compat = _load_json(compat_path)
    if not compat:
        errors.append({
            "level": "error",
            "code": "missing_compat_report",
            "message": "PPTX compatibility report missing; export with svg_to_pptx.py sanitizer enabled.",
            "path": str(compat_path),
        })
    elif compat.get("valid") is False:
        errors.append({
            "level": "error",
            "code": "invalid_compat_report",
            "message": "PPTX compatibility report is not valid.",
            "path": str(compat_path),
        })

    trace_path = _find_conversion_trace(project, pptx)
    trace = _load_json(trace_path) if trace_path else {}
    if strict and not trace:
        errors.append({
            "level": "error",
            "code": "missing_conversion_trace",
            "message": "conversion trace missing; export with svg_to_pptx.py --conversion-trace.",
            "path": str(project / "exports" / "pptx" / "conversion_trace.json"),
        })

    svg_sources: list[dict[str, Any]] = []
    if svg_final.is_dir():
        for svg in sorted(svg_final.glob("*.svg")):
            svg_sources.append({
                "path": str(svg.relative_to(project)),
                "sha256": _sha256(svg),
            })

    picture_stats = _pptx_picture_stats(pptx) if pptx.is_file() else {}
    if picture_stats.get("full_slide_picture_count", 0) > 0 and not _is_snapshot_mode(project):
        errors.append({
            "level": "error",
            "code": "full_slide_picture_present",
            "message": f"PPTX contains {picture_stats['full_slide_picture_count']} full-slide picture(s).",
            "path": str(pptx),
        })

    declared_pictures = trace.get("picture_count")
    if strict and isinstance(declared_pictures, int) and picture_stats.get("picture_count", 0) > declared_pictures:
        errors.append({
            "level": "error",
            "code": "picture_count_exceeds_trace",
            "message": (
                f"PPTX picture_count {picture_stats.get('picture_count')} exceeds "
                f"conversion trace declaration {declared_pictures}."
            ),
            "path": str(pptx),
        })

    declared_shapes = trace.get("shape_count")
    if strict and isinstance(declared_shapes, int) and picture_stats.get("shape_count", 0) < declared_shapes:
        warnings.append({
            "level": "warning",
            "code": "shape_count_below_trace",
            "message": (
                f"PPTX shape_count {picture_stats.get('shape_count')} is below "
                f"conversion trace declaration {declared_shapes}."
            ),
            "path": str(pptx),
        })

    try:
        with ZipFile(pptx) as package:
            bad_xml = 0
            for name in package.namelist():
                if name.endswith(".xml") or name.endswith(".rels"):
                    try:
                        package.read(name)
                    except BadZipFile:
                        bad_xml += 1
            if bad_xml:
                errors.append({
                    "level": "error",
                    "code": "pptx_package_read_failed",
                    "message": f"PPTX package has {bad_xml} unreadable XML entries.",
                    "path": str(pptx),
                })
    except (OSError, BadZipFile) as exc:
        errors.append({
            "level": "error",
            "code": "pptx_open_failed",
            "message": str(exc),
            "path": str(pptx),
        })

    return {
        "workflow": "slide-image-rebuild",
        "check": "pptx_export_source",
        "project": str(project),
        "valid": not errors,
        "strict": strict,
        "exported_pptx": str(pptx) if pptx.is_file() else "",
        "svg_final": svg_sources,
        "conversion_trace": str(trace_path.relative_to(project)) if trace_path else "",
        "compat_report": str(compat_path.relative_to(project)) if compat_path.is_file() else "",
        "picture_stats": picture_stats,
        "trace_summary": {
            "output": trace.get("output"),
            "slide_count": trace.get("slide_count"),
            "export_mode": trace.get("export_mode"),
            "source_svg_sha256": trace.get("source_svg_sha256"),
        },
        "errors": errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify PPTX export source and package artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--pptx", type=Path, help="Explicit exported PPTX path")
    parser.add_argument("--strict", action="store_true", help="Require conversion trace and stricter picture checks")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write exports/qa/export_source_report.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project_path.resolve()
    if not project.is_dir():
        payload = {"valid": False, "errors": [{"code": "missing_project", "message": f"Not found: {project}"}]}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    payload = verify_project(
        project,
        pptx_path=args.pptx.resolve() if args.pptx else None,
        strict=args.strict,
    )
    if args.write_report:
        report_path = project / "exports" / "qa" / "export_source_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_path"] = str(report_path.relative_to(project))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
