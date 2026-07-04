from __future__ import annotations

from .models import SemanticPlan


ROLE_MIN_FONT = {
    "title": 14.0,
    "subtitle": 10.0,
    "body": 9.0,
    "kpi": 14.0,
    "evidence": 6.5,
    "caveat": 6.5,
    "so_what": 9.5,
}


def _inside(inner: list[float], outer: list[float]) -> bool:
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def _overlap(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def check_layout(plan: SemanticPlan) -> dict:
    containers = {container.id: container for container in plan.containers}
    issues = []
    for index, item in enumerate(plan.items):
        container = containers[item.container_id]
        if not _inside(item.bbox, container.text_safe_bbox):
            issues.append(
                {
                    "severity": "error",
                    "code": "text_box_outside_container",
                    "item_index": index,
                    "container_id": item.container_id,
                    "bbox": item.bbox,
                    "text_safe_bbox": container.text_safe_bbox,
                }
            )
        minimum = ROLE_MIN_FONT.get(item.role, 7.5)
        if item.font_size < minimum:
            issues.append(
                {
                    "severity": "error",
                    "code": "font_below_role_floor",
                    "item_index": index,
                    "role": item.role,
                    "font_size": item.font_size,
                    "minimum": minimum,
                }
            )

    for left_index, left in enumerate(plan.items):
        for right_index, right in enumerate(plan.items[left_index + 1 :], start=left_index + 1):
            if _overlap(left.bbox, right.bbox) > 4.0:
                issues.append(
                    {
                        "severity": "error",
                        "code": "text_boxes_overlap",
                        "left_index": left_index,
                        "right_index": right_index,
                    }
                )

    return {
        "schema": "cyberppt.dual_image.layout_qa.v1",
        "valid": not issues,
        "issues": issues,
        "error_count": len(issues),
    }
