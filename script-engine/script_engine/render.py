"""Render the versioned Script Engine JSON contract to host-compatible Markdown."""

from __future__ import annotations

from typing import Any


PAGE_TYPE_LABELS = {
    "cover": "封面",
    "contents": "目录",
    "chapter": "章节页",
    "content": "内容页",
    "closing": "封底",
}


def _text(value: object) -> str:
    return str(value or "").strip()


def _render_onscreen(sections: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for section in sections:
        heading = _text(section.get("heading"))
        body = _text(section.get("text"))
        items = [
            _text(item)
            for item in (section.get("items") or [])
            if _text(item)
        ]
        if heading and body:
            lines.append(f"- {heading}：{body}")
        elif heading:
            lines.append(f"- {heading}")
        elif body:
            lines.append(f"- {body}")
        for item in items:
            lines.append(f"  - {item}")
    return lines


def _render_visual(slide: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    thesis = _text(slide.get("visual_thesis"))
    if thesis:
        lines.append(thesis)
    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict):
            continue
        source = _text(relation.get("from"))
        target = _text(relation.get("to"))
        kind = _text(relation.get("relation"))
        if not source or not target:
            continue
        suffix = f"：{kind}" if kind else ""
        lines.append(f"{source} → {target}{suffix}")
    return lines


def render_stage02_markdown(payload: dict[str, Any]) -> str:
    """Render JSON to Markdown accepted by the existing CyberPPT Stage 02 parser.

    The renderer intentionally targets only the stable script-field surface used
    by Stage 02. It does not expose Script Engine workbench or planning files.
    """

    deck = payload.get("deck") if isinstance(payload.get("deck"), dict) else {}
    lines: list[str] = []
    title = _text(deck.get("title"))
    if title:
        lines.extend([f"# {title}", ""])
    goal = _text(deck.get("communication_goal"))
    if goal:
        lines.extend([f"> 交流目标：{goal}", ""])

    for index, slide in enumerate(payload.get("slides") or [], start=1):
        if not isinstance(slide, dict):
            continue
        raw_id = _text(slide.get("id")) or f"P{index:02d}"
        digits = "".join(char for char in raw_id if char.isdigit())
        page_number = int(digits) if digits else index
        page_title = _text(slide.get("title")) or f"第{page_number}页"
        page_type = _text(slide.get("page_type")) or "content"
        lines.extend([
            f"## P{page_number:02d} {page_title}",
            "",
            f"- 页面类型：{PAGE_TYPE_LABELS.get(page_type, page_type)}",
            f"- 页面标题：{page_title}",
        ])

        mission = _text(slide.get("mission"))
        if mission:
            lines.append(f"- 页面使命：{mission}")
        core_message = _text(slide.get("core_message"))
        if core_message:
            lines.append(f"- 核心结论：{core_message}")

        argument = slide.get("argument") if isinstance(slide.get("argument"), dict) else {}
        pattern = _text(argument.get("pattern"))
        chain = [_text(item) for item in (argument.get("chain") or []) if _text(item)]
        if pattern or chain:
            logic = " → ".join(chain)
            value = "｜".join(part for part in (pattern, logic) if part)
            lines.append(f"- 主论证链：{value}")

        full_copy = _text(slide.get("full_copy"))
        if full_copy:
            lines.extend(["", "### 完整文字稿", "", full_copy])

        onscreen = slide.get("onscreen") if isinstance(slide.get("onscreen"), list) else []
        onscreen_lines = _render_onscreen([item for item in onscreen if isinstance(item, dict)])
        if onscreen_lines:
            lines.extend(["", "### 上屏文字", "", *onscreen_lines])

        source_refs = [_text(item) for item in (slide.get("source_refs") or []) if _text(item)]
        if source_refs:
            lines.extend(["", f"- 证据：{'、'.join(source_refs)}"])

        visual_lines = _render_visual(slide)
        if visual_lines:
            lines.extend(["", "### 视觉结构", "", *visual_lines])

        notes = _text(slide.get("speaker_notes"))
        if notes:
            lines.extend(["", "### 演讲者备注", "", notes])

        lines.extend(["", "---", ""])

    return "\n".join(lines).rstrip() + "\n"
