#!/usr/bin/env python3
"""
PPT Master - Layout Reference Components

Small deterministic helpers for rebuilding reference layouts. These helpers do
not generate full slides; they provide reusable geometry and text-fitting
calculations that Executor scripts may call from per-page hand-authored SVG
generators.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable, Sequence

try:
    from arrow_geometry import (
        ArrowOptions,
        block_arrow_polygon,
        get_arrow,
        get_box_to_box_arrow,
        svg_path_arrow,
    )
except ImportError:  # pragma: no cover
    from scripts.arrow_geometry import (  # type: ignore
        ArrowOptions,
        block_arrow_polygon,
        get_arrow,
        get_box_to_box_arrow,
        svg_path_arrow,
    )


def cjk_text_width(text: str, font_size: float) -> float:
    """Approximate rendered text width for mixed CJK/Latin strings."""
    width = 0.0
    for char in text:
        code = ord(char)
        if char.isspace():
            width += font_size * 0.32
        elif 0x3400 <= code <= 0x9FFF or 0x3000 <= code <= 0x303F or 0xFF00 <= code <= 0xFFEF:
            width += font_size
        elif char.isupper() or char.isdigit():
            width += font_size * 0.62
        else:
            width += font_size * 0.54
    return width


DEFAULT_PROTECTED_TERMS: tuple[str, ...] = (
    "设备可靠性",
    "质量改进",
    "结果出证",
    "目录授权",
    "规则计算",
    "产品交付",
    "反馈回流",
)


@dataclass(frozen=True)
class FitTextBoxResult:
    lines: tuple[str, ...]
    font_size: float
    line_height: float
    truncated: bool
    warnings: tuple[str, ...]


def _box_width_height(
    box: dict[str, float] | tuple[float, float, float, float],
) -> tuple[float, float]:
    if isinstance(box, dict):
        return float(box["w"]), float(box["h"])
    return float(box[2]), float(box[3])


def _line_block_height(line_count: int, font_size: float, line_height: float) -> float:
    if line_count <= 0:
        return 0.0
    if line_count == 1:
        return font_size * 1.3
    return line_height * (line_count - 1) + font_size * 1.3


def _truncate_line(
    text: str,
    max_width: float,
    font_size: float,
    *,
    ellipsis: str = "…",
) -> str:
    if cjk_text_width(text, font_size) <= max_width:
        return text
    trimmed = text
    while trimmed and cjk_text_width(trimmed + ellipsis, font_size) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + ellipsis) if trimmed else ellipsis


def _tokenize_protected(text: str, protected_terms: Sequence[str]) -> list[str]:
    """Split text into atomic tokens: each protected term is one unbreakable token,
    every other character is its own token. Longest term wins on overlap."""
    terms = sorted((t for t in protected_terms if t), key=len, reverse=True)
    tokens: list[str] = []
    i, n = 0, len(text)
    while i < n:
        match = next((t for t in terms if text.startswith(t, i)), None)
        if match:
            tokens.append(match)
            i += len(match)
        else:
            tokens.append(text[i])
            i += 1
    return tokens


def _wrap_cjk_atomic(
    text: str,
    max_width: float,
    font_size: float,
    protected_terms: Sequence[str],
    *,
    max_lines: int | None = None,
) -> list[str]:
    """Greedy wrap that mirrors :func:`wrap_cjk` but never breaks inside a protected
    term (the term is treated as one atomic token). A single token wider than
    ``max_width`` still occupies its own line — that overflow is unavoidable and the
    caller's fit search handles it by shrinking the font."""
    lines: list[str] = []
    current = ""
    for tok in _tokenize_protected(text, protected_terms):
        candidate = current + tok
        if current and cjk_text_width(candidate, font_size) > max_width:
            lines.append(current.rstrip("，、；： "))
            current = tok.lstrip()
            if max_lines and len(lines) >= max_lines - 1:
                break
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines


