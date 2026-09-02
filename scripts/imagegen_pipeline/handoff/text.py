"""Visible-text selection and text-render-mode rules for ImageGen handoff."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from cyberppt.script_quality_contract import ScriptPage, resolve_judgment_mode
from scripts.imagegen_pipeline.handoff.common import _clean_onscreen_for_imagegen
from scripts.imagegen_pipeline.prompt_compiler import (
    DEFAULT_PROMPT_COMPILER,
    DEFAULT_TEXT_RENDER_MODE,
    validate_text_render_mode,
)
from scripts.imagegen_pipeline.style_library import (
    load_style_lock,
    resolve_default_style,
)


def content_lock_text(page: ScriptPage, page_mission: str = "") -> str:
    """Build prompt context followed by the drawable 上屏文字 reference."""

    if page.page_type != "content":
        raise ValueError(f"page {page.page_id} is {page.page_type}; no body ImageGen handoff")
    onscreen = page.onscreen_text.strip()
    context: list[str] = [
        "[Prompt context] 页面使命 / Page mission（用于理解本页要回答的问题；不要把字段名或说明文字画出来）",
        page_mission.strip() or "未提供页面使命",
    ]
    context.extend(
        [
            "[Prompt context] 核心意思 / Core meaning（忠实表达；不要把字段名画出来）",
            page.core_message.strip(),
            "[Prompt context] 不得增加源合同未声明的因果、必要性、排他性、协同机制或结果承诺。",
        ]
    )
    context.extend(["上屏文字（需要准确表达的正文文字层）", onscreen])
    return "\n".join(context).strip() + "\n"


def _flatten_markdown_tables(text: str) -> str:
    """Preserve table cell meanings without prescribing a rendered table."""

    output: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if re.fullmatch(r"\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?", line):
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            output.append(" · ".join(cell for cell in cells if cell))
        else:
            output.append(raw)
    return "\n".join(output).strip()


def diagnostic_onscreen_text(
    page: ScriptPage,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
) -> str:
    """Return the authored on-screen text used as the model's content reference."""

    if prompt_compiler == "content-first-v1":
        body = page.onscreen_text.strip()
        return "\n\n".join(
            part for part in (page.onscreen_judgment.strip(), body) if part
        )
    return page.onscreen_text


ONSCREEN_JUDGMENT_MODES = (
    "locked",
    "semantic_only",
    "semantic_alignment",
    "hidden",
)


