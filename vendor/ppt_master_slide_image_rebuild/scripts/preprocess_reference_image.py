#!/usr/bin/env python3
"""
PPT Master - Reference Image Preprocessor

Normalize a slide reference image before layout extraction (EXIF, optional trim,
optional sharpen, optional downscale). Keeps the original file unchanged.

Usage:
    python3 scripts/preprocess_reference_image.py <input_image> --project <project_path>
    python3 scripts/preprocess_reference_image.py <input_image> --out normalized.png --meta meta.json

Examples:
    python3 scripts/preprocess_reference_image.py projects/demo/images/reference_layout.png --project projects/demo
    python3 scripts/preprocess_reference_image.py ref.png --out work/normalized.png --meta work/source_meta.json --trim

Dependencies:
    Pillow
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class PreprocessOptions:
    trim_whitespace: bool = False
    sharpen: bool = False
    max_width_px: int = 2400


@dataclass(frozen=True)
class PreprocessResult:
    source_path: Path
    normalized_path: Path
    meta_path: Path
    meta: dict[str, Any]


def trim_whitespace(img: Image.Image, threshold: int = 248) -> Image.Image:
    gray = ImageOps.grayscale(img.convert("RGB"))
    mask = gray.point(lambda pixel: 255 if pixel < threshold else 0)
    bbox = mask.getbbox()
    if not bbox:
        return img
    pad = 8
    left, top, right, bottom = bbox
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img.width, right + pad)
    bottom = min(img.height, bottom + pad)
    return img.crop((left, top, right, bottom))


def preprocess_reference_image(
    input_path: Path,
    *,
    out_path: Path,
    meta_path: Path,
    options: PreprocessOptions | None = None,
) -> PreprocessResult:
    opts = options or PreprocessOptions()
    img = Image.open(input_path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    original_size = img.size

    if opts.trim_whitespace:
        img = trim_whitespace(img)

    if opts.max_width_px and img.width > opts.max_width_px:
        scale = opts.max_width_px / img.width
        new_size = (opts.max_width_px, round(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    if opts.sharpen:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=3))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)

    meta: dict[str, Any] = {
        "source": str(input_path),
        "normalized": str(out_path),
        "original_width": original_size[0],
        "original_height": original_size[1],
        "width": img.width,
        "height": img.height,
        "aspect_ratio": round(img.width / img.height, 6),
        "preprocess": {
            "trim_whitespace": opts.trim_whitespace,
            "sharpen": opts.sharpen,
            "max_width_px": opts.max_width_px,
        },
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return PreprocessResult(
        source_path=input_path,
        normalized_path=out_path,
        meta_path=meta_path,
        meta=meta,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preprocess a reference image for slide-image-rebuild intake.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Source reference image")
    parser.add_argument("--project", type=Path, help="Project directory (sets default out/meta paths)")
    parser.add_argument(
        "--out",
        type=Path,
        help="Normalized PNG path (default: <project>/images/reference_layout.normalized.png)",
    )
    parser.add_argument(
        "--meta",
        type=Path,
        help="Metadata JSON path (default: <project>/images/source_meta.json)",
    )
    parser.add_argument("--trim", action="store_true", help="Trim near-white outer margins")
    parser.add_argument("--sharpen", action="store_true", help="Apply mild unsharp mask")
    parser.add_argument("--max-width", type=int, default=2400, help="Downscale width cap in pixels")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    input_path = args.input.resolve()
    if not input_path.is_file():
        raise SystemExit(f"File not found: {input_path}")

    if args.out:
        out_path = args.out.resolve()
    elif args.project:
        out_path = args.project.resolve() / "images" / "reference_layout.normalized.png"
    else:
        out_path = input_path.with_suffix(".normalized.png")

    if args.meta:
        meta_path = args.meta.resolve()
    elif args.project:
        meta_path = args.project.resolve() / "images" / "source_meta.json"
    else:
        meta_path = input_path.with_suffix(".source_meta.json")

    result = preprocess_reference_image(
        input_path,
        out_path=out_path,
        meta_path=meta_path,
        options=PreprocessOptions(
            trim_whitespace=args.trim,
            sharpen=args.sharpen,
            max_width_px=args.max_width,
        ),
    )
    print(json.dumps(result.meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
