#!/usr/bin/env python3
"""Compile final-deliverable image prompts for dual-image generation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dual_image_overlay.style_library import default_style_choices, load_style_lock


PAGE_HEADING_RE = re.compile(
    r"^##\s*(?:第(?P<num_cn>\d+)页[:：]|P(?P<num_p>\d+)\s+)(?P<title>.+?)\s*$",
    re.M,
)
FENCE_RE = re.compile(r"^\s*```.*?$")
EVIDENCE_LABEL_RE = re.compile(r"[（(]E\d+(?:\s*[-,，、]\s*E?\d+)*[)）]")
QUOTED_EVIDENCE_LABEL_RE = re.compile(r"标签[\"“']?\s*[（(]E\d+.*?[)）][\"”']?[:：]?", re.I)
COMPONENT_PREFIX_RE = re.compile(r"^组件[A-ZＡ-Ｚ一二三四五六七八九十0-9]+[（(].*?[)）]\s*[—-]+")
COMPONENT_PREFIX_SIMPLE_RE = re.compile(r"^组件[A-ZＡ-Ｚ一二三四五六七八九十0-9]+[：:]\s*")
COMPONENT_LINE_RE = re.compile(r"^组件[A-ZＡ-Ｚ一二三四五六七八九十0-9]+")
PAGE_TYPE_LINE_RE = re.compile(r"^页面类型\s*[:：]\s*(?P<page_type>.+?)\s*$")
TITLE_REFERENCE_RE = re.compile(r"本页结论标题.*")
TEMPLATE_TITLE_RE = re.compile(r"本页结论标题[^\"“”]*[\"“](?P<title>[^\"”]+)[\"”]")
TEMPLATE_TITLE_MAX_CHARS = 42
DISALLOWED_LINE_PATTERNS = (
    re.compile(r"^\[通用风格前缀\]$"),
    re.compile(r"标题占位条"),
    re.compile(r"证据编号"),
    re.compile(r"caveat", re.I),
    re.compile(r"小字\s*caveat", re.I),
    re.compile(r"^\s*注[:：]"),
    re.compile(r"仅供参考"),
    re.compile(r"核对内容"),
    re.compile(r"不要求作为图内文字"),
    re.compile(r"来源说明"),
)


@dataclass(frozen=True)
class PageBlock:
    page_number: int
    title: str
    text: str


def _collapse_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def parse_page_blocks(script_path: Path) -> dict[int, PageBlock]:
    text = script_path.read_text(encoding="utf-8")
    matches = list(PAGE_HEADING_RE.finditer(text))
    pages: dict[int, PageBlock] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        page_number = int(match.group("num_cn") or match.group("num_p") or "0")
        pages[page_number] = PageBlock(
            page_number=page_number,
            title=match.group("title").strip(),
            text=text[match.end() : end].strip(),
        )
    return pages


def _section_lines_from_lock(section: dict[str, Any]) -> list[str]:
    heading = _collapse_text(section.get("heading"))
    text = _collapse_text(section.get("text"))
    lines: list[str] = []
    if heading:
        lines.append(heading)
    if text:
        lines.extend(line.strip() for line in text.splitlines() if line.strip())
    return lines


def page_block_from_content_lock(lock_path: Path) -> PageBlock:
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"content lock root must be an object: {lock_path}")
    page_number = int(payload.get("slide") or 0)
    if page_number <= 0:
        raise ValueError(f"content lock slide must be positive: {lock_path}")
    title = _collapse_text(payload.get("title"))
    if not title:
        raise ValueError(f"content lock title is required: {lock_path}")

    text_lines: list[str] = []
    subtitle = _collapse_text(payload.get("subtitle"))
    if subtitle and subtitle != title:
        text_lines.append(f"页面角色：{subtitle}")
    sections = payload.get("content_sections")
    if isinstance(sections, list):
        for raw_section in sections:
            if isinstance(raw_section, dict):
                text_lines.extend(_section_lines_from_lock(raw_section))
    annotations = payload.get("annotations")
    if isinstance(annotations, list):
        for annotation in annotations:
            cleaned = _collapse_text(annotation)
            if cleaned and cleaned != "无":
                text_lines.append(f"关系：{cleaned}")
    components = payload.get("required_components")
    if isinstance(components, list):
        for component in components:
            cleaned = _collapse_text(component)
            if cleaned:
                text_lines.append(f"组件：{cleaned}")

    return PageBlock(page_number=page_number, title=title, text="\n".join(text_lines))


def parse_content_locks(lock_dir: Path) -> dict[int, PageBlock]:
    if not lock_dir.is_dir():
        raise ValueError(f"content lock directory not found: {lock_dir}")
    pages: dict[int, PageBlock] = {}
    for lock_path in sorted(lock_dir.glob("slide-*-content-lock.json")):
        page = page_block_from_content_lock(lock_path)
        pages[page.page_number] = page
    if not pages:
        raise ValueError(f"no slide content locks found in: {lock_dir}")
    return pages


def _drop_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if FENCE_RE.match(stripped):
        return True
    if PAGE_TYPE_LINE_RE.match(stripped):
        return True
    if re.match(r"^组件[A-ZＡ-Ｚ一二三四五六七八九十0-9]+", stripped) and (
        "——" in stripped or "标签" in stripped or "下方" in stripped or "主体" in stripped or "（" in stripped
    ):
        return True
    if any(pattern.search(stripped) for pattern in DISALLOWED_LINE_PATTERNS):
        return True
    return stripped.startswith(("【", "目标语言", "用途"))


def _clean_line(line: str) -> str:
    line = line.strip()
    line = TITLE_REFERENCE_RE.sub("", line)
    line = QUOTED_EVIDENCE_LABEL_RE.sub("", line)
    line = EVIDENCE_LABEL_RE.sub("", line)
    line = COMPONENT_PREFIX_RE.sub("", line)
    line = COMPONENT_PREFIX_SIMPLE_RE.sub("", line)
    line = re.sub(r"——\s*", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" ：:")


def visible_deliverable_lines(page: PageBlock) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw in page.text.splitlines():
        if _drop_line(raw):
            continue
        cleaned = _clean_line(raw)
        if not cleaned:
            continue
        key = re.sub(r"\s+", "", cleaned)
        if key not in seen:
            lines.append(cleaned)
            seen.add(key)
    return lines


def _clean_structure_directive(line: str) -> str:
    line = line.strip()
    line = TITLE_REFERENCE_RE.sub("", line)
    line = re.sub(r"^组件[A-ZＡ-Ｚ一二三四五六七八九十0-9]+", "", line)
    line = re.sub(r"^[（(]([^）)]+)[）)]\s*[—-]*\s*", r"\1，", line)
    line = re.sub(r"，?\s*右下角小标签[\"“']?\s*[（(]E\d+.*?[)）][\"”']?", "", line)
    line = re.sub(r"，?\s*标签[\"“']?\s*[（(]E\d+.*?[)）][\"”']?", "", line)
    line = QUOTED_EVIDENCE_LABEL_RE.sub("", line)
    line = EVIDENCE_LABEL_RE.sub("", line)
    line = re.sub(r"，?\s*右下角小标签[\"“']?\s*[:：]?", "", line)
    line = re.sub(r"，?\s*标签[\"“']?\s*[:：]?", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" ：:，,—-")


def layout_density_directives(page: PageBlock) -> list[str]:
    directives: list[str] = []
    seen: set[str] = set()
    for raw in page.text.splitlines():
        stripped = raw.strip()
        if not stripped or FENCE_RE.match(stripped):
            continue
        if any(pattern.search(stripped) for pattern in DISALLOWED_LINE_PATTERNS):
            continue
        if not COMPONENT_LINE_RE.match(stripped) and not stripped.startswith(("组件：", "关系：")):
            continue
        cleaned = _clean_structure_directive(stripped.removeprefix("组件：").removeprefix("关系："))
        if not cleaned:
            continue
        key = re.sub(r"\s+", "", cleaned)
        if key not in seen:
            directives.append(cleaned)
            seen.add(key)
    return directives


def page_type_directive(page: PageBlock) -> str:
    """Return a non-visible page-type instruction for ImageGen composition."""

    for raw in page.text.splitlines():
        match = PAGE_TYPE_LINE_RE.match(raw.strip())
        if match:
            return match.group("page_type").strip()
    return "内容页"


def template_title(page: PageBlock) -> str:
    match = TEMPLATE_TITLE_RE.search(page.text)
    if match:
        return fit_template_title(match.group("title").strip())
    return page.title


def fit_template_title(title: str) -> str:
    if len(title) <= TEMPLATE_TITLE_MAX_CHARS:
        return title
    if "中电联" in title and "出海能力证明" in title:
        return "建议由中电联牵头，建设出海能力可信证明体系"
    segments = [part.strip() for part in re.split(r"[，,；;。]", title) if part.strip()]
    fitted: list[str] = []
    for segment in segments:
        candidate = "，".join(fitted + [segment])
        if len(candidate) > TEMPLATE_TITLE_MAX_CHARS:
            break
        fitted.append(segment)
    if fitted:
        return "，".join(fitted)
    return title[:TEMPLATE_TITLE_MAX_CHARS]


def _extract_hex_colors(text: str) -> list[str]:
    seen: set[str] = set()
    colors: list[str] = []
    for color in re.findall(r"#[0-9A-Fa-f]{6}", text):
        normalized = color.upper()
        if normalized not in seen:
            colors.append(normalized)
            seen.add(normalized)
    return colors


def _style_contract_from_payload(payload: dict[str, Any]) -> str | None:
    style = payload.get("style")
    if not isinstance(style, dict):
        return None
    colors = style.get("colors") if isinstance(style.get("colors"), dict) else {}
    color_values = [
        ("背景", colors.get("background")),
        ("标题", colors.get("title")),
        ("正文", colors.get("body")),
        ("强调", colors.get("accent")),
    ]
    color_text = "，".join(f"{label}{value}" for label, value in color_values if value)
    style_name = _collapse_text(style.get("name")) or "项目视觉锁定"
    return (
        f"视觉锁定：{style_name}；{color_text or '按锁定色板执行'}。"
        "采用正式内部汇报语气、清晰层级、克制图形和紧凑信息密度；"
        "版式必须服从本页内容锁定和构图要求。"
    )


def style_contract(style_lock_path: Path | None) -> str:
    if style_lock_path is None:
        raise ValueError(
            "missing visual style lock. 直接上传脚本转换前必须先选择 CyberPPT 默认 8 种风格之一，"
            "或传入 --style-lock。可用选项：\n" + default_style_choices()
        )
    try:
        payload = load_style_lock(style_lock_path)
    except json.JSONDecodeError:
        payload = {}
    if payload:
        contract = _style_contract_from_payload(payload)
        if contract:
            return contract
    text = style_lock_path.read_text(encoding="utf-8")
    colors = _extract_hex_colors(text)
    color_text = "、".join(colors[:8]) if colors else "以该视觉锁定文件为准"
    return (
        f"视觉锁定：核心色板 {color_text}。"
        "采用正式内部汇报语气、清晰层级、克制图形和紧凑信息密度；"
        "版式必须服从本页内容锁定和构图要求。"
    )


def render_prompt(page: PageBlock, *, style_lock_path: Path | None = None) -> str:
    body = "\n".join(f"- {line}" for line in visible_deliverable_lines(page))
    layout_directives = "\n".join(f"- {line}" for line in layout_density_directives(page))
    page_type = page_type_directive(page)
    return f"""## 第{page.page_number}页：{template_title(page)}

