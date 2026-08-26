"""Source-grounded strength checks for author-supplied visual semantics."""

from __future__ import annotations

import re

from cyberppt.semantic_fidelity import (
    RELATION_SOURCE_MARKERS,
    audit_semantic_strength,
    source_text,
)

from .models import ScriptPage, ScriptQualityIssue, _issue


_VISUAL_FIDELITY_CODES = {
    "MODALITY_STRENGTH_UPGRADED": "AUTHOR_VISUAL_MODALITY_STRENGTH_UPGRADED",
    "RELATION_STRENGTH_UPGRADED": "AUTHOR_VISUAL_RELATION_STRENGTH_UPGRADED",
}
_LAYOUT_NOUNS = (
    "行列",
    "位置",
    "中心",
    "连接",
    "入口",
    "出口",
    "版式",
    "布局",
    "画布",
    "卡片",
    "节点",
    "区域",
    "容器",
    "文字",
    "内容",
    "数量",
    "长度",
    "阅读顺序",
    "视觉顺序",
)
_LAYOUT_NOUN_RE = "(?:" + "|".join(map(re.escape, _LAYOUT_NOUNS)) + ")"
_LAYOUT_STRENGTH_RE = re.compile(
    rf"{_LAYOUT_NOUN_RE}[^，,。；;\n]{{0,8}}"
    rf"(?:决定|驱动|依赖|实现)[^，,。；;\n]{{0,8}}{_LAYOUT_NOUN_RE}"
)
_SEMANTIC_UNIT_RE = re.compile(r"[。！？；;\n]+")
_CONDITIONAL_DECISION_RE = re.compile(
    r"决定是否(?P<object>[0-9A-Za-z\u4e00-\u9fff]{1,12})"
)
_CONDITION_GATE_RE = re.compile(
    r"(?:验证|条件|门槛|标准)[^。；;\n]{0,8}(?:通过|满足|达到)[^。；;\n]{0,4}(?:后|再|方可)"
)


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list):
        return tuple(
            text
            for item in value
            for text in _string_values(item)
        )
    if isinstance(value, dict):
        return tuple(
            text
            for item in value.values()
            for text in _string_values(item)
        )
    return ()


def _approved_visual_semantic_corpus(
    contract: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> str:
    """Collect approved page semantics without trusting authored page copy."""

    parts: list[str] = []
    for field in (
        "core_message",
        "main_message",
        "key_judgment",
        "page_mission",
        "audience_question",
    ):
        parts.extend(_string_values(contract.get(field)))
    for field in ("core_message_derivation", "judgment_derivation"):
        parts.extend(_string_values(contract.get(field)))
    for item in contract.get("argument_chain") or []:
        if isinstance(item, dict):
            parts.extend(_string_values(item.get("statement")))
    for relation in contract.get("content_relations") or []:
        if not isinstance(relation, dict):
            continue
        parts.extend(_string_values(relation))
        relation_type = str(relation.get("relation") or "").strip()
        parts.extend(RELATION_SOURCE_MARKERS.get(relation_type, ()))
    refs = tuple(
        str(ref)
        for ref in contract.get("source_refs") or []
        if str(ref).strip()
    )
    parts.append(source_text(refs, records_by_id))
    return "\n".join(part for part in parts if part)


def _without_layout_strength_phrases(unit: str) -> str:
    """Remove explicit layout-to-layout strength phrases, retaining business claims."""

    return _LAYOUT_STRENGTH_RE.sub("", unit).strip()


def _conditional_decision_evidence(output: str, evidence: str) -> str:
    """Recognize the approved condition-gate equivalent of 决定是否放大."""

    evidence_units = tuple(_SEMANTIC_UNIT_RE.split(evidence))
    supported_objects = tuple(
        match.group("object")
        for match in _CONDITIONAL_DECISION_RE.finditer(output)
        if any(
            match.group("object") in unit and _CONDITION_GATE_RE.search(unit)
            for unit in evidence_units
        )
    )
    if not supported_objects:
        return evidence
    return evidence + "\n决定"


def _author_visual_semantic_strength_issues(
    page: ScriptPage,
    contract: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[ScriptQualityIssue]:
    """Reject unsupported strong business meaning in author visual fields."""

    if page.page_type != "content":
        return []
    approved = _approved_visual_semantic_corpus(contract, records_by_id)
    issues: list[ScriptQualityIssue] = []
    seen: set[tuple[str, str, str]] = set()
    for field, text in (
        ("visual_structure", page.visual_structure),
        ("visual_proof", page.visual_proof),
    ):
        for unit in _SEMANTIC_UNIT_RE.split(text):
            unit = unit.strip()
            semantic_unit = _without_layout_strength_phrases(unit)
            if not semantic_unit:
                continue
            evidence = _conditional_decision_evidence(semantic_unit, approved)
            for fidelity_issue in audit_semantic_strength(semantic_unit, evidence):
                code = _VISUAL_FIDELITY_CODES.get(fidelity_issue.code)
                if code is None:
                    continue
                key = (code, field, unit)
                if key in seen:
                    continue
                seen.add(key)
                issues.append(
                    _issue(
                        code,
                        page,
                        f"Author-supplied {field} strengthens the approved page semantics: {fidelity_issue.message}",
                        "Restore the approved relationship or modality in the visual field, or revise the authoritative page semantics and cited evidence first.",
                        evidence=(f"field={field}", unit),
                    )
                )
    return issues


__all__ = [
    "_approved_visual_semantic_corpus",
    "_author_visual_semantic_strength_issues",
    "_conditional_decision_evidence",
    "_without_layout_strength_phrases",
]
