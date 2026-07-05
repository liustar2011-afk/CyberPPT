#!/usr/bin/env python3
"""
PPT Master - SVG Text Fit Verifier

Checks text elements for likely overflow. Elements can opt into explicit fit
boxes with data-fit-width / data-fit-height attributes. Without explicit boxes,
the script still flags text close to or beyond the canvas edge.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from layout_reference_components import cjk_text_width
from text_fit_report_lib import report_path_for, upsert_svg_checks

REPORT_VERSION = "1.0"

SVG_NS = "{http://www.w3.org/2000/svg}"

# data-fit-status severity, mirrors text_fit_cn.DEFAULT_GATE_SEVERITY (修订版 §十一).
STATUS_SEVERITY: dict[str, str] = {
    "fit": "ok",
    "fit_at_min_font": "warning",
    "compressed_line_height": "warning",
    "truncated": "error",
    "overflow": "error",
    "invalid_box": "error",
    "protected_term_split": "error",
    "punctuation_violation": "warning",
}


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox") or root.get("viewbox")
    if raw:
        parts = [float(part) for part in re.split(r"[\s,]+", raw.strip()) if part]
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
    return 0, 0, _float(root.get("width")) or 1280, _float(root.get("height")) or 720


def _text(elem: ET.Element) -> str:
    return "".join(elem.itertext()).strip()


def _visual_lines(elem: ET.Element) -> list[str]:
    tspans = [child for child in list(elem) if _strip_ns(child.tag) == "tspan"]
    if not tspans:
        return [_text(elem)]
    lines = []
    for child in tspans:
        line = "".join(child.itertext()).strip()
        if line:
            lines.append(line)
    return lines or [_text(elem)]


def _find_svgs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() == ".svg":
        return [target]
    final_files = sorted((target / "svg_final").glob("*.svg")) if (target / "svg_final").is_dir() else []
    if final_files:
        return final_files
    if (target / "svg_output").is_dir():
        return sorted((target / "svg_output").glob("*.svg"))
    return sorted(target.glob("*.svg"))


def inspect(svg_path: Path, *, edge_margin: float = 4) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    root = ET.parse(svg_path).getroot()
    vx, vy, vw, vh = _viewbox(root)
    max_x = vx + vw
    max_y = vy + vh

    checked = 0
    fit_checked = 0
    fit_ids: list[str] = []
    for elem in root.iter():
        if _strip_ns(elem.tag) != "text":
            continue
        lines = _visual_lines(elem)
        if not lines:
            continue
        checked += 1
        fit_id = elem.get("data-fit-id")
        fit_status = elem.get("data-fit-status")
        if fit_id:
            fit_ids.append(fit_id)
        if fit_status:
            severity = STATUS_SEVERITY.get(fit_status, "warning")
            tag = fit_id or elem.get("data-fit-label") or lines[0][:24]
            if severity == "error":
                errors.append(f"{tag}: fit status '{fit_status}'")
            elif severity == "warning":
                warnings.append(f"{tag}: fit status '{fit_status}'")
        x = _float(elem.get("x"))
        y = _float(elem.get("y"))
        size = _float(elem.get("font-size")) or 16
        if x is None or y is None:
            continue
        approx_w = max(cjk_text_width(line, size) for line in lines)
        line_height = _float(elem.get("data-paragraph-line-height")) or size * 1.3
        approx_h = line_height * (len(lines) - 1) + size * 1.3
        anchor = elem.get("text-anchor", "start")
        if anchor == "middle":
            x1 = x - approx_w / 2
            x2 = x + approx_w / 2
        elif anchor == "end":
            x1 = x - approx_w
            x2 = x
        else:
            x1 = x
            x2 = x + approx_w
        y1 = y - size
        y2 = y + size * 0.3

        label = elem.get("data-fit-label") or lines[0][:24]
        fit_width = _float(elem.get("data-fit-width"))
        fit_height = _float(elem.get("data-fit-height"))
        fit_center_y = _float(elem.get("data-fit-center-y"))
        if fit_width is not None:
            fit_checked += 1
            if approx_w > fit_width:
                errors.append(f"{label}: text width {approx_w:.1f}px exceeds fit width {fit_width:.1f}px")
        if fit_height is not None and approx_h > fit_height:
            errors.append(f"{label}: text height {approx_h:.1f}px exceeds fit height {fit_height:.1f}px")
        if fit_center_y is not None:
            fit_checked += 1
            text_center_y = y - size + approx_h / 2
            tolerance = max(3.0, min(size * 0.35, 6.0))
            if abs(text_center_y - fit_center_y) > tolerance:
                errors.append(
                    f"{label}: text vertical center {text_center_y:.1f}px "
                    f"deviates from fit center {fit_center_y:.1f}px"
                )

        if x1 < vx - edge_margin or x2 > max_x + edge_margin or y1 < vy - edge_margin or y2 > max_y + edge_margin:
            errors.append(f"{label}: text appears outside canvas bounds")
        elif x1 < vx + edge_margin or x2 > max_x - edge_margin or y1 < vy + edge_margin or y2 > max_y - edge_margin:
            warnings.append(f"{label}: text is close to canvas edge")

    return {
        "path": str(svg_path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "text_elements": checked,
        "fit_checked": fit_checked,
        "fit_ids": fit_ids,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def cross_check_report(report_path: Path, svg_fit_ids: set[str]) -> dict[str, Any]:
    """Cross-check engine report (修订版 §十一) against fit_ids found in SVGs.

    Reads an engine-produced text_fit_report.json with top-level ``items``
    (fit_id level). Flags: SVG fit_ids missing from the report (unreported)
    and reported fit_ids whose status fails the gate.
    """
    errors: list[str] = []
    warnings: list[str] = []
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"errors": [], "warnings": [f"report unreadable: {report_path}"], "checked": False}

    items = payload.get("items")
    if not isinstance(items, list):
        # Not an engine report (e.g. the per-svg report this script writes) — skip.
        return {"errors": [], "warnings": [], "checked": False}

    reported_ids = {str(item.get("fit_id")) for item in items if item.get("fit_id")}
    for fid in sorted(svg_fit_ids - reported_ids):
        errors.append(f"{fid}: present in SVG but missing from text_fit_report.json")
    for item in items:
        fid = str(item.get("fit_id", ""))
        status = str(item.get("status", ""))
        severity = STATUS_SEVERITY.get(status, "warning")
        if severity == "error":
            errors.append(f"{fid}: report status '{status}'")
        elif severity == "warning" and status:
            warnings.append(f"{fid}: report status '{status}'")
    return {"errors": errors, "warnings": warnings, "checked": True}


def build_text_fit_report(target: Path, results: list[dict[str, Any]]) -> dict[str, Any]:
    project = target if target.is_dir() else target.parent
    return {
        "workflow": "slide-image-rebuild",
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "project": str(project.resolve()),
        "valid": all(result.get("valid") for result in results),
        "count": len(results),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SVG text fit.")
    parser.add_argument("target", type=Path, help="Project directory or SVG file")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write exports/qa/text_fit_report.json when target is a project directory",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Engine text_fit_report.json to cross-check (default: <project>/exports/qa/text_fit_report.json)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    svgs = _find_svgs(args.target)
    if not svgs:
        print(json.dumps({"valid": False, "errors": ["No SVG files found"]}, ensure_ascii=False, indent=2))
        return 1
    results = [inspect(svg) for svg in svgs]
    payload = build_text_fit_report(args.target, results)

    # Cross-check against any pre-existing engine report (read BEFORE we overwrite).
    project = args.target if args.target.is_dir() else args.target.parent
    report_path = args.report or report_path_for(project)
    cross: dict[str, Any] | None = None
    if report_path.is_file():
        svg_fit_ids = {fid for r in results for fid in r.get("fit_ids", [])}
        cross = cross_check_report(report_path, svg_fit_ids)
        if cross["checked"]:
            payload["cross_check"] = cross
            if cross["errors"]:
                payload["valid"] = False

    if args.write_report and args.target.is_dir():
        # Merge svg_checks into the canonical report; preserve engine items.
        written = upsert_svg_checks(args.target.resolve(), results, cross if cross and cross.get("checked") else None)
        payload["report_path"] = str(written.relative_to(args.target.resolve()))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
