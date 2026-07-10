from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "cyberppt.dual_image.workspace_layout_qa.v1"
# Real typeset text routinely has a few px of intentional, cosmetically-fine
# vertical crowding between tightly-set lines (confirmed by hand against a
# real render: small overlaps rendered fine, only the larger ones did not).
# A raw area/epsilon check flags all of that as "overlap" and buries the real
# defects in noise, so this instead thresholds on how much of the *smaller*
# box is eaten by the overlap -- a near-total collision (two distinct OCR
# lines placed at the same coordinates) scores near 1.0; ordinary tight
# leading scores well under this threshold.
OVERLAP_RATIO_THRESHOLD = 0.2

# Mirrors `layout_qa.ROLE_MIN_FONT` (the `build_page.py` pipeline's role/font
# floor table) so both pipelines enforce the same legibility bar.
ROLE_MIN_FONT_PT = {
    "title": 14.0,
    "subtitle": 10.0,
    "body": 9.0,
    "kpi": 14.0,
    "evidence": 6.5,
    "caveat": 6.5,
    "so_what": 9.5,
}
DEFAULT_MIN_FONT_PT = 7.5


def _xyxy(bbox: dict[str, Any]) -> tuple[float, float, float, float]:
    x = float(bbox.get("x", 0.0) or 0.0)
    y = float(bbox.get("y", 0.0) or 0.0)
    w = float(bbox.get("w", bbox.get("width", 0.0)) or 0.0)
    h = float(bbox.get("h", bbox.get("height", 0.0)) or 0.0)
    return x, y, x + w, y + h


def _area(bbox: dict[str, Any]) -> float:
    _, _, x2, y2 = _xyxy(bbox)
    x1 = float(bbox.get("x", 0.0) or 0.0)
    y1 = float(bbox.get("y", 0.0) or 0.0)
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _overlap_area(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax1, ay1, ax2, ay2 = _xyxy(a)
    bx1, by1, bx2, by2 = _xyxy(b)
    w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    h = max(0.0, min(ay2, by2) - max(ay1, by1))
    return w * h


def _overlap_ratio(a: dict[str, Any], b: dict[str, Any]) -> float:
    area = _overlap_area(a, b)
    if area <= 0.0:
        return 0.0
    smaller = min(_area(a), _area(b))
    if smaller <= 0.0:
        return 0.0
    return area / smaller


def check_page_layout_overlaps(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect any two distinct text boxes on a page that overlap after workspace assignment.

    `workspace_assignment.build_workspace_assignment` places each text item
    against its own slot independently (`_clamp_to_slot`); it has no visibility
    into siblings, so two OCR-detected lines placed at the same or overlapping
    coordinates (a real, observed vision-OCR bbox collision, not just a
    rendering artifact) survive untouched. This is the backstop that catches
    it deterministically in the pipeline's own report instead of relying on
    someone noticing a garbled render screenshot.

    This is the `template_rebuild.py` / `workspace_assignment.py` pipeline's
    counterpart to `layout_qa.check_layout`, which already does an equivalent
    pairwise overlap check but for the separate `build_page.py` /
    `SemanticPlan`-based pipeline and isn't shaped to consume
    `workspace_assignment` output directly.
    """
    boxes = [
        item
        for item in assignments
        if isinstance(item, dict) and isinstance(item.get("final_bbox"), dict)
    ]
    overlaps: list[dict[str, Any]] = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ratio = _overlap_ratio(boxes[i]["final_bbox"], boxes[j]["final_bbox"])
            if ratio <= OVERLAP_RATIO_THRESHOLD:
                continue
            overlaps.append(
                {
                    "text_index_a": boxes[i].get("text_index"),
                    "text_a": boxes[i].get("text"),
                    "text_index_b": boxes[j].get("text_index"),
                    "text_b": boxes[j].get("text"),
                    "overlap_area": round(_overlap_area(boxes[i]["final_bbox"], boxes[j]["final_bbox"]), 2),
                    "overlap_ratio": round(ratio, 3),
                }
            )
    return {
        "schema": SCHEMA,
        "valid": not overlaps,
        "box_count": len(boxes),
        "overlap_count": len(overlaps),
        "overlaps": overlaps,
    }


def check_page_font_floor(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Flag any text assigned a font size below its role's legibility floor.

    The `build_page.py` pipeline's `layout_qa.check_layout` already enforces
    this; `workspace_assignment` output carries `role` and (as of this check)
    `font_size_pt`, so the same floor table can be applied here without
    needing the heavier `SemanticPlan` shape that check requires.
    """
    issues: list[dict[str, Any]] = []
    checked = 0
    for item in assignments:
        if not isinstance(item, dict):
            continue
        font_size = item.get("font_size_pt")
        if font_size is None:
            continue
        checked += 1
        role = str(item.get("role") or "body")
        minimum = ROLE_MIN_FONT_PT.get(role, DEFAULT_MIN_FONT_PT)
        if float(font_size) < minimum:
            issues.append(
                {
                    "text_index": item.get("text_index"),
                    "text": item.get("text"),
                    "role": role,
                    "font_size_pt": font_size,
                    "minimum_pt": minimum,
                }
            )
    return {
        "schema": SCHEMA,
        "valid": not issues,
        "checked_count": checked,
        "issue_count": len(issues),
        "issues": issues,
    }


def check_page_layout(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Combined overlap + font-floor check for a single page's assignments."""
    overlap_report = check_page_layout_overlaps(assignments)
    font_report = check_page_font_floor(assignments)
    return {
        "schema": SCHEMA,
        "valid": overlap_report["valid"] and font_report["valid"],
        "box_count": overlap_report["box_count"],
        "overlap_count": overlap_report["overlap_count"],
        "overlaps": overlap_report["overlaps"],
        "font_floor_checked_count": font_report["checked_count"],
        "font_floor_issue_count": font_report["issue_count"],
        "font_floor_issues": font_report["issues"],
    }


def check_workspace_assignment_layout(workspace_assignment: dict[str, Any]) -> dict[str, Any]:
    """Run the overlap + font-floor checks over every page in a workspace_assignment(_set) payload."""
    pages_in = workspace_assignment.get("pages")
    page_payloads = pages_in if isinstance(pages_in, list) else [workspace_assignment]
    pages: list[dict[str, Any]] = []
    for page in page_payloads:
        if not isinstance(page, dict):
            continue
        assignments = page.get("assignments")
        report = check_page_layout(assignments if isinstance(assignments, list) else [])
        report["page_number"] = page.get("page_number")
        pages.append(report)
    overlap_count = sum(int(page["overlap_count"]) for page in pages)
    font_floor_issue_count = sum(int(page["font_floor_issue_count"]) for page in pages)
    return {
        "schema": SCHEMA,
        "valid": bool(pages) and overlap_count == 0 and font_floor_issue_count == 0,
        "page_count": len(pages),
        "overlap_count": overlap_count,
        "font_floor_issue_count": font_floor_issue_count,
        "pages": pages,
    }


def write_workspace_layout_qa(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
