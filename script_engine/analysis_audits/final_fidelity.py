"""Faithful-mode checks for author-created semantic additions."""
from __future__ import annotations

import re
from typing import Any

from .common import _item_text


_RELATION_PROMOTION_PATTERNS = (
    ("因此", re.compile(r"因此")),
    ("因而", re.compile(r"因而")),
    ("从而", re.compile(r"从而")),
    ("意味着", re.compile(r"意味着")),
    ("决定", re.compile(r"决定(?:了|着)?")),
    ("导致", re.compile(r"导致")),
    ("闭环", re.compile(r"闭环")),
    ("递进/缺一不可", re.compile(r"(?:依次|逐步|逐级)?递进|缺一不可")),
    ("转化为", re.compile(r"转化为")),
    ("价值转化/释放", re.compile(r"价值(?:转化|释放)")),
    ("核心/关键支撑", re.compile(r"(?:核心|关键)支撑")),
    ("协同/运营/长效机制", re.compile(r"(?:协同|运营|长效)机制")),
    ("持续优化", re.compile(r"持续优化")),
    ("复制/规模化推广", re.compile(r"(?:复制推广|规模化推广)")),
    ("只有…才/才能", re.compile(r"只有[^。；\n]{0,50}(?:才|才能)")),
    ("必须…才能/方可", re.compile(r"必须[^。；\n]{0,50}(?:才能|方可)")),
    (
        "需要在…条件/节点下形成/实现/完成/推进/建设",
        re.compile(
            r"需要在[^。；\n]{0,40}(?:条件|节点|要求|背景)?下"
            r"[^。；\n]{0,40}(?:形成|实现|完成|推进|建设)"
        ),
    ),
    ("必然", re.compile(r"必然(?:形成|实现|导致|带来|推动|提升)")),
)

_OUTSIDE_NARRATOR_RE = re.compile(
    r"通知所称|材料指出|材料认为|文件认为|文件指出|原文说明|"
    r"在通知中已明确|根据材料可以看出|从材料看|上述材料表明"
)
_NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)?(?:年\d{1,2}月\d{1,2}日|年\d{1,2}月|亿元|万元|年|月|日|%|％|项|类|级|个|家|亿|万)?"
)
_FORMAL_INSTRUMENT_RE = re.compile(r"《[^》\n]{2,80}》")
_ACHIEVED_RE = re.compile(r"已(?:完成|形成|实现|建立|具备|明确|建成|上线|投入|发布|通过|纳入)")
_OBLIGATION_RE = re.compile(r"必须|应当|不得|严禁")


