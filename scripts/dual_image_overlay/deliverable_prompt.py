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
from scripts.dual_image_overlay.visual_grammar import (
    creative_brief_visual_grammar,
    default_visual_grammar,
)


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
    if stripped.startswith("页面角色"):
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
    # Strip parenthetical noise on 上屏文字 headers only.
    line = re.sub(r"^上屏文字（[^）]+）", "上屏文字", line)
    line = re.sub(r"^上屏文字\([^)]+\)", "上屏文字", line)
    line = re.sub(r"——\s*", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" ：:")


# Boundary / 禁止项 are authoring + human-QA fields only. ImageGen prompts must not
# receive invisible boundary prose — rely on well-authored 上屏文字 instead.
_BOUNDARY_HEADER_RE = re.compile(
    r"^(?:Boundary\s*\(do not show on slide\)|禁止项)",
    re.I,
)
_CONTENT_FIELD_STARTERS = ("核心判断", "上屏文字", "禁止项", "Boundary")


def _filter_imagegen_content_lines(lines: list[str]) -> list[str]:
    """Keep drawable 上屏 lines; drop thesis-field and boundary/constraint blocks.

    Thesis belongs in script-final 上屏文字 (lead). Boundary stays in script-final /
    human QA parsing — never inject Boundary/禁止项 into ImageGen prompts.
    """

    content: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("核心判断"):
            i += 1
            continue
        if not _BOUNDARY_HEADER_RE.match(line):
            content.append(line)
            i += 1
            continue
        # Drop labeled boundary line, or header-only + following body until next field.
        if re.search(r"[：:]\s*\S", line):
            i += 1
            continue
        i += 1
        while i < len(lines) and not lines[i].startswith(_CONTENT_FIELD_STARTERS):
            i += 1
    return content


def _strip_visual_structure_meta(text: str) -> str:
    """Remove composition-meta asides; keep actionable icon/style guidance."""

    cleaned = text
    cleaned = re.sub(
        r"\s*Do not rely on 「视觉结构」 fields\.?",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\s*Do not use 「视觉结构」 or backend layout fields as composition input\.?",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\s*请勿依赖「视觉结构」[^。]*。?", "", cleaned)
    return cleaned.strip()


def visible_deliverable_lines(page: PageBlock) -> list[str]:
    # Final manuscripts carry authoring fields around the drawable layer.  When
    # this compiler receives a full manuscript, select the explicit 上屏文字
    # block rather than trying to delete every non-drawable field line-by-line.
    raw_lines = page.text.splitlines()
    onscreen_start = next(
        (index for index, line in enumerate(raw_lines) if re.match(r"^\s*-\s*上屏文字[：:]?\s*$", line)),
        None,
    )
    if onscreen_start is not None:
        selected: list[str] = []
        for raw in raw_lines[onscreen_start + 1 :]:
            if re.match(r"^\s*-\s*(?:证据|边界|视觉结构|讲解提示|演讲者备注)[：:]", raw):
                break
            if raw.strip().startswith("【演讲者备注】"):
                break
            selected.append(raw)
        raw_lines = selected
    lines: list[str] = []
    seen: set[str] = set()
    for raw in raw_lines:
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