def resolve_onscreen_judgment_mode(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    mode = str(
        (visual_context or {}).get("onscreen_judgment_mode")
        or page.onscreen_judgment_mode
    ).strip()
    role = str(
        (visual_context or {}).get("judgment_role")
        or page.judgment_role
    ).strip()
    try:
        return resolve_judgment_mode(mode, role)
    except ValueError as exc:
        raise ValueError(
            f"{page.page_id} has invalid judgment display policy: {exc}"
        ) from exc


def locked_onscreen_text(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    """Return only verbatim-critical visible copy; keep the rest semantically flexible."""

    locked: list[str] = []
    if (
        resolve_onscreen_judgment_mode(page, visual_context) == "locked"
        and page.onscreen_judgment.strip()
    ):
        locked.append(page.onscreen_judgment.strip())
    for title in page.module_titles:
        label = title.strip()
        if label and label not in locked:
            locked.append(label)
    for raw in _clean_onscreen_for_imagegen(page.onscreen_text).splitlines():
        line = raw.strip()
        if not line or line in locked:
            continue
        relation_label = re.match(
            r"^(?:[-*•]\s*)?([^：:\n]{2,14})[：:]",
            line,
        )
        if relation_label:
            label = relation_label.group(1).strip()
            if (
                label.endswith("关系")
                or label
                in {
                    "工作流",
                    "业务含义",
                    "四层贯通",
                    "页面主线",
                }
            ) and label not in locked:
                locked.append(label)
        if re.search(r"\d", line):
            locked.append(line)
    return "\n".join(locked).strip()


MAX_IMAGE_LOCKED_LINES = 7
MAX_IMAGE_LOCKED_LINE_CHARS = 14
MAX_IMAGE_LOCKED_CHARS = 84


def select_image_locked_text(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    """Return short, bitmap-safe text while leaving body copy editable."""

    raw = page.image_locked_text.strip() or locked_onscreen_text(page, visual_context)
    if not raw and not page.field_order and page.title.strip():
        # Older free-form final scripts do not expose structured fields.  Keep
        # their page heading as the minimal safe visible anchor.
        raw = page.title.strip()
    candidates = [line.strip(" -*") for line in raw.splitlines() if line.strip()]
    selected: list[str] = []
    total = 0
    for line in candidates:
        compact = re.sub(r"\s+", "", line)
        if not compact or line in selected:
            continue
        if len(compact) > MAX_IMAGE_LOCKED_LINE_CHARS:
            # Numeric fact lines often carry a long explanatory tail.  Preserve
            # the compact fact as bitmap copy and leave the tail editable.
            if re.search(r"\d", compact):
                shortened = re.split(r"[，,；;。]", line, maxsplit=1)[0].strip()
                if shortened and len(re.sub(r"\s+", "", shortened)) <= MAX_IMAGE_LOCKED_LINE_CHARS:
                    line = shortened
                    compact = re.sub(r"\s+", "", line)
                else:
                    continue
            else:
                continue
        if len(selected) >= MAX_IMAGE_LOCKED_LINES or total + len(compact) > MAX_IMAGE_LOCKED_CHARS:
            continue
        selected.append(line)
        total += len(compact)
    return "\n".join(selected).strip()


def _semantic_phrase_digest(text: str, *, limit: int = 8) -> list[str]:
    """Turn visible copy into short semantic anchors, never a copy block.

    The digest deliberately splits on Chinese list punctuation and joins the
    resulting terms with slashes. This gives ImageGen concrete business nouns
    and actions without presenting the approved sentence as a bitmap layout
    instruction.
    """

    cleaned = re.sub(r"\*+", "", text or "").strip(" -*")
    if not cleaned:
        return []
    parts = [
        part.strip()
        for part in re.split(r"[，,、；;。:：→—\-]+", cleaned)
        if part.strip()
    ]
    anchors: list[str] = []
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip()
        if not part or part in anchors:
            continue
        # Remove editorial lead-ins while keeping the underlying business term.
        part = re.sub(r"^(?:主要需求是|围绕|包括|适合|采用|形成|客户可以|可以)", "", part).strip()
        if not part:
            continue
        if len(part) > 24:
            part = part[:24].rstrip("，,；;。")
        anchors.append(part)
        if len(anchors) >= limit:
            break
    return anchors


def render_semantic_visual_brief(page: ScriptPage) -> str:
    """Render a compact, non-rendering semantic brief for ImageGen."""

    groups: list[str] = []
    current = "未命名模块"
    title_set = {title.strip() for title in page.module_titles if title.strip()}
    for raw in page.onscreen_text.splitlines():
        line = re.sub(r"\*+", "", raw).strip()
        if not line:
            continue
        if line in title_set:
            current = line
            continue
        if line.startswith(("-", "*", "•")):
            anchors = _semantic_phrase_digest(line, limit=7)
            if anchors:
                groups.append(f"- {current}：" + " / ".join(anchors))
    if not groups:
        anchors = _semantic_phrase_digest(page.onscreen_text, limit=12)
        if anchors:
            groups.append("- 页面业务锚点：" + " / ".join(anchors))
    return "\n".join(groups)


def resolve_text_render_mode(
    style_lock: Path,
    *,
    explicit: str | None = None,
) -> str:
    """Resolve the text/image boundary without changing legacy styles."""

    if explicit:
        return validate_text_render_mode(explicit)
    style = _selected_content_first_style(style_lock)
    configured = str(style.get("default_text_render_mode") or "").strip()
    if configured:
        return validate_text_render_mode(configured)
    return DEFAULT_TEXT_RENDER_MODE


def _selected_content_first_style(style_lock: Path) -> dict[str, Any]:
    """Load a selected style with a non-weakenable Style 09 baseline.

    Project locks are snapshots and older Style 09 locks may contain experimental
    scene-first wording.  Preserve their selected palette, but always compile
    Style 09 from the canonical library contract so a historical lock cannot
    silently weaken the text-led, single-medium presentation rules.
"""

    payload = load_style_lock(style_lock)
    style = payload.get("style")
    if not isinstance(style, dict):
        raise ValueError(f"visual style lock has no selected style: {style_lock}")
    name = str(style.get("name") or "").strip()
    colors = style.get("colors")
    if not name or not isinstance(colors, dict) or not colors:
        raise ValueError(
            f"visual style lock must provide style name and colors: {style_lock}"
        )
    if int(style.get("id") or 0) != 9:
        return style
    canonical = resolve_default_style(style_id=9)
    canonical["colors"] = dict(colors)
    # Keep the live STYLE09 reference contract refreshed by load_style_lock;
    # only fall back to the bundled JSON contract when the lock has none.
    lock_contract = str(style.get("prompt_contract") or "").strip()
    if lock_contract:
        canonical["prompt_contract"] = lock_contract
    return canonical
