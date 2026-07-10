#!/usr/bin/env python3
"""
Icon style consistency checks for slide-image-rebuild icon contract verification.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"

DEFAULT_MAX_STROKE_WIDTH_PX = 2.5
DEFAULT_MIN_BBOX_FILL_RATIO = 0.12
DEFAULT_MAX_BBOX_FILL_RATIO = 0.85
DEFAULT_MIN_PADDING_RATIO = 0.08
DEFAULT_MAX_STROKE_WIDTH_SPREAD_PX = 0.75
DEFAULT_STROKE_TOLERANCE_PX = 0.6


@dataclass(frozen=True)
class StylePolicy:
    enabled: bool = True
    max_stroke_width_px: float = DEFAULT_MAX_STROKE_WIDTH_PX
    min_bbox_fill_ratio: float = DEFAULT_MIN_BBOX_FILL_RATIO
    max_bbox_fill_ratio: float = DEFAULT_MAX_BBOX_FILL_RATIO
    min_padding_ratio: float = DEFAULT_MIN_PADDING_RATIO
    max_stroke_width_spread_px: float = DEFAULT_MAX_STROKE_WIDTH_SPREAD_PX
    stroke_tolerance_px: float = DEFAULT_STROKE_TOLERANCE_PX
    require_render_metrics: bool = False

    @classmethod
    def from_manifest_policy(cls, policy: dict[str, Any] | None, *, style_check: bool) -> StylePolicy:
        raw = policy if isinstance(policy, dict) else {}
        if raw.get("style_check") is False:
            enabled = False
        else:
            enabled = bool(style_check) or raw.get("style_check", False) is True
        return cls(
            enabled=enabled,
            max_stroke_width_px=float(raw.get("max_stroke_width_px", DEFAULT_MAX_STROKE_WIDTH_PX)),
            min_bbox_fill_ratio=float(raw.get("min_bbox_fill_ratio", DEFAULT_MIN_BBOX_FILL_RATIO)),
            max_bbox_fill_ratio=float(raw.get("max_bbox_fill_ratio", DEFAULT_MAX_BBOX_FILL_RATIO)),
            min_padding_ratio=float(raw.get("min_padding_ratio", DEFAULT_MIN_PADDING_RATIO)),
            max_stroke_width_spread_px=float(
                raw.get("max_stroke_width_spread_px", DEFAULT_MAX_STROKE_WIDTH_SPREAD_PX)
            ),
            stroke_tolerance_px=float(raw.get("stroke_tolerance_px", DEFAULT_STROKE_TOLERANCE_PX)),
            require_render_metrics=raw.get("require_render_metrics", False) is True,
        )


@dataclass
class StyleFinding:
    level: str
    code: str
    message: str
    icon_id: str = ""
    page_id: str = ""
    path: str = ""
    metrics: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            payload["path"] = self.path
        if self.page_id:
            payload["page_id"] = self.page_id
        if self.icon_id:
            payload["icon_id"] = self.icon_id
        if self.metrics:
            payload["metrics"] = self.metrics
        return payload


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    cleaned = []
    for char in text:
        if char.isdigit() or char in ".-":
            cleaned.append(char)
        elif cleaned:
            break
    try:
        return float("".join(cleaned)) if cleaned else None
    except ValueError:
        return None


def _inherited_stroke_width(elem: ET.Element, inherited: float | None = None) -> float | None:
    local = _number(elem.get("stroke-width"))
    width = local if local is not None else inherited
    tag = _strip_ns(elem.tag)
    if tag in {"path", "line", "rect", "circle", "ellipse", "polyline", "polygon"}:
        stroke = (elem.get("stroke") or "").strip().lower()
        if stroke in {"", "none", "transparent"}:
            return width
        if width is not None:
            return width
    for child in list(elem):
        child_width = _inherited_stroke_width(child, width)
        if child_width is not None:
            return child_width
    return width


def collect_stroke_widths(icon_elem: ET.Element) -> list[float]:
    widths: list[float] = []
    root_width = _number(icon_elem.get("stroke-width"))

    def walk(elem: ET.Element, inherited: float | None) -> None:
        local = _number(elem.get("stroke-width"))
        current = local if local is not None else inherited
        tag = _strip_ns(elem.tag)
        if tag in {"path", "line", "rect", "circle", "ellipse", "polyline", "polygon"}:
            stroke = (elem.get("stroke") or "").strip().lower()
            fill = (elem.get("fill") or "").strip().lower()
            has_stroke = stroke not in {"", "none", "transparent"}
            has_fill = fill not in {"", "none", "transparent"}
            if has_stroke and current is not None:
                widths.append(current)
            elif has_fill and tag == "path" and current is not None:
                widths.append(current)
        for child in list(elem):
            walk(child, current)

    walk(icon_elem, root_width)
    deduped = sorted({round(value, 3) for value in widths})
    return deduped


def _is_ink_pixel(red: int, green: int, blue: int, alpha: int) -> bool:
    if alpha <= 20:
        return False
    if red > 245 and green > 245 and blue > 245:
        return False
    return max(red, green, blue) - min(red, green, blue) > 12 or (red + green + blue) / 3 < 238


def analyze_slot_metrics(image_path: Path, slot_bbox: tuple[float, float, float, float]) -> dict[str, Any] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        image = Image.open(image_path).convert("RGBA")
    except OSError:
        return None

    x, y, width, height = slot_bbox
    left = max(0, int(round(x)))
    top = max(0, int(round(y)))
    right = min(image.width, int(round(x + width)))
    bottom = min(image.height, int(round(y + height)))
    if right <= left or bottom <= top:
        return {
            "fill_ratio": 0.0,
            "padding_ratio": 0.0,
            "tight_bbox_px": [left, top, 0, 0],
        }

    crop = image.crop((left, top, right, bottom))
    slot_w = crop.width
    slot_h = crop.height
    total = slot_w * slot_h
    if total <= 0:
        return None

    ink = 0
    ink_left = slot_w
    ink_top = slot_h
    ink_right = -1
    ink_bottom = -1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        pixels = crop.load()
    for row in range(slot_h):
        for col in range(slot_w):
            red, green, blue, alpha = pixels[col, row]
            if not _is_ink_pixel(red, green, blue, alpha):
                continue
            ink += 1
            ink_left = min(ink_left, col)
            ink_top = min(ink_top, row)
            ink_right = max(ink_right, col)
            ink_bottom = max(ink_bottom, row)

    if ink <= 0 or ink_right < 0:
        return {
            "fill_ratio": 0.0,
            "padding_ratio": 0.0,
            "tight_bbox_px": [left, top, 0, 0],
        }

    tight_w = ink_right - ink_left + 1
    tight_h = ink_bottom - ink_top + 1
    pad_left = ink_left / slot_w
    pad_top = ink_top / slot_h
    pad_right = (slot_w - ink_right - 1) / slot_w
    pad_bottom = (slot_h - ink_bottom - 1) / slot_h
    min_padding = min(pad_left, pad_top, pad_right, pad_bottom)
    occupancy = (tight_w * tight_h) / total
    return {
        "fill_ratio": ink / total,
        "padding_ratio": min_padding,
        "occupancy_ratio": occupancy,
        "tight_bbox_px": [left + ink_left, top + ink_top, tight_w, tight_h],
        "surface_ink_ratio": _surface_ink_ratio(image, (left, top, right, bottom)),
    }


def _surface_ink_ratio(image: Any, bbox: tuple[int, int, int, int], *, gap: int = 3, thickness: int = 2) -> float:
    """Ink ratio of a thin ring just outside the slot bbox.

    A high ratio means the icon sits on a colored surface (navy chevron, tinted
    strip, ...) — fill/padding metrics measured against the page then count the
    surface itself as ink and are meaningless.
    """
    left, top, right, bottom = bbox
    outer_left = max(0, left - gap - thickness)
    outer_top = max(0, top - gap - thickness)
    outer_right = min(image.width, right + gap + thickness)
    outer_bottom = min(image.height, bottom + gap + thickness)
    inner_left = max(0, left - gap)
    inner_top = max(0, top - gap)
    inner_right = min(image.width, right + gap)
    inner_bottom = min(image.height, bottom + gap)
    if outer_right <= outer_left or outer_bottom <= outer_top:
        return 0.0
    ink = 0
    total = 0
    pixels = image.load()
    for row in range(outer_top, outer_bottom):
        for col in range(outer_left, outer_right):
            if inner_left <= col < inner_right and inner_top <= row < inner_bottom:
                continue
            red, green, blue, alpha = pixels[col, row]
            total += 1
            if _is_ink_pixel(red, green, blue, alpha):
                ink += 1
    return ink / total if total else 0.0


def _implementation_skips_stroke(icon_entry: dict[str, Any]) -> bool:
    implementation = str(icon_entry.get("implementation", "")).strip().lower()
    if implementation in {"icon_crop", "raster_crop", "slot_crop"}:
        return True
    priority = icon_entry.get("implementation_priority")
    return priority == 3 or icon_entry.get("fallback_allowed") is True and implementation == "crop"


def check_page_icon_styles(
    *,
    page_id: str,
    svg_path: Path,
    svg_icons: dict[str, tuple[ET.Element, tuple[float, float, float, float] | None]],
    manifest_icons: list[dict[str, Any]],
    preview_path: Path | None,
    policy: StylePolicy,
) -> tuple[list[StyleFinding], list[dict[str, Any]]]:
    if not policy.enabled:
        return [], []

    findings: list[StyleFinding] = []
    summaries: list[dict[str, Any]] = []
    page_stroke_widths: list[float] = []

    for item in manifest_icons:
        if not isinstance(item, dict):
            continue
        icon_id = str(item.get("id", "")).strip()
        if not icon_id or item.get("required", True) is False:
            continue
        actual = svg_icons.get(icon_id)
        summary: dict[str, Any] = {"id": icon_id, "style_checked": True}
        summaries.append(summary)
        if actual is None:
            continue

        icon_elem, _bbox = actual
        slot_values = item.get("bbox_px")
        if not isinstance(slot_values, list) or len(slot_values) < 4:
            continue
        slot_bbox = tuple(float(value) for value in slot_values[:4])

        if not _implementation_skips_stroke(item):
            stroke_widths = collect_stroke_widths(icon_elem)
            summary["stroke_widths_px"] = stroke_widths
            if stroke_widths:
                page_stroke_widths.extend(stroke_widths)
                max_width = max(stroke_widths)
                summary["max_stroke_width_px"] = max_width
                if max_width > policy.max_stroke_width_px:
                    findings.append(StyleFinding(
                        "error",
                        "icon_stroke_too_heavy",
                        f"Page {page_id} icon {icon_id} max stroke width {max_width:.2f}px exceeds "
                        f"{policy.max_stroke_width_px:.2f}px.",
                        icon_id=icon_id,
                        page_id=page_id,
                        path=str(svg_path),
                        metrics={"stroke_widths_px": stroke_widths, "max_stroke_width_px": max_width},
                    ))
                expected = item.get("stroke_width_px")
                if isinstance(expected, (int, float)):
                    if any(abs(width - float(expected)) > policy.stroke_tolerance_px for width in stroke_widths):
                        findings.append(StyleFinding(
                            "error",
                            "icon_stroke_mismatch",
                            f"Page {page_id} icon {icon_id} stroke width {stroke_widths} "
                            f"does not match manifest stroke_width_px {expected}.",
                            icon_id=icon_id,
                            page_id=page_id,
                            path=str(svg_path),
                            metrics={"stroke_widths_px": stroke_widths, "expected_stroke_width_px": float(expected)},
                        ))

        if preview_path is not None and preview_path.is_file():
            metrics = analyze_slot_metrics(preview_path, slot_bbox)
            if metrics is None:
                findings.append(StyleFinding(
                    "warning",
                    "icon_style_metrics_unavailable",
                    f"Page {page_id} icon {icon_id} style metrics could not be computed from preview.",
                    icon_id=icon_id,
                    page_id=page_id,
                    path=str(preview_path),
                ))
            elif float(metrics.get("surface_ink_ratio", 0.0)) >= 0.5:
                summary.update({
                    "fill_ratio": round(float(metrics["fill_ratio"]), 5),
                    "padding_ratio": round(float(metrics["padding_ratio"]), 5),
                    "surface_ink_ratio": round(float(metrics["surface_ink_ratio"]), 5),
                })
                findings.append(StyleFinding(
                    "warning",
                    "icon_style_colored_surface_skipped",
                    f"Page {page_id} icon {icon_id} sits on a colored surface "
                    f"(surface ink ratio {float(metrics['surface_ink_ratio']):.2f}); "
                    "fill/padding metrics skipped.",
                    icon_id=icon_id,
                    page_id=page_id,
                    path=str(preview_path),
                    metrics=metrics,
                ))
            else:
                summary.update({
                    "fill_ratio": round(float(metrics["fill_ratio"]), 5),
                    "padding_ratio": round(float(metrics["padding_ratio"]), 5),
                    "occupancy_ratio": round(float(metrics.get("occupancy_ratio", 0.0)), 5),
                })
                fill_ratio = float(metrics["fill_ratio"])
                if fill_ratio < policy.min_bbox_fill_ratio:
                    findings.append(StyleFinding(
                        "error",
                        "icon_bbox_fill_low",
                        f"Page {page_id} icon {icon_id} fill ratio {fill_ratio:.4f} is below "
                        f"{policy.min_bbox_fill_ratio:.4f}.",
                        icon_id=icon_id,
                        page_id=page_id,
                        path=str(preview_path),
                        metrics=metrics,
                    ))
                elif fill_ratio > policy.max_bbox_fill_ratio:
                    findings.append(StyleFinding(
                        "error",
                        "icon_bbox_fill_high",
                        f"Page {page_id} icon {icon_id} fill ratio {fill_ratio:.4f} exceeds "
                        f"{policy.max_bbox_fill_ratio:.4f}.",
                        icon_id=icon_id,
                        page_id=page_id,
                        path=str(preview_path),
                        metrics=metrics,
                    ))
                padding_ratio = float(metrics["padding_ratio"])
                if padding_ratio < policy.min_padding_ratio:
                    findings.append(StyleFinding(
                        "error",
                        "icon_padding_low",
                        f"Page {page_id} icon {icon_id} padding ratio {padding_ratio:.4f} is below "
                        f"{policy.min_padding_ratio:.4f}.",
                        icon_id=icon_id,
                        page_id=page_id,
                        path=str(preview_path),
                        metrics=metrics,
                    ))
        elif policy.require_render_metrics:
            findings.append(StyleFinding(
                "error",
                "icon_style_render_required",
                f"Page {page_id} icon {icon_id} requires preview render metrics but no preview image was found.",
                icon_id=icon_id,
                page_id=page_id,
                path=str(svg_path),
            ))

    if page_stroke_widths:
        spread = max(page_stroke_widths) - min(page_stroke_widths)
        if spread > policy.max_stroke_width_spread_px:
            findings.append(StyleFinding(
                "error",
                "icon_stroke_inconsistent",
                f"Page {page_id} icon stroke widths vary by {spread:.2f}px "
                f"(max spread {policy.max_stroke_width_spread_px:.2f}px).",
                page_id=page_id,
                path=str(svg_path),
                metrics={
                    "stroke_widths_px": sorted(set(round(value, 3) for value in page_stroke_widths)),
                    "stroke_spread_px": spread,
                },
            ))

    return findings, summaries