def _term_split_len(line_a: str, line_b: str, terms: Sequence[str]) -> int:
    """If a protected term straddles the ``line_a``/``line_b`` boundary, return how
    many of its leading chars sit at the end of ``line_a`` (1..len-1). 0 if none."""
    for term in terms:
        if not term or term in line_a or term in line_b:
            continue
        for k in range(1, len(term)):
            if line_a.endswith(term[:k]) and line_b.startswith(term[k:]):
                return k
    return 0


def _merge_split_protected_terms(
    lines: list[str],
    protected_terms: Sequence[str],
    *,
    max_width: float | None = None,
    font_size: float | None = None,
) -> list[str]:
    """Repair protected terms that a greedy wrap split across a line boundary.

    The fix pushes the split term *down* to the next line (moving the term's prefix
    from the end of the previous line to the start of the next), rather than merging
    the two whole lines together. Merging produced lines far wider than the box,
    which broke font-size monotonicity in the fit search (a larger size could be
    rejected while a smaller one fit). When ``max_width``/``font_size`` are supplied,
    a line that overflows after gaining the prefix is locally re-wrapped — keeping
    the term atomic — so no line exceeds ``max_width`` (save a lone oversized term).
    """
    if len(lines) < 2 or not protected_terms:
        return lines
    terms = [t for t in protected_terms if t]
    out = list(lines)
    i = 0
    guard = 0
    limit = len(out) * len(terms) * 8 + 16
    while i < len(out) - 1 and guard < limit:
        guard += 1
        k = _term_split_len(out[i], out[i + 1], terms)
        if k == 0:
            i += 1
            continue
        moved = out[i][-k:]
        head = out[i][:-k].rstrip("，、；： ")
        out[i + 1] = moved + out[i + 1]
        if head:
            out[i] = head
        else:
            del out[i]
            continue  # indices shifted; re-check this position
        if max_width and font_size and cjk_text_width(out[i + 1], font_size) > max_width:
            out[i + 1 : i + 2] = _wrap_cjk_atomic(out[i + 1], max_width, font_size, terms)
        # do not advance: re-check (i, i+1) for a second straddling term
    return out


def _wrap_with_protected_terms(
    text: str,
    max_width: float,
    font_size: float,
    *,
    max_lines: int | None,
    protected_terms: Sequence[str],
) -> list[str]:
    lines = wrap_cjk(text, max_width, font_size, max_lines=max_lines)
    if not protected_terms:
        return lines
    merged = _merge_split_protected_terms(
        lines, protected_terms, max_width=max_width, font_size=font_size,
    )
    if max_lines and len(merged) > max_lines:
        return merged[:max_lines]
    return merged


