"""Line-level visual QA for reconstructed editable text."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageChops


MASK_THRESHOLD = 1
PASS_MASK_IOU = 0.55
PASS_COLOR_DISTANCE = 24.0
PASS_CONTRAST_RATIO = 3.0


def _bbox(line: Mapping[str, Any]) -> tuple[int, int, int, int]:
    target = line.get("target") if isinstance(line.get("target"), Mapping) else {}
    raw = target.get("bbox_px") if isinstance(target.get("bbox_px"), Mapping) else line.get("bbox")
    if not isinstance(raw, Mapping):
        raise ValueError(f"text line has no bbox: {line.get('line_id', '')}")
    x, y = int(raw["x"]), int(raw["y"])
    width, height = int(raw["width"]), int(raw["height"])
    if width <= 0 or height <= 0:
        raise ValueError(f"text line has invalid bbox: {line.get('line_id', '')}")
    return x, y, x + width, y + height


def _max_channel(image: Image.Image) -> Image.Image:
    red, green, blue = image.convert("RGB").split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def _foreground_mask(image: Image.Image, background: Image.Image) -> Image.Image:
    delta = _max_channel(ImageChops.difference(image.convert("RGB"), background.convert("RGB")))
    return delta.point(lambda value: 255 if value >= MASK_THRESHOLD else 0)


def _iou(first: Image.Image, second: Image.Image) -> float:
    first_values = list(first.get_flattened_data())
    second_values = list(second.get_flattened_data())
    intersection = sum(1 for left, right in zip(first_values, second_values) if left and right)
    union = sum(1 for left, right in zip(first_values, second_values) if left or right)
    return intersection / union if union else 0.0


def _mean_rgb(image: Image.Image, mask: Image.Image | None = None) -> tuple[int, int, int]:
    pixels = list(image.convert("RGB").get_flattened_data())
    if mask is not None:
        selected = [pixel for pixel, value in zip(pixels, mask.get_flattened_data()) if value]
        pixels = selected or pixels
    return tuple(int(round(sum(pixel[index] for pixel in pixels) / max(1, len(pixels)))) for index in range(3))


def _color_distance(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(first, second)))


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    channels = []
    for value in rgb:
        normalized = value / 255.0
        channels.append(normalized / 12.92 if normalized <= 0.03928 else ((normalized + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    left, right = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (left + 0.05) / (right + 0.05)


def compare_text_line(
    rendered_image: Image.Image,
    full_image: Image.Image,
    background_image: Image.Image,
    line: Mapping[str, Any],
    *,
    overflow: bool = False,
) -> dict[str, Any]:
    """Compare one rendered native text line with its FULL/BACKGROUND evidence."""

    box = _bbox(line)
    rendered = rendered_image.crop(box).convert("RGB")
    full = full_image.crop(box).convert("RGB")
    background = background_image.crop(box).convert("RGB")
    reference_mask = _foreground_mask(full, background)
    rendered_mask = _foreground_mask(rendered, background)
    mask_iou = _iou(reference_mask, rendered_mask)
    reference_color = _mean_rgb(full, reference_mask)
    rendered_color = _mean_rgb(rendered, rendered_mask)
    background_color = _mean_rgb(background)
    color_distance = _color_distance(reference_color, rendered_color)
    contrast_ratio = _contrast(rendered_color, background_color)
    status = "failed" if overflow else "passed"
    if not overflow and (
        mask_iou < PASS_MASK_IOU
        or color_distance > PASS_COLOR_DISTANCE
        or contrast_ratio < PASS_CONTRAST_RATIO
    ):
        status = "review"
    return {
        "line_id": str(line.get("line_id") or ""),
        "status": status,
        "mask_iou": round(mask_iou, 4),
        "color_distance_rgb": round(color_distance, 4),
        "contrast_ratio": round(contrast_ratio, 4),
        "reference_color": "#" + "".join(f"{value:02X}" for value in reference_color),
        "rendered_color": "#" + "".join(f"{value:02X}" for value in rendered_color),
        "overflow": bool(overflow),
    }


def compare_page_text_styles(
    rendered_path: str | Path,
    full_path: str | Path,
    background_path: str | Path,
    page_json_path: str | Path,
    output_path: str | Path,
    *,
    overflow: bool = False,
) -> dict[str, Any]:
    """Write a page-level report with one finding per stable line id."""

    page = json.loads(Path(page_json_path).read_text(encoding="utf-8"))
    with Image.open(rendered_path).convert("RGB") as rendered_source, Image.open(full_path).convert(
        "RGB"
    ) as full, Image.open(background_path).convert("RGB") as background:
        rendered = rendered_source.resize(full.size, Image.Resampling.LANCZOS)
        lines = [
            compare_text_line(rendered, full, background, line, overflow=overflow)
            for line in page.get("text_lines", [])
        ]
    status = "failed" if any(line["status"] == "failed" for line in lines) else "review" if any(
        line["status"] == "review" for line in lines
    ) else "passed"
    report = {
        "schema": "three-image.text-style-qa.v1",
        "status": status,
        "checks": {"line_count": len(lines)},
        "lines": lines,
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
