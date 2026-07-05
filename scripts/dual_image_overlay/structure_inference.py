from __future__ import annotations

from statistics import median
from typing import Any


SCHEMA = "cyberppt.dual_image.structure_inference.v1"
DEFAULT_CANVAS = {"width": 1280.0, "height": 720.0}


def _rect(item: dict[str, Any]) -> dict[str, float]:
    raw = item.get("bbox")
    if isinstance(raw, dict):
        try:
            x = float(raw.get("x", 0.0) or 0.0)
            y = float(raw.get("y", 0.0) or 0.0)
            w = float(raw.get("w", raw.get("width", 0.0)) or 0.0)
            h = float(raw.get("h", raw.get("height", 0.0)) or 0.0)
        except (TypeError, ValueError):
            return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
        return {"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3)}
    if isinstance(raw, list) and len(raw) == 4:
        try:
            x1, y1, x2, y2 = [float(value) for value in raw]
        except (TypeError, ValueError):
            return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
        return {"x": round(x1, 3), "y": round(y1, 3), "w": round(max(0.0, x2 - x1), 3), "h": round(max(0.0, y2 - y1), 3)}
    try:
        return {
            "x": round(float(item.get("x", 0.0) or 0.0), 3),
            "y": round(float(item.get("y", 0.0) or 0.0), 3),
            "w": round(float(item.get("w", 0.0) or 0.0), 3),
            "h": round(float(item.get("h", 0.0) or 0.0), 3),
        }
    except (TypeError, ValueError):
        return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}


def _area(rect: dict[str, float]) -> float:
    return max(0.0, rect["w"]) * max(0.0, rect["h"])


def _center_x(item: dict[str, Any]) -> float:
    rect = _rect(item)
    return rect["x"] + rect["w"] / 2


def _center_y(item: dict[str, Any]) -> float:
    rect = _rect(item)
    return rect["y"] + rect["h"] / 2


def _union(items: list[dict[str, Any]], *, padding: float, canvas: dict[str, float]) -> dict[str, float]:
    rects = [_rect(item) for item in items if _area(_rect(item)) > 0]
    if not rects:
        return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
    x1 = max(0.0, min(rect["x"] for rect in rects) - padding)
    y1 = max(0.0, min(rect["y"] for rect in rects) - padding)
    x2 = min(float(canvas["width"]), max(rect["x"] + rect["w"] for rect in rects) + padding)
    y2 = min(float(canvas["height"]), max(rect["y"] + rect["h"] for rect in rects) + padding)
    return {"x": round(x1, 3), "y": round(y1, 3), "w": round(max(0.0, x2 - x1), 3), "h": round(max(0.0, y2 - y1), 3)}


