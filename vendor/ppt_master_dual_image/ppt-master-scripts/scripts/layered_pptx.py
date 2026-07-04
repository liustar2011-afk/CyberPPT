#!/usr/bin/env python3
"""
PPT Master - Layered PPTX Builder

Build PPTX files for A/B/C image-result packaging and locked-background with
editable text overlay.

Usage:
    python3 scripts/layered_pptx.py --help

Examples:
    python3 scripts/layered_pptx.py --help

Dependencies:
    python-pptx, Pillow
"""

from __future__ import annotations

import html
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.util import Emu, Pt


SVG_NS = "http://www.w3.org/2000/svg"
EMU_PER_PX = 9525


@dataclass
class TextRun:
    text: str
    x: float
    y: float
    font_size: float
    font_family: str
    fill: str
    font_weight: str
    text_anchor: str
    line_height: float


@dataclass
class PositionedText:
    text: str
    x: float
    y: float
    w: float
    h: float
    font_size: float
    font_family: str
    fill: str
    font_weight: str
    align: str = "left"
    word_wrap: bool = False


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.match(r"[-+]?\d*\.?\d+", value.strip())
    if not match:
        return default
    return float(match.group(0))


def _style_map(style: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    if not style:
        return result
    for item in style.split(";"):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def _attr(elem: ET.Element, name: str, inherited: dict[str, str]) -> str | None:
    styles = _style_map(elem.get("style"))
    if name in styles:
        return styles[name]
    if elem.get(name) is not None:
        return elem.get(name)
    return inherited.get(name)


def _merge_inherited(elem: ET.Element, inherited: dict[str, str]) -> dict[str, str]:
    merged = dict(inherited)
    styles = _style_map(elem.get("style"))
    for name in (
        "font-family",
        "font-size",
        "font-weight",
        "fill",
        "text-anchor",
        "line-height",
    ):
        value = styles.get(name) or elem.get(name)
        if value is not None:
            merged[name] = value
    return merged


def _text_content(elem: ET.Element) -> str:
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in list(elem):
        if _local_name(child.tag) in {"tspan", "text"}:
            parts.append(_text_content(child))
        if child.tail:
            parts.append(child.tail)
    return html.unescape("".join(parts)).strip()


def _hex_to_rgb(value: str) -> RGBColor:
    text = (value or "#000000").strip()
    if text.lower() in {"none", "transparent"}:
        text = "#000000"
    if text.startswith("#"):
        text = text[1:]
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", text):
        text = "000000"
    return RGBColor(int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def _estimate_width_px(text: str, font_size: float, font_weight: str) -> float:
    weight_factor = 1.08 if font_weight in {"bold", "700", "800", "900"} else 1.0
    width = 0.0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            width += font_size
        elif ch.isspace():
            width += font_size * 0.35
        else:
            width += font_size * 0.56
    return max(width * weight_factor, font_size)


def extract_text_runs(svg_text: str) -> list[TextRun]:
    """Extract top-level editable text frames from an SVG."""
    root = ET.fromstring(svg_text)
    runs: list[TextRun] = []

    def walk(elem: ET.Element, inherited: dict[str, str]) -> None:
        merged = _merge_inherited(elem, inherited)
        if _local_name(elem.tag) == "text":
            text = _text_content(elem)
            if text:
                font_size = _float(_attr(elem, "font-size", merged), 18.0)
                line_height = _float(_attr(elem, "line-height", merged), font_size * 1.2)
                runs.append(
                    TextRun(
                        text=text,
                        x=_float(elem.get("x"), 0.0),
                        y=_float(elem.get("y"), 0.0),
                        font_size=font_size,
                        font_family=(_attr(elem, "font-family", merged) or "Arial").split(",")[0].strip("'\" "),
                        fill=_attr(elem, "fill", merged) or "#000000",
                        font_weight=_attr(elem, "font-weight", merged) or "400",
                        text_anchor=_attr(elem, "text-anchor", merged) or "start",
                        line_height=line_height,
                    )
                )
            return
        for child in list(elem):
            walk(child, merged)

    walk(root, {})
    return runs


def _set_slide_size(prs: Presentation, pixel_size: tuple[int, int]) -> None:
    width, height = pixel_size
    prs.slide_width = Emu(width * EMU_PER_PX)
    prs.slide_height = Emu(height * EMU_PER_PX)


def create_three_image_pptx(
    image_pages: list[tuple[Path, str]],
    output_path: Path,
    pixel_size: tuple[int, int],
) -> None:
    """Create a PPTX where every slide is one full-canvas image."""
    prs = Presentation()
    _set_slide_size(prs, pixel_size)
    blank = prs.slide_layouts[6]
    for image_path, _label in image_pages:
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(str(image_path), 0, 0, width=prs.slide_width, height=prs.slide_height)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))


