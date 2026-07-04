#!/usr/bin/env python3
"""Compile final-deliverable image prompts for dual-image generation."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


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


def _drop_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if FENCE_RE.match(stripped):
        return True
    if re.match(r"^组件[A-ZＡ-Ｚ一二三四五六七八九十0-9]+", stripped) and (
        "——" in stripped or "标签" in stripped or "下方" in stripped or "主体" in stripped or "（" in stripped
    ):
        return True
    return any(pattern.search(stripped) for pattern in DISALLOWED_LINE_PATTERNS)


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
        if not COMPONENT_LINE_RE.match(stripped):
            continue
        cleaned = _clean_structure_directive(stripped)
        if not cleaned:
            continue
        key = re.sub(r"\s+", "", cleaned)
        if key not in seen:
            directives.append(cleaned)
            seen.add(key)
    return directives


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


def style_contract(style_lock_path: Path | None) -> str:
    if style_lock_path is None:
        return (
            "采用正式咨询汇报成稿风格：浅灰白连续纸面、墨绿强调、细线分隔、"
            "规则几何容器、克制图标、清晰留白。"
        )
    text = style_lock_path.read_text(encoding="utf-8")
    colors = _extract_hex_colors(text)
    color_text = "、".join(colors[:8]) if colors else "#F2F3EF、#1F5B4D、#333333、#D7D9D3"
    return (
        "沿用项目视觉锁定，不使用外部风格 preset。"
        f"核心色板：{color_text}。"
        "页面应是最终交付成稿：连续纸面、墨绿结论锚点、细线分隔、规则信息容器、"
        "低干扰图标和企业汇报质感。"
    )


def render_prompt(page: PageBlock, *, style_lock_path: Path | None = None) -> str:
    body = "\n".join(f"- {line}" for line in visible_deliverable_lines(page))
    layout_directives = "\n".join(f"- {line}" for line in layout_density_directives(page))
    return f"""## 第{page.page_number}页：{page.title}

【内容锁定】
标题：{template_title(page)}
副标题：
{body}

【构图指令】
生成一张面向最终客户交付的 PPT 正文内容区成稿图，不是蓝图、草稿、过程说明页、复刻中间产物或调试预览图。

只生成正文内容区画面。不要生成页面标题、副标题、Logo、页脚、页码、母版红线、公共元素、临时占位元素或任何完整 PPT 外框；这些由 PPT 模板/母版和可编辑文字层生成。

不得出现证据编号、来源编号、过程性注释、脚注、口径说明、参考来源、调试标记、占位符、乱码、水印，或任何面向制作过程而非最终受众的文字。

{style_contract(style_lock_path)}

【结构密度】
必须保持高信息密度，不能把页面简化成少量留白卡片。保留原脚本组件数量、组件关系、网格/流程/卡片结构和底部 SO WHAT 区。所有正文内容都要进入画面，不得遗漏关键数字、判断句、清单项或行动链。
{layout_directives}

把正文内容组织为正式汇报页的信息图结构：一个清晰主判断区、若干业务要点/结构模块、一个醒目的 SO WHAT 或行动提示。所有文字承载区必须干净、留白充分、可被后续 PPT 文本层覆盖；图形关系、容器、图标和连接线应边界清楚，适合作为无字背景保留。
""".strip() + "\n"


def assert_deliverable_prompt(prompt: str) -> None:
    forbidden = [
        r"\(E\d+",
        r"（E\d+",
        r"caveat",
        r"标题占位条（",
        r"标题占位条",
        r"仅供参考",
        r"核对内容",
        r"\[通用风格前缀\]",
    ]
    for pattern in forbidden:
        if re.search(pattern, prompt, re.I):
            raise ValueError(f"Deliverable prompt still contains forbidden marker: {pattern}")


def compile_pages(script_path: Path, pages: Iterable[int], style_lock_path: Path | None = None) -> str:
    blocks = parse_page_blocks(script_path)
    rendered: list[str] = []
    for page_number in pages:
        if page_number not in blocks:
            raise ValueError(f"Page {page_number} not found in script: {script_path}")
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
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--pages", default="all")
    parser.add_argument("--style-lock", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    blocks = parse_page_blocks(args.script)
    pages = parse_pages(args.pages, set(blocks))
    output = compile_pages(args.script, pages, style_lock_path=args.style_lock)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(output, encoding="utf-8")
    if args.manifest:
        payload = {
            "schema": "cyberppt.deliverable_image_prompt_manifest.v1",
            "source_script": str(args.script),
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
