#!/usr/bin/env python3
"""Compare a rendered dual-image rebuild slide against the full reference image."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat


DEFAULT_REGIONS = {
    "all": [0, 0, 1280, 720],
    "top_five_stage": [170, 45, 1085, 225],
    "left_source": [0, 0, 170, 315],
    "right_user": [1090, 0, 1280, 320],
    "chain": [170, 240, 1080, 465],
    "product": [165, 470, 1065, 565],
    "bottom_services": [410, 585, 1080, 710],
    "right_trust": [1080, 320, 1275, 710],
}


def _mse_similarity(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    stat = ImageStat.Stat(diff)
    mse = sum(value * value for value in stat.rms) / (3 * 255 * 255)
    return max(0.0, 1.0 - math.sqrt(mse))


def _load_regions(path: Path | None) -> dict[str, list[int]]:
    if path is None:
        return DEFAULT_REGIONS
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("regions JSON must be an object.")
    regions: dict[str, list[int]] = {}
    for name, bbox in data.items():
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"region {name} must be [x1,y1,x2,y2].")
        regions[str(name)] = [int(value) for value in bbox]
    return regions


def _compare_region(reference: Image.Image, render: Image.Image, bbox: list[int]) -> dict[str, float]:
    ref_crop = reference.crop(tuple(bbox))
    render_crop = render.crop(tuple(bbox))
    ref_perceptual = ref_crop.resize((max(1, ref_crop.width // 4), max(1, ref_crop.height // 4))).filter(
        ImageFilter.GaussianBlur(3)
    )
    render_perceptual = render_crop.resize(
        (max(1, render_crop.width // 4), max(1, render_crop.height // 4))
    ).filter(ImageFilter.GaussianBlur(3))
    return {
        "pixel_similarity": round(_mse_similarity(ref_crop, render_crop) * 100.0, 3),
        "perceptual_similarity": round(_mse_similarity(ref_perceptual, render_perceptual) * 100.0, 3),
    }


def _write_crop_sheet(reference: Image.Image, render: Image.Image, regions: dict[str, list[int]], output: Path) -> None:
    rows: list[Image.Image] = []
    font = ImageFont.load_default()
    for name, bbox in regions.items():
        if name == "all":
            continue
        ref_crop = reference.crop(tuple(bbox))
        render_crop = render.crop(tuple(bbox))
        width, height = ref_crop.size
        row = Image.new("RGB", (width * 2 + 18, height + 26), "white")
        draw = ImageDraw.Draw(row)
        draw.text((0, 0), f"{name} | full reference", fill="black", font=font)
        draw.text((width + 18, 0), f"{name} | rendered output", fill="black", font=font)
        row.paste(ref_crop, (0, 26))
        row.paste(render_crop, (width + 18, 26))
        rows.append(row)
    if not rows:
        return
    sheet_width = max(row.width for row in rows)
    sheet_height = sum(row.height + 14 for row in rows) - 14
    sheet = Image.new("RGB", (sheet_width, sheet_height), "white")
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height + 14
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def build_report(
    reference_path: Path,
    render_path: Path,
    *,
    regions_path: Path | None = None,
    crops_output: Path | None = None,
) -> dict[str, Any]:
    reference = Image.open(reference_path).convert("RGB").resize((1280, 720))
    render = Image.open(render_path).convert("RGB").resize((1280, 720))
    regions = _load_regions(regions_path)
    region_scores = {
        name: {"bbox": bbox, **_compare_region(reference, render, bbox)}
        for name, bbox in regions.items()
    }
    if crops_output is not None:
        _write_crop_sheet(reference, render, regions, crops_output)
    return {
        "reference": str(reference_path),
        "render": str(render_path),
        "canvas": {"width": 1280, "height": 720},
        "metric_note": (
            "pixel_similarity is full-resolution MSE-based and is sensitive to font antialiasing; "
            "perceptual_similarity downsamples and blurs to score layout-level resemblance."
        ),
        "regions": region_scores,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a visual similarity report for dual-image rebuild output.")
    parser.add_argument("--reference", required=True, type=Path, help="Full text-bearing reference image.")
    parser.add_argument("--render", required=True, type=Path, help="Rendered PPTX screenshot.")
    parser.add_argument("--regions", type=Path, help="Optional JSON region map.")
    parser.add_argument("--output", required=True, type=Path, help="Output report JSON.")
    parser.add_argument("--crops-output", type=Path, help="Optional side-by-side crop sheet image.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        args.reference,
        args.render,
        regions_path=args.regions,
        crops_output=args.crops_output,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