def fit_text_box(
    text: str,
    box: dict[str, float] | tuple[float, float, float, float],
    *,
    min_size: float = 7.5,
    max_size: float = 12.0,
    max_lines: int = 3,
    line_height_ratio: float = 1.12,
    prefer_keep_terms: bool = True,
    fit_strategy: str = "shrink_then_wrap_then_truncate",
    protected_terms: Sequence[str] | None = None,
) -> FitTextBoxResult:
    """Fit CJK-heavy text into a box by shrinking, wrapping, then truncating."""
    cleaned = (text or "").strip()
    if not cleaned:
        return FitTextBoxResult((), max_size, max_size * line_height_ratio, False, ())

    box_w, box_h = _box_width_height(box)
    if box_w <= 0 or box_h <= 0:
        return FitTextBoxResult(
            (cleaned,),
            max_size,
            max_size * line_height_ratio,
            False,
            ("box width/height must be positive; returning single line.",),
        )

    terms = tuple(protected_terms or (DEFAULT_PROTECTED_TERMS if prefer_keep_terms else ()))
    warnings: list[str] = []
    strategies = {
        "shrink_then_wrap_then_truncate": ("shrink", "truncate"),
        "wrap_then_shrink": ("shrink", "truncate"),
        "wrap_only": ("truncate",),
    }
    steps = strategies.get(fit_strategy, ("shrink", "truncate"))

    best_lines = (cleaned,)
    best_size = min_size
    best_line_height = min_size * line_height_ratio

    size = max_size
    while size + 1e-6 >= min_size:
        line_height = size * line_height_ratio
        wrap_fn = (
            (lambda t, w, fs: _wrap_with_protected_terms(
                t, w, fs, max_lines=max_lines, protected_terms=terms,
            ))
            if prefer_keep_terms
            else (lambda t, w, fs: wrap_cjk(t, w, fs, max_lines=max_lines))
        )
        lines = wrap_fn(cleaned, box_w, size)
        block_h = _line_block_height(len(lines), size, line_height)
        widest = max((cjk_text_width(line, size) for line in lines), default=0.0)
        if block_h <= box_h and widest <= box_w:
            return FitTextBoxResult(tuple(lines), size, line_height, False, tuple(warnings))

        best_lines = tuple(lines)
        best_size = size
        best_line_height = line_height
        size -= 0.5

    if "truncate" in steps:
        line_height = best_size * line_height_ratio
        lines = list(best_lines)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            warnings.append("line count truncated to max_lines.")
        if lines:
            lines[-1] = _truncate_line(lines[-1], box_w, best_size)
        while lines and _line_block_height(len(lines), best_size, line_height) > box_h:
            if len(lines) == 1:
                lines[0] = _truncate_line(lines[0], box_w, best_size)
                break
            lines.pop()
            warnings.append("dropped trailing line to satisfy box height.")
        if lines:
            widest = max(cjk_text_width(line, best_size) for line in lines)
            if widest > box_w:
                warnings.append("text width still exceeds box after truncation.")
        return FitTextBoxResult(tuple(lines), best_size, best_line_height, True, tuple(warnings))

    warnings.append("text does not fully fit box at min_font_size_pt.")
    return FitTextBoxResult(best_lines, best_size, best_line_height, False, tuple(warnings))


def wrap_cjk(text: str, max_width: float, font_size: float, *, max_lines: int | None = None) -> list[str]:
    """Greedy line-wrap for Chinese-heavy PowerPoint labels."""
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and cjk_text_width(candidate, font_size) > max_width:
            lines.append(current.rstrip("，、；： "))
            current = char.lstrip()
            if max_lines and len(lines) >= max_lines - 1:
                break
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines


def svg_paragraph_text(
    x: float,
    y: float,
    lines: Iterable[str],
    *,
    font_family: str,
    font_size: float,
    line_height: float,
    font_weight: int | str = 400,
    fill: str = "#111827",
    anchor: str = "start",
    fit_width: float | None = None,
    fit_height: float | None = None,
    fit_center_y: float | None = None,
    fit_label: str | None = None,
    element_id: str | None = None,
) -> str:
    """Return one SVG <text> containing multiple visual lines.

    Use this for one semantic paragraph that should become one editable PPT
    text frame. Export with ``svg_to_pptx.py --merge-paragraphs`` so the
    tspan lines survive as one textbox with controlled line spacing.
    """
    line_list = [str(line) for line in lines if str(line)]
    if not line_list:
        return ""
    attrs = [
        f'x="{x}"',
        f'y="{y}"',
        f"font-family='{font_family}'",
        f'font-size="{font_size}"',
        f'font-weight="{font_weight}"',
        f'fill="{fill}"',
        f'text-anchor="{anchor}"',
        f'data-paragraph-line-height="{line_height}"',
    ]
    if fit_width is not None:
        attrs.append(f'data-fit-width="{fit_width}"')
    if fit_height is not None:
        attrs.append(f'data-fit-height="{fit_height}"')
    if fit_center_y is not None:
        attrs.append(f'data-fit-center-y="{fit_center_y}"')
    if fit_label:
        attrs.append(f'data-fit-label="{escape(fit_label)}"')
    if element_id:
        attrs.append(f'id="{escape(element_id)}"')
    tspans = []
    for index, line in enumerate(line_list):
        dy = 0 if index == 0 else line_height
        tspans.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    return f"<text {' '.join(attrs)}>{''.join(tspans)}</text>"


