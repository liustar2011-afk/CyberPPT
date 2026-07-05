from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from PIL import Image


SKIP_ROLES = {"bullet_marker", "index"}


def _bbox(box: dict[str, Any]) -> list[float]:
    raw = box.get("bbox")
    if not isinstance(raw, list) or len(raw) != 4:
        return [0.0, 0.0, 0.0, 0.0]
    try:
        return [float(value) for value in raw]
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0, 0.0]


def _role(box: dict[str, Any]) -> str:
    for key in ("semantic_role", "role", "typography_role"):
        value = box.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _text_units(text: str) -> float:
    units = 0.0
    for char in str(text):
        if ord(char) > 127:
            units += 1.0
        elif char.isspace():
            units += 0.3
        elif char.isdigit() or char in ".%":
            units += 0.58
        else:
            units += 0.56
    return max(units, 1.0)


def _required_width_px(text: str, font_size_pt: float, *, headroom: float) -> float:
    # Office uses point sizes; 1pt is roughly 1.333px at the 96dpi coordinate
    # basis used by the rebuild pipeline. Headroom absorbs CJK metric variance.
    return _text_units(text) * font_size_pt * 1.333 / headroom


def _is_vertical_or_tall(box: dict[str, Any]) -> bool:
    x1, y1, x2, y2 = _bbox(box)
    return (y2 - y1) > max(28.0, (x2 - x1) * 1.8)


def _expand_interval_around_center(start: float, end: float, required: float, lower: float, upper: float) -> tuple[float, float]:
    required = min(max(required, 1.0), max(1.0, upper - lower))
    center = (start + end) / 2.0
    new_start = center - required / 2.0
    new_end = center + required / 2.0
    if new_start < lower:
        new_start = lower
        new_end = lower + required
    if new_end > upper:
        new_end = upper
        new_start = upper - required
    return max(lower, new_start), min(upper, new_end)


def _set_y(box: dict[str, Any], y1: float, y2: float) -> None:
    x1, _old_y1, x2, _old_y2 = _bbox(box)
    box["bbox"] = [round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3)]


def _set_bbox(box: dict[str, Any], bbox: list[float]) -> None:
    box["bbox"] = [round(float(value), 3) for value in bbox]


