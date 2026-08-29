"""Render the versioned Script Engine JSON contract to host-compatible Markdown."""
from __future__ import annotations
from typing import Any

from .delivery_cleanliness import argument_pattern_label, sanitize_delivery_prose, sanitize_relation_text

PAGE_TYPE_LABELS = {"cover": "封面", "contents": "目录", "chapter": "章节页", "content": "内容页", "closing": "封底"}

def _text(value: object) -> str:
    return str(value or "").strip()

def _single_line(value: object) -> str:
    """Like `_text`, but for fields the Markdown list/heading structure depends on being one
    physical line. `full_copy` is intentionally exempt because paragraph breaks are meaningful."""
    return " ".join(_text(value).split())

def _render_onscreen(sections: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for section in sections:
        heading = _single_line(section.get("heading")).rstrip("：:")
        body = _single_line(section.get("text"))
        items = [_single_line(item) for item in (section.get("items") or []) if _text(item)]
        if heading and body: lines.append(f"- {heading}：{body}")
        elif heading: lines.append(f"- {heading}")
        elif body: lines.append(f"- {body}")
        for item in items: lines.append(f"  - {item}")
    return lines

def _render_visual(slide: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    thesis = _single_line(sanitize_delivery_prose(slide.get("visual_thesis")))
    if thesis: lines.append(thesis)
    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict): continue
        source = _single_line(relation.get("from")); target = _single_line(relation.get("to")); kind = _single_line(sanitize_relation_text(relation.get("relation")))
        if not source or not target: continue
        lines.append(f"{source} → {target}" + (f"：{kind}" if kind else ""))
    return lines

def render_stage02_markdown(payload: dict[str, Any]) -> str:
    deck = payload.get("deck") if isinstance(payload.get("deck"), dict) else {}
    lines: list[str] = []
    title = _single_line(deck.get("title")); goal = _single_line(deck.get("communication_goal"))
    if title: lines.extend([f"# {title}", ""])
    if goal: lines.extend([f"> 交流目标：{goal}", ""])
    for index, slide in enumerate(payload.get("slides") or [], start=1):
        if not isinstance(slide, dict): continue
        raw_id = _text(slide.get("id")) or f"P{index:02d}"
        digits = "".join(char for char in raw_id if char.isdigit())
        page_number = int(digits) if digits else index
        page_title = _single_line(slide.get("title")) or f"第{page_number}页"
        page_type = _text(slide.get("page_type")) or "content"
        lines.extend([f"## P{page_number:02d} {page_title}", "", f"- 页面类型：{PAGE_TYPE_LABELS.get(page_type, page_type)}", f"- 页面标题：{page_title}"])
        subtitle = _single_line(slide.get("subtitle"))
        if subtitle: lines.append(f"- 页面副标题：{subtitle}")
        content_load = _single_line(slide.get("content_load"))
        if content_load: lines.append(f"- 内容负载：{content_load}")
        mission = _single_line(slide.get("mission")); core_message = _single_line(slide.get("core_message"))
        if mission: lines.append(f"- 页面使命：{mission}")
        if core_message: lines.append(f"- 核心结论：{core_message}")
        argument = slide.get("argument") if isinstance(slide.get("argument"), dict) else {}
        pattern = _single_line(argument_pattern_label(argument.get("pattern"))); chain = [_single_line(i) for i in (argument.get("chain") or []) if _text(i)]
        if pattern or chain:
            logic = " → ".join(chain); value = "｜".join(part for part in (pattern, logic) if part)
            lines.append(f"- 主论证链：{value}")
        full_copy = sanitize_delivery_prose(slide.get("full_copy"))
        if full_copy: lines.extend(["", "### 完整文字稿", "", full_copy])
        onscreen = slide.get("onscreen") if isinstance(slide.get("onscreen"), list) else []
        onscreen_lines = _render_onscreen([item for item in onscreen if isinstance(item, dict)])
        if onscreen_lines: lines.extend(["", "### 上屏文字", "", *onscreen_lines])
        visual_lines = _render_visual(slide)
        if visual_lines: lines.extend(["", "### 视觉结构", "", *visual_lines])
        notes = sanitize_delivery_prose(slide.get("speaker_notes"))
        if notes: lines.extend(["", "### 演讲者备注", "", notes])
        source_refs = [_text(item) for item in (slide.get("source_refs") or []) if _text(item)]
        if source_refs: lines.extend(["", "### 内容来源", "", f"- {'、'.join(source_refs)}"])
        lines.extend(["", "---", ""])
    return "\n".join(lines).rstrip() + "\n"
