#!/usr/bin/env python3
"""Verify coarse vertical composition balance for rebuilt SVG pages."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


SVG_NS = "{http://www.w3.org/2000/svg}"


@dataclass(frozen=True)
class RectBox:
    label: str
    x: float
    y: float
    w: float
    h: float

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def area(self) -> float:
        return self.w * self.h


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(raw: str | None) -> float | None:
    if raw is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", raw)
    return float(match.group(1)) if match else None


def _canvas_size(root: ET.Element) -> tuple[float, float]:
    width = _float(root.get("width"))
    height = _float(root.get("height"))
    if width is not None and height is not None:
        return width, height
    viewbox = [_float(value) for value in (root.get("viewBox") or "").split()]
    if len(viewbox) == 4 and viewbox[2] is not None and viewbox[3] is not None:
        return viewbox[2], viewbox[3]
    return 1280.0, 720.0


def _rect_box(elem: ET.Element, label: str) -> RectBox | None:
    x = _float(elem.get("x"))
    y = _float(elem.get("y"))
    w = _float(elem.get("width"))
    h = _float(elem.get("height"))
    if x is None or y is None or w is None or h is None:
        return None
    return RectBox(label, x, y, w, h)


def _card_boxes(root: ET.Element) -> list[RectBox]:
    cards: list[RectBox] = []
    for group in root.iter():
        if _strip_ns(group.tag) != "g":
            continue
        if group.get("data-primitive") != "target_goal_card":
            continue
        rects = [
            box
            for child in group.iter()
            if _strip_ns(child.tag) == "rect"
            if (box := _rect_box(child, group.get("data-zone-id") or "target_goal_card")) is not None
        ]
        if rects:
            cards.append(max(rects, key=lambda item: item.area))
    return cards


def inspect(svg_path: Path) -> dict[str, Any]:
    root = ET.parse(svg_path).getroot()
    _width, height = _canvas_size(root)
    cards = _card_boxes(root)
    errors: list[str] = []
    warnings: list[str] = []

    if len(cards) < 2:
        warnings.append("composition balance skipped: fewer than 2 target_goal_card groups")
        return {
            "path": str(svg_path),
            "valid": True,
            "errors": errors,
            "warnings": warnings,
            "metrics": {"target_goal_cards": len(cards)},
        }

    bottom = max(card.bottom for card in cards)
    bottom_margin = height - bottom
    min_bottom_margin = height * 0.04
    max_bottom_margin = height * 0.08
    if bottom_margin > max_bottom_margin:
        errors.append(
            f"main content ends too high: bottom margin is {bottom_margin:.1f}px "
            f"({bottom_margin / height:.1%}); expected <= {max_bottom_margin:.1f}px"
        )
    if bottom_margin < min_bottom_margin:
        errors.append(
            f"main content is too low: bottom margin is {bottom_margin:.1f}px "
            f"({bottom_margin / height:.1%}); expected >= {min_bottom_margin:.1f}px"
        )

    top_spread = max(card.y for card in cards) - min(card.y for card in cards)
    if top_spread > 4:
        errors.append(f"goal card top edges differ by {top_spread:.1f}px; expected <= 4.0px")

    return {
        "path": str(svg_path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "target_goal_cards": len(cards),
            "main_content_bottom_px": bottom,
            "bottom_margin_px": bottom_margin,
            "max_bottom_margin_px": max_bottom_margin,
            "min_bottom_margin_px": min_bottom_margin,
            "card_top_spread_px": top_spread,
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
    parser = argparse.ArgumentParser(description="Verify SVG vertical composition balance.")
    parser.add_argument("target", type=Path, help="Project directory or SVG file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    svgs = _find_svgs(args.target)
    if not svgs:
        payload = {"valid": False, "errors": ["No SVG files found"], "results": []}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
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
