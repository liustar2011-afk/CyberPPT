"""Image-only, conservative typography estimates for OCR lines.

The raster does not contain enough information to identify a font reliably.
This module therefore reports measurable attributes and candidate families,
never a definitive font identity.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


_DEFAULT_FONTS = ["Arial", "Calibri", "Noto Sans CJK SC"]


def _catalog(path: Path | None) -> list[str]:
    if path is None or not Path(path).is_file():
        return list(_DEFAULT_FONTS)
    try:
        raw = Path(path).read_text(encoding="utf-8")
        value: Any = json.loads(raw) if Path(path).suffix.lower() == ".json" else raw.splitlines()
        if isinstance(value, dict):
            value = value.get("fonts", value.get("families", []))
        names = [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []
        return names[:8] or list(_DEFAULT_FONTS)
    except (OSError, ValueError, TypeError):
        return list(_DEFAULT_FONTS)


def _ink_stats(image: Image.Image) -> tuple[str | None, float]:
    pixels = list(image.convert("RGB").getdata())
    if not pixels:
        return None, 0.0
    background = Counter(pixels).most_common(1)[0][0]
    ink = [pixel for pixel in pixels if sum(abs(a - b) for a, b in zip(pixel, background)) > 18]
    if not ink:
        return None, 0.0
    color = Counter(ink).most_common(1)[0][0]
    return "#%02x%02x%02x" % color, len(ink) / len(pixels)


def infer_line_style(
    image: Image.Image,
    line: dict[str, Any],
    *,
    font_catalog: Path | None = None,
) -> dict[str, Any]:
    """Infer reviewable visual attributes from a line crop and OCR geometry."""
    crop = image
    glyph_crop = line.get("glyph_crop")
    if glyph_crop:
        try:
            with Image.open(glyph_crop) as opened:
                crop = opened.convert("RGB")
        except (OSError, TypeError):
            crop = image
    color, density = _ink_stats(crop)
    boxes = [item.get("bbox") for item in line.get("items", []) if isinstance(item, dict)]
    heights = [float(box[3]) - float(box[1]) for box in boxes if isinstance(box, (list, tuple)) and len(box) == 4]
    glyph_height = max(heights) if heights else float(line.get("line_height_px") or 0)
    font_size_px = round(glyph_height * 1.25, 2) if glyph_height else None
    line_height = line.get("line_height_px")
    line_height_px = round(float(line_height), 2) if isinstance(line_height, (int, float)) else None
    gaps = []
    ordered = sorted((box for box in boxes if isinstance(box, (list, tuple)) and len(box) == 4), key=lambda box: float(box[0]))
    for left, right in zip(ordered, ordered[1:]):
        gaps.append(max(0.0, float(right[0]) - float(left[2])))
    letter_spacing = round(sum(gaps) / len(gaps), 2) if gaps else 0.0
    weight = "700" if density >= 0.20 else "400"
    candidates = _catalog(font_catalog)
    confidence = {
        "font_family": 0.0,
        "similar_fonts": 0.2 if candidates else 0.0,
        "font_size_px": 0.65 if font_size_px is not None else 0.0,
        "font_size_pt": 0.65 if font_size_px is not None else 0.0,
        "font_weight": 0.45 if color is not None else 0.0,
        "color": 0.8 if color is not None else 0.0,
        "line_height_px": 0.9 if line_height_px is not None else 0.0,
        "letter_spacing_px": 0.35 if gaps else 0.2,
    }
    evidence = {
        "font_family": "Raster evidence cannot establish exact font identity",
        "similar_fonts": "Candidate families supplied for visual comparison only",
        "font_size_px": "Estimated from OCR glyph bounding-box height",
        "font_size_pt": "Converted from estimated pixels at 96 DPI",
        "font_weight": f"Ink density proxy ({density:.3f}); not an authored weight",
        "color": "Most frequent non-background pixel in the line crop",
        "line_height_px": "OCR line bounding-box height",
        "letter_spacing_px": "Mean gap between adjacent OCR item boxes",
    }
    return {
        "font_family": None,
        "similar_fonts": candidates,
        "font_size_px": font_size_px,
        "font_size_pt": round(font_size_px * 72 / 96, 2) if font_size_px is not None else None,
        "font_weight": weight,
        "color": color or line.get("dominant_fill"),
        "line_height_px": line_height_px,
        "letter_spacing_px": letter_spacing,
        "confidence": confidence,
        "evidence": evidence,
    }
