from __future__ import annotations

import re


_NOTE_FIELDS = ("开场承接", "核心讲解", "重点强调", "边界说明", "转场语", "预计讲解时长")


def _notes_section(content: str) -> str:
    match = re.search(r"^(?:备注讲解词|演讲者备注)[：:]\s*(.*?)(?:\n---|\Z)", content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _note_field(content: str, name: str) -> str:
    notes = _notes_section(content)
    match = re.search(rf"^{re.escape(name)}[：:]\s*(.*)$", notes, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    first = match.group(1).strip()
    tail = notes[start:]
    end_positions = []
    for field in _NOTE_FIELDS:
        if field == name:
            continue
        next_match = re.search(rf"^\s*{re.escape(field)}[：:]", tail, re.MULTILINE)
        if next_match:
            end_positions.append(next_match.start())
    body = tail[: min(end_positions)] if end_positions else tail
    parts = [first] if first else []
    if body.strip():
        parts.append(body.strip())
    return "\n".join(parts).strip()


def _first_sentence(text: str) -> str:
    compact = re.sub(r"\s+", "", text.strip())
    if not compact:
        return ""
    match = re.match(r".*?[。！？；]", compact)
    return match.group(0) if match else compact


def build_full_understanding_context(content: str) -> str:
    fields = [("核心讲解", _note_field(content, "核心讲解")), ("重点强调", _note_field(content, "重点强调")), ("边界说明", _note_field(content, "边界说明"))]
    fields = [(label, value) for label, value in fields if value]
    if not fields:
        return ""
    lines = ["【页面理解上下文｜禁止上屏】", "用途：仅用于理解业务含义、表达重点和边界，不属于画面文字。", "渲染权限：false"]
    for label, value in fields:
        lines.extend([f"{label}：", value])
    return "\n".join(lines)


def build_compact_understanding_context(content: str) -> str:
    parts = [_first_sentence(_note_field(content, field)) for field in ("核心讲解", "重点强调", "边界说明")]
    summary = "".join(part for part in parts if part)
    if not summary:
        return ""
    return "\n".join((
        "【页面理解上下文｜禁止上屏】",
        "渲染权限：false",
        f"讲解摘要：{summary}",
    ))


def build_semantic_summary(content: str) -> str:
    """Return visual-relevant speaker-note semantics without render-control labels."""
    parts = [_first_sentence(_note_field(content, field)) for field in ("核心讲解", "重点强调", "边界说明")]
    meta_markers = ("原文", "源材料", "待复核", "尚待", "未提供", "需法务", "字段缺口", "无来源")
    return "".join(part for part in parts if part and not any(marker in part for marker in meta_markers))
