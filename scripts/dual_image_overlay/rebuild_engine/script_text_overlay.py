#!/usr/bin/env python3
"""Map script text truth onto OCR text boxes and render editable overlay SVG."""

from __future__ import annotations

import argparse
import html
import importlib.util
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


MIN_EXPORT_FONT_SIZE_PX = 12.0


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
    line = re.sub(r"^\*\*(.*?)\*\*$", r"\1", line)
    line = re.sub(r"^\*(.*?)\*$", r"\1", line)
    line = line.replace("**", "")
    line = line.strip("* ")
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


def extract_script_truth_sections(script_path: Path, page_number: int) -> dict[str, list[dict[str, Any]]]:
    pages = parse_page_blocks(script_path)
    if page_number not in pages:
        raise ValueError(f"Page {page_number} not found in script: {script_path}")
    content = extract_content(pages[page_number])
    sections: dict[str, list[dict[str, Any]]] = {}
    current_section = ""
    current_group: dict[str, Any] | None = None
    for raw_line in content.body.splitlines():
        line = raw_line.strip()
        if not line or line == "---":
            continue
        if line.startswith("### "):
            current_section = _clean_line(line[4:])
            sections.setdefault(current_section, [])
            current_group = None
            continue
        if line.startswith("## "):
            current_section = ""
            current_group = None
            continue
        if not current_section:
            continue
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if raw_line.strip().startswith("**") and raw_line.strip().endswith("**"):
            current_group = {"title": cleaned, "lines": []}
            sections.setdefault(current_section, []).append(current_group)
            continue
        if current_group is None:
            sections.setdefault(current_section, []).append({"title": "", "lines": [cleaned]})
        else:
            current_group.setdefault("lines", []).append(cleaned)
    return sections


def reconcile_semantic_plan_with_script_truth(plan: dict[str, Any], script_path: Path, page_number: int) -> dict[str, Any]:
    """Use script text as the final semantic truth for known structured containers."""
    reconciled = json.loads(json.dumps(plan, ensure_ascii=False))
    sections = extract_script_truth_sections(script_path, page_number)
    corrections: list[dict[str, Any]] = []

    def resolve_container_id(requested_id: str) -> str:
        for container in reconciled.get("containers", []):
            if not isinstance(container, dict):
                continue
            container_id = str(container.get("id") or "")
            aliases = [str(item) for item in container.get("aliases", []) if item]
            if container_id == requested_id or requested_id in aliases:
                return container_id
        return requested_id

    def replace_item_text(container_id: str, text: str, *, role: str = "body") -> None:
        container_id = resolve_container_id(container_id)
        for item in reconciled.get("items", []):
            if not isinstance(item, dict) or str(item.get("container_id") or "") != container_id:
                continue
            old = str(item.get("display_text") or item.get("text") or "")
            if normalize_text(old) != normalize_text(text):
                item["display_text"] = text
                item["source_text"] = text
                item["role"] = role
                item["word_wrap"] = True
                item["script_truth_reconciled"] = True
                corrections.append({"container_id": container_id, "old_text": old, "new_text": text})
            return
        reconciled.setdefault("items", []).append(
            {
                "display_text": text,
                "source_text": text,
                "role": role,
                "container_id": container_id,
                "word_wrap": True,
                "script_truth_reconciled": True,
            }
        )
        corrections.append({"container_id": container_id, "old_text": "", "new_text": text})

    app_groups = _section_groups_by_title(sections, "右侧", "结果应用方")
    for index, group in enumerate(app_groups[:3], start=1):
        title = str(group.get("title") or "").strip()
        parts = _split_script_items(group.get("lines", []))
        if title and parts:
            replace_item_text(f"application_{index}", title + "\n" + "\n".join(f"• {part}" for part in parts))

    governance_groups = _section_groups_by_title(sections, "右侧竖条", "安全合规")
    governance_parts: list[str] = []
    for group in governance_groups:
        governance_parts.extend(_split_script_items(group.get("lines", [])))
    for index, label in enumerate(governance_parts[:6], start=1):
        replace_item_text(f"governance_{index}", label)

    if corrections:
        reconciled.setdefault("reconciliation", {})["script_truth"] = {
            "source": str(script_path),
            "page_number": page_number,
            "corrections": corrections,
        }
        inputs = reconciled.setdefault("inputs", {})
        if isinstance(inputs, dict):
            inputs["text_truth"] = "script_truth_reconciled"
    return reconciled


def _section_groups_by_title(sections: dict[str, list[dict[str, Any]]], *title_fragments: str) -> list[dict[str, Any]]:
    for title, groups in sections.items():
        if all(fragment in title for fragment in title_fragments):
            return [group for group in groups if isinstance(group, dict)]
    return []