def svg_centered_paragraph_text(
    x: float,
    container_y: float,
    container_h: float,
    lines: Iterable[str],
    *,
    font_family: str,
    font_size: float,
    line_height: float,
    font_weight: int | str = 400,
    fill: str = "#111827",
    anchor: str = "start",
    fit_width: float | None = None,
    fit_label: str | None = None,
    element_id: str | None = None,
) -> str:
    """Return paragraph text vertically centered inside a fixed-height box."""
    line_list = [str(line) for line in lines if str(line)]
    if not line_list:
        return ""
    text_h = line_height * (len(line_list) - 1) + font_size * 1.3
    center_y = container_y + container_h / 2
    baseline_y = center_y - text_h / 2 + font_size
    return svg_paragraph_text(
        x,
        baseline_y,
        line_list,
        font_family=font_family,
        font_size=font_size,
        line_height=line_height,
        font_weight=font_weight,
        fill=fill,
        anchor=anchor,
        fit_width=fit_width,
        fit_height=container_h,
        fit_center_y=center_y,
        fit_label=fit_label,
        element_id=element_id,
    )


def icon_center_from_text(text_left: float, text_top: float, text_height: float, *, circle_r: float, text_gap: float) -> tuple[float, float]:
    """Return icon center from the paired text block.

    ``text_gap`` is the clearance from the icon circle's right edge to text left.
    """
    return text_left - text_gap - circle_r, text_top + text_height / 2


@dataclass(frozen=True)
class ChevronSegment:
    x: float
    y: float
    w: float
    h: float
    label: str
    icon: str
    font_size: float
    is_first: bool = False
    is_last: bool = False


def distribute_chevrons(
    labels: Iterable[str],
    icons: Iterable[str],
    *,
    x: float,
    y: float,
    total_w: float,
    h: float,
    min_font_size: float = 16,
    max_font_size: float = 20,
    last_weight: float = 1.12,
) -> list[ChevronSegment]:
    """Distribute a horizontal chevron chain with text-fit aware widths."""
    label_list = list(labels)
    icon_list = list(icons)
    if len(label_list) != len(icon_list):
        raise ValueError("labels and icons must have the same length")
    if not label_list:
        return []

    weights = []
    for index, label in enumerate(label_list):
        weight = max(1.0, cjk_text_width(label, max_font_size) / 150)
        if index == len(label_list) - 1:
            weight *= last_weight
        weights.append(weight)

    unit = total_w / sum(weights)
    segments: list[ChevronSegment] = []
    cursor = x
    for index, (label, icon, weight) in enumerate(zip(label_list, icon_list, weights)):
        w = unit * weight
        usable = max(40, w - 102)
        font_size = max(min_font_size, min(max_font_size, usable / max(len(label), 1)))
        segments.append(ChevronSegment(
            x=round(cursor, 2),
            y=y,
            w=round(w, 2),
            h=h,
            label=label,
            icon=icon,
            font_size=round(font_size, 1),
            is_first=index == 0,
            is_last=index == len(label_list) - 1,
        ))
        cursor += w
    return segments


def zone_px(layout: dict, zone_id: str) -> dict[str, int]:
    """Convert a layout_reference zone id to pixel box on the project canvas."""
    canvas = layout.get("canvas", {})
    width = int(canvas.get("width_px") or 1280)
    height = int(canvas.get("height_px") or 720)
    for zone in layout.get("zones", []):
        if zone.get("id") != zone_id:
            continue
        keys = ("x_ratio", "y_ratio", "w_ratio", "h_ratio")
        if not all(isinstance(zone.get(key), (int, float)) for key in keys):
            raise ValueError(f"zone {zone_id} missing ratio fields")
        return {
            "x": round(float(zone["x_ratio"]) * width),
            "y": round(float(zone["y_ratio"]) * height),
            "w": round(float(zone["w_ratio"]) * width),
            "h": round(float(zone["h_ratio"]) * height),
        }
    raise KeyError(zone_id)


