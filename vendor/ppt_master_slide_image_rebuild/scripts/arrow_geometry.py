#!/usr/bin/env python3
"""
PPT Master - Arrow Geometry Helpers

Compute stable point-to-point and box-to-box arrow geometry for SVG pages that
will later be converted to editable PowerPoint shapes.

Usage:
    python3 scripts/arrow_geometry.py point <x0> <y0> <x1> <y1> [options]
    python3 scripts/arrow_geometry.py box <x0> <y0> <w0> <h0> <x1> <y1> <w1> <h1> [options]
    python3 scripts/arrow_geometry.py demo -o /tmp/arrow_demo.svg

Examples:
    python3 scripts/arrow_geometry.py box 80 160 240 120 520 220 240 120 --pad-end 18
    python3 scripts/arrow_geometry.py demo -o /tmp/arrow_demo.svg

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
from typing import Any


Point = tuple[float, float]
Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class ArrowOptions:
    """Tuning options for arrow geometry."""

    bow: float = 0.0
    stretch: float = 0.5
    stretch_min: float = 0.0
    stretch_max: float = 420.0
    pad_start: float = 0.0
    pad_end: float = 0.0
    flip: bool = False
    straights: bool = True


@dataclass(frozen=True)
class ArrowGeometry:
    """Computed arrow points and tangent angles."""

    start: Point
    control: Point
    end: Point
    end_angle: float
    start_angle: float
    center_angle: float

    def as_flat_tuple(self) -> tuple[float, float, float, float, float, float, float, float, float]:
        sx, sy = self.start
        cx, cy = self.control
        ex, ey = self.end
        return sx, sy, cx, cy, ex, ey, self.end_angle, self.start_angle, self.center_angle

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["flat"] = list(self.as_flat_tuple())
        payload["end_angle_degrees"] = math.degrees(self.end_angle)
        payload["start_angle_degrees"] = math.degrees(self.start_angle)
        payload["center_angle_degrees"] = math.degrees(self.center_angle)
        return payload


def _distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _unit(a: Point, b: Point) -> Point:
    dist = _distance(a, b)
    if dist <= 1e-9:
        return 1.0, 0.0
    return (b[0] - a[0]) / dist, (b[1] - a[1]) / dist


def _pad_points(start: Point, end: Point, options: ArrowOptions) -> tuple[Point, Point]:
    ux, uy = _unit(start, end)
    sx = start[0] + ux * options.pad_start
    sy = start[1] + uy * options.pad_start
    ex = end[0] - ux * options.pad_end
    ey = end[1] - uy * options.pad_end
    if _distance((sx, sy), (ex, ey)) < 1:
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        return mid, mid
    return (sx, sy), (ex, ey)


def _stretch_factor(length: float, options: ArrowOptions) -> float:
    span = max(1.0, options.stretch_max - options.stretch_min)
    raw = (length - options.stretch_min) / span
    return max(0.0, min(1.0, raw)) * max(0.0, options.stretch)


def get_arrow(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    options: ArrowOptions | None = None,
) -> ArrowGeometry:
    """Return quadratic arrow geometry between two points."""
    resolved = options or ArrowOptions()
    start, end = _pad_points((x0, y0), (x1, y1), resolved)
    length = _distance(start, end)
    ux, uy = _unit(start, end)
    mx = (start[0] + end[0]) / 2
    my = (start[1] + end[1]) / 2

    bend = 0.0
    if abs(resolved.bow) > 1e-9 and (not resolved.straights or length > 1):
        bend = resolved.bow * length * (1.0 - _stretch_factor(length, resolved) * 0.65)
        if resolved.flip:
            bend *= -1
    cx = mx - uy * bend
    cy = my + ux * bend

    start_angle = math.atan2(cy - start[1], cx - start[0])
    end_angle = math.atan2(end[1] - cy, end[0] - cx)
    center_angle = math.atan2(end[1] - start[1], end[0] - start[0])
    return ArrowGeometry(
        start=start,
        control=(cx, cy),
        end=end,
        end_angle=end_angle,
        start_angle=start_angle,
        center_angle=center_angle,
    )


def _box_edge_point(box: Box, toward: Point) -> Point:
    x, y, w, h = box
    cx = x + w / 2
    cy = y + h / 2
    dx = toward[0] - cx
    dy = toward[1] - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return cx, cy
    sx = (w / 2) / abs(dx) if abs(dx) > 1e-9 else float("inf")
    sy = (h / 2) / abs(dy) if abs(dy) > 1e-9 else float("inf")
    scale = min(sx, sy)
    return cx + dx * scale, cy + dy * scale


def get_box_to_box_arrow(
    x0: float,
    y0: float,
    w0: float,
    h0: float,
    x1: float,
    y1: float,
    w1: float,
    h1: float,
    options: ArrowOptions | None = None,
) -> ArrowGeometry:
    """Return quadratic arrow geometry between two rectangle edges."""
    box0 = (x0, y0, w0, h0)
    box1 = (x1, y1, w1, h1)
    center0 = (x0 + w0 / 2, y0 + h0 / 2)
    center1 = (x1 + w1 / 2, y1 + h1 / 2)
    start = _box_edge_point(box0, center1)
    end = _box_edge_point(box1, center0)
    return get_arrow(start[0], start[1], end[0], end[1], options)


def quadratic_path(geometry: ArrowGeometry, *, precision: int = 2) -> str:
    """Return an SVG quadratic path string."""
    sx, sy = geometry.start
    cx, cy = geometry.control
    ex, ey = geometry.end
    return (
        f"M{sx:.{precision}f},{sy:.{precision}f} "
        f"Q{cx:.{precision}f},{cy:.{precision}f} {ex:.{precision}f},{ey:.{precision}f}"
    )


def arrowhead_polygon(
    tip: Point,
    angle: float,
    *,
    length: float = 18.0,
    width: float = 14.0,
    precision: int = 2,
) -> str:
    """Return SVG polygon points for a triangular arrowhead."""
    ux = math.cos(angle)
    uy = math.sin(angle)
    nx = -uy
    ny = ux
    bx = tip[0] - ux * length
    by = tip[1] - uy * length
    points = [
        tip,
        (bx + nx * width / 2, by + ny * width / 2),
        (bx - nx * width / 2, by - ny * width / 2),
    ]
    return " ".join(f"{x:.{precision}f},{y:.{precision}f}" for x, y in points)


def block_arrow_polygon(
    start: Point,
    end: Point,
    *,
    shaft_width: float = 14.0,
    head_width: float = 30.0,
    head_length: float = 34.0,
    precision: int = 2,
) -> str:
    """Return a chunky straight block-arrow polygon from start to end."""
    length = _distance(start, end)
    if length <= 1e-9:
        x, y = start
        return f"{x:.{precision}f},{y:.{precision}f}"
    ux, uy = _unit(start, end)
    nx, ny = -uy, ux
    resolved_head = min(head_length, length * 0.55)
    neck = (end[0] - ux * resolved_head, end[1] - uy * resolved_head)
    shaft_half = min(shaft_width / 2, max(1.0, head_width / 2 - 1))
    head_half = max(head_width / 2, shaft_half + 1)
    points = [
        (start[0] + nx * shaft_half, start[1] + ny * shaft_half),
        (neck[0] + nx * shaft_half, neck[1] + ny * shaft_half),
        (neck[0] + nx * head_half, neck[1] + ny * head_half),
        end,
        (neck[0] - nx * head_half, neck[1] - ny * head_half),
        (neck[0] - nx * shaft_half, neck[1] - ny * shaft_half),
        (start[0] - nx * shaft_half, start[1] - ny * shaft_half),
    ]
    return " ".join(f"{x:.{precision}f},{y:.{precision}f}" for x, y in points)


def svg_path_arrow(
    geometry: ArrowGeometry,
    *,
    stroke: str = "#475569",
    stroke_width: float = 4.0,
    fill: str | None = None,
    connector_id: str | None = None,
) -> str:
    """Return PPTX-friendly SVG for a curved path plus separate arrowhead polygon."""
    resolved_fill = fill or stroke
    data = f' data-chain-connector="{escape(connector_id)}"' if connector_id else ""
    return "\n".join([
        (
            f'<path d="{quadratic_path(geometry)}" fill="none" stroke="{stroke}" '
            f'stroke-width="{stroke_width:g}" stroke-linecap="round"{data}/>'
        ),
        (
            f'<polygon points="{arrowhead_polygon(geometry.end, geometry.end_angle)}" '
            f'fill="{resolved_fill}"{data}/>'
        ),
    ])


def svg_block_arrow(
    start: Point,
    end: Point,
    *,
    fill: str = "#475569",
    connector_id: str | None = None,
) -> str:
    """Return PPTX-friendly SVG for a straight chunky block arrow."""
    data = f' data-chain-connector="{connector_id}"' if connector_id else ""
    return f'<polygon points="{block_arrow_polygon(start, end)}" fill="{fill}"{data}/>'


def _options_from_args(args: argparse.Namespace) -> ArrowOptions:
    return ArrowOptions(
        bow=args.bow,
        stretch=args.stretch,
        stretch_min=args.stretch_min,
        stretch_max=args.stretch_max,
        pad_start=args.pad_start,
        pad_end=args.pad_end,
        flip=args.flip,
        straights=not args.no_straights,
    )


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bow", type=float, default=0.0, help="Curvature amount; 0 is straight")
    parser.add_argument("--stretch", type=float, default=0.5, help="Length-based bow dampening")
    parser.add_argument("--stretch-min", type=float, default=0.0, help="Minimum distance for stretch")
    parser.add_argument("--stretch-max", type=float, default=420.0, help="Maximum distance for stretch")
    parser.add_argument("--pad-start", type=float, default=0.0, help="Pixels to trim from the start")
    parser.add_argument("--pad-end", type=float, default=0.0, help="Pixels to trim from the end")
    parser.add_argument("--flip", action="store_true", help="Flip curved arrow direction")
    parser.add_argument("--no-straights", action="store_true", help="Do not force straight behavior")


def _demo_svg() -> str:
    first = get_box_to_box_arrow(
        88, 170, 260, 120,
        512, 170, 260, 120,
        ArrowOptions(pad_start=10, pad_end=22),
    )
    second = get_box_to_box_arrow(
        512, 170, 260, 120,
        924, 360, 220, 120,
        ArrowOptions(bow=0.18, pad_start=10, pad_end=22),
    )
    block = block_arrow_polygon((238, 462), (520, 462), shaft_width=18, head_width=38, head_length=42)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect x="0" y="0" width="1280" height="720" fill="#f8fafc"/>
  <text x="80" y="96" font-family="Arial, sans-serif" font-size="38" font-weight="700" fill="#0f172a">Arrow Geometry Demo</text>
  <rect x="88" y="170" width="260" height="120" rx="18" fill="#dbeafe" stroke="#2563eb" stroke-width="3"/>
  <rect x="512" y="170" width="260" height="120" rx="18" fill="#dcfce7" stroke="#16a34a" stroke-width="3"/>
  <rect x="924" y="360" width="220" height="120" rx="18" fill="#fee2e2" stroke="#dc2626" stroke-width="3"/>
  <text x="128" y="242" font-family="Arial, sans-serif" font-size="26" fill="#1d4ed8">Start box</text>
  <text x="552" y="242" font-family="Arial, sans-serif" font-size="26" fill="#166534">Middle box</text>
  <text x="962" y="432" font-family="Arial, sans-serif" font-size="26" fill="#991b1b">End box</text>
  {svg_path_arrow(first, stroke="#475569", stroke_width=5, connector_id="start->middle")}
  {svg_path_arrow(second, stroke="#475569", stroke_width=5, connector_id="middle->end")}
  <text x="88" y="470" font-family="Arial, sans-serif" font-size="24" fill="#334155">Block arrow:</text>
  <polygon points="{block}" fill="#0f766e" data-chain-connector="block-demo"/>
</svg>
'''


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute PPTX-friendly SVG arrow geometry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    point = subparsers.add_parser("point", help="Compute a point-to-point arrow")
    point.add_argument("x0", type=float)
    point.add_argument("y0", type=float)
    point.add_argument("x1", type=float)
    point.add_argument("y1", type=float)
    _add_common_options(point)

    box = subparsers.add_parser("box", help="Compute a box-to-box arrow")
    box.add_argument("x0", type=float)
    box.add_argument("y0", type=float)
    box.add_argument("w0", type=float)
    box.add_argument("h0", type=float)
    box.add_argument("x1", type=float)
    box.add_argument("y1", type=float)
    box.add_argument("w1", type=float)
    box.add_argument("h1", type=float)
    _add_common_options(box)

    demo = subparsers.add_parser("demo", help="Write a demo SVG")
    demo.add_argument("-o", "--output", type=Path, required=True, help="Output SVG path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "point":
        geometry = get_arrow(args.x0, args.y0, args.x1, args.y1, _options_from_args(args))
        print(json.dumps(geometry.as_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "box":
        geometry = get_box_to_box_arrow(
            args.x0, args.y0, args.w0, args.h0,
            args.x1, args.y1, args.w1, args.h1,
            _options_from_args(args),
        )
        print(json.dumps(geometry.as_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "demo":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(_demo_svg(), encoding="utf-8")
        print(args.output)
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
