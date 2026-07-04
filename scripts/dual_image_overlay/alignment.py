from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from .normalize import CANVAS


@dataclass(frozen=True)
class AlignmentTransform:
    scale: float = 1.0
    dx: float = 0.0
    dy: float = 0.0
    score: float = 0.0
    model: str = "uniform-scale-translation"

    def map_point(self, x: float, y: float, canvas: tuple[int, int] = CANVAS) -> tuple[float, float]:
        cx = canvas[0] / 2.0
        cy = canvas[1] / 2.0
        return (
            cx + (x - cx) * self.scale + self.dx,
            cy + (y - cy) * self.scale + self.dy,
        )

    def map_bbox(self, bbox: list[float], canvas: tuple[int, int] = CANVAS) -> list[float]:
        x1, y1 = self.map_point(bbox[0], bbox[1], canvas)
        x2, y2 = self.map_point(bbox[2], bbox[3], canvas)
        return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def semantic_plan_owns_geometry(plan_has_containers: bool) -> bool:
    return plan_has_containers


def _make_text_mask(
    items: list[dict[str, Any]],
    *,
    canvas: tuple[int, int],
    scale_to: tuple[int, int],
    inflate: int = 8,
) -> Image.Image:
    mask = Image.new("L", scale_to, 255)
    draw = ImageDraw.Draw(mask)
    sx = scale_to[0] / canvas[0]
    sy = scale_to[1] / canvas[1]
    for item in items:
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = [float(v) for v in bbox]
        box = [
            (x1 - inflate) * sx,
            (y1 - inflate) * sy,
            (x2 + inflate) * sx,
            (y2 + inflate) * sy,
        ]
        draw.rectangle(box, fill=0)
    return mask


def _transform_image_low(
    image: Image.Image,
    *,
    scale: float,
    dx: float,
    dy: float,
    size: tuple[int, int],
) -> Image.Image:
    cx = size[0] / 2.0
    cy = size[1] / 2.0
    matrix = (
        1.0 / scale,
        0.0,
        (cx * (scale - 1.0) - dx) / scale,
        0.0,
        1.0 / scale,
        (cy * (scale - 1.0) - dy) / scale,
    )
    return image.transform(size, Image.Transform.AFFINE, matrix, resample=Image.Resampling.BILINEAR)


def estimate_alignment(
    full_image: Path,
    background_image: Path,
    layout: dict[str, Any],
    *,
    canvas: tuple[int, int] = CANVAS,
    low_size: tuple[int, int] = (320, 180),
    max_shift_px: int = 48,
) -> AlignmentTransform:
    """Estimate a small uniform scale + translation from full image to background.

    This is ported from a legacy dual-image geometry helper. It is a
    fallback for diagnostic layouts; production plans should prefer explicit
    semantic containers and use identity geometry.
    """
    with Image.open(full_image) as full_raw, Image.open(background_image) as bg_raw:
        full = full_raw.convert("L").resize(low_size, Image.Resampling.LANCZOS).filter(ImageFilter.FIND_EDGES)
        bg = bg_raw.convert("L").resize(low_size, Image.Resampling.LANCZOS).filter(ImageFilter.FIND_EDGES)

    text_mask = _make_text_mask(layout.get("items", []), canvas=canvas, scale_to=low_size)
    low_max_dx = max(1, round(max_shift_px * low_size[0] / canvas[0]))
    low_max_dy = max(1, round(max_shift_px * low_size[1] / canvas[1]))
    scale_values = (0.98, 0.99, 1.0, 1.01, 1.02)
    best: tuple[float, float, float, float] | None = None

    for scale in scale_values:
        for dx in range(-low_max_dx, low_max_dx + 1):
            for dy in range(-low_max_dy, low_max_dy + 1):
                transformed_full = _transform_image_low(full, scale=scale, dx=dx, dy=dy, size=low_size)
                transformed_mask = _transform_image_low(text_mask, scale=scale, dx=dx, dy=dy, size=low_size)
                diff = ImageChops.difference(transformed_full, bg)
                masked = ImageChops.multiply(diff, transformed_mask)
                valid = max(1.0, ImageStat.Stat(transformed_mask).sum[0] / 255.0)
                score = ImageStat.Stat(masked).sum[0] / valid
                if best is None or score < best[0]:
                    best = (score, scale, dx, dy)

    if best is None:
        return AlignmentTransform()
    score, scale, low_dx, low_dy = best
    return AlignmentTransform(
        scale=scale,
        dx=low_dx * canvas[0] / low_size[0],
        dy=low_dy * canvas[1] / low_size[1],
        score=score,
    )
