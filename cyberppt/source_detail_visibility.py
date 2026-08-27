"""Detect when source-backed detail is compressed into an opaque label."""
from __future__ import annotations

import re
from collections.abc import Iterable


_MEANINGFUL_RE = re.compile(r"[一-鿿A-Za-z0-9]")
_CLAUSE_SPLIT_RE = re.compile(r"[，,、；;。！？!?\n]+")
_FUNCTIONAL_PARENT_RE = re.compile(
    r"(?:定位|能力|任务|职责|作用|场景|验证|支撑|衔接|要求|安排|机制)"
)
_LIST_WRAPPER_TERMS = (
    "项目",
    "重点",
    "主要",
    "相关",
    "场景",
    "方向",
    "类别",
    "类型",
    "能力",
    "任务",
    "内容",
    "包括",
    "包含",
    "覆盖",
    "聚焦",
    "围绕",
    "列为",
    "已",
    "等",
    "之一",
)


def meaningful_char_count(value: object) -> int:
    return len(_MEANINGFUL_RE.findall(str(value or "")))


def clean_visible_line(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^[-*+•]\s*", "", text).strip()
    text = re.sub(r"^\*\*(.+?)\*\*$", r"\1", text).strip()
    return text


def is_bare_business_label(value: object) -> bool:
    """A compact noun-like label with no attached explanatory payload."""

    text = clean_visible_line(value)
    if not text or "：" in text or ":" in text:
        return False
    chars = meaningful_char_count(text)
    if chars < 2 or chars > 10:
        return False
    return True


def _local_source_clauses(label: str, statements: Iterable[str]) -> tuple[str, ...]:
    clauses: list[str] = []
    for statement in statements:
        for clause in _CLAUSE_SPLIT_RE.split(str(statement or "")):
            clause = clause.strip()
            if label and label in clause:
                clauses.append(clause)
    return tuple(dict.fromkeys(clauses))


def source_has_richer_item_detail(label: object, statements: Iterable[str]) -> bool:
    """Return true only when the label's local source clause carries detail.

    Splitting enumeration punctuation keeps a source list such as
    ``行业治理、市场运行、绿色低碳`` from masquerading as four explained
    items. Generic list wrappers are removed before measuring the remainder.
    """

    clean_label = clean_visible_line(label)
    if not clean_label:
        return False
    for clause in _local_source_clauses(clean_label, statements):
        remainder = clause.replace(clean_label, "")
        for term in _LIST_WRAPPER_TERMS:
            remainder = remainder.replace(term, "")
        if meaningful_char_count(remainder) >= 6:
            return True
    return False


def functional_group_needs_item_explanations(
    heading: object,
    items: Iterable[object],
    *,
    content_load: object = "standard",
    label_only_allowed: bool = False,
) -> bool:
    """Require payload for role-bearing groups unless PLAN explicitly opts out."""

    if label_only_allowed or str(content_load or "standard") == "light":
        return False
    values = [clean_visible_line(item) for item in items if clean_visible_line(item)]
    if len(values) < 2 or not _FUNCTIONAL_PARENT_RE.search(str(heading or "")):
        return False
    return any(is_bare_business_label(value) for value in values)
