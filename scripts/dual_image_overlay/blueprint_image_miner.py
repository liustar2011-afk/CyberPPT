from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image


CANVAS_W = 1280
CANVAS_H = 720


def _page_number_from_name(name: str) -> int | None:
    match = re.search(r"slide-(\d+)-blueprint", name)
    return int(match.group(1)) if match else None


def _scale_rect(rect: dict[str, float], width: int, height: int) -> dict[str, float]:
    return {
        "x": round(rect["x"] * CANVAS_W / width, 2),
        "y": round(rect["y"] * CANVAS_H / height, 2),
        "w": round(rect["w"] * CANVAS_W / width, 2),
        "h": round(rect["h"] * CANVAS_H / height, 2),
    }


def _is_dark_blue(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return b > r + 18 and b > g + 5 and r < 70 and g < 100 and b < 150


def _is_not_background(pixel: tuple[int, int, int], background: tuple[int, int, int]) -> bool:
    return sum(abs(pixel[i] - background[i]) for i in range(3)) > 34


def _median_color(samples: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    return tuple(int(median(channel)) for channel in zip(*samples))


def _estimate_background(image: Image.Image) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    samples: list[tuple[int, int, int]] = []
    for x, y in (
        (8, 8),
        (width - 9, 8),
        (8, height - 9),
        (width - 9, height - 9),
        (width // 2, 8),
        (width // 2, height - 9),
    ):
        samples.append(rgb.getpixel((x, y)))
    return _median_color(samples)


def _row_segments(flags: list[bool], min_len: int = 3) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    start: int | None = None
    for index, flag in enumerate(flags + [False]):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            if index - start >= min_len:
                segments.append((start, index - 1))
            start = None
    return segments


def _bbox_from_mask(points: list[tuple[int, int]]) -> dict[str, float] | None:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return {"x": float(x0), "y": float(y0), "w": float(x1 - x0 + 1), "h": float(y1 - y0 + 1)}


def _dark_blue_bbox(image: Image.Image, x_range: tuple[int, int], y_range: tuple[int, int]) -> dict[str, float] | None:
    rgb = image.convert("RGB")
    points: list[tuple[int, int]] = []
    for y in range(max(0, y_range[0]), min(rgb.height, y_range[1])):
        for x in range(max(0, x_range[0]), min(rgb.width, x_range[1])):
            if _is_dark_blue(rgb.getpixel((x, y))):
                points.append((x, y))
    return _bbox_from_mask(points)


def _content_bbox(image: Image.Image, background: tuple[int, int, int]) -> dict[str, float] | None:
    rgb = image.convert("RGB")
    points: list[tuple[int, int]] = []
    step = 2
    for y in range(0, rgb.height, step):
        for x in range(0, rgb.width, step):
            if _is_not_background(rgb.getpixel((x, y)), background):
                points.append((x, y))
    return _bbox_from_mask(points)


def _lower_dark_band(image: Image.Image) -> dict[str, float] | None:
    rgb = image.convert("RGB")
    width, height = rgb.size
    y_start = int(height * 0.68)
    flags: list[bool] = []
    for y in range(y_start, height):
        dark_count = sum(1 for x in range(width) if _is_dark_blue(rgb.getpixel((x, y))))
        flags.append(dark_count / width > 0.18)
    segments = _row_segments(flags, min_len=4)
    if not segments:
        return None
    start, end = max(segments, key=lambda segment: segment[1] - segment[0])
    y0 = y_start + start
    y1 = y_start + end
    return _dark_blue_bbox(image, (0, width), (max(0, y0 - 2), min(height, y1 + 3)))


def analyze_blueprint_image(path: Path) -> dict[str, Any]:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    background = _estimate_background(image)
    content = _content_bbox(image, background)
    lower_band = _lower_dark_band(image)
    top_badge = _dark_blue_bbox(image, (0, int(width * 0.14)), (0, int(height * 0.2)))
    dark_pixels = 0
    sampled = 0
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            sampled += 1
            if _is_dark_blue(image.getpixel((x, y))):
                dark_pixels += 1
    return {
        "page_number": _page_number_from_name(path.name),
        "source": str(path),
        "width": width,
        "height": height,
        "background_rgb": background,
        "dark_blue_sample_ratio": round(dark_pixels / sampled, 4) if sampled else 0,
        "content_bbox": _scale_rect(content, width, height) if content else None,
        "top_badge_bbox": _scale_rect(top_badge, width, height) if top_badge else None,
        "lower_dark_band_bbox": _scale_rect(lower_band, width, height) if lower_band else None,
    }


def _slide_meta_by_page(blueprint_dir: Path) -> dict[int, dict[str, Any]]:
    manifest_path = blueprint_dir / "blueprint-manifest.json"
    if not manifest_path.exists():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {int(slide["slide"]): slide for slide in manifest.get("slides", []) if "slide" in slide}


def _median_rect(rects: list[dict[str, float]]) -> dict[str, float] | None:
    if not rects:
        return None
    return {
        key: round(float(median(rect[key] for rect in rects)), 2)
        for key in ("x", "y", "w", "h")
    }


def _safe_body_zone(slides: list[dict[str, Any]]) -> dict[str, float] | None:
    bands = [slide["lower_dark_band_bbox"] for slide in slides if slide.get("lower_dark_band_bbox")]
    if not bands:
        return None
    left = max(24.0, round(float(median(band["x"] for band in bands)), 2))
    right_margin = max(24.0, round(float(median(CANVAS_W - band["x"] - band["w"] for band in bands)), 2))
    top = 84.0
    bottom = round(float(median(band["y"] for band in bands)) - 14.0, 2)
    return {
        "x": left,
        "y": top,
        "w": round(CANVAS_W - left - right_margin, 2),
        "h": round(max(1.0, bottom - top), 2),
    }


def mine_blueprint_images(blueprint_dir: Path) -> dict[str, Any]:
    slide_meta = _slide_meta_by_page(blueprint_dir)
    slides: list[dict[str, Any]] = []
    for path in sorted(blueprint_dir.glob("slide-*-blueprint.png")):
        analyzed = analyze_blueprint_image(path)
        meta = slide_meta.get(analyzed["page_number"] or -1, {})
        analyzed["title"] = meta.get("title")
        analyzed["role"] = meta.get("role")
        analyzed["density_target"] = meta.get("density_target")
        analyzed["chart_plan"] = meta.get("chart_plan")
        slides.append(analyzed)

    lower_bands = [slide["lower_dark_band_bbox"] for slide in slides if slide.get("lower_dark_band_bbox")]
    content_boxes = [slide["content_bbox"] for slide in slides if slide.get("content_bbox")]
    badges = [slide["top_badge_bbox"] for slide in slides if slide.get("top_badge_bbox")]
    ratios = [float(slide["dark_blue_sample_ratio"]) for slide in slides]
    roles = sorted({str(slide.get("role")) for slide in slides if slide.get("role")})
    return {
        "schema": "cyberppt.blueprint_image_style_learning.v1",
        "blueprint_dir": str(blueprint_dir),
        "sample_count": len(slides),
        "learned_rules": {
            "canvas": {"width": CANVAS_W, "height": CANVAS_H, "aspect": "16:9"},
            "content_bbox_median": _median_rect(content_boxes),
            "safe_body_zone_median": _safe_body_zone(slides),
            "top_badge_bbox_median": _median_rect(badges),
            "lower_so_what_band_bbox_median": _median_rect(lower_bands),
            "dark_blue_sample_ratio_median": round(float(median(ratios)), 4) if ratios else 0,
            "roles_seen": roles,
            "blueprint_text_policy": "treat blueprint text as placeholder; final PPT uses content-lock text",
            "candidate_rules": [
                "Reserve top-left badge area for slide number on high-density pages.",
                "Place editable body components inside safe_body_zone_median unless the slide is a cover.",
                "Use lower dark band as SO WHAT/conclusion area when detected.",
                "Use blueprint images for layout and visual density only; do not copy distorted small text.",
            ],
        },
        "slides": slides,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Learn visual layout rules from CyberPPT blueprint images.")
    parser.add_argument("blueprint_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = mine_blueprint_images(args.blueprint_dir)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