def _split_script_items(lines: Any) -> list[str]:
    items: list[str] = []
    for line in lines if isinstance(lines, list) else []:
        for part in re.split(r"[、，,|｜]", str(line)):
            cleaned = _clean_line(part)
            if cleaned:
                items.append(cleaned)
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        key = normalize_text(item)
        if key and key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def _flow_nodes_from_script_sections(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    groups = sections.get("主链节点")
    if not isinstance(groups, list):
        return []
    nodes: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for group in groups:
        if not isinstance(group, dict):
            continue
        lines = group.get("lines")
        if not isinstance(lines, list):
            continue
        for raw in lines:
            line = _clean_line(str(raw))
            if not line:
                continue
            match = re.match(r"^(\d+)\.\s*(.+)$", line)
            if match:
                current = {"number": match.group(1), "title": match.group(2).strip(), "body": ""}
                nodes.append(current)
            elif current is not None and not current["body"]:
                current["body"] = line
    return [node for node in nodes if node.get("number") and node.get("title") and node.get("body")]


def _build_main_flow_overlay_boxes(
    *,
    script_path: Path,
    page_number: int,
    ocr_layout: dict[str, Any],
    body_region: dict[str, float],
    font_family: str,
    fill: str,
    background: Image.Image | None,
) -> list[OverlayTextBox]:
    try:
        nodes = _flow_nodes_from_script_sections(extract_script_truth_sections(script_path, page_number))
    except ValueError:
        return []
    if len(nodes) != 10:
        return []

    items = [item for item in ocr_layout.get("items", []) if isinstance(item, dict)]
    image_size = ocr_layout.get("image_size") or {}
    image_width = float(image_size.get("width") or 1)
    image_height = float(image_size.get("height") or 1)
    sx = float(body_region["width"]) / image_width
    sy = float(body_region["height"]) / image_height

    number_centers: list[tuple[int, float, float]] = []
    for item in items:
        text = str(item.get("text") or "").strip()
        if not re.fullmatch(r"\d{1,2}", text):
            continue
        number = int(text)
        if not 1 <= number <= 10:
            continue
        x1, y1, x2, y2 = [float(value) for value in item.get("bbox", [])]
        number_centers.append((number, (x1 + x2) / 2, (y1 + y2) / 2))
    number_centers.sort(key=lambda item: item[0])
    if len(number_centers) < 10:
        return []

    centers = [center for _, center, _ in number_centers[:10]]
    first_gap = centers[1] - centers[0]
    last_gap = centers[-1] - centers[-2]
    boundaries = [max(18.0, centers[0] - first_gap / 2)]
    boundaries.extend((centers[index] + centers[index + 1]) / 2 for index in range(9))
    boundaries.append(min(image_width - 18.0, centers[-1] + last_gap / 2))

    flow_top = min(item[2] for item in number_centers[:10])
    title_top = max(flow_top + 120.0, 246.0)
    title_h = 34.0
    body_top = title_top + title_h + 10.0
    body_bottom = min(image_height - 150.0, max(body_top + 150.0, 520.0))

    boxes: list[OverlayTextBox] = []

    def slide_box(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float, float, float]:
        return (
            float(body_region["x"]) + x1 * sx,
            float(body_region["y"]) + y1 * sy,
            max(1.0, (x2 - x1) * sx),
            max(1.0, (y2 - y1) * sy),
        )

    for index, node in enumerate(nodes):
        left = boundaries[index] + 8.0
        right = boundaries[index + 1] - 8.0
        center = centers[index]
        num_x, num_y, num_w, num_h = slide_box(center - 13.0, flow_top - 8.0, center + 13.0, flow_top + 24.0)
        boxes.append(
            OverlayTextBox(
                text=node["number"],
                x=num_x,
                y=num_y,
                w=num_w,
                h=num_h,
                font_size=13.0,
                font_family=font_family,
                fill="#FFFFFF",
                font_weight="700",
                align="center",
                word_wrap=False,
                source="script_main_flow_fallback",
                confidence=1.0,
            )
        )

        title_x, title_y, title_w, title_box_h = slide_box(left, title_top, right, title_top + title_h)
        boxes.append(
            OverlayTextBox(
                text=f'{node["number"]}. {node["title"]}',
                x=title_x,
                y=title_y,
                w=title_w,
                h=title_box_h,
                font_size=10.5,
                font_family=font_family,
                fill=fill,
                font_weight="700",
                align="center",
                word_wrap=True,
                source="script_main_flow_fallback",
                confidence=1.0,
            )
        )

        body_x, body_y, body_w, body_h = slide_box(left, body_top, right, body_bottom)
        text_fill = _fill_for_background(background, (left, body_top, right, body_bottom), image_width, image_height, fill)
        boxes.append(
            OverlayTextBox(
                text=node["body"],
                x=body_x,
                y=body_y,
                w=body_w,
                h=body_h,
                font_size=10.5,
                font_family=font_family,
                fill=text_fill,
                font_weight="400",
                align="left",
                word_wrap=True,
                source="script_main_flow_fallback",
                confidence=1.0,
            )
        )
    return boxes


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


def _font_size_from_box(height: float, text: str = "", source: str = "") -> float:
    if source.startswith("manual_source_faithful"):
        line_count = max(1, len(str(text).splitlines()))
        if line_count > 1:
            return max(6.5, min(14.0, (height / line_count) * 0.82))
    return max(MIN_EXPORT_FONT_SIZE_PX, min(28.0, height * 0.62))


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
    estimated = max(_text_estimated_width(line, preferred) for line in str(text).splitlines() or [""])
    if estimated <= width:
        return preferred
    if estimated <= 0:
        return preferred
    return max(minimum, preferred * width / estimated)


def _estimated_line_count(text: str, width: float, font_size: float, *, word_wrap: bool) -> int:
    lines = str(text).splitlines() or [str(text)]
    if not word_wrap:
        return max(1, len(lines))
    count = 0
    for line in lines:
        estimated = _text_estimated_width(line, font_size)
        count += max(1, int((estimated + max(width, 1.0) - 1) // max(width, 1.0)))
    return count


def _fit_font_size_to_box(
    text: str,
    width: float,
    height: float,
    preferred: float,
    *,
    minimum: float,
    word_wrap: bool,
) -> float:
    size = preferred if word_wrap else _fit_font_size(text, width * 0.96, preferred, minimum=minimum)
    while size > minimum:
        line_count = _estimated_line_count(text, width * 0.96, size, word_wrap=word_wrap)
        estimated_height = line_count * size * 1.18
        if estimated_height <= height * 0.96:
            break
        next_size = max(minimum, size - 0.5)
        if next_size == size:
            break
        size = next_size
    return size


def _fit_all_boxes(boxes: list[OverlayTextBox]) -> None:
    for box in boxes:
        minimum = 6.5 if box.source.startswith("manual_source_faithful") else MIN_EXPORT_FONT_SIZE_PX
        box.font_size = round(
            _fit_font_size_to_box(
                box.text,
                box.w,
                box.h,
                box.font_size,
                minimum=minimum,
                word_wrap=box.word_wrap,
            ),
            2,
        )


def _repeated_body_text_candidates(boxes: list[OverlayTextBox], body_region: dict[str, float]) -> list[OverlayTextBox]:
    body_y = float(body_region["y"])
    body_h = float(body_region["height"])
    middle_top = body_y + body_h * 0.24
    middle_bottom = body_y + body_h * 0.82
    return [
        box
        for box in boxes
        if not box.source.startswith("manual_source_faithful")
        and box.word_wrap
        and box.align == "left"
        and box.fill.strip().upper() != "#FFFFFF"
        and len(normalize_text(box.text)) >= 10
        and middle_top <= box.y + box.h / 2 <= middle_bottom
    ]


def _group_repeated_body_columns(boxes: list[OverlayTextBox]) -> list[list[OverlayTextBox]]:
    column_threshold = 42.0
    columns: list[list[OverlayTextBox]] = []
    for box in sorted(boxes, key=lambda item: item.x):
        for column in columns:
            column_x = _median([item.x for item in column])
            if abs(box.x - column_x) <= column_threshold:
                column.append(box)
                break
        else:
            columns.append([box])
    return [sorted(column, key=lambda item: item.y + item.h / 2) for column in columns]


def _snap_repeated_column_body_rows(boxes: list[OverlayTextBox], body_region: dict[str, float]) -> None:
    columns = _group_repeated_body_columns(_repeated_body_text_candidates(boxes, body_region))
    columns = [column for column in columns if len(column) >= 2]
    if len(columns) < 3:
        return

    row_count = max(len(column) for column in columns)
    for row_index in range(row_count):
        row = [column[row_index] for column in columns if row_index < len(column)]
        if len(row) < 3:
            continue
        centers = [box.y + box.h / 2 for box in row]
        if max(centers) - min(centers) > 48.0:
            continue
        target_y = round(_median([box.y for box in row]), 2)
        target_size = round(max(box.font_size for box in row), 2)
        for box in row:
            box.y = target_y
            box.font_size = target_size


def _relax_repeated_body_text_lanes(boxes: list[OverlayTextBox], body_region: dict[str, float]) -> None:
    body_right = float(body_region["x"]) + float(body_region["width"])
    candidates = _repeated_body_text_candidates(boxes, body_region)
    if len(candidates) < 3:
        return

    column_threshold = 42.0
    columns = _group_repeated_body_columns(candidates)
    if len(columns) < 2:
        return

    column_lefts = [_median([box.x for box in column]) for column in columns]
    pitches = [
        right - left
        for left, right in zip(column_lefts, column_lefts[1:])
        if right - left > column_threshold
    ]
    if not pitches:
        return

    base_lane_width = min(220.0, max(170.0, _median(pitches) * 0.68))
    for index, column in enumerate(columns):
        column_x = column_lefts[index]
        next_x = column_lefts[index + 1] if index + 1 < len(column_lefts) else body_right
        max_lane_width = max(1.0, next_x - column_x - 24.0)
        target_width = min(base_lane_width, max_lane_width)
        for box in column:
            line_count = _estimated_line_count(box.text, box.w * 0.96, box.font_size, word_wrap=True)
            if line_count <= 1:
                continue
            box.w = round(max(box.w, target_width), 2)


BODY_TEXT_ROLES = {"body", "bullet", "list_item", "stage_body", "trust_body", "service_item", "summary"}
TITLE_TEXT_ROLES = {"title", "stage_label", "section_title", "card_title", "ability_title"}
INDEX_TEXT_ROLES = {"index", "number", "step_number"}
TEXT_ZONE_ELEMENT_TYPES = {"text_zone", "label_zone", "text_safe_zone"}
CONTAINER_LIKE_ELEMENT_TYPES = {
    "core_capability_cell",
    "object_pool",
    "object_pool_cell",
    "application_card",
    "application_panel",
    "source_card",
    "governance_spine",
    "service_segment",
    "service_value_bar",
}
RESERVED_ELEMENT_TYPES = {
    "icon",
    "flow_arrow",
    "feedback_connector",
    "connector",
    "arrow",
    "badge",
    "decorative",
}
ICON_AWARE_CONTAINER_ROLES = {
    "source_card",
    "application_card",
    "governance_step",
    "service_segment",
    "object_pool_cell",
}


def _size_dict(width: float, height: float) -> dict[str, float]:
    return {"width": round(float(width), 2), "height": round(float(height), 2)}


def _declared_plan_size(plan: dict[str, Any]) -> dict[str, float] | None:
    image_size = plan.get("image_size") if isinstance(plan.get("image_size"), dict) else {}
    try:
        width = float(image_size.get("width") or 0)
        height = float(image_size.get("height") or 0)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return _size_dict(width, height)


def _normalization_coordinate_space(plan: dict[str, Any]) -> dict[str, float] | None:
    normalization = plan.get("coordinate_normalization") if isinstance(plan.get("coordinate_normalization"), dict) else {}
    coordinate_space = normalization.get("coordinate_space") if isinstance(normalization.get("coordinate_space"), dict) else {}
    try:
        width = float(coordinate_space.get("width") or 0)
        height = float(coordinate_space.get("height") or 0)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return _size_dict(width, height)


def _registry_canvas_size(visual_registry: dict[str, Any] | None) -> dict[str, float] | None:
    if not visual_registry:
        return None
    canvas = visual_registry.get("blueprint_canvas_px") if isinstance(visual_registry.get("blueprint_canvas_px"), dict) else {}
    try:
        width = float(canvas.get("w") or canvas.get("width") or 0)
        height = float(canvas.get("h") or canvas.get("height") or 0)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return _size_dict(width, height)


def _bbox_extent_size(objects: list[Any], fields: tuple[str, ...]) -> dict[str, float] | None:
    max_x = 0.0
    max_y = 0.0
    found = False
    for item in objects:
        if not isinstance(item, dict):
            continue
        for field in fields:
            bbox = _as_xyxy(item.get(field))
            if bbox is None:
                continue
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])
            found = True
    if not found or max_x <= 0 or max_y <= 0:
        return None
    return _size_dict(max_x, max_y)


def _registry_extent_size(visual_registry: dict[str, Any] | None) -> dict[str, float] | None:
    if not visual_registry:
        return None
    max_x = 0.0
    max_y = 0.0
    found = False
    for element in visual_registry.get("elements", []):
        if not isinstance(element, dict):
            continue
        raw = element.get("blueprint_bbox_px")
        if isinstance(raw, dict):
            try:
                x = float(raw.get("x") or 0)
                y = float(raw.get("y") or 0)
                w = float(raw.get("w") or raw.get("width") or 0)
                h = float(raw.get("h") or raw.get("height") or 0)
            except (TypeError, ValueError):
                continue
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
            found = True
            continue
        bbox = _as_xyxy(raw)
        if bbox is not None:
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])
            found = True
    if not found or max_x <= 0 or max_y <= 0:
        return None
    return _size_dict(max_x, max_y)


def _choose_semantic_input_space(
    *,
    plan: dict[str, Any],
    plan_size: dict[str, float] | None,
    actual_size: dict[str, float] | None,
    registry_size: dict[str, float] | None,
    plan_extent: dict[str, float] | None,
    registry_extent: dict[str, float] | None,
    warnings: list[dict[str, Any]],
) -> dict[str, float]:
    fallback = actual_size or registry_size or plan_size or _size_dict(1280, 720)
    normalized_space = _normalization_coordinate_space(plan)
    if plan_size and normalized_space and _sizes_close(plan_size, normalized_space):
        return plan_size
    if plan_size and registry_size and registry_extent and (
        float(registry_extent["width"]) > float(registry_size["width"]) + 2.0
        or float(registry_extent["height"]) > float(registry_size["height"]) + 2.0
    ):
        if float(registry_extent["width"]) <= float(plan_size["width"]) + 2.0 and float(
            registry_extent["height"]
        ) <= float(plan_size["height"]) + 2.0:
            warnings.append(
                {
                    "code": "semantic_coordinate_space_follows_registry_extent",
                    "semantic_plan_image_size": plan_size,
                    "visual_registry_canvas": registry_size,
                    "registry_bbox_extent": registry_extent,
                    "resolved_semantic_input_space": plan_size,
                }
            )
            return plan_size
    if plan_size and plan_extent:
        if actual_size and (
            float(plan_extent["width"]) > float(actual_size["width"]) + 2.0
            or float(plan_extent["height"]) > float(actual_size["height"]) + 2.0
        ):
            warnings.append(
                {
                    "code": "semantic_coordinate_space_uses_plan_extent",
                    "semantic_plan_image_size": plan_size,
                    "background_image_actual": actual_size,
                    "semantic_bbox_extent": plan_extent,
                    "resolved_semantic_input_space": plan_size,
                }
            )
            return plan_size
    return fallback


