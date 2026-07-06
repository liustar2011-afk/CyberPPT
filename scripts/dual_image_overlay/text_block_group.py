from __future__ import annotations

from copy import deepcopy
import math
from typing import Any


EDIT_BEHAVIOR = "move_and_scale_as_group"


def _finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _xyxy(raw: Any) -> list[float] | None:
    if isinstance(raw, dict):
        if "bbox" in raw:
            return _xyxy(raw.get("bbox"))
        x = _finite_float(raw.get("x"))
        y = _finite_float(raw.get("y"))
        width = _finite_float(raw.get("w", raw.get("width")))
        height = _finite_float(raw.get("h", raw.get("height")))
        if x is None or y is None or width is None or height is None:
            return None
        return _ordered_bbox([x, y, x + width, y + height])
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    values = [_finite_float(value) for value in raw]
    if any(value is None for value in values):
        return None
    return _ordered_bbox(values)


def _ordered_bbox(values: list[float | None]) -> list[float] | None:
    if any(value is None for value in values):
        return None
    left, top, right, bottom = [float(value) for value in values]
    if right <= left or bottom <= top:
        return None
    return [left, top, right, bottom]


def _relative_bbox(line_bbox: list[float], root_bbox: list[float]) -> list[float]:
    return [
        round(line_bbox[0] - root_bbox[0], 2),
        round(line_bbox[1] - root_bbox[1], 2),
        round(line_bbox[2] - root_bbox[0], 2),
        round(line_bbox[3] - root_bbox[1], 2),
    ]


def _fallback_line_bbox(root_bbox: list[float], line_count: int, index: int) -> list[float]:
    line_count = max(1, line_count)
    block_height = max(1.0, root_bbox[3] - root_bbox[1])
    line_height = block_height / line_count
    top = root_bbox[1] + line_height * index
    bottom = root_bbox[1] + line_height * (index + 1)
    return [root_bbox[0], top, root_bbox[2], bottom]


def _invalid_geometry_bbox() -> list[float]:
    return [0.0, 0.0, 0.0, 0.0]


def _text_lines(text_block: dict[str, Any]) -> list[str]:
    text = str(text_block.get("final_text") or text_block.get("text") or text_block.get("ocr_text") or "")
    return text.splitlines() if text else []


def _scale_from_fit(fit: dict[str, Any] | None) -> float:
    if not isinstance(fit, dict):
        return 1.0
    scale = _finite_float(fit.get("scale"))
    if scale is None:
        return 1.0
    return max(0.0, scale)


def build_text_block_group(text_block: dict[str, Any], fit: dict[str, Any] | None = None) -> dict[str, Any]:
    """Represent a verified text block as one editable group.

    The block has exactly one scale and one fitted style. Line members keep
    their original relative offsets so downstream exporters can move and resize
    the text as a single unit instead of fitting lines independently.
    """

    block_id = str(text_block.get("id") or "text_block")
    parsed_root_bbox = _xyxy(text_block.get("bbox"))
    root_bbox = parsed_root_bbox or _invalid_geometry_bbox()
    root_bbox_valid = parsed_root_bbox is not None
    scale = round(_scale_from_fit(fit), 4)
    base_style = deepcopy(text_block.get("style") or {})
    fitted_style = deepcopy(fit.get("fitted_style") or base_style) if isinstance(fit, dict) else base_style
    lines = _text_lines(text_block)

    raw_line_boxes = text_block.get("line_boxes")
    raw_line_box_items = raw_line_boxes if isinstance(raw_line_boxes, (list, tuple)) else []
    parsed_line_boxes = [_xyxy(item) for item in raw_line_box_items]
    line_box_count_matches = len(parsed_line_boxes) == len(lines)

    review_reasons: list[str] = []
    if not root_bbox_valid:
        review_reasons.append("invalid_or_missing_root_bbox")
    if not isinstance(raw_line_boxes, (list, tuple)) or not raw_line_boxes:
        review_reasons.append("missing_line_boxes")
    elif not line_box_count_matches:
        review_reasons.append("line_box_count_mismatch")
    if any(item is None for item in parsed_line_boxes):
        review_reasons.append("invalid_line_box_geometry")

    members: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if not root_bbox_valid:
            line_bbox = _invalid_geometry_bbox()
            line_box_source = "invalid_root_bbox_fallback"
            used_fallback = True
        else:
            line_bbox = parsed_line_boxes[index] if index < len(parsed_line_boxes) else None
            used_fallback = line_bbox is None or not line_box_count_matches
            if used_fallback:
                line_bbox = _fallback_line_bbox(root_bbox, len(lines), index)
            line_box_source = "fallback" if used_fallback else "text_block.line_boxes"
        if line_bbox is None:
            line_bbox = _fallback_line_bbox(root_bbox, len(lines), index)
        members.append(
            {
                "member_id": f"{block_id}_line_{index + 1:02d}",
                "kind": "editable_text_line",
                "text": line,
                "line_index": index,
                "bbox": line_bbox,
                "relative_bbox": _relative_bbox(line_bbox, root_bbox),
                "style": deepcopy(fitted_style),
                "scale": scale,
                "metadata": {
                    "line_box_source": line_box_source,
                    "review_required": used_fallback,
                },
            }
        )

    return {
        "group_id": f"group_{block_id}",
        "text_block_id": block_id,
        "bbox": root_bbox,
        "transform": {
            "x": root_bbox[0],
            "y": root_bbox[1],
            "scale_x": scale,
            "scale_y": scale,
        },
        "members": members,
        "scale": scale,
        "edit_behavior": EDIT_BEHAVIOR,
        "metadata": {
            "status": "invalid_geometry" if not root_bbox_valid else "ok",
            "review_required": bool(review_reasons),
            "review_reasons": review_reasons,
            "line_box_count": len(raw_line_box_items),
            "line_count": len(lines),
        },
    }