def _cluster_rows(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not items:
        return []
    heights = [max(1.0, _rect(item)["h"]) for item in items if _area(_rect(item)) > 0]
    tolerance = max(16.0, median(heights or [18.0]) * 1.4)
    rows: list[list[dict[str, Any]]] = []
    for item in sorted(items, key=_center_y):
        center = _center_y(item)
        for row in rows:
            row_center = median(_center_y(existing) for existing in row)
            if abs(center - row_center) <= tolerance:
                row.append(item)
                break
        else:
            rows.append([item])
    return rows


def _cluster_columns(items: list[dict[str, Any]], *, canvas: dict[str, float]) -> list[list[dict[str, Any]]]:
    if not items:
        return []
    centers = sorted(_center_x(item) for item in items)
    widths = [max(1.0, _rect(item)["w"]) for item in items if _area(_rect(item)) > 0]
    threshold = max(80.0, min(180.0, median(widths or [120.0]) * 0.8))
    threshold = min(threshold, float(canvas["width"]) * 0.14)
    columns: list[list[dict[str, Any]]] = []
    for item in sorted(items, key=_center_x):
        center = _center_x(item)
        if not columns:
            columns.append([item])
            continue
        previous_center = median(_center_x(existing) for existing in columns[-1])
        if center - previous_center > threshold:
            columns.append([item])
        else:
            columns[-1].append(item)
    if len(columns) <= 1 and len(centers) >= 3:
        return [[item] for item in sorted(items, key=_center_x)]
    return columns


def _inside(rect: dict[str, float], container: dict[str, float]) -> bool:
    cx = rect["x"] + rect["w"] / 2
    cy = rect["y"] + rect["h"] / 2
    return container["x"] <= cx <= container["x"] + container["w"] and container["y"] <= cy <= container["y"] + container["h"]


def _nearest_container_id(rect: dict[str, float], containers: list[dict[str, Any]]) -> str:
    cx = rect["x"] + rect["w"] / 2
    cy = rect["y"] + rect["h"] / 2
    best_id = ""
    best_distance = float("inf")
    for container in containers:
        bbox = _rect(container)
        if _inside(rect, bbox):
            return str(container["id"])
        ccx = bbox["x"] + bbox["w"] / 2
        ccy = bbox["y"] + bbox["h"] / 2
        distance = abs(cx - ccx) + abs(cy - ccy)
        if distance < best_distance:
            best_id = str(container["id"])
            best_distance = distance
    return best_id


def infer_structure_containers(
    *,
    page_number: int | None,
    text_items: list[dict[str, Any]],
    canvas: dict[str, Any] | None = None,
) -> dict[str, Any]:
    canvas_px = {
        "width": float((canvas or {}).get("width") or DEFAULT_CANVAS["width"]),
        "height": float((canvas or {}).get("height") or DEFAULT_CANVAS["height"]),
    }
    valid_items = [item for item in text_items if _area(_rect(item)) > 0]
    rows = _cluster_rows(valid_items)
    row_groups = [
        row
        for row in rows
        if len(row) >= 2 and (_union(row, padding=0, canvas=canvas_px)["w"] >= canvas_px["width"] * 0.45 or len(row) >= 3)
    ]
    top_rows = [row for row in row_groups if median(_center_y(item) for item in row) <= canvas_px["height"] * 0.32]
    bottom_rows = [row for row in row_groups if median(_center_y(item) for item in row) >= canvas_px["height"] * 0.78]
    top_items = [item for row in top_rows for item in row]
    top_items.extend(
        item
        for item in valid_items
        if _center_y(item) <= canvas_px["height"] * 0.32
        and _rect(item)["w"] >= canvas_px["width"] * 0.4
        and id(item) not in {id(existing) for existing in top_items}
    )
    bottom_items = [item for row in bottom_rows for item in row]
    reserved = {id(item) for item in top_items + bottom_items}
    middle_items = [item for item in valid_items if id(item) not in reserved]
    columns = [column for column in _cluster_columns(middle_items, canvas=canvas_px) if column]

    containers: list[dict[str, Any]] = []
    if top_items:
        containers.append(_container("inferred_row_band_top", "row_band", top_items, canvas_px))
    for index, column in enumerate(columns, start=1):
        if len(column) >= 2:
            containers.append(_container(f"inferred_panel_{index:02d}", "repeated_panel", column, canvas_px))
    if bottom_items:
        containers.append(_container("inferred_row_band_bottom", "row_band", bottom_items, canvas_px))

    assigned_items = []
    for item in text_items:
        updated = dict(item)
        if containers and not updated.get("container_id"):
            updated["container_id"] = _nearest_container_id(_rect(item), containers)
        assigned_items.append(updated)

    return {
        "schema": SCHEMA,
        "page_number": page_number,
        "valid": bool(containers) and all(item.get("container_id") for item in assigned_items if _area(_rect(item)) > 0),
        "container_count": len(containers),
        "containers": containers,
        "text_items": assigned_items,
    }


def _container(container_id: str, role: str, items: list[dict[str, Any]], canvas: dict[str, float]) -> dict[str, Any]:
    bbox = _union(items, padding=18.0, canvas=canvas)
    return {
        "id": container_id,
        "role": role,
        **bbox,
        "bbox": [bbox["x"], bbox["y"], bbox["x"] + bbox["w"], bbox["y"] + bbox["h"]],
        "text_safe_bbox": bbox,
        "source": "structure_inference",
        "text_count": len(items),
    }
