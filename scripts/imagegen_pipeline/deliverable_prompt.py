#!/usr/bin/env python3
"""Compile final-deliverable prompts for the current ImageGen pipeline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.imagegen_pipeline.style_library import (
    default_style_choices,
    load_style_lock,
    resolve_default_style,
)
from scripts.imagegen_pipeline.runtime_style_contract import (
    TERMINAL_EXECUTION_HEADING,
    enforce_terminal_execution_lock,
    load_runtime_style_contract,
    project_runtime_style_contract,
)
from scripts.imagegen_pipeline.visual_grammar import (
    creative_brief_visual_grammar,
    default_visual_grammar,
)
from cyberppt.script_quality_contract import strip_authoring_group_marker


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
    line = strip_authoring_group_marker(line)
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
        (
            index
            for index, line in enumerate(raw_lines)
            if re.match(
                r"^\s*(?:-\s*)?(?:#{1,6}\s*)?上屏文字(?:（严格锁定）)?[：:]?\s*$",
                line,
            )
        ),
        None,
    )
    if onscreen_start is not None:
        selected: list[str] = []
        for raw in raw_lines[onscreen_start + 1 :]:
            if re.match(r"^\s*(?:-\s*)?#{1,6}\s+", raw):
                break
            if re.match(r"^\s*(?:-\s*){1,2}上屏(?:模块|顶层模块)清单[：:]", raw):
                break
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


_STYLE09_CONDITIONAL_HEADING = "### 条件构图规则（编译器按需选择）"
_STYLE09_TERMINAL_HEADING = "### Final ImageGen execution lock — hard"
_STYLE09_TAG_LINE_RE = re.compile(r"(?m)^semantic_tags:\s*\[([^\]]*)\]\s*$")
_STYLE09_SCOPE_COMMENT_RE = re.compile(r"(?m)^\s*<!--\s*style09:[^>]+-->\s*$")


def _style09_page_semantic_tags(page: PageBlock, content_lines: list[str]) -> frozenset[str]:
    """Infer composable Style 09 clause tags from the locked page content."""

    corpus = "\n".join((page.title, *content_lines))
    compact = re.sub(r"\s+", "", corpus)
    labels = [page.title]
    for raw_line in content_lines:
        line = re.sub(r"^\s*[-*•]+\s*", "", raw_line).strip("* ")
        if not line:
            continue
        label = re.split(r"[：:]", line, maxsplit=1)[0].strip()
        if len(label) <= 24:
            labels.append(label)
    label_corpus = "\n".join(labels)
    tags: set[str] = set()
    if len(compact) >= 180 or len([line for line in content_lines if line.strip()]) >= 6:
        tags.add("dense_text")
    if re.search(r"(?:多个维度|多维|维度|方面|层级|架构|视图)", label_corpus):
        tags.add("multi_dimension")
    if re.search(
        r"(?:分类|类别|矩阵|分为|分成|层级|架构|方向|[一二三四五六七八九十\d]+(?:类|层|个方向))",
        label_corpus,
    ) or re.search(r"[一二三四五六七八九十\d]+类", corpus):
        tags.add("classification")
    if "矩阵" in label_corpus:
        tags.add("matrix")
    if re.search(
        r"(?:流程|步骤|阶段|路径|生命周期|输入输出|形成链|履行链|反馈链|业务链)",
        label_corpus,
    ):
        tags.update(("flow", "sequence"))
    has_input = bool(re.search(r"(?:输入|需求侧|供给侧|来源)", label_corpus))
    has_output = bool(re.search(r"(?:输出|交付结果|成果|服务对象)", label_corpus))
    if has_input and has_output:
        tags.add("input_output")
    boundary_terms = set(
        re.findall(r"权利|责任|授权|准入|门控|边界|范围|受控|控制", corpus)
    )
    if len(boundary_terms) >= 3 or re.search(
        r"(?:权利边界|授权范围|准入条件|受控输出|控制边界|安全合规|权利|授权)",
        label_corpus,
    ):
        tags.update(("boundary", "authorization"))
    if re.search(r"(?:反馈|回流|复盘|返回前序)", label_corpus):
        tags.add("feedback")
    if re.search(r"(?:闭环|闭合|循环|反馈环|回流|返回前序)", label_corpus):
        tags.add("loop")
    return frozenset(tags)


def _compile_style09_contract(
    contract: str,
    semantic_tags: frozenset[str] | None,
) -> str:
    """Strip authoring metadata and select tagged Style 09 clauses for one page."""

    contract = _STYLE09_SCOPE_COMMENT_RE.sub("", contract)
    if _STYLE09_CONDITIONAL_HEADING not in contract or _STYLE09_TERMINAL_HEADING not in contract:
        return _STYLE09_TAG_LINE_RE.sub("", contract)
    before, tail = contract.split(_STYLE09_CONDITIONAL_HEADING, 1)
    conditional, after = tail.split(_STYLE09_TERMINAL_HEADING, 1)
    matches = list(re.finditer(r"(?m)^####\s+(.+?)\s*$", conditional))
    selected: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(conditional)
        block = conditional[match.start() : end].strip()
        tag_match = _STYLE09_TAG_LINE_RE.search(block)
        block_tags = {
            tag.strip()
            for tag in (tag_match.group(1).split(",") if tag_match else [])
            if tag.strip()
        }
        if semantic_tags is None or not block_tags or block_tags.intersection(semantic_tags):
            selected.append(_STYLE09_TAG_LINE_RE.sub("", block).strip())
    parts = [before.rstrip()]
    if selected:
        parts.append("### 本页命中的条件构图规则\n\n" + "\n\n".join(selected))
    parts.append(f"{_STYLE09_TERMINAL_HEADING}{after}")
    return "\n\n".join(part for part in parts if part).strip()


def _style_contract_from_payload(
    payload: dict[str, Any],
    semantic_tags: frozenset[str] | None = None,
) -> str | None:
    style = payload.get("style")
    if not isinstance(style, dict):
        return None
    style_prompt_v2 = _collapse_text(style.get("style_prompt_v2"))
    if style_prompt_v2:
        return style_prompt_v2
    prompt_contract = _strip_visual_structure_meta(_collapse_text(style.get("prompt_contract")))
    # Style 09 is an authored, self-contained source contract: the people,
    # factuality, on-screen-text and component/craftsmanship rules that used
    # to live as separate JSON fields (people_rule/factuality_rule/
    # semantic_image_text_rule/component_rule) are now authored directly
    # inside references/visual-system.md's "扩展风格9" section and arrives
    # here already folded into prompt_contract.
    # The final prompt must carry this entire contract verbatim under its
    # formal style lock, rather than letting a downstream compiler select
    # clauses or recreate a terminal fragment. Page layout belongs to Stage 02.
    if int(style.get("id") or 0) == 9 and prompt_contract:
        return prompt_contract
    scope_rule = _strip_visual_structure_meta(_collapse_text(style.get("scope_rule")))
    semantic_structure_rule = _strip_visual_structure_meta(
        _collapse_text(style.get("semantic_structure_rule"))
    )
    scene_layer_rule = _strip_visual_structure_meta(_collapse_text(style.get("scene_layer_rule")))
    semantic_image_rule = _strip_visual_structure_meta(
        _collapse_text(style.get("semantic_image_rule"))
    )
    people_rule = _strip_visual_structure_meta(_collapse_text(style.get("people_rule")))
    factuality_rule = _strip_visual_structure_meta(_collapse_text(style.get("factuality_rule")))
    semantic_image_text_rule = _strip_visual_structure_meta(
        _collapse_text(style.get("semantic_image_text_rule"))
    )
    default_text_render_mode = _collapse_text(style.get("default_text_render_mode"))
    truth_lock = _collapse_text(style.get("truth_lock"))
    visual_freedom = _collapse_text(style.get("visual_freedom"))
    content_visual_rule = _strip_visual_structure_meta(_collapse_text(style.get("content_visual_rule")))
    icon_rule = _strip_visual_structure_meta(_collapse_text(style.get("icon_rule")))
    density_rule = _collapse_text(style.get("density_rule"))
    carrier_router = _collapse_text(style.get("carrier_router"))
    component_rule = (
        ""
        if int(style.get("id") or 0) == 9 and prompt_contract
        else _collapse_text(style.get("component_rule"))
    )
    deck_consistency_rule = _collapse_text(style.get("deck_consistency_rule"))
    prompt_sequence_rule = _collapse_text(style.get("prompt_sequence_rule"))
    parts = [prompt_contract]
    # Styles with an explicit two-layer contract must send that priority into
    # ImageGen. Legacy styles keep their existing prompt behavior unchanged.
    if semantic_structure_rule:
        parts.extend(part for part in (scope_rule, semantic_structure_rule, scene_layer_rule) if part)
    if semantic_image_rule:
        parts.append(semantic_image_rule)
    if people_rule:
        parts.append(people_rule)
    if factuality_rule:
        parts.append(factuality_rule)
    if semantic_image_text_rule:
        parts.append(semantic_image_text_rule)
    if default_text_render_mode:
        parts.append(f"默认文字渲染模式：{default_text_render_mode}。")
    if truth_lock:
        parts.append(truth_lock)
    if visual_freedom:
        parts.append(visual_freedom)
    if content_visual_rule:
        parts.append(content_visual_rule)
    if icon_rule:
        parts.append(icon_rule)
    if density_rule:
        parts.append(density_rule)
    if carrier_router:
        parts.append(carrier_router)
    if component_rule:
        parts.append(component_rule)
    if deck_consistency_rule:
        parts.append(deck_consistency_rule)
    if prompt_sequence_rule:
        parts.append(prompt_sequence_rule)
    contract = "\n\n".join(part for part in parts if part)
    return contract


def _is_live_runtime_style(style_lock_path: Path) -> bool:
    try:
        payload = load_style_lock(style_lock_path)
    except (OSError, ValueError, TypeError):
        return False
    style = payload.get("style") if isinstance(payload.get("style"), dict) else payload
    try:
        return int(style.get("id") or 0) in (9, 10)
    except (TypeError, ValueError):
        return False

def style_contract(
    style_lock_path: Path | None,
    *,
    semantic_tags: frozenset[str] | None = None,
) -> str:
    if style_lock_path is None:
        return str(resolve_default_style(style_id=9).get("prompt_contract") or "")
    try:
        payload = load_style_lock(style_lock_path)
    except json.JSONDecodeError:
        payload = {}
    if payload:
        contract = _style_contract_from_payload(payload, semantic_tags)
        if contract:
            return contract
    text = style_lock_path.read_text(encoding="utf-8")
    colors = _extract_hex_colors(text)
    color_text = "、".join(colors[:8]) if colors else "以该视觉锁定文件为准"
    return f"核心色板：{color_text}。"


def _creative_brief_style_contract(
    style_lock_path: Path | None,
    *,
    semantic_tags: frozenset[str] | None = None,
) -> str:
    """Remove bitmap-inapplicable or text-expanding clauses for the new compiler."""

    contract = style_contract(style_lock_path, semantic_tags=semantic_tags)
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
    creative_layout_freedom = (
        "只需保持锁定上屏文字完整准确；不要求沿用原始列表、卡片、栏位或段落"
        "排布形式，整体构图、视觉隐喻和辅助表达均可自由发挥。"
    )
    if "不要求沿用原始列表、卡片、栏位或段落排布形式" not in contract:
        contract = f"{contract}\n\n{creative_layout_freedom}"
    required_guardrails = (
        "Auxiliary imagery may use clear supporting words, interface text, chart labels, or document-like wording when it improves the visual idea. This auxiliary text does not need to duplicate the locked wording, but must not masquerade as a new factual number, organization claim, or unsupported conclusion.",
        "Do not introduce organization or person names beyond the locked on-screen text.",
        "Schematic screens, charts, maps, time bands, interface-like structures, and their supporting labels may organize the composition freely;",
    )
    for guardrail in required_guardrails:
        if guardrail not in contract:
            contract = f"{contract}\n\n{guardrail}"
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


def _style_contract_owns_visual_grammar(style_lock_path: Path | None) -> bool:
    """Return whether global visual grammar is already owned by the style lock."""

    if uses_compact_style_contract(style_lock_path):
        return True
    if style_lock_path is None or not style_lock_path.is_file():
        return False
    try:
        payload = json.loads(style_lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    style = payload.get("style")
    return (
        isinstance(style, dict)
        and int(style.get("id") or 0) in (9, 10)
        and bool(_collapse_text(style.get("prompt_contract")))
    )


def _resolve_text_render_mode(
    style_lock_path: Path | None,
    explicit: str | None,
) -> str:
    value = str(explicit or "").strip()
    if not value and style_lock_path is not None and style_lock_path.is_file():
        try:
            payload = json.loads(style_lock_path.read_text(encoding="utf-8"))
            style = payload.get("style") if isinstance(payload, dict) else None
            if isinstance(style, dict):
                value = str(style.get("default_text_render_mode") or "").strip()
        except (OSError, json.JSONDecodeError):
            value = ""
    value = value or "full_image"
    if value not in {"full_image", "semantic_visual"}:
        raise ValueError(
            "unsupported text render mode: "
            f"{value}; choose full_image or semantic_visual"
        )
    return value


def _semantic_visual_lines(lines: list[str]) -> list[str]:
    """Keep concrete nouns/actions while removing the sentence-layout lock."""

    anchors: list[str] = []
    for line in lines:
        parts = [
            part.strip(" -*")
            for part in re.split(r"[，,、；;。:：→—\-]+", line)
            if part.strip(" -*")
        ]
        if not parts:
            continue
        compact = " / ".join(parts[:8])
        if len(compact) > 120:
            compact = compact[:120].rstrip("/ ")
        if compact and compact not in anchors:
            anchors.append(compact)
    return anchors


def _style09_terminal_execution_lock(style_lock_path: Path | None) -> str:
    """Compatibility wrapper over the generic live-style runtime contract."""
    if style_lock_path is None:
        return ""
    try:
        return load_runtime_style_contract(style_lock_path).terminal_lock
    except (OSError, ValueError, TypeError):
        return ""



STYLE09_TERMINAL_LOCK_HEADER = TERMINAL_EXECUTION_HEADING


def _style09_people_rule(style_lock_path: Path | None) -> str:
    """Return Style 09's people constraint for final prompt reassertion."""

    if style_lock_path is None:
        return ""
    try:
        payload = load_style_lock(style_lock_path)
    except (OSError, ValueError, TypeError):
        return ""
    style = payload.get("style") if isinstance(payload.get("style"), dict) else payload
    if int(style.get("id") or 0) not in (9, 10):
        return ""
    return _strip_visual_structure_meta(_collapse_text(style.get("people_rule")))