def _choose_registry_input_space(
    *,
    visual_registry: dict[str, Any] | None,
    registry_size: dict[str, float] | None,
    registry_extent: dict[str, float] | None,
    semantic_input_space: dict[str, float],
    warnings: list[dict[str, Any]],
) -> dict[str, float]:
    if not visual_registry:
        return semantic_input_space
    if registry_size and registry_extent and (
        float(registry_extent["width"]) > float(registry_size["width"]) + 2.0
        or float(registry_extent["height"]) > float(registry_size["height"]) + 2.0
    ):
        if float(registry_extent["width"]) <= float(semantic_input_space["width"]) + 2.0 and float(
            registry_extent["height"]
        ) <= float(semantic_input_space["height"]) + 2.0:
            warnings.append(
                {
                    "code": "visual_registry_canvas_metadata_stale",
                    "visual_registry_canvas": registry_size,
                    "registry_bbox_extent": registry_extent,
                    "resolved_visual_registry_input_space": semantic_input_space,
                }
            )
            return semantic_input_space
        inferred = _size_dict(
            max(float(registry_extent["width"]), float(registry_size["width"])),
            max(float(registry_extent["height"]), float(registry_size["height"])),
        )
        warnings.append(
            {
                "code": "visual_registry_canvas_metadata_stale",
                "visual_registry_canvas": registry_size,
                "registry_bbox_extent": registry_extent,
                "resolved_visual_registry_input_space": inferred,
            }
        )
        return inferred
    return registry_size or semantic_input_space


def _background_image_size(background_image: Path | None) -> dict[str, float] | None:
    if background_image is None:
        return None
    with Image.open(background_image) as image:
        width, height = image.size
    if width <= 0 or height <= 0:
        return None
    return _size_dict(width, height)


def _sizes_close(a: dict[str, float] | None, b: dict[str, float] | None, *, tolerance: float = 2.0) -> bool:
    if not a or not b:
        return False
    return abs(float(a["width"]) - float(b["width"])) <= tolerance and abs(float(a["height"]) - float(b["height"])) <= tolerance


def resolve_overlay_coordinate_context(
    plan: dict[str, Any],
    *,
    visual_registry: dict[str, Any] | None = None,
    background_image: Path | None = None,
) -> dict[str, Any]:
    """Resolve the single source coordinate space used by semantic layout.

    ppt-master avoids drift by normalizing everything at ingress. CyberPPT keeps
    the template body region, so this context makes the equivalent decision
    explicit before any registry or safe-area math runs.
    """
    plan_size = _declared_plan_size(plan)
    registry_size = _registry_canvas_size(visual_registry)
    plan_extent = _bbox_extent_size(
        [*([item for item in plan.get("containers", [])] if isinstance(plan.get("containers"), list) else []), *([item for item in plan.get("items", [])] if isinstance(plan.get("items"), list) else [])],
        ("bbox", "text_safe_bbox"),
    )
    registry_extent = _registry_extent_size(visual_registry)
    actual_size = _background_image_size(background_image)
    warnings: list[dict[str, Any]] = []

    semantic_input_space = _choose_semantic_input_space(
        plan=plan,
        plan_size=plan_size,
        actual_size=actual_size,
        registry_size=registry_size,
        plan_extent=plan_extent,
        registry_extent=registry_extent,
        warnings=warnings,
    )
    registry_input_space = _choose_registry_input_space(
        visual_registry=visual_registry,
        registry_size=registry_size,
        registry_extent=registry_extent,
        semantic_input_space=semantic_input_space,
        warnings=warnings,
    )
    source_space = actual_size or semantic_input_space
    coordinate_space = _size_dict(1280, 720)
    source = "normalized_1280x720"

    for name, size in (("semantic_plan_image_size", plan_size), ("visual_registry_canvas", registry_size)):
        if size and not _sizes_close(size, coordinate_space):
            warnings.append(
                {
                    "code": "coordinate_space_mismatch",
                    "source": name,
                    "declared_size": size,
                    "source_coordinate_space": semantic_input_space,
                    "resolved_coordinate_space": coordinate_space,
                }
            )

    return {
        "schema": "cyberppt.dual_image.coordinate_context.v1",
        "coordinate_space": coordinate_space,
        "coordinate_space_source": source,
        "source_coordinate_space": source_space,
        "semantic_input_space": semantic_input_space,
        "visual_registry_input_space": registry_input_space,
        "semantic_plan_image_size": plan_size,
        "visual_registry_canvas": registry_size,
        "semantic_bbox_extent": plan_extent,
        "visual_registry_bbox_extent": registry_extent,
        "background_image_actual": actual_size,
        "warnings": warnings,
    }


def _scale_xyxy_between(bbox: list[float], source: dict[str, float], target: dict[str, float]) -> list[float]:
    sx = float(target["width"]) / float(source["width"])
    sy = float(target["height"]) / float(source["height"])
    return [bbox[0] * sx, bbox[1] * sy, bbox[2] * sx, bbox[3] * sy]


def _normalize_bbox_to_context(
    bbox: list[float],
    input_space: dict[str, float],
    coordinate_context: dict[str, Any],
) -> list[float]:
    target = coordinate_context.get("coordinate_space")
    if not isinstance(target, dict) or _sizes_close(input_space, target):
        return bbox
    return _scale_xyxy_between(bbox, input_space, target)


def normalize_semantic_plan_to_context(plan: dict[str, Any], coordinate_context: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(plan, ensure_ascii=False))
    input_space = coordinate_context.get("semantic_input_space")
    if not isinstance(input_space, dict):
        return normalized

    def normalize_field(owner: dict[str, Any], field: str) -> None:
        bbox = _as_xyxy(owner.get(field))
        if bbox is not None:
            owner[field] = _round_xyxy(_normalize_bbox_to_context(bbox, input_space, coordinate_context))

    for container in normalized.get("containers", []):
        if not isinstance(container, dict):
            continue
        normalize_field(container, "bbox")
        normalize_field(container, "text_safe_bbox")
        for zone in container.get("reserved_zones", []):
            if isinstance(zone, dict):
                normalize_field(zone, "bbox")
    for item in normalized.get("items", []):
        if isinstance(item, dict):
            normalize_field(item, "bbox")
    normalized["image_size"] = dict(coordinate_context["coordinate_space"])
    normalized["coordinate_normalization"] = {
        "input_space": input_space,
        "coordinate_space": coordinate_context["coordinate_space"],
        "method": "scale_xyxy_to_normalized_canvas",
    }
    return normalized


def normalize_semantic_plan_to_canvas(plan: dict[str, Any], input_space: dict[str, Any]) -> dict[str, Any]:
    coordinate_context = {
        "semantic_input_space": _size_dict(float(input_space["width"]), float(input_space["height"])),
        "coordinate_space": _size_dict(1280, 720),
    }
    return normalize_semantic_plan_to_context(plan, coordinate_context)


def _normalize_semantic_plan_to_context(plan: dict[str, Any], coordinate_context: dict[str, Any]) -> dict[str, Any]:
    return normalize_semantic_plan_to_context(plan, coordinate_context)


def _semantic_issue(
    severity: str,
    code: str,
    *,
    item_index: int | None = None,
    container_id: str | None = None,
    message: str,
    recommended_action: str,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "item_index": item_index,
        "container_id": container_id,
        "message": message,
        "recommended_action": recommended_action,
    }


