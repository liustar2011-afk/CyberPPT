"""Recover editable text appearance from registered FULL/BACKGROUND/TEXT images."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from scripts.font_resolver import resolve_font_face
from scripts.models import BBox, TextLine, TextRun


TEXT_MASK_THRESHOLD = 18
FULL_BACKGROUND_DELTA_THRESHOLD = 18
MIN_COLOR_PIXELS = 20
FONT_LIMITS_PT = {
    "page_title": (20.0, 26.0),
    "section_title": (14.0, 18.0),
    "headline_number": (28.0, 40.0),
    "percentage": (20.0, 28.0),
    "card_title": (13.0, 18.0),
    "body": (10.5, 18.0),
    "label": (9.0, 12.0),
    "footer_conclusion": (16.0, 22.0),
}


@dataclass(frozen=True)
class RecoveredColor:
    hex_color: str
    confidence: float
    method: str
    sample_count: int


@dataclass(frozen=True)
class RecoveredFont:
    font_family: str
    font_size_px: float
    weight: str
    confidence: float
    mask_iou: float
    width_similarity: float
    height_similarity: float


@dataclass(frozen=True)
class RecoveredAlignment:
    align: str
    confidence: float


@dataclass(frozen=True)
class StyleRecoveryResult:
    lines: tuple[TextLine, ...]
    review_items: tuple[Mapping[str, Any], ...]


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


def _trimmed(mask: Image.Image) -> Image.Image:
    binary = mask.convert("L").point(lambda value: 255 if value else 0)
    bounds = binary.getbbox()
    return binary.crop(bounds) if bounds is not None else Image.new("L", (1, 1), 0)


def _render_text_mask(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    left, top, right, bottom = font.getbbox(text)
    width = max(1, right - left)
    height = max(1, bottom - top)
    image = Image.new("L", (width, height), 0)
    ImageDraw.Draw(image).text((-left, -top), text, font=font, fill=255)
    return image


def _mask_iou(first: Image.Image, second: Image.Image) -> float:
    target = _trimmed(first)
    candidate = _trimmed(second).resize(target.size, Image.Resampling.NEAREST)
    target_values = list(target.get_flattened_data())
    candidate_values = list(candidate.get_flattened_data())
    intersection = sum(1 for left, right in zip(target_values, candidate_values) if left and right)
    union = sum(1 for left, right in zip(target_values, candidate_values) if left or right)
    return intersection / union if union else 0.0


def _dimension_similarity(first: int, second: int) -> float:
    return min(first, second) / max(1, max(first, second))


def classify_text_role(text: str, bbox: BBox) -> str:
    """Classify a visual line without page-specific wording."""

    compact = re.sub(r"\s+", "", text)
    if re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?%", compact):
        return "percentage"
    numeric_count = sum(character.isdigit() for character in compact)
    if numeric_count >= 3 and (numeric_count / max(1, len(compact)) >= 0.45 or bbox.height >= 55):
        return "headline_number"
    if len(compact) <= 5 and bbox.height <= 50:
        return "label"
    if 8 <= len(compact) <= 18 and bbox.height <= 52:
        return "section_title"
    return "body"


def _pt_candidates(role: str) -> list[float]:
    minimum, maximum = FONT_LIMITS_PT.get(role, (9.0, 18.0))
    count = int(round((maximum - minimum) * 2))
    return [maximum - index * 0.5 for index in range(count + 1)]


def fit_font_style(
    text: str,
    source_mask: Image.Image,
    bbox: BBox,
    font_family: str = "Microsoft YaHei",
) -> RecoveredFont:
    """Fit installed font size and weight to an extracted glyph mask."""

    source = _trimmed(source_mask)
    source_width, source_height = source.size
    role = classify_text_role(text, bbox)
    candidates_pt = _pt_candidates(role)
    best: tuple[float, float, str, float, float, float] | None = None
    for weight in ("light", "regular", "bold"):
        font_path = resolve_font_face(font_family, weight)
        for size_pt in candidates_pt:
            measured_px = max(1, round(size_pt * 96.0 / 72.0))
            font = ImageFont.truetype(str(font_path), measured_px)
            candidate = _render_text_mask(text, font)
            if candidate.width > bbox.width * 0.90 or candidate.height > bbox.height * 0.82:
                continue
            width_similarity = _dimension_similarity(source_width, candidate.width)
            height_similarity = _dimension_similarity(source_height, candidate.height)
            mask_iou = _mask_iou(source, candidate)
            score = 0.55 * mask_iou + 0.25 * width_similarity + 0.20 * height_similarity
            if best is None or score > best[0]:
                best = (score, size_pt, weight, mask_iou, width_similarity, height_similarity)
    if best is None:
        minimum_pt = FONT_LIMITS_PT.get(role, (9.0, 18.0))[0]
        weight = "regular"
        font = ImageFont.truetype(str(resolve_font_face(font_family, weight)), round(minimum_pt * 96 / 72))
        candidate = _render_text_mask(text, font)
        best = (
            0.0,
            minimum_pt,
            weight,
            _mask_iou(source, candidate),
            _dimension_similarity(source_width, candidate.width),
            _dimension_similarity(source_height, candidate.height),
        )
    score, size_pt, weight, mask_iou, width_similarity, height_similarity = best
    return RecoveredFont(
        font_family=font_family,
        font_size_px=round(size_pt * 96.0 / 72.0, 3),
        weight=weight,
        confidence=score,
        mask_iou=mask_iou,
        width_similarity=width_similarity,
        height_similarity=height_similarity,
    )


def recover_alignment(bbox: BBox, container: BBox) -> RecoveredAlignment:
    """Infer horizontal alignment from a line bbox inside its container."""

    width = max(1, container.width)
    distances = {
        "left": abs(bbox.x - container.x) / width,
        "center": abs((bbox.x + bbox.width / 2) - (container.x + container.width / 2)) / width,
        "right": abs((bbox.x + bbox.width) - (container.x + container.width)) / width,
    }
    ranked = sorted(distances.items(), key=lambda item: item[1])
    best_name, best_distance = ranked[0]
    second_distance = ranked[1][1]
    confidence = max(0.0, min(1.0, (second_distance - best_distance) / 0.15))
    return RecoveredAlignment(best_name, confidence)


def _semantic_spans(text: str) -> list[tuple[int, int]]:
    matches = list(re.finditer(r"\d+(?:[.,]\d+)*%?", text))
    if not matches:
        return [(0, len(text))]
    boundaries = {0, len(text)}
    for match in matches:
        boundaries.add(match.start())
        boundaries.add(match.end())
    ordered = sorted(boundaries)
    return [(start, end) for start, end in zip(ordered, ordered[1:]) if start < end]


def _occupied_x_ranges(mask: Image.Image) -> list[tuple[int, int]]:
    binary = mask.convert("L")
    width, height = binary.size
    pixels = binary.load()
    occupied = [any(pixels[x, y] for y in range(height)) for x in range(width)]
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    for x, present in enumerate(occupied + [False]):
        if present and start is None:
            start = x
        elif not present and start is not None:
            ranges.append((start, x))
            start = None
    return ranges


def _span_pixel_ranges(mask: Image.Image, count: int) -> list[tuple[int, int]]:
    bounds = mask.getbbox()
    if bounds is None or count <= 1:
        return [(0, mask.width)]
    ranges = _occupied_x_ranges(mask)
    gaps = sorted(
        ((ranges[index + 1][0] - ranges[index][1], ranges[index][1], ranges[index + 1][0]) for index in range(len(ranges) - 1)),
        reverse=True,
    )
    split_points = sorted((left + right) // 2 for gap, left, right in gaps[: count - 1] if gap >= 4)
    if len(split_points) != count - 1:
        left, _, right, _ = bounds
        split_points = [round(left + (right - left) * index / count) for index in range(1, count)]
    points = [0, *split_points, mask.width]
    return [(start, end) for start, end in zip(points, points[1:])]


def recover_mixed_runs(
    text: str,
    full_image: Image.Image,
    background_image: Image.Image,
    text_image: Image.Image,
    bbox: BBox,
    font_family: str = "Microsoft YaHei",
) -> tuple[TextRun, ...]:
    """Recover numeric emphasis and surrounding text as independently styled runs."""

    runs, _ = _recover_mixed_runs_with_evidence(
        text, full_image, background_image, text_image, bbox, font_family
    )
    return runs


def _recover_mixed_runs_with_evidence(
    text: str,
    full_image: Image.Image,
    background_image: Image.Image,
    text_image: Image.Image,
    bbox: BBox,
    font_family: str,
) -> tuple[tuple[TextRun, ...], tuple[Mapping[str, Any], ...]]:

    spans = _semantic_spans(text)
    line_mask = build_text_mask(text_image, bbox)
    pixel_ranges = _span_pixel_ranges(line_mask, len(spans))
    runs: list[TextRun] = []
    evidence: list[Mapping[str, Any]] = []
    for (start, end), (pixel_start, pixel_end) in zip(spans, pixel_ranges):
        run_text = text[start:end]
        run_bbox = BBox(
            bbox.x + pixel_start,
            bbox.y,
            max(1, pixel_end - pixel_start),
            bbox.height,
        )
        run_mask = build_text_mask(text_image, run_bbox)
        font = fit_font_style(run_text.strip() or run_text, run_mask, run_bbox, font_family)
        color = recover_line_color(full_image, background_image, text_image, run_bbox)
        runs.append(
            TextRun(
                text=run_text,
                style={
                    "font_family": font.font_family,
                    "font_size_px": font.font_size_px,
                    "weight": font.weight,
                    "bold": font.weight == "bold",
                    "color": color.hex_color,
                },
            )
        )
        evidence.append({"font": asdict(font), "color": asdict(color)})
    return tuple(runs), tuple(evidence)


def _bbox_from_mapping(value: Mapping[str, Any]) -> BBox | None:
    try:
        return BBox(
            int(value["x"]),
            int(value["y"]),
            int(value["width"]),
            int(value["height"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _contains(container: BBox, line: BBox) -> bool:
    return (
        line.x >= container.x
        and line.y >= container.y
        and line.x + line.width <= container.x + container.width
        and line.y + line.height <= container.y + container.height
    )


def _line_container(line: BBox, containers: Sequence[Mapping[str, Any]], page: BBox) -> BBox:
    candidates: list[BBox] = []
    for container in containers:
        raw = container.get("safe_bbox")
        bbox = _bbox_from_mapping(raw) if isinstance(raw, Mapping) else None
        if bbox is not None and _contains(bbox, line):
            candidates.append(bbox)
    return min(candidates, key=lambda value: value.width * value.height) if candidates else page


def recover_page_styles(
    full_path: str | Path,
    background_path: str | Path,
    text_path: str | Path,
    lines: Sequence[TextLine],
    containers: Sequence[Mapping[str, Any]],
    font_family: str = "Microsoft YaHei",
) -> StyleRecoveryResult:
    """Enrich normalized OCR lines using all three registered images."""

    with Image.open(full_path).convert("RGB") as full_image, Image.open(background_path).convert(
        "RGB"
    ) as background_image, Image.open(text_path).convert("RGB") as text_image:
        page = BBox(0, 0, background_image.width, background_image.height)
        enriched: list[TextLine] = []
        reviews: list[Mapping[str, Any]] = []
        for line in lines:
            runs, run_evidence = _recover_mixed_runs_with_evidence(
                line.text,
                full_image,
                background_image,
                text_image,
                line.bbox,
                font_family,
            )
            alignment = recover_alignment(line.bbox, _line_container(line.bbox, containers, page))
            evidence = {
                "runs": list(run_evidence),
                "alignment": {"method": "container_geometry", **asdict(alignment)},
            }
            enriched.append(
                replace(
                    line,
                    runs=runs,
                    layout={
                        "align": alignment.align,
                        "valign": "top",
                        "wrap": False,
                        "margin_px": 0,
                        "rotation_deg": 0,
                    },
                    style_evidence=evidence,
                )
            )
            confidences = [alignment.confidence]
            for item in run_evidence:
                confidences.append(float(item["font"]["confidence"]))
                confidences.append(float(item["color"]["confidence"]))
            if min(confidences) < 0.70:
                reviews.append(
                    {
                        "rule": "text_style_confidence",
                        "line_id": line.line_id,
                        "value": min(confidences),
                        "message": "Recovered text style confidence is below 0.70",
                    }
                )
    return StyleRecoveryResult(tuple(enriched), tuple(reviews))
