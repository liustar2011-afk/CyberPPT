from __future__ import annotations

from typing import Any


RENDER_QA_SCHEMA = "cyberppt.scene_graph.render_qa.v1"


def _inside_canvas(bbox: list[float], width: float, height: float) -> bool:
    return bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= width and bbox[3] <= height and bbox[2] > bbox[0] and bbox[3] > bbox[1]


def build_render_qa(layout_plan: dict[str, Any], rendered_image_size: dict[str, Any]) -> dict[str, Any]:
    width = float(rendered_image_size.get("width") or 1280)
    height = float(rendered_image_size.get("height") or 720)
    issues: list[dict[str, Any]] = []
    for item in layout_plan.get("items", []):
        if not isinstance(item, dict):
            continue
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            issues.append(
                {
                    "severity": "error",
                    "code": "render_text_missing_bbox",
                    "node_id": item.get("node_id"),
                    "text": item.get("text"),
                    "blocking": True,
                }
            )
            continue
        values = [float(value) for value in bbox]
        if not _inside_canvas(values, width, height):
            issues.append(
                {
                    "severity": "error",
                    "code": "render_text_outside_canvas",
                    "node_id": item.get("node_id"),
                    "text": item.get("text"),
                    "bbox": [round(value, 3) for value in values],
                    "canvas": {"width": width, "height": height},
                    "blocking": True,
                }
            )
    return {
        "schema": RENDER_QA_SCHEMA,
        "valid": not any(issue.get("blocking") for issue in issues),
        "blocking_count": sum(1 for issue in issues if issue.get("blocking")),
        "issues": issues,
    }
