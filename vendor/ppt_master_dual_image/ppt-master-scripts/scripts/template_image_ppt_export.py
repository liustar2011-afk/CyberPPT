#!/usr/bin/env python3
"""Template-image PPT export.

Generate image-based PPT pages where AI output is constrained to the template
content region; title, subtitle, master chrome, footer and page numbers are
created by the PPT pipeline.
"""

from __future__ import annotations

import argparse
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

from PIL import Image

from codex_oauth_image import run_codex_image
from image_prompt_styles import DEFAULT_STYLE_NAME, load_image_style, style_name, style_prompt_block
from project_manager import sanitize_name

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
DEFAULT_BRAND_DIR = SKILL_DIR / "templates" / "brands" / "中电联公共元素_轻量版"
PAGE_HEADING_RE = re.compile(r"^##\s*第(?P<num>\d+)页[:：](?P<title>.+?)\s*$", re.M)
MODULE_PREFIX_RE = re.compile(r"^模块[一二三四五六七八九十百千万0-9]+[:：]\s*")
MODULE_MARKER_RE = re.compile(r"模块[一二三四五六七八九十百千万0-9]+[:：]?\s*")
IMAGEGEN_NON_VISIBLE_SECTION_RE = re.compile(
    r"\n(?:保真约束[:：]|【(?:保真约束|构图指令|构图接口)】)"
)
COMPOSITION_SECTION_RE = re.compile(r"【(?:构图指令|构图接口)】(?P<body>.*)$", re.S)
CANVAS_SIZE = (1280, 720)
CONTENT_REGION_TOP_INSET = -24
CONTENT_REGION_BOTTOM_INSET = -11
CONTENT_REGION_SIDE_OUTSET = 26
IMAGE_GENERATION_SCALE = 2


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
- 可见文字只能取自下面“正文内容”中的事实、概念、数字和短语；可以压缩、取舍、重组，但不得新增事实、数字、口号、英文伪字、水印、乱码。
- 脚本里的结构编号只用于分组理解，不得作为画面文字出现，也不得按原编号抄写。

{style_prompt_block(image_style)}

正文内容：
{visible_text}

