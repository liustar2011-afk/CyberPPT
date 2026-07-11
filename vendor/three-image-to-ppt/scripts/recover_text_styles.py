"""Recover editable text appearance from registered FULL/BACKGROUND/TEXT images."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from PIL import Image, ImageChops, ImageFilter

from scripts.models import BBox


TEXT_MASK_THRESHOLD = 18
FULL_BACKGROUND_DELTA_THRESHOLD = 18
MIN_COLOR_PIXELS = 20


@dataclass(frozen=True)
class RecoveredColor:
    hex_color: str
    confidence: float
    method: str
    sample_count: int


def _crop_box(bbox: BBox) -> tuple[int, int, int, int]:
    return bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height


def _quantized(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(min(255, int(round(channel / 8.0) * 8)) for channel in rgb)


def _dominant_rgb(pixels: Iterable[tuple[int, int, int]]) -> tuple[tuple[int, int, int], float, int]:
    values = list(pixels)
    if not values:
        return (16, 24, 32), 0.0, 0
    buckets = Counter(_quantized(value) for value in values)
    key, count = buckets.most_common(1)[0]
    selected = [value for value in values if _quantized(value) == key]
    color = tuple(int(round(sum(value[index] for value in selected) / len(selected))) for index in range(3))
    color = tuple(0 if channel <= 4 else 255 if channel >= 251 else channel for channel in color)
    return color, count / len(values), len(values)


def _dominant_border_color(image: Image.Image) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    border: list[tuple[int, int, int]] = []
    for x in range(width):
        border.append(pixels[x, 0])
        if height > 1:
            border.append(pixels[x, height - 1])
    for y in range(1, max(1, height - 1)):
        border.append(pixels[0, y])
        if width > 1:
            border.append(pixels[width - 1, y])
    color, _, _ = _dominant_rgb(border)
    return color


def _max_channel(image: Image.Image) -> Image.Image:
    red, green, blue = image.convert("RGB").split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def build_text_mask(text_image: Image.Image, bbox: BBox) -> Image.Image:
    """Return a binary foreground mask for one OCR line in the TEXT image."""

    crop = text_image.crop(_crop_box(bbox))
    if "A" in crop.getbands():
        alpha = crop.getchannel("A")
        minimum, maximum = alpha.getextrema()
        if minimum < maximum:
            return alpha.point(lambda value: 255 if value >= TEXT_MASK_THRESHOLD else 0).filter(
                ImageFilter.MedianFilter(3)
            )
    rgb = crop.convert("RGB")
    background = Image.new("RGB", rgb.size, _dominant_border_color(rgb))
    delta = _max_channel(ImageChops.difference(rgb, background))
    return delta.point(lambda value: 255 if value >= TEXT_MASK_THRESHOLD else 0).filter(
        ImageFilter.MedianFilter(3)
    )


def _masked_pixels(image: Image.Image, mask: Image.Image) -> list[tuple[int, int, int]]:
    rgb = image.convert("RGB")
    rgb_values = list(rgb.get_flattened_data())
    mask_values = list(mask.get_flattened_data())
    return [rgb for rgb, selected in zip(rgb_values, mask_values) if selected]


def _hex_color(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


def recover_line_color(
    full_image: Image.Image,
    background_image: Image.Image,
    text_image: Image.Image,
    bbox: BBox,
) -> RecoveredColor:
    """Recover the visible glyph color using TEXT geometry and FULL/BACKGROUND delta."""

    mask = build_text_mask(text_image, bbox)
    full_crop = full_image.crop(_crop_box(bbox)).convert("RGB")
    background_crop = background_image.crop(_crop_box(bbox)).convert("RGB")
    delta = _max_channel(ImageChops.difference(full_crop, background_crop))
    valid_mask = ImageChops.multiply(
        mask,
        delta.point(lambda value: 255 if value >= FULL_BACKGROUND_DELTA_THRESHOLD else 0),
    )
    mask_count = sum(1 for value in mask.get_flattened_data() if value)
    pixels = _masked_pixels(full_crop, valid_mask)
    if len(pixels) >= MIN_COLOR_PIXELS:
        color, dominance, count = _dominant_rgb(pixels)
        coverage = min(1.0, count / max(1, mask_count))
        confidence = min(1.0, 0.80 * coverage + 0.20 * dominance)
        return RecoveredColor(_hex_color(color), confidence, "full_background_delta", count)

    text_crop = text_image.crop(_crop_box(bbox)).convert("RGB")
    fallback_pixels = _masked_pixels(text_crop, mask)
    color, _, count = _dominant_rgb(fallback_pixels)
    return RecoveredColor(_hex_color(color), 0.45 if count else 0.0, "text_fallback", count)
