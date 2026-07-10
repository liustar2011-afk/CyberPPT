#!/usr/bin/env python3
"""
PPT Master - Editable PPTX Verifier

Run generic PPTX package and editability checks. Use this for projects without
brand/master chrome, or alongside verify_pptx_chrome.py for branded decks.

Usage:
    python3 scripts/verify_editable_pptx.py <exported.pptx>

Examples:
    python3 scripts/verify_editable_pptx.py projects/demo/exports/demo.pptx

Dependencies:
    python-pptx
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

try:
    from pptx import Presentation
except ImportError as exc:  # pragma: no cover - user environment issue
    raise SystemExit("python-pptx is required. Install project requirements first.") from exc


EMU_PER_INCH = 914400
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
SP = f"{{{P_NS}}}sp"
SP_PR = f"{{{P_NS}}}spPr"
XFRM = f"{{{A_NS}}}xfrm"
EXT = f"{{{A_NS}}}ext"
PRST_GEOM = f"{{{A_NS}}}prstGeom"


def _xml_errors(path: Path) -> list[str]:
    errors: list[str] = []
    with ZipFile(path) as package:
        for name in package.namelist():
            if not name.endswith((".xml", ".rels")):
                continue
            try:
                ET.fromstring(package.read(name))
            except ET.ParseError as exc:
                errors.append(f"{name}: {exc}")
    return errors


def _powerpoint_line_extent_errors(path: Path) -> list[str]:
    errors: list[str] = []
    with ZipFile(path) as package:
        for name in package.namelist():
            if not (name.startswith("ppt/") and name.endswith(".xml")):
                continue
            try:
                root = ET.fromstring(package.read(name))
            except ET.ParseError:
                continue
            bad_count = 0
            for shape in root.iter(SP):
                sp_pr = shape.find(SP_PR)
                if sp_pr is None:
                    continue
                geom = sp_pr.find(PRST_GEOM)
                if geom is None or geom.get("prst") != "line":
                    continue
                xfrm = sp_pr.find(XFRM)
                ext = xfrm.find(EXT) if xfrm is not None else None
                if ext is None:
                    continue
                try:
                    cx = int(ext.get("cx", "0"))
                    cy = int(ext.get("cy", "0"))
                except ValueError:
                    bad_count += 1
                    continue
                if cx <= 0 or cy <= 0:
                    bad_count += 1
            if bad_count:
                errors.append(
                    f"{name}: {bad_count} preset line shape(s) have non-positive a:ext cx/cy; run sanitize_pptx_package.py for PowerPoint compatibility"
                )
    return errors


def _is_snapshot_mode(project: Path | None) -> bool:
    """text-editable-snapshot deliberately exports one full-slide background
    picture (the approved non-editable underlay, see image_crops_manifest.json
    / manifest.user_acceptance) -- it shouldn't trip the generic "deck is
    flattened" full-slide-picture check that exists for vector-hifi exports."""
    if project is None:
        return False
    manifest_path = project / "slide_image_rebuild_manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    try:
        from rebuild_quality_mode import resolve_rebuild_modes
    except ImportError:  # pragma: no cover
        from scripts.rebuild_quality_mode import resolve_rebuild_modes  # type: ignore
    resolved = resolve_rebuild_modes(manifest)
    rebuild_mode = resolved.rebuild_mode or manifest.get("rebuild_mode")
    return rebuild_mode == "text-editable-snapshot"


