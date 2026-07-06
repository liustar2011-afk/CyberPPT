from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image


SCHEMA = "cyberppt.dual_image.container_workspace.v1"
VISUAL_EXCLUDED_TYPES = {"container", "text", "text_box", "text_object"}
VISUAL_OCCUPIED_TYPES = {
    "icon",
    "number",
    "index",
    "badge",
    "arrow",
    "line",
    "shape",
    "visual",
    "decoration",
    "image",
}
SLOT_PADDING_PX = 4.0
MIN_SLOT_W = 18.0
MIN_SLOT_H = 12.0
BACKGROUND_PANEL_INTERSECTION_RATIO = 0.70
TEXT_PROVES_WRITABLE_OVERLAP_RATIO = 0.55
DEFAULT_CANVAS_WIDTH = 1672.0
DEFAULT_CANVAS_HEIGHT = 941.0


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


def _intersection_area(a: dict[str, float], b: dict[str, float]) -> float:
    ax1, ay1, ax2, ay2 = _xyxy_from_rect(a)
    bx1, by1, bx2, by2 = _xyxy_from_rect(b)
    return max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))


def _is_background_panel_zone(rect: dict[str, float], safe: dict[str, float], item: dict[str, Any]) -> bool:
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    inventory_source = source.get("inventory_source")
    kind = _visual_kind(item).lower()
    safe_area = _rect_area(safe)
    if safe_area <= 0:
        return False
    if inventory_source != "background_visual_component" or kind not in {"shape", "visual"}:
        return False
    return _intersection_area(rect, safe) / safe_area >= BACKGROUND_PANEL_INTERSECTION_RATIO


def _source_text_proves_writable(
    *,
    rect: dict[str, float],
    container_id: str,
    text_items: list[dict[str, Any]],
    item: dict[str, Any],
) -> bool:
    kind = _visual_kind(item).lower()
    if kind not in {"shape", "visual", "decoration"}:
        return False
    rect_area = _rect_area(rect)
    if rect_area <= 0:
        return False
    for text_item in text_items:
        if str(text_item.get("container_id") or "") != container_id:
            continue
        if _role(text_item) in {"index", "icon_label", "bullet_marker"}:
            continue
        text_rect = _text_rect(text_item)
        text_area = _rect_area(text_rect)
        if text_area <= 0:
            continue
        overlap_ratio = _intersection_area(rect, text_rect) / min(rect_area, text_area)
        if overlap_ratio >= TEXT_PROVES_WRITABLE_OVERLAP_RATIO:
            return True
    return False


def _contains_point(rect: dict[str, float], x: float, y: float) -> bool:
    x1, y1, x2, y2 = _xyxy_from_rect(rect)
    return x1 <= x <= x2 and y1 <= y <= y2


def _normalize_rect(rect: dict[str, Any]) -> dict[str, float]:
    xyxy = _xyxy_from_rect(rect)
    return _rect_from_xyxy(xyxy)


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


def _element_rect(item: dict[str, Any]) -> dict[str, float] | None:
    for key in ("bbox", "blueprint_bbox_px", "render_bbox_px", "ppt_target_bbox_px"):
        raw = item.get(key)
        if isinstance(raw, list) and len(raw) == 4:
            rect = _rect_from_xyxy(_bbox_xyxy(raw))
            if _rect_area(rect) > 0:
                return rect
        if isinstance(raw, dict):
            rect = _text_rect(raw)
            if _rect_area(rect) > 0:
                return rect
    rect = _text_rect(item)
    if _rect_area(rect) > 0:
        return rect
    return None


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
        for key in ("text_safe_bbox", "safe_bbox", "safe_area"):
            raw = container.get(key)
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


def _source_kind(item: dict[str, Any]) -> str:
    source = item.get("source")
    if isinstance(source, dict):
        value = source.get("kind")
        if isinstance(value, str) and value.strip():
            return value.strip()
    value = item.get("source")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "visual_element_inventory"


