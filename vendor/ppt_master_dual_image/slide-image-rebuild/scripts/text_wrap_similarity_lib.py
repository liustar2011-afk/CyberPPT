#!/usr/bin/env python3
"""
Text wrap / baseline similarity checks for slide-image rebuild.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from layout_reference_components import cjk_text_width
from reference_object_similarity_lib import canvas_size, resolve_bbox_px
from svg_page_discovery import find_page_svg

SVG_NS = "{http://www.w3.org/2000/svg}"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
REPORT_VERSION = "1.0"


@dataclass(frozen=True)
class Thresholds:
    bbox_position_px: float = 3.0
    baseline_px: float = 2.0
    edge_margin_px: float = 4.0


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


def _visual_lines(elem: ET.Element) -> list[str]:
    tspans = [child for child in list(elem) if _strip_ns(child.tag) == "tspan"]
    if not tspans:
        text = "".join(elem.itertext()).strip()
        return [text] if text else []
    lines: list[str] = []
    for child in tspans:
        line = "".join(child.itertext()).strip()
        if line:
            lines.append(line)
    return lines


def _text_anchor_box(x: float, y: float, width: float, height: float, anchor: str) -> tuple[float, float, float, float]:
    if anchor == "middle":
        return x - width / 2, y - height * 0.85, width, height
    if anchor == "end":
        return x - width, y - height * 0.85, width, height
    return x, y - height * 0.85, width, height


def _estimate_text_block(elem: ET.Element) -> dict[str, Any]:
    lines = _visual_lines(elem)
    x = _float(elem.get("x"))
    y = _float(elem.get("y"))
    size = _float(elem.get("font-size")) or 16.0
    if x is None or y is None or not lines:
        return {}
    line_height = _float(elem.get("data-paragraph-line-height")) or size * 1.3
    width = max(cjk_text_width(line, size) for line in lines)
    height = line_height * max(0, len(lines) - 1) + size * 1.25
    bbox = _text_anchor_box(x, y, width, height, elem.get("text-anchor", "start"))
    baselines = [y + index * line_height for index in range(len(lines))]
    return {
        "lines": lines,
        "line_count": len(lines),
        "bbox_px": [round(value, 2) for value in bbox],
        "baselines_px": [round(value, 2) for value in baselines],
        "font_size_px": size,
        "auto_scaled": str(elem.get("data-text-auto-scale", "")).lower() in {"1", "true", "yes"},
    }


def _collect_svg_regions(svg_path: Path) -> dict[str, dict[str, Any]]:
    root = ET.parse(svg_path).getroot()
    out: dict[str, dict[str, Any]] = {}
    for elem in root.iter():
        if _strip_ns(elem.tag) != "text":
            continue
        region_id = elem.get("data-text-region-id") or elem.get("data-region-id")
        if not region_id:
            continue
        block = _estimate_text_block(elem)
        if block:
            out[str(region_id)] = block
    return out


def _regions_for_page(text_map: dict[str, Any], page_id: str) -> list[dict[str, Any]]:
    pages = text_map.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            if str(page.get("page_id", "")) not in {page_id, ""}:
                continue
            regions = page.get("regions", [])
            return [item for item in regions if isinstance(item, dict)]
    regions = text_map.get("regions", [])
    if isinstance(regions, list):
        return [item for item in regions if isinstance(item, dict)]
    return []


def _region_bbox(region: dict[str, Any], canvas_w: int, canvas_h: int) -> tuple[float, float, float, float] | None:
    bbox = resolve_bbox_px(region, canvas_w, canvas_h)
    if bbox is not None:
        return bbox
    raw = region.get("bbox")
    if isinstance(raw, list) and len(raw) >= 4:
        try:
            return tuple(float(raw[index]) for index in range(4))  # type: ignore[return-value]
        except (TypeError, ValueError):
            return None
    return None


def _expected_line_count(region: dict[str, Any]) -> int | None:
    for key in ("expected_line_count", "line_count", "reference_line_count"):
        value = region.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    draft = str(region.get("draft_text") or "")
    if "\n" in draft:
        return len([line for line in draft.splitlines() if line.strip()])
    role = str(region.get("role", "")).lower()
    if role in {"title", "label", "badge"}:
        return 1
    return None


def _failure_action(issue_code: str) -> str:
    actions = {
        "TEXT_BBOX_DRIFT": "Move or resize the SVG text block to match the declared text region bbox.",
        "LINE_COUNT_MISMATCH": "Adjust manual line breaks or fit width so the visual line count matches the reference.",
        "BASELINE_DRIFT": "Re-align the first-line baseline to the reference y position.",
        "TEXT_EDGE_MARGIN": "Add padding so text stays at least 4px inside the declared region bbox.",
        "AUTO_SCALE_TRIGGERED": "Remove auto-scaled text; rebuild with reference font size and explicit line breaks.",
        "MISSING_TEXT_REGION": "Add editable <text data-text-region-id=\"...\"> for the mapped region.",
    }
    return actions.get(issue_code, "Review the text region against the reference image.")


def compare_region(
    region: dict[str, Any],
    svg_block: dict[str, Any] | None,
    *,
    canvas_w: int,
    canvas_h: int,
    thresholds: Thresholds,
) -> dict[str, Any]:
    region_id = str(region.get("id", "")).strip()
    ref_bbox = _region_bbox(region, canvas_w, canvas_h)
    item: dict[str, Any] = {
        "id": region_id,
        "role": region.get("role", ""),
        "reference_bbox_px": [round(value, 2) for value in ref_bbox] if ref_bbox else None,
        "valid": True,
        "issues": [],
    }
    failures: list[dict[str, Any]] = []
    if svg_block is None:
        failure = {
            "id": region_id,
            "issue_code": "MISSING_TEXT_REGION",
            "message": f"Text region `{region_id}` has no matching SVG data-text-region-id.",
            "tier": "blocking",
            "action": _failure_action("MISSING_TEXT_REGION"),
        }
        item["valid"] = False
        item["issues"].append("MISSING_TEXT_REGION")
        failures.append(failure)
        item["failures"] = failures
        return item

    item["candidate"] = svg_block
    if svg_block.get("auto_scaled"):
        failure = {
            "id": region_id,
            "issue_code": "AUTO_SCALE_TRIGGERED",
            "message": f"Text region `{region_id}` uses data-text-auto-scale.",
            "tier": "blocking",
            "action": _failure_action("AUTO_SCALE_TRIGGERED"),
        }
        failures.append(failure)
        item["valid"] = False
        item["issues"].append("AUTO_SCALE_TRIGGERED")

    expected_lines = _expected_line_count(region)
    actual_lines = int(svg_block.get("line_count", 0))
    item["metrics"] = {"expected_line_count": expected_lines, "actual_line_count": actual_lines}
    if expected_lines is not None and actual_lines != expected_lines:
        failure = {
            "id": region_id,
            "issue_code": "LINE_COUNT_MISMATCH",
            "message": f"Text region `{region_id}` line count {actual_lines} != expected {expected_lines}.",
            "metrics": item["metrics"],
            "tier": "blocking",
            "action": _failure_action("LINE_COUNT_MISMATCH"),
        }
        failures.append(failure)
        item["valid"] = False
        item["issues"].append("LINE_COUNT_MISMATCH")

    if ref_bbox is not None:
        cand_values = svg_block.get("bbox_px", [])
        if isinstance(cand_values, list) and len(cand_values) >= 4:
            cand_bbox = tuple(float(value) for value in cand_values[:4])
            reference_text_bbox = region.get("reference_text_bbox_px") or region.get("text_bbox_px")
            if isinstance(reference_text_bbox, list) and len(reference_text_bbox) >= 4:
                text_ref_bbox = tuple(float(reference_text_bbox[index]) for index in range(4))
                dx = abs(cand_bbox[0] - text_ref_bbox[0])
                dy = abs(cand_bbox[1] - text_ref_bbox[1])
                item["metrics"]["bbox_drift_px"] = {"dx": round(dx, 2), "dy": round(dy, 2)}
                if dx > thresholds.bbox_position_px or dy > thresholds.bbox_position_px:
                    failure = {
                        "id": region_id,
                        "issue_code": "TEXT_BBOX_DRIFT",
                        "message": (
                            f"Text region `{region_id}` bbox drift dx={dx:.1f}px dy={dy:.1f}px "
                            f"exceeds {thresholds.bbox_position_px:.1f}px."
                        ),
                        "reference_bbox_px": [round(value, 2) for value in text_ref_bbox],
                        "candidate_bbox_px": [round(value, 2) for value in cand_bbox],
                        "tier": "blocking",
                        "action": _failure_action("TEXT_BBOX_DRIFT"),
                    }
                    failures.append(failure)
                    item["valid"] = False
                    item["issues"].append("TEXT_BBOX_DRIFT")

            left_margin = cand_bbox[0] - ref_bbox[0]
            top_margin = cand_bbox[1] - ref_bbox[1]
            right_margin = (ref_bbox[0] + ref_bbox[2]) - (cand_bbox[0] + cand_bbox[2])
            bottom_margin = (ref_bbox[1] + ref_bbox[3]) - (cand_bbox[1] + cand_bbox[3])
            item["metrics"]["edge_margin_px"] = {
                "left": round(left_margin, 2),
                "top": round(top_margin, 2),
                "right": round(right_margin, 2),
                "bottom": round(bottom_margin, 2),
            }
            if min(left_margin, top_margin, right_margin, bottom_margin) < thresholds.edge_margin_px:
                failure = {
                    "id": region_id,
                    "issue_code": "TEXT_EDGE_MARGIN",
                    "message": f"Text region `{region_id}` is closer than {thresholds.edge_margin_px:.0f}px to a region edge.",
                    "metrics": item["metrics"]["edge_margin_px"],
                    "tier": "warning",
                    "action": _failure_action("TEXT_EDGE_MARGIN"),
                }
                failures.append(failure)
                if failure["tier"] == "blocking":
                    item["valid"] = False
                    item["issues"].append("TEXT_EDGE_MARGIN")

        expected_baseline = region.get("baseline_y")
        if isinstance(expected_baseline, (int, float)):
            baselines = svg_block.get("baselines_px", [])
            if isinstance(baselines, list) and baselines:
                delta = abs(float(baselines[0]) - float(expected_baseline))
                item["metrics"]["baseline_drift_px"] = round(delta, 2)
                if delta > thresholds.baseline_px:
                    failure = {
                        "id": region_id,
                        "issue_code": "BASELINE_DRIFT",
                        "message": f"Text region `{region_id}` baseline drift {delta:.1f}px exceeds {thresholds.baseline_px:.1f}px.",
                        "metrics": {"baseline_drift_px": round(delta, 2)},
                        "tier": "blocking",
                        "action": _failure_action("BASELINE_DRIFT"),
                    }
                    failures.append(failure)
                    item["valid"] = False
                    item["issues"].append("BASELINE_DRIFT")

    blocking = [item for item in failures if item.get("tier") == "blocking"]
    item["failures"] = failures
    item["valid"] = not blocking and item.get("valid", True)
    return item


def _page_dirs(project: Path) -> list[tuple[str, Path]]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages", []) if isinstance(manifest, dict) else []
    out: list[tuple[str, Path]] = []
    if isinstance(pages, list) and pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_id = str(page.get("page_id", "")).strip() or "01"
            page_dir = project / "pages" / page_id
            out.append((page_id, page_dir if page_dir.is_dir() else project))
        if out:
            return out
    if (project / "layout_reference.json").is_file() or (project / "svg_output").is_dir():
        return [("01", project)]
    pages_dir = project / "pages"
    if pages_dir.is_dir():
        return [(path.name, path) for path in sorted(pages_dir.iterdir()) if path.is_dir()]
    return [("01", project)]


def verify_project(
    project: Path,
    *,
    thresholds: Thresholds | None = None,
    write_report: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    project = project.resolve()
    limits = thresholds or Thresholds()
    text_map = load_json(project / "text_region_map.json")
    if not text_map:
        return {
            "version": REPORT_VERSION,
            "workflow": "slide-image-rebuild",
            "check": "text_wrap_similarity",
            "project": str(project),
            "valid": False,
            "errors": ["text_region_map.json is missing or unreadable."],
            "pages": [],
        }

    page_payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    for page_id, page_dir in _page_dirs(project):
        regions = _regions_for_page(text_map, page_id)
        if not regions:
            continue
        layout_path = page_dir / "layout_reference.json"
        if not layout_path.is_file():
            layout_path = project / "layout_reference.json"
        layout = load_json(layout_path)
        canvas_w, canvas_h = canvas_size(layout, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT)
        svg_path = find_page_svg(project, page_id, page_dir=page_dir)
        if svg_path is None:
            errors.append(f"No SVG found for page `{page_id}`.")
            continue
        svg_regions = _collect_svg_regions(svg_path)
        checked: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        page_warnings: list[dict[str, Any]] = []
        for region in regions:
            region_id = str(region.get("id", "")).strip()
            if not region_id:
                continue
            result = compare_region(
                region,
                svg_regions.get(region_id),
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                thresholds=limits,
            )
            checked.append(result)
            for failure in result.get("failures", []):
                if isinstance(failure, dict):
                    if failure.get("tier") == "blocking":
                        failures.append(failure)
                        errors.append(str(failure.get("message", failure)))
                    else:
                        page_warnings.append(failure)
                        warnings.append(str(failure.get("message", failure)))

        page_payloads.append({
            "page_id": page_id,
            "svg": str(svg_path),
            "regions_checked": len(checked),
            "regions_failed": len(failures),
            "regions_warned": len(page_warnings),
            "valid": not failures,
            "regions": checked,
            "failures": failures,
            "warnings": page_warnings,
        })

    payload = {
        "version": REPORT_VERSION,
        "workflow": "slide-image-rebuild",
        "check": "text_wrap_similarity",
        "generated_at": utc_now(),
        "project": str(project),
        "valid": not errors,
        "thresholds": {
            "bbox_position_px": limits.bbox_position_px,
            "baseline_px": limits.baseline_px,
            "edge_margin_px": limits.edge_margin_px,
        },
        "summary": {
            "page_count": len(page_payloads),
            "regions_checked": sum(item.get("regions_checked", 0) for item in page_payloads),
            "regions_failed": sum(item.get("regions_failed", 0) for item in page_payloads),
            "regions_warned": sum(item.get("regions_warned", 0) for item in page_payloads),
        },
        "pages": page_payloads,
        "errors": errors,
        "warnings": warnings,
    }
    if payload["summary"]["regions_checked"] == 0:
        payload["valid"] = True
        payload["skipped"] = True
        payload["warnings"] = list(warnings) + ["No text regions declared; text wrap similarity was skipped."]

    if write_report:
        out = report_path or project / "exports" / "qa" / "text_wrap_similarity_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_path"] = str(out.relative_to(project)) if out.is_relative_to(project) else str(out)
    return payload