def exact_visible_deliverable_lines(page: PageBlock) -> list[str]:
    """Preserve controlled handoff text exactly for creative-brief compilation.

    ``imagegen_handoff.content_lock_text`` has already removed backend-only
    fields.  The legacy cleaner performs useful compatibility normalization but
    also removes meaningful punctuation such as ``——``.  The new compiler keeps
    every non-empty controlled line verbatim.
    """

    lines: list[str] = []
    for raw in page.text.splitlines():
        line = raw.strip()
        if line and not FENCE_RE.match(line):
            lines.append(line)
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
    style_prompt_v2 = _collapse_text(style.get("style_prompt_v2"))
    if style_prompt_v2:
        return style_prompt_v2
    prompt_contract = _strip_visual_structure_meta(_collapse_text(style.get("prompt_contract")))
    scope_rule = _strip_visual_structure_meta(_collapse_text(style.get("scope_rule")))
    semantic_structure_rule = _strip_visual_structure_meta(
        _collapse_text(style.get("semantic_structure_rule"))
    )
    scene_layer_rule = _strip_visual_structure_meta(_collapse_text(style.get("scene_layer_rule")))
    people_rule = _strip_visual_structure_meta(_collapse_text(style.get("people_rule")))
    factuality_rule = _strip_visual_structure_meta(_collapse_text(style.get("factuality_rule")))
    semantic_image_text_rule = _strip_visual_structure_meta(
        _collapse_text(style.get("semantic_image_text_rule"))
    )
    content_visual_rule = _strip_visual_structure_meta(_collapse_text(style.get("content_visual_rule")))
    icon_rule = _strip_visual_structure_meta(_collapse_text(style.get("icon_rule")))
    density_rule = _collapse_text(style.get("density_rule"))
    parts = [prompt_contract]
    # Styles with an explicit two-layer contract must send that priority into
    # ImageGen. Legacy styles keep their existing prompt behavior unchanged.
    if semantic_structure_rule:
        parts.extend(part for part in (scope_rule, semantic_structure_rule, scene_layer_rule) if part)
    if people_rule:
        parts.append(people_rule)
    if factuality_rule:
        parts.append(factuality_rule)
    if semantic_image_text_rule:
        parts.append(semantic_image_text_rule)
    if content_visual_rule:
        parts.append(content_visual_rule)
    if icon_rule:
        parts.append(icon_rule)
    if density_rule:
        parts.append(density_rule)
    return "\n\n".join(part for part in parts if part)


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
    return f"核心色板：{color_text}。"


def _creative_brief_style_contract(style_lock_path: Path | None) -> str:
    """Remove bitmap-inapplicable or text-expanding clauses for the new compiler."""

    contract = style_contract(style_lock_path)
    contract = re.sub(
        r"允许根据画面容量压缩、取舍和重组文字，但不得改变原意，?",
        "完整、准确呈现锁定的上屏文字，不得压缩、删减、改写或重组，",
        contract,
    )
    contract = re.sub(
        r"(?:may|can)\s+(?:compress|shorten|summarize|paraphrase)[^.]*\.",
        (
            "Render the locked on-screen text completely and exactly; do not compress, "
            "shorten, summarize, paraphrase, or reorganize it."
        ),
        contract,
        flags=re.I,
    )
    contract = re.sub(
        r"factual numbers and labels must be verified and remain editable\.?",
        (
            "Keep every locked factual number and label exact. Auxiliary visuals may contain "
            "supporting words or non-evidentiary labels, but must not present invented numbers "
            "or claims as locked facts."
        ),
        contract,
        flags=re.I,
    )
    contract = re.sub(
        r"Auxiliary semantic imagery may use a small amount of clear Chinese labels,"
        r"\s*interface text, chart labels, or document wording when it directly clarifies"
        r"\s*the nearby business object or relationship\.",
        (
            "Auxiliary imagery may use clear supporting words, interface text, chart labels, "
            "or document-like wording when it improves the visual idea. This auxiliary text "
            "does not need to duplicate the locked wording, but must not masquerade as a new "
            "factual number, organization claim, or unsupported conclusion."
        ),
        contract,
        flags=re.I,
    )
    contract = re.sub(
        r"Auxiliary imagery may use only a small amount of clear supporting text when it "
        r"directly clarifies a nearby business object\.",
        (
            "Auxiliary imagery may use concise supporting text when it improves the overall "
            "visual idea. It does not need a one-to-one mapping to the locked modules."
        ),
        contract,
        flags=re.I,
    )
    contract = re.sub(
        r"Keep real organization and person names in the editable text layer only\.",
        "Do not introduce organization or person names beyond the locked on-screen text.",
        contract,
        flags=re.I,
    )
    contract = re.sub(
        r"Generic, non-location-specific facilities, layered workspaces, control consoles, "
        r"equipment rooms, and industrial scenes may be used as (?:restrained )?illustrative "
        r"carriers when they map to the locked content\.",
        (
            "Choose scenes, visual metaphors, facilities, workspaces, control environments, "
            "industrial imagery, or abstract editorial forms freely according to the strongest "
            "overall composition."
        ),
        contract,
        flags=re.I,
    )
    contract = re.sub(
        r"Schematic screens, charts, maps, and interface labels may organize the composition, "
        r"but generated values are non-evidentiary;",
        (
            "Schematic screens, charts, maps, time bands, interface-like structures, and their "
            "supporting labels may organize the composition freely;"
        ),
        contract,
        flags=re.I,
    )
    contract = re.sub(
        r"在不改变原脚本结构的前提下，",
        (
            "只需保持锁定上屏文字完整准确；不要求沿用原始列表、卡片、栏位或段落"
            "排布形式，整体构图、视觉隐喻和辅助表达均可自由发挥；"
        ),
        contract,
    )
    return contract


