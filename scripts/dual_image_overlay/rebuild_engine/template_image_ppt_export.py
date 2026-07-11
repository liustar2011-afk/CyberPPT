#!/usr/bin/env python3
"""CyberPPT template-image PPT export helpers.

Generate image-based PPT pages where AI output is constrained to the template
content region; title, subtitle, master chrome, footer and page numbers are
created by the PPT pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import quoteattr

from PIL import Image, ImageChops

try:
    from .codex_oauth_image import run_codex_image
except ImportError:
    from codex_oauth_image import run_codex_image

SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_BRAND_DIR = SCRIPTS_DIR / "templates" / "brands" / "中电联公共元素_轻量版"
PROJECT_CONTRACT = Path("workbench/analysis_expression/contract.json")
PROJECT_STAGE_ROOT = Path("workbench/stages/02-blueprint-dual-image")
PAGE_HEADING_RE = re.compile(r"^##\s*第(?P<num>\d+)页[:：](?P<title>.+?)\s*$", re.M)
MODULE_PREFIX_RE = re.compile(r"^模块[一二三四五六七八九十百千万0-9]+[:：]\s*")
MODULE_MARKER_RE = re.compile(r"模块[一二三四五六七八九十百千万0-9]+[:：]?\s*")
IMAGEGEN_NON_VISIBLE_SECTION_RE = re.compile(
    r"\n(?:保真约束[:：]|来源位置[:：]|完整性校核[:：]|"
    r"#{1,6}\s*(?:非上屏|证据链|来源位置|完整性校核).*|"
    r"【(?:保真约束|构图指令|构图接口|非上屏|证据链|来源位置|完整性校核)】)"
)
COMPOSITION_SECTION_RE = re.compile(r"【(?:构图指令|构图接口)】(?P<body>.*)$", re.S)
IMAGE_PROMPT_PROVENANCE_RE = re.compile(
    r"(证据链|来源位置|源材料|完整性校核|业务稿证据|重点对应|对应E\d+|\bE\d+\b|P(?!10\b|50\b|90\b)\d+|T\d+)"
)
CANVAS_SIZE = (1280, 720)
CONTENT_REGION_TOP_INSET = -18
CONTENT_REGION_BOTTOM_INSET = -20
CONTENT_REGION_SIDE_OUTSET = 38
IMAGE_GENERATION_SCALE = 2
MAX_GENERATED_ASPECT_RATIO_DRIFT = 0.08
MIN_GENERATED_CONTENT_WIDTH_RATIO = 0.90
MAX_GENERATED_SIDE_MARGIN_RATIO = 0.06
GENERATED_CONTENT_BACKGROUND_DIFF_THRESHOLD = 18
DEFAULT_STYLE_NAME = "cyberppt-full-image-default"
DEFAULT_IMAGE_STYLE = {
    "name": DEFAULT_STYLE_NAME,
    "style_prompt": (
        "咨询报告式信息图风格；清晰分区、克制配色、轻量图表语言、"
        "高信息密度但保持可读；避免营销海报感、避免大段装饰性背景。"
    ),
}


def load_image_style(name: str | None) -> dict:
    """Return the self-contained default style used by the full-image PPT path."""
    if name in {None, "", DEFAULT_STYLE_NAME}:
        return dict(DEFAULT_IMAGE_STYLE)
    candidate = Path(str(name)).expanduser()
    if candidate.is_file():
        if candidate.suffix.lower() == ".json":
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("name", candidate.stem)
                return data
        return {"name": candidate.stem, "style_prompt": candidate.read_text(encoding="utf-8").strip()}
    return {"name": str(name), "style_prompt": str(name)}


def style_name(style: dict | None) -> str:
    if not style:
        return DEFAULT_STYLE_NAME
    return str(style.get("name") or DEFAULT_STYLE_NAME)


def style_prompt_block(style: dict | None) -> str:
    style = style or DEFAULT_IMAGE_STYLE
    prompt = str(style.get("style_prompt") or style.get("prompt") or "").strip()
    if not prompt:
        prompt = DEFAULT_IMAGE_STYLE["style_prompt"]
    return f"视觉风格：{style_name(style)}\n{prompt}"


def sanitize_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value.strip())
    safe = safe.strip("._")
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe[:120] or "source"


@dataclass
class PageBlock:
    page_number: int
    title: str
    text: str


@dataclass
class PageContent:
    title: str
    subtitle: str
    body: str


def page_notes_text(block: PageBlock) -> str:
    """Build speaker notes from the page content, not from image prompt instructions."""
    explicit = re.search(r"【(?:演讲者备注|演讲稿|讲稿|备注)】(?P<body>.*)$", block.text, re.S)
    if explicit:
        text = explicit.group("body").strip()
        return re.sub(r"\n-{3,}\s*$", "", text).strip()
    content = extract_content(block)
    lines = [line.strip() for line in content.body.splitlines() if line.strip()]
    notes: list[str] = []
    if content.title:
        notes.append(f"本页围绕“{content.title}”展开。")
    if content.subtitle:
        notes.append(f"核心提示：{content.subtitle}")
    if lines:
        notes.append("汇报要点：")
        notes.extend(f"- {line}" for line in lines)
    return "\n".join(notes).strip()


def page_role(block: PageBlock) -> str:
    if block.page_number == 1 or "封面" in block.title:
        return "cover"
    if "目录" in block.title:
        return "agenda"
    if re.search(r"第[一二三四五六七八九十]+章", block.title):
        return "section"
    if any(keyword in block.title for keyword in ("封底", "结束", "感谢")):
        return "ending"
    return "body"


def parse_page_blocks(script_path: Path) -> dict[int, PageBlock]:
    text = script_path.read_text(encoding="utf-8")
    matches = list(PAGE_HEADING_RE.finditer(text))
    pages: dict[int, PageBlock] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        number = int(match.group("num"))
        pages[number] = PageBlock(number, match.group("title").strip(), text[match.start():end].strip())
    return pages


def parse_page_selection(raw: str, available: set[int]) -> list[int]:
    if not raw.strip() or raw.strip().lower() == "all":
        return sorted(available)
    selected: set[int] = set()
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            left, right = item.split("-", 1)
            start, end = int(left.strip()), int(right.strip())
            selected.update(range(start, end + 1))
        else:
            selected.add(int(item))
    missing = sorted(selected - available)
    if missing:
        raise ValueError(f"Pages not found in script: {missing}")
    return sorted(selected)


def page_stem(page_number: int, title: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", title).strip("_")[:36] or "page"
    return f"page_{page_number:03d}_{normalized}"


def locked_content_text(block: PageBlock) -> str:
    match = re.search(r"【内容锁定】(?P<body>.*)$", block.text, re.S)
    if match:
        content = match.group("body")
        content = IMAGEGEN_NON_VISIBLE_SECTION_RE.split(content, maxsplit=1)[0]
    else:
        content = PAGE_HEADING_RE.sub("", block.text, count=1)
    return re.sub(r"\n-{3,}\s*$", "", content.strip()).strip()


def extract_content(block: PageBlock) -> PageContent:
    content = locked_content_text(block)
    lines = [line.strip() for line in content.splitlines()]
    title = block.title
    subtitle = ""
    body_lines: list[str] = []
    current_label = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue
        if line.startswith("标题：") or line.startswith("标题:"):
            inline = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
            values: list[str] = []
            if inline.strip():
                values.append(inline.strip())
                i += 1
            else:
                i += 1
                while i < len(lines) and lines[i] and not re.match(r"^[\u4e00-\u9fffA-Za-z]+[一二三四五六七八九十0-9]*[:：]", lines[i]):
                    values.append(lines[i])
                    i += 1
            if values:
                title = " ".join(values)
            continue
        if line.startswith("副标题：") or line.startswith("副标题:"):
            subtitle = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
        elif line.startswith("英文标题：") or line.startswith("英文标题:"):
            extra = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
            if extra:
                subtitle = extra
        elif re.match(r"^(模块|主判断|一、|二、|三、|四、|五、|六、|七、|八、|九、)", line):
            current_label = line
            body_lines.append(line)
        elif line.startswith("- "):
            body_lines.append(line[2:])
        elif line not in {"标题：", "标题:", "英文标题：", "英文标题:"}:
            body_lines.append(line)
        i += 1
    return PageContent(title=title, subtitle=subtitle, body="\n".join(body_lines).strip())


def strip_visual_structure_markers(line: str) -> str:
    """Remove script-only composition labels that should not appear as image text."""
    return MODULE_PREFIX_RE.sub("", line).strip()


def sanitize_image_prompt_text(text: str) -> str:
    """Remove source-script structure markers before sending text to image generation."""
    return MODULE_MARKER_RE.sub("", text)


def image_body_visible_text(body: str) -> str:
    lines = []
    for line in body.splitlines():
        cleaned = strip_visual_structure_markers(line)
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines).strip()


def image_visible_text(block: PageBlock, content: PageContent, role: str) -> str:
    lines: list[str] = []
    if role in {"cover", "ending"}:
        if content.title:
            lines.append(content.title)
        if content.subtitle:
            lines.append(content.subtitle)
    if content.body:
        lines.append(image_body_visible_text(content.body))
    return "\n\n".join(lines).strip()


def extract_composition_instruction(block: PageBlock) -> str:
    match = COMPOSITION_SECTION_RE.search(block.text)
    if not match:
        return ""
    text = re.sub(r"\n-{3,}\s*$", "", match.group("body").strip()).strip()
    return sanitize_image_prompt_text(text).strip()


def load_brand_rules(brand_dir: Path = DEFAULT_BRAND_DIR) -> dict:
    return json.loads((brand_dir / "brand_rules.json").read_text(encoding="utf-8"))


def scale_region(region: dict, pixel_size: tuple[int, int]) -> dict[str, int]:
    width, height = pixel_size
    return {
        "x": round(region.get("x", 0) * width / CANVAS_SIZE[0]),
        "y": round(region.get("y", 0) * height / CANVAS_SIZE[1]),
        "width": round(region.get("width", 0) * width / CANVAS_SIZE[0]),
        "height": round(region.get("height", 0) * height / CANVAS_SIZE[1]),
    }


def inset_content_region(region: dict[str, int]) -> dict[str, int]:
    top = CONTENT_REGION_TOP_INSET
    bottom = CONTENT_REGION_BOTTOM_INSET
    side = CONTENT_REGION_SIDE_OUTSET
    x = max(0, region["x"] - side)
    height = max(1, region["height"] - top - bottom)
    return {
        "x": x,
        "y": region["y"] + top,
        "width": min(CANVAS_SIZE[0] - x, region["width"] + side * 2),
        "height": height,
    }


def content_prompt(
    page: PageBlock,
    content: PageContent,
    body_region: dict[str, int],
    generation_size: dict[str, int],
    role: str,
    image_style: dict | None = None,
) -> str:
    if role in {"cover", "ending"}:
        title_rule = "封面/封底标题、副标题允许作为图片正文区文字生成；不要画字段名“标题：”“副标题：”“英文标题：”。"
    else:
        title_rule = "不要画标题、副标题；标题、副标题由 PPT 模板文字层生成。"
    image_style = image_style or load_image_style(DEFAULT_STYLE_NAME)
    visible_text = image_visible_text(page, content, role)
    return f"""请生成一张用于 PPT 内容区的图片，输出画布尺寸为 {generation_size['width']}×{generation_size['height']}。这张图后续会被代码放入 PPT 模板正文内容区（模板坐标 x={body_region['x']}, y={body_region['y']}, w={body_region['width']}, h={body_region['height']}）。