def inspect_pptx(path: Path, *, snapshot_mode: bool = False) -> dict[str, object]:
    prs = Presentation(str(path))
    slide_count = len(prs.slides)
    shape_count = 0
    text_shape_count = 0
    picture_count = 0
    full_slide_picture_count = 0
    sample_text: list[str] = []
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    def visit_shape(shape) -> None:
        nonlocal shape_count, text_shape_count, picture_count, full_slide_picture_count
        shape_count += 1
        if getattr(shape, "shape_type", None) == 13:
            picture_count += 1
            if (
                abs(shape.left) < EMU_PER_INCH * 0.05
                and abs(shape.top) < EMU_PER_INCH * 0.05
                and shape.width >= slide_w * 0.95
                and shape.height >= slide_h * 0.95
            ):
                full_slide_picture_count += 1
        if hasattr(shape, "text") and shape.text.strip():
            text_shape_count += 1
            if len(sample_text) < 12:
                sample_text.append(shape.text.strip())
        child_shapes = getattr(shape, "shapes", None)
        if child_shapes is not None:
            for child in child_shapes:
                visit_shape(child)

    for slide in prs.slides:
        for shape in slide.shapes:
            visit_shape(shape)

    xml_errors = _xml_errors(path)
    powerpoint_line_errors = _powerpoint_line_extent_errors(path)
    errors: list[str] = []
    warnings: list[str] = []
    if xml_errors:
        errors.extend(xml_errors)
    if powerpoint_line_errors:
        errors.extend(powerpoint_line_errors)
    if slide_count == 0:
        errors.append("PPTX has no slides")
    if shape_count == 0:
        errors.append("PPTX has no shapes")
    if text_shape_count == 0:
        errors.append("PPTX has no editable text shapes")
    if full_slide_picture_count and not snapshot_mode:
        errors.append(f"Detected {full_slide_picture_count} full-slide picture shape(s)")
    if picture_count and picture_count == shape_count:
        errors.append("All slide shapes are pictures; deck is likely flattened")
    if picture_count:
        warnings.append(f"Picture shapes present: {picture_count}")

    payload = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "slides": slide_count,
        "shapes": shape_count,
        "text_shapes": text_shape_count,
        "pictures": picture_count,
        "full_slide_pictures": full_slide_picture_count,
        "sample_text": sample_text,
    }
    payload.update(score_editability(payload))
    return payload


EDITABILITY_WEIGHTS = {
    "text": 0.35,
    "shape": 0.25,
    "picture_penalty": 0.20,
    "icon": 0.10,
    "compat": 0.10,
}


def score_editability(inspect: dict[str, object]) -> dict[str, object]:
    """Derive a weighted editability score from inspect_pptx() output."""
    shapes = int(inspect.get("shapes") or 0)
    text_shapes = int(inspect.get("text_shapes") or 0)
    pictures = int(inspect.get("pictures") or 0)
    full_slide = int(inspect.get("full_slide_pictures") or 0)
    valid = bool(inspect.get("valid"))

    native_shapes = max(0, shapes - pictures)
    native_shape_ratio = round(native_shapes / shapes, 4) if shapes else 0.0
    text_as_image_heuristic = pictures > 0 and text_shapes == 0
    full_slide_image_detected = full_slide > 0

    text_component = 1.0 if text_shapes >= 3 else (text_shapes / 3.0 if text_shapes else 0.0)
    shape_component = native_shape_ratio
    if pictures == 0:
        picture_component = 1.0
    else:
        picture_component = max(0.0, 1.0 - pictures / max(1, shapes))
    icon_component = 1.0 if native_shape_ratio >= 0.5 else min(1.0, native_shape_ratio * 2.0)
    compat_component = 1.0 if valid else 0.0

    if full_slide_image_detected or text_as_image_heuristic:
        picture_component = 0.0
        text_component *= 0.5

    editable_score = round(
        EDITABILITY_WEIGHTS["text"] * text_component
        + EDITABILITY_WEIGHTS["shape"] * shape_component
        + EDITABILITY_WEIGHTS["picture_penalty"] * picture_component
        + EDITABILITY_WEIGHTS["icon"] * icon_component
        + EDITABILITY_WEIGHTS["compat"] * compat_component,
        4,
    )

    return {
        "editable_score": editable_score,
        "text_frame_count": text_shapes,
        "shape_count": shapes,
        "picture_count": pictures,
        "full_slide_image_detected": full_slide_image_detected,
        "text_as_image_heuristic": text_as_image_heuristic,
        "native_shape_ratio": native_shape_ratio,
        "weights": dict(EDITABILITY_WEIGHTS),
    }


def write_editability_report(project: Path, inspect: dict[str, object], *, pptx_path: Path | None = None) -> Path:
    out_dir = project / "exports" / "qa"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "workflow": "slide-image-rebuild",
        "version": "1.0",
        "pptx": str(pptx_path) if pptx_path else None,
        **inspect,
    }
    out = out_dir / "editability_score.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify generic PPTX openability and editability.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Path to exported PPTX")
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="When set with --write-report, write exports/qa/editability_score.json under this project",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write exports/qa/editability_score.json (requires --project)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = inspect_pptx(args.path, snapshot_mode=_is_snapshot_mode(args.project))
    if args.write_report:
        if args.project is None:
            result["errors"] = [*result.get("errors", []), "--write-report requires --project"]
            result["valid"] = False
        else:
            report_path = write_editability_report(args.project.resolve(), result, pptx_path=args.path.resolve())
            result["editability_report"] = str(report_path.relative_to(args.project.resolve()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
