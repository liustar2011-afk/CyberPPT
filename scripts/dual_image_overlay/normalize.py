from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PIL import Image


CANVAS = (1672, 941)


def scale_bbox(
    bbox: Sequence[float],
    *,
    source_size: tuple[int | float, int | float],
    canvas: tuple[int, int] = CANVAS,
) -> list[float]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain four values")
    src_w, src_h = float(source_size[0]), float(source_size[1])
    if src_w <= 0 or src_h <= 0:
        raise ValueError("source_size must be positive")

    x1, y1, x2, y2 = [float(value) for value in bbox]
    if x2 <= x1 or y2 <= y1:
        raise ValueError("bbox must satisfy x2>x1 and y2>y1")

    sx = canvas[0] / src_w
    sy = canvas[1] / src_h
    return [
        round(x1 * sx, 3),
        round(y1 * sy, 3),
        round(x2 * sx, 3),
        round(y2 * sy, 3),
    ]


def relative_bbox(container_bbox: Sequence[float], rel: Sequence[float]) -> list[float]:
    if len(container_bbox) != 4:
        raise ValueError("container_bbox must contain four values")
    if len(rel) != 4:
        raise ValueError("relative_bbox must contain four values")

    cx1, cy1, cx2, cy2 = [float(value) for value in container_bbox]
    rx1, ry1, rx2, ry2 = [float(value) for value in rel]
    if cx2 <= cx1 or cy2 <= cy1:
        raise ValueError("container_bbox must satisfy x2>x1 and y2>y1")
    if rx2 <= rx1 or ry2 <= ry1:
        raise ValueError("relative_bbox must satisfy x2>x1 and y2>y1")
    if min(rx1, ry1, rx2, ry2) < 0 or max(rx1, ry1, rx2, ry2) > 1:
        raise ValueError("relative_bbox values must be within 0..1")

    width = cx2 - cx1
    height = cy2 - cy1
    return [
        round(cx1 + rx1 * width, 3),
        round(cy1 + ry1 * height, 3),
        round(cx1 + rx2 * width, 3),
        round(cy1 + ry2 * height, 3),
    ]


def normalize_image(source: Path, target: Path, canvas: tuple[int, int] = CANVAS) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.convert("RGB").resize(canvas, Image.Resampling.LANCZOS).save(target)
