#!/usr/bin/env python3
"""Verify conservative SVG layer-order hazards.

The first rule catches the practical failure mode from image-to-PPT rebuilds:
a large filled container/card is authored after an icon or text object and can
cover it after SVG/PPTX conversion. The check is conservative and ignores
stroke-only frames, tiny shapes, and marked-safe overlays.
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
class LayerItem:
    order: int
    kind: str
    label: str
    bbox: tuple[float, float, float, float]
    tag: str

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bbox
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _numbers_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    nums = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", raw)]
    if len(nums) < 4:
        return None
    xs = nums[0::2]
    ys = nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


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


def _bbox_attr(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    nums = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", raw)]
    if len(nums) < 4:
        return None
    x, y, w, h = nums[:4]
    return x, y, x + w, y + h


def _group_bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    boxes: list[tuple[float, float, float, float]] = []
    attr_bbox = _bbox_attr(elem.get("data-icon-bbox") or elem.get("data-bbox"))
    if attr_bbox:
        boxes.append(attr_bbox)
    for child in elem.iter():
        tag = _strip_ns(child.tag)
        bbox = None
        if tag == "rect":
            bbox = _rect_bbox(child)
        elif tag == "circle":
            bbox = _circle_bbox(child)
        elif tag in {"polygon", "polyline", "path"}:
            bbox = _numbers_bbox(child.get("points") or child.get("d"))
        if bbox:
            boxes.append(bbox)
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _text_bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    x = _float(elem.get("x"))
    y = _float(elem.get("y"))
    size = _float(elem.get("font-size")) or 16
    if x is None or y is None:
        return None
    tspans = [child for child in list(elem) if _strip_ns(child.tag) == "tspan"]
    block_tspans = [child for child in tspans if child.get("x") is not None or child.get("dy") is not None]
    if block_tspans:
        lines = ["".join(child.itertext()).strip() for child in block_tspans]
        lines = [line for line in lines if line]
    else:
        lines = ["".join(elem.itertext()).strip()]
    if not lines:
        return None
    width = max(cjk_text_width(line, size) for line in lines)
    line_height = _float(elem.get("data-paragraph-line-height")) or size * 1.3
    height = line_height * (len(lines) - 1) + size * 1.3
    anchor = elem.get("text-anchor", "start")
    if anchor == "middle":
        x1, x2 = x - width / 2, x + width / 2
    elif anchor == "end":
        x1, x2 = x - width, x
    else:
        x1, x2 = x, x + width
    return x1, y - size, x2, y + height - size


def _opacity(elem: ET.Element) -> float:
    for attr in ("opacity", "fill-opacity"):
        value = _float(elem.get(attr))
        if value is not None:
            return max(0.0, min(1.0, value))
    return 1.0


def _filled_cover_candidate(elem: ET.Element) -> bool:
    if elem.get("data-layer-ok") == "overlay":
        return False
    tag = _strip_ns(elem.tag)
    if tag not in {"rect", "polygon", "path"}:
        return False
    fill = (elem.get("fill") or "").strip().lower()
    if fill in {"", "none", "transparent"} or fill.startswith("url("):
        return False
    if _opacity(elem) < 0.2:
        return False
    bbox = _rect_bbox(elem) if tag == "rect" else _numbers_bbox(elem.get("points") or elem.get("d"))
    if not bbox:
        return False
    x1, y1, x2, y2 = bbox
    return (x2 - x1) >= 60 and (y2 - y1) >= 24


def _overlap_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _find_svgs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() == ".svg":
        return [target]
    if (target / "svg_output").is_dir():
        return sorted((target / "svg_output").glob("*.svg"))
    if (target / "svg_final").is_dir():
        return sorted((target / "svg_final").glob("*.svg"))
    return sorted(target.glob("*.svg"))


def _collect_items(root: ET.Element) -> list[LayerItem]:
    items: list[LayerItem] = []
    order = 0

    def visit(elem: ET.Element) -> None:
        nonlocal order
        tag = _strip_ns(elem.tag)
        current = order
        order += 1
        label = elem.get("id") or elem.get("data-icon-id") or elem.get("data-text-region-id") or tag
        if tag == "text":
            bbox = _text_bbox(elem)
            if bbox:
                items.append(LayerItem(current, "text", label, bbox, tag))
        elif tag == "g" and elem.get("data-icon-id"):
            bbox = _group_bbox(elem)
            if bbox:
                items.append(LayerItem(current, "icon", label, bbox, tag))
        elif _filled_cover_candidate(elem):
            bbox = _rect_bbox(elem) if tag == "rect" else _numbers_bbox(elem.get("points") or elem.get("d"))
            if bbox:
                items.append(LayerItem(current, "cover", label, bbox, tag))
        for child in list(elem):
            visit(child)

    visit(root)
    return items


def inspect(svg_path: Path) -> dict[str, Any]:
    root = ET.parse(svg_path).getroot()
    items = _collect_items(root)
    foreground = [item for item in items if item.kind in {"text", "icon"}]
    covers = [item for item in items if item.kind == "cover"]
    errors: list[str] = []
    for cover in covers:
        for item in foreground:
            if cover.order <= item.order:
                continue
            overlap = _overlap_area(cover.bbox, item.bbox)
            if overlap <= 0:
                continue
            ratio = overlap / max(item.area, 1.0)
            if ratio >= 0.35:
                errors.append(
                    f"{cover.label}: filled {cover.tag} is after {item.kind} `{item.label}` "
                    f"and overlaps {ratio:.0%} of its bbox"
                )
    return {
        "path": str(svg_path),
        "valid": not errors,
        "errors": errors,
        "warnings": [],
        "items": {
            "covers": len(covers),
            "texts": sum(1 for item in foreground if item.kind == "text"),
            "icons": sum(1 for item in foreground if item.kind == "icon"),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SVG layer order for hidden text/icon hazards.")
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
        "warnings": [],
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