def create_editable_text_pptx(
    pages: list[tuple[Path, str, str]],
    output_path: Path,
    pixel_size: tuple[int, int],
) -> None:
    """Create PPTX pages from a locked background image plus editable text."""
    prs = Presentation()
    _set_slide_size(prs, pixel_size)
    blank = prs.slide_layouts[6]

    for background_path, text_svg, _label in pages:
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(str(background_path), 0, 0, width=prs.slide_width, height=prs.slide_height)
        for run in extract_text_runs(text_svg):
            width_px = _estimate_width_px(run.text, run.font_size, run.font_weight) * 1.08
            height_px = max(run.line_height * 1.5, run.font_size * 1.5)
            x_px = run.x
            if run.text_anchor == "middle":
                x_px -= width_px / 2
            elif run.text_anchor == "end":
                x_px -= width_px
            y_px = run.y - run.font_size * 1.05
            textbox = slide.shapes.add_textbox(
                Emu(x_px * EMU_PER_PX),
                Emu(y_px * EMU_PER_PX),
                Emu(width_px * EMU_PER_PX),
                Emu(height_px * EMU_PER_PX),
            )
            text_frame = textbox.text_frame
            text_frame.clear()
            text_frame.margin_left = 0
            text_frame.margin_right = 0
            text_frame.margin_top = 0
            text_frame.margin_bottom = 0
            text_frame.vertical_anchor = MSO_ANCHOR.TOP
            paragraph = text_frame.paragraphs[0]
            paragraph.alignment = {
                "middle": PP_ALIGN.CENTER,
                "end": PP_ALIGN.RIGHT,
            }.get(run.text_anchor, PP_ALIGN.LEFT)
            ppt_run = paragraph.add_run()
            ppt_run.text = run.text
            ppt_run.font.size = Pt(run.font_size * 0.75)
            ppt_run.font.name = run.font_family or "Arial"
            ppt_run.font.bold = run.font_weight in {"bold", "700", "800", "900"}
            ppt_run.font.color.rgb = _hex_to_rgb(run.fill)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))


def create_positioned_text_pptx(
    pages: list[tuple[Path, list[PositionedText], str]],
    output_path: Path,
    pixel_size: tuple[int, int],
) -> None:
    """Create PPTX pages from background images and explicit text boxes."""
    prs = Presentation()
    _set_slide_size(prs, pixel_size)
    blank = prs.slide_layouts[6]

    for background_path, text_boxes, _label in pages:
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(str(background_path), 0, 0, width=prs.slide_width, height=prs.slide_height)
        for box in text_boxes:
            textbox = slide.shapes.add_textbox(
                Emu(max(0, box.x) * EMU_PER_PX),
                Emu(max(0, box.y) * EMU_PER_PX),
                Emu(max(1, box.w) * EMU_PER_PX),
                Emu(max(1, box.h) * EMU_PER_PX),
            )
            text_frame = textbox.text_frame
            text_frame.clear()
            text_frame.word_wrap = box.word_wrap
            text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            text_frame.margin_left = 0
            text_frame.margin_right = 0
            text_frame.margin_top = 0
            text_frame.margin_bottom = 0
            text_frame.vertical_anchor = MSO_ANCHOR.TOP
            paragraph = text_frame.paragraphs[0]
            paragraph.alignment = {
                "center": PP_ALIGN.CENTER,
                "right": PP_ALIGN.RIGHT,
            }.get(box.align, PP_ALIGN.LEFT)
            lines = box.text.splitlines() or [box.text]
            for index, line in enumerate(lines):
                current = paragraph if index == 0 else text_frame.add_paragraph()
                current.alignment = paragraph.alignment
                current.space_after = Pt(0)
                current.space_before = Pt(0)
                ppt_run = current.add_run()
                ppt_run.text = line
                ppt_run.font.size = Pt(box.font_size)
                ppt_run.font.name = box.font_family or "SimHei"
                ppt_run.font.bold = box.font_weight in {"bold", "700", "800", "900"}
                ppt_run.font.color.rgb = _hex_to_rgb(box.fill)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))


def main(argv: list[str] | None = None) -> int:
    print("layered_pptx is a helper module; use layered_export.py.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
