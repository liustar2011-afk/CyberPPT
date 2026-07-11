"""Deterministic line-level OCR evidence extraction.

This module deliberately keeps the OCR observations intact while adding a
stable reading order and small, reviewable image crops for each reconstructed
line.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


SCHEMA_VERSION = "1.0"


def _bbox(item: dict[str, Any]) -> tuple[float, float, float, float]:
    values = item.get("bbox")
    if not isinstance(values, (list, tuple)) or len(values) != 4:
        raise ValueError("OCR item bbox must contain four numbers")
    x1, y1, x2, y2 = (float(value) for value in values)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("OCR item bbox must satisfy x2>x1 and y2>y1")
    return x1, y1, x2, y2


def _same_line(item: tuple[dict[str, Any], tuple[float, float, float, float]],
               line: list[tuple[dict[str, Any], tuple[float, float, float, float]]]) -> bool:
    _, (x1, y1, x2, y2) = item
    height = y2 - y1
    center = (y1 + y2) / 2
    ly1 = min(box[1] for _, box in line)
    ly2 = max(box[3] for _, box in line)
    lheight = max(box[3] - box[1] for _, box in line)
    lcenter = sum((box[1] + box[3]) / 2 for _, box in line) / len(line)
    overlap = max(0.0, min(y2, ly2) - max(y1, ly1))
    overlap_ratio = overlap / max(1.0, min(height, lheight))
    normalized_distance = abs(center - lcenter) / max(1.0, height, lheight)
    return overlap_ratio >= 0.35 or normalized_distance <= 0.45


def _dominant_fill(image: Image.Image, boxes: list[tuple[int, int, int, int]]) -> str | None:
    pixels: list[tuple[int, int, int]] = []
    for box in boxes:
        pixels.extend(image.crop(box).convert("RGB").getdata())
    if not pixels:
        return None
    # Ignore the usual near-white slide background when estimating glyph fill.
    # The most frequent color in an OCR box is normally its fill/background;
    # discard it before selecting the glyph/interior color. This also avoids
    # padded slide backgrounds and colored decoration dominating the result.
    background = Counter(pixels).most_common(1)[0][0]
    ink = [pixel for pixel in pixels if sum(abs(a - b) for a, b in zip(pixel, background)) > 18]
    sample = ink or pixels
    color = Counter(sample).most_common(1)[0][0]
    return "#%02x%02x%02x" % color


def build_line_evidence(
    layout: dict[str, Any],
    image_path: Path,
    *,
    evidence_dir: Path,
) -> dict[str, Any]:
    """Cluster normalized OCR items into lines and persist bounded evidence crops."""
    image_path = Path(image_path).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    size = layout.get("image_size") or {}
    declared_width = int(float(size.get("width", 0)))
    declared_height = int(float(size.get("height", 0)))
    if declared_width <= 0 or declared_height <= 0:
        raise ValueError("layout image_size must contain positive width and height")

    with Image.open(image_path) as source:
        image = source.convert("RGB")
        actual_width, actual_height = image.size
        items: list[tuple[dict[str, Any], tuple[float, float, float, float]]] = []
        sx, sy = actual_width / declared_width, actual_height / declared_height
        for raw in layout.get("items", []):
            if not isinstance(raw, dict) or not str(raw.get("text") or "").strip():
                continue
            source_box = _bbox(raw)
            observed = dict(raw)
            observed["source_bbox"] = list(source_box)
            observed["bbox"] = [source_box[0] * sx, source_box[1] * sy, source_box[2] * sx, source_box[3] * sy]
            if isinstance(raw.get("polygon"), list):
                observed["source_polygon"] = raw["polygon"]
                observed["polygon"] = [[float(point[0]) * sx, float(point[1]) * sy] for point in raw["polygon"] if isinstance(point, (list, tuple)) and len(point) >= 2]
            items.append((observed, _bbox(observed)))

        # Sort before clustering so equivalent OCR permutations produce the
        # same groups and reading order.
        items.sort(key=lambda pair: ((pair[1][1] + pair[1][3]) / 2, pair[1][0], pair[1][1], str(pair[0].get("text") or "")))
        lines: list[list[tuple[dict[str, Any], tuple[float, float, float, float]]]] = []
        for item in items:
            candidates = [line for line in lines if _same_line(item, line)]
            if candidates:
                min_y = min(min(box[1] for _, box in line) for line in candidates)
                target = min(candidates, key=lambda line: (abs(min_y - item[1][1]), min(box[0] for _, box in line)))
                target.append(item)
            else:
                lines.append([item])
        lines.sort(key=lambda line: (min(box[1] for _, box in line), min(box[0] for _, box in line)))

        line_records: list[dict[str, Any]] = []
        padding = 3
        for reading_order, line in enumerate(lines, start=1):
            line.sort(key=lambda pair: (pair[1][0], pair[1][1]))
            x1 = max(0, int(min(box[0] for _, box in line)) - padding)
            y1 = max(0, int(min(box[1] for _, box in line)) - padding)
            x2 = min(actual_width, int(max(box[2] for _, box in line)) + padding)
            y2 = min(actual_height, int(max(box[3] for _, box in line)) + padding)
            crop_name = f"line_{reading_order:03d}.png"
            crop_path = evidence_dir / crop_name
            image.crop((x1, y1, x2, y2)).save(crop_path)
            observed = "".join(str(item.get("text") or "").strip() for item, _ in line)
            boxes = [list(box) for _, box in line]
            source_boxes = [list(item.get("source_bbox", box)) for item, box in line]
            polygons = [item.get("polygon") for item, _ in line if item.get("polygon") is not None]
            source_polygons = [item.get("source_polygon") for item, _ in line if item.get("source_polygon") is not None]
            record: dict[str, Any] = {
                "observed_text": observed,
                "polygon": polygons[0] if len(polygons) == 1 else polygons,
                "source_polygon": source_polygons[0] if len(source_polygons) == 1 else source_polygons,
                "bbox": [x1, y1, x2, y2],
                "source_bbox": source_boxes,
                "confidence": min(float(item.get("confidence", 1.0)) for item, _ in line),
                "reading_order": reading_order,
                "glyph_crop": str(crop_path),
                "dominant_fill": _dominant_fill(image, [(int(box[0]), int(box[1]), int(box[2]), int(box[3])) for _, box in line]),
                "line_height_px": max(box[3] for _, box in line) - min(box[1] for _, box in line),
                "items": [{"text": item.get("text"), "bbox": list(box), "polygon": item.get("polygon")} for item, box in line],
            }
            line_records.append(record)

        scale = {"x": sx, "y": sy}
        return {
            "schema_version": SCHEMA_VERSION,
            "image": {"path": str(image_path), "width": actual_width, "height": actual_height, "declared_width": declared_width, "declared_height": declared_height, "scale": scale},
            "model": {"source": layout.get("backend", "ocr")},
            "lines": line_records,
            "quality": {"item_count": len(items), "line_count": len(line_records), "scale": scale},
            "artifacts": {"evidence_dir": str(evidence_dir)},
        }