def enforce_style09_terminal_lock(
    prompt: str,
    style_lock_path: Path | None,
) -> str:
    """Compatibility wrapper over generic terminal-lock enforcement."""
    if style_lock_path is None or TERMINAL_EXECUTION_HEADING in prompt:
        return prompt
    try:
        runtime = load_runtime_style_contract(style_lock_path)
    except (OSError, ValueError, TypeError):
        return prompt
    return enforce_terminal_execution_lock(prompt, runtime)



def render_prompt(
    page: PageBlock,
    *,
    style_lock_path: Path | None = None,
    composition_guidance: str = "",
    compiler_version: str = "legacy",
    text_render_mode: str | None = None,
    include_style_contract: bool = True,
) -> str:
    creative_brief = compiler_version == "creative-brief-v1"
    content_lines = (
        exact_visible_deliverable_lines(page)
        if creative_brief
        else _filter_imagegen_content_lines(visible_deliverable_lines(page))
    )
    style09_semantic_tags = _style09_page_semantic_tags(page, content_lines)
    resolved_text_render_mode = _resolve_text_render_mode(style_lock_path, text_render_mode)
    semantic_visual = resolved_text_render_mode == "semantic_visual"
    runtime_style = None
    if include_style_contract and style_lock_path is not None and _is_live_runtime_style(style_lock_path):
        authored_style_contract = (
            _creative_brief_style_contract(
                style_lock_path, semantic_tags=style09_semantic_tags
            )
            if creative_brief
            else style_contract(style_lock_path, semantic_tags=style09_semantic_tags)
        )
        runtime_style = project_runtime_style_contract(
            authored_style_contract, source=str(style_lock_path)
        )
    if semantic_visual:
        semantic_lines = _semantic_visual_lines(content_lines)
        body = "\n".join(f"- {line}" for line in semantic_lines)
    else:
        body = "\n".join(f"- {line}" for line in content_lines)
    compact_style = uses_compact_style_contract(style_lock_path)
    style_owns_visual_grammar = _style_contract_owns_visual_grammar(style_lock_path)
    layout_directives = (
        [] if style_owns_visual_grammar else layout_density_directives(page)
    )
    visual_grammar = (
        creative_brief_visual_grammar()
        if creative_brief
        else ("" if style_owns_visual_grammar else default_visual_grammar().render())
    )
    parts = [
        f"【页面编码】P{page.page_number:02d}｜{page.title}",
        "以上为提示词元数据，仅用于按页追踪；不得在生成图中渲染页面编码或页面标题。",
        "",
    ]
    if composition_guidance.strip() and (not compact_style or creative_brief):
        parts.extend(
            [
                _source_visual_expression_header(),
                composition_guidance.strip(),
                "",
            ]
        )
    parts.extend(
        [
        (
            "【事实语义参考｜仅供理解，不在图内排版】"
            if semantic_visual
            else "【源文案语义输入】"
        ),
        body,
        (
            "正文、数字、主体名称和完整结论由后续 PPT 可编辑文字层承载；默认不要在图片中生成长句、伪中文或新增标签。"
            if semantic_visual
            else ""
        ),
        "",
        "【构图指令】",
        "画布 2048×1024（2:1）。只生成正文内容区成稿图。",
        "不要生成页面标题、副标题、Logo、页脚、页码或任何页面外框。",
        "No evidence IDs, watermarks, debug marks, or placeholders.",
        "Do not render prompt field labels or meta headers. Rewrite the source copy into conclusion-first visible Chinese while preserving its factual boundary.",
        ]
    )
    if not semantic_visual:
        parts.extend(
            [
                "可将源文案改写为结论、标题、标签、流程节点或正文；保持业务对象、数字、时间、范围、责任、条件、状态和结论力度准确，不得新增分类或事实。",
                "改写并列内容时，保留父级与子项的实际适用范围；共享谓词、共享限定语和父级说明不能被误写成每个子项都已单独具备的事实。",
                "避免把同一内容以正文和拆分标签机械重复呈现；根据页面使命选择最清晰的层级表达。",
                "任何按业务语义选择的视觉载体都可承载经过改写的可见文字；空间不足时优先减少视觉元素或扩大文字区，避免微型文字。",
            ]
        )
    if visual_grammar:
        parts.extend(["", "【视觉组织原则】", visual_grammar])
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
            (
                "忠实于【事实语义参考】表达业务对象、动作和关系；不要把参考短语逐字排版进图片。"
                if semantic_visual
            else "基于源文案进行专业改写：核心模块、关键数字与业务术语须保持事实准确；可使用更清晰的同义表达，避免伪文字。"
            ),
        ]
    )
    if include_style_contract:
        # The human-readable visual-system.md contract is the final visual
        # authority.  Page-authored composition guidance may explain the
        # business relationship, but it must not override Style 09's hard
        # bans on card dashboards, equal-weight peer cards, icon walls, and
        # other prohibited surface grammar.
        parts.extend(
            [
                "",
                "【源头视觉规则权威｜最高优先级】",
                (
                    runtime_style.contract
                    if runtime_style is not None
                    else (
                        _creative_brief_style_contract(
                            style_lock_path,
                            semantic_tags=style09_semantic_tags,
                        )
                        if creative_brief
                        else style_contract(
                            style_lock_path,
                            semantic_tags=style09_semantic_tags,
                        )
                    )
                ),
            ]
        )
    rendered = "\n".join(parts).strip() + "\n"
    if runtime_style is not None:
        rendered = enforce_terminal_execution_lock(rendered, runtime_style)
    return rendered


