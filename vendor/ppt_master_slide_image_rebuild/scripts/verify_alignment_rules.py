#!/usr/bin/env python3
"""Verify alignment rules for rebuilt SVG slide pages.

This complements verify_svg_spacing.py. Spacing catches collisions and edge
pressure; this gate checks whether objects inside common horizontal containers
share a stable visual centerline.
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


@dataclass(frozen=True)
class Box:
    kind: str
    label: str
    x1: float
    y1: float
    x2: float
    y2: float
    groups: tuple[str, ...]
    baseline_y: float | None = None
    max_font_size: float | None = None

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass(frozen=True)
class Container:
    label: str
    role: str
    x1: float
    y1: float
    x2: float
    y2: float
    groups: tuple[str, ...]

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

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


def _numbers(raw: str | None) -> list[float]:
    if not raw:
        return []
    return [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", raw)]


def _bbox_attr(raw: str | None) -> tuple[float, float, float, float] | None:
    nums = _numbers(raw)
    if len(nums) < 4:
        return None
    x, y, w, h = nums[:4]
    return x, y, x + w, y + h


def _rect_bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    x = _float(elem.get("x"))
    y = _float(elem.get("y"))
    w = _float(elem.get("width"))
    h = _float(elem.get("height"))
    if x is None or y is None or w is None or h is None:
        return None
    return x, y, x + w, y + h


def _circle_bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    cx = _float(elem.get("cx"))
    cy = _float(elem.get("cy"))
    r = _float(elem.get("r"))
    if cx is None or cy is None or r is None:
        return None
    return cx - r, cy - r, cx + r, cy + r


def _text_lines(elem: ET.Element) -> list[str]:
    tspans = [child for child in list(elem) if _strip_ns(child.tag) == "tspan"]
    block_tspans = [child for child in tspans if child.get("x") is not None or child.get("dy") is not None]
    if block_tspans:
        lines = ["".join(child.itertext()).strip() for child in block_tspans]
    else:
        lines = ["".join(elem.itertext()).strip()]
    return [line for line in lines if line]


def _max_text_size(elem: ET.Element, fallback: float) -> float:
    sizes = [fallback]
    for child in elem.iter():
        size = _float(child.get("font-size"))
        if size is not None:
            sizes.append(size)
    return max(sizes)


def _text_box(elem: ET.Element, groups: tuple[str, ...]) -> Box | None:
    x = _float(elem.get("x"))
    y = _float(elem.get("y"))
    size = _float(elem.get("font-size")) or 16
    if x is None or y is None:
        return None
    lines = _text_lines(elem)
    if not lines:
        return None
    max_size = _max_text_size(elem, size)
    width = max(cjk_text_width(line, size) for line in lines)
    line_height = _float(elem.get("data-paragraph-line-height")) or max_size * 1.22
    height = line_height * (len(lines) - 1) + max_size
    # Approximate the visible glyph box around the baseline. This intentionally
    # favors PPT export behavior where CJK/rich text often renders lower than a
    # browser's raw SVG bbox.
    y1 = y - max_size * 0.76
    y2 = y1 + height
    anchor = elem.get("text-anchor", "start")
    if anchor == "middle":
        x1, x2 = x - width / 2, x + width / 2
    elif anchor == "end":
        x1, x2 = x - width, x
    else:
        x1, x2 = x, x + width
    label = elem.get("data-text-region-id") or elem.get("id") or lines[0][:32]
    return Box("text", label, x1, y1, x2, y2, groups, baseline_y=y, max_font_size=max_size)


def _group_icon_box(elem: ET.Element, label: str, groups: tuple[str, ...]) -> Box | None:
    attr = _bbox_attr(elem.get("data-icon-bbox") or elem.get("data-bbox"))
    if attr:
        return Box("icon", label, *attr, groups)
    boxes: list[tuple[float, float, float, float]] = []
    for child in elem.iter():
        tag = _strip_ns(child.tag)
        bbox = _circle_bbox(child) if tag == "circle" else _rect_bbox(child) if tag == "rect" else None
        if bbox:
            boxes.append(bbox)
    if not boxes:
        return None
    return Box(
        "icon",
        label,
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
        groups,
    )


def _container_role(elem: ET.Element, bbox: tuple[float, float, float, float]) -> str | None:
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    fill = (elem.get("fill") or "").strip().lower()
    stroke = (elem.get("stroke") or "").strip().lower()
    if fill in {"", "none", "transparent"}:
        return None
    # Wide framed top strips.
    if y1 < 180 and 44 <= h <= 90 and w >= 120 and stroke not in {"", "none"}:
        return "top_band"
    # Navy pills / card headers / timeline labels.
    if 24 <= h <= 44 and 80 <= w <= 420 and fill not in {"#ffffff", "#fff", "#fbfaf6"}:
        return "horizontal_label"
    return None


def _collect(root: ET.Element) -> tuple[list[Container], list[Box]]:
    containers: list[Container] = []
    boxes: list[Box] = []

    def visit(elem: ET.Element, groups: tuple[str, ...]) -> None:
        tag = _strip_ns(elem.tag)
        elem_id = elem.get("id")
        next_groups = groups + ((elem_id,) if elem_id else ())
        if tag == "rect":
            bbox = _rect_bbox(elem)
            if bbox:
                role = _container_role(elem, bbox)
                if role:
                    containers.append(Container(elem_id or f"rect@{bbox[0]:.0f},{bbox[1]:.0f}", role, *bbox, next_groups))
        elif tag == "text":
            box = _text_box(elem, groups)
            if box:
                boxes.append(box)
        elif tag == "g" and elem.get("data-icon-id"):
            box = _group_icon_box(elem, elem.get("data-icon-id") or "icon", next_groups)
            if box:
                boxes.append(box)
        for child in list(elem):
            visit(child, next_groups)

    visit(root, ())
    return containers, boxes


def _inside(box: Box, container: Container, *, tolerance: float = 1.0) -> bool:
    return (
        container.x1 - tolerance <= box.cx <= container.x2 + tolerance
        and container.y1 - tolerance <= box.cy <= container.y2 + tolerance
    )


def _alignment_tolerance(container: Container, box: Box) -> float:
    if container.role == "top_band":
        return 6.0 if box.kind == "text" else 5.0
    return 4.5


def _alignment_clusters(container: Container, members: list[Box]) -> list[list[Box]]:
    if container.role != "top_band":
        return [members]
    clusters: list[list[Box]] = []
    current: list[Box] = []
    last_x2: float | None = None
    for box in sorted(members, key=lambda item: item.x1):
        if last_x2 is None or box.x1 - last_x2 <= 80:
            current.append(box)
        else:
            if current:
                clusters.append(current)
            current = [box]
        last_x2 = max(last_x2 if last_x2 is not None else box.x2, box.x2)
    if current:
        clusters.append(current)
    return clusters


def inspect(svg_path: Path) -> dict[str, Any]:
    root = ET.parse(svg_path).getroot()
    containers, boxes = _collect(root)
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0
    for container in containers:
        members = [box for box in boxes if _inside(box, container)]
        if not members:
            continue
        checked += len(members)
        for box in members:
            delta = box.cy - container.cy
            tolerance = _alignment_tolerance(container, box)
            if abs(delta) > tolerance:
                errors.append(
                    f"{box.label}: {box.kind} visual center is {delta:+.1f}px from "
                    f"{container.role} `{container.label}` centerline (tolerance {tolerance:.1f}px)"
                )
            if (
                container.role == "top_band"
                and box.kind == "text"
                and box.baseline_y is not None
                and (box.max_font_size or 0) >= 30
            ):
                baseline_delta = box.baseline_y - container.cy
                max_baseline_delta = 5.0
                if baseline_delta > max_baseline_delta:
                    errors.append(
                        f"{box.label}: rich title baseline is {baseline_delta:+.1f}px below "
                        f"{container.role} `{container.label}` centerline; expected <= +{max_baseline_delta:.1f}px"
                    )
            bottom_pad = container.y2 - box.y2
            if container.role == "top_band":
                min_bottom = 8.0 if box.kind == "text" else 6.0
            else:
                # Short pills/card headers are often only 28-36px tall; centerline
                # alignment is the main quality signal, with a small hard edge
                # guard to prevent visible clipping.
                min_bottom = 1.0 if box.kind == "text" else 4.0
            if bottom_pad < min_bottom:
                errors.append(
                    f"{box.label}: {box.kind} bottom padding inside {container.role} "
                    f"`{container.label}` is {bottom_pad:.1f}px; expected >= {min_bottom:.1f}px"
                )
        for cluster in _alignment_clusters(container, members):
            if len(cluster) < 2:
                continue
            centers = [box.cy for box in cluster]
            spread = max(centers) - min(centers)
            max_spread = 8.0 if container.role == "top_band" else 6.0
            if spread > max_spread:
                labels = ", ".join(box.label for box in cluster[:5])
                errors.append(
                    f"{container.label}: member centerlines differ by {spread:.1f}px "
                    f"(max {max_spread:.1f}px): {labels}"
                )
    return {
        "path": str(svg_path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "containers": len(containers),
            "aligned_members_checked": checked,
        },
    }


def _find_svgs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() == ".svg":
        return [target]
    if (target / "svg_output").is_dir():
        return sorted((target / "svg_output").glob("*.svg"))
    if (target / "svg_final").is_dir():
        return sorted((target / "svg_final").glob("*.svg"))
    return sorted(target.glob("*.svg"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SVG visual alignment rules.")
    parser.add_argument("target", type=Path, help="Project directory or SVG file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    svgs = _find_svgs(args.target)
    if not svgs:
        print(json.dumps({"valid": False, "errors": ["No SVG files found"], "results": []}, ensure_ascii=False, indent=2))
        return 1
    results = [inspect(svg) for svg in svgs]
    payload = {
        "valid": all(result["valid"] for result in results),
        "count": len(results),
        "errors": [error for result in results for error in result.get("errors", [])],
        "warnings": [warning for result in results for warning in result.get("warnings", [])],
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
