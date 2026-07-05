from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "cyberppt.dual_image.container_workspace.v1"


def _bbox_xyxy(values: Any) -> list[float]:
    if not isinstance(values, list) or len(values) != 4:
        return [0.0, 0.0, 0.0, 0.0]
    try:
        return [float(value) for value in values]
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0, 0.0]


def _rect_from_xyxy(values: list[float]) -> dict[str, float]:
    x1, y1, x2, y2 = values
    return {
        "x": round(x1, 3),
        "y": round(y1, 3),
        "w": round(max(0.0, x2 - x1), 3),
        "h": round(max(0.0, y2 - y1), 3),
    }


def _xyxy_from_rect(rect: dict[str, Any]) -> list[float]:
    try:
        x = float(rect.get("x", 0.0))
        y = float(rect.get("y", 0.0))
        w = float(rect.get("w", rect.get("width", 0.0)))
        h = float(rect.get("h", rect.get("height", 0.0)))
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0, 0.0]
    return [x, y, x + w, y + h]


def _rect_area(rect: dict[str, float]) -> float:
    return max(0.0, float(rect.get("w", 0.0))) * max(0.0, float(rect.get("h", 0.0)))


def _intersects(a: dict[str, float], b: dict[str, float]) -> bool:
    ax1, ay1, ax2, ay2 = _xyxy_from_rect(a)
    bx1, by1, bx2, by2 = _xyxy_from_rect(b)
    return min(ax2, bx2) > max(ax1, bx1) and min(ay2, by2) > max(ay1, by1)


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


def _text_rect(item: dict[str, Any]) -> dict[str, float]:
    if isinstance(item.get("bbox"), list):
        return _rect_from_xyxy(_bbox_xyxy(item["bbox"]))
    if isinstance(item.get("bbox"), dict):
        return _text_rect(item["bbox"])
    return {
        "x": round(float(item.get("x", 0.0) or 0.0), 3),
        "y": round(float(item.get("y", 0.0) or 0.0), 3),
        "w": round(float(item.get("w", 0.0) or 0.0), 3),
        "h": round(float(item.get("h", 0.0) or 0.0), 3),
    }


def _container_rect(container: Any) -> dict[str, float]:
    if hasattr(container, "bbox"):
        return _rect_from_xyxy(_bbox_xyxy(list(container.bbox)))
    if isinstance(container, dict):
        if isinstance(container.get("bbox"), list):
            return _rect_from_xyxy(_bbox_xyxy(container["bbox"]))
        return _text_rect(container)
    return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}


def _safe_rect(container: Any) -> dict[str, float]:
    if hasattr(container, "text_safe_bbox"):
        return _rect_from_xyxy(_bbox_xyxy(list(container.text_safe_bbox)))
    if isinstance(container, dict):
        raw = container.get("text_safe_bbox")
        if isinstance(raw, list):
            return _rect_from_xyxy(_bbox_xyxy(raw))
        if isinstance(raw, dict):
            return _text_rect(raw)
    return _container_rect(container)


def _container_id(container: Any, index: int) -> str:
    value = getattr(container, "id", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(container, dict):
        raw = container.get("id")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return f"container_{index:03d}"


def _container_role(container: Any) -> str:
    value = getattr(container, "role", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(container, dict):
        raw = container.get("role")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return "container"


def _text_occupied_zones(container_id: str, text_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for index, item in enumerate(text_items, start=1):
        if str(item.get("container_id") or "") != container_id:
            continue
        role = _role(item)
        if role not in {"index", "icon_label", "bullet_marker"}:
            continue
        zones.append(
            {
                "id": f"{container_id}_occupied_{index:03d}",
                "kind": role,
                "source": "semantic_text_item",
                "bbox": _text_rect(item),
            }
        )
    return zones


def _slots_for_container(
    *,
    container_id: str,
    safe: dict[str, float],
    text_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    assigned = [item for item in text_items if str(item.get("container_id") or "") == container_id]
    title_items = [item for item in assigned if _role(item) in {"title", "ability_title", "parallel_title", "service_title"}]
    body_items = [item for item in assigned if _role(item) not in {"index", "icon_label", "bullet_marker"}]
    slots: list[dict[str, Any]] = []

    if title_items and safe["h"] >= 24.0:
        title_h = min(max(18.0, safe["h"] * 0.28), safe["h"])
        slots.append(
            {
                "id": f"{container_id}_title_slot",
                "bbox": {"x": safe["x"], "y": safe["y"], "w": safe["w"], "h": round(title_h, 3)},
                "preferred_roles": ["title", "ability_title", "parallel_title", "service_title"],
                "capacity": {"area": round(safe["w"] * title_h, 3), "source": "safe_zone_top_band"},
            }
        )
        body_y = safe["y"] + title_h
        body_h = max(0.0, safe["h"] - title_h)
        if body_h > 0:
            slots.append(
                {
                    "id": f"{container_id}_body_slot",
                    "bbox": {"x": safe["x"], "y": round(body_y, 3), "w": safe["w"], "h": round(body_h, 3)},
                    "preferred_roles": ["body", "bullet", "description", "evidence"],
                    "capacity": {"area": round(safe["w"] * body_h, 3), "source": "safe_zone_remainder"},
                }
            )
    elif body_items:
        slots.append(
            {
                "id": f"{container_id}_body_slot",
                "bbox": safe,
                "preferred_roles": ["body", "bullet", "description", "title", "ability_title"],
                "capacity": {"area": round(_rect_area(safe), 3), "source": "safe_zone_full"},
            }
        )

    return [slot for slot in slots if _rect_area(slot["bbox"]) > 0]


def build_container_workspace(
    *,
    page_number: int | None,
    containers: list[Any],
    text_items: list[dict[str, Any]],
    stage: str,
) -> dict[str, Any]:
    workspace_containers = []
    issues: list[dict[str, Any]] = []
    for index, container in enumerate(containers, start=1):
        container_id = _container_id(container, index)
        bbox = _container_rect(container)
        safe = _safe_rect(container)
        occupied_zones = _text_occupied_zones(container_id, text_items)
        slots = _slots_for_container(container_id=container_id, safe=safe, text_items=text_items)
        for zone in occupied_zones:
            if any(_intersects(zone["bbox"], slot["bbox"]) for slot in slots):
                issues.append(
                    {
                        "severity": "warning",
                        "code": "occupied_zone_intersects_slot",
                        "container_id": container_id,
                        "occupied_zone": zone["id"],
                    }
                )
        if not slots:
            issues.append(
                {
                    "severity": "error",
                    "code": "container_has_no_work_slots",
                    "container_id": container_id,
                }
            )
        workspace_containers.append(
            {
                "id": container_id,
                "role": _container_role(container),
                "container_bbox": bbox,
                "text_safe_bbox": safe,
                "occupied_zones": occupied_zones,
                "work_slots": slots,
                "slot_count": len(slots),
            }
        )
    error_count = len([issue for issue in issues if issue["severity"] == "error"])
    return {
        "schema": SCHEMA,
        "stage": stage,
        "page_number": page_number,
        "valid": error_count == 0 and bool(workspace_containers),
        "container_count": len(workspace_containers),
        "slot_count": sum(len(item["work_slots"]) for item in workspace_containers),
        "containers": workspace_containers,
        "issues": issues,
        "error_count": error_count,
    }


def write_container_workspace(path: Path, workspace: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return workspace
