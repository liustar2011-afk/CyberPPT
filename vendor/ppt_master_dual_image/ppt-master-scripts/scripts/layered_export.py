#!/usr/bin/env python3
"""
PPT Master - Layered Export

Export A/B/C image result packages and locked-background/editable-text PPTX
from existing SVG text sources and provided clean background images.

Usage:
    python3 scripts/layered_export.py <project_path> --page 6 --background-image A.png --editable-text-pptx

Examples:
    python3 skills/ppt-master/scripts/layered_export.py projects/demo --page 6 \
        --background-image projects/demo/layers/page_006_A.png --three-images --editable-text-pptx

Dependencies:
    python-pptx, Pillow, svglib/reportlab or cairosvg for SVG PNG rendering
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from layered_pptx import create_editable_text_pptx, create_three_image_pptx  # noqa: E402
from svg_layers import make_background_svg, make_text_only_svg  # noqa: E402
from svg_to_pptx.pptx_media import convert_svg_to_png  # noqa: E402


@dataclass
class LayeredExportResult:
    assets_dir: Path
    background_pngs: list[Path]
    full_pngs: list[Path]
    text_pngs: list[Path]
    three_images_pptx: Path | None
    editable_text_pptx: Path | None


def _page_num_from_name(path: Path) -> int | None:
    match = re.search(r"(\d+)", path.stem)
    if not match:
        return None
    return int(match.group(1))


def _resolve_svg_files(project_path: Path, source: str, page: int | None, all_pages: bool) -> list[Path]:
    source_dir = project_path / source
    if not source_dir.is_dir():
        raise FileNotFoundError(f"SVG source directory not found: {source_dir}")
    files = sorted(source_dir.glob("*.svg"), key=lambda p: (_page_num_from_name(p) or 10**9, p.name))
    if page is not None:
        matched = [p for p in files if _page_num_from_name(p) == page]
        if not matched and 1 <= page <= len(files):
            matched = [files[page - 1]]
        if not matched:
            raise FileNotFoundError(f"No SVG page {page} in {source_dir}")
        return matched
    if all_pages:
        return files
    raise ValueError("Specify --page or --all")


def _pixel_size_from_svg(svg_text: str) -> tuple[int, int]:
    viewbox = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', svg_text)
    if viewbox:
        parts = [float(x) for x in re.split(r"[\s,]+", viewbox.group(1).strip()) if x]
        if len(parts) == 4:
            return int(round(parts[2])), int(round(parts[3]))
    width = re.search(r'width\s*=\s*["\'](\d+(?:\.\d+)?)', svg_text)
    height = re.search(r'height\s*=\s*["\'](\d+(?:\.\d+)?)', svg_text)
    if width and height:
        return int(float(width.group(1))), int(float(height.group(1)))
    return 1280, 720


def _render_svg_file(svg_path: Path, png_path: Path, pixel_size: tuple[int, int]) -> None:
    ok = convert_svg_to_png(svg_path, png_path, pixel_size[0], pixel_size[1])
    if not ok:
        raise RuntimeError(f"Failed to render SVG to PNG: {svg_path}")


def _render_svg_text(svg_text: str, base_svg_path: Path, png_path: Path, pixel_size: tuple[int, int]) -> None:
    tmp_svg = base_svg_path.parent / f".layered_{png_path.stem}.svg"
    tmp_svg.write_text(svg_text, encoding="utf-8")
    ok = convert_svg_to_png(tmp_svg, png_path, pixel_size[0], pixel_size[1])
    try:
        tmp_svg.unlink()
    except FileNotFoundError:
        pass
    if not ok:
        raise RuntimeError(f"Failed to render SVG layer to PNG: {tmp_svg}")


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def run_layered_export(
    project_path: Path,
    svg_files: list[Path],
    output_dir: Path,
    provided_backgrounds: dict[Path, Path] | None = None,
    make_three_images: bool = True,
    make_editable_text: bool = True,
    order: tuple[str, ...] = ("A", "B", "C"),
    derive_background: bool = False,
) -> LayeredExportResult:
    provided_backgrounds = provided_backgrounds or {}
    assets_dir = output_dir / "layered_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    background_pngs: list[Path] = []
    full_pngs: list[Path] = []
    text_pngs: list[Path] = []
    editable_pages: list[tuple[Path, str, str]] = []
    pixel_size: tuple[int, int] | None = None

    for index, svg_file in enumerate(svg_files, 1):
        svg_text = svg_file.read_text(encoding="utf-8")
        current_size = _pixel_size_from_svg(svg_text)
        pixel_size = pixel_size or current_size
        label = f"page_{index:03d}"
        stem = svg_file.stem

        full_png = assets_dir / f"{stem}_B_full.png"
        text_png = assets_dir / f"{stem}_C_text_only.png"
        text_svg = make_text_only_svg(svg_text)
        _render_svg_file(svg_file, full_png, current_size)
        _render_svg_text(text_svg, svg_file, text_png, current_size)

        background_png = provided_backgrounds.get(svg_file)
        if background_png is None:
            if not derive_background:
                raise ValueError(
                    f"Missing clean A background for {svg_file}. "
                    "Pass --background-image for single-page export, or --derive-background to create a fallback."
                )
            background_svg = make_background_svg(svg_text)
            background_png = assets_dir / f"{stem}_A_background.png"
            _render_svg_text(background_svg, svg_file, background_png, current_size)

        if _image_size(background_png) != current_size:
            # PowerPoint will scale the image to canvas, but the mismatch is
            # material enough to surface immediately.
            print(
                f"Warning: background image size {_image_size(background_png)} "
                f"differs from SVG canvas {current_size}: {background_png}",
                file=sys.stderr,
            )

        background_pngs.append(background_png)
        full_pngs.append(full_png)
        text_pngs.append(text_png)
        editable_pages.append((background_png, text_svg, label))

    assert pixel_size is not None

    three_images_pptx: Path | None = None
    if make_three_images:
        image_pages: list[tuple[Path, str]] = []
        layer_map = {"A": background_pngs, "B": full_pngs, "C": text_pngs}
        for page_index in range(len(svg_files)):
            for key in order:
                image_pages.append((layer_map[key][page_index], key))
        three_images_pptx = output_dir / f"{project_path.name}_three_images.pptx"
        create_three_image_pptx(image_pages, three_images_pptx, pixel_size)

    editable_text_pptx: Path | None = None
    if make_editable_text:
        editable_text_pptx = output_dir / f"{project_path.name}_image_locked_text_editable.pptx"
        create_editable_text_pptx(editable_pages, editable_text_pptx, pixel_size)

    return LayeredExportResult(
        assets_dir=assets_dir,
        background_pngs=background_pngs,
        full_pngs=full_pngs,
        text_pngs=text_pngs,
        three_images_pptx=three_images_pptx,
        editable_text_pptx=editable_text_pptx,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export A/B/C images and locked-background/editable-text PPTX.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--page", type=int, default=None, help="Page number to export")
    parser.add_argument("--all", action="store_true", help="Export all SVG pages")
    parser.add_argument("--source", default="svg_output", help="SVG source directory under project")
    parser.add_argument("--background-image", type=Path, help="Clean A background PNG for single-page export")
    parser.add_argument("--derive-background", action="store_true", help="Fallback: derive A by removing SVG text")
    parser.add_argument("--three-images", action="store_true", help="Create A/B/C image package PPTX")
    parser.add_argument("--editable-text-pptx", action="store_true", help="Create locked-background/editable-text PPTX")
    parser.add_argument("--order", default="A,B,C", help="Layer package order, e.g. A,B,C or B,A,C")
    parser.add_argument("-o", "--output-dir", type=Path, default=None, help="Output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        svg_files = _resolve_svg_files(args.project_path, args.source, args.page, args.all)
        provided: dict[Path, Path] = {}
        if args.background_image:
            if len(svg_files) != 1:
                print("--background-image is only valid with a single --page export", file=sys.stderr)
                return 1
            provided[svg_files[0]] = args.background_image
        output_dir = args.output_dir or (args.project_path / "exports")
        order = tuple(part.strip().upper() for part in args.order.split(",") if part.strip())
        if set(order) != {"A", "B", "C"} or len(order) != 3:
            print("--order must contain A, B, and C exactly once", file=sys.stderr)
            return 1
        if not args.three_images and not args.editable_text_pptx:
            args.three_images = True
            args.editable_text_pptx = True
        result = run_layered_export(
            project_path=args.project_path,
            svg_files=svg_files,
            output_dir=output_dir,
            provided_backgrounds=provided,
            make_three_images=args.three_images,
            make_editable_text=args.editable_text_pptx,
            order=order,
            derive_background=args.derive_background,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Assets: {result.assets_dir}")
    if result.three_images_pptx:
        print(f"Three-image PPTX: {result.three_images_pptx}")
    if result.editable_text_pptx:
        print(f"Editable-text PPTX: {result.editable_text_pptx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