def _visual_kind(item: dict[str, Any]) -> str:
    for key in ("kind", "element_type", "type", "role"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "visual"


def _visual_occupied_zones(
    *,
    container_id: str,
    safe: dict[str, float],
    text_items: list[dict[str, Any]],
    visual_elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for index, item in enumerate(visual_elements, start=1):
        kind = _visual_kind(item)
        kind_norm = kind.lower()
        if kind_norm in VISUAL_EXCLUDED_TYPES:
            continue
        if kind_norm not in VISUAL_OCCUPIED_TYPES and _source_kind(item) != "visual_element_registry":
            continue
        rect = _element_rect(item)
        if rect is None or not _intersects(rect, safe):
            continue
        if _is_background_panel_zone(rect, safe, item):
            continue
        if _source_text_proves_writable(
            rect=rect,
            container_id=container_id,
            text_items=text_items,
            item=item,
        ):
            continue
        zones.append(
            {
                "id": f"{container_id}_visual_occupied_{index:03d}",
                "kind": kind,
                "source": _source_kind(item),
                "element_id": item.get("element_id") or item.get("id"),
                "bbox": rect,
            }
        )
    return zones


def _background_occupied_zones(
    *,
    container_id: str,
    safe: dict[str, float],
    background_image: Path | None,
) -> list[dict[str, Any]]:
    if background_image is None or not background_image.exists() or _rect_area(safe) <= 0:
        return []
    try:
        image = Image.open(background_image).convert("L")
    except OSError:
        return []
    width, height = image.size
    sx = width / DEFAULT_CANVAS_WIDTH
    sy = height / DEFAULT_CANVAS_HEIGHT
    x1, y1, x2, y2 = _xyxy_from_rect(safe)
    px1 = max(0, min(width, int(round(x1 * sx))))
    py1 = max(0, min(height, int(round(y1 * sy))))
    px2 = max(0, min(width, int(round(x2 * sx))))
    py2 = max(0, min(height, int(round(y2 * sy))))
    if px2 <= px1 or py2 <= py1:
        return []
    crop = image.crop((px1, py1, px2, py2))
    tile = 12
    dark_tiles: list[tuple[int, int, int, int]] = []
    for ty in range(0, crop.height, tile):
        for tx in range(0, crop.width, tile):
            box = (tx, ty, min(crop.width, tx + tile), min(crop.height, ty + tile))
            tile_image = crop.crop(box)
            flattened = getattr(tile_image, "get_flattened_data", tile_image.getdata)
            pixels = list(flattened())
            if not pixels:
                continue
            dark_ratio = sum(1 for value in pixels if value < 145) / len(pixels)
            if dark_ratio >= 0.18:
                dark_tiles.append(box)
    if not dark_tiles:
        return []
    # Coarse componenting is enough here: the slot refiner will only trim where zones intersect.
    min_x = min(item[0] for item in dark_tiles)
    min_y = min(item[1] for item in dark_tiles)
    max_x = max(item[2] for item in dark_tiles)
    max_y = max(item[3] for item in dark_tiles)
    rect = {
        "x": round((px1 + min_x) / sx, 3),
        "y": round((py1 + min_y) / sy, 3),
        "w": round((max_x - min_x) / sx, 3),
        "h": round((max_y - min_y) / sy, 3),
    }
    if _rect_area(rect) < 24.0:
        return []
    return [
        {
            "id": f"{container_id}_background_occupied_001",
            "kind": "background_dark_region",
            "source": "background_image_dark_region",
            "bbox": rect,
        }
    ]


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


def _largest_clear_rect(slot: dict[str, float], zone: dict[str, float]) -> dict[str, float]:
    sx1, sy1, sx2, sy2 = _xyxy_from_rect(slot)
    zx1, zy1, zx2, zy2 = _xyxy_from_rect(zone)
    candidates = [
        {"x": sx1, "y": sy1, "w": max(0.0, zx1 - sx1 - SLOT_PADDING_PX), "h": sy2 - sy1},
        {"x": zx2 + SLOT_PADDING_PX, "y": sy1, "w": max(0.0, sx2 - zx2 - SLOT_PADDING_PX), "h": sy2 - sy1},
        {"x": sx1, "y": sy1, "w": sx2 - sx1, "h": max(0.0, zy1 - sy1 - SLOT_PADDING_PX)},
        {"x": sx1, "y": zy2 + SLOT_PADDING_PX, "w": sx2 - sx1, "h": max(0.0, sy2 - zy2 - SLOT_PADDING_PX)},
    ]
    viable = [item for item in candidates if item["w"] >= MIN_SLOT_W and item["h"] >= MIN_SLOT_H]
    if not viable:
        return slot
    return _normalize_rect(max(viable, key=_rect_area))


def _refine_slots_against_zones(
    *,
    container_id: str,
    slots: list[dict[str, Any]],
    occupied_zones: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    refined: list[dict[str, Any]] = []
    for slot in slots:
        slot_copy = json.loads(json.dumps(slot, ensure_ascii=False))
        adjustments: list[dict[str, Any]] = []
        for zone in occupied_zones:
            bbox = zone.get("bbox") if isinstance(zone.get("bbox"), dict) else {}
            if not _intersects(slot_copy["bbox"], bbox):
                continue
            before = dict(slot_copy["bbox"])
            after = _largest_clear_rect(before, bbox)
            if after == before or _intersects(after, bbox):
                issues.append(
                    {
                        "severity": "error",
                        "code": "occupied_zone_intersects_slot",
                        "container_id": container_id,
                        "slot_id": slot_copy.get("id"),
                        "occupied_zone": zone.get("id"),
                    }
                )
                continue
            slot_copy["bbox"] = after
            adjustments.append(
                {
                    "code": "subtract_occupied_zone",
                    "occupied_zone": zone.get("id"),
                    "source": zone.get("source"),
                    "from_bbox": before,
                    "to_bbox": after,
                }
            )
        if adjustments:
            slot_copy["slot_adjustments"] = adjustments
            slot_copy["capacity"] = {
                **(slot_copy.get("capacity") if isinstance(slot_copy.get("capacity"), dict) else {}),
                "area": round(_rect_area(slot_copy["bbox"]), 3),
                "source": "safe_zone_minus_occupied_zones",
            }
        if _rect_area(slot_copy["bbox"]) > 0:
            refined.append(slot_copy)
    return refined


def _page_understanding_workspace_containers(page_understanding: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(page_understanding, dict):
        return []
    containers = page_understanding.get("containers")
    if not isinstance(containers, list):
        return []

    workspace_containers: list[dict[str, Any]] = []
    for index, container in enumerate(containers, start=1):
        if not isinstance(container, dict):
            continue
        container_id = _container_id(container, index)
        bbox = _container_rect(container)
        safe = _safe_rect(container)
        if _rect_area(safe) <= 0:
            continue
        slot = {
            "id": f"{container_id}_body_slot",
            "bbox": safe,
            "preferred_roles": ["body", "bullet", "description", "title", "ability_title"],
            "capacity": {"area": round(_rect_area(safe), 3), "source": "page_understanding_text_safe_bbox"},
            "source": "page_understanding",
        }
        workspace_containers.append(
            {
                "id": container_id,
                "role": _container_role(container),
                "container_bbox": bbox,
                "text_safe_bbox": safe,
                "occupied_zones": [],
                "work_slots": [slot],
                "slot_count": 1,
                "source": "page_understanding",
            }
        )
    return workspace_containers


def build_container_workspace(
    *,
    page_number: int | None,
    containers: list[Any],
    text_items: list[dict[str, Any]],
    stage: str,
    visual_elements: list[dict[str, Any]] | None = None,
    background_image: Path | None = None,
    page_understanding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workspace_containers = []
    issues: list[dict[str, Any]] = []

    page_understanding_containers = _page_understanding_workspace_containers(page_understanding)
    if page_understanding_containers:
        workspace_containers.extend(page_understanding_containers)
    else:
        for index, container in enumerate(containers, start=1):
            container_id = _container_id(container, index)
            bbox = _container_rect(container)
            safe = _safe_rect(container)
            occupied_zones = [
                *_text_occupied_zones(container_id, text_items),
                *_visual_occupied_zones(
                    container_id=container_id,
                    safe=safe,
                    text_items=text_items,
                    visual_elements=visual_elements or [],
                ),
                *_background_occupied_zones(
                    container_id=container_id,
                    safe=safe,
                    background_image=background_image,
                ),
            ]
            slots = _slots_for_container(container_id=container_id, safe=safe, text_items=text_items)
            slots = _refine_slots_against_zones(
                container_id=container_id,
                slots=slots,
                occupied_zones=occupied_zones,
                issues=issues,
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
