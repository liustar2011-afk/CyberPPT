#!/usr/bin/env python3
"""Map script text truth onto OCR text boxes and render editable overlay SVG."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from template_image_ppt_export import extract_content, image_visible_text, page_role, parse_page_blocks


MODULE_PREFIX_RE = re.compile(r"^模块[一二三四五六七八九十百千万0-9]+[:：]\s*")
MODULE_LINE_RE = re.compile(r"^(模块[一二三四五六七八九十百千万0-9]+)[:：]\s*(?P<title>.+)$")


@dataclass
class OverlayTextBox:
    text: str
    x: float
    y: float
    w: float
    h: float
    font_size: float
    font_family: str = "Microsoft YaHei"
    fill: str = "#0B1F3D"
    font_weight: str = "400"
    align: str = "left"
    word_wrap: bool = False
    source: str = "script_matched"
    confidence: float = 1.0


@dataclass
class SemanticContainer:
    id: str
    role: str
    x: float
    y: float
    w: float
    h: float
    background: str = "light"
    fill: str = "#0B1F3D"
    align: str = "center"
    max_lines: int = 1


@dataclass
class SemanticLayer:
    role: str
    title: str
    expected_count: int | None
    keywords: list[str]


@dataclass
class SemanticPlan:
    page_number: int
    layers: list[SemanticLayer]


def normalize_text(text: str) -> str:
    return re.sub(r"[\s\-·•,，.。:：;；、\"'“”‘’（）()\[\]【】]+", "", text).lower()


def _clean_line(line: str) -> str:
    line = line.strip()
    line = MODULE_PREFIX_RE.sub("", line)
    line = re.sub(r"^[-*•·]\s*", "", line)
    if line.startswith("标题：") or line.startswith("标题:"):
        line = re.split(r"[:：]", line, 1)[-1].strip()
    if line.startswith("副标题：") or line.startswith("副标题:"):
        line = re.split(r"[:：]", line, 1)[-1].strip()
    return line.strip()


def extract_script_truth_lines(script_path: Path, page_number: int) -> list[str]:
    pages = parse_page_blocks(script_path)
    if page_number not in pages:
        raise ValueError(f"Page {page_number} not found in script: {script_path}")
    block = pages[page_number]
    content = extract_content(block)
    visible = image_visible_text(block, content, page_role(block))
    candidates = [content.title, content.subtitle, *visible.splitlines()]
    lines: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = _clean_line(candidate)
        if not cleaned:
            continue
        key = normalize_text(cleaned)
        if key and key not in seen:
            lines.append(cleaned)
            seen.add(key)
    return lines


def match_script_text(ocr_text: str, script_lines: list[str], threshold: float = 0.66) -> tuple[str, str]:
    """Return corrected text and source label."""
    ocr_key = normalize_text(ocr_text)
    if not ocr_key:
        return ocr_text, "ocr_unmatched"
    best_line = ""
    best_score = 0.0
    for line in script_lines:
        line_key = normalize_text(line)
        if not line_key:
            continue
        if ocr_key in line_key or line_key in ocr_key:
            score = min(len(ocr_key), len(line_key)) / max(len(ocr_key), len(line_key))
        else:
            score = SequenceMatcher(None, ocr_key, line_key).ratio()
        if score > best_score:
            best_score = score
            best_line = line
    if best_line and best_score >= threshold:
        return best_line, "script_matched"
    return ocr_text, "ocr_unmatched"


def _role_for_module_title(title: str) -> str:
    if "底座" in title:
        return "foundation_base"
    if "支撑体系" in title or "体系" in title:
        return "support_system"
    if "核心场景" in title or "场景" in title:
        return "application_scenario"
    if "生态节点" in title or "节点" in title:
        return "ecosystem_node"
    return "content_group"


def _expected_count_from_title(title: str) -> int | None:
    match = re.search(r"(\d+)\s*(?:个|套|大)?", title)
    if match:
        return int(match.group(1))
    return None


def extract_semantic_plan(script_path: Path, page_number: int) -> SemanticPlan:
    pages = parse_page_blocks(script_path)
    if page_number not in pages:
        raise ValueError(f"Page {page_number} not found in script: {script_path}")
    content = extract_content(pages[page_number])
    layers: list[SemanticLayer] = []
    current: dict[str, Any] | None = None
    for raw_line in content.body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        module_match = MODULE_LINE_RE.match(line)
        if module_match:
            if current is not None:
                layers.append(
                    SemanticLayer(
                        role=_role_for_module_title(str(current["title"])),
                        title=str(current["title"]),
                        expected_count=_expected_count_from_title(str(current["title"])),
                        keywords=list(current["keywords"]),
                    )
                )
            current = {"title": module_match.group("title").strip(), "keywords": [module_match.group("title").strip()]}
            continue
        if current is not None:
            current["keywords"].append(_clean_line(line))
    if current is not None:
        layers.append(
            SemanticLayer(
                role=_role_for_module_title(str(current["title"])),
                title=str(current["title"]),
                expected_count=_expected_count_from_title(str(current["title"])),
                keywords=list(current["keywords"]),
            )
        )
    return SemanticPlan(page_number=page_number, layers=layers)


def _font_size_from_box(height: float) -> float:
    return max(10.0, min(28.0, height * 0.62))


def _weight_for_text(text: str, height: float) -> str:
    if height >= 28 or len(text) <= 8:
        return "700"
    return "400"


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    red, green, blue = rgb
    return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)


def _sample_background_luminance(
    image: Image.Image,
    bbox: tuple[float, float, float, float],
    image_width: float,
    image_height: float,
) -> float | None:
    if image_width <= 0 or image_height <= 0:
        return None
    actual_width, actual_height = image.size
    x1, y1, x2, y2 = bbox
    left = max(0, min(actual_width - 1, int(round(x1 / image_width * actual_width))))
    top = max(0, min(actual_height - 1, int(round(y1 / image_height * actual_height))))
    right = max(left + 1, min(actual_width, int(round(x2 / image_width * actual_width))))
    bottom = max(top + 1, min(actual_height, int(round(y2 / image_height * actual_height))))
    region = image.crop((left, top, right, bottom)).convert("RGB")
    red, green, blue = ImageStat.Stat(region).mean[:3]
    return _relative_luminance((int(red), int(green), int(blue)))


def _fill_for_background(
    background: Image.Image | None,
    bbox: tuple[float, float, float, float],
    image_width: float,
    image_height: float,
    default_fill: str,
) -> str:
    if background is None:
        return default_fill
    luminance = _sample_background_luminance(background, bbox, image_width, image_height)
    if luminance is not None and luminance < 105:
        return "#FFFFFF"
    return default_fill


def _image_bbox_to_body(
    bbox: tuple[float, float, float, float],
    image_width: float,
    image_height: float,
    body_region: dict[str, float],
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    sx = float(body_region["width"]) / image_width
    sy = float(body_region["height"]) / image_height
    x = float(body_region["x"]) + x1 * sx
    y = float(body_region["y"]) + y1 * sy
    w = max(1.0, (x2 - x1) * sx)
    h = max(1.0, (y2 - y1) * sy)
    return x, y, w, h


def infer_semantic_containers(
    background_image: Path,
    ocr_layout: dict[str, Any],
    body_region: dict[str, float],
    *,
    semantic_plan: SemanticPlan | None = None,
) -> list[SemanticContainer]:
    """Infer coarse visual containers from generated background shapes."""
    image_size = ocr_layout.get("image_size") or {}
    image_width = float(image_size.get("width") or 1)
    image_height = float(image_size.get("height") or 1)
    containers: list[SemanticContainer] = []
    with Image.open(background_image) as raw:
        image = raw.convert("RGB")
        width, height = image.size
        dark_rows: list[bool] = []
        for y in range(height):
            row = image.crop((0, y, width, y + 1))
            mean = tuple(int(value) for value in ImageStat.Stat(row).mean[:3])
            dark_rows.append(_relative_luminance(mean) < 160)

        runs: list[tuple[int, int]] = []
        start: int | None = None
        for index, is_dark in enumerate(dark_rows):
            if is_dark and start is None:
                start = index
            elif not is_dark and start is not None:
                if index - start >= max(8, int(height * 0.05)):
                    runs.append((start, index))
                start = None
        if start is not None and height - start >= max(8, int(height * 0.05)):
            runs.append((start, height))

        for idx, (top, bottom) in enumerate(runs, start=1):
            xs: list[int] = []
            for x in range(width):
                column = image.crop((x, top, x + 1, bottom))
                stat = ImageStat.Stat(column)
                mean = tuple(int(value) for value in stat.mean[:3])
                if _relative_luminance(mean) < 115:
                    xs.append(x)
            if not xs:
                continue
            left = min(xs)
            right = max(xs) + 1
            if (right - left) / width < 0.25:
                continue
            x, y, w, h = _image_bbox_to_body(
                (
                    left / width * image_width,
                    top / height * image_height,
                    right / width * image_width,
                    bottom / height * image_height,
                ),
                image_width,
                image_height,
                body_region,
            )
            role = _container_role_from_plan(y, h, body_region, semantic_plan)
            containers.append(
                SemanticContainer(
                    id=f"{role}_{idx}",
                    role=role,
                    x=round(x, 2),
                    y=round(y, 2),
                    w=round(w, 2),
                    h=round(h, 2),
                    background="dark",
                    fill="#FFFFFF",
                    align="center",
                )
            )
    return containers


def _container_role_from_plan(
    y: float,
    h: float,
    body_region: dict[str, float],
    semantic_plan: SemanticPlan | None,
) -> str:
    body_y = float(body_region["y"])
    body_h = float(body_region["height"])
    center_ratio = ((y + h / 2) - body_y) / body_h if body_h else 0
    roles = {layer.role for layer in semantic_plan.layers} if semantic_plan else set()
    if center_ratio >= 0.68 and (not roles or "foundation_base" in roles):
        return "foundation_base"
    if 0.48 <= center_ratio < 0.68 and "support_system" in roles:
        return "support_system"
    return "dark_band"


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _snap_same_row_boxes(boxes: list[OverlayTextBox]) -> None:
    row_threshold = 8.0
    rows: list[list[OverlayTextBox]] = []
    for box in sorted(boxes, key=lambda item: item.y + item.h / 2):
        center_y = box.y + box.h / 2
        for row in rows:
            row_center = _median([item.y + item.h / 2 for item in row])
            if abs(center_y - row_center) <= row_threshold:
                row.append(box)
                break
        else:
            rows.append([box])

    for row in rows:
        if len(row) < 2:
            continue
        target_y = round(_median([box.y for box in row]), 2)
        target_size = round(max(box.font_size for box in row), 2)
        for box in row:
            box.y = target_y
            box.font_size = target_size


def _is_dark_base_title(box: OverlayTextBox, body_region: dict[str, float]) -> bool:
    body_y = float(body_region["y"])
    body_h = float(body_region["height"])
    center_y = box.y + box.h / 2
    lower_band_start = body_y + body_h * 0.68
    text_key = normalize_text(box.text)
    semantic_hit = any(keyword in text_key for keyword in ("底座", "数据空间", "平台"))
    return box.fill.upper() == "#FFFFFF" and center_y >= lower_band_start and semantic_hit


def _text_estimated_width(text: str, font_size: float) -> float:
    wide_count = sum(1 for char in text if ord(char) > 127)
    narrow_count = len(text) - wide_count
    return (wide_count * font_size) + (narrow_count * font_size * 0.56)


def _fit_font_size(text: str, width: float, preferred: float, minimum: float = 10.0) -> float:
    estimated = _text_estimated_width(text, preferred)
    if estimated <= width:
        return preferred
    if estimated <= 0:
        return preferred
    return max(minimum, preferred * width / estimated)


def _fit_all_boxes(boxes: list[OverlayTextBox]) -> None:
    for box in boxes:
        box.font_size = round(_fit_font_size(box.text, box.w * 0.96, box.font_size, minimum=7.0), 2)


def _container_for_box(box: OverlayTextBox, containers: list[SemanticContainer]) -> SemanticContainer | None:
    center_x = box.x + box.w / 2
    center_y = box.y + box.h / 2
    text_key = normalize_text(box.text)
    containing = [
        container
        for container in containers
        if container.x <= center_x <= container.x + container.w and container.y <= center_y <= container.y + container.h
        and container.role == "foundation_base"
        and any(keyword in text_key for keyword in ("底座", "数据空间", "平台"))
    ]
    if containing:
        return min(containing, key=lambda item: item.w * item.h)
    return None


def _apply_container_layout(box: OverlayTextBox, container: SemanticContainer) -> None:
    pad_x = 0.0 if container.role == "foundation_base" else min(20.0, max(4.0, container.w * 0.06))
    pad_y = min(8.0, max(2.0, container.h * 0.12))
    box.x = container.x + pad_x
    box.w = max(1.0, container.w - pad_x * 2)
    box.h = max(box.h, container.h - pad_y * 2)
    preferred_size = max(box.font_size, 16.0 if container.role == "foundation_base" else box.font_size)
    box.font_size = round(_fit_font_size(box.text, box.w, preferred_size, minimum=8.5), 2)
    box.y = round(container.y + (container.h - box.font_size) / 2, 2)
    box.fill = container.fill
    box.align = container.align
    if container.background == "dark":
        box.font_weight = "700" if container.role == "foundation_base" else box.font_weight


def _apply_semantic_overlay_layout(
    boxes: list[OverlayTextBox],
    body_region: dict[str, float],
    containers: list[SemanticContainer] | None = None,
) -> None:
    _snap_same_row_boxes(boxes)
    containers = containers or []
    for box in boxes:
        container = _container_for_box(box, containers)
        if container is not None:
            _apply_container_layout(box, container)
        elif _is_dark_base_title(box, body_region):
            box.x = float(body_region["x"])
            box.w = float(body_region["width"])
            box.align = "center"
            box.font_size = max(box.font_size, 16.0)
            box.font_weight = "700"
        elif len(box.text) <= 12 and box.w < 260:
            box.align = "center"
    _fit_all_boxes(boxes)


def build_overlay_boxes(
    script_path: Path,
    page_number: int,
    ocr_layout: dict[str, Any],
    body_region: dict[str, float],
    *,
    font_family: str = "Microsoft YaHei",
    fill: str = "#0B1F3D",
    background_image: Path | None = None,
    semantic_containers: list[SemanticContainer] | None = None,
    semantic_plan: SemanticPlan | None = None,
) -> list[OverlayTextBox]:
    script_lines = extract_script_truth_lines(script_path, page_number)
    image_size = ocr_layout.get("image_size") or {}
    image_width = float(image_size.get("width") or 1)
    image_height = float(image_size.get("height") or 1)
    sx = float(body_region["width"]) / image_width
    sy = float(body_region["height"]) / image_height
    boxes: list[OverlayTextBox] = []
    background = Image.open(background_image).convert("RGB") if background_image else None
    containers = (
        semantic_containers
        if semantic_containers is not None
        else infer_semantic_containers(background_image, ocr_layout, body_region, semantic_plan=semantic_plan)
        if background_image
        else []
    )
    try:
        for item in ocr_layout.get("items", []):
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            x1, y1, x2, y2 = [float(value) for value in item["bbox"]]
            corrected, source = match_script_text(text, script_lines)
            x = float(body_region["x"]) + x1 * sx
            y = float(body_region["y"]) + y1 * sy
            w = max(1.0, (x2 - x1) * sx)
            h = max(1.0, (y2 - y1) * sy)
            font_size = _font_size_from_box(h)
            text_fill = _fill_for_background(background, (x1, y1, x2, y2), image_width, image_height, fill)
            boxes.append(
                OverlayTextBox(
                    text=corrected,
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    font_size=font_size,
                    font_family=font_family,
                    fill=text_fill,
                    font_weight=_weight_for_text(corrected, h),
                    align="center" if len(corrected) <= 12 and w < 260 else "left",
                    word_wrap=True,
                    source=source,
                    confidence=float(item.get("confidence", 1.0)),
                )
            )
    finally:
        if background is not None:
            background.close()
    _apply_semantic_overlay_layout(boxes, body_region, containers)
    return boxes


def render_overlay_svg(
    *,
    background_href: str,
    canvas: dict[str, int],
    body_region: dict[str, float],
    slide_title: str,
    subtitle: str = "",
    text_boxes: list[OverlayTextBox],
) -> str:
    width = int(canvas["width"])
    height = int(canvas["height"])
    body = body_region
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>',
        f'<text x="{body["x"]}" y="46" font-family="Microsoft YaHei, Arial, sans-serif" font-size="25" font-weight="700" fill="#123B66">{html.escape(slide_title)}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="{body["x"]}" y="72" font-family="Microsoft YaHei, Arial, sans-serif" font-size="14" fill="#60758A">{html.escape(subtitle)}</text>'
        )
    parts.append(
        f'<image x="{body["x"]}" y="{body["y"]}" width="{body["width"]}" height="{body["height"]}" href="{html.escape(background_href)}" xlink:href="{html.escape(background_href)}" preserveAspectRatio="none"/>'
    )
    for box in text_boxes:
        anchor = {"center": "middle", "right": "end"}.get(box.align, "start")
        text_x = box.x + (box.w / 2 if box.align == "center" else box.w if box.align == "right" else 0)
        text_y = box.y + box.font_size
        parts.append(
            f'<text x="{text_x:.2f}" y="{text_y:.2f}" text-anchor="{anchor}" '
            f'font-family="{html.escape(box.font_family)}, Arial, sans-serif" '
            f'font-size="{box.font_size:.2f}" font-weight="{html.escape(box.font_weight)}" '
            f'fill="{html.escape(box.fill)}">{html.escape(box.text)}</text>'
        )
    parts.append("</svg>\n")
    return "\n".join(parts)


def boxes_to_json(boxes: list[OverlayTextBox]) -> list[dict[str, Any]]:
    return [asdict(box) for box in boxes]


def containers_to_json(containers: list[SemanticContainer]) -> list[dict[str, Any]]:
    return [asdict(container) for container in containers]


def semantic_plan_to_json(plan: SemanticPlan) -> dict[str, Any]:
    return asdict(plan)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build editable text overlay boxes from script truth and OCR layout.")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--page", required=True, type=int)
    parser.add_argument("--ocr-layout", required=True, type=Path)
    parser.add_argument("--body-region", required=True, help='JSON object, e.g. {"x":32,"y":98,"width":1216,"height":589}')
    parser.add_argument("-o", "--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        layout = json.loads(args.ocr_layout.read_text(encoding="utf-8"))
        body_region = json.loads(args.body_region)
        boxes = build_overlay_boxes(args.script, args.page, layout, body_region)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(boxes_to_json(boxes), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        print(args.out)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
