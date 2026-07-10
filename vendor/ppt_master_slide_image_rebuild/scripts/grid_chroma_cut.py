#!/usr/bin/env python3
"""Cut CxR/NxN icon contact sheets with adaptive per-cell chroma key.

This is an opt-in asset helper, not part of the default strict runner. It uses
foreground-content centers to infer grid cell edges instead of slicing from
(0,0) by image_width / columns.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _cluster_1d(values: list[int], k: int) -> list[float]:
    if k <= 0:
        return []
    if not values:
        return [(i + 0.5) / k for i in range(k)]
    lo, hi = min(values), max(values)
    if lo == hi:
        return [float(lo) for _ in range(k)]
    centers = [lo + (hi - lo) * (i + 0.5) / k for i in range(k)]
    for _ in range(24):
        groups = [[] for _ in range(k)]
        for value in values:
            idx = min(range(k), key=lambda i: abs(value - centers[i]))
            groups[idx].append(value)
        next_centers = [
            sum(group) / len(group) if group else centers[i]
            for i, group in enumerate(groups)
        ]
        if max(abs(a - b) for a, b in zip(centers, next_centers, strict=True)) < 0.05:
            break
        centers = next_centers
    return sorted(centers)


def _edges_from_centers(centers: list[float], limit: int) -> list[int]:
    if not centers:
        return [0, limit]
    if len(centers) == 1:
        span = limit
        return [0, span]
    gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    typical_gap = _median(gaps)
    edges = [centers[0] - typical_gap / 2]
    edges.extend((centers[i] + centers[i + 1]) / 2 for i in range(len(centers) - 1))
    edges.append(centers[-1] + typical_gap / 2)
    out = [max(0, min(limit, int(round(value)))) for value in edges]
    out[0] = max(0, out[0])
    out[-1] = min(limit, out[-1])
    for i in range(1, len(out)):
        if out[i] <= out[i - 1]:
            out[i] = min(limit, out[i - 1] + 1)
    return out


def _edge_samples(rgb: Image.Image) -> list[tuple[int, int, int]]:
    pix = rgb.load()
    samples: list[tuple[int, int, int]] = []
    w, h = rgb.size
    for x in range(w):
        samples.append(pix[x, 0])
        samples.append(pix[x, h - 1])
    for y in range(h):
        samples.append(pix[0, y])
        samples.append(pix[w - 1, y])
    return samples


def _background_color(samples: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    return tuple(int(round(_median([sample[i] for sample in samples]))) for i in range(3))  # type: ignore[return-value]


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _foreground_mask(image: Image.Image, *, threshold: float | None = None) -> list[tuple[int, int]]:
    rgb = image.convert("RGB")
    bg = _background_color(_edge_samples(rgb))
    samples = _edge_samples(rgb)
    edge_distances = [_distance(sample, bg) for sample in samples]
    cutoff = threshold if threshold is not None else max(18.0, _median(edge_distances) + 18.0)
    pix = rgb.load()
    points: list[tuple[int, int]] = []
    for y in range(rgb.height):
        for x in range(rgb.width):
            if _distance(pix[x, y], bg) > cutoff:
                points.append((x, y))
    return points


def _transparent_cell(cell: Image.Image, *, threshold: float | None = None) -> Image.Image:
    rgb = cell.convert("RGB")
    rgba = cell.convert("RGBA")
    bg = _background_color(_edge_samples(rgb))
    edge_distances = [_distance(sample, bg) for sample in _edge_samples(rgb)]
    cutoff = threshold if threshold is not None else max(18.0, _median(edge_distances) + 18.0)
    pix_rgb = rgb.load()
    pix_rgba = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            if _distance(pix_rgb[x, y], bg) <= cutoff:
                r, g, b, _a = pix_rgba[x, y]
                pix_rgba[x, y] = (r, g, b, 0)
    return rgba


def cut_sheet(
    image_path: Path,
    *,
    rows: int,
    columns: int,
    out_dir: Path,
    prefix: str = "icon",
    threshold: float | None = None,
) -> dict[str, Any]:
    if rows <= 0 or columns <= 0:
        raise ValueError("rows and columns must be positive")
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as image:
        source = image.convert("RGBA")
    points = _foreground_mask(source, threshold=threshold)
    xs = [x for x, _y in points]
    ys = [y for _x, y in points]
    col_centers = _cluster_1d(xs, columns)
    row_centers = _cluster_1d(ys, rows)
    x_edges = _edges_from_centers(col_centers, source.width)
    y_edges = _edges_from_centers(row_centers, source.height)

    assets: list[dict[str, Any]] = []
    for row in range(rows):
        for col in range(columns):
            box = (x_edges[col], y_edges[row], x_edges[col + 1], y_edges[row + 1])
            cell = source.crop(box)
            transparent = _transparent_cell(cell, threshold=threshold)
            name = f"{prefix}_{row + 1:02d}_{col + 1:02d}.png"
            out_path = out_dir / name
            transparent.save(out_path)
            assets.append({
                "id": f"{prefix}_{row + 1:02d}_{col + 1:02d}",
                "row": row,
                "column": col,
                "source_box": list(box),
                "path": str(out_path),
            })

    manifest = {
        "workflow": "slide-image-rebuild",
        "tool": "grid_chroma_cut",
        "source": str(image_path),
        "rows": rows,
        "columns": columns,
        "row_centers": [round(value, 2) for value in row_centers],
        "column_centers": [round(value, 2) for value in col_centers],
        "x_edges": x_edges,
        "y_edges": y_edges,
        "assets": assets,
    }
    (out_dir / "grid_chroma_cut_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cut an icon grid/contact sheet into transparent PNG assets.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--columns", type=int, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="icon")
    parser.add_argument("--threshold", type=float, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = cut_sheet(
        args.image,
        rows=args.rows,
        columns=args.columns,
        out_dir=args.out_dir,
        prefix=args.prefix,
        threshold=args.threshold,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