def append_composition_guidance(prompt: str, guidance: str) -> str:
    """Append source-authored relationships without turning them into a layout recipe."""

    guidance = str(guidance or "").strip()
    if not guidance or guidance in prompt:
        return prompt
    block = _source_visual_expression_header()
    return f"{prompt.rstrip()}\n\n{block}\n{guidance}\n"


def _source_visual_expression_header() -> str:
    return (
        "【本页业务关系与视觉表达意图｜不上屏】以下内容只锁定业务对象、动作、状态、"
        "边界、因果与收束关系，不锁定分栏、卡片、框体或文字区。将锁定文字就近附着于"
        "同一连续业务场中的相关对象、动作或状态，使图形与文字共同表达关系；不得把每个"
        "语义分句自动拆成独立面板，也不得另建一套与文字分离或重复的图形结构。"
    )


def source_visual_structure_guidance(value: str, visible_text: str = "") -> str:
    """Keep visual relations without leaking non-visible copy into ImageGen.

    Stage 01 visual notes may quote a semantic focus to explain composition.  A
    quoted phrase is especially likely to be copied verbatim by an image model,
    even when the surrounding block is marked non-visible.  Preserve quoted
    text only when it already occurs in the locked visible-text corpus;
    otherwise replace it with a non-lexical reference to the semantic focus.
    """

    text = str(value or "").strip()
    if not text:
        return ""
    excluded_markers = (
        "阅读出口",
        "交给P",
        "交给 P",
        "下一页",
        "视觉结构只表达",
        "不上屏",
        "不预设固定版式",
        "不预设固定版式或",
    )
    compact_visible = re.sub(r"\s+", "", str(visible_text or ""))

    def sanitize_quote(match: re.Match[str]) -> str:
        quoted = next(
            (group for group in match.groups() if group is not None),
            "",
        ).strip()
        if quoted and re.sub(r"\s+", "", quoted) in compact_visible:
            return match.group(0)
        return "该语义焦点"

    text = re.sub(
        r"“([^”]+)”|‘([^’]+)’|「([^」]+)」|『([^』]+)』|\"([^\"]+)\"",
        sanitize_quote,
        text,
    )
    sentences = re.split(r"(?<=[。！？])\s*", text)
    kept = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
        and not any(marker in sentence for marker in excluded_markers)
        and not re.search(r"\bP\d{1,3}\b", sentence, flags=re.I)
    ]
    return "".join(kept).strip()


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


def compile_pages(
    script_path: Path,
    pages: Iterable[int],
    style_lock_path: Path | None = None,
    composition_guidance_by_page: Mapping[int, str] | None = None,
) -> str:
    blocks = parse_page_blocks(script_path)
    return compile_page_blocks(
        blocks,
        pages,
        style_lock_path=style_lock_path,
        composition_guidance_by_page=composition_guidance_by_page,
    )


def compile_page_blocks(
    blocks: dict[int, PageBlock],
    pages: Iterable[int],
    style_lock_path: Path | None = None,
    composition_guidance_by_page: Mapping[int, str] | None = None,
) -> str:
    rendered: list[str] = []
    for page_number in pages:
        if page_number not in blocks:
            raise ValueError(f"Page {page_number} not found")
        prompt = render_prompt(
            blocks[page_number],
            style_lock_path=style_lock_path,
            composition_guidance=(composition_guidance_by_page or {}).get(page_number, ""),
        )
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
    with args.out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(output)
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
        with args.manifest.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