def _assignment_by_index(workspace_assignment: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not isinstance(workspace_assignment, dict):
        return {}
    result: dict[int, dict[str, Any]] = {}
    for item in workspace_assignment.get("assignments", []):
        if not isinstance(item, dict):
            continue
        try:
            result[int(item["text_index"])] = item
        except (KeyError, TypeError, ValueError):
            continue
    return result


def _slot_bounds(assignment: dict[str, Any] | None, *, width: float, height: float) -> tuple[float, float, float, float]:
    if not isinstance(assignment, dict):
        return 0.0, 0.0, width, height
    slot = assignment.get("slot_bbox")
    if not isinstance(slot, dict):
        return 0.0, 0.0, width, height
    try:
        x = float(slot.get("x", 0.0) or 0.0)
        y = float(slot.get("y", 0.0) or 0.0)
        w = float(slot.get("w", slot.get("width", 0.0)) or 0.0)
        h = float(slot.get("h", slot.get("height", 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0, 0.0, width, height
    if w <= 0 or h <= 0:
        return 0.0, 0.0, width, height
    return max(0.0, x), max(0.0, y), min(width, x + w), min(height, y + h)


def _nearest_bullet_for_detail(boxes: list[dict[str, Any]], old_detail: list[float]) -> dict[str, Any] | None:
    old_center = (old_detail[1] + old_detail[3]) / 2.0
    candidates = [
        box
        for box in boxes
        if _role(box) == "bullet_marker"
        and abs(((_bbox(box)[1] + _bbox(box)[3]) / 2.0) - old_center) <= 4.0
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda box: abs(_bbox(box)[0] - old_detail[0]))


def _candidate_title_for_detail(title_box: list[float], detail_box: list[float]) -> tuple[float, float] | None:
    title_w = max(1.0, title_box[2] - title_box[0])
    title_h = max(1.0, title_box[3] - title_box[1])
    title_center_x = (title_box[0] + title_box[2]) / 2.0
    detail_center_x = (detail_box[0] + detail_box[2]) / 2.0
    vertical_gap = detail_box[1] - title_box[3]
    horizontal_gap = abs(detail_center_x - title_center_x)
    horizontal_radius = max(title_w, 90.0)
    vertical_window = min(92.0, title_h * 6.0)
    if vertical_gap < 4.0 or vertical_gap > vertical_window:
        return None
    if horizontal_gap > horizontal_radius:
        return None
    return vertical_gap, horizontal_gap


def _assign_details_to_nearest_titles(boxes: list[dict[str, Any]]) -> dict[int, list[int]]:
    title_indices = [
        idx
        for idx, box in enumerate(boxes)
        if _role(box) == "parallel_title"
    ]
    groups: dict[int, list[int]] = {idx: [] for idx in title_indices}
    for detail_idx, detail in enumerate(boxes):
        if _role(detail) != "body":
            continue
        detail_box = _bbox(detail)
        candidates: list[tuple[float, float, int]] = []
        for title_idx in title_indices:
            candidate = _candidate_title_for_detail(_bbox(boxes[title_idx]), detail_box)
            if candidate is not None:
                vertical_gap, horizontal_gap = candidate
                candidates.append((vertical_gap, horizontal_gap, title_idx))
        if not candidates:
            continue
        _vertical_gap, _horizontal_gap, title_idx = min(candidates)
        groups[title_idx].append(detail_idx)
    return groups


def _compact_generic_title_detail_groups(boxes: list[dict[str, Any]], groups: dict[int, list[int]]) -> list[dict[str, Any]]:
    adjustments: list[dict[str, Any]] = []
    title_indices = [idx for idx, box in enumerate(boxes) if _role(box) == "parallel_title"]
    for title_idx in title_indices:
        detail_indices = groups.get(title_idx, [])
        if len(detail_indices) < 2:
            continue
        title = boxes[title_idx]
        title_box = _bbox(title)
        title_h = max(1.0, title_box[3] - title_box[1])
        detail_indices = sorted(detail_indices, key=lambda idx: _bbox(boxes[idx])[1])
        nearby_indexes = [
            box
            for box in boxes
            if _role(box) == "index"
            and _bbox(box)[2] <= title_box[0]
            and abs(((_bbox(box)[1] + _bbox(box)[3]) / 2.0) - ((title_box[1] + title_box[3]) / 2.0)) <= title_h * 1.8
        ]
        if nearby_indexes:
            index_box = min(nearby_indexes, key=lambda box: abs(_bbox(box)[2] - title_box[0]))
            new_title_y1 = min(title_box[1], max(0.0, _bbox(index_box)[1] - title_h * 0.1))
            if round(new_title_y1, 3) != round(title_box[1], 3):
                old_title = _bbox(title)
                _set_y(title, new_title_y1, new_title_y1 + title_h)
                title_box = _bbox(title)
                adjustments.append({"text": title.get("text"), "from_bbox": old_title, "to_bbox": title_box})
        detail_h = max(_bbox(boxes[idx])[3] - _bbox(boxes[idx])[1] for idx in detail_indices)
        gap = max(0.5, detail_h * 0.07)
        first_y = title_box[3] + max(2.0, title_h * 0.28)
        for detail_idx in detail_indices:
            detail = boxes[detail_idx]
            old_detail = _bbox(detail)
            _set_y(detail, first_y, first_y + detail_h)
            adjustments.append({"text": detail.get("text"), "from_bbox": old_detail, "to_bbox": _bbox(detail)})
            bullet = _nearest_bullet_for_detail(boxes, old_detail)
            if bullet is not None:
                bullet_h = _bbox(bullet)[3] - _bbox(bullet)[1]
                center = first_y + detail_h / 2.0
                _set_y(bullet, center - bullet_h / 2.0, center + bullet_h / 2.0)
            first_y += detail_h + gap
    return adjustments


def _load_dark_horizontal_rows(background_image: Path | None, canvas: dict[str, float]) -> list[float]:
    if background_image is None:
        return []
    try:
        image = Image.open(background_image).convert("L")
    except (FileNotFoundError, OSError):
        return []
    width, height = image.size
    if width <= 0 or height <= 0:
        return []
    pixels = image.load()
    rows: list[float] = []
    min_dark_run = max(18, int(width * 0.05))
    for y in range(height):
        run = 0
        best = 0
        for x in range(width):
            if pixels[x, y] < 225:
                run += 1
                best = max(best, run)
            else:
                run = 0
        if best >= min_dark_run:
            rows.append(y * float(canvas["height"]) / height)
    clustered: list[float] = []
    for row in rows:
        if not clustered or row - clustered[-1] > 1.2:
            clustered.append(row)
        else:
            clustered[-1] = (clustered[-1] + row) / 2.0
    return clustered


def _clear_band_for_box(box: list[float], rows: list[float], canvas_height: float) -> tuple[float, float] | None:
    x1, y1, x2, y2 = box
    _ = (x1, x2)
    near = [row for row in rows if y1 - 20.0 <= row <= y2 + 20.0]
    if len(near) < 2:
        return None
    center = (y1 + y2) / 2.0
    above = [row for row in near if row <= center]
    below = [row for row in near if row >= center]
    top = max(above) if above else max(0.0, y1 - 20.0)
    bottom = min(below) if below else min(canvas_height, y2 + 20.0)
    if bottom - top < 10.0:
        return None
    return top, bottom


def _has_adjacent_parallel_title(boxes: list[dict[str, Any]], index: int) -> bool:
    box = _bbox(boxes[index])
    center_x = (box[0] + box[2]) / 2.0
    height = max(1.0, box[3] - box[1])
    for other_index, other in enumerate(boxes):
        if other_index == index or _role(other) != "parallel_title":
            continue
        other_box = _bbox(other)
        other_center_x = (other_box[0] + other_box[2]) / 2.0
        width = max(1.0, box[2] - box[0])
        other_width = max(1.0, other_box[2] - other_box[0])
        width_similarity = min(width, other_width) / max(width, other_width)
        horizontal_gap = abs(other_center_x - center_x)
        vertical_gap = max(other_box[1] - box[3], box[1] - other_box[3], 0.0)
        if width_similarity >= 0.45 and horizontal_gap <= max(width, other_width) * 0.45 and vertical_gap <= height * 0.5:
            return True
    return False


def _fit_isolated_labels_to_clear_bands(
    boxes: list[dict[str, Any]],
    groups: dict[int, list[int]],
    rows: list[float],
    *,
    min_font_size: float,
    canvas_height: float,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    adjustments: list[dict[str, Any]] = []
    for idx, box in enumerate(boxes):
        old_box = _bbox(box)
        label_h = max(1.0, old_box[3] - old_box[1])
        if (
            _role(box) != "parallel_title"
            or groups.get(idx)
            or _is_vertical_or_tall(box)
            or label_h > 24.0
            or _has_adjacent_parallel_title(boxes, idx)
        ):
            continue
        interior_top = old_box[1] + label_h * 0.25
        interior_bottom = old_box[3] - label_h * 0.1
        if not any(interior_top <= row <= interior_bottom for row in rows):
            continue
        band = _clear_band_for_box(old_box, rows, canvas_height)
        if band is None:
            continue
        top, bottom = band
        target_font = min(float(box.get("font_size") or min_font_size), min_font_size)
        target_height = target_font * 1.6
        available = max(1.0, bottom - top - 2.0)
        if target_height > available:
            target_height = available
            target_font = max(1.0, target_height / 1.6)
        y1 = top + (bottom - top - target_height) / 2.0
        y2 = y1 + target_height
        changed = (
            round(float(box.get("font_size") or 0.0), 3) != round(target_font, 3)
            or round(old_box[1], 3) != round(y1, 3)
            or round(old_box[3], 3) != round(y2, 3)
        )
        if not changed:
            continue
        box["font_size"] = round(target_font, 2)
        _set_bbox(box, [old_box[0], y1, old_box[2], y2])
        adjustments.append(
            {
                "text": box.get("text"),
                "from_bbox": old_box,
                "to_bbox": _bbox(box),
                "to_font_size": round(target_font, 2),
                "code": "isolated_label_fit_to_clear_band",
            }
        )
    return adjustments


def apply_office_textbox_fit(
    boxes: list[dict[str, Any]],
    *,
    canvas: dict[str, float] | None = None,
    min_font_size: float = 9.0,
    headroom: float = 0.86,
    background_image: Path | None = None,
    workspace_assignment: dict[str, Any] | None = None,
    report_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Expand transparent text boxes and compact related text groups for Office."""
    width = float((canvas or {}).get("width") or 1280.0)
    height = float((canvas or {}).get("height") or 720.0)
    fitted = [copy.deepcopy(box) for box in boxes]
    adjustments: list[dict[str, Any]] = []
    assignment_adjustments: list[dict[str, Any]] = []
    skipped = 0
    below_minimum = 0
    assignment_map = _assignment_by_index(workspace_assignment)

    for index, box in enumerate(fitted):
        text = str(box.get("text") or "")
        role = _role(box)
        if not text.strip() or role in SKIP_ROLES or text.strip() in {"•", "·", "-"} or _is_vertical_or_tall(box):
            skipped += 1
            continue

        x1, y1, x2, y2 = _bbox(box)
        slot_x1, slot_y1, slot_x2, slot_y2 = _slot_bounds(assignment_map.get(index), width=width, height=height)
        x1 = min(max(x1, slot_x1), max(slot_x1, slot_x2 - 1.0))
        x2 = min(max(x2, x1 + 1.0), slot_x2)
        y1 = min(max(y1, slot_y1), max(slot_y1, slot_y2 - 1.0))
        y2 = min(max(y2, y1 + 1.0), slot_y2)
        current_width = max(1.0, x2 - x1)
        current_height = max(1.0, y2 - y1)
        original_font_size = float(box.get("font_size") or 0.0)
        target_font = max(original_font_size, min_font_size)
        required_width = _required_width_px(text, target_font, headroom=headroom)
        new_x1, new_x2 = x1, x2
        align = str(box.get("align") or "left")
        if required_width > current_width:
            if align == "center":
                new_x1, new_x2 = _expand_interval_around_center(x1, x2, required_width, slot_x1, slot_x2)
            elif x1 + required_width <= slot_x2:
                new_x2 = x1 + required_width
            else:
                new_x1 = max(slot_x1, slot_x2 - required_width)
                new_x2 = slot_x2

        available = max(1.0, new_x2 - new_x1)
        if available + 0.01 < required_width:
            target_font = max(1.0, available * headroom / (_text_units(text) * 1.333))
            if target_font < min_font_size:
                below_minimum += 1

        required_height = max(current_height, target_font * 1.6)
        new_y1, new_y2 = _expand_interval_around_center(y1, y2, required_height, slot_y1, slot_y2)
        changed = (
            round(original_font_size, 3) != round(target_font, 3)
            or round(new_x1, 3) != round(x1, 3)
            or round(new_x2, 3) != round(x2, 3)
            or round(new_y1, 3) != round(y1, 3)
            or round(new_y2, 3) != round(y2, 3)
        )
        box["font_size"] = round(target_font, 2)
        box["bbox"] = [round(new_x1, 3), round(new_y1, 3), round(new_x2, 3), round(new_y2, 3)]
        box["wrap"] = False
        if index in assignment_map:
            box["workspace_assignment"] = {
                "assigned_slot": assignment_map[index].get("assigned_slot"),
                "slot_bbox": assignment_map[index].get("slot_bbox"),
            }
            assignment_adjustments.append(
                {
                    "index": index,
                    "text": text,
                    "assigned_slot": assignment_map[index].get("assigned_slot"),
                    "to_bbox": box["bbox"],
                    "code": "constrained_to_workspace_slot",
                }
            )
        if changed:
            box["office_textbox_fit"] = {
                "min_font_size": min_font_size,
                "required_width_px": round(required_width, 3),
                "required_height_px": round(required_height, 3),
                "original_bbox": [x1, y1, x2, y2],
            }
            adjustments.append(
                {
                    "index": index,
                    "text": text,
                    "from_bbox": [x1, y1, x2, y2],
                    "to_bbox": box["bbox"],
                    "from_font_size": original_font_size,
                    "to_font_size": round(target_font, 2),
                    "code": "textbox_expanded_before_font_reduction",
                }
            )

    canvas_info = {"width": width, "height": height}
    title_detail_groups = _assign_details_to_nearest_titles(fitted)
    generic_group_adjustments = _compact_generic_title_detail_groups(fitted, title_detail_groups)
    horizontal_rows = _load_dark_horizontal_rows(background_image, canvas_info)
    isolated_label_adjustments = _fit_isolated_labels_to_clear_bands(
        fitted,
        title_detail_groups,
        horizontal_rows,
        min_font_size=min_font_size,
        canvas_height=height,
    )
    report = {
        "schema": "cyberppt.dual_image.office_textbox_fit.v1",
        "valid": below_minimum == 0,
        "checks": {
            "textbox_expanded_before_font_reduction": True,
            "generic_title_detail_spacing_compacted": True,
            "isolated_label_clear_band_fit": bool(background_image),
            "workspace_assignment_consumed": bool(assignment_map),
            "minimum_font_size_pt": min_font_size,
        },
        "adjustments": adjustments,
        "generic_title_detail_adjustments": generic_group_adjustments,
        "isolated_label_adjustments": isolated_label_adjustments,
        "workspace_assignment_adjustments": assignment_adjustments,
        "expanded_count": len(adjustments),
        "workspace_assignment_consumed_count": len(assignment_adjustments),
        "generic_title_detail_compacted_count": len({item["text"] for item in generic_group_adjustments if item.get("text")}),
        "isolated_label_adjusted_count": len(isolated_label_adjustments),
        "skipped_count": skipped,
        "below_minimum_count": below_minimum,
        "error_count": below_minimum,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fitted, report