def validate_explicit_semantic_plan(plan: dict[str, Any] | None, *, required: bool = True) -> dict[str, Any]:
    """Validate the production semantic-container contract for dual-image rebuilds."""
    issues: list[dict[str, Any]] = []
    if not plan:
        if not required:
            report = _semantic_validation_report(issues)
            report["status"] = "skipped_optional"
            return report
        issues.append(
            _semantic_issue(
                "error",
                "missing_semantic_plan",
                message="No explicit semantic plan was supplied.",
                recommended_action="Provide semantic_plan.containers[] and items[].container_id before production export.",
            )
        )
        return _semantic_validation_report(issues)

    inputs = plan.get("inputs") if isinstance(plan.get("inputs"), dict) else {}
    geometry_truth = str(plan.get("geometry_truth") or inputs.get("geometry_truth") or "semantic_containers")
    text_truth = str(plan.get("text_truth") or inputs.get("text_truth") or "semantic_display_text")
    if geometry_truth in {"ocr", "ocr_bbox", "text_layout"}:
        issues.append(
            _semantic_issue(
                "error",
                "ocr_geometry_truth_forbidden",
                message="OCR/text-layout bbox is locator evidence, not production geometry truth.",
                recommended_action="Set geometry_truth to semantic_containers and provide container safe areas.",
            )
        )
    if not any(inputs.get(key) for key in ("script_truth", "evidence_chain", "source_capture", "visual_element_registry")):
        issues.append(
            _semantic_issue(
                "warning",
                "semantic_sources_not_declared",
                message="Semantic plan does not declare script/evidence/source-capture inputs.",
                recommended_action="Record available upstream truth sources so OCR is not mistaken for semantic truth.",
            )
        )

    containers_raw = plan.get("containers")
    items_raw = plan.get("items")
    containers = [item for item in containers_raw if isinstance(item, dict)] if isinstance(containers_raw, list) else []
    items = [item for item in items_raw if isinstance(item, dict)] if isinstance(items_raw, list) else []
    if not containers:
        issues.append(
            _semantic_issue(
                "error",
                "missing_containers",
                message="semantic_plan.containers[] is required for production geometry.",
                recommended_action="Declare visual containers with id, role, bbox, and optional text_safe_bbox.",
            )
        )
    if not items:
        issues.append(
            _semantic_issue(
                "error",
                "missing_items",
                message="semantic_plan.items[] is required for editable text.",
                recommended_action="Declare each visible text item with display_text/source_text, role, and container_id.",
            )
        )

    container_by_id = {str(item.get("id") or ""): item for item in containers}
    for index, item in enumerate(items):
        container_id = str(item.get("container_id") or "")
        container = container_by_id.get(container_id)
        role = str(item.get("role") or "")
        if not container:
            issues.append(
                _semantic_issue(
                    "error",
                    "missing_container",
                    item_index=index,
                    container_id=container_id,
                    message=f"Item {index} references a missing container.",
                    recommended_action="Add the container or correct item.container_id.",
                )
            )
            continue
        if str(container.get("role") or "") == "isolated_text_region" and role in BODY_TEXT_ROLES:
            issues.append(
                _semantic_issue(
                    "error",
                    "body_in_isolated_region",
                    item_index=index,
                    container_id=container_id,
                    message="Body text cannot be accepted in an isolated fallback region.",
                    recommended_action="Assign the item to an explicit semantic container and safe area.",
                )
            )
        if not str(item.get("display_text") or item.get("text") or "").strip():
            issues.append(
                _semantic_issue(
                    "error",
                    "missing_display_text",
                    item_index=index,
                    container_id=container_id,
                    message="Visible text item has no display_text.",
                    recommended_action="Set display_text from semantic truth before rendering.",
                )
            )
        safe_bbox = container.get("text_safe_bbox") or container.get("bbox")
        item_bbox = item.get("bbox")
        if isinstance(item_bbox, list) and len(item_bbox) == 4 and isinstance(safe_bbox, list) and len(safe_bbox) == 4:
            if not _bbox_inside_xyxy([float(v) for v in item_bbox], [float(v) for v in safe_bbox], tolerance=6.0):
                issues.append(
                    _semantic_issue(
                        "warning",
                        "item_bbox_outside_container_safe_bbox",
                        item_index=index,
                        container_id=container_id,
                        message="Item bbox is outside its semantic container safe area; layout plan may override it.",
                        recommended_action="Prefer relative_bbox or container-role slot layout over raw OCR bbox.",
                    )
                )
    return _semantic_validation_report(issues)


def _semantic_validation_report(issues: list[dict[str, Any]]) -> dict[str, Any]:
    error_count = sum(1 for item in issues if item.get("severity") == "error")
    warning_count = sum(1 for item in issues if item.get("severity") == "warning")
    return {
        "schema": "cyberppt.dual_image.semantic_plan_gate.v1",
        "valid": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues,
    }


def _bbox_inside_xyxy(box: list[float], safe: list[float], *, tolerance: float = 0.0) -> bool:
    return (
        box[0] >= safe[0] - tolerance
        and box[1] >= safe[1] - tolerance
        and box[2] <= safe[2] + tolerance
        and box[3] <= safe[3] + tolerance
    )


