from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "cyberppt.dual_image.workspace_assignment.v1"
SET_SCHEMA = "cyberppt.dual_image.workspace_assignment_set.v1"
SKIP_ROLES = {"index", "icon_label", "bullet_marker"}
GEOMETRY_EPSILON = 1e-3


def _role(item: dict[str, Any]) -> str:
    style = item.get("style") if isinstance(item.get("style"), dict) else {}
    for key in ("role", "semantic_role", "typography_role"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        value = style.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "body"


def _rect(item: dict[str, Any]) -> dict[str, float]:
    bbox = item.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        x1, y1, x2, y2 = [float(value) for value in bbox]
        return {"x": x1, "y": y1, "w": max(0.0, x2 - x1), "h": max(0.0, y2 - y1)}
    if isinstance(bbox, dict):
        return _rect(bbox)
    return {
        "x": float(item.get("x", 0.0) or 0.0),
        "y": float(item.get("y", 0.0) or 0.0),
        "w": float(item.get("w", 0.0) or 0.0),
        "h": float(item.get("h", 0.0) or 0.0),
    }


def _xyxy(rect: dict[str, Any]) -> tuple[float, float, float, float]:
    x = float(rect.get("x", 0.0) or 0.0)
    y = float(rect.get("y", 0.0) or 0.0)
    w = float(rect.get("w", rect.get("width", 0.0)) or 0.0)
    h = float(rect.get("h", rect.get("height", 0.0)) or 0.0)
    return x, y, x + w, y + h


def _inside(inner: dict[str, Any], outer: dict[str, Any]) -> bool:
    ix1, iy1, ix2, iy2 = _xyxy(inner)
    ox1, oy1, ox2, oy2 = _xyxy(outer)
    return (
        ix1 >= ox1 - GEOMETRY_EPSILON
        and iy1 >= oy1 - GEOMETRY_EPSILON
        and ix2 <= ox2 + GEOMETRY_EPSILON
        and iy2 <= oy2 + GEOMETRY_EPSILON
    )


def _intersection_area(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax1, ay1, ax2, ay2 = _xyxy(a)
    bx1, by1, bx2, by2 = _xyxy(b)
    w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    h = max(0.0, min(ay2, by2) - max(ay1, by1))
    return w * h


def _clamp_to_slot(rect: dict[str, float], slot: dict[str, Any]) -> dict[str, float]:
    sx1, sy1, sx2, sy2 = _xyxy(slot)
    width = min(max(1.0, rect["w"]), max(1.0, sx2 - sx1))
    height = min(max(1.0, rect["h"]), max(1.0, sy2 - sy1))
    x = min(max(rect["x"], sx1), sx2 - width)
    y = min(max(rect["y"], sy1), sy2 - height)
    return {"x": round(x, 3), "y": round(y, 3), "w": round(width, 3), "h": round(height, 3)}


def _slots_by_container(workspace: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    containers = workspace.get("containers", [])
    if not isinstance(containers, list):
        return result
    for container in containers:
        if not isinstance(container, dict):
            continue
        container_id = str(container.get("id") or "")
        slots = [slot for slot in container.get("work_slots", []) if isinstance(slot, dict)]
        if container_id:
            result[container_id] = slots
    return result


def _page_understanding_bindings(page_understanding: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(page_understanding, dict):
        return {}
    bindings = page_understanding.get("container_text_bindings")
    if not isinstance(bindings, list):
        return {}
    result: dict[str, str] = {}
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        text_id = str(binding.get("text_block_id") or "").strip()
        container_id = str(binding.get("container_id") or "").strip()
        if text_id and container_id:
            result[text_id] = container_id
    return result


def _text_id(item: dict[str, Any]) -> str:
    for key in ("id", "text_block_id", "text_id"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _choose_slot(text_rect: dict[str, float], role: str, slots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not slots:
        return None
    preferred = [
        slot
        for slot in slots
        if role in [str(item) for item in slot.get("preferred_roles", [])]
    ]
    candidates = preferred or slots
    return max(candidates, key=lambda slot: _intersection_area(text_rect, slot.get("bbox", {})))


def build_workspace_assignment(
    *,
    page_number: int | None,
    workspace: dict[str, Any],
    text_items: list[dict[str, Any]],
    stage: str,
    page_understanding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    slots_by_container = _slots_by_container(workspace)
    page_understanding_binding_by_text = _page_understanding_bindings(page_understanding)
    assignments: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for index, item in enumerate(text_items):
        role = _role(item)
        if role in SKIP_ROLES:
            continue
        item_text_id = _text_id(item)
        bound_container_id = page_understanding_binding_by_text.get(item_text_id)
        page_understanding_container_id = bound_container_id if slots_by_container.get(bound_container_id or "") else None
        if bound_container_id and page_understanding_container_id is None:
            issues.append(
                {
                    "severity": "warning",
                    "code": "page_understanding_binding_missing_slot",
                    "text_index": index,
                    "text_id": item_text_id,
                    "container_id": bound_container_id,
                }
            )
        container_id = page_understanding_container_id or str(item.get("container_id") or "")
        text_rect = _rect(item)
        slot = _choose_slot(text_rect, role, slots_by_container.get(container_id, []))
        if slot is None:
            issues.append(
                {
                    "severity": "error",
                    "code": "text_has_no_work_slot",
                    "text_index": index,
                    "text": item.get("text") or item.get("rendered_text"),
                    "container_id": container_id,
                    "role": role,
                }
            )
            continue
        slot_bbox = slot.get("bbox", {})
        final_bbox = _clamp_to_slot(text_rect, slot_bbox)
        inside = _inside(final_bbox, slot_bbox)
        if not inside:
            issues.append(
                {
                    "severity": "error",
                    "code": "assigned_text_outside_slot",
                    "text_index": index,
                    "container_id": container_id,
                    "slot_id": slot.get("id"),
                }
            )
        assignments.append(
            {
                "text_index": index,
                "text": item.get("text") or item.get("rendered_text"),
                "role": role,
                "container_id": container_id,
                "assigned_slot": slot.get("id"),
                "slot_bbox": slot_bbox,
                "original_bbox": text_rect,
                "final_bbox": final_bbox,
                "fit_actions": ["assign_to_work_slot"] if final_bbox != text_rect else [],
                "inside_slot": inside,
            }
        )
        if page_understanding_container_id:
            assignments[-1]["text_id"] = item_text_id
            assignments[-1]["source"] = "page_understanding"
    error_count = len([issue for issue in issues if issue["severity"] == "error"])
    return {
        "schema": SCHEMA,
        "stage": stage,
        "page_number": page_number,
        "valid": error_count == 0 and bool(assignments),
        "assignment_count": len(assignments),
        "error_count": error_count,
        "assignments": assignments,
        "issues": issues,
    }


def write_workspace_assignment(path: Path, assignment: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(assignment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return assignment
