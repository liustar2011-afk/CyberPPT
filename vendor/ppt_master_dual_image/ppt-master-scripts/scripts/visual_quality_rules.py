#!/usr/bin/env python3
"""Reusable visual quality helpers.

These helpers implement small automatic fixes aligned with
references/visual-review.md hard rule H4 (readability). They are intentionally
local and deterministic: callers provide rendered/background pixels and text
boxes, then receive adjusted text boxes plus audit records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, TypeVar

from PIL import Image, ImageStat


class PositionedTextLike(Protocol):
    text: str
    x: float
    y: float
    w: float
    h: float
    font_size: float
    font_family: str
    fill: str
    font_weight: str
    align: str
    word_wrap: bool


TextBoxT = TypeVar("TextBoxT", bound=PositionedTextLike)


@dataclass
class TextQualityRecord:
    text: str
    dark_background: bool
    font_color_auto: bool
    adjusted_position: bool
    text_fit_checked: bool
    text_fit_fixed: bool
    text_fit_unresolved: bool
    estimated_text_width: float
    container_overflow_checked: bool
    container_overflow_fixed: bool
    container_overflow_unresolved: bool
    container_bbox: list[float] | None
    bbox: list[float]
    fill: str
    font_size: float
    font_weight: str


@dataclass
class TextGroupQualityRecord:
    group_id: str
    texts: list[str]
    editable_text_box_count: int
    visual_line_count: int
    bbox: list[float]
    container_bbox: list[float] | None
    container_overflow_checked: bool
    container_overflow_unresolved: bool
    overflow_sides: list[str]


@dataclass
class QualityLayerStatus:
    name: str
    status: str
    checked: bool
    fixed_count: int = 0
    unresolved_count: int = 0
    details: list[str] | None = None


@dataclass
class VisualQualitySummary:
    deterministic_status: QualityLayerStatus
    content_lock_status: QualityLayerStatus
    text_group_status: QualityLayerStatus
    visual_similarity_status: QualityLayerStatus
    manual_review_status: QualityLayerStatus

    def to_dict(self) -> dict[str, dict]:
        return {
            "deterministic_status": asdict(self.deterministic_status),
            "content_lock_status": asdict(self.content_lock_status),
            "text_group_status": asdict(self.text_group_status),
            "visual_similarity_status": asdict(self.visual_similarity_status),
            "manual_review_status": asdict(self.manual_review_status),
        }


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """Return WCAG relative luminance approximation on 0-255 RGB values."""
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def clip_box(
    x: float,
    y: float,
    w: float,
    h: float,
    pixel_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    width, height = pixel_size
    left = max(0, min(width - 1, int(x)))
    top = max(0, min(height - 1, int(y)))
    right = max(left + 1, min(width, int(x + w + 0.999)))
    bottom = max(top + 1, min(height, int(y + h + 0.999)))
    return left, top, right, bottom


def box_mean_luminance(background: Image.Image, box: PositionedTextLike, pixel_size: tuple[int, int]) -> float:
    left, top, right, bottom = clip_box(box.x, box.y, box.w, box.h, pixel_size)
    crop = background.crop((left, top, right, bottom)).convert("RGB")
    stat = ImageStat.Stat(crop)
    mean = tuple(int(value) for value in stat.mean[:3])
    return relative_luminance(mean)


def local_dark_region_bbox(
    background: Image.Image,
    box: PositionedTextLike,
    pixel_size: tuple[int, int],
    *,
    padding: int = 18,
    threshold: int = 132,
) -> tuple[float, float, float, float] | None:
    """Find a nearby dark visual container, such as a blue title bar."""
    left, top, right, bottom = clip_box(
        box.x - padding,
        box.y - padding,
        box.w + padding * 2,
        box.h + padding * 2,
        pixel_size,
    )
    crop = background.crop((left, top, right, bottom)).convert("RGB")
    mask = crop.convert("L").point(lambda value: 255 if value < threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return None
    x1, y1, x2, y2 = bbox
    dark_pixels = mask.crop(bbox).point(lambda value: 1 if value else 0)
    dark_area = dark_pixels.histogram()[1]
    bbox_area = max(1, (x2 - x1) * (y2 - y1))
    if dark_area < max(80, box.w * box.h * 0.35) or dark_area / bbox_area < 0.55:
        return None
    return float(left + x1), float(top + y1), float(x2 - x1), float(y2 - y1)


def _estimate_text_width_px(text: str, font_size: float, font_weight: str) -> float:
    weight_factor = 1.08 if font_weight in {"bold", "700", "800", "900"} else 1.0
    line_widths = []
    for line in text.splitlines() or [text]:
        width = 0.0
        for ch in line:
            if "\u4e00" <= ch <= "\u9fff":
                width += font_size
            elif ch.isspace():
                width += font_size * 0.35
            else:
                width += font_size * 0.56
        line_widths.append(width)
    return max(max(line_widths, default=0.0) * weight_factor, font_size)


def local_visual_container_bbox(
    background: Image.Image,
    box: PositionedTextLike,
    pixel_size: tuple[int, int],
    *,
    padding: int = 28,
) -> tuple[float, float, float, float] | None:
    """Find a nearby non-white text-bearing container in a no-text background."""
    left, top, right, bottom = clip_box(
        box.x - padding,
        box.y - padding,
        box.w + padding * 2,
        box.h + padding * 2,
        pixel_size,
    )
    crop = background.crop((left, top, right, bottom)).convert("RGB")
    # In clean-background slide images, text-bearing cards are usually subtle
    # blue/gray panels. Treat pixels meaningfully different from near-white as
    # local container structure; require enough ink to avoid single borders.
    mask = crop.convert("L").point(lambda value: 255 if value < 248 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return None
    x1, y1, x2, y2 = bbox
    component_pixels = mask.crop(bbox).point(lambda value: 1 if value else 0)
    component_area = component_pixels.histogram()[1]
    bbox_area = max(1, (x2 - x1) * (y2 - y1))
    if component_area < max(160, box.w * box.h * 0.18) or component_area / bbox_area < 0.18:
        return None

    abs_box = (float(left + x1), float(top + y1), float(x2 - x1), float(y2 - y1))
    cx = box.x + box.w / 2
    cy = box.y + box.h / 2
    bx, by, bw, bh = abs_box
    if not (bx - 8 <= cx <= bx + bw + 8 and by - 8 <= cy <= by + bh + 8):
        return None
    if bw < box.h * 2 or bh < box.h * 0.8:
        return None
    return abs_box


def _fit_text_to_width(
    text: str,
    font_size: float,
    font_weight: str,
    width_px: float,
    *,
    min_size: float = 8.0,
) -> tuple[float, bool]:
    fitted = font_size
    while fitted > min_size and _estimate_text_width_px(text, fitted, font_weight) > width_px * 0.96:
        fitted -= 0.5
    return max(min_size, fitted), fitted <= min_size


def fit_text_box_width(
    box: TextBoxT,
    pixel_size: tuple[int, int],
    container: tuple[float, float, float, float] | None,
    *,
    min_size: float = 8.0,
) -> tuple[TextBoxT, bool, bool, float]:
    """Keep a rendered one-line text box wide enough to avoid vertical wrapping."""
    estimated = _estimate_text_width_px(box.text, box.font_size, box.font_weight)
    if estimated <= box.w * 0.96:
        return box, False, False, estimated

    max_right = pixel_size[0] - 2.0
    if container is not None:
        cx, _, cw, _ = container
        max_right = min(max_right, cx + cw - 8.0)
    max_w = max(1.0, max_right - box.x)
    new_w = min(max_w, max(box.w, estimated * 1.04))
    fitted_size, hit_min = _fit_text_to_width(
        box.text,
        box.font_size,
        box.font_weight,
        new_w,
        min_size=min_size,
    )
    unresolved = hit_min and _estimate_text_width_px(box.text, fitted_size, box.font_weight) > new_w * 0.96
    adjusted = type(box)(
        text=box.text,
        x=box.x,
        y=box.y,
        w=new_w,
        h=box.h,
        font_size=fitted_size,
        font_family=box.font_family,
        fill=box.fill,
        font_weight=box.font_weight,
        align=box.align,
        word_wrap=False,
    )
    return adjusted, True, unresolved, estimated


def constrain_text_to_container(
    box: TextBoxT,
    container: tuple[float, float, float, float] | None,
    *,
    padding: float = 8.0,
) -> tuple[TextBoxT, bool, bool]:
    """Constrain one text box to its detected visual container."""
    if container is None:
        return box, False, False
    cx, cy, cw, ch = container
    inner_x = cx + padding
    inner_y = cy + max(2.0, padding * 0.55)
    inner_w = max(1.0, cw - padding * 2)
    inner_h = max(1.0, ch - max(4.0, padding * 1.1))
    overflow = (
        box.x < inner_x
        or box.y < inner_y
        or box.x + box.w > inner_x + inner_w
        or box.y + box.h > inner_y + inner_h
    )
    if not overflow:
        return box, False, False

    new_w = min(box.w, inner_w)
    new_h = min(max(box.h, min(inner_h, box.font_size * 1.35)), inner_h)
    new_x = min(max(box.x, inner_x), inner_x + inner_w - new_w)
    new_y = min(max(box.y, inner_y), inner_y + inner_h - new_h)
    fitted_size, hit_min = _fit_text_to_width(
        box.text,
        box.font_size,
        box.font_weight,
        new_w,
    )
    unresolved = hit_min and _estimate_text_width_px(box.text, fitted_size, box.font_weight) > new_w
    adjusted = type(box)(
        text=box.text,
        x=new_x,
        y=new_y,
        w=new_w,
        h=new_h,
        font_size=fitted_size,
        font_family=box.font_family,
        fill=box.fill,
        font_weight=box.font_weight,
        align=box.align,
        word_wrap=box.word_wrap or unresolved,
    )
    return adjusted, True, unresolved


def _group_bbox(boxes: list[PositionedTextLike]) -> tuple[float, float, float, float]:
    x1 = min(box.x for box in boxes)
    y1 = min(box.y for box in boxes)
    x2 = max(box.x + box.w for box in boxes)
    y2 = max(box.y + box.h for box in boxes)
    return x1, y1, x2 - x1, y2 - y1


def _visual_line_count(boxes: list[PositionedTextLike], *, tolerance: float) -> int:
    lines: list[float] = []
    for box in sorted(boxes, key=lambda item: item.y + item.h / 2):
        center_y = box.y + box.h / 2
        if not any(abs(center_y - line_y) <= max(tolerance, box.h * 0.38) for line_y in lines):
            lines.append(center_y)
    return len(lines)


def _overflow_sides(
    bbox: tuple[float, float, float, float],
    container: tuple[float, float, float, float],
    *,
    tolerance: float,
) -> list[str]:
    x, y, w, h = bbox
    cx, cy, cw, ch = container
    sides: list[str] = []
    if x < cx - tolerance:
        sides.append("left")
    if y < cy - tolerance:
        sides.append("top")
    if x + w > cx + cw + tolerance:
        sides.append("right")
    if y + h > cy + ch + tolerance:
        sides.append("bottom")
    return sides


def _boxes_overlap(
    a: list[float],
    b: list[float],
    *,
    tolerance: float = 0.0,
) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (
        ax + aw <= bx + tolerance
        or bx + bw <= ax + tolerance
        or ay + ah <= by + tolerance
        or by + bh <= ay + tolerance
    )


def find_text_overlaps(
    records: list[TextQualityRecord],
    *,
    tolerance: float = 1.0,
) -> list[tuple[str, str]]:
    """Report overlapping editable text boxes for deterministic QA."""
    overlaps: list[tuple[str, str]] = []
    for left_index, left in enumerate(records):
        for right in records[left_index + 1 :]:
            if _boxes_overlap(left.bbox, right.bbox, tolerance=tolerance):
                overlaps.append((left.text, right.text))
    return overlaps


def _normalize_text(value: str) -> str:
    return "".join(value.split()).lower()


def check_content_lock(
    required_texts: list[str],
    observed_texts: list[str],
) -> tuple[list[str], list[str]]:
    """Compare required locked strings with observed editable text strings."""
    observed_joined = _normalize_text("".join(observed_texts))
    required_normalized = {_normalize_text(item): item for item in required_texts if item.strip()}
    missing = [
        original
        for normalized, original in required_normalized.items()
        if normalized and normalized not in observed_joined
    ]

    allowed_joined = _normalize_text("".join(required_texts))
    additions = [
        observed
        for observed in observed_texts
        if _normalize_text(observed) and _normalize_text(observed) not in allowed_joined
    ]
    return missing, additions


def _layer_status(
    name: str,
    *,
    checked: bool,
    fixed_count: int = 0,
    unresolved_count: int = 0,
    details: list[str] | None = None,
) -> QualityLayerStatus:
    if not checked:
        status = "not_evaluated"
    elif unresolved_count:
        status = "needs_human"
    elif fixed_count:
        status = "fixed"
    else:
        status = "passed"
    return QualityLayerStatus(
        name=name,
        status=status,
        checked=checked,
        fixed_count=fixed_count,
        unresolved_count=unresolved_count,
        details=details or [],
    )


def summarize_visual_quality(
    records: list[TextQualityRecord],
    groups: list[TextGroupQualityRecord],
    *,
    required_texts: list[str] | None = None,
    observed_texts: list[str] | None = None,
    visual_similarity_checked: bool = False,
    visual_similarity_unresolved: bool = False,
    visual_similarity_details: list[str] | None = None,
) -> VisualQualitySummary:
    """Build the five-layer QA summary used by image-to-editable-PPT flows.

    This does not claim visual equivalence. `visual_similarity_status` remains
    `not_evaluated` until a rendered PPT image is compared with the source.
    """
    overlaps = find_text_overlaps(records)
    deterministic_fixed = sum(
        int(record.text_fit_fixed)
        + int(record.container_overflow_fixed)
        + int(record.font_color_auto)
        + int(record.adjusted_position)
        for record in records
    )
    deterministic_unresolved = sum(
        int(record.text_fit_unresolved or record.container_overflow_unresolved)
        for record in records
    ) + len(overlaps)
    deterministic_details = [
        f"text_overlap: {left} / {right}" for left, right in overlaps
    ]
    deterministic = _layer_status(
        "deterministic",
        checked=bool(records),
        fixed_count=deterministic_fixed,
        unresolved_count=deterministic_unresolved,
        details=deterministic_details,
    )

    required = required_texts or []
    observed = observed_texts or [record.text for record in records]
    missing, additions = check_content_lock(required, observed) if required else ([], [])
    content_lock = _layer_status(
        "content_lock",
        checked=bool(required),
        unresolved_count=len(missing) + len(additions),
        details=[f"missing: {item}" for item in missing]
        + [f"unexpected: {item}" for item in additions],
    )

    unresolved_groups = [group for group in groups if group.container_overflow_unresolved]
    text_group = _layer_status(
        "text_group",
        checked=bool(groups),
        unresolved_count=len(unresolved_groups),
        details=[
            f"{group.group_id} overflow {','.join(group.overflow_sides)}: {' / '.join(group.texts)}"
            for group in unresolved_groups
        ],
    )

    similarity = _layer_status(
        "visual_similarity",
        checked=visual_similarity_checked,
        unresolved_count=int(visual_similarity_unresolved),
        details=visual_similarity_details or [],
    )

    manual_unresolved = (
        deterministic.unresolved_count
        + content_lock.unresolved_count
        + text_group.unresolved_count
        + similarity.unresolved_count
    )
    manual_details: list[str] = []
    for layer in (deterministic, content_lock, text_group, similarity):
        if layer.unresolved_count:
            manual_details.append(f"{layer.name}: {layer.unresolved_count}")
    manual = _layer_status(
        "manual_review",
        checked=True,
        unresolved_count=manual_unresolved,
        details=manual_details,
    )

    return VisualQualitySummary(
        deterministic_status=deterministic,
        content_lock_status=content_lock,
        text_group_status=text_group,
        visual_similarity_status=similarity,
        manual_review_status=manual,
    )


def build_text_quality_groups(
    text_boxes: list[TextBoxT],
    records: list[TextQualityRecord],
    *,
    tolerance: float = 3.0,
) -> list[TextGroupQualityRecord]:
    """Build QA-only text groups without merging editable text boxes.

    The exported PPT should keep each editable text object separate. This helper
    groups related objects only for inspection: for example a three-box label
    may be checked as one visual phrase against its underlying container while
    still remaining three independently editable PowerPoint text boxes.
    """
    buckets: dict[tuple[int, int, int, int] | tuple[str, int], list[int]] = {}
    for index, (box, record) in enumerate(zip(text_boxes, records)):
        if record.container_bbox is not None:
            key = tuple(round(value) for value in record.container_bbox)
        else:
            key = ("line", round((box.y + box.h / 2) / max(1.0, box.h)))
        buckets.setdefault(key, []).append(index)

    groups: list[TextGroupQualityRecord] = []
    for group_number, indexes in enumerate(buckets.values(), start=1):
        boxes = [text_boxes[index] for index in indexes]
        x, y, w, h = _group_bbox(boxes)
        container = records[indexes[0]].container_bbox
        checked = container is not None
        sides: list[str] = []
        if container is not None:
            sides = _overflow_sides(
                (x, y, w, h),
                tuple(container),
                tolerance=tolerance,
            )
        groups.append(
            TextGroupQualityRecord(
                group_id=f"text_group_{group_number:03d}",
                texts=[box.text for box in boxes],
                editable_text_box_count=len(boxes),
                visual_line_count=_visual_line_count(boxes, tolerance=tolerance),
                bbox=[x, y, w, h],
                container_bbox=container,
                container_overflow_checked=checked,
                container_overflow_unresolved=bool(sides),
                overflow_sides=sides,
            )
        )
    return groups


def apply_visual_quality_rules(
    text_boxes: list[TextBoxT],
    background_image: Path,
    pixel_size: tuple[int, int],
) -> tuple[list[TextBoxT], list[TextQualityRecord]]:
    """Apply reusable visual QA rules based on background pixels.

    Rules:
    - H4 readability: text over dark regions turns white and bold.
    - S4-style alignment support: text near a detected dark title bar is centered
      within that local dark region.
    - Text fitting: one-line text boxes are widened or shrunk before export so
      PowerPoint cannot turn horizontal Chinese text into vertical wrapping.
    """
    with Image.open(background_image) as image:
        background = image.convert("RGB")

    adjusted_boxes: list[TextBoxT] = []
    records: list[TextQualityRecord] = []
    for box in text_boxes:
        dark_region = local_dark_region_bbox(background, box, pixel_size)
        container = local_visual_container_bbox(background, box, pixel_size)
        sample_luma = box_mean_luminance(background, box, pixel_size)
        dark_background = sample_luma < 142 or dark_region is not None
        adjusted_position = False
        container_overflow_fixed = False
        container_overflow_unresolved = False

        x, y, w, h = box.x, box.y, box.w, box.h
        align = box.align
        font_weight = box.font_weight
        fill = box.fill
        if dark_region is not None:
            rx, ry, rw, rh = dark_region
            if rh <= max(64, box.h * 3.0):
                x = rx + max(4.0, rw * 0.04)
                y = ry + max(1.0, (rh - box.h) / 2)
                w = max(1, rw - max(8.0, rw * 0.08))
                align = "center"
                adjusted_position = True
        if dark_background:
            fill = "#FFFFFF"
            font_weight = "700"

        adjusted = type(box)(
            text=box.text,
            x=x,
            y=y,
            w=w,
            h=h,
            font_size=box.font_size,
            font_family=box.font_family,
            fill=fill,
            font_weight=font_weight,
            align=align,
            word_wrap=box.word_wrap,
        )
        adjusted, container_overflow_fixed, container_overflow_unresolved = constrain_text_to_container(
            adjusted,
            container,
        )
        adjusted, text_fit_fixed, text_fit_unresolved, estimated_width = fit_text_box_width(
            adjusted,
            pixel_size,
            container,
        )
        adjusted_boxes.append(adjusted)
        records.append(
            TextQualityRecord(
                text=adjusted.text,
                dark_background=dark_background,
                font_color_auto=dark_background and box.fill != "#FFFFFF",
                adjusted_position=adjusted_position,
                text_fit_checked=True,
                text_fit_fixed=text_fit_fixed,
                text_fit_unresolved=text_fit_unresolved,
                estimated_text_width=estimated_width,
                container_overflow_checked=container is not None,
                container_overflow_fixed=container_overflow_fixed,
                container_overflow_unresolved=container_overflow_unresolved or text_fit_unresolved,
                container_bbox=list(container) if container is not None else None,
                bbox=[adjusted.x, adjusted.y, adjusted.w, adjusted.h],
                fill=adjusted.fill,
                font_size=adjusted.font_size,
                font_weight=adjusted.font_weight,
            )
        )
    return adjusted_boxes, records