def zones_px_map(layout: dict) -> dict[str, dict[str, int]]:
    """Return pixel boxes for every zone id in layout_reference.json."""
    return {str(zone["id"]): zone_px(layout, str(zone["id"])) for zone in layout.get("zones", []) if zone.get("id")}


def _chevron_header_path(x: float, y: float, w: float, h: float, *, is_first: bool, is_last: bool) -> str:
    notch = min(18.0, w * 0.12)
    if is_first and is_last:
        return f"M{x},{y} h{w} v{h} h{-w} z"
    if is_first:
        return f"M{x},{y} h{w - notch} l{notch},{h / 2} l{-notch},{h / 2} h{-(w - notch)} z"
    if is_last:
        return f"M{x + notch},{y} h{w - notch} v{h} h{-(w - notch)} l{-notch},{-h / 2} z"
    return (
        f"M{x + notch},{y} h{w - 2 * notch} l{notch},{h / 2} l{-notch},{h / 2} "
        f"h{-(w - 2 * notch)} l{-notch},{-h / 2} z"
    )


def svg_chevron_column_header(
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    *,
    fill: str,
    zone_id: str,
    icon_id: str = "",
    is_first: bool = False,
    is_last: bool = False,
    font_size: float = 16,
) -> str:
    """Column header chevron with data-zone-id / data-primitive markers (复刻流程2)."""
    path = _chevron_header_path(x, y, w, h, is_first=is_first, is_last=is_last)
    icon_attr = f' data-icon-id="{escape(icon_id)}"' if icon_id else ""
    text_y = y + h / 2 + font_size * 0.35
    return (
        f'<g data-zone-id="{escape(zone_id)}" data-primitive="chevron_column_header">'
        f'<path d="{path}" fill="{fill}" stroke="none"/>'
        f'<text x="{x + w / 2}" y="{text_y}" font-family="Microsoft YaHei, Arial, sans-serif" '
        f'font-size="{font_size}" font-weight="700" fill="#FFFFFF" text-anchor="middle">'
        f"{escape(label)}</text>"
        f'<circle cx="{x + 22}" cy="{y + h / 2}" r="10" fill="#FFFFFF" opacity="0.2"{icon_attr}/>'
        f"</g>"
    )


def svg_chain_arrow(
    x1: float,
    y: float,
    x2: float,
    *,
    connector_id: str,
    stroke: str = "#94A3B8",
) -> str:
    """Horizontal flow arrow between columns."""
    mid_y = y
    head = 8
    return (
        f'<g data-chain-connector="{escape(connector_id)}" data-primitive="horizontal_arrow_connector">'
        f'<line x1="{x1}" y1="{mid_y}" x2="{x2 - head}" y2="{mid_y}" stroke="{stroke}" stroke-width="2"/>'
        f'<polygon points="{x2},{mid_y} {x2 - head},{mid_y - head / 2} {x2 - head},{mid_y + head / 2}" fill="{stroke}"/>'
        f"</g>"
    )


def svg_box_connector_arrow(
    source_box: dict[str, float] | tuple[float, float, float, float],
    target_box: dict[str, float] | tuple[float, float, float, float],
    *,
    connector_id: str,
    stroke: str = "#475569",
    stroke_width: float = 4.0,
    bow: float = 0.0,
    pad_start: float = 8.0,
    pad_end: float = 18.0,
) -> str:
    """Curved editable connector from one rectangle edge to another."""
    sx, sy, sw, sh = _box_tuple(source_box)
    tx, ty, tw, th = _box_tuple(target_box)
    geometry = get_box_to_box_arrow(
        sx, sy, sw, sh,
        tx, ty, tw, th,
        ArrowOptions(bow=bow, pad_start=pad_start, pad_end=pad_end),
    )
    return (
        f'<g data-chain-connector="{escape(connector_id)}" '
        f'data-primitive="box_to_box_arrow_connector">'
        f'{svg_path_arrow(geometry, stroke=stroke, stroke_width=stroke_width, connector_id=connector_id)}'
        f"</g>"
    )


