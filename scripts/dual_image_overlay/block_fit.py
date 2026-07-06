from __future__ import annotations

import math
import unicodedata
from typing import Any


DEFAULT_THRESHOLDS = {
    "auto_pass": 0.85,
    "warning": 0.70,
    "review": 0.60,
}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return parsed


def _strict_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _xyxy(raw: Any) -> list[float] | None:
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        values = [_float(value) for value in raw]
        if values[2] < values[0]:
            values[0], values[2] = values[2], values[0]
        if values[3] < values[1]:
            values[1], values[3] = values[3], values[1]
        return values
    if isinstance(raw, dict):
        if "bbox" in raw:
            return _xyxy(raw.get("bbox"))
        x = _float(raw.get("x"))
        y = _float(raw.get("y"))
        w = _float(raw.get("w", raw.get("width")))
        h = _float(raw.get("h", raw.get("height")))
        if w > 0.0 and h > 0.0:
            return [x, y, x + w, y + h]
    return None


def _bbox_size(raw: Any) -> tuple[float, float]:
    bbox = _xyxy(raw)
    if bbox is None:
        return 1.0, 1.0
    return max(1.0, bbox[2] - bbox[0]), max(1.0, bbox[3] - bbox[1])


def _strict_xyxy(raw: Any) -> list[float] | None:
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        values = [_strict_float(value) for value in raw]
        if any(value is None for value in values):
            return None
        left, top, right, bottom = values
        if right < left:
            left, right = right, left
        if bottom < top:
            top, bottom = bottom, top
        if right <= left or bottom <= top:
            return None
        return [left, top, right, bottom]
    if isinstance(raw, dict):
        if "bbox" in raw:
            return _strict_xyxy(raw.get("bbox"))
        x = _strict_float(raw.get("x"))
        y = _strict_float(raw.get("y"))
        width = _strict_float(raw.get("w", raw.get("width")))
        height = _strict_float(raw.get("h", raw.get("height")))
        if x is None or y is None or width is None or height is None:
            return None
        if width <= 0.0 or height <= 0.0:
            return None
        return [x, y, x + width, y + height]
    return None


def _strict_bbox_size(raw: Any) -> tuple[float, float] | None:
    bbox = _strict_xyxy(raw)
    if bbox is None:
        return None
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _container_size(container: dict[str, Any]) -> tuple[float, float] | None:
    if not isinstance(container, dict):
        return None
    if "text_safe_bbox" in container:
        return _strict_bbox_size(container.get("text_safe_bbox"))
    if "bbox" in container:
        return _strict_bbox_size(container.get("bbox"))
    return _strict_bbox_size(container)


def _line_boxes_extent(line_boxes: Any) -> tuple[float, float] | None:
    if not isinstance(line_boxes, list):
        return None
    boxes = [_xyxy(item) for item in line_boxes]
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = max(box[2] for box in boxes)
    bottom = max(box[3] for box in boxes)
    return max(1.0, right - left), max(1.0, bottom - top)


def _char_width_factor(char: str) -> float:
    if char.isspace():
        return 0.35
    if ord(char) <= 127:
        if char.isupper():
            return 0.68
        if char.isdigit() or char in ".%,:;/\\|":
            return 0.60
        return 0.62
    east_asian_width = unicodedata.east_asian_width(char)
    if east_asian_width in {"F", "W"}:
        return 1.0
    return 0.85


def _text_width(text: str, font_size: float) -> float:
    return max(1.0, sum(_char_width_factor(char) * font_size for char in text))


def _text_lines(text_block: dict[str, Any]) -> list[str]:
    text = str(text_block.get("final_text") or text_block.get("text") or "")
    lines = text.splitlines()
    return lines or [""]


def _natural_block_size(text_block: dict[str, Any], font_size: float, line_height: float) -> tuple[float, float]:
    lines = _text_lines(text_block)
    estimated_width = max(_text_width(line, font_size) for line in lines)
    estimated_height = font_size + max(0, len(lines) - 1) * font_size * line_height

    bbox_width, bbox_height = _bbox_size(text_block.get("bbox") or text_block)
    line_extent = _line_boxes_extent(text_block.get("line_boxes"))
    if line_extent is None:
        evidence_width, evidence_height = bbox_width, bbox_height
    else:
        evidence_width, evidence_height = line_extent

    return max(estimated_width, evidence_width), max(estimated_height, evidence_height)


def _threshold_status(scale: float, thresholds: dict[str, float]) -> tuple[str, bool]:
    if scale >= thresholds["auto_pass"]:
        return "auto_pass", False
    if scale >= thresholds["warning"]:
        return "warning", False
    if scale >= thresholds["review"]:
        return "review_recommended", True
    return "blocked_too_small", True


def _active_thresholds(thresholds: dict[str, float] | None) -> dict[str, float]:
    active = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    for key in DEFAULT_THRESHOLDS:
        active[key] = _float(active.get(key), DEFAULT_THRESHOLDS[key])
    return active


def _reported_scale(raw_scale: float) -> float:
    bounded = min(1.0, max(0.0, raw_scale))
    return math.floor(bounded * 10000.0) / 10000.0


def fit_text_block_to_container(
    text_block: dict[str, Any],
    container: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Fit a complete text block with one uniform scale.

    The function intentionally preserves the incoming text and line structure.
    It computes one block-level scale from the widest line and total block
    height; callers can apply that same scale to font size, line height, and
    internal line offsets.
    """

    active_thresholds = _active_thresholds(thresholds)
    style = dict(text_block.get("style") or {})
    font_size = max(1.0, _float(style.get("font_size"), 12.0))
    line_height = max(1.0, _float(style.get("line_height"), 1.36))

    container_size = _container_size(container)
    if container_size is None:
        fitted_style = dict(style)
        fitted_style["font_size"] = 0.0
        fitted_style["line_height"] = line_height
        fitted_style["block_scale"] = 0.0
        fitted_style["internal_offset_scale"] = 0.0
        return {
            "mode": "uniform_block_scale",
            "scale": 0.0,
            "status": "invalid_container",
            "review_required": True,
            "fitted_style": fitted_style,
        }

    container_width, container_height = container_size
    natural_width, natural_height = _natural_block_size(text_block, font_size, line_height)
    raw_scale = min(1.0, container_width / natural_width, container_height / natural_height)
    scale = _reported_scale(raw_scale)

    status, review_required = _threshold_status(scale, active_thresholds)
    fitted_style = dict(style)
    fitted_style["font_size"] = round(font_size * scale, 2)
    fitted_style["line_height"] = line_height
    fitted_style["block_scale"] = scale
    fitted_style["internal_offset_scale"] = scale

    return {
        "mode": "uniform_block_scale",
        "scale": scale,
        "status": status,
        "review_required": review_required,
        "fitted_style": fitted_style,
    }