def enrich_semantic_plan_with_visual_registry(
    plan: dict[str, Any],
    visual_registry: dict[str, Any] | None = None,
    *,
    coordinate_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach registry-derived text zones and icon/shape reserved zones to semantic containers."""
    if not visual_registry:
        return json.loads(json.dumps(plan, ensure_ascii=False))

    coordinate_context = coordinate_context or resolve_overlay_coordinate_context(plan, visual_registry=visual_registry)
    enriched = _normalize_semantic_plan_to_context(
        json.loads(json.dumps(plan, ensure_ascii=False)),
        coordinate_context,
    )
    containers = [item for item in enriched.get("containers", []) if isinstance(item, dict)]
    registry_elements = [
        _registry_element_record(item, enriched, visual_registry, coordinate_context=coordinate_context)
        for item in visual_registry.get("elements", [])
        if isinstance(item, dict)
    ]
    registry_elements = [item for item in registry_elements if item is not None]
    for container in containers:
        container_bbox = _as_xyxy(container.get("bbox"))
        if container_bbox is None:
            continue
        child_elements = [
            element
            for element in registry_elements
            if _element_belongs_to_container(element, container, container_bbox)
        ]
        text_zones = [
            element for element in child_elements if str(element.get("element_type") or "") in TEXT_ZONE_ELEMENT_TYPES
        ]
        reserved = [
            element
            for element in child_elements
            if str(element.get("element_type") or "") in RESERVED_ELEMENT_TYPES
            and _registry_zone_intersects_text_region(element, container_bbox, text_zones)
        ]
        container_role = str(container.get("role") or "")
        has_explicit_safe = isinstance(container.get("text_safe_bbox"), list) and len(container.get("text_safe_bbox", [])) == 4
        if text_zones:
            container["registry_text_zones"] = [
                {
                    "element_id": element.get("element_id"),
                    "bbox": _round_xyxy(element["bbox"]),
                    "element_type": element.get("element_type"),
                }
                for element in text_zones
            ]
        if child_elements:
            container["registry_child_elements"] = [
                {
                    "element_id": element.get("element_id"),
                    "element_type": element.get("element_type"),
                    "source_component_id": element.get("source_component_id"),
                    "bbox": _round_xyxy(element["bbox"]),
                    "relation": "contained_or_component_matched",
                }
                for element in child_elements
            ]
        if text_zones and not has_explicit_safe and container_role not in {"ability_card", "capability_card"}:
            text_safe = _union_bbox([element["bbox"] for element in text_zones])
            container["text_safe_bbox"] = _round_xyxy(_expand_bbox_within(text_safe, container_bbox, x=4.0, y=3.0))
            container["text_zone_source"] = "visual_element_registry"
        elif not isinstance(container.get("text_safe_bbox"), list):
            container["text_safe_bbox"] = _round_xyxy(_inset_xyxy(container_bbox, 10.0, 8.0, 10.0, 8.0))
            container["text_zone_source"] = "container_inset_default"
        if reserved:
            existing = [zone for zone in container.get("reserved_zones", []) if isinstance(zone, dict)]
            existing_keys = {str(zone.get("source_element_id") or zone.get("name") or "") for zone in existing}
            for element in reserved:
                key = str(element.get("element_id") or "")
                if key in existing_keys:
                    continue
                existing.append(
                    {
                        "name": _reserved_zone_name(element),
                        "bbox": _round_xyxy(element["bbox"]),
                        "source_element_id": key,
                        "element_type": element.get("element_type"),
                    }
                )
            container["reserved_zones"] = existing
    return enriched


def build_semantic_layout_plan(
    plan: dict[str, Any],
    *,
    visual_registry: dict[str, Any] | None = None,
    coordinate_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build container-first text placement before rendering editable boxes."""
    coordinate_context = coordinate_context or resolve_overlay_coordinate_context(plan, visual_registry=visual_registry)
    effective_plan = enrich_semantic_plan_with_visual_registry(
        plan,
        visual_registry,
        coordinate_context=coordinate_context,
    )
    containers = {str(item.get("id") or ""): item for item in effective_plan.get("containers", []) if isinstance(item, dict)}
    items = [item for item in effective_plan.get("items", []) if isinstance(item, dict)]
    by_container: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, item in enumerate(items):
        by_container.setdefault(str(item.get("container_id") or ""), []).append((index, item))

    planned: list[dict[str, Any]] = []
    for container_id, entries in by_container.items():
        container = containers.get(container_id, {})
        role = str(container.get("role") or "")
        if role in {"ability_card", "capability_card"}:
            planned.extend(_plan_ability_card(container_id, container, entries))
        else:
            planned.extend(_plan_generic_container(container_id, container, entries))
    planned.sort(key=lambda item: int(item["index"]))
    planned = _apply_ppt_master_core_layout(planned)
    return {
        "schema": "cyberppt.dual_image.semantic_layout_plan.v1",
        "layout_policy": "semantic_container_safe_bbox_first",
        "ppt_master_core_policy": "container_role_and_text_role_first",
        "coordinate_context": coordinate_context,
        "truth_policy": {
            "geometry_truth": "semantic_plan.containers[].text_safe_bbox",
            "text_truth": "semantic_plan.items[].display_text",
            "ocr_role": "locator_evidence_only",
        },
        "container_relations": _semantic_container_relations(containers),
        "text_neighbors": _semantic_text_neighbors(planned, containers),
        "items": planned,
    }


def _apply_ppt_master_core_layout(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run the copied ppt-master layout core over CyberPPT semantic items."""
    ppt_master_core = _load_vendored_ppt_master_core()
    if ppt_master_core is None:
        return items
    core_items: list[dict[str, Any]] = []
    for item in items:
        safe = item.get("container_safe_bbox")
        core_items.append(
            {
                "text": item.get("text"),
                "display_text": item.get("text"),
                "source_text": item.get("source_text"),
                "role": item.get("role"),
                "bbox": item.get("bbox"),
                "font_size": item.get("font_size"),
                "font_weight": item.get("font_weight"),
                "fill": item.get("fill"),
                "align": item.get("align"),
                "word_wrap": item.get("word_wrap"),
                "container_id": item.get("container_id"),
                "container_role": item.get("container_role"),
                "container_bbox": safe,
                "container_text_safe_bbox": safe,
                "container_has_text_safe_bbox": True,
                "container_reserved_zones": item.get("reserved_zones") or [],
                "container_safe_bbox": safe,
                "reserved_zones": item.get("reserved_zones") or [],
                "layout_hints": item.get("layout_hints") or {},
                "lock_bbox": True,
                "container_fit": True,
            }
        )
    try:
        core_layout = {"image_size": {"width": 1280, "height": 720}, "items": core_items}
        core_plan = ppt_master_core.build_layout_plan(core_layout)
        applied = ppt_master_core.apply_layout_plan(core_layout, core_plan)
    except Exception:
        return items

    merged: list[dict[str, Any]] = []
    for original, core_item in zip(items, applied.get("items", []), strict=False):
        updated = dict(original)
        for source_key, target_key in (
            ("bbox", "bbox"),
            ("font_size", "font_size"),
            ("font_weight", "font_weight"),
            ("align", "align"),
            ("v_align", "v_align"),
            ("container_safe_bbox", "container_safe_bbox"),
            ("reserved_zones", "reserved_zones"),
            ("group_id", "group_id"),
            ("group_align", "group_align"),
            ("layout_rationale", "layout_rationale"),
            ("semantic_compression_level", "semantic_compression_level"),
            ("fit_order", "fit_order"),
        ):
            value = core_item.get(source_key)
            if value is not None:
                updated[target_key] = value
        if core_item.get("layout_strategy"):
            updated["ppt_master_layout_strategy"] = core_item["layout_strategy"]
        merged.append(updated)
    return merged


def _load_vendored_ppt_master_core() -> Any | None:
    repo_root = Path(__file__).resolve().parents[3]
    scripts_dir = repo_root / "vendor" / "ppt_master_slide_image_rebuild" / "scripts"
    module_path = scripts_dir / "dual_image_rebuild_pptx.py"
    if not module_path.is_file():
        return None
    module_name = "_cyberppt_vendored_ppt_master_dual_image_rebuild"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        return None
    return module


def _registry_element_record(
    element: dict[str, Any],
    plan: dict[str, Any],
    visual_registry: dict[str, Any],
    *,
    coordinate_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    raw_bbox = element.get("blueprint_bbox_px") or element.get("bbox")
    if not isinstance(raw_bbox, dict):
        return None
    try:
        x = float(raw_bbox["x"])
        y = float(raw_bbox["y"])
        w = float(raw_bbox["w"])
        h = float(raw_bbox["h"])
    except (KeyError, TypeError, ValueError):
        return None
    bbox = [x, y, x + w, y + h]
    bbox = _scale_registry_bbox_if_needed(bbox, plan, visual_registry, coordinate_context=coordinate_context)
    return {
        "element_id": str(element.get("element_id") or element.get("id") or ""),
        "element_type": str(element.get("element_type") or ""),
        "source_component_id": str(element.get("source_component_id") or ""),
        "bbox": bbox,
    }


def _scale_registry_bbox_if_needed(
    bbox: list[float],
    plan: dict[str, Any],
    visual_registry: dict[str, Any],
    *,
    coordinate_context: dict[str, Any] | None = None,
) -> list[float]:
    coordinate_space = (
        coordinate_context.get("coordinate_space")
        if isinstance(coordinate_context, dict) and isinstance(coordinate_context.get("coordinate_space"), dict)
        else None
    )
    registry_input_space = (
        coordinate_context.get("visual_registry_input_space")
        if isinstance(coordinate_context, dict) and isinstance(coordinate_context.get("visual_registry_input_space"), dict)
        else None
    )
    if coordinate_space and registry_input_space:
        return _normalize_bbox_to_context(bbox, registry_input_space, coordinate_context)
    if coordinate_space:
        plan_w = float(coordinate_space.get("width") or 0)
        plan_h = float(coordinate_space.get("height") or 0)
    else:
        image_size = plan.get("image_size") if isinstance(plan.get("image_size"), dict) else {}
        plan_w = float(image_size.get("width") or 0)
        plan_h = float(image_size.get("height") or 0)
    canvas = visual_registry.get("blueprint_canvas_px") if isinstance(visual_registry.get("blueprint_canvas_px"), dict) else {}
    registry_w = float(canvas.get("w") or 0)
    registry_h = float(canvas.get("h") or 0)
    if plan_w <= 0 or plan_h <= 0 or registry_w <= 0 or registry_h <= 0:
        return bbox
    # Some historical registries carry stale canvas metadata while element
    # coordinates still match the source image; avoid scaling those twice.
    if _registry_has_stale_canvas_metadata(visual_registry, registry_w, registry_h):
        return bbox
    if abs(plan_w - registry_w) <= 2.0 and abs(plan_h - registry_h) <= 2.0:
        return bbox
    sx = plan_w / registry_w
    sy = plan_h / registry_h
    return [bbox[0] * sx, bbox[1] * sy, bbox[2] * sx, bbox[3] * sy]


def _registry_has_stale_canvas_metadata(visual_registry: dict[str, Any], registry_w: float, registry_h: float) -> bool:
    if registry_w <= 0 or registry_h <= 0:
        return False
    for element in visual_registry.get("elements", []):
        if not isinstance(element, dict):
            continue
        raw_bbox = element.get("blueprint_bbox_px") or element.get("bbox")
        if not isinstance(raw_bbox, dict):
            continue
        try:
            x2 = float(raw_bbox["x"]) + float(raw_bbox["w"])
            y2 = float(raw_bbox["y"]) + float(raw_bbox["h"])
        except (KeyError, TypeError, ValueError):
            continue
        if x2 > registry_w + 2.0 or y2 > registry_h + 2.0:
            return True
    return False


def _element_belongs_to_container(
    element: dict[str, Any],
    container: dict[str, Any],
    container_bbox: list[float],
) -> bool:
    element_bbox = element["bbox"]
    if not _bbox_intersects(element_bbox, container_bbox):
        return False
    intersection = _intersection_area(element_bbox, container_bbox)
    element_area = max(1.0, (element_bbox[2] - element_bbox[0]) * (element_bbox[3] - element_bbox[1]))
    if intersection / element_area >= 0.55:
        return True
    source_component = str(element.get("source_component_id") or "")
    container_id = str(container.get("id") or "")
    return bool(source_component and source_component in container_id)


def _registry_zone_intersects_text_region(
    element: dict[str, Any],
    container_bbox: list[float],
    text_zones: list[dict[str, Any]],
) -> bool:
    element_bbox = element["bbox"]
    if not text_zones:
        return _intersection_area(element_bbox, container_bbox) > 0
    vertical_overlap = any(_axis_overlap(element_bbox[1], element_bbox[3], zone["bbox"][1], zone["bbox"][3]) > 0 for zone in text_zones)
    horizontal_overlap = any(_axis_overlap(element_bbox[0], element_bbox[2], zone["bbox"][0], zone["bbox"][2]) > 0 for zone in text_zones)
    return vertical_overlap or horizontal_overlap


def _reserved_zone_name(element: dict[str, Any]) -> str:
    kind = str(element.get("element_type") or "visual")
    if kind == "icon":
        return "icon_zone"
    if kind in {"flow_arrow", "arrow", "connector", "feedback_connector"}:
        return "connector_zone"
    return f"{kind}_zone"


def _semantic_container_relations(containers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for container_id, container in containers.items():
        child_elements = [
            item for item in container.get("registry_child_elements", []) if isinstance(item, dict)
        ]
        for child in child_elements:
            relations.append(
                {
                    "container_id": container_id,
                    "container_role": str(container.get("role") or ""),
                    "element_id": child.get("element_id"),
                    "element_type": child.get("element_type"),
                    "source_component_id": child.get("source_component_id"),
                    "relation": child.get("relation") or "contained_or_component_matched",
                    "bbox": child.get("bbox"),
                }
            )
    return relations


def _semantic_text_neighbors(items: list[dict[str, Any]], containers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    neighbors: list[dict[str, Any]] = []
    for item in items:
        bbox = _as_xyxy(item.get("bbox")) if isinstance(item, dict) else None
        if bbox is None:
            continue
        container = containers.get(str(item.get("container_id") or ""), {})
        candidates = [
            element
            for element in container.get("registry_child_elements", [])
            if isinstance(element, dict)
            and _as_xyxy(element.get("bbox")) is not None
            and str(element.get("element_type") or "") not in CONTAINER_LIKE_ELEMENT_TYPES
        ]
        neighbors.append(
            {
                "text": item.get("text"),
                "role": item.get("role"),
                "container_id": item.get("container_id"),
                "bbox": _round_xyxy(bbox),
                "nearest": _nearest_elements_by_side(bbox, candidates),
            }
        )
    return neighbors


def _nearest_elements_by_side(text_bbox: list[float], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    sides: dict[str, tuple[float, dict[str, Any]] | None] = {
        "left": None,
        "right": None,
        "above": None,
        "below": None,
    }
    overlapping: list[dict[str, Any]] = []
    tx1, ty1, tx2, ty2 = text_bbox
    for element in candidates:
        eb = _as_xyxy(element.get("bbox"))
        if eb is None:
            continue
        ex1, ey1, ex2, ey2 = eb
        vertical_overlap = _axis_overlap(ty1, ty2, ey1, ey2)
        horizontal_overlap = _axis_overlap(tx1, tx2, ex1, ex2)
        if ex2 <= tx1 and vertical_overlap > 0:
            _keep_nearest(sides, "left", tx1 - ex2, element, eb, vertical_overlap)
        if ex1 >= tx2 and vertical_overlap > 0:
            _keep_nearest(sides, "right", ex1 - tx2, element, eb, vertical_overlap)
        if ey2 <= ty1 and horizontal_overlap > 0:
            _keep_nearest(sides, "above", ty1 - ey2, element, eb, horizontal_overlap)
        if ey1 >= ty2 and horizontal_overlap > 0:
            _keep_nearest(sides, "below", ey1 - ty2, element, eb, horizontal_overlap)
        if _bbox_intersects(text_bbox, eb):
            overlap_area = _intersection_area(text_bbox, eb)
            payload = _neighbor_payload(
                {
                    **element,
                    "bbox": _round_xyxy(eb),
                    "axis_overlap": round(max(vertical_overlap, horizontal_overlap), 2),
                },
                0.0,
            )
            payload["overlap_area"] = round(overlap_area, 2)
            overlapping.append(payload)
    result: dict[str, Any] = {side: (_neighbor_payload(record[1], record[0]) if record else None) for side, record in sides.items()}
    result["overlapping"] = sorted(overlapping, key=lambda item: float(item.get("overlap_area") or 0), reverse=True)
    return result


def _keep_nearest(
    sides: dict[str, tuple[float, dict[str, Any]] | None],
    side: str,
    distance: float,
    element: dict[str, Any],
    bbox: list[float],
    overlap: float,
) -> None:
    payload = dict(element)
    payload["bbox"] = _round_xyxy(bbox)
    payload["axis_overlap"] = round(overlap, 2)
    current = sides.get(side)
    if current is None or distance < current[0]:
        sides[side] = (round(distance, 2), payload)


def _neighbor_payload(element: dict[str, Any], distance: float) -> dict[str, Any]:
    return {
        "element_id": element.get("element_id"),
        "element_type": element.get("element_type"),
        "source_component_id": element.get("source_component_id"),
        "bbox": element.get("bbox"),
        "distance": distance,
        "axis_overlap": element.get("axis_overlap"),
    }


def build_semantic_layout_qa_report(layout_plan: dict[str, Any]) -> dict[str, Any]:
    """Validate planned text against semantic safe areas and reserved visual zones."""
    issues: list[dict[str, Any]] = []
    for index, item in enumerate(layout_plan.get("items", [])):
        if not isinstance(item, dict):
            continue
        bbox = _as_xyxy(item.get("bbox"))
        if bbox is None:
            issues.append(
                {
                    "severity": "error",
                    "code": "missing_text_bbox",
                    "item_index": index,
                    "text": item.get("text"),
                    "message": "Layout item has no bbox.",
                }
            )
            continue
        safe = _as_xyxy(item.get("container_safe_bbox"))
        if safe is not None and not _bbox_inside_xyxy(bbox, safe, tolerance=0.5):
            issues.append(
                {
                    "severity": "error",
                    "code": "text_outside_container_safe_bbox",
                    "item_index": index,
                    "text": item.get("text"),
                    "bbox": _round_xyxy(bbox),
                    "container_safe_bbox": _round_xyxy(safe),
                    "message": "Text bbox is outside its semantic container safe bbox.",
                }
            )
        if str(item.get("role") or "") in INDEX_TEXT_ROLES:
            continue
        for zone in item.get("reserved_zones", []):
            if not isinstance(zone, dict):
                continue
            zone_bbox = _as_xyxy(zone.get("bbox"))
            if zone_bbox is not None and _bbox_intersects(bbox, zone_bbox):
                issues.append(
                    {
                        "severity": "error",
                        "code": "text_intersects_reserved_zone",
                        "item_index": index,
                        "text": item.get("text"),
                        "bbox": _round_xyxy(bbox),
                        "reserved_zone": {
                            "name": zone.get("name"),
                            "bbox": _round_xyxy(zone_bbox),
                            "source_element_id": zone.get("source_element_id"),
                        },
                        "message": "Text bbox intersects a registry-derived reserved visual zone.",
                    }
                )
    return {
        "schema": "cyberppt.dual_image.semantic_layout_qa.v1",
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def _bbox_intersects(a: list[float], b: list[float]) -> bool:
    return _axis_overlap(a[0], a[2], b[0], b[2]) > 0 and _axis_overlap(a[1], a[3], b[1], b[3]) > 0


def _axis_overlap(a1: float, a2: float, b1: float, b2: float) -> float:
    return max(0.0, min(a2, b2) - max(a1, b1))


def _intersection_area(a: list[float], b: list[float]) -> float:
    return _axis_overlap(a[0], a[2], b[0], b[2]) * _axis_overlap(a[1], a[3], b[1], b[3])


def _union_bbox(boxes: list[list[float]]) -> list[float]:
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _round_xyxy(bbox: list[float]) -> list[float]:
    return [round(float(value), 2) for value in bbox]


def _inset_xyxy(bbox: list[float], left: float, top: float, right: float, bottom: float) -> list[float]:
    return [
        bbox[0] + left,
        bbox[1] + top,
        max(bbox[0] + left + 1.0, bbox[2] - right),
        max(bbox[1] + top + 1.0, bbox[3] - bottom),
    ]


def _expand_bbox_within(bbox: list[float], container_bbox: list[float], *, x: float, y: float) -> list[float]:
    return [
        max(container_bbox[0], bbox[0] - x),
        max(container_bbox[1], bbox[1] - y),
        min(container_bbox[2], bbox[2] + x),
        min(container_bbox[3], bbox[3] + y),
    ]


def _plan_ability_card(
    container_id: str,
    container: dict[str, Any],
    entries: list[tuple[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    bbox = _as_xyxy(container.get("bbox"))
    safe = _as_xyxy(container.get("text_safe_bbox")) or bbox
    if safe is None:
        return _plan_generic_container(container_id, container, entries)
    x1, y1, x2, y2 = safe
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    text_zones = [_as_xyxy(zone.get("bbox")) for zone in container.get("registry_text_zones", []) if isinstance(zone, dict)]
    text_zones = [zone for zone in text_zones if zone is not None]
    icon_zones = [
        _as_xyxy(zone.get("bbox"))
        for zone in container.get("reserved_zones", [])
        if isinstance(zone, dict) and str(zone.get("name") or "") == "icon_zone"
    ]
    icon_zones = [zone for zone in icon_zones if zone is not None and _bbox_intersects(zone, safe)]
    text_anchor_x = x1 + width * 0.43
    if text_zones:
        text_anchor_x = max(text_anchor_x, min(zone[0] for zone in text_zones))
    if icon_zones:
        text_anchor_x = max(text_anchor_x, max(zone[2] for zone in icon_zones) + max(6.0, width * 0.04))
    text_anchor_x = min(text_anchor_x, x2 - max(48.0, width * 0.34))
    ability_hints = {
        "applied_rules": [],
        "reserved_zone_drivers": [],
        "text_zone_drivers": [_round_xyxy(zone) for zone in text_zones],
    }
    if icon_zones:
        ability_hints["applied_rules"].append("anchor_text_after_left_icon")
        ability_hints["reserved_zone_drivers"] = [
            {"side": "left", "name": "icon_zone", "bbox": _round_xyxy(zone)}
            for zone in icon_zones
        ]
    if text_zones:
        ability_hints["applied_rules"].append("honor_registry_text_zone")
    number_box = [x1 + width * 0.08, y1 + height * 0.08, x1 + width * 0.2, y1 + height * 0.25]
    title_box = [text_anchor_x, y1 + height * 0.06, x2 - width * 0.05, y1 + height * 0.28]
    bullet_x1 = text_anchor_x
    bullet_y1 = y1 + height * 0.36
    bullet_y2 = y2 - height * 0.08
    bullet_entries = [(index, item) for index, item in entries if str(item.get("role") or "") in BODY_TEXT_ROLES]
    bullet_count = max(1, len(bullet_entries))
    line_h = max(1.0, (bullet_y2 - bullet_y1) / bullet_count)

    planned: list[dict[str, Any]] = []
    bullet_position = 0
    for index, item in entries:
        item_role = str(item.get("role") or "")
        if item_role in INDEX_TEXT_ROLES:
            item_bbox = number_box
            align = "center"
            font_size = float(item.get("font_size") or min(16.0, (number_box[3] - number_box[1]) * 0.75))
            font_weight = item.get("font_weight") or "700"
        elif item_role in TITLE_TEXT_ROLES:
            item_bbox = title_box
            align = str(container.get("align") or "left")
            font_size = float(item.get("font_size") or min(18.0, (title_box[3] - title_box[1]) * 0.72))
            font_weight = item.get("font_weight") or "700"
        elif item_role in BODY_TEXT_ROLES:
            by = bullet_y1 + bullet_position * line_h
            item_bbox = [bullet_x1, by, x2 - width * 0.05, min(bullet_y2, by + line_h * 0.86)]
            bullet_position += 1
            align = str(item.get("align") or "left")
            font_size = float(item.get("font_size") or min(13.5, max(8.0, (item_bbox[3] - item_bbox[1]) * 0.72)))
            font_weight = item.get("font_weight") or "400"
        else:
            item_bbox = _item_bbox_or_safe(item, safe)
            align = str(item.get("align") or "left")
            font_size = float(item.get("font_size") or max(8.0, (item_bbox[3] - item_bbox[1]) * 0.62))
            font_weight = item.get("font_weight") or "400"
        planned.append(
            _semantic_layout_record(
                index,
                item,
                container_id,
                container,
                item_bbox,
                align,
                font_size,
                font_weight,
                layout_hints=ability_hints if item_role in TITLE_TEXT_ROLES or item_role in BODY_TEXT_ROLES else None,
            )
        )
    return planned


def _plan_generic_container(
    container_id: str,
    container: dict[str, Any],
    entries: list[tuple[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    safe = _as_xyxy(container.get("text_safe_bbox")) or _as_xyxy(container.get("bbox")) or [0.0, 0.0, 1.0, 1.0]
    planned: list[dict[str, Any]] = []
    for index, item in entries:
        item_bbox = _item_bbox_or_safe(item, safe)
        item_role = str(item.get("role") or "")
        item_bbox, layout_hints = _avoid_reserved_zones_for_text_bbox(
            item_bbox,
            safe,
            container.get("reserved_zones", []),
            role=item_role,
            container_role=str(container.get("role") or ""),
        )
        _apply_registry_text_zone_hints(layout_hints, container)
        align = str(item.get("align") or ("left" if item_role in BODY_TEXT_ROLES else "center"))
        font_size = float(item.get("font_size") or max(7.0, min(18.0, (item_bbox[3] - item_bbox[1]) * 0.62)))
        font_weight = item.get("font_weight") or ("700" if item_role in TITLE_TEXT_ROLES else "400")
        planned.append(
            _semantic_layout_record(
                index,
                item,
                container_id,
                container,
                item_bbox,
                align,
                font_size,
                font_weight,
                layout_hints=layout_hints,
            )
        )
    return planned


def _avoid_reserved_zones_for_text_bbox(
    bbox: list[float],
    safe: list[float],
    reserved_zones: Any,
    *,
    role: str,
    container_role: str = "",
) -> tuple[list[float], dict[str, Any]]:
    hints: dict[str, Any] = {"applied_rules": [], "reserved_zone_drivers": []}
    if role in INDEX_TEXT_ROLES:
        return bbox, hints
    adjusted = list(bbox)
    min_width = min(max(24.0, (safe[2] - safe[0]) * 0.45), max(1.0, safe[2] - safe[0]))
    for zone in reserved_zones if isinstance(reserved_zones, list) else []:
        if not isinstance(zone, dict):
            continue
        zone_bbox = _as_xyxy(zone.get("bbox"))
        if zone_bbox is None:
            continue
        gap = 8.0 if container_role in ICON_AWARE_CONTAINER_ROLES else 4.0
        bbox_center_x = (adjusted[0] + adjusted[2]) / 2
        zone_center_x = (zone_bbox[0] + zone_bbox[2]) / 2
        vertical_overlap = _axis_overlap(adjusted[1], adjusted[3], zone_bbox[1], zone_bbox[3])
        left_neighbor_gap = adjusted[0] - zone_bbox[2]
        right_neighbor_gap = zone_bbox[0] - adjusted[2]
        if zone_center_x <= bbox_center_x and vertical_overlap > 0 and 0 <= left_neighbor_gap <= 10.0:
            hints["applied_rules"].append("anchor_text_after_left_icon")
            hints["reserved_zone_drivers"].append(_layout_hint_zone_driver(zone, zone_bbox, side="left"))
            if left_neighbor_gap < gap:
                new_x1 = min(max(adjusted[0], zone_bbox[2] + gap), safe[2] - min_width)
                adjusted[0] = new_x1
                adjusted[2] = max(adjusted[2], adjusted[0] + min_width)
                adjusted[2] = min(adjusted[2], safe[2])
        elif zone_center_x > bbox_center_x and vertical_overlap > 0 and 0 <= right_neighbor_gap <= 10.0:
            hints["applied_rules"].append("anchor_text_before_right_reserved_zone")
            hints["reserved_zone_drivers"].append(_layout_hint_zone_driver(zone, zone_bbox, side="right"))
            if right_neighbor_gap < gap:
                new_x2 = max(min(adjusted[2], zone_bbox[0] - gap), safe[0] + min_width)
                adjusted[2] = new_x2
                adjusted[0] = min(adjusted[0], adjusted[2] - min_width)
                adjusted[0] = max(adjusted[0], safe[0])
        if not _bbox_intersects(adjusted, zone_bbox):
            continue
        if zone_center_x <= bbox_center_x:
            new_x1 = min(max(adjusted[0], zone_bbox[2] + gap), safe[2] - min_width)
            if new_x1 > adjusted[0]:
                hints["applied_rules"].append("avoid_left_reserved_zone")
                hints["reserved_zone_drivers"].append(_layout_hint_zone_driver(zone, zone_bbox, side="left"))
            adjusted[0] = new_x1
            adjusted[2] = max(adjusted[2], adjusted[0] + min_width)
            adjusted[2] = min(adjusted[2], safe[2])
        else:
            new_x2 = max(min(adjusted[2], zone_bbox[0] - gap), safe[0] + min_width)
            if new_x2 < adjusted[2]:
                hints["applied_rules"].append("avoid_right_reserved_zone")
                hints["reserved_zone_drivers"].append(_layout_hint_zone_driver(zone, zone_bbox, side="right"))
            adjusted[2] = new_x2
            adjusted[0] = min(adjusted[0], adjusted[2] - min_width)
            adjusted[0] = max(adjusted[0], safe[0])
    hints["applied_rules"] = sorted(set(hints["applied_rules"]))
    return adjusted, hints


def _apply_registry_text_zone_hints(layout_hints: dict[str, Any], container: dict[str, Any]) -> None:
    text_zones = [
        _as_xyxy(zone.get("bbox"))
        for zone in container.get("registry_text_zones", [])
        if isinstance(zone, dict)
    ]
    text_zones = [zone for zone in text_zones if zone is not None]
    if not text_zones:
        return
    layout_hints.setdefault("applied_rules", []).append("honor_registry_text_zone")
    layout_hints["text_zone_drivers"] = [_round_xyxy(zone) for zone in text_zones]


def _layout_hint_zone_driver(zone: dict[str, Any], zone_bbox: list[float], *, side: str) -> dict[str, Any]:
    return {
        "side": side,
        "name": zone.get("name"),
        "source_element_id": zone.get("source_element_id"),
        "element_type": zone.get("element_type"),
        "bbox": _round_xyxy(zone_bbox),
    }


def _semantic_layout_record(
    index: int,
    item: dict[str, Any],
    container_id: str,
    container: dict[str, Any],
    bbox: list[float],
    align: str,
    font_size: float,
    font_weight: Any,
    layout_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role = str(item.get("role") or "text")
    return {
        "index": index,
        "text": str(item.get("display_text") or item.get("text") or ""),
        "source_text": str(item.get("source_text") or item.get("display_text") or item.get("text") or ""),
        "role": role,
        "container_id": container_id,
        "container_role": str(container.get("role") or ""),
        "bbox": [round(v, 2) for v in bbox],
        "container_safe_bbox": [round(v, 2) for v in (_as_xyxy(container.get("text_safe_bbox")) or _as_xyxy(container.get("bbox")) or bbox)],
        "font_size": round(font_size, 2),
        "font_weight": str(font_weight),
        "fill": str(item.get("fill") or container.get("fill") or "#0B1F3D"),
        "align": align,
        "word_wrap": bool(item.get("word_wrap", role in BODY_TEXT_ROLES)),
        "layout_strategy": "ability_card_slots" if str(container.get("role") or "") in {"ability_card", "capability_card"} else "container_safe_bbox",
        "reserved_zones": list(container.get("reserved_zones") or []),
        "text_zone_source": container.get("text_zone_source"),
        "layout_hints": layout_hints or {"applied_rules": [], "reserved_zone_drivers": []},
    }


def _as_xyxy(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    x1, y1, x2, y2 = [float(v) for v in value]
    return [x1, y1, x2, y2]


def _item_bbox_or_safe(item: dict[str, Any], safe: list[float]) -> list[float]:
    rel = _as_xyxy(item.get("relative_bbox"))
    if rel is not None:
        x1, y1, x2, y2 = safe
        w = x2 - x1
        h = y2 - y1
        return [x1 + rel[0] * w, y1 + rel[1] * h, x1 + rel[2] * w, y1 + rel[3] * h]
    bbox = _as_xyxy(item.get("bbox"))
    if bbox is not None and _bbox_inside_xyxy(bbox, safe, tolerance=6.0):
        return bbox
    return safe


def build_overlay_boxes_from_semantic_plan(
    plan: dict[str, Any],
    body_region: dict[str, float],
    *,
    visual_registry: dict[str, Any] | None = None,
    background_image: Path | None = None,
    font_family: str = "Microsoft YaHei",
) -> tuple[list[OverlayTextBox], dict[str, Any], dict[str, Any]]:
    gate = validate_explicit_semantic_plan(plan)
    coordinate_context = resolve_overlay_coordinate_context(
        plan,
        visual_registry=visual_registry,
        background_image=background_image,
    )
    layout_plan = build_semantic_layout_plan(
        plan,
        visual_registry=visual_registry,
        coordinate_context=coordinate_context,
    )
    layout_qa = build_semantic_layout_qa_report(layout_plan)
    gate = json.loads(json.dumps(gate, ensure_ascii=False))
    gate["layout_qa"] = layout_qa
    if not layout_qa["valid"]:
        gate["valid"] = False
        gate["error_count"] = int(gate.get("error_count") or 0) + int(layout_qa.get("issue_count") or 0)
        gate.setdefault("issues", []).extend(
            {
                "severity": issue.get("severity", "error"),
                "code": issue.get("code"),
                "item_index": issue.get("item_index"),
                "container_id": None,
                "message": issue.get("message"),
                "recommended_action": "Adjust semantic container safe areas or registry reserved zones before export.",
            }
            for issue in layout_qa.get("issues", [])
            if isinstance(issue, dict)
        )
    resolved_space = coordinate_context.get("coordinate_space") if isinstance(coordinate_context.get("coordinate_space"), dict) else {}
    image_width = float(resolved_space.get("width") or 1280)
    image_height = float(resolved_space.get("height") or 720)
    background = Image.open(background_image).convert("RGB") if background_image else None
    sx = float(body_region["width"]) / image_width
    sy = float(body_region["height"]) / image_height
    text_boxes: list[OverlayTextBox] = []
    try:
        for item in layout_plan["items"]:
            x1, y1, x2, y2 = [float(v) for v in item["bbox"]]
            x = float(body_region["x"]) + x1 * sx
            y = float(body_region["y"]) + y1 * sy
            w = max(1.0, (x2 - x1) * sx)
            h = max(1.0, (y2 - y1) * sy)
            fill = str(item.get("fill") or "#0B1F3D")
            fill = _fill_for_background(background, (x1, y1, x2, y2), image_width, image_height, fill)
            font_size = float(item.get("font_size") or _font_size_from_box(h))
            text_boxes.append(
                OverlayTextBox(
                    text=str(item["text"]),
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    font_size=round(font_size * sy, 2),
                    font_family=font_family,
                    fill=fill,
                    font_weight=str(item.get("font_weight") or "400"),
                    align=str(item.get("align") or "left"),
                    word_wrap=bool(item.get("word_wrap", False)),
                    source="semantic_plan",
                    confidence=1.0,
                )
            )
    finally:
        if background is not None:
            background.close()
    _fit_all_boxes(text_boxes)
    return text_boxes, layout_plan, gate


def _container_for_box(text_box: OverlayTextBox, containers: list[SemanticContainer]) -> SemanticContainer | None:
    center_x = text_box.x + text_box.w / 2
    center_y = text_box.y + text_box.h / 2
    text_key = normalize_text(text_box.text)
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


def _apply_container_layout(text_box: OverlayTextBox, container: SemanticContainer) -> None:
    pad_x = 0.0 if container.role == "foundation_base" else min(20.0, max(4.0, container.w * 0.06))
    pad_y = min(8.0, max(2.0, container.h * 0.12))
    text_box.x = container.x + pad_x
    text_box.w = max(1.0, container.w - pad_x * 2)
    text_box.h = max(text_box.h, container.h - pad_y * 2)
    preferred_size = max(text_box.font_size, 16.0 if container.role == "foundation_base" else text_box.font_size)
    text_box.font_size = round(_fit_font_size(text_box.text, text_box.w, preferred_size, minimum=MIN_EXPORT_FONT_SIZE_PX), 2)
    text_box.y = round(container.y + (container.h - text_box.font_size) / 2, 2)
    text_box.fill = container.fill
    text_box.align = container.align
    if container.background == "dark":
        text_box.font_weight = "700" if container.role == "foundation_base" else text_box.font_weight


def _apply_semantic_overlay_layout(
    text_boxes: list[OverlayTextBox],
    body_region: dict[str, float],
    containers: list[SemanticContainer] | None = None,
) -> None:
    free_boxes = [text_box for text_box in text_boxes if not text_box.source.startswith("manual_source_faithful")]
    _snap_same_row_boxes(free_boxes)
    _relax_repeated_body_text_lanes(free_boxes, body_region)
    _snap_repeated_column_body_rows(free_boxes, body_region)
    containers = containers or []
    for text_box in text_boxes:
        if text_box.source.startswith("manual_source_faithful"):
            continue
        container = _container_for_box(text_box, containers)
        if container is not None:
            _apply_container_layout(text_box, container)
        elif _is_dark_base_title(text_box, body_region):
            text_box.x = float(body_region["x"])
            text_box.w = float(body_region["width"])
            text_box.align = "center"
            text_box.font_size = max(text_box.font_size, 16.0)
            text_box.font_weight = "700"
        elif re.fullmatch(r"\d{1,2}", text_box.text.strip()) or (
            len(text_box.text) <= 16 and text_box.fill.strip().upper() == "#FFFFFF"
        ):
            text_box.align = "center"
    _fit_all_boxes(text_boxes)


def _is_tail_duplicate_fragment(
    *,
    text: str,
    source: str,
    item_bbox: tuple[float, float, float, float],
    previous_boxes: list[OverlayTextBox],
    sx: float,
    sy: float,
    body_region: dict[str, float],
) -> bool:
    if source != "ocr_unmatched":
        return False
    text_key = normalize_text(text)
    if len(text_key) < 2:
        return False
    x1, y1, _x2, _y2 = item_bbox
    page_x = float(body_region["x"]) + x1 * sx
    page_y = float(body_region["y"]) + y1 * sy
    for previous in reversed(previous_boxes[-6:]):
        previous_key = normalize_text(previous.text)
        if not previous_key or previous_key == text_key or not previous_key.endswith(text_key):
            continue
        same_column = abs(previous.x - page_x) <= 10.0
        just_below = 0.0 <= page_y - previous.y <= 38.0
        if same_column and just_below:
            return True
    return False


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
    text_boxes: list[OverlayTextBox] = []
    background = Image.open(background_image).convert("RGB") if background_image else None
    containers = (
        semantic_containers
        if semantic_containers is not None
        else infer_semantic_containers(background_image, ocr_layout, body_region, semantic_plan=semantic_plan)
        if background_image
        else []
    )
    try:
        flow_boxes = _build_main_flow_overlay_boxes(
            script_path=script_path,
            page_number=page_number,
            ocr_layout=ocr_layout,
            body_region=body_region,
            font_family=font_family,
            fill=fill,
            background=background,
        )
        flow_text_keys = {normalize_text(box.text) for box in flow_boxes}
        text_boxes.extend(flow_boxes)
        for item in ocr_layout.get("items", []):
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            x1, y1, x2, y2 = [float(value) for value in item["bbox"]]
            item_source = str(item.get("source") or "")
            if item_source.startswith("manual_source_faithful"):
                corrected, source = text, item_source
            else:
                corrected, source = match_script_text(text, script_lines)
            if flow_boxes:
                corrected_key = normalize_text(corrected)
                text_key = normalize_text(text)
                if corrected_key in flow_text_keys or text_key in flow_text_keys:
                    continue
                if re.fullmatch(r"\d{1,2}", text.strip()) and 1 <= int(text.strip()) <= 10:
                    continue
                if 110.0 <= y1 <= 460.0:
                    continue
            if _is_tail_duplicate_fragment(
                text=corrected,
                source=source,
                item_bbox=(x1, y1, x2, y2),
                previous_boxes=text_boxes,
                sx=sx,
                sy=sy,
                body_region=body_region,
            ):
                continue
            x = float(body_region["x"]) + x1 * sx
            y = float(body_region["y"]) + y1 * sy
            w = max(1.0, (x2 - x1) * sx)
            h = max(1.0, (y2 - y1) * sy)
            font_size = _font_size_from_box(h, corrected, source)
            text_fill = _fill_for_background(background, (x1, y1, x2, y2), image_width, image_height, fill)
            align = "center" if re.fullmatch(r"\d{1,2}", corrected.strip()) or text_fill.strip().upper() == "#FFFFFF" else "left"
            text_boxes.append(
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
                    align=align,
                    word_wrap=True,
                    source=source,
                    confidence=float(item.get("confidence", 1.0)),
                )
            )
    finally:
        if background is not None:
            background.close()
    _apply_semantic_overlay_layout(text_boxes, body_region, containers)
    return text_boxes


def render_overlay_svg(
    *,
    background_href: str,
    canvas: dict[str, int],
    body_region: dict[str, float],
    slide_title: str,
    subtitle: str = "",
    text_boxes: list[OverlayTextBox],
    text_opacity: float = 1.0,
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
        lines = _wrap_svg_text(box.text, box.w, box.font_size) if box.word_wrap else str(box.text).splitlines() or [box.text]
        line_height = box.font_size * 1.18
        total_height = box.font_size + (len(lines) - 1) * line_height
        text_y = box.y + max(box.font_size, (box.h - total_height) / 2 + box.font_size * 0.88)
        parts.append(
            f'<text x="{text_x:.2f}" y="{text_y:.2f}" text-anchor="{anchor}" '
            f'font-family="{html.escape(box.font_family)}, Arial, sans-serif" '
            f'font-size="{box.font_size:.2f}" font-weight="{html.escape(box.font_weight)}" '
            f'fill="{html.escape(box.fill)}" fill-opacity="{max(0.0, min(1.0, text_opacity)):.3f}">'
            + "".join(
                f'<tspan x="{text_x:.2f}" dy="{0 if index == 0 else line_height:.2f}">{html.escape(line)}</tspan>'
                for index, line in enumerate(lines)
            )
            + "</text>"
        )
    parts.append("</svg>\n")
    return "\n".join(parts)


def _wrap_svg_text(text: str, width: float, font_size: float) -> list[str]:
    if not text:
        return [""]
    explicit_lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    if len(explicit_lines) > 1:
        return [
            wrapped
            for line in explicit_lines
            for wrapped in _wrap_svg_text(line, width, font_size)
        ]
    normalized = str(text).strip()
    if _text_estimated_width(normalized, font_size) <= width:
        return [normalized]

    chunks = re.split(r"([/／|｜、，,；;])", normalized)
    tokens: list[str] = []
    for index in range(0, len(chunks), 2):
        token = chunks[index]
        if index + 1 < len(chunks):
            token += chunks[index + 1]
        if token:
            tokens.append(token)
    if len(tokens) <= 1:
        tokens = list(normalized)

    lines: list[str] = []
    current = ""
    for token in tokens:
        candidate = current + token
        if current and _text_estimated_width(candidate, font_size) > width:
            lines.append(current.rstrip("/／|｜、，,；;"))
            current = token.lstrip("/／|｜、，,；;")
        else:
            current = candidate
    if current:
        lines.append(current.rstrip("/／|｜、，,；;"))
    return lines or [normalized]


def text_boxes_to_json(text_boxes: list[OverlayTextBox]) -> list[dict[str, Any]]:
    return [asdict(text_box) for text_box in text_boxes]


def boxes_to_json(boxes: list[OverlayTextBox]) -> list[dict[str, Any]]:
    return text_boxes_to_json(boxes)


def containers_to_json(containers: list[SemanticContainer]) -> list[dict[str, Any]]:
    return [asdict(container) for container in containers]


def semantic_plan_to_json(plan: SemanticPlan) -> dict[str, Any]:
    return asdict(plan)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build editable text overlay boxes from script truth and OCR layout.")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--page", required=True, type=int)
    parser.add_argument("--ocr-layout", required=True, type=Path)
    parser.add_argument("--body-region", required=True, help='JSON object, e.g. {"x":20,"y":104,"width":1240,"height":592}')
    parser.add_argument("-o", "--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        layout = json.loads(args.ocr_layout.read_text(encoding="utf-8"))
        body_region = json.loads(args.body_region)
        text_boxes = build_overlay_boxes(args.script, args.page, layout, body_region)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(text_boxes_to_json(text_boxes), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        print(args.out)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