构图要求：
{extract_composition_instruction(page)}
"""


def page_template_name(role: str) -> str | None:
    if role == "cover":
        return "cover"
    if role == "ending":
        return "ending"
    return None


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
        resized = image.convert("RGBA").resize(target, Image.Resampling.LANCZOS)
        resized.save(image_path)
    return target


def build_manifest(
    script_path: Path,
    page_numbers: list[int],
    pages: dict[int, PageBlock],
    output_dir: Path,
    *,
    image_style_name: str | None = None,
) -> dict:
    rules = load_brand_rules()
    brand_body_region = scale_region(rules["content_regions"]["body_pages"], CANVAS_SIZE)
    body_region = inset_content_region(brand_body_region)
    generation_size = generation_size_for_region(body_region)
    image_style = load_image_style(image_style_name)
    tasks = []
    for number in page_numbers:
        page = pages[number]
        role = page_role(page)
        content = extract_content(page)
        stem = page_stem(number, page.title)
        task = {
            "page_number": number,
            "page_role": role,
            "title": page.title,
            "slide_title": content.title,
            "subtitle": content.subtitle,
            "body_text": content.body,
            "notes_text": page_notes_text(page),
        }
        template_name = page_template_name(role)
        if template_name:
            task.update(
                {
                    "render_mode": "brand-template",
                    "template": template_name,
                    "status": "Template",
                }
            )
        else:
            image_path = output_dir / "images" / f"{stem}_content.png"
            task.update(
                {
                    "render_mode": "content-image",
                    "image_path": str(image_path),
                    "prompt": content_prompt(page, content, body_region, generation_size, role, image_style),
                    "size": f"{generation_size['width']}x{generation_size['height']}",
                    "status": "Pending",
                }
            )
        tasks.append(task)
    return {
        "mode": "template-image-ppt",
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
        "tasks": tasks,
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_brand(project_path: Path, brand_dir: Path = DEFAULT_BRAND_DIR) -> None:
    for sub in ("templates", "images"):
        (project_path / sub).mkdir(parents=True, exist_ok=True)
    for source in brand_dir.iterdir():
        if not source.is_file():
            continue
        target = project_path / ("images" if source.suffix.lower() in {".png", ".jpg", ".jpeg"} else "templates") / source.name
        shutil.copy2(source, target)


def fmt(value: float | int) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0").rstrip(".")


def write_spec_lock(project_path: Path, rules: dict, pixel_size: tuple[int, int]) -> None:
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


def render_brand_template_svg(task: dict, rules: dict) -> str:
    template_name = task.get("template") or page_template_name(task.get("page_role", ""))
    templates = rules.get("brand_page_templates") or {}
    template_info = templates.get(template_name) or {}
    template_file = template_info.get("file")
    if not template_file:
        raise ValueError(f"Missing brand template file for {template_name!r}")
    svg = (DEFAULT_BRAND_DIR / template_file).read_text(encoding="utf-8")
    svg = template_href_for_output(svg)
    if template_name == "cover":
        content = PageContent(task.get("slide_title", ""), task.get("subtitle", ""), task.get("body_text", ""))
        title = task.get("slide_title") or task.get("title", "")
        svg = re.sub(
            r'\s*<text[^>]*>\{\{TITLE\}\}</text>',
            "\n" + cover_title_svg(title),
            svg,
            count=1,
        )
        replacements = {
            "{{AUTHOR}}": cover_author(content),
            "{{DATE}}": cover_date(content),
        }
        for placeholder, value in replacements.items():
            svg = svg.replace(placeholder, xml_escape(value))
    return svg


def write_project(manifest: dict, output_dir: Path, name: str) -> Path:
    project_path = output_dir / f"{sanitize_name(name)}_template_image_project"
    if project_path.exists():
        shutil.rmtree(project_path)
    for sub in ("svg_output", "notes", "templates", "images", "exports"):
        (project_path / sub).mkdir(parents=True, exist_ok=True)
    rules = load_brand_rules()
    copy_brand(project_path)
    write_spec_lock(project_path, rules, (manifest["canvas"]["width"], manifest["canvas"]["height"]))
    header = scale_region(rules["content_regions"]["body_header_region"], CANVAS_SIZE)
    body = manifest["body_region"]
    source_pages: dict[int, PageBlock] = {}
    source_script = manifest.get("source_script")
    if source_script:
        source_path = Path(source_script)
        if source_path.is_file():
            source_pages = parse_page_blocks(source_path)
    for task in manifest["tasks"]:
        stem = page_stem(task["page_number"], task["title"])
        if task.get("render_mode") == "brand-template" or page_template_name(task.get("page_role", "")):
            svg_text_content = render_brand_template_svg(task, rules)
        else:
            image_path = Path(task["image_path"]).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"Missing content image: {image_path}")
            target_image = project_path / "images" / image_path.name
            shutil.copy2(image_path, target_image)
            svg = [
                f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1280" height="720" viewBox="0 0 1280 720">',
                '<rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>',
            ]
            svg.append(svg_text(header["x"], header["y"] + 30, task["slide_title"], 25, 700))
            if task.get("subtitle"):
                svg.append(svg_text(header["x"], header["y"] + 56, task["subtitle"], 14, 400, "#60758A"))
            svg.append(
                f'<image x="{body["x"]}" y="{body["y"]}" width="{body["width"]}" height="{body["height"]}" '
                f'href={quoteattr("../images/" + target_image.name)} xlink:href={quoteattr("../images/" + target_image.name)} preserveAspectRatio="xMidYMid meet"/>'
            )
            svg.append("</svg>\n")
            svg_text_content = "\n".join(svg)
        (project_path / "svg_output" / f"{stem}.svg").write_text(svg_text_content, encoding="utf-8")
        notes_text = task.get("notes_text")
        if not notes_text:
            source_page = source_pages.get(int(task["page_number"]))
            notes_text = page_notes_text(source_page) if source_page else task.get("body_text", "")
        (project_path / "notes" / f"{stem}.md").write_text(
            f"# {task['slide_title']}\n\n{notes_text}\n",
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
    manifest = build_manifest(script, nums, pages, output_dir, image_style_name=args.image_style)
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


def command_generate(args: argparse.Namespace) -> int:
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for task in manifest["tasks"]:
        if task.get("render_mode") == "brand-template" or page_template_name(task.get("page_role", "")):
            task["status"] = "Template"
            continue
        image_path = Path(task["image_path"])
        if image_path.exists() and not args.force:
            task["status"] = "Generated"
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
            task["status"] = "Generated"
            task["generated_at"] = datetime.now(timezone.utc).isoformat()
            task["actual_size"] = f"{normalized_size[0]}x{normalized_size[1]}"
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
    rc = command_plan(args)
    if rc != 0 or args.dry_run:
        return rc
    manifest = args.output_dir.resolve() / "template_image_manifest.json"
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
        p.set_defaults(func=command_plan if name == "plan" else command_run)
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