【页面类型】
本页类型：{page_type}。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
{body}

【构图指令】
生成正式内部汇报的正文内容区成稿图。
仅生成正文内容区；模板标题、页眉页脚、页码、Logo 和公共外框不绘制。
不得出现证据编号、来源、脚注、制作注释、占位符、乱码或水印。

{style_contract(style_lock_path)}

【结构密度】
保持高信息密度，完整保留本页内容、关键数字、判断句、清单项和结构关系；不得擅自合并、删减或改写业务术语。
{layout_directives}

图形关系、容器和连接线边界清楚，文字清晰可读；页面类型不得改作通用内容页。
""".strip() + "\n"


def assert_deliverable_prompt(prompt: str) -> None:
    forbidden = [
        r"\(E\d+",
        r"（E\d+",
        r"caveat",
        r"标题占位条（",
        r"标题占位条",
        r"(?m)^标题[:：]",
        r"(?m)^副标题[:：]",
        r"仅供参考",
        r"核对内容",
        r"\[通用风格前缀\]",
    ]
    for pattern in forbidden:
        if re.search(pattern, prompt, re.I):
            raise ValueError(f"Deliverable prompt still contains forbidden marker: {pattern}")


def compile_pages(script_path: Path, pages: Iterable[int], style_lock_path: Path | None = None) -> str:
    blocks = parse_page_blocks(script_path)
    return compile_page_blocks(blocks, pages, style_lock_path=style_lock_path)


def compile_page_blocks(
    blocks: dict[int, PageBlock],
    pages: Iterable[int],
    style_lock_path: Path | None = None,
) -> str:
    rendered: list[str] = []
    for page_number in pages:
        if page_number not in blocks:
            raise ValueError(f"Page {page_number} not found")
        prompt = render_prompt(blocks[page_number], style_lock_path=style_lock_path)
        assert_deliverable_prompt(prompt)
        rendered.append(prompt)
    return "\n".join(rendered)


def parse_pages(raw: str, available: set[int]) -> list[int]:
    if raw.strip().lower() == "all":
        return sorted(available)
    selected: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(value.strip()) for value in part.split("-", 1)]
            selected.update(range(start, end + 1))
        else:
            selected.add(int(part))
    missing = selected - available
    if missing:
        raise ValueError(f"Pages not found: {sorted(missing)}")
    return sorted(selected)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile final-deliverable image prompts.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--script", type=Path)
    source.add_argument("--content-lock-dir", type=Path)
    parser.add_argument("--pages", default="all")
    parser.add_argument("--style-lock", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    blocks = parse_page_blocks(args.script) if args.script else parse_content_locks(args.content_lock_dir)
    pages = parse_pages(args.pages, set(blocks))
    output = compile_page_blocks(blocks, pages, style_lock_path=args.style_lock)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(output, encoding="utf-8")
    if args.manifest:
        payload = {
            "schema": "cyberppt.deliverable_image_prompt_manifest.v1",
            "source_script": str(args.script) if args.script else None,
            "content_lock_dir": str(args.content_lock_dir) if args.content_lock_dir else None,
            "style_lock": str(args.style_lock) if args.style_lock else None,
            "pages": pages,
            "output": str(args.out),
            "policy": {
                "final_deliverable_only": True,
                "content_region_only": True,
                "template_title_subtitle": True,
                "forbid_evidence_ids": True,
                "forbid_caveats_and_notes": True,
                "forbid_title_placeholder_bar": True,
                "forbid_external_style_preset": True,
            },
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
