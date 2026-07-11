from __future__ import annotations

from typing import Any

OVERLAP_RATIO_THRESHOLD = 0.2
ROLE_MIN_FONT_PT = {"title": 14.0, "subtitle": 10.0, "body": 9.0, "kpi": 14.0, "evidence": 6.5, "caveat": 6.5, "so_what": 9.5}
DEFAULT_MIN_FONT_PT = 7.5


def _xyxy(bbox: dict[str, Any]) -> tuple[float, float, float, float]:
    x, y = float(bbox.get("x", 0) or 0), float(bbox.get("y", 0) or 0)
    w, h = float(bbox.get("w", bbox.get("width", 0)) or 0), float(bbox.get("h", bbox.get("height", 0)) or 0)
    return x, y, x + w, y + h


def _overlap_area(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax1, ay1, ax2, ay2 = _xyxy(a); bx1, by1, bx2, by2 = _xyxy(b)
    return max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))


def check_page_layout_overlaps(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    boxes = [item for item in assignments if isinstance(item, dict) and isinstance(item.get("final_bbox"), dict)]
    overlaps = []
    for i, left in enumerate(boxes):
        for right in boxes[i + 1:]:
            area = _overlap_area(left["final_bbox"], right["final_bbox"])
            lax, lay, lax2, lay2 = _xyxy(left["final_bbox"]); rax, ray, rax2, ray2 = _xyxy(right["final_bbox"])
            smaller = min(max(0.0, lax2 - lax) * max(0.0, lay2 - lay), max(0.0, rax2 - rax) * max(0.0, ray2 - ray))
            ratio = area / smaller if smaller else 0.0
            if ratio > OVERLAP_RATIO_THRESHOLD:
                overlaps.append({"text_a": left.get("text"), "text_b": right.get("text"), "overlap_ratio": round(ratio, 3)})
    return {"schema": "cyberppt.dual_image.workspace_layout_qa.v1", "valid": not overlaps, "box_count": len(boxes), "overlap_count": len(overlaps), "overlaps": overlaps}


def check_page_font_floor(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    issues = []
    for item in assignments:
        if not isinstance(item, dict) or item.get("font_size_pt") is None:
            continue
        minimum = ROLE_MIN_FONT_PT.get(str(item.get("role") or "body"), DEFAULT_MIN_FONT_PT)
        if float(item["font_size_pt"]) < minimum:
            issues.append({"text": item.get("text"), "font_size_pt": item["font_size_pt"], "minimum_pt": minimum})
    return {"valid": not issues, "checked_count": len(assignments), "issue_count": len(issues), "issues": issues}


def check_page_layout(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    overlap = check_page_layout_overlaps(assignments); font = check_page_font_floor(assignments)
    return {"schema": "cyberppt.dual_image.workspace_layout_qa.v1", "valid": overlap["valid"] and font["valid"], "box_count": overlap["box_count"], "overlap_count": overlap["overlap_count"], "overlaps": overlap["overlaps"], "font_floor_checked_count": font["checked_count"], "font_floor_issue_count": font["issue_count"], "font_floor_issues": font["issues"]}


def check_workspace_assignment_layout(payload: dict[str, Any]) -> dict[str, Any]:
    pages = payload.get("pages") if isinstance(payload.get("pages"), list) else [payload]
    reports = [{**check_page_layout(page.get("assignments", [])), "page_number": page.get("page_number")} for page in pages if isinstance(page, dict)]
    return {"schema": "cyberppt.dual_image.workspace_layout_qa.v1", "valid": bool(reports) and all(page["valid"] for page in reports), "page_count": len(reports), "pages": reports, "overlap_count": sum(page["overlap_count"] for page in reports), "font_floor_issue_count": sum(page["font_floor_issue_count"] for page in reports)}