def uses_compact_style_contract(style_lock_path: Path | None) -> bool:
    if style_lock_path is None or not style_lock_path.is_file():
        return False
    try:
        payload = json.loads(style_lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    style = payload.get("style")
    return isinstance(style, dict) and bool(_collapse_text(style.get("style_prompt_v2")))


def render_prompt(
    page: PageBlock,
    *,
    style_lock_path: Path | None = None,
    composition_guidance: str = "",
    compiler_version: str = "legacy",
) -> str:
    creative_brief = compiler_version == "creative-brief-v1"
    content_lines = (
        exact_visible_deliverable_lines(page)
        if creative_brief
        else _filter_imagegen_content_lines(visible_deliverable_lines(page))
    )
    body = "\n".join(f"- {line}" for line in content_lines)
    compact_style = uses_compact_style_contract(style_lock_path)
    layout_directives = [] if compact_style else layout_density_directives(page)
    visual_grammar = (
        creative_brief_visual_grammar()
        if creative_brief
        else ("" if compact_style else default_visual_grammar().render())
    )
    parts = [
        f"【页面编码】P{page.page_number:02d}｜{page.title}",
        "以上为提示词元数据，仅用于按页追踪；不得在生成图中渲染页面编码或页面标题。",
        "",
    ]
    if composition_guidance.strip() and (not compact_style or creative_brief):
        parts.extend(
            [
                "[Mandatory composition guidance] Apply this layout guidance before placing "
                "any on-screen text. Do not render its field names or instruction text.",
                composition_guidance.strip(),
                "",
            ]
        )
    parts.extend(
        [
        "【内容锁定】",
        body,
        "",
        "【构图指令】",
        "画布 2048×1024（2:1）。只生成正文内容区成稿图。",
        "不要生成页面标题、副标题、Logo、页脚、页码或任何页面外框。",
        "No evidence IDs, watermarks, debug marks, or placeholders.",
        "Do not invent section labels like meta headers; only render 上屏文字 modules.",
        ]
    )
    parts.extend(
        [
            "",
            (
                _creative_brief_style_contract(style_lock_path)
                if creative_brief
                else style_contract(style_lock_path)
            ),
            "",
            "【视觉组织原则】",
            visual_grammar,
        ]
    )
    if layout_directives:
        parts.extend(
            [
                "",
                "【结构密度】",
                "\n".join(f"- {line}" for line in layout_directives),
            ]
        )
    parts.extend(
        [
            "",
            "忠实于【内容锁定】：核心模块、关键数字与业务术语须可读；不得近义替换或生成伪文字。",
        ]
    )
    return "\n".join(parts).strip() + "\n"


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