def svg_center_node_arrow(
    source_box: dict[str, float] | tuple[float, float, float, float],
    *,
    center: tuple[float, float],
    radius: float,
    connector_id: str,
    fill: str = "#475569",
    gap: float = 6.0,
    shaft_width: float = 14.0,
    head_width: float = 32.0,
    head_length: float = 34.0,
) -> str:
    """Short chunky polygon arrow from a source box toward a center circle."""
    sx, sy, sw, sh = _box_tuple(source_box)
    cx, cy = center
    edge = get_box_to_box_arrow(
        sx, sy, sw, sh,
        cx - radius, cy - radius, radius * 2, radius * 2,
        ArrowOptions(pad_start=8.0, pad_end=max(0.0, gap)),
    )
    points = block_arrow_polygon(
        edge.start,
        edge.end,
        shaft_width=shaft_width,
        head_width=head_width,
        head_length=head_length,
    )
    return (
        f'<polygon points="{points}" fill="{fill}" '
        f'data-chain-connector="{escape(connector_id)}" '
        f'data-primitive="center_node_block_arrow"/>'
    )


def svg_block_arrow_between(
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    connector_id: str,
    fill: str = "#475569",
    shaft_width: float = 14.0,
    head_width: float = 32.0,
    head_length: float = 34.0,
) -> str:
    """Straight chunky polygon connector between two explicit points."""
    points = block_arrow_polygon(
        start,
        end,
        shaft_width=shaft_width,
        head_width=head_width,
        head_length=head_length,
    )
    return (
        f'<polygon points="{points}" fill="{fill}" '
        f'data-chain-connector="{escape(connector_id)}" '
        f'data-primitive="block_arrow_connector"/>'
    )


def _box_tuple(box: dict[str, float] | tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    if isinstance(box, dict):
        return float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"])
    return float(box[0]), float(box[1]), float(box[2]), float(box[3])


def svg_section_label_pill(
    x: float,
    y: float,
    label: str,
    *,
    icon_id: str = "",
    fill: str = "#E8EEF4",
    text_fill: str = "#1B4F8A",
    font_size: float = 13,
) -> str:
    """Section label strip (e.g. 内容提供) with optional icon anchor."""
    width = max(88.0, cjk_text_width(label, font_size) + 36)
    icon_attr = f' data-icon-id="{escape(icon_id)}"' if icon_id else ""
    return (
        f'<g data-primitive="section_label_pill"{icon_attr}>'
        f'<rect x="{x}" y="{y}" width="{width}" height="{font_size + 10}" rx="4" fill="{fill}"/>'
        f'<text x="{x + 10}" y="{y + font_size + 2}" font-family="Microsoft YaHei, Arial, sans-serif" '
        f'font-size="{font_size}" font-weight="700" fill="{text_fill}">▶ {escape(label)}</text>'
        f"</g>"
    )


def svg_footer_principle_chip(
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    *,
    icon_id: str = "",
    fill: str = "#E8EEF4",
    font_size: float = 12,
) -> str:
    """Single bottom principle chip (not a chevron chain)."""
    lines = wrap_cjk(label, w - 16, font_size, max_lines=2)
    icon_attr = f' data-icon-id="{escape(icon_id)}"' if icon_id else ""
    text_block = svg_centered_paragraph_text(
        x + w / 2,
        y,
        h,
        lines,
        font_family="Microsoft YaHei, Arial, sans-serif",
        font_size=font_size,
        line_height=14,
        font_weight=600,
        fill="#1F2937",
        anchor="middle",
    )
    return (
        f'<g data-primitive="footer_principle_chip"{icon_attr}>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="#D1D5DB" stroke-width="1"/>'
        f"{text_block}"
        f"</g>"
    )


def svg_guidance_banner(
    x: float,
    y: float,
    w: float,
    h: float,
    lines: Iterable[str],
    *,
    zone_id: str = "zone_guidance",
    icon_id: str = "icon-guidance",
    fill: str = "#1A3D5C",
) -> str:
    """Top guidance band with paragraph text and icon marker."""
    text = svg_paragraph_text(
        x + 48,
        y + 22,
        lines,
        font_family="Microsoft YaHei, Arial, sans-serif",
        font_size=15,
        line_height=20,
        fill="#FFFFFF",
    )
    return (
        f'<g data-zone-id="{escape(zone_id)}" data-primitive="guidance_banner">'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}"/>'
        f'<circle cx="{x + 24}" cy="{y + h / 2}" r="12" fill="#FCD34D" data-icon-id="{escape(icon_id)}"/>'
        f"{text}"
        f"</g>"
    )


