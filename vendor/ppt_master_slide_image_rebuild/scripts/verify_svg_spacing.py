#!/usr/bin/env python3
"""
PPT Master - SVG Spacing Verifier

Detect likely visual collisions in rebuilt reference slides. This complements
text-fit and icon/text formula checks by inspecting approximate rendered boxes
for icons, badges, and dense horizontal labels.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from layout_reference_components import cjk_text_width

SVG_NS = "{http://www.w3.org/2000/svg}"
PAINT_ATTRS = ("fill", "stroke", "stop-color", "flood-color", "color")
ALLOWED_NON_HEX_PAINTS = {"none", "transparent", "currentcolor"}
SAFE_PAINT_PREFIXES = ("#", "url(")


@dataclass(frozen=True)
class Box:
    kind: str
    label: str
    x1: float
    y1: float
    x2: float
    y2: float
    groups: tuple[str, ...]
    stroke_opacity: float | None = None
    fill_opacity: float | None = None
    primitive: str = ""
    tag: str = ""

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass(frozen=True)
class Container:
    label: str
    x1: float
    y1: float
    x2: float
    y2: float
    fill: str = ""
    stroke: str = ""

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _opacity(value: str | None) -> float | None:
    parsed = _float(value)
    if parsed is None:
        return None
    return max(0.0, min(1.0, parsed))


def _numbers_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    nums = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", raw)]
    if len(nums) < 4:
        return None
    xs = nums[0::2]
    ys = nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_attr(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    nums = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", raw)]
    if len(nums) < 4:
        return None
    x, y, w, h = nums[:4]
    return x, y, x + w, y + h


def _path_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", raw)
    if not tokens:
        return None

    points: list[tuple[float, float]] = []
    index = 0
    cmd = ""
    x = 0.0
    y = 0.0
    start_x = 0.0
    start_y = 0.0

    def is_cmd(value: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z]", value))

    def has_number(offset: int = 0) -> bool:
        return index + offset < len(tokens) and not is_cmd(tokens[index + offset])

    def has_numbers(count: int) -> bool:
        return all(has_number(offset) for offset in range(count))

    def take_number() -> float:
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    def add_point(px: float, py: float) -> None:
        points.append((px, py))

    try:
        while index < len(tokens):
            if is_cmd(tokens[index]):
                cmd = tokens[index]
                index += 1
            if not cmd:
                return _numbers_bbox(raw)

            absolute = cmd.isupper()
            op = cmd.upper()

            if op == "Z":
                x, y = start_x, start_y
                add_point(x, y)
                cmd = ""
                continue

            if op == "M":
                first = True
                while has_numbers(2):
                    nx = take_number()
                    ny = take_number()
                    x = nx if absolute else x + nx
                    y = ny if absolute else y + ny
                    add_point(x, y)
                    if first:
                        start_x, start_y = x, y
                        first = False
                        cmd = "L" if absolute else "l"
                continue

            if op == "L":
                while has_numbers(2):
                    nx = take_number()
                    ny = take_number()
                    x = nx if absolute else x + nx
                    y = ny if absolute else y + ny
                    add_point(x, y)
                continue

            if op == "H":
                while has_number():
                    nx = take_number()
                    x = nx if absolute else x + nx
                    add_point(x, y)
                continue

            if op == "V":
                while has_number():
                    ny = take_number()
                    y = ny if absolute else y + ny
                    add_point(x, y)
                continue

            if op == "C":
                while has_numbers(6):
                    coords = [take_number() for _ in range(6)]
                    for px, py in zip(coords[0::2], coords[1::2]):
                        ax = px if absolute else x + px
                        ay = py if absolute else y + py
                        add_point(ax, ay)
                    end_x, end_y = coords[4], coords[5]
                    x = end_x if absolute else x + end_x
                    y = end_y if absolute else y + end_y
                continue

            if op == "S" or op == "Q":
                stride = 4
                while has_numbers(stride):
                    coords = [take_number() for _ in range(stride)]
                    for px, py in zip(coords[0::2], coords[1::2]):
                        ax = px if absolute else x + px
                        ay = py if absolute else y + py
                        add_point(ax, ay)
                    end_x, end_y = coords[-2], coords[-1]
                    x = end_x if absolute else x + end_x
                    y = end_y if absolute else y + end_y
                continue

            if op == "T":
                while has_numbers(2):
                    nx = take_number()
                    ny = take_number()
                    x = nx if absolute else x + nx
                    y = ny if absolute else y + ny
                    add_point(x, y)
                continue

            if op == "A":
                while has_numbers(7):
                    coords = [take_number() for _ in range(7)]
                    end_x, end_y = coords[5], coords[6]
                    x = end_x if absolute else x + end_x
                    y = end_y if absolute else y + end_y
                    add_point(x, y)
                continue

            return _numbers_bbox(raw)
    except (ValueError, IndexError):
        return _numbers_bbox(raw)

    if not points:
        return _numbers_bbox(raw)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _points_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    return _numbers_bbox(raw)


def _text(elem: ET.Element) -> str:
    return "".join(elem.itertext()).strip()


def _visual_lines(elem: ET.Element) -> list[str]:
    tspans = [child for child in list(elem) if _strip_ns(child.tag) == "tspan"]
    if not tspans:
        return [_text(elem)]
    lines = ["".join(child.itertext()).strip() for child in tspans]
    return [line for line in lines if line] or [_text(elem)]


def _text_box(elem: ET.Element, groups: tuple[str, ...]) -> Box | None:
    x = _float(elem.get("x"))
    y = _float(elem.get("y"))
    size = _float(elem.get("font-size")) or 16
    if x is None or y is None:
        return None
    lines = _visual_lines(elem)
    if not lines:
        return None
    approx_w = max(cjk_text_width(line, size) for line in lines)
    line_height = _float(elem.get("data-paragraph-line-height")) or size * 1.3
    approx_h = line_height * (len(lines) - 1) + size * 1.3
    anchor = elem.get("text-anchor", "start")
    if anchor == "middle":
        x1, x2 = x - approx_w / 2, x + approx_w / 2
    elif anchor == "end":
        x1, x2 = x - approx_w, x
    else:
        x1, x2 = x, x + approx_w
    y1 = y - size
    y2 = y + approx_h - size
    label = elem.get("data-fit-label") or lines[0][:32]
    return Box("text", label, x1, y1, x2, y2, groups)


def _circle_box(elem: ET.Element, label: str, groups: tuple[str, ...]) -> Box | None:
    cx = _float(elem.get("cx"))
    cy = _float(elem.get("cy"))
    r = _float(elem.get("r"))
    if cx is None or cy is None or r is None:
        return None
    return Box("icon", label, cx - r, cy - r, cx + r, cy + r, groups)


def _group_bbox(elem: ET.Element, label: str, groups: tuple[str, ...]) -> Box | None:
    boxes: list[tuple[float, float, float, float]] = []
    for child in elem.iter():
        tag = _strip_ns(child.tag)
        if tag == "circle":
            cx = _float(child.get("cx"))
            cy = _float(child.get("cy"))
            r = _float(child.get("r"))
            if cx is not None and cy is not None and r is not None:
                boxes.append((cx - r, cy - r, cx + r, cy + r))
        elif tag == "rect":
            x = _float(child.get("x"))
            y = _float(child.get("y"))
            w = _float(child.get("width"))
            h = _float(child.get("height"))
            if x is not None and y is not None and w is not None and h is not None:
                boxes.append((x, y, x + w, y + h))
        elif tag == "line":
            x1 = _float(child.get("x1"))
            y1 = _float(child.get("y1"))
            x2 = _float(child.get("x2"))
            y2 = _float(child.get("y2"))
            if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
                boxes.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        elif tag in {"polygon", "polyline"}:
            bbox = _points_bbox(child.get("points"))
            if bbox:
                boxes.append(bbox)
        elif tag == "path":
            bbox = _path_bbox(child.get("d"))
            if bbox:
                boxes.append(bbox)
    if not boxes:
        return None
    return Box(
        "badge",
        label,
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
        groups,
    )


def _graphic_box(elem: ET.Element, label: str, groups: tuple[str, ...]) -> Box | None:
    tag = _strip_ns(elem.tag)
    bbox = _element_bbox(elem)
    if not bbox:
        return None
    x1, y1, x2, y2 = bbox
    # Only generic small graphics are treated as icon-like objects. Larger
    # shapes are usually panels, arrows, bands, or decorative containers.
    if x2 - x1 > 42 or y2 - y1 > 42:
        return None
    return Box("graphic", label, x1, y1, x2, y2, groups)


def _element_bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    tag = _strip_ns(elem.tag)
    bbox: tuple[float, float, float, float] | None = None
    if tag == "circle":
        circle = _circle_box(elem, tag, ())
        if circle:
            bbox = (circle.x1, circle.y1, circle.x2, circle.y2)
    elif tag == "ellipse":
        cx = _float(elem.get("cx"))
        cy = _float(elem.get("cy"))
        rx = _float(elem.get("rx"))
        ry = _float(elem.get("ry"))
        if cx is not None and cy is not None and rx is not None and ry is not None:
            bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
    elif tag == "line":
        x1 = _float(elem.get("x1"))
        y1 = _float(elem.get("y1"))
        x2 = _float(elem.get("x2"))
        y2 = _float(elem.get("y2"))
        if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            bbox = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    elif tag in {"polygon", "polyline"}:
        bbox = _points_bbox(elem.get("points"))
    elif tag == "path":
        bbox = _path_bbox(elem.get("d"))
    return bbox


def _overlap(a: Box, b: Box, *, margin: float = 0) -> bool:
    return not (
        a.x2 + margin <= b.x1
        or b.x2 + margin <= a.x1
        or a.y2 + margin <= b.y1
        or b.y2 + margin <= a.y1
    )


def _hgap(a: Box, b: Box) -> float:
    if a.x2 <= b.x1:
        return b.x1 - a.x2
    if b.x2 <= a.x1:
        return a.x1 - b.x2
    return -min(a.x2, b.x2) + max(a.x1, b.x1)


def _same_group(a: Box, b: Box, prefix: str) -> bool:
    return bool(set(g for g in a.groups if g.startswith(prefix)) & set(g for g in b.groups if g.startswith(prefix)))


def _find_svgs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() == ".svg":
        return [target]
    if (target / "svg_output").is_dir():
        return sorted((target / "svg_output").glob("*.svg"))
    if (target / "svg_final").is_dir():
        return sorted((target / "svg_final").glob("*.svg"))
    return sorted(target.glob("*.svg"))


def _collect_boxes(root: ET.Element) -> list[Box]:
    boxes: list[Box] = []

    def visit(elem: ET.Element, groups: tuple[str, ...]) -> None:
        tag = _strip_ns(elem.tag)
        elem_id = elem.get("id")
        next_groups = groups + ((elem_id,) if elem_id else ())
        connector_id = elem.get("data-chain-connector")
        if connector_id:
            if tag == "g":
                box = _group_bbox(elem, connector_id, next_groups)
            else:
                bbox = _element_bbox(elem)
                box = Box("connector", connector_id, *bbox, next_groups) if bbox else None
            if box:
                boxes.append(Box(
                    "connector",
                    connector_id,
                    box.x1,
                    box.y1,
                    box.x2,
                    box.y2,
                    box.groups,
                    stroke_opacity=_opacity(elem.get("stroke-opacity") or elem.get("opacity")),
                    fill_opacity=_opacity(elem.get("fill-opacity") or elem.get("opacity")),
                    primitive=elem.get("data-primitive", ""),
                    tag=tag,
                ))
        if tag == "g":
            icon_id = elem.get("data-icon-id")
            if icon_id:
                attr_bbox = _bbox_attr(elem.get("data-icon-bbox"))
                if attr_bbox:
                    boxes.append(Box("icon", icon_id, *attr_bbox, next_groups))
                else:
                    for child in elem.iter():
                        if _strip_ns(child.tag) == "circle":
                            box = _circle_box(child, icon_id, next_groups)
                            if box:
                                boxes.append(box)
                                break
            if elem_id and elem_id.startswith("badge-"):
                box = _group_bbox(elem, elem_id, next_groups)
                if box:
                    boxes.append(box)
        elif tag == "text":
            box = _text_box(elem, groups)
            if box:
                boxes.append(box)
        elif tag in {"circle", "ellipse", "polygon", "polyline", "path"}:
            box = _graphic_box(elem, elem_id or tag, groups)
            if box:
                boxes.append(box)
        for child in list(elem):
            visit(child, next_groups)

    visit(root, ())
    return boxes


def _collect_top_band_containers(root: ET.Element) -> list[Container]:
    containers: list[Container] = []
    for elem in root.iter():
        if _strip_ns(elem.tag) != "rect":
            continue
        x = _float(elem.get("x"))
        y = _float(elem.get("y"))
        w = _float(elem.get("width"))
        h = _float(elem.get("height"))
        if x is None or y is None or w is None or h is None:
            continue
        fill = (elem.get("fill") or "").strip()
        stroke = (elem.get("stroke") or "").strip()
        has_visible_frame = bool(stroke and stroke.lower() != "none")
        # Top guidance/title strips are short framed containers. These are the
        # places where PPT text baselines and icon bboxes most often drift into
        # the bottom border after SVG->PPTX conversion.
        if y < 180 and 44 <= h <= 90 and w >= 120 and has_visible_frame:
            containers.append(Container(elem.get("id") or f"rect@{x:.0f},{y:.0f}", x, y, x + w, y + h, fill, stroke))
    return containers


def _box_inside_container(box: Box, container: Container, *, tolerance: float = 1.0) -> bool:
    cx = (box.x1 + box.x2) / 2
    cy = (box.y1 + box.y2) / 2
    return (
        container.x1 - tolerance <= cx <= container.x2 + tolerance
        and container.y1 - tolerance <= cy <= container.y2 + tolerance
    )


def _paint_value_errors(root: ET.Element) -> list[str]:
    errors: list[str] = []
    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        label = elem.get("id") or elem.get("data-text-region-id") or elem.get("data-icon-id") or tag
        values: list[tuple[str, str]] = []
        for attr in PAINT_ATTRS:
            raw = elem.get(attr)
            if raw:
                values.append((attr, raw.strip()))
        style = elem.get("style") or ""
        for part in style.split(";"):
            if ":" not in part:
                continue
            key, raw = part.split(":", 1)
            key = key.strip()
            if key in PAINT_ATTRS:
                values.append((key, raw.strip()))
        for attr, raw in values:
            lowered = raw.lower()
            if not raw or lowered in ALLOWED_NON_HEX_PAINTS or lowered.startswith(SAFE_PAINT_PREFIXES):
                continue
            if re.fullmatch(r"#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?([0-9a-fA-F]{2})?", raw):
                continue
            if re.fullmatch(r"rgb\([^)]+\)", lowered):
                # Existing quality gates handle rgba(); plain rgb() renders in
                # browsers but is not reliably consumed by the PPTX converter.
                errors.append(f"{label}: paint `{attr}={raw}` should be normalized to #RRGGBB for PPTX export")
                continue
            if re.search(r"[A-Za-z]", raw):
                errors.append(
                    f"{label}: named paint `{attr}={raw}` is not PPTX-safe; use an explicit #RRGGBB value"
                )
    return errors


def inspect(svg_path: Path, *, min_gap: float = 8.0, label_gap: float = 12.0) -> dict[str, Any]:
    root = ET.parse(svg_path).getroot()
    boxes = _collect_boxes(root)
    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(_paint_value_errors(root))

    icons = [box for box in boxes if box.kind == "icon"]
    graphics = [box for box in boxes if box.kind == "graphic"]
    badges = [box for box in boxes if box.kind == "badge"]
    texts = [box for box in boxes if box.kind == "text"]
    connectors = [box for box in boxes if box.kind == "connector"]
    top_band_containers = _collect_top_band_containers(root)

    for icon in [*icons, *graphics]:
        for badge in badges:
            if _same_group(icon, badge, "card-") and _overlap(icon, badge, margin=min_gap):
                errors.append(f"{icon.label}: icon overlaps or is too close to {badge.label}")
        for txt in texts:
            if _same_group(icon, txt, "card-") and _overlap(icon, txt, margin=min_gap):
                errors.append(f"{icon.label}: icon overlaps or is too close to text `{txt.label}`")
            if any(group in {"running-chain", "deliverable-strip", "feedback-band"} for group in icon.groups) and any(
                group in {"running-chain", "deliverable-strip", "feedback-band"} for group in txt.groups
            ) and _overlap(icon, txt, margin=2):
                errors.append(f"{icon.label}: small graphic overlaps or is too close to text `{txt.label}`")

    deliverable_texts = [
        box for box in texts
        if any(group == "deliverable-strip" for group in box.groups)
        and not box.label.startswith("deliverable-label")
    ]
    deliverable_texts.sort(key=lambda box: box.x1)
    for left, right in zip(deliverable_texts, deliverable_texts[1:]):
        gap = _hgap(left, right)
        if gap < label_gap:
            errors.append(f"deliverable labels `{left.label}` and `{right.label}` are too close ({gap:.1f}px)")

    for connector in connectors:
        low_opacity = (
            connector.stroke_opacity is not None
            and connector.stroke_opacity < 0.45
            and not connector.primitive
        )
        if low_opacity:
            errors.append(
                f"{connector.label}: low-opacity decorative line is marked as data-chain-connector; "
                "move the marker to the functional arrowhead or remove the connector marker"
            )
        if connector.tag == "path":
            continue
        diagonalish = connector.width >= 14 and connector.height >= 14
        if not diagonalish:
            continue
        if max(connector.width, connector.height) > 80:
            errors.append(
                f"{connector.label}: diagonal connector is too long "
                f"({connector.width:.1f}x{connector.height:.1f}px); use a short chunky arrow near the target node"
            )
        if min(connector.width, connector.height) < 12:
            errors.append(
                f"{connector.label}: diagonal connector is too thin "
                f"({connector.width:.1f}x{connector.height:.1f}px); use a block/polygon arrow"
            )

    for container in top_band_containers:
        for box in [*texts, *icons]:
            if not _box_inside_container(box, container):
                continue
            top_pad = box.y1 - container.y1
            bottom_pad = container.y2 - box.y2
            if top_pad < 3 or bottom_pad < 3:
                errors.append(
                    f"{box.label}: {box.kind} touches or crosses top band `{container.label}` "
                    f"(top={top_pad:.1f}px, bottom={bottom_pad:.1f}px)"
                )
            if box.kind == "text":
                # Text that is technically inside the band can still render
                # lower in PowerPoint than Cairo because of CJK font metrics.
                # Keep a baseline guard from the bottom frame for short bands.
                baseline_to_bottom = container.y2 - box.y2 + max(0.0, box.height * 0.25)
                if baseline_to_bottom < 10:
                    errors.append(
                        f"{box.label}: text baseline is too close to top band `{container.label}` "
                        f"bottom edge ({baseline_to_bottom:.1f}px)"
                    )
            elif bottom_pad < 6:
                errors.append(
                    f"{box.label}: icon/graphic is too close to top band `{container.label}` "
                    f"bottom edge ({bottom_pad:.1f}px)"
                )

    return {
        "path": str(svg_path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "boxes": {
            "icons": len(icons),
            "graphics": len(graphics),
            "badges": len(badges),
            "texts": len(texts),
            "connectors": len(connectors),
            "top_band_containers": len(top_band_containers),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SVG icon/badge/text spacing.")
    parser.add_argument("target", type=Path, help="Project directory or SVG file")
    parser.add_argument("--min-gap", type=float, default=8.0, help="Minimum icon/badge/text gap in px")
    parser.add_argument("--label-gap", type=float, default=12.0, help="Minimum horizontal label gap in px")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    svgs = _find_svgs(args.target)
    if not svgs:
        print(json.dumps({"valid": False, "errors": ["No SVG files found"]}, ensure_ascii=False, indent=2))
        return 1
    results = [inspect(svg, min_gap=args.min_gap, label_gap=args.label_gap) for svg in svgs]
    payload = {"valid": all(result["valid"] for result in results), "count": len(results), "results": results}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
