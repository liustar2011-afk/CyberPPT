#!/usr/bin/env python3
"""
Geometry lock helpers for slide-image-rebuild export hard constraints.

geometry_locks[] in layout_reference.json records measured coordinates and style
targets that must survive into rebuilt SVG before export.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from reference_object_similarity_lib import canvas_size, resolve_bbox_px
from svg_page_discovery import find_page_svg

SVG_NS = "{http://www.w3.org/2000/svg}"
REPORT_VERSION = "1.0"

ALLOWED_KINDS = frozenset({
    "horizontal_edge",
    "box",
    "arrow",
    "path",
    "footer_bar",
    "title_rule",
})

ALLOWED_SELECTORS = frozenset({
    "data-geometry-lock-id",
    "data-zone-id",
    "data-primitive",
    "data-chain-connector",
})


@dataclass(frozen=True)
class Thresholds:
    position_px: float = 3.0
    size_px: float = 4.0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


try:  # shared helper; see scripts/json_io.py
    from json_io import load_json
except ImportError:  # pragma: no cover - package-context import
    from scripts.json_io import load_json  # type: ignore


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def validate_geometry_lock(lock: dict[str, Any], *, index: int = 0) -> list[str]:
    errors: list[str] = []
    prefix = f"geometry_locks[{index}]"
    lock_id = lock.get("id")
    if not isinstance(lock_id, str) or not lock_id.strip():
        errors.append(f"{prefix}.id must be a non-empty string.")
    kind = lock.get("kind")
    if kind not in ALLOWED_KINDS:
        errors.append(f"{prefix}.kind must be one of: {', '.join(sorted(ALLOWED_KINDS))}.")
    selector = lock.get("svg_selector")
    if not isinstance(selector, dict):
        errors.append(f"{prefix}.svg_selector must be an object.")
    else:
        if not selector:
            errors.append(f"{prefix}.svg_selector must name at least one SVG marker attribute.")
        for key in selector:
            if key not in ALLOWED_SELECTORS:
                errors.append(f"{prefix}.svg_selector key `{key}` is not allowed.")
    has_bbox = isinstance(lock.get("bbox_px"), list) and len(lock["bbox_px"]) >= 4
    has_y = isinstance(lock.get("y_px"), (int, float))
    if kind == "horizontal_edge" and not has_y and not has_bbox:
        errors.append(f"{prefix} horizontal_edge requires y_px or bbox_px.")
    if kind in {"box", "footer_bar", "arrow", "path", "title_rule"} and not has_bbox:
        errors.append(f"{prefix} {kind} requires bbox_px.")
    if "blocking" in lock and lock.get("blocking") not in {True, False}:
        errors.append(f"{prefix}.blocking must be true or false when present.")
    tolerance = lock.get("tolerance_px")
    if tolerance is not None and not isinstance(tolerance, (int, float)):
        errors.append(f"{prefix}.tolerance_px must be numeric when present.")
    style = lock.get("style")
    if style is not None and not isinstance(style, dict):
        errors.append(f"{prefix}.style must be an object when present.")
    return errors


def validate_geometry_locks_list(locks: Any) -> list[str]:
    if locks is None:
        return []
    if not isinstance(locks, list):
        return ["geometry_locks must be a list when present."]
    errors: list[str] = []
    seen: set[str] = set()
    for index, lock in enumerate(locks):
        if not isinstance(lock, dict):
            errors.append(f"geometry_locks[{index}] must be an object.")
            continue
        errors.extend(validate_geometry_lock(lock, index=index))
        lock_id = str(lock.get("id", "")).strip()
        if lock_id:
            if lock_id in seen:
                errors.append(f"geometry_locks id `{lock_id}` is duplicated.")
            seen.add(lock_id)
    return errors


def seed_geometry_locks_from_measurement(measured: dict[str, Any]) -> list[dict[str, Any]]:
    """Build draft geometry_locks[] from measure_layout_geometry_from_image output."""
    if not measured.get("measured"):
        return []
    target = measured.get("target_canvas", [1280, 720])
    try:
        canvas_w = int(target[0])
        canvas_h = int(target[1])
    except (TypeError, ValueError, IndexError):
        canvas_w, canvas_h = 1280, 720

    locks: list[dict[str, Any]] = []
    px_bands = measured.get("px_bands", {})
    style = measured.get("style_reference", {})
    if not isinstance(px_bands, dict):
        px_bands = {}
    if not isinstance(style, dict):
        style = {}

    title_bottom = px_bands.get("title_bottom_px")
    if isinstance(title_bottom, (int, float)):
        locks.append({
            "id": "lock_title_rule",
            "kind": "title_rule",
            "label": "Title band bottom / red rule",
            "y_px": float(title_bottom),
            "bbox_px": [0, max(0, int(title_bottom) - 2), canvas_w, 4],
            "svg_selector": {"data-primitive": "title_rule"},
            "style": {
                "stroke": style.get("accent_color", "#C00000"),
                "stroke_width_px": 2,
            },
            "tolerance_px": 3,
            "blocking": True,
            "source": "measure_layout_geometry_from_image.px_bands.title_bottom_px",
        })

    guidance_y = px_bands.get("guidance_y_px")
    guidance_h = px_bands.get("guidance_h_px")
    if isinstance(guidance_y, (int, float)) and isinstance(guidance_h, (int, float)):
        locks.append({
            "id": "lock_guidance_band",
            "kind": "box",
            "label": "Top guidance banner",
            "bbox_px": [0, int(guidance_y), canvas_w, int(guidance_h)],
            "svg_selector": {"data-zone-id": "zone_guidance", "data-primitive": "guidance_banner"},
            "style": {
                "fill": style.get("guidance_fill", "#E8F4FC"),
            },
            "tolerance_px": 3,
            "blocking": True,
            "source": "measure_layout_geometry_from_image.px_bands",
        })

    footer_y = px_bands.get("footer_y_px")
    footer_h = px_bands.get("footer_h_px")
    if isinstance(footer_y, (int, float)) and isinstance(footer_h, (int, float)):
        locks.append({
            "id": "lock_footer_bar",
            "kind": "footer_bar",
            "label": "Bottom navy principle bar",
            "bbox_px": [0, int(footer_y), canvas_w, int(footer_h)],
            "svg_selector": {"data-zone-id": "zone_footer", "data-primitive": "footer_principle_chip"},
            "style": {
                "fill": style.get("footer_fill", style.get("primary_color", "#1F3A63")),
            },
            "tolerance_px": 3,
            "blocking": True,
            "source": "measure_layout_geometry_from_image.px_bands.footer",
        })

    column_boxes = measured.get("column_boxes_px", [])
    if isinstance(column_boxes, list):
        header_y = px_bands.get("header_y_px", 172)
        body_h = px_bands.get("body_h_px", 430)
        if not isinstance(header_y, (int, float)):
            header_y = 172
        if not isinstance(body_h, (int, float)):
            body_h = 430
        for index, box in enumerate(column_boxes[:4], start=1):
            if not isinstance(box, list) or len(box) < 2:
                continue
            try:
                x_px = int(box[0])
                w_px = int(box[1])
            except (TypeError, ValueError):
                continue
            zone_id = f"zone_col_{['public', 'member', 'product', 'ecosystem'][index - 1]}"
            if measured.get("layout_family", "").startswith("four_stage"):
                zone_id = f"zone_stage_{index:02d}"
            locks.append({
                "id": f"lock_column_{index:02d}",
                "kind": "box",
                "label": f"Column/card frame {index}",
                "bbox_px": [x_px, int(header_y), w_px, int(body_h)],
                "svg_selector": {"data-zone-id": zone_id},
                "style": {
                    "stroke": style.get("card_border", "#D0D0D0"),
                    "rx_px": style.get("card_radius_px", 8),
                },
                "tolerance_px": 4,
                "blocking": True,
                "source": "measure_layout_geometry_from_image.column_boxes_px",
            })

    anchors = measured.get("visual_anchors", [])
    if isinstance(anchors, list):
        for anchor in anchors:
            if not isinstance(anchor, dict):
                continue
            anchor_id = str(anchor.get("id", "")).strip()
            if anchor.get("type") == "horizontal_edge" and isinstance(anchor.get("y"), (int, float)):
                locks.append({
                    "id": f"lock_anchor_{anchor_id}",
                    "kind": "horizontal_edge",
                    "label": f"Anchor edge {anchor_id}",
                    "y_px": float(anchor["y"]),
                    "svg_selector": {"data-geometry-lock-id": f"lock_anchor_{anchor_id}"},
                    "tolerance_px": 3,
                    "blocking": True,
                    "source": "measure_layout_geometry_from_image.visual_anchors",
                })

    return locks


def _iter_elements(root: ET.Element) -> list[ET.Element]:
    return [elem for elem in root.iter()]


def _selector_match(elem: ET.Element, selector: dict[str, Any]) -> bool:
    for key, expected in selector.items():
        if not isinstance(expected, str):
            return False
        actual = elem.get(key)
        if actual != expected:
            return False
    return True


def _find_elements(root: ET.Element, selector: dict[str, Any]) -> list[ET.Element]:
    if not selector:
        return []
    matches: list[ET.Element] = []
    for elem in _iter_elements(root):
        if _selector_match(elem, selector):
            matches.append(elem)
    deduped: list[ET.Element] = []
    seen: set[int] = set()
    for elem in matches:
        key = id(elem)
        if key not in seen:
            seen.add(key)
            deduped.append(elem)
    return deduped


def _rect_bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    tag = _strip_ns(elem.tag)
    if tag == "rect":
        x = _float(elem.get("x"))
        y = _float(elem.get("y"))
        w = _float(elem.get("width"))
        h = _float(elem.get("height"))
        if x is not None and y is not None and w is not None and h is not None:
            return x, y, w, h
    if tag == "line":
        x1 = _float(elem.get("x1"))
        y1 = _float(elem.get("y1"))
        x2 = _float(elem.get("x2"))
        y2 = _float(elem.get("y2"))
        if None not in {x1, y1, x2, y2}:
            x = min(x1, x2)
            y = min(y1, y2)
            return x, y, abs(x2 - x1), max(abs(y2 - y1), 1.0)
    return None


def _group_bbox(root: ET.Element, group: ET.Element) -> tuple[float, float, float, float] | None:
    boxes: list[tuple[float, float, float, float]] = []
    for child in group.iter():
        if child is group:
            continue
        rect = _rect_bbox(child)
        if rect is not None:
            boxes.append(rect)
    if not boxes:
        return None
    x0 = min(item[0] for item in boxes)
    y0 = min(item[1] for item in boxes)
    x1 = max(item[0] + item[2] for item in boxes)
    y1 = max(item[1] + item[3] for item in boxes)
    return x0, y0, x1 - x0, y1 - y0


def _normalize_color(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip().lower()
    if text.startswith("#") and len(text) in {4, 7}:
        if len(text) == 4:
            return "#" + "".join(ch * 2 for ch in text[1:])
        return text
    named = {
        "none": "",
        "transparent": "",
    }
    return named.get(text, text)


def _style_matches(elem: ET.Element, style: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not style:
        return issues
    if "stroke_width_px" in style:
        expected = float(style["stroke_width_px"])
        actual = _float(elem.get("stroke-width"))
        if actual is None:
            for child in elem.iter():
                actual = _float(child.get("stroke-width"))
                if actual is not None:
                    break
        if actual is not None and abs(actual - expected) > 1.0:
            issues.append(f"stroke_width expected {expected}, got {actual}")
    for key, attr in (("stroke", "stroke"), ("fill", "fill")):
        if key not in style:
            continue
        expected = _normalize_color(str(style[key]))
        actual = _normalize_color(elem.get(attr))
        if not actual:
            for child in elem.iter():
                actual = _normalize_color(child.get(attr))
                if actual:
                    break
        if expected and actual and expected != actual:
            issues.append(f"{key} expected {expected}, got {actual or 'unset'}")
    if "rx_px" in style:
        expected = float(style["rx_px"])
        actual = _float(elem.get("rx"))
        if actual is not None and abs(actual - expected) > 2.0:
            issues.append(f"rx expected {expected}, got {actual}")
    return issues


def _drift(actual: float, expected: float) -> float:
    return abs(actual - expected)


def _bbox_drift(
    actual: tuple[float, float, float, float],
    expected: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    return (
        _drift(actual[0], expected[0]),
        _drift(actual[1], expected[1]),
        _drift(actual[2], expected[2]),
        _drift(actual[3], expected[3]),
    )


def verify_lock_on_svg(lock: dict[str, Any], svg_path: Path, *, thresholds: Thresholds | None = None) -> dict[str, Any]:
    limits = thresholds or Thresholds()
    tolerance = float(lock.get("tolerance_px", limits.position_px))
    size_tolerance = max(tolerance, limits.size_px)
    lock_id = str(lock.get("id", ""))
    selector = lock.get("svg_selector", {})
    if not isinstance(selector, dict):
        selector = {}

    result: dict[str, Any] = {
        "id": lock_id,
        "kind": lock.get("kind"),
        "blocking": lock.get("blocking", True) is not False,
        "valid": True,
        "issues": [],
    }

    try:
        root = ET.parse(svg_path).getroot()
    except (ET.ParseError, OSError) as exc:
        result["valid"] = False
        result["issues"].append(f"svg_parse_error: {exc}")
        return result

    elements = _find_elements(root, selector)
    if not elements:
        result["valid"] = False
        result["issues"].append("svg_selector_not_found")
        return result

    expected_bbox = None
    bbox_values = lock.get("bbox_px")
    if isinstance(bbox_values, list) and len(bbox_values) >= 4:
        expected_bbox = tuple(float(value) for value in bbox_values[:4])

    expected_y = lock.get("y_px")
    if isinstance(expected_y, (int, float)):
        expected_y = float(expected_y)

    best_issue: list[str] = []
    best_valid = False
    for elem in elements:
        issues: list[str] = []
        bbox = _rect_bbox(elem)
        if bbox is None and _strip_ns(elem.tag) == "g":
            bbox = _group_bbox(root, elem)
        if expected_y is not None:
            actual_y = bbox[1] if bbox is not None else None
            if actual_y is None:
                issues.append("horizontal_edge_missing")
            elif _drift(actual_y, expected_y) > tolerance:
                issues.append(f"y_drift:{actual_y:.1f}!={expected_y:.1f}")
        if expected_bbox is not None:
            if bbox is None:
                issues.append("bbox_missing")
            else:
                dx, dy, dw, dh = _bbox_drift(bbox, expected_bbox)
                if dx > tolerance or dy > tolerance:
                    issues.append(f"position_drift:dx={dx:.1f},dy={dy:.1f}")
                if dw > size_tolerance or dh > size_tolerance:
                    issues.append(f"size_drift:dw={dw:.1f},dh={dh:.1f}")
                result["actual_bbox_px"] = [round(value, 2) for value in bbox]
        style = lock.get("style")
        if isinstance(style, dict):
            issues.extend(_style_matches(elem, style))
        if not issues:
            best_valid = True
            best_issue = []
            break
        if len(issues) > len(best_issue):
            best_issue = issues

    result["valid"] = best_valid
    result["issues"] = best_issue
    if expected_bbox is not None:
        result["expected_bbox_px"] = [round(value, 2) for value in expected_bbox]
    if expected_y is not None:
        result["expected_y_px"] = expected_y
    return result


def _layout_files(project: Path) -> list[tuple[str, Path]]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages", [])
    paths: list[tuple[str, Path]] = []
    if isinstance(pages, list) and pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_id = str(page.get("page_id", "")).strip() or "01"
            raw = page.get("page_dir") or page.get("page_project")
            page_root = project / raw if isinstance(raw, str) and raw.strip() else project / "pages" / page_id
            if not page_root.is_dir():
                page_root = project
            layout = page_root / "layout_reference.json"
            if layout.is_file():
                paths.append((page_id, layout))
        if paths:
            return paths
    root = project / "layout_reference.json"
    return [("01", root)] if root.is_file() else []


def _svg_for_page(project: Path, page_id: str) -> Path | None:
    return find_page_svg(project, page_id)


def verify_project(
    project: Path,
    *,
    thresholds: Thresholds | None = None,
    write_report: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0

    for page_id, layout_path in _layout_files(project):
        layout = load_json(layout_path)
        locks = layout.get("geometry_locks")
        if not isinstance(locks, list) or not locks:
            continue
        schema_errors = validate_geometry_locks_list(locks)
        if schema_errors:
            errors.extend(schema_errors)
            continue
        svg_path = _svg_for_page(project, page_id)
        if svg_path is None:
            errors.append(f"Page `{page_id}` has geometry_locks but no rebuilt SVG was found.")
            continue
        page_results: list[dict[str, Any]] = []
        for lock in locks:
            if not isinstance(lock, dict):
                continue
            item = verify_lock_on_svg(lock, svg_path, thresholds=thresholds)
            checked += 1
            page_results.append(item)
            if item.get("valid"):
                continue
            message = f"Geometry lock `{item.get('id')}` failed: {', '.join(item.get('issues', []))}"
            if item.get("blocking"):
                errors.append(message)
            else:
                warnings.append(message)
        pages.append({
            "page_id": page_id,
            "layout_reference": str(layout_path.relative_to(project)),
            "svg": str(svg_path.relative_to(project)),
            "locks_checked": len(page_results),
            "results": page_results,
        })

    payload = {
        "workflow": "slide-image-rebuild",
        "check": "geometry_locks",
        "version": REPORT_VERSION,
        "generated_at": utc_now(),
        "project": str(project.resolve()),
        "valid": not errors,
        "locks_checked": checked,
        "pages": pages,
        "errors": errors,
        "warnings": warnings,
    }
    if write_report:
        out = report_path or project / "exports" / "qa" / "geometry_locks_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload["report_path"] = str(out.relative_to(project))
    return payload