def svg_title_band(
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    *,
    zone_id: str = "zone_title",
    subtitle: str = "",
    rule_fill: str = "#C8102E",
    title_fill: str = "#0B3A8D",
    font_size: float = 28,
    font_family: str = "Microsoft YaHei, Arial, sans-serif",
) -> str:
    """Page title strip with optional subtitle and bottom accent rule."""
    rule_y = y + h - 4
    title_y = y + font_size + 8
    subtitle_block = ""
    if subtitle.strip():
        subtitle_block = (
            f'<text x="{x + w / 2}" y="{title_y + 22}" font-family="{font_family}" '
            f'font-size="{max(12, font_size * 0.55):.1f}" fill="#475569" text-anchor="middle">'
            f"{escape(subtitle.strip())}</text>"
        )
    return (
        f'<g data-zone-id="{escape(zone_id)}" data-primitive="title_band">'
        f'<text x="{x + w / 2}" y="{title_y}" font-family="{font_family}" font-size="{font_size}" '
        f'font-weight="700" fill="{title_fill}" text-anchor="middle">{escape(title.strip())}</text>'
        f"{subtitle_block}"
        f'<rect x="{x}" y="{rule_y}" width="{w}" height="3" fill="{rule_fill}"/>'
        f"</g>"
    )


def svg_column_panel(
    x: float,
    y: float,
    w: float,
    h: float,
    header_label: str,
    *,
    zone_id: str,
    header_h: float = 44.0,
    header_fill: str = "#1B4F8A",
    body_fill: str = "#F8FAFC",
    body_stroke: str = "#CBD5E1",
    icon_id: str = "",
    is_first: bool = False,
    is_last: bool = False,
    body_lines: Iterable[str] | None = None,
    font_family: str = "Microsoft YaHei, Arial, sans-serif",
) -> str:
    """Column shell: chevron header + body card for five-column / stage layouts."""
    header = svg_chevron_column_header(
        x,
        y,
        w,
        header_h,
        header_label,
        fill=header_fill,
        zone_id=zone_id,
        icon_id=icon_id,
        is_first=is_first,
        is_last=is_last,
    )
    body_y = y + header_h
    body_h = max(0.0, h - header_h)
    body_text = ""
    if body_lines:
        fitted = fit_text_box(
            " ".join(str(line) for line in body_lines if str(line).strip()),
            (x + 10, body_y + 8, w - 20, body_h - 16),
            max_lines=4,
        )
        if fitted.lines:
            body_text = svg_paragraph_text(
                x + 12,
                body_y + 18,
                fitted.lines,
                font_family=font_family,
                font_size=fitted.font_size,
                line_height=fitted.line_height,
                fill="#334155",
                element_id=f"{zone_id}-body",
            )
    return (
        f'<g data-zone-id="{escape(zone_id)}" data-primitive="column_panel">'
        f"{header}"
        f'<rect x="{x}" y="{body_y}" width="{w}" height="{body_h}" fill="{body_fill}" '
        f'stroke="{body_stroke}" stroke-width="1"/>'
        f"{body_text}"
        f"</g>"
    )


