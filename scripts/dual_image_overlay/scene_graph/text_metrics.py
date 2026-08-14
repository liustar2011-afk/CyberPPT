"""Deterministic text measurement, fitting, and reserved-zone avoidance.

The functions use the PPT Master DrawingML estimator when it is importable and
fall back to a conservative CJK-aware estimate. They return diagnostics rather
than silently shrinking text below the readability floor.
"""

from __future__ import annotations

import importlib
import math
import unicodedata
from typing import Any, Mapping

from .schema import BBox


DEFAULT_MIN_FONT_SIZE = 7.0
DEFAULT_LINE_HEIGHT = 1.2


def _char_factor(char: str) -> float:
    if char.isspace():
        return 0.35
    if ord(char) <= 127:
        return 0.62 if not char.isdigit() else 0.58
    return 1.0 if unicodedata.east_asian_width(char) in {"F", "W"} else 0.85


def _ppt_master_width(text: str, font_size: float, font_family: str | None) -> float | None:
    try:
        module = importlib.import_module("svg_to_pptx.drawingml.elements")
        estimator = getattr(module, "estimate_single_line_text_frame_width", None)
        if estimator is None:
            return None
        runs = [{"text": text, "font_size": float(font_size), "font_family": font_family or "Microsoft YaHei"}]
        value = float(estimator(runs))
        return value if math.isfinite(value) and value > 0 else None
    except (ImportError, OSError, TypeError, ValueError):
        return None


def measure_line(text: str, font_size: float, *, font_family: str | None = None) -> dict[str, Any]:
    host_width = _ppt_master_width(text, font_size, font_family)
    if host_width is not None:
        return {"width": round(host_width, 3), "method": "ppt_master_drawingml"}
    width = max(1.0, sum(_char_factor(char) * float(font_size) for char in str(text)))
    return {"width": round(width, 3), "method": "cjk_conservative_fallback"}


def measure_text(text: str, font_size: float, *, line_height: float = DEFAULT_LINE_HEIGHT, font_family: str | None = None) -> dict[str, Any]:
    lines = str(text).splitlines() or [""]
    measured = [measure_line(line, font_size, font_family=font_family) for line in lines]
    return {
        "width": max(item["width"] for item in measured),
        "height": round(max(1.0, len(lines) * float(font_size) * float(line_height)), 3),
        "line_count": len(lines),
        "method": "+".join(sorted({item["method"] for item in measured})),
    }


def _wrap(text: str, font_size: float, width: float, *, font_family: str | None) -> str:
    paragraphs: list[str] = []
    for paragraph in str(text).splitlines() or [""]:
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and measure_line(candidate, font_size, font_family=font_family)["width"] > width:
                paragraphs.append(current)
                current = char
            else:
                current = candidate
        paragraphs.append(current)
    return "\n".join(paragraphs)


def fit_text_to_safe_bbox(
    text: str,
    safe_bbox: BBox | list[float] | Mapping[str, Any],
    preferred_font_size: float,
    *,
    font_family: str | None = None,
    line_height: float = DEFAULT_LINE_HEIGHT,
    min_font_size: float = DEFAULT_MIN_FONT_SIZE,
) -> dict[str, Any]:
    """Fit by wrapping first, then uniform font reduction, never silently overflow."""
    safe = BBox.from_any(safe_bbox)
    width = max(1.0, safe.x2 - safe.x1)
    height = max(1.0, safe.y2 - safe.y1)
    size = max(float(min_font_size), float(preferred_font_size))
    while True:
        wrapped = _wrap(text, size, width, font_family=font_family)
        measured = measure_text(wrapped, size, line_height=line_height, font_family=font_family)
        if measured["width"] <= width + 0.01 and measured["height"] <= height + 0.01:
            return {"status": "fit" if size >= preferred_font_size else "fit_after_scale", "text": wrapped, "font_size": round(size, 2), "bbox": safe.as_list(), "measured": measured, "min_font_size": min_font_size}
        if size <= min_font_size + 0.01:
            return {"status": "blocked_overflow", "text": wrapped, "font_size": round(size, 2), "bbox": safe.as_list(), "measured": measured, "min_font_size": min_font_size, "reason": "readability_floor_reached"}
        size = max(float(min_font_size), round(size - 0.5, 2))


def _overlap(a: BBox, b: BBox, gap: float) -> bool:
    return not (a.x2 + gap <= b.x1 or b.x2 + gap <= a.x1 or a.y2 + gap <= b.y1 or b.y2 + gap <= a.y1)


def avoid_reserved_zones(
    bbox: BBox | list[float] | Mapping[str, Any],
    safe_bbox: BBox | list[float] | Mapping[str, Any],
    reserved_zones: list[Mapping[str, Any] | list[float]] | None,
    *,
    gap: float = 4.0,
) -> dict[str, Any]:
    """Move a text box within its safe area when it collides with reserved zones."""
    original = BBox.from_any(bbox)
    safe = BBox.from_any(safe_bbox)
    zones = [BBox.from_any(zone) for zone in (reserved_zones or [])]
    current = original
    for zone in zones:
        if not _overlap(current, zone, gap):
            continue
        candidates = [
            BBox(current.x1, zone.y2 + gap, current.x2, zone.y2 + gap + (current.y2 - current.y1)),
            BBox(zone.x2 + gap, current.y1, zone.x2 + gap + (current.x2 - current.x1), current.y2),
            BBox(current.x1, zone.y1 - gap - (current.y2 - current.y1), current.x2, zone.y1 - gap),
        ]
        valid = [candidate for candidate in candidates if candidate.x1 >= safe.x1 and candidate.y1 >= safe.y1 and candidate.x2 <= safe.x2 and candidate.y2 <= safe.y2]
        if not valid:
            return {"status": "blocked_reserved_zone", "bbox": current.as_list(), "collisions": [zone.as_list()]}
        current = valid[0]
    return {"status": "shifted" if current != original else "clear", "bbox": current.as_list(), "collisions": []}

