from __future__ import annotations

import re
from dataclasses import dataclass


_FIELDS = {
    "主视觉中心": "center",
    "业务角色": "role",
    "辅助信息": "supporting",
    "约束信息": "constraints",
    "阅读路径": "reading_path",
}
_CONFLICT_MARKERS = ("双中心", "两个中心", "同等突出", "同等放大", "并列核心")


@dataclass(frozen=True, slots=True)
class VisualFocus:
    center: str = ""
    role: str = ""
    supporting: str = ""
    constraints: str = ""
    reading_path: str = ""
    center_count: int = 0
    raw: str = ""


def _values(text: str, name: str) -> list[str]:
    pattern = rf"(?:^|\n)\s*{re.escape(name)}[：:]\s*([^\n]+)"
    return [value.strip() for value in re.findall(pattern, text or "") if value.strip()]


def parse_visual_focus(text: str) -> VisualFocus:
    found = {attribute: _values(text, label) for label, attribute in _FIELDS.items()}
    return VisualFocus(
        center=found["center"][0] if found["center"] else "",
        role=found["role"][0] if found["role"] else "",
        supporting=found["supporting"][0] if found["supporting"] else "",
        constraints=found["constraints"][0] if found["constraints"] else "",
        reading_path=found["reading_path"][0] if found["reading_path"] else "",
        center_count=len(found["center"]),
        raw=text or "",
    )


def validate_visual_focus(focus: VisualFocus) -> tuple[str, ...]:
    issues: list[str] = []
    if focus.center_count == 0:
        issues.append("missing-center")
    elif focus.center_count != 1:
        issues.append("multiple-centers")
    if not focus.role:
        issues.append("missing-role")
    if not focus.reading_path:
        issues.append("missing-reading-path")
    if any(marker in focus.raw for marker in _CONFLICT_MARKERS):
        issues.append("competing-centers")
    return tuple(issues)


def render_visual_narrative(key_message: str, focus: VisualFocus) -> str:
    sentence = f"画面围绕{key_message}这一核心结论展开，以{focus.center}作为主视觉中心，承担{focus.role}的作用"
    if focus.supporting:
        sentence += f"；{focus.supporting}作为辅助信息退居次级"
    if focus.constraints and focus.constraints != "无":
        sentence += f"，并由{focus.constraints}贯穿或限定整体表达"
    if focus.reading_path:
        sentence += f"；阅读顺序沿{focus.reading_path}自然推进"
    return sentence + "。全页保持单一视觉重心，其他元素不得与主中心竞争。"


def render_compact_visual_priority(focus: VisualFocus) -> str:
    sentence = f"以{focus.center}作为主视觉中心，承担{focus.role}的作用"
    if focus.supporting:
        sentence += f"，{focus.supporting}退居辅助"
    if focus.constraints and focus.constraints != "无":
        sentence += f"，由{focus.constraints}限定表达"
    if focus.reading_path:
        sentence += f"，阅读顺序沿{focus.reading_path}推进"
    return sentence + "；其他元素不与主中心竞争。"
