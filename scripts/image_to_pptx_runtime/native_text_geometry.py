"""Geometry-only QA for native text reconstructed from a reference image.

The graphic-text policy records image-space OCR regions while authored SVGs
record text baselines and font sizes.  This module compares the two contracts
without modifying the SVG.  It is intentionally diagnostic: OCR boxes are
visual glyph regions, not PowerPoint text-frame bounds, so the report must not
be used as an automatic font-size replacement.
"""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import median
from typing import Any, Mapping


SVG_NS = "http://www.w3.org/2000/svg"
SCHEMA = "cyberppt.native_text_geometry_qa.v1"
LOCKED_STYLE_ATTR = "data-cyberppt-native-text-style"
TEXT_ID_ATTR = "data-cyberppt-text-id"
_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
_COORDINATE_TOLERANCE = 12.0
_FONT_RATIO_MIN = 0.45
_FONT_RATIO_MAX = 1.50
_MIN_INTRA_TEXT_X_SPAN = 120.0
_MAX_INTRA_TEXT_X_SPAN_IN_FONTS = 6.0
_MAX_BASELINE_STEP_IN_FONTS = 4.0
POINTS_PER_SVG_PX = 0.75
DEFAULT_MIN_FONT_PT_BY_ROLE = {
    "caption": 9.0,
    "card_body": 10.0,
    "body": 12.0,
    "module_title": 15.0,
    "page_title": 20.0,
}


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _number(value: object) -> float | None:
    if value is None:
        return None
    match = _NUMBER_RE.search(str(value))
    return float(match.group(0)) if match else None


def _numbers(value: object) -> list[float]:
    return [float(match.group(0)) for match in _NUMBER_RE.finditer(str(value or ""))]


def _bbox(value: object) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        left, top, right, bottom = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(left) and math.isfinite(top) and math.isfinite(right) and math.isfinite(bottom)):
        return None
    if not (left < right and top < bottom):
        return None
    return left, top, right, bottom


def _normalise_svg_text(node: ET.Element) -> str:
    return _text("".join(node.itertext()))


def _svg_canvas(root: ET.Element) -> tuple[float, float, float, float, float, float]:
    viewbox = _numbers(root.get("viewBox"))
    if len(viewbox) != 4 or viewbox[2] <= 0 or viewbox[3] <= 0:
        width = _number(root.get("width")) or 1.0
        height = _number(root.get("height")) or 1.0
        return 0.0, 0.0, width, height, width, height
    pixel_width = _number(root.get("width")) or viewbox[2]
    pixel_height = _number(root.get("height")) or viewbox[3]
    return (*viewbox, pixel_width, pixel_height)


def _map_bbox(
    box: tuple[float, float, float, float],
    *,
    viewbox: tuple[float, float, float, float],
    pixel_width: float,
    pixel_height: float,
) -> tuple[float, float, float, float]:
    view_x, view_y, view_width, view_height = viewbox
    left, top, right, bottom = box
    return (
        view_x + left * view_width / pixel_width,
        view_y + top * view_height / pixel_height,
        view_x + right * view_width / pixel_width,
        view_y + bottom * view_height / pixel_height,
    )


def _node_x(node: ET.Element) -> float | None:
    values = _numbers(node.get("x"))
    return values[0] if values else None


def _node_y(node: ET.Element) -> float | None:
    values = _numbers(node.get("y"))
    return values[0] if values else None


def _font_size(node: ET.Element) -> float | None:
    value = _number(node.get("font-size"))
    if value is not None and value > 0:
        return value
    return None


def _line_metrics(node: ET.Element) -> tuple[int, float | None]:
    """Return visual baseline rows and a representative baseline step."""

    explicit_baselines: list[float] = []
    baseline_steps: list[float] = []
    for child in node.iter():
        if child is node or _local_name(child) != "tspan":
            continue
        y = _number(child.get("y"))
        if y is not None and not any(math.isclose(y, value, abs_tol=1e-9) for value in explicit_baselines):
            explicit_baselines.append(y)
        dy = _number(child.get("dy"))
        if dy is not None and not math.isclose(dy, 0.0, abs_tol=1e-9):
            baseline_steps.append(abs(dy))
    if len(explicit_baselines) >= 2:
        ordered = sorted(explicit_baselines)
        return len(ordered), median(right - left for left, right in zip(ordered, ordered[1:]))
    if explicit_baselines:
        return 1, None
    return 1 + len(baseline_steps), (median(baseline_steps) if baseline_steps else None)


