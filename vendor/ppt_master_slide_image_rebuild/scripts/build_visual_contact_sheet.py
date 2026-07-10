#!/usr/bin/env python3
"""Build visual QA contact sheets from reference and preview images.

The sheet is a review artifact only: it never decides whether a rebuild is
valid. It helps humans inspect repeated failure areas such as top bands, main
content, dense text, icons, and bottom margins without reopening multiple
files.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


CANVAS_FALLBACK = (1280, 720)
CONTACT_DIR = Path("exports/qa/contact_sheets")


@dataclass(frozen=True)
class Region:
    label: str
    bbox: tuple[int, int, int, int]
    source: str

    @property
    def area(self) -> int:
        x1, y1, x2, y2 = self.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _rel_or_abs(project: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = project / path
    return path if path.is_file() else None


def _manifest_page_map(project: Path) -> dict[str, dict[str, Any]]:
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages", []) if isinstance(manifest, dict) else []
    out: dict[str, dict[str, Any]] = {}
    if isinstance(pages, list):
        for index, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                continue
            page_id = str(page.get("page_id") or f"P{index:02d}")
            out[page_id] = page
    return out


def _find_reference(project: Path, page_id: str) -> Path | None:
    page = _manifest_page_map(project).get(page_id, {})
    for key in ("reference_image", "source_image"):
        candidate = _rel_or_abs(project, page.get(key))
        if candidate:
            return candidate
    layout = _load_json(project / "layout_reference.json")
    source = layout.get("source_reference", {}) if isinstance(layout, dict) else {}
    if isinstance(source, dict):
        candidate = _rel_or_abs(project, source.get("path"))
        if candidate:
            return candidate
    images = project / "images"
    if images.is_dir():
        for pattern in ("reference_layout.*", "reference.*", "*reference*layout*"):
            for path in sorted(images.glob(pattern)):
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    return path
    return None


def _preview_paths(project: Path) -> list[Path]:
    preview_dir = project / "exports" / "preview_qa"
    if not preview_dir.is_dir():
        return []
    return sorted(preview_dir.glob("*.preview.png"))


def _page_id_from_preview(path: Path) -> str:
    name = path.name
    return name.removesuffix(".preview.png")


def _bbox(raw: Any, size: tuple[int, int], *, expand: int = 0) -> tuple[int, int, int, int] | None:
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    if not all(isinstance(value, (int, float)) for value in raw):
        return None
    x, y, w, h = [float(value) for value in raw]
    width, height = size
    x1 = max(0, int(round(x - expand)))
    y1 = max(0, int(round(y - expand)))
    x2 = min(width, int(round(x + w + expand)))
    y2 = min(height, int(round(y + h + expand)))
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def _union(regions: list[Region], label: str, source: str, size: tuple[int, int], expand: int = 0) -> Region | None:
    if not regions:
        return None
    x1 = min(region.bbox[0] for region in regions)
    y1 = min(region.bbox[1] for region in regions)
    x2 = max(region.bbox[2] for region in regions)
    y2 = max(region.bbox[3] for region in regions)
    width, height = size
    box = (
        max(0, x1 - expand),
        max(0, y1 - expand),
        min(width, x2 + expand),
        min(height, y2 + expand),
    )
    return Region(label, box, source)


def _layout_regions(project: Path, size: tuple[int, int]) -> list[Region]:
    layout = _load_json(project / "layout_reference.json")
    zones = layout.get("zones", []) if isinstance(layout, dict) else []
    regions: list[Region] = []
    if isinstance(zones, list):
        for zone in zones:
            if not isinstance(zone, dict):
                continue
            box = _bbox(zone.get("bbox_px"), size, expand=12)
            if box:
                label = str(zone.get("id") or zone.get("role") or "zone")
                regions.append(Region(label, box, "layout_reference.zones"))
    return regions


def _text_regions(project: Path, page_id: str, size: tuple[int, int]) -> list[Region]:
    mapping = _load_json(project / "text_region_map.json")
    pages = mapping.get("pages", []) if isinstance(mapping, dict) else []
    regions: list[Region] = []
    for page in pages if isinstance(pages, list) else []:
        if not isinstance(page, dict):
            continue
        if str(page.get("page_id") or page_id) not in {page_id, page_id.removeprefix("P")}:
            continue
        for item in page.get("regions", []) if isinstance(page.get("regions"), list) else []:
            if not isinstance(item, dict):
                continue
            box = _bbox(item.get("bbox"), size, expand=10)
            if box:
                label = str(item.get("id") or "text_region")
                regions.append(Region(label, box, "text_region_map"))
    return regions


def _icon_regions(project: Path, page_id: str, size: tuple[int, int]) -> list[Region]:
    manifest = _load_json(project / "icon_manifest.json")
    pages = manifest.get("pages", []) if isinstance(manifest, dict) else []
    regions: list[Region] = []
    for page in pages if isinstance(pages, list) else []:
        if not isinstance(page, dict):
            continue
        if str(page.get("page_id") or page_id) not in {page_id, page_id.removeprefix("P")}:
            continue
        icons = page.get("icons", [])
        for icon in icons if isinstance(icons, list) else []:
            if not isinstance(icon, dict):
                continue
            box = _bbox(icon.get("bbox_px"), size, expand=12)
            if box:
                regions.append(Region(str(icon.get("id") or "icon"), box, "icon_manifest"))
    return regions


def _default_regions(project: Path, page_id: str, size: tuple[int, int]) -> list[Region]:
    width, height = size
    regions = [
        Region("full_page", (0, 0, width, height), "default"),
        Region("top_band", (0, 0, width, min(height, int(height * 0.24))), "default"),
        Region("main_content", (0, int(height * 0.22), width, min(height, int(height * 0.92))), "default"),
        Region("bottom_band", (0, max(0, int(height * 0.86)), width, height), "default"),
    ]
    zones = _layout_regions(project, size)
    text_regions = _text_regions(project, page_id, size)
    icon_regions = _icon_regions(project, page_id, size)
    text_union = _union(text_regions, "text_regions", "text_region_map", size, expand=16)
    icon_union = _union(icon_regions, "icon_regions", "icon_manifest", size, expand=16)
    regions.extend(sorted(zones, key=lambda item: item.area, reverse=True)[:6])
    if text_union:
        regions.append(text_union)
    if icon_union:
        regions.append(icon_union)
    return _dedupe_regions(regions)


def _dedupe_regions(regions: list[Region]) -> list[Region]:
    seen: set[tuple[int, int, int, int]] = set()
    out: list[Region] = []
    for region in regions:
        if region.bbox in seen:
            continue
        seen.add(region.bbox)
        out.append(region)
    return out[:12]


def _fit_crop(image: Image.Image | None, bbox: tuple[int, int, int, int], size: tuple[int, int]) -> Image.Image:
    if image is None:
        return Image.new("RGB", size, (245, 247, 250))
    crop = image.crop(bbox).convert("RGB")
    return ImageOps.contain(crop, size, Image.Resampling.LANCZOS)


def _diff_crop(reference: Image.Image | None, preview: Image.Image, bbox: tuple[int, int, int, int], size: tuple[int, int]) -> Image.Image:
    if reference is None:
        return Image.new("RGB", size, (245, 247, 250))
    ref = reference.crop(bbox).convert("RGB")
    out = preview.crop(bbox).convert("RGB")
    diff = ImageChops.difference(ref, out)
    diff = ImageOps.autocontrast(diff)
    return ImageOps.contain(diff, size, Image.Resampling.LANCZOS)


def _font(size: int = 18) -> ImageFont.ImageFont:
    for name in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        path = Path(name)
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _paste_centered(canvas: Image.Image, image: Image.Image, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    x = x1 + (x2 - x1 - image.width) // 2
    y = y1 + (y2 - y1 - image.height) // 2
    canvas.paste(image, (x, y))


def _draw_label(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str, font: ImageFont.ImageFont) -> None:
    x1, y1, x2, _y2 = box
    draw.rectangle((x1, y1, x2, y1 + 28), fill=(17, 24, 39))
    draw.text((x1 + 8, y1 + 5), label[:64], fill=(255, 255, 255), font=font)


def _sheet_for_page(
    project: Path,
    page_id: str,
    preview_path: Path,
    *,
    output_dir: Path,
) -> dict[str, Any]:
    preview = Image.open(preview_path).convert("RGB")
    reference_path = _find_reference(project, page_id)
    reference = Image.open(reference_path).convert("RGB").resize(preview.size) if reference_path else None
    regions = _default_regions(project, page_id, preview.size)
    thumb_w, thumb_h = 300, 170
    label_h = 28
    gap = 14
    row_h = label_h + thumb_h + 12
    header_h = 54
    width = gap * 4 + thumb_w * 3
    height = header_h + gap + len(regions) * (row_h + gap)
    sheet = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    font = _font(17)
    small = _font(14)
    draw.text((gap, 14), f"{page_id} visual QA contact sheet", fill=(17, 24, 39), font=_font(24))
    for index, title in enumerate(("reference", "preview", "diff")):
        x = gap + index * (thumb_w + gap)
        draw.text((x + 6, header_h - 18), title, fill=(75, 85, 99), font=small)
    for row, region in enumerate(regions):
        y = header_h + gap + row * (row_h + gap)
        for col in range(3):
            x = gap + col * (thumb_w + gap)
            cell = (x, y, x + thumb_w, y + label_h + thumb_h)
            draw.rectangle(cell, outline=(203, 213, 225), width=1)
            if col == 0:
                crop = _fit_crop(reference, region.bbox, (thumb_w, thumb_h))
            elif col == 1:
                crop = _fit_crop(preview, region.bbox, (thumb_w, thumb_h))
            else:
                crop = _diff_crop(reference, preview, region.bbox, (thumb_w, thumb_h))
            _draw_label(draw, (x, y, x + thumb_w, y + label_h), f"{region.label} | {region.source}", small)
            _paste_centered(sheet, crop, (x, y + label_h, x + thumb_w, y + label_h + thumb_h))
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{page_id}.contact_sheet.png"
    sheet.save(out_path)
    return {
        "page_id": page_id,
        "valid": True,
        "preview": str(preview_path),
        "reference": str(reference_path) if reference_path else None,
        "contact_sheet": str(out_path),
        "regions": [{"label": region.label, "bbox": list(region.bbox), "source": region.source} for region in regions],
    }


def inspect(project: Path, *, output_dir: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    previews = _preview_paths(project)
    if not previews:
        return {
            "valid": False,
            "errors": ["No preview PNGs found under exports/preview_qa"],
            "warnings": warnings,
            "results": [],
        }
    out_dir = output_dir or project / CONTACT_DIR
    results: list[dict[str, Any]] = []
    for preview_path in previews:
        page_id = _page_id_from_preview(preview_path)
        try:
            result = _sheet_for_page(project, page_id, preview_path, output_dir=out_dir)
            if result.get("reference") is None:
                warnings.append(f"{page_id}: reference image not found; generated preview-only sheet")
            results.append(result)
        except Exception as exc:  # pragma: no cover - defensive report artifact
            errors.append(f"{page_id}: contact sheet generation failed: {exc}")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "count": len(results),
        "output_dir": str(out_dir),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build visual QA contact sheets for rendered previews.")
    parser.add_argument("project", type=Path, help="slide-image-rebuild project directory")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = inspect(args.project, output_dir=args.output_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