def _slide_text_fields(slide: dict[str, Any]) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for name in ("title", "subtitle", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
        value = slide.get(name)
        if isinstance(value, str) and value.strip():
            fields.append((name, value.strip()))
    argument = slide.get("argument")
    if isinstance(argument, dict):
        for item_index, value in enumerate(argument.get("chain") or []):
            if isinstance(value, str) and value.strip():
                fields.append((f"argument.chain[{item_index}]", value.strip()))
    for index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        for name in ("heading", "text"):
            value = module.get(name)
            if isinstance(value, str) and value.strip():
                fields.append((f"onscreen[{index}].{name}", value.strip()))
        for item_index, value in enumerate(module.get("items") or []):
            if isinstance(value, str) and value.strip():
                fields.append((f"onscreen[{index}].items[{item_index}]", value.strip()))
    for index, relation in enumerate(slide.get("relationships") or []):
        if not isinstance(relation, dict):
            continue
        for name in ("from", "to", "relation"):
            value = relation.get(name)
            if isinstance(value, str) and value.strip():
                fields.append((f"relationships[{index}].{name}", value.strip()))
    return fields


def _source_surface(
    evidence: list[dict[str, Any]],
    items: dict[str, dict[str, Any]] | None = None,
) -> str:
    parts: list[str] = []
    items = items or {}
    for item in evidence:
        text = _item_text(item)
        if text:
            parts.append(text)
        parts.extend(
            str(value).strip()
            for value in item.get("conditions") or []
            if str(value).strip()
        )
        for number_ref in item.get("number_refs") or []:
            number = items.get(number_ref)
            if not isinstance(number, dict):
                continue
            raw_value = number.get("value")
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            unit = str(number.get("unit") or "").strip()
            for value in values:
                if value is None:
                    continue
                token = str(value).strip()
                if token:
                    parts.append(f"{token}{unit}" if unit else token)
        for entity_ref in item.get("entity_refs") or []:
            entity = items.get(entity_ref)
            if isinstance(entity, dict):
                name = str(entity.get("name") or "").strip()
                if name:
                    parts.append(name)
    return "\n".join(parts)


def faithful_relation_promotion_issues(
    slide: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[str]:
    """Reject unsupported causal, necessity, progression, mechanism or value language."""

    source_text = _source_surface(evidence)
    if not source_text.strip():
        return []

    issues: list[str] = []
    for field, text in _slide_text_fields(slide):
        introduced = sorted(
            label
            for label, pattern in _RELATION_PROMOTION_PATTERNS
            if pattern.search(text) and not pattern.search(source_text)
        )
        if introduced:
            issues.append(
                "FAITHFUL_RELATION_PROMOTED: "
                f"{field} introduces unsupported relationship/synthesis marker(s) {introduced}; "
                "remove the composed relation or explicitly authorize analytical mode"
            )
    return issues


def faithful_semantic_addition_issues(
    slide: dict[str, Any],
    evidence: list[dict[str, Any]],
    items: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    """Reject high-confidence semantic additions that are absent from page evidence.

    This is intentionally conservative. It catches objective additions and clear
    strength/voice promotions; it does not pretend to be a complete entailment
    engine.
    """

    source_text = _source_surface(evidence, items)
    if not source_text.strip():
        return []

    source_numbers = set(_NUMBER_RE.findall(source_text))
    source_instruments = set(_FORMAL_INSTRUMENT_RE.findall(source_text))
    source_has_achieved = bool(_ACHIEVED_RE.search(source_text))
    source_has_obligation = bool(_OBLIGATION_RE.search(source_text))
    source_has_outside_narrator = bool(_OUTSIDE_NARRATOR_RE.search(source_text))

    issues: list[str] = []
    for field, text in _slide_text_fields(slide):
        added_numbers = sorted(set(_NUMBER_RE.findall(text)) - source_numbers)
        if added_numbers:
            issues.append(
                "FAITHFUL_NUMBER_ADDED: "
                f"{field} introduces numeric/date token(s) absent from the page source evidence: {added_numbers}"
            )

        added_instruments = sorted(set(_FORMAL_INSTRUMENT_RE.findall(text)) - source_instruments)
        if added_instruments:
            issues.append(
                "FAITHFUL_FORMAL_INSTRUMENT_ADDED: "
                f"{field} introduces formal instrument name(s) absent from the page source evidence: {added_instruments}"
            )

        if _OUTSIDE_NARRATOR_RE.search(text) and not source_has_outside_narrator:
            issues.append(
                "FAITHFUL_OUTSIDE_NARRATOR: "
                f"{field} changes the speaking position into an outside narrator; state the source proposition directly"
            )

        achieved = sorted(set(_ACHIEVED_RE.findall(text)))
        if achieved and not source_has_achieved:
            issues.append(
                "FAITHFUL_STATUS_PROMOTED: "
                f"{field} introduces achieved/completed status marker(s) absent from the page source evidence: {achieved}"
            )

        obligations = sorted(set(_OBLIGATION_RE.findall(text)))
        if obligations and not source_has_obligation:
            issues.append(
                "FAITHFUL_MODALITY_PROMOTED: "
                f"{field} introduces obligation/prohibition marker(s) absent from the page source evidence: {obligations}"
            )

    return issues


__all__ = [
    "faithful_relation_promotion_issues",
    "faithful_semantic_addition_issues",
]