def _intra_text_geometry(node: ET.Element, font_size: float | None) -> tuple[float, float, list[str]]:
    """Detect tspans that accidentally jump into another visual region."""

    xs: list[float] = []
    ys: list[float] = []
    for current in node.iter():
        x = _number(current.get("x"))
        y = _number(current.get("y"))
        if x is not None:
            xs.append(x)
        if y is not None:
            ys.append(y)
    x_span = max(xs) - min(xs) if xs else 0.0
    ordered_y = sorted(set(ys))
    max_baseline_step = max(
        (right - left for left, right in zip(ordered_y, ordered_y[1:])),
        default=0.0,
    )
    issues: list[str] = []
    if font_size is not None:
        if x_span > max(_MIN_INTRA_TEXT_X_SPAN, font_size * _MAX_INTRA_TEXT_X_SPAN_IN_FONTS):
            issues.append("tspan x positions jump across visual regions")
        if max_baseline_step > font_size * _MAX_BASELINE_STEP_IN_FONTS:
            issues.append("tspan baselines jump across visual regions")
    return x_span, max_baseline_step, issues


def _policy_items(policy: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    raw = policy.get("items") if isinstance(policy, Mapping) else None
    return [dict(item) for item in raw if isinstance(item, Mapping) and _text(item.get("treatment")) == "native_text"] if isinstance(raw, list) else []


def _text_nodes(root: ET.Element) -> list[ET.Element]:
    return [node for node in root.iter() if _local_name(node) == "text" and _normalise_svg_text(node)]


def _match_nodes(items: list[dict[str, Any]], nodes: list[ET.Element]) -> tuple[dict[int, tuple[ET.Element, str, float]], list[str]]:
    """Match policy items to nodes and return only unambiguous matches."""

    warnings: list[str] = []
    matched: dict[int, tuple[ET.Element, str, float]] = {}
    used: set[int] = set()
    node_by_id = {
        _text(node.get(TEXT_ID_ATTR)): (index, node)
        for index, node in enumerate(nodes)
        if _text(node.get(TEXT_ID_ATTR))
    }
    for index, item in enumerate(items):
        item_id = _text(item.get("id"))
        if item_id and item_id in node_by_id:
            node_index, node = node_by_id[item_id]
            if node_index in used:
                warnings.append(f"{item_id}: explicit text id matched more than once")
            else:
                matched[index] = (node, "explicit_id", 1.0)
                used.add(node_index)

    for index, item in enumerate(items):
        if index in matched:
            continue
        expected = _text(item.get("text"))
        candidates = [
            (node_index, node)
            for node_index, node in enumerate(nodes)
            if node_index not in used and _normalise_svg_text(node) == expected
        ]
        if len(candidates) == 1:
            node_index, node = candidates[0]
            matched[index] = (node, "unique_text", 0.95)
            used.add(node_index)

    unresolved = [index for index in range(len(items)) if index not in matched]
    if unresolved:
        remaining_nodes = [(index, node) for index, node in enumerate(nodes) if index not in used]
        if len(unresolved) == len(remaining_nodes) and unresolved:
            # Sequence is only useful when every remaining item/node is still
            # one-to-one.  A partial sequence match would hide a real mismatch.
            for item_index, (node_index, node) in zip(unresolved, remaining_nodes):
                matched[item_index] = (node, "stable_order", 0.75)
                used.add(node_index)
        else:
            for item_index in unresolved:
                item_id = _text(items[item_index].get("id")) or f"item-{item_index + 1:03d}"
                expected = _text(items[item_index].get("text"))
                same_text = [node for node in nodes if _normalise_svg_text(node) == expected]
                if len(same_text) > 1:
                    warnings.append(f"{item_id}: duplicate text is ambiguous")
                else:
                    warnings.append(f"{item_id}: no unambiguous authored SVG text match")
    return matched, warnings


def analyze_native_text_geometry(
    policy: Mapping[str, Any] | None,
    *,
    authored_svg: Path | str,
    page_number: int,
    body_scale: float = 1.0,
    min_font_pt_by_role: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Compare native SVG text geometry against policy OCR boxes, read-only."""

    svg_path = Path(authored_svg).expanduser().resolve()
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
    except (OSError, ET.ParseError) as exc:
        return {
            "schema": SCHEMA,
            "page_number": page_number,
            "path": str(svg_path),
            "status": "invalid",
            "valid": False,
            "review_required": True,
            "items": [],
            "warnings": [str(exc)],
        }
    locked = root.get(LOCKED_STYLE_ATTR) == "locked"
    if not math.isfinite(body_scale) or body_scale <= 0:
        raise ValueError("body_scale must be a finite positive number")
    font_floors = dict(DEFAULT_MIN_FONT_PT_BY_ROLE)
    if min_font_pt_by_role is not None:
        font_floors.update({str(key): float(value) for key, value in min_font_pt_by_role.items()})

    view_x, view_y, view_width, view_height, pixel_width, pixel_height = _svg_canvas(root)
    items = _policy_items(policy)
    exact_source_fidelity = (
        isinstance(policy, Mapping)
        and policy.get("fidelity_mode") == "exact_source_image"
    )
    nodes = _text_nodes(root)
    matched, match_warnings = _match_nodes(items, nodes)
    reports: list[dict[str, Any]] = []
    warnings = list(match_warnings)
    for index, item in enumerate(items):
        item_id = _text(item.get("id")) or f"item-{index + 1:03d}"
        source_box = _bbox(item.get("bbox"))
        base: dict[str, Any] = {
            "text_id": item_id,
            "text": _text(item.get("text")),
            "source_bbox": list(source_box) if source_box else None,
            "svg_x": None,
            "svg_y": None,
            "font_size": None,
            "line_count": None,
            "line_step": None,
            "dx": None,
            "dy": None,
            "font_ratio": None,
            "match_method": "none",
            "match_confidence": 0.0,
            "action": "review",
        }
        if source_box is None:
            base["action"] = "missing_bbox"
            warnings.append(f"{item_id}: native_text bbox is missing or invalid")
            reports.append(base)
            continue
        match = matched.get(index)
        if match is None:
            reports.append(base)
            continue
        node, method, confidence = match
        svg_x = _node_x(node)
        svg_y = _node_y(node)
        font_size = _font_size(node)
        role = _text(item.get("role")) or "body"
        final_font_pt = font_size * body_scale * POINTS_PER_SVG_PX if font_size is not None else None
        minimum_font_pt = font_floors.get(role, font_floors["body"])
        line_count, line_step = _line_metrics(node)
        intra_text_x_span, max_baseline_step, structural_issues = _intra_text_geometry(
            node, font_size
        )
        mapped = _map_bbox(source_box, viewbox=(view_x, view_y, view_width, view_height), pixel_width=pixel_width, pixel_height=pixel_height)
        mapped_left, mapped_top, _, mapped_bottom = mapped
        # A frozen exact-source inventory describes the complete visible region.
        # Multiline nodes therefore compare their first baseline with the first
        # line instead of the region's final baseline.
        expected_baseline = (
            mapped_top + (font_size or 0)
            if exact_source_fidelity and line_count > 1
            else mapped_bottom
        )
        delta_x = svg_x - mapped_left if svg_x is not None else None
        delta_y = svg_y - expected_baseline if svg_y is not None else None
        bbox_height = mapped_bottom - mapped_top
        per_line_height = bbox_height / max(line_count, 1)
        font_ratio = font_size / per_line_height if font_size is not None and per_line_height > 0 else None
        issues: list[str] = []
        if svg_x is None or svg_y is None:
            issues.append("missing SVG x/y")
        if delta_x is not None and abs(delta_x) > _COORDINATE_TOLERANCE:
            issues.append("x deviation exceeds QA tolerance")
        if delta_y is not None and abs(delta_y) > _COORDINATE_TOLERANCE:
            issues.append("baseline deviation exceeds QA tolerance")
        if font_ratio is not None and not (_FONT_RATIO_MIN <= font_ratio <= _FONT_RATIO_MAX):
            issues.append("font-to-region ratio requires review")
        if final_font_pt is None:
            issues.append("missing SVG font-size")
        elif not exact_source_fidelity and final_font_pt < minimum_font_pt:
            issues.append(
                f"final font size {final_font_pt:.2f}pt is below {minimum_font_pt:.2f}pt floor for {role}"
            )
        issues.extend(structural_issues)
        base.update(
            {
                "mapped_bbox": list(mapped),
                "svg_x": svg_x,
                "svg_y": svg_y,
                "font_size": font_size,
                "role": role,
                "body_scale": body_scale,
                "final_font_pt": final_font_pt,
                "minimum_font_pt": minimum_font_pt,
                "exact_source_fidelity": exact_source_fidelity,
                "line_count": line_count,
                "line_step": line_step,
                "expected_x": mapped_left,
                "expected_baseline": expected_baseline,
                "dx": delta_x,
                "dy": delta_y,
                "font_ratio": font_ratio,
                "intra_text_x_span": intra_text_x_span,
                "max_baseline_step": max_baseline_step,
                "structural_issues": structural_issues,
                "match_method": method,
                "match_confidence": confidence,
                "issues": issues,
                "action": "review" if issues else "pass",
            }
        )
        if issues:
            warnings.append(f"{item_id}: " + "; ".join(issues))
        reports.append(base)
    return {
        "schema": SCHEMA,
        "page_number": page_number,
        "path": str(svg_path),
        "status": "checked_locked" if locked else "complete",
        "valid": not warnings,
        "review_required": bool(warnings),
        "qa_only": True,
        "detail_level": "full",
        "canvas": {
            "pixel_width": pixel_width,
            "pixel_height": pixel_height,
            "viewBox": [view_x, view_y, view_width, view_height],
        },
        "items": reports,
        "warnings": warnings,
    }


def write_native_text_geometry_receipt(
    reports: list[dict[str, Any]],
    output_path: Path | str,
) -> Path:
    """Persist page-level geometry QA without changing the source SVGs."""

    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "qa_only": True,
                "pages": reports,
                "valid": all(report.get("valid") is True for report in reports),
                "review_required": any(report.get("review_required") for report in reports),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8", newline="\n",
    )
    return path
