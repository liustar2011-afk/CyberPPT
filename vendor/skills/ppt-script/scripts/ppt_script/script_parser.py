from __future__ import annotations

import re

from .models import ScriptSlide
from .planning import extract_source_ids

_HEADING_RE = re.compile(
    r"^\s*#{1,6}\s*(?:第\s*)?(?P<num>\d+)\s*(?:页|頁|slide)\s*(?:[｜|:：—\-]\s*)?(?P<title>.*?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_FIELD_LINE_RE = re.compile(r"^[^\n：:]{2,24}[：:][ \t]*.*$", re.MULTILINE)
_SECTION_MARKERS = ("上屏文字", "备注讲解词", "演讲者备注", "内容关系草图", "本页内容关系判断", "第二段视觉转译接口")
_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(秒|分钟|分)")


def _extract_block(content: str, marker: str) -> str:
    match = re.search(rf"^{re.escape(marker)}[：:][ \t]*(.*)$", content, re.MULTILINE)
    if not match:
        return ""
    lines: list[str] = []
    first = match.group(1).strip()
    if first:
        lines.append(first)
    for raw in content[match.end():].splitlines():
        line, stripped = raw.rstrip(), raw.strip()
        if stripped == "---":
            break
        if stripped and _FIELD_LINE_RE.match(stripped) and not line.startswith((" ", "\t", "-")):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _extract_section(content: str, marker: str) -> str:
    match = re.search(rf"^{re.escape(marker)}[：:][ \t]*(.*)$", content, re.MULTILINE)
    if not match:
        return ""
    lines: list[str] = []
    first = match.group(1).strip()
    if first:
        lines.append(first)
    for raw in content[match.end():].splitlines():
        stripped = raw.strip()
        if stripped == "---":
            break
        if any(re.match(rf"^{re.escape(name)}[：:]", stripped) for name in _SECTION_MARKERS if name != marker):
            break
        lines.append(raw.rstrip())
    return "\n".join(lines).strip()


def _duration_seconds(value: str) -> int | None:
    match = _DURATION_RE.search(value)
    if not match:
        return None
    amount = float(match.group(1))
    return int(round(amount * 60 if match.group(2) in {"分钟", "分"} else amount))


def _parse_slide(number: int, title: str, raw: str) -> ScriptSlide:
    notes = _extract_section(raw, "备注讲解词") or _extract_section(raw, "演讲者备注")
    source_field = (
        _extract_block(raw, "材料依据ID") or _extract_block(raw, "引用Source ID")
        or _extract_block(raw, "引用来源ID") or _extract_block(raw, "引用事实清单ID")
    )
    return ScriptSlide(
        number=number, title=title.strip().strip("|｜:：—- "),
        mission=_extract_block(raw, "页面使命") or _extract_block(raw, "页面职能"),
        key_message=_extract_block(raw, "页面结论") or _extract_block(raw, "核心结论"),
        source_ids=extract_source_ids(source_field), necessity=_extract_block(raw, "页面必要性"),
        previous_relation=_extract_block(raw, "与前页关系"), next_relation=_extract_block(raw, "与后页关系"),
        page_type=_extract_block(raw, "页面类型"), body=_extract_section(raw, "上屏文字"), raw=raw.strip(),
        speaker_opening=_extract_block(notes, "开场承接"), speaker_explanation=_extract_block(notes, "核心讲解"),
        speaker_emphasis=_extract_block(notes, "重点强调"), speaker_boundary=_extract_block(notes, "边界说明"),
        speaker_transition=_extract_block(notes, "转场语"), speaker_notes_raw=notes,
        speaker_notes_seconds=_duration_seconds(_extract_block(notes, "预计讲解时长")),
    )


def parse_script(text: str) -> list[ScriptSlide]:
    normalized = text.replace("\r\n", "\n")
    matches = list(_HEADING_RE.finditer(normalized))
    return [
        _parse_slide(int(match.group("num")), match.group("title"), normalized[match.start():(matches[index + 1].start() if index + 1 < len(matches) else len(normalized))])
        for index, match in enumerate(matches)
    ]