def svg_resource_card(
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body_lines: Iterable[str],
    *,
    zone_id: str,
    card_fill: str = "#FFFFFF",
    title_fill: str = "#0B3A8D",
    stroke: str = "#CBD5E1",
    font_family: str = "Microsoft YaHei, Arial, sans-serif",
    title_font_size: float = 13.0,
    min_body_size: float = 7.5,
    max_body_size: float = 11.0,
) -> str:
    """Dense resource card with fitted body copy inside a bordered panel."""
    title_h = title_font_size + 14
    body_box_h = max(0.0, h - title_h - 8)
    fitted = fit_text_box(
        "\n".join(str(line) for line in body_lines if str(line).strip()),
        (x + 10, y + title_h, w - 20, body_box_h),
        min_size=min_body_size,
        max_size=max_body_size,
        max_lines=5,
    )
    body_svg = ""
    if fitted.lines:
        body_svg = svg_paragraph_text(
            x + 12,
            y + title_h + 6,
            fitted.lines,
            font_family=font_family,
            font_size=fitted.font_size,
            line_height=fitted.line_height,
            fill="#334155",
            element_id=f"{zone_id}-body",
        )
    return (
        f'<g data-zone-id="{escape(zone_id)}" data-primitive="resource_card">'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{card_fill}" '
        f'stroke="{stroke}" stroke-width="1"/>'
        f'<text x="{x + 10}" y="{y + title_font_size + 6}" font-family="{font_family}" '
        f'font-size="{title_font_size}" font-weight="700" fill="{title_fill}">'
        f"{escape(title.strip())}</text>"
        f"{body_svg}"
        f"</g>"
    )


def svg_bottom_flow_chain(
    segments: Sequence[ChevronSegment],
    *,
    zone_id: str = "zone_main_chain",
    fill: str = "#1B4F8A",
    connector_stroke: str = "#94A3B8",
) -> str:
    """Bottom chevron flow chain built from distribute_chevrons() segments."""
    if not segments:
        return ""
    parts: list[str] = [
        f'<g data-zone-id="{escape(zone_id)}" data-primitive="bottom_flow_chain">',
    ]
    for index, segment in enumerate(segments):
        path = _chevron_header_path(
            segment.x,
            segment.y,
            segment.w,
            segment.h,
            is_first=segment.is_first,
            is_last=segment.is_last,
        )
        text_y = segment.y + segment.h / 2 + segment.font_size * 0.35
        parts.append(
            f'<g data-chain-node="{index}">'
            f'<path d="{path}" fill="{fill}" stroke="none"/>'
            f'<text x="{segment.x + segment.w / 2}" y="{text_y}" '
            f'font-family="Microsoft YaHei, Arial, sans-serif" font-size="{segment.font_size}" '
            f'font-weight="700" fill="#FFFFFF" text-anchor="middle">{escape(segment.label)}</text>'
            f"</g>"
        )
        if index < len(segments) - 1:
            next_seg = segments[index + 1]
            parts.append(
                svg_chain_arrow(
                    segment.x + segment.w,
                    segment.y + segment.h / 2,
                    next_seg.x,
                    connector_id=f"chain_{index}_to_{index + 1}",
                    stroke=connector_stroke,
                ),
            )
    parts.append("</g>")
    return "".join(parts)


def svg_footer_principle_chips(
    chips: Sequence[tuple[float, float, float, float, str]],
    *,
    zone_id: str = "zone_footer",
    fill: str = "#E8EEF4",
    font_size: float = 12.0,
) -> str:
    """Row of footer principle chips; each chip is (x, y, w, h, label)."""
    rendered = [
        svg_footer_principle_chip(x, y, w, h, label, fill=fill, font_size=font_size)
        for x, y, w, h, label in chips
    ]
    return (
        f'<g data-zone-id="{escape(zone_id)}" data-primitive="footer_principle_chips">'
        f"{''.join(rendered)}"
        f"</g>"
    )
