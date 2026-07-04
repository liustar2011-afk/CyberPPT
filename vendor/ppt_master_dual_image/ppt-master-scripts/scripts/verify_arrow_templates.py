#!/usr/bin/env python3
"""
PPT Master - Verify Arrow Templates

Validate the reusable arrow template library for SVG/PPTX compatibility.

Usage:
    python3 skills/ppt-master/scripts/verify_arrow_templates.py
    python3 skills/ppt-master/scripts/verify_arrow_templates.py --root skills/ppt-master/templates/arrows

Examples:
    python3 skills/ppt-master/scripts/verify_arrow_templates.py --json

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SVG_NS = "http://www.w3.org/2000/svg"
BANNED_TAGS = {
    "animate",
    "animateMotion",
    "animateTransform",
    "foreignObject",
    "iframe",
    "script",
    "set",
    "style",
    "symbol",
}
BANNED_ATTRS = {"class", "mask"}
ALLOWED_MARKER_SHAPES = {"triangle", "diamond", "oval"}
POINT_RE = re.compile(r"[MLml]\s*(-?\d+(?:\.\d+)?)\s*[,\s]\s*(-?\d+(?:\.\d+)?)")
POLY_POINT_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*[,\s]\s*(-?\d+(?:\.\d+)?)")


def _tag(elem: ET.Element) -> str:
    return elem.tag.rsplit("}", 1)[-1]


def _points_from_path(d: str) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for x, y in POINT_RE.findall(d)]


def _points_from_polygon(points: str) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for x, y in POLY_POINT_RE.findall(points)]


def _is_right_facing_triangle(points: list[tuple[float, float]]) -> bool:
    if len(points) != 3:
        return False
    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    base_points = [(x, y) for x, y in points if abs(x - min_x) < 0.001]
    tip_points = [(x, y) for x, y in points if abs(x - max_x) < 0.001]
    if len(base_points) != 2 or len(tip_points) != 1:
        return False
    base_y_values = sorted(y for _, y in base_points)
    tip_y = tip_points[0][1]
    return base_y_values[0] <= tip_y <= base_y_values[1]


def _is_triangle(points: list[tuple[float, float]]) -> bool:
    if len(points) != 3:
        return False
    unique_points = {(round(x, 3), round(y, 3)) for x, y in points}
    if len(unique_points) != 3:
        return False
    return (max(x for x, _ in points) - min(x for x, _ in points)) > 0 and (
        max(y for _, y in points) - min(y for _, y in points)
    ) > 0


def _has_inline_arrowhead(root: ET.Element) -> bool:
    for elem in root.iter():
        tag = _tag(elem)
        if tag in {"polygon", "polyline"} and _is_triangle(_points_from_polygon(elem.get("points", ""))):
            return True
        if tag == "path":
            d = elem.get("d", "")
            if re.search(r"[Zz]\s*$", d.strip()) and _is_triangle(_points_from_path(d)):
                return True
    return False


def _classify_marker(marker: ET.Element) -> str | None:
    orient = marker.get("orient")
    if orient != "auto":
        return None

    for child in marker:
        tag = _tag(child)
        if tag in {"circle", "ellipse"}:
            return "oval"
        if tag == "path":
            d = child.get("d", "")
            points = _points_from_path(d)
            closed = bool(re.search(r"[Zz]\s*$", d.strip()))
            if len(points) == 3 and closed:
                return "triangle" if _is_right_facing_triangle(points) else "triangle_wrong_direction"
            if len(points) == 4 and closed:
                return "diamond"
        if tag in {"polygon", "polyline"}:
            points = _points_from_polygon(child.get("points", ""))
            if len(points) == 3:
                return "triangle" if _is_right_facing_triangle(points) else "triangle_wrong_direction"
            if len(points) == 4:
                return "diamond"
    return None


def _marker_refs(elem: ET.Element) -> list[str]:
    refs = []
    for attr in ("marker-start", "marker-end"):
        value = elem.get(attr)
        if not value or value == "none":
            continue
        match = re.fullmatch(r"url\(#([^)]+)\)", value.strip())
        refs.append(match.group(1) if match else value)
    return refs


def validate_svg(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"{path}: invalid XML: {exc}"]

    if _tag(root) != "svg":
        errors.append(f"{path}: root element is not <svg>")
    if root.get("viewBox") != "0 0 1280 720":
        errors.append(f"{path}: viewBox must be 0 0 1280 720")

    markers: dict[str, ET.Element] = {}
    for elem in root.iter():
        tag = _tag(elem)
        if tag in BANNED_TAGS:
            errors.append(f"{path}: banned tag <{tag}>")
        for attr in elem.attrib:
            if attr in BANNED_ATTRS or attr.startswith("on"):
                errors.append(f"{path}: banned attribute {attr}")
        if tag == "marker":
            marker_id = elem.get("id")
            if marker_id:
                markers[marker_id] = elem

    used_refs: set[str] = set()
    for elem in root.iter():
        tag = _tag(elem)
        refs = _marker_refs(elem)
        if refs and tag not in {"line", "path"}:
            errors.append(f"{path}: markers are only allowed on <line> or <path>, found <{tag}>")
        for ref in refs:
            used_refs.add(ref)
            marker = markers.get(ref)
            if marker is None:
                errors.append(f"{path}: marker reference {ref!r} is not defined")
                continue
            shape = _classify_marker(marker)
            if shape == "triangle_wrong_direction":
                errors.append(
                    f"{path}: marker {ref!r} triangle must be canonical right-facing "
                    "geometry so orient='auto' rotates it correctly"
                )
                continue
            if shape not in ALLOWED_MARKER_SHAPES:
                errors.append(
                    f"{path}: marker {ref!r} is not a supported triangle, diamond, or oval marker"
                )

    if not used_refs and "connector" in path.stem and not _has_inline_arrowhead(root):
        errors.append(f"{path}: connector template must demonstrate at least one marker or inline arrowhead")
    return errors


def load_index(root: Path) -> dict[str, Any]:
    index_path = root / "arrows_index.json"
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Missing {index_path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {index_path}: {exc}") from None


def validate_library(root: Path) -> dict[str, Any]:
    index = load_index(root)
    arrows = index.get("arrows")
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(arrows, dict):
        return {"valid": False, "errors": ["arrows_index.json must contain an arrows object"], "warnings": []}

    indexed = set(arrows)
    files = {path.stem for path in root.glob("*.svg")}

    missing_files = sorted(indexed - files)
    unindexed_files = sorted(files - indexed)
    for key in missing_files:
        errors.append(f"index entry {key!r} has no matching SVG file")
    for key in unindexed_files:
        warnings.append(f"SVG file {key!r} is not listed in arrows_index.json")

    expected_total = len(indexed)
    actual_total = index.get("meta", {}).get("total")
    if actual_total != expected_total:
        errors.append(f"meta.total is {actual_total!r}, expected {expected_total}")

    for key, item in arrows.items():
        summary = item.get("summary") if isinstance(item, dict) else None
        if not isinstance(summary, str) or "Pick for " not in summary or "Skip" not in summary:
            errors.append(f"index entry {key!r} summary must follow 'Pick for ... Skip ...'")

    for svg in sorted(root.glob("*.svg")):
        errors.extend(validate_svg(svg))

    return {
        "valid": not errors,
        "root": str(root),
        "checked": len(files),
        "errors": errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate PPT Master arrow template SVGs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    default_root = Path(__file__).resolve().parents[1] / "templates" / "arrows"
    parser.add_argument("--root", type=Path, default=default_root, help="Arrow template directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = validate_library(args.root.resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if report["valid"] else "FAIL"
        print(f"{status}: checked {report.get('checked', 0)} arrow templates")
        for warning in report.get("warnings", []):
            print(f"warning: {warning}")
        for error in report.get("errors", []):
            print(f"error: {error}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