硬性边界：
- {title_rule}
- 不要画页码、Logo、页脚、红线、蓝色底栏或任何中电联公共元素。
- 不要预留页面外边框，不要生成完整 PPT 页面，只生成正文内容区画面。
- 内容必须充分铺满本图片画布：最左侧有效内容距左边缘不超过画布宽度 6%，最右侧有效内容距右边缘不超过画布宽度 6%，有效内容整体宽度不少于画布宽度 90%。
- 不要把内容缩成居中的“小版面”“截图页”“白纸页”或带宽边距的容器；背景承载面可以到达画布边缘，模块、流程线、图表和说明文字应横向展开。
- 可见文字只能取自下面“正文内容”中的事实、概念、数字和短语；可以压缩、取舍、重组，但不得新增事实、数字、口号、英文伪字、水印、乱码。
- 脚本里的结构编号只用于分组理解，不得作为画面文字出现，也不得按原编号抄写。

{style_prompt_block(image_style)}

正文内容：
{visible_text}

构图要求：
{extract_composition_instruction(page)}
"""


def validate_image_prompt_text(page_number: int, prompt: str) -> None:
    match = IMAGE_PROMPT_PROVENANCE_RE.search(prompt)
    if match:
        raise ValueError(
            f"image generation prompt for page {page_number} contains non-visual provenance text: {match.group(0)}"
        )


def validate_task_role_contract(task: dict) -> None:
    page_number = int(task.get("page_number", 0))
    role = str(task.get("page_role") or "")
    render_mode = str(task.get("render_mode") or "")
    if role in {"cover", "agenda", "section", "ending"}:
        expected_template = page_template_name(role)
        if render_mode != "brand-template" or task.get("template") != expected_template:
            raise ValueError(f"page {page_number} role {role} must use brand template rendering")
        forbidden = [key for key in ("image_path", "prompt", "size") if key in task]
        if forbidden:
            raise ValueError(f"page {page_number} role {role} must not request image generation: {forbidden}")
    else:
        if render_mode != "content-image":
            raise ValueError(f"page {page_number} body page must use content-image rendering")
        required = [key for key in ("image_path", "prompt", "size") if not task.get(key)]
        if required:
            raise ValueError(f"page {page_number} body page missing image generation fields: {required}")
        validate_image_prompt_text(page_number, str(task["prompt"]))


def validate_manifest_contract(manifest: dict) -> None:
    for task in manifest.get("tasks", []):
        if not isinstance(task, dict):
            raise ValueError("template image manifest tasks must be objects")
        validate_task_role_contract(task)


def page_template_name(role: str) -> str | None:
    if role in {"cover", "agenda", "section", "ending"}:
        return role
    return None


def chapter_label_and_title(title: str) -> tuple[str, str]:
    match = re.search(r"(第[一二三四五六七八九十]+章)\s*(?P<title>.*)", title)
    if match:
        return match.group(1), match.group("title").strip() or title
    return "", title


def agenda_items_from_pages(pages: dict[int, PageBlock], selected: list[int]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for number in selected:
        block = pages[number]
        if page_role(block) != "section":
            continue
        label, title = chapter_label_and_title(block.title)
        items.append({"label": label, "title": title})
    return items


def agenda_items_svg(items: list[dict[str, str]]) -> str:
    if not items:
        items = [
            {"label": "01", "title": "建设背景与基础"},
            {"label": "02", "title": "建设总体思路"},
            {"label": "03", "title": "建设内容及实施方案"},
            {"label": "04", "title": "需请领导审定事项"},
        ]
    y0 = 246
    gap = 82
    lines = []
    for index, item in enumerate(items[:6], start=1):
        y = y0 + (index - 1) * gap
        label = str(item.get("label") or f"{index:02d}")
        title = str(item.get("title") or "")
        lines.append(f'<text x="356" y="{y}" font-family="Microsoft YaHei, Arial, sans-serif" font-size="22" font-weight="700" fill="#8B0000">{xml_escape(label)}</text>')
        lines.append(f'<text x="448" y="{y}" font-family="Microsoft YaHei, Arial, sans-serif" font-size="28" font-weight="600" fill="#1F2933">{xml_escape(title)}</text>')
        lines.append(f'<line x1="448" y1="{y + 24}" x2="1088" y2="{y + 24}" stroke="#D8DEE8" stroke-width="1"/>')
    return "\n    ".join(lines)


def page_meta_value(content: PageContent, label: str) -> str:
    pattern = re.compile(rf"^{re.escape(label)}[:：]\s*(?P<value>.+?)\s*$")
    for line in content.body.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group("value").strip()
    return ""


def cover_author(content: PageContent) -> str:
    return page_meta_value(content, "汇报单位") or page_meta_value(content, "编制单位") or content.subtitle


def cover_date(content: PageContent) -> str:
    return page_meta_value(content, "汇报日期") or page_meta_value(content, "日期")


def cover_content_fields(task: dict) -> tuple[str, str, str]:
    """Extract cover title, author/unit, and date from script content before using role labels."""

    fallback_title = str(task.get("slide_title") or task.get("title") or "")
    def is_structural_cover_line(line: str) -> bool:
        return (
            line.startswith("页面类型")
            or line.startswith("本页类型")
            or line.startswith("组件")
            or "——" in line
        )

    body_lines = [
        line.strip().lstrip("- ").strip()
        for line in str(task.get("body_text") or "").splitlines()
        if line.strip() and not is_structural_cover_line(line.strip().lstrip("- ").strip())
    ]
    content = PageContent(fallback_title, str(task.get("subtitle") or ""), str(task.get("body_text") or ""))
    title = page_meta_value(content, "汇报标题") or page_meta_value(content, "项目名称")
    if not title and fallback_title in {"封面", "首页"} and body_lines:
        title = body_lines[0]
    title = title or fallback_title
    author = cover_author(content)
    if not author and len(body_lines) >= 2:
        author = body_lines[1]
    date = cover_date(content)
    if not date and len(body_lines) >= 3:
        date = body_lines[2]
    date = re.sub(r"\s+", "", date)
    return title, author, date


def body_lines_from_task(task: dict) -> list[str]:
    return [
        line.strip().lstrip("- ").strip()
        for line in str(task.get("body_text") or "").splitlines()
        if line.strip()
    ]


def notes_heading_for_task(task: dict) -> str:
    template_name = task.get("template") or page_template_name(task.get("page_role", ""))
    if template_name == "cover":
        title, _, _ = cover_content_fields(task)
        return title
    if template_name == "section":
        return str(task.get("section_title") or task.get("slide_title") or task.get("title") or "")
    if template_name == "ending":
        lines = body_lines_from_task(task)
        if lines and str(task.get("slide_title") or task.get("title") or "") in {"封底", "结束页"}:
            return lines[0]
    return str(task.get("slide_title") or task.get("title") or "")


def page_notes_text_for_task(block: PageBlock, task: dict) -> str:
    """Build speaker notes from the script page, with template-page headings resolved from page content."""
    explicit = re.search(r"【(?:演讲者备注|演讲稿|讲稿|备注)】(?P<body>.*)$", block.text, re.S)
    if explicit:
        text = explicit.group("body").strip()
        return re.sub(r"\n-{3,}\s*$", "", text).strip()
    lines = body_lines_from_task(task)
    notes: list[str] = []
    heading = notes_heading_for_task(task)
    if heading:
        notes.append(f"本页围绕“{heading}”展开。")
    subtitle = str(task.get("subtitle") or "")
    if subtitle:
        notes.append(f"核心提示：{subtitle}")
    if lines:
        notes.append("汇报要点：")
        notes.extend(f"- {line}" for line in lines)
    return "\n".join(notes).strip()


def char_width_units(char: str) -> float:
    if char.isascii():
        return 0.55
    return 1.0


def text_width_units(text: str) -> float:
    return sum(char_width_units(char) for char in text)


def wrap_text_by_units(text: str, max_units: float, max_lines: int = 3) -> list[str]:
    clean = re.sub(r"\s+", "", text.strip())
    if not clean:
        return [""]
    lines: list[str] = []
    current = ""
    current_units = 0.0
    for char in clean:
        units = char_width_units(char)
        if current and current_units + units > max_units and len(lines) < max_lines - 1:
            lines.append(current)
            current = char
            current_units = units
        else:
            current += char
            current_units += units
    if current:
        lines.append(current)
    return lines


def cover_title_lines(title: str) -> tuple[list[str], int, int]:
    units = text_width_units(title)
    if units <= 20:
        size = 50
        max_units = 20
    elif units <= 40:
        size = 42
        max_units = 22
    else:
        size = 34
        max_units = 24
    lines = wrap_text_by_units(title, max_units=max_units, max_lines=3)
    line_gap = round(size * 1.35)
    return lines, size, line_gap


def cover_title_svg(title: str) -> str:
    lines, size, line_gap = cover_title_lines(title)
    total_height = line_gap * (len(lines) - 1)
    start_y = 250 - total_height // 2
    return "\n".join(
        (
            f'  <text x="640" y="{start_y + index * line_gap}" text-anchor="middle" '
            f'font-family="Microsoft YaHei, Arial, sans-serif" font-size="{size}" '
            f'font-weight="700" fill="#1F2933">{xml_escape(line)}</text>'
        )
        for index, line in enumerate(lines)
    )


def round_up_16(value: int) -> int:
    return ((value + 15) // 16) * 16


def generation_size_for_region(region: dict[str, int]) -> dict[str, int]:
    width = round_up_16(region["width"] * IMAGE_GENERATION_SCALE)
    height = round_up_16(region["height"] * IMAGE_GENERATION_SCALE)
    while width * height < 655_360:
        if width / max(1, height) < region["width"] / max(1, region["height"]):
            width += 16
        else:
            height += 16
    return {"width": width, "height": height}


def parse_generation_size(size: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", size)
    if not match:
        raise ValueError(f"Invalid generation size: {size}")
    return int(match.group(1)), int(match.group(2))


def normalize_generated_image_size(image_path: Path, size: str) -> tuple[int, int]:
    target = parse_generation_size(size)
    with Image.open(image_path) as image:
        actual = image.size
        if actual == target:
            return actual
        target_ratio = target[0] / target[1]
        actual_ratio = actual[0] / actual[1]
        if actual[0] <= actual[1]:
            raise ValueError(
                f"generated image is portrait ({actual[0]}x{actual[1]}), expected landscape {size}"
            )
        ratio_drift = abs(actual_ratio - target_ratio) / target_ratio
        if ratio_drift > MAX_GENERATED_ASPECT_RATIO_DRIFT:
            raise ValueError(
                f"generated image aspect ratio {actual_ratio:.3f} differs from target {target_ratio:.3f}; "
                f"actual={actual[0]}x{actual[1]}, target={size}"
            )
        source = image.convert("RGB")
        scale = min(target[0] / actual[0], target[1] / actual[1])
        scaled_size = (
            max(1, round(actual[0] * scale)),
            max(1, round(actual[1] * scale)),
        )
        resized = source.resize(scaled_size, Image.Resampling.LANCZOS)
        background = source.getpixel((0, 0))
        canvas = Image.new("RGB", target, background)
        offset = ((target[0] - scaled_size[0]) // 2, (target[1] - scaled_size[1]) // 2)
        canvas.paste(resized, offset)
        canvas.save(image_path)
    return target


def generated_content_fill_report(image_path: Path) -> dict[str, object]:
    with Image.open(image_path) as image:
        source = image.convert("RGB")
        background = source.getpixel((0, 0))
        diff = ImageChops.difference(source, Image.new("RGB", source.size, background)).convert("L")
        mask = diff.point(lambda value: 255 if value > GENERATED_CONTENT_BACKGROUND_DIFF_THRESHOLD else 0)
        bbox = mask.getbbox()
        width, height = source.size
    if bbox is None:
        return {
            "image_size": f"{width}x{height}",
            "content_bbox": None,
            "content_width_ratio": 0.0,
            "left_margin_ratio": 1.0,
            "right_margin_ratio": 1.0,
        }
    left, top, right, bottom = bbox
    content_width = max(0, right - left)
    return {
        "image_size": f"{width}x{height}",
        "content_bbox": [left, top, right, bottom],
        "content_width_ratio": round(content_width / width, 4),
        "left_margin_ratio": round(left / width, 4),
        "right_margin_ratio": round((width - right) / width, 4),
    }


def assert_generated_content_fill(image_path: Path) -> dict[str, object]:
    report = generated_content_fill_report(image_path)
    width_ratio = float(report["content_width_ratio"])
    left_ratio = float(report["left_margin_ratio"])
    right_ratio = float(report["right_margin_ratio"])
    if (
        width_ratio < MIN_GENERATED_CONTENT_WIDTH_RATIO
        or left_ratio > MAX_GENERATED_SIDE_MARGIN_RATIO
        or right_ratio > MAX_GENERATED_SIDE_MARGIN_RATIO
    ):
        raise ValueError(
            "generated image has too much internal horizontal whitespace; "
            f"content_width_ratio={width_ratio:.3f}, "
            f"left_margin_ratio={left_ratio:.3f}, right_margin_ratio={right_ratio:.3f}, "
            f"image={image_path}"
        )
    return report


def _assert_exact_page_set(label: str, actual: set[int], pages: list[int]) -> None:
    expected = set(pages)
    if actual != expected:
        raise ValueError(
            f"{label} page set mismatch: expected {sorted(expected)}, got {sorted(actual)}"
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_exact_page_records(
    label: str,
    records: object,
    pages: list[int],
    *,
    page_key: str,
) -> list[dict]:
    if len(pages) != len(set(pages)):
        duplicates = sorted({page for page in pages if pages.count(page) > 1})
        raise ValueError(f"duplicate requested page {duplicates[0]}")
    if not isinstance(records, list):
        raise ValueError(f"{label} must contain records[]")
    expected = set(pages)
    by_page: dict[int, dict] = {}
    for record in records:
        if not isinstance(record, dict) or page_key not in record:
            raise ValueError(f"{label} record is missing {page_key}")
        page_number = int(record[page_key])
        if page_number in by_page:
            raise ValueError(f"duplicate {label} record for page {page_number}")
        by_page[page_number] = record
    if len(records) != len(expected):
        raise ValueError(
            f"{label} record count mismatch: expected {len(expected)}, got {len(records)}"
        )
    _assert_exact_page_set(label, set(by_page), pages)
    return [by_page[page_number] for page_number in pages]


def _resolve_recorded_path(value: object, *, base: Path, label: str) -> Path:
    if not value:
        raise ValueError(f"{label} is required")
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _locate_project_root(*approved_inputs: Path) -> Path:
    roots: set[Path] = set()
    for approved_input in approved_inputs:
        path = Path(approved_input).expanduser().resolve()
        for candidate in (path.parent, *path.parents):
            if (candidate / PROJECT_CONTRACT).is_file():
                roots.add(candidate)
                break
        else:
            raise ValueError(
                "project production requires approved inputs under a project containing "
                "workbench/analysis_expression/contract.json"
            )
    if len(roots) != 1:
        raise ValueError("project production approved inputs must belong to the same project")
    return roots.pop()


def _read_json_object(path: Path, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _validate_blueprint_image_review(
    project_root: Path,
    page_image_manifest: Path,
    pages: list[int],
    approved_images: dict[int, Path],
) -> None:
    stage_root = project_root / PROJECT_STAGE_ROOT
    approval_path = stage_root / "blueprint_image_review.approved.json"
    if not approval_path.is_file():
        raise ValueError("blueprint image review approval is required")
    approval = _read_json_object(approval_path, "blueprint image review approval")
    if approval.get("approved") is not True:
        raise ValueError("blueprint image review approval is required")
    review_path = _resolve_recorded_path(
        approval.get("artifact"), base=approval_path.parent, label="blueprint image review approval artifact"
    )
    expected_review = stage_root / "blueprint_image_review.json"
    if review_path != expected_review or not review_path.is_file():
        raise ValueError("blueprint image review approval artifact mismatch")
    review = _read_json_object(review_path, "blueprint image review")
    reviewed_manifest = _resolve_recorded_path(
        review.get("page_image_manifest"), base=review_path.parent, label="blueprint image review manifest"
    )
    if reviewed_manifest != page_image_manifest:
        raise ValueError("approved page image manifest path mismatch")
    if review.get("page_image_manifest_sha256") != _sha256(page_image_manifest):
        raise ValueError("approved page image manifest has changed")
    records = _require_exact_page_records(
        "approved blueprint image review", review.get("images"), pages, page_key="page"
    )
    for record in records:
        page_number = int(record["page"])
        image_path = _resolve_recorded_path(
            record.get("path"), base=review_path.parent, label=f"approved blueprint image path for page {page_number}"
        )
        if image_path != approved_images[page_number]:
            raise ValueError(f"approved blueprint image path mismatch for page {page_number}")
        if not image_path.is_file() or record.get("sha256") != _sha256(image_path):
            raise ValueError(f"approved blueprint image hash mismatch for page {page_number}")


def _validate_speaker_notes_review(project_root: Path, speaker_notes_manifest: Path) -> None:
    approval_path = project_root / PROJECT_STAGE_ROOT / "speaker_notes_review.approved.json"
    if not approval_path.is_file():
        raise ValueError("speaker notes approval is required")
    approval = _read_json_object(approval_path, "speaker notes review approval")
    if approval.get("approved") is not True:
        raise ValueError("speaker notes approval is required")
    approved_manifest = _resolve_recorded_path(
        approval.get("manifest"), base=approval_path.parent, label="speaker notes approval manifest"
    )
    if approved_manifest != speaker_notes_manifest:
        raise ValueError("approved speaker notes manifest path mismatch")
    if approval.get("manifest_sha256") != _sha256(speaker_notes_manifest):
        raise ValueError("approved speaker notes manifest has changed")


def load_template_text_lock(path: Path, pages: list[int]) -> dict[int, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records")
    if not isinstance(records, list):
        raise ValueError(f"template text lock must contain records[]: {path}")
    declared_pages = data.get("pages")
    if not isinstance(declared_pages, list):
        raise ValueError(f"template text lock must contain pages[]: {path}")
    if len(declared_pages) != len(set(declared_pages)):
        duplicates = sorted({int(page) for page in declared_pages if declared_pages.count(page) > 1})
        raise ValueError(f"duplicate template text lock declared page {duplicates[0]}")
    _assert_exact_page_set("template text lock", {int(item) for item in declared_pages}, pages)

    by_page: dict[int, dict] = {}
    for item in records:
        if not isinstance(item, dict) or "page" not in item:
            continue
        page_number = int(item["page"])
        if page_number in by_page:
            raise ValueError(f"duplicate template text lock record for page {page_number}")
        by_page[page_number] = item
    for page_number in pages:
        record = by_page.get(page_number)
        if record is None:
            raise ValueError(f"missing template text lock record for page {page_number}")
        if record.get("approved") is not True:
            raise ValueError(f"template text lock is not approved for page {page_number}")
    return by_page


def load_approved_full_images(
    path: Path, pages: list[int], *, project_root: Path | None = None
) -> dict[int, Path]:
    path = Path(path).expanduser().resolve()
    data = _read_json_object(path, "approved page image manifest")
    pairs = data.get("pairs")
    pairs = _require_exact_page_records(
        "approved page image manifest", pairs, pages, page_key="page_number"
    )
    images: dict[int, Path] = {}
    for item in pairs:
        page_number = int(item["page_number"])
        full = item.get("full")
        raw_path = full.get("path") if isinstance(full, dict) else None
        if not raw_path:
            raise ValueError(f"approved full image path is missing for page {page_number}")
        image_path = Path(str(raw_path)).expanduser()
        if not image_path.is_absolute():
            image_path = path.parent / image_path
        image_path = image_path.resolve()
        if not image_path.is_file():
            raise FileNotFoundError(
                f"approved full image is missing for page {page_number}: {image_path}"
            )
        images[page_number] = image_path
    if project_root is not None:
        _validate_blueprint_image_review(project_root, path, pages, images)
    return images


def _resolve_editable_path(raw: object, base: Path, label: str) -> Path:
    if not raw:
        raise ValueError(f"{label} is missing")
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    return path


def load_editable_body_pages(result_manifest: Path, pages: list[int]) -> dict[int, dict]:
    """Load passed vendor page JSON into a template-body rendering contract."""

    result_path = Path(result_manifest).expanduser().resolve()
    result = _read_json_object(result_path, "editable-text result manifest")
    records = result.get("pages")
    if not isinstance(records, dict):
        raise ValueError("editable-text result manifest must contain pages{}")
    result_pages: dict[int, dict] = {}
    for page_number in pages:
        raw_record = records.get(str(page_number))
        if not isinstance(raw_record, dict):
            raise ValueError(f"editable-text result is missing page {page_number}")
        if raw_record.get("status") != "passed":
            raise ValueError(f"editable-text page {page_number} is not passed")
        page_json = _resolve_editable_path(raw_record.get("page_json"), result_path.parent, f"page JSON for page {page_number}")
        payload = _read_json_object(page_json, f"page JSON for page {page_number}")
        page_meta = payload.get("page") if isinstance(payload.get("page"), dict) else {}
        width = int(page_meta.get("width_px", 0) or 0)
        height = int(page_meta.get("height_px", 0) or 0)
        if width <= 0 or height <= 0:
            raise ValueError(f"page {page_number} has invalid source canvas")
        images = payload.get("images") if isinstance(payload.get("images"), dict) else {}
        background_meta = images.get("background") if isinstance(images.get("background"), dict) else {}
        background = _resolve_editable_path(
            raw_record.get("background_path") or background_meta.get("path"),
            page_json.parent,
            f"background image for page {page_number}",
        )
        lines = payload.get("text_lines")
        if not isinstance(lines, list) or not lines:
            raise ValueError(f"page {page_number} has no editable text lines")
        normalized_lines: list[dict] = []
        for line in lines:
            if not isinstance(line, dict):
                raise ValueError(f"page {page_number} contains an invalid text line")
            text = str(line.get("text") or "")
            if not text or "\n" in text or "\r" in text:
                raise ValueError(f"page {page_number} contains newline or empty editable text")
            target = line.get("target") if isinstance(line.get("target"), dict) else {}
            bbox = target.get("bbox_px") if isinstance(target.get("bbox_px"), dict) else line.get("bbox")
            if not isinstance(bbox, dict) or not all(key in bbox for key in ("x", "y", "width", "height")):
                raise ValueError(f"page {page_number} line {line.get('line_id', '')} has no target bbox")
            normalized_lines.append({**line, "text": text, "bbox_px": {key: float(bbox[key]) for key in ("x", "y", "width", "height")}})
        result_pages[page_number] = {
            "page_number": page_number,
            "page_id": str(page_meta.get("page_id") or f"page-{page_number:03d}"),
            "canvas": {"width": width, "height": height},
            "background_path": background,
            "text_lines": normalized_lines,
        }
    return result_pages


def _map_editable_bbox(bbox: dict[str, float], canvas: dict[str, int], body: dict[str, int]) -> dict[str, float]:
    scale = min(body["width"] / canvas["width"], body["height"] / canvas["height"])
    offset_x = body["x"] + (body["width"] - canvas["width"] * scale) / 2
    offset_y = body["y"] + (body["height"] - canvas["height"] * scale) / 2
    return {
        "x": offset_x + bbox["x"] * scale,
        "y": offset_y + bbox["y"] * scale,
        "width": bbox["width"] * scale,
        "height": bbox["height"] * scale,
    }


def render_editable_body_svg(page: dict, body_region: dict[str, int], canvas: dict[str, int]) -> str:
    """Render a background plus stable, native-convertible SVG text boxes."""

    background = Path(page["background_path"])
    if not background.is_file():
        raise FileNotFoundError(f"editable background is missing: {background}")
    image_href = "../images/" + background.name
    body = body_region
    parts = [
        f'<image x="{body["x"]}" y="{body["y"]}" width="{body["width"]}" height="{body["height"]}" href={quoteattr(image_href)} xlink:href={quoteattr(image_href)} preserveAspectRatio="xMidYMid meet"/>',
    ]
    for line in page["text_lines"]:
        mapped = _map_editable_bbox(line["bbox_px"], canvas, body)
        font_size = max(6.5, mapped["height"] * 0.75)
        line_id = str(line.get("line_id") or "line")
        name = f'text-{page["page_number"]}-{line_id}'
        parts.append(
            f'<text id={quoteattr(name)} data-pptx-name={quoteattr(name)} '
            f'x="{fmt(mapped["x"])}" y="{fmt(mapped["y"] + font_size * 0.85)}" '
            f'data-pptx-width="{fmt(mapped["width"])}" font-family="Microsoft YaHei" '
            f'font-size="{fmt(font_size)}" fill="#123B66" xml:space="preserve">'
            f'{xml_escape(str(line["text"]))}</text>'
        )
    return "\n".join(parts)


def approved_image_content_region(path: Path) -> dict[str, int] | None:
    data = _read_json_object(Path(path).expanduser().resolve(), "approved page image manifest")
    contract = data.get("generation_contract")
    if not isinstance(contract, dict):
        return None
    region = contract.get("content_region")
    if not isinstance(region, dict):
        return None
    required = ("x", "y", "width", "height")
    if any(key not in region for key in required):
        return None
    return {key: int(region[key]) for key in required}


def _load_approved_speaker_notes(
    path: Path, pages: list[int], *, project_root: Path | None = None
) -> dict[int, dict]:
    path = Path(path).expanduser().resolve()
    data = _read_json_object(path, "approved speaker notes manifest")
    records = _require_exact_page_records(
        "approved speaker notes", data.get("notes"), pages, page_key="page_number"
    )
    declared_pages = data.get("pages")
    if not isinstance(declared_pages, list):
        raise ValueError(f"approved speaker notes manifest must contain pages[]: {path}")
    if len(declared_pages) != len(set(declared_pages)):
        duplicates = sorted({int(page) for page in declared_pages if declared_pages.count(page) > 1})
        raise ValueError(f"duplicate approved speaker notes declared page {duplicates[0]}")
    _assert_exact_page_set("approved speaker notes manifest", {int(page) for page in declared_pages}, pages)
    notes = {int(record["page_number"]): record for record in records}
    if project_root is not None:
        _validate_speaker_notes_review(project_root, path)
    return notes


def build_manifest(
    script_path: Path,
    page_numbers: list[int] | None = None,
    pages: dict[int, PageBlock] | None = None,
    output_dir: Path | None = None,
    *,
    selected_pages: list[int] | None = None,
    image_style_name: str | None = None,
    speaker_notes_manifest: Path | None = None,
    template_text_lock: Path | None = None,
    page_image_manifest: Path | None = None,
    project_production: bool = False,
) -> dict:
    script_path = Path(script_path)
    pages = pages if pages is not None else parse_page_blocks(script_path)
    if selected_pages is not None:
        if page_numbers is not None and list(page_numbers) != list(selected_pages):
            raise ValueError("page_numbers and selected_pages must match when both are provided")
        page_numbers = list(selected_pages)
    if page_numbers is None:
        page_numbers = sorted(pages)
    missing_script_pages = sorted(set(page_numbers) - set(pages))
    if missing_script_pages:
        raise ValueError(f"Pages not found in script: {missing_script_pages}")
    if output_dir is None:
        raise ValueError("output_dir is required")
    output_dir = Path(output_dir)

    template_locks: dict[int, dict] = {}
    approved_images: dict[int, Path] = {}
    if project_production:
        if template_text_lock is None:
            raise ValueError("metadata_required: --template-text-lock is required")
        if page_image_manifest is None:
            raise ValueError("approved page image manifest is required")
        if speaker_notes_manifest is None:
            raise ValueError("approved speaker notes manifest is required")
        template_locks = load_template_text_lock(Path(template_text_lock), page_numbers)
        project_root = _locate_project_root(
            Path(template_text_lock), Path(page_image_manifest), Path(speaker_notes_manifest)
        )
        approved_images = load_approved_full_images(
            Path(page_image_manifest), page_numbers, project_root=project_root
        )
        speaker_notes = _load_approved_speaker_notes(
            Path(speaker_notes_manifest), page_numbers, project_root=project_root
        )
    else:
        speaker_notes = load_speaker_notes(speaker_notes_manifest)

    rules = load_brand_rules()
    brand_body_region = scale_region(rules["content_regions"]["body_pages"], CANVAS_SIZE)
    body_region = inset_content_region(brand_body_region)
    generation_size = generation_size_for_region(body_region)
    image_style = load_image_style(image_style_name)
    if project_production:
        agenda_items = []
        for number in page_numbers:
            page = pages[number]
            if page_role(page) != "section":
                continue
            record = template_locks[number]
            locked_title = str(record.get("title") or "")
            fallback_label, section_title = chapter_label_and_title(locked_title)
            agenda_items.append(
                {
                    "label": str(record.get("section") or fallback_label),
                    "title": section_title,
                }
            )
    else:
        agenda_items = agenda_items_from_pages(pages, page_numbers)
    tasks = []
    for number in page_numbers:
        page = pages[number]
        role = page_role(page)
        content = extract_content(page)
        lock_record = template_locks.get(number)
        if lock_record is not None:
            task_title = str(lock_record.get("title") or "")
            content = PageContent(
                title=task_title,
                subtitle=str(lock_record.get("subtitle") or ""),
                body=content.body,
            )
        else:
            task_title = page.title
        stem = page_stem(number, task_title)
        task = {
            "page_number": number,
            "page_role": role,
            "title": task_title,
            "slide_title": content.title,
            "subtitle": content.subtitle,
            "body_text": content.body,
        }
        if lock_record is not None:
            task.update(
                {
                    "section": str(lock_record.get("section") or ""),
                    "template_variant": str(lock_record.get("template_variant") or "default"),
                    "page_badge_enabled": bool(lock_record.get("page_badge_enabled", False)),
                    "footer_enabled": bool(lock_record.get("footer_enabled", False)),
                }
            )
        template_name = page_template_name(role)
        if template_name:
            task.update(
                {
                    "render_mode": "brand-template",
                    "template": template_name,
                    "status": "Template",
                }
            )
            if template_name == "agenda":
                task["agenda_items"] = agenda_items
            elif template_name == "section":
                if lock_record is not None:
                    label = str(lock_record.get("section") or "")
                    fallback_label, section_title = chapter_label_and_title(task_title)
                    label = label or fallback_label
                else:
                    label, section_title = chapter_label_and_title(page.title)
                task["section_no"] = label
                task["section_title"] = section_title
        else:
            image_path = (
                approved_images[number]
                if project_production
                else output_dir / "images" / f"{stem}_content.png"
            )
            prompt = content_prompt(page, content, body_region, generation_size, role, image_style)
            validate_image_prompt_text(number, prompt)
            task.update(
                {
                    "render_mode": "content-image",
                    "image_path": str(image_path),
                    "prompt": prompt,
                    "size": f"{generation_size['width']}x{generation_size['height']}",
                    "status": "Approved" if project_production else "Pending",
                }
            )
        note_record = speaker_notes.get(number)
        if note_record is not None:
            task["notes_text"] = str(note_record.get("notes_text") or "")
            task["notes_source"] = (
                "approved_speaker_notes"
                if project_production
                else str(note_record.get("source") or "speaker_notes_manifest")
            )
            task["notes_title"] = str(note_record.get("title") or notes_heading_for_task(task))
        else:
            task["notes_text"] = page_notes_text_for_task(page, task)
            task["notes_source"] = "fallback_from_page_script"
        validate_task_role_contract(task)
        tasks.append(task)
    manifest = {
        "mode": "template-image-ppt",
        "project_production": project_production,
        "source_script": str(script_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canvas": {"width": CANVAS_SIZE[0], "height": CANVAS_SIZE[1]},
        "brand_body_region": brand_body_region,
        "body_region": body_region,
        "body_region_inset": {
            "top": CONTENT_REGION_TOP_INSET,
            "bottom": CONTENT_REGION_BOTTOM_INSET,
            "side_outset": CONTENT_REGION_SIDE_OUTSET,
        },
        "image_style": {
            "name": style_name(image_style),
            "source_path": image_style.get("source_path", ""),
        },
        "image_generation_scale": IMAGE_GENERATION_SCALE,
        "generation_size": generation_size,
        "speaker_notes_manifest": str(speaker_notes_manifest) if speaker_notes_manifest else None,
        "template_text_lock": str(template_text_lock) if template_text_lock else None,
        "page_image_manifest": str(page_image_manifest) if page_image_manifest else None,
        "approved_image_content_region": (
            approved_image_content_region(Path(page_image_manifest)) if page_image_manifest else None
        ),
        "tasks": tasks,
    }
    validate_manifest_contract(manifest)
    return manifest


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_speaker_notes(notes_manifest: Path | None) -> dict[int, dict]:
    if notes_manifest is None:
        return {}
    data = json.loads(notes_manifest.read_text(encoding="utf-8"))
    notes = data.get("notes")
    if not isinstance(notes, list):
        raise ValueError(f"speaker notes manifest must contain notes[]: {notes_manifest}")
    by_page: dict[int, dict] = {}
    for item in notes:
        if not isinstance(item, dict):
            continue
        page_number = int(item.get("page_number"))
        by_page[page_number] = item
    return by_page


def copy_brand(project_path: Path, brand_dir: Path = DEFAULT_BRAND_DIR) -> None:
    for sub in ("templates", "images"):
        (project_path / sub).mkdir(parents=True, exist_ok=True)
    for source in brand_dir.iterdir():
        if not source.is_file():
            continue
        target = project_path / ("images" if source.suffix.lower() in {".png", ".jpg", ".jpeg"} else "templates") / source.name
        shutil.copy2(source, target)


def crop_approved_content_image(source: Path, target: Path, region: dict[str, int] | None) -> Path:
    if not region:
        shutil.copy2(source, target)
        return target
    with Image.open(source) as image:
        width, height = image.size
        left = max(0, min(width, int(region["x"])))
        top = max(0, min(height, int(region["y"])))
        right = max(left + 1, min(width, left + int(region["width"])))
        bottom = max(top + 1, min(height, top + int(region["height"])))
        image.convert("RGB").crop((left, top, right, bottom)).save(target)
    return target


def fmt(value: float | int) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0").rstrip(".")


def write_spec_lock(
    project_path: Path,
    rules: dict,
    pixel_size: tuple[int, int],
    tasks: list[dict] | None = None,
) -> None:
    width, height = pixel_size

    def sx(v: float | int) -> str:
        return fmt(float(v) * width / CANVAS_SIZE[0])

    def sy(v: float | int) -> str:
        return fmt(float(v) * height / CANVAS_SIZE[1])

    master = rules.get("master_elements") or {}
    lines = [
        "# Spec Lock",
        "",
        "## canvas",
        f"- width: {width}",
        f"- height: {height}",
        "",
        "## master_chrome",
    ]
    top = master.get("top_divider") or {}
    footer = master.get("footer_bar") or {}
    logo = master.get("logo") or {}
    org = master.get("footer_company_text") or {}
    num = master.get("footer_page_num") or {}
    if top:
        lines.append(f"- top_divider: rect x=0 y={sy(top.get('y', 82))} w={width} h={sy(top.get('height', 7))} fill={top.get('fill', '#8B0000')}")
    if footer:
        lines.append(f"- footer_bar: rect x=0 y={sy(footer.get('y', 696))} w={width} h={sy(footer.get('height', 24))} fill={footer.get('fill', '#003366')}")
    if logo:
        lines.append(f"- logo: image x={sx(logo.get('x', 1060))} y={sy(logo.get('y', 16))} w={sx(logo.get('width', 189))} h={sy(logo.get('height', 63))} href=../images/logo.png")
    if org:
        lines.append(f"- footer_org_text: x={sx(org.get('x', 40))} y={sy(org.get('y', 712))} size={sy(org.get('font_size', 10))} fill={org.get('fill', '#FFFFFF')} text=\"{org.get('text', '中国电力企业联合会')}\"")
    if num:
        lines.append(f"- footer_page_num: x={sx(num.get('x', 1240))} y={sy(num.get('y', 712))} size={sy(num.get('font_size', 10))} fill={num.get('fill', '#FFFFFF')} mono dynamic")
    page_layouts: list[str] = []
    for task in tasks or []:
        if task.get("render_mode") != "brand-template":
            continue
        template_name = task.get("template") or page_template_name(str(task.get("page_role") or ""))
        if template_name:
            page_layouts.append(f"- P{int(task['page_number'])}: {template_name}")
    if page_layouts:
        lines.extend(["", "## page_layouts", *page_layouts])
    (project_path / "spec_lock.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_text(x: int, y: int, text: str, size: int, weight: int = 400, fill: str = "#123B66") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Microsoft YaHei, PingFang SC, Arial" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{xml_escape(text)}</text>'
    )


def template_href_for_output(svg: str) -> str:
    return svg.replace('xlink:href="cover_bg.jpg"', 'xlink:href="../images/cover_bg.jpg"').replace(
        'href="cover_bg.jpg"', 'href="../images/cover_bg.jpg"'
    )


def cover_slide_svg_only(svg: str) -> str:
    svg = re.sub(r'\s*<image\b[^>]*(?:xlink:href|href)="../images/cover_bg\.jpg"[^>]*/>', '', svg, count=1)
    svg = re.sub(r'\s*<g id="cover-decor">.*?</g>', '', svg, flags=re.S, count=1)
    return svg


def render_brand_template_svg(task: dict, rules: dict, *, slide_layer_only: bool = False) -> str:
    template_name = task.get("template") or page_template_name(task.get("page_role", ""))
    templates = rules.get("brand_page_templates") or {}
    template_info = templates.get(template_name) or {}
    template_file = template_info.get("file")
    if not template_file:
        raise ValueError(f"Missing brand template file for {template_name!r}")
    svg = (DEFAULT_BRAND_DIR / template_file).read_text(encoding="utf-8")
    svg = template_href_for_output(svg)
    if template_name == "cover":
        title, author, date = cover_content_fields(task)
        svg = re.sub(
            r'\s*<text[^>]*>\{\{TITLE\}\}</text>',
            "\n" + cover_title_svg(title),
            svg,
            count=1,
        )
        replacements = {
            "{{AUTHOR}}": author,
            "{{DATE}}": date,
        }
        for placeholder, value in replacements.items():
            svg = svg.replace(placeholder, xml_escape(value))
        if slide_layer_only:
            svg = cover_slide_svg_only(svg)
    elif template_name == "agenda":
        items = task.get("agenda_items")
        svg = svg.replace("{{AGENDA_ITEMS}}", agenda_items_svg(items if isinstance(items, list) else []))
    elif template_name == "section":
        label = str(task.get("section_no") or "")
        title = str(task.get("section_title") or task.get("slide_title") or task.get("title") or "")
        svg = svg.replace("{{SECTION_NO}}", xml_escape(label))
        svg = svg.replace("{{SECTION_TITLE}}", xml_escape(title))
    return svg


def write_project(manifest: dict, output_dir: Path, name: str) -> Path:
    project_path = output_dir / f"{sanitize_name(name)}_template_image_project"
    if project_path.exists():
        shutil.rmtree(project_path)
    for sub in ("svg_output", "notes", "templates", "images", "exports"):
        (project_path / sub).mkdir(parents=True, exist_ok=True)
    rules = load_brand_rules()
    copy_brand(project_path)
    write_spec_lock(
        project_path,
        rules,
        (manifest["canvas"]["width"], manifest["canvas"]["height"]),
        manifest.get("tasks"),
    )
    header = scale_region(rules["content_regions"]["body_header_region"], CANVAS_SIZE)
    body = manifest["body_region"]
    source_pages: dict[int, PageBlock] = {}
    source_script = manifest.get("source_script")
    if source_script:
        source_path = Path(source_script)
        if source_path.is_file():
            source_pages = parse_page_blocks(source_path)
    approved_image_region = manifest.get("approved_image_content_region")
    if not isinstance(approved_image_region, dict):
        approved_image_region = None
    editable_pages: dict[int, dict] = {}
    editable_manifest = manifest.get("editable_body_manifest")
    if editable_manifest:
        editable_page_numbers = [
            int(task["page_number"])
            for task in manifest["tasks"]
            if task.get("editable_body") is True and task.get("page_number") is not None
        ]
        editable_pages = load_editable_body_pages(Path(str(editable_manifest)), editable_page_numbers)
    for task in manifest["tasks"]:
        stem = page_stem(task["page_number"], task["title"])
        if task.get("render_mode") == "brand-template" or page_template_name(task.get("page_role", "")):
            svg_text_content = render_brand_template_svg(
                task,
                rules,
                slide_layer_only=(task.get("template") or page_template_name(task.get("page_role", ""))) == "cover",
            )
        else:
            image_path = Path(task["image_path"]).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"Missing content image: {image_path}")
            svg = [
                f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{CANVAS_SIZE[0]}" height="{CANVAS_SIZE[1]}" viewBox="0 0 {CANVAS_SIZE[0]} {CANVAS_SIZE[1]}">',
                f'<rect x="0" y="0" width="{CANVAS_SIZE[0]}" height="{CANVAS_SIZE[1]}" fill="#FFFFFF"/>',
            ]
            svg.append(svg_text(header["x"], header["y"] + 30, task["slide_title"], 25, 700))
            if task.get("subtitle"):
                svg.append(svg_text(header["x"], header["y"] + 56, task["subtitle"], 14, 400, "#60758A"))
            if task.get("editable_body") is True:
                editable_page = editable_pages[int(task["page_number"])]
                source_background = Path(editable_page["background_path"])
                target_image = project_path / "images" / f"page_{int(task['page_number']):03d}_{source_background.name}"
                shutil.copy2(source_background, target_image)
                editable_page = {**editable_page, "background_path": target_image}
                svg.append(render_editable_body_svg(editable_page, body, editable_page["canvas"]))
            else:
                target_image = project_path / "images" / f"{image_path.stem}_content_crop{image_path.suffix}"
                crop_approved_content_image(image_path, target_image, approved_image_region)
                svg.append(
                    f'<image x="{body["x"]}" y="{body["y"]}" width="{body["width"]}" height="{body["height"]}" '
                    f'href={quoteattr("../images/" + target_image.name)} xlink:href={quoteattr("../images/" + target_image.name)} preserveAspectRatio="xMidYMid meet"/>'
                )
            svg.append("</svg>\n")
            svg_text_content = "\n".join(svg)
        (project_path / "svg_output" / f"{stem}.svg").write_text(svg_text_content, encoding="utf-8")
        notes_text = task.get("notes_text")
        if notes_text is None:
            source_page = source_pages.get(int(task["page_number"]))
            notes_text = page_notes_text(source_page) if source_page else task.get("body_text", "")
        notes_heading = str(task.get("notes_title") or notes_heading_for_task(task))
        (project_path / "notes" / f"{stem}.md").write_text(
            f"# {notes_heading}\n\n{notes_text}\n",
            encoding="utf-8",
        )
    write_json(project_path / "template_image_manifest.json", manifest)
    return project_path


def run_export(project_path: Path) -> Path:
    cmd = [sys.executable, str(SCRIPTS_DIR / "svg_to_pptx.py"), str(project_path)]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"svg_to_pptx failed with exit code {result.returncode}")
    exports = sorted((project_path / "exports").glob("*.pptx"), key=lambda p: p.stat().st_mtime)
    if not exports:
        raise FileNotFoundError(f"No PPTX produced in {project_path / 'exports'}")
    return exports[-1]


def command_plan(args: argparse.Namespace) -> int:
    script = args.script.resolve()
    pages = parse_page_blocks(script)
    nums = parse_page_selection(args.pages, set(pages))
    output_dir = args.output_dir.resolve()
    speaker_notes_manifest = args.speaker_notes_manifest.resolve() if args.speaker_notes_manifest else None
    manifest = build_manifest(
        script,
        nums,
        pages,
        output_dir,
        image_style_name=args.image_style,
        speaker_notes_manifest=speaker_notes_manifest,
    )
    write_json(output_dir / "template_image_manifest.json", manifest)
    prompt_blocks = []
    for task in manifest["tasks"]:
        if task.get("render_mode") == "brand-template":
            prompt_blocks.append(f"## 第{task['page_number']}页：{task['title']}\n\n套用品牌模板：`{task['template']}`\n")
        else:
            prompt_blocks.append(f"## 第{task['page_number']}页：{task['title']}\n\n保存到：`{task['image_path']}`\n\n{task['prompt']}")
    (output_dir / "template_image_prompts.md").write_text("\n\n".join(prompt_blocks) + "\n", encoding="utf-8")
    print(output_dir / "template_image_manifest.json")
    return 0


def command_plan_dispatch(args: argparse.Namespace) -> int:
    if not getattr(args, "project_production", False):
        return command_plan(args)

    script = args.script.resolve()
    pages = parse_page_blocks(script)
    nums = parse_page_selection(args.pages, set(pages))
    output_dir = args.output_dir.resolve()
    manifest = build_manifest(
        script_path=script,
        selected_pages=nums,
        pages=pages,
        output_dir=output_dir,
        image_style_name=args.image_style,
        speaker_notes_manifest=(
            args.speaker_notes_manifest.resolve() if args.speaker_notes_manifest else None
        ),
        template_text_lock=(args.template_text_lock.resolve() if args.template_text_lock else None),
        page_image_manifest=(args.page_image_manifest.resolve() if args.page_image_manifest else None),
        project_production=True,
    )
    write_json(output_dir / "template_image_manifest.json", manifest)
    print(output_dir / "template_image_manifest.json")
    return 0


def command_generate(args: argparse.Namespace) -> int:
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for task in manifest["tasks"]:
        if task.get("render_mode") == "brand-template" or page_template_name(task.get("page_role", "")):
            task["status"] = "Template"
            continue
        image_path = Path(task["image_path"])
        if image_path.exists() and not args.force:
            normalized_size = normalize_generated_image_size(image_path, args.size or task["size"])
            fill_report = assert_generated_content_fill(image_path)
            task["status"] = "Generated"
            task["actual_size"] = f"{normalized_size[0]}x{normalized_size[1]}"
            task["content_fill"] = fill_report
            continue
        run_codex_image(
            prompt=task["prompt"],
            output_path=image_path,
            image_paths=[],
            model=args.model,
            size=args.size or task["size"],
            quality=args.quality,
            force=True,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
        if not args.dry_run:
            normalized_size = normalize_generated_image_size(image_path, args.size or task["size"])
            fill_report = assert_generated_content_fill(image_path)
            task["status"] = "Generated"
            task["generated_at"] = datetime.now(timezone.utc).isoformat()
            task["actual_size"] = f"{normalized_size[0]}x{normalized_size[1]}"
            task["content_fill"] = fill_report
    write_json(manifest_path, manifest)
    return 0


def command_export(args: argparse.Namespace) -> int:
    manifest = json.loads(args.manifest.resolve().read_text(encoding="utf-8"))
    project_path = write_project(manifest, args.output_dir.resolve(), args.name)
    pptx = run_export(project_path)
    print(f"Project: {project_path}")
    print(f"PPTX: {pptx}")
    return 0


def command_run(args: argparse.Namespace) -> int:
    rc = command_plan_dispatch(args)
    if rc != 0 or args.dry_run:
        return rc
    manifest = args.output_dir.resolve() / "template_image_manifest.json"
    if getattr(args, "editable_body_manifest", None):
        editable_manifest = args.editable_body_manifest.resolve()
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        content_pages = [
            int(task["page_number"])
            for task in manifest_data.get("tasks", [])
            if isinstance(task, dict) and task.get("render_mode") == "content-image"
        ]
        load_editable_body_pages(editable_manifest, content_pages)
        manifest_data["editable_body_manifest"] = str(editable_manifest)
        for task in manifest_data["tasks"]:
            if task.get("render_mode") == "content-image":
                task["editable_body"] = True
        write_json(manifest, manifest_data)
    if getattr(args, "project_production", False):
        return command_export(
            argparse.Namespace(manifest=manifest, output_dir=args.output_dir, name=args.name)
        )
    gen_args = argparse.Namespace(
        manifest=manifest,
        model=args.model,
        size=args.size,
        quality=args.quality,
        timeout=args.timeout,
        force=args.force,
        dry_run=False,
    )
    rc = command_generate(gen_args)
    if rc != 0:
        return rc
    return command_export(argparse.Namespace(manifest=manifest, output_dir=args.output_dir, name=args.name))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate image-based PPT inside the CEC template.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        p = sub.add_parser(name)
        p.add_argument("--script", required=True, type=Path)
        p.add_argument("--pages", default="all")
        p.add_argument("-o", "--output-dir", required=True, type=Path)
        p.add_argument("--name", default="template_image_ppt")
        p.add_argument("--model", default="gpt-image-2")
        p.add_argument("--size", default=None, help="Override image generation size. Defaults to template body region.")
        p.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="high")
        p.add_argument("--timeout", type=int, default=300)
        p.add_argument("--force", action="store_true")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--image-style", default=DEFAULT_STYLE_NAME, help="Image style preset name or style JSON/Markdown path.")
        p.add_argument("--speaker-notes-manifest", type=Path, help="Optional business-script speaker notes manifest.")
        p.add_argument("--project-production", action="store_true")
        p.add_argument("--template-text-lock", type=Path)
        p.add_argument("--page-image-manifest", type=Path)
        p.add_argument("--editable-body-manifest", type=Path)
        p.set_defaults(func=command_plan_dispatch if name == "plan" else command_run)
    gen = sub.add_parser("generate")
    gen.add_argument("manifest", type=Path)
    gen.add_argument("--model", default="gpt-image-2")
    gen.add_argument("--size", default=None)
    gen.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="high")
    gen.add_argument("--timeout", type=int, default=300)
    gen.add_argument("--force", action="store_true")
    gen.add_argument("--dry-run", action="store_true")
    gen.set_defaults(func=command_generate)
    exp = sub.add_parser("export")
    exp.add_argument("manifest", type=Path)
    exp.add_argument("-o", "--output-dir", required=True, type=Path)
    exp.add_argument("--name", default="template_image_ppt")
    exp.set_defaults(func=command_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
