"""CJK / preview smoke helpers for render-backend QA."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

CJK_RE = re.compile(r"[\u3400-\u9fff]")
TOFU_RE = re.compile(r"[□�]")


def svg_text_has_cjk(svg_path: Path) -> bool:
    try:
        text = svg_path.read_text(encoding="utf-8")
    except OSError:
        return False
    if TOFU_RE.search(text):
        return True
    return bool(CJK_RE.search(text))


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


@dataclass(frozen=True)
class TextRegion:
    x: int
    y: int
    width: int
    height: int
    has_cjk: bool


def _parse_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def text_regions_from_svg(svg_path: Path) -> list[TextRegion]:
    try:
        root = ET.parse(svg_path).getroot()
    except (ET.ParseError, OSError):
        return []
    regions: list[TextRegion] = []
    for elem in root.iter():
        if _strip_ns(elem.tag) != "text":
            continue
        content = "".join(elem.itertext())
        if not content.strip():
            continue
        x = _parse_int(elem.get("x"), 0)
        y = _parse_int(elem.get("y"), 0)
        font_size = _parse_int(elem.get("font-size"), 28)
        width = max(240, len(content) * font_size)
        height = max(font_size + 16, font_size * 2)
        regions.append(
            TextRegion(
                x=x,
                y=max(0, y - font_size),
                width=width,
                height=height,
                has_cjk=bool(CJK_RE.search(content)),
            )
        )
    return regions


def preview_is_nonblank(preview_path: Path, *, threshold: float = 0.99) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return preview_path.is_file() and preview_path.stat().st_size > 500
    if not preview_path.is_file():
        return False
    image = Image.open(preview_path).convert("RGB")
    pixels = list(image.getdata())
    if not pixels:
        return False
    counts: dict[tuple[int, int, int], int] = {}
    for pixel in pixels:
        key = (pixel[0] >> 4, pixel[1] >> 4, pixel[2] >> 4)
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values()) / len(pixels) < threshold


def detect_preview_cjk_tofu(preview_path: Path, svg_path: Path) -> bool:
    """
    Heuristic: missing-glyph / tofu boxes in CJK text regions are low-variance gray fills.
    """
    if not svg_text_has_cjk(svg_path) or not preview_path.is_file():
        return False
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return False
    regions = [region for region in text_regions_from_svg(svg_path) if region.has_cjk]
    if not regions:
        return False
    image = Image.open(preview_path).convert("L")
    width, height = image.size
    for region in regions:
        x1 = max(0, min(width - 1, region.x))
        y1 = max(0, min(height - 1, region.y))
        x2 = max(x1 + 1, min(width, region.x + region.width))
        y2 = max(y1 + 1, min(height, region.y + region.height))
        crop = image.crop((x1, y1, x2, y2))
        if crop.width < 8 or crop.height < 8:
            continue
        stat = ImageStat.Stat(crop)
        stddev = stat.stddev[0]
        mean = stat.mean[0]
        if stddev < 10.0 and 165.0 <= mean <= 245.0:
            return True
    return False
