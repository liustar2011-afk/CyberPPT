"""Derive Stage 02 business relationships from canonical final-script Markdown semantics.

CyberPPT-Script keeps the audience-facing Markdown clean: it exposes semantic
relationships through ``### 视觉结构`` instead of the legacy hidden
``content_relations`` receipt. Stage 02 owns the adapter from that script
semantics into its internal ``business_relationships`` model.

The adapter preserves *business-semantic families* rather than choosing visual
topology. A peer classification, evidence support, problem-response mapping,
optional progression, and layered support remain distinct even when older
CyberPPT code historically collapsed them into the same expression form.
"""
from __future__ import annotations

import re
from typing import Iterable

_ARROW_RE = re.compile(
    r"^\s*(?P<subject>.+?)\s*(?:→|->|⇒)\s*(?P<object>.+?)"
    r"(?:\s*[：:]\s*(?P<label>.+?))?\s*$"
)
_EVIDENCE_NOTE_RE = re.compile(
    r"\s*[（(]\s*(?:explicit|inferred|speculative)\b[^）)]*[）)]\s*$",
    re.I,
)


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n；;。")


def _clean_relation_label(value: object) -> str:
    label = _clean(value)
    label = _EVIDENCE_NOTE_RE.sub("", label).strip()
    return label


def _semantic_relation(label: str) -> str:
    """Map wording to a business-semantic family, never to visual topology."""

    text = label.lower()
    if "可独立" in text and any(token in text for token in ("逐步深化", "逐步", "深化")):
        return "optional_progression"
    if any(token in text for token in ("因果", "导致", "引发", "驱动")):
        return "causes"
    if any(token in text for token in ("反馈", "回流", "回到", "回返")):
        return "feeds_back_to"
    if any(token in text for token in ("顺序", "衔接", "推进至", "转入", "先后")):
        return "sequence_before"
    if any(token in text for token in ("分层支撑", "层级支撑", "承托", "托底")):
        return "layer_supports"
    if any(token in text for token in ("并列支撑", "共同支撑", "证据支撑", "支撑")):
        return "evidence_supports"
    if any(token in text for token in ("问题回应", "问题到响应", "问题—响应", "回应", "映射")):
        return "problem_response"
    if any(token in text for token in ("并列分类", "分类", "同类", "并列")):
        return "peer_classification"
    if any(token in text for token in ("分层", "层级")):
        return "layered_as"
    if any(token in text for token in ("覆盖", "贯穿")):
        return "covers"
    if any(token in text for token in ("边界", "约束", "护栏")):
        return "bounded_by"
    if any(token in text for token in ("对照", "比较", "差异")):
        return "comparison"
    if any(token in text for token in ("对应", "匹配", "适配")):
        return "semantic_mapping"
    if any(token in text for token in ("形成", "转化", "生成", "产出", "汇聚")):
        return "transforms_to"
    if "构成" in text:
        return "composed_of"
    return "semantic_association"


def _relation_record(subject: str, object_: str, label: str, *, confidence: str = "high") -> dict[str, object]:
    normalized_label = _clean_relation_label(label) or "语义关联"
    return {
        "subject": subject,
        "relation": _semantic_relation(normalized_label),
        "objects": [object_],
        "direction": "subject_to_objects",
        "condition": "",
        "modality": "",
        "basis": "derived_from_script_visual_structure",
        "confidence": confidence,
        "relation_label": normalized_label,
        "authority_ref": "final-script.visual-structure",
    }


def _explicit_arrow_relations(visual_structure: str) -> list[dict[str, object]]:
    relationships: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in str(visual_structure or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = _ARROW_RE.match(line)
        if not match:
            continue
        subject = _clean(match.group("subject"))
        object_ = _clean(match.group("object"))
        label = _clean_relation_label(match.group("label") or "")
        if not subject or not object_:
            continue
        key = (subject, object_, label)
        if key in seen:
            continue
        seen.add(key)
        relationships.append(_relation_record(subject, object_, label))
    return relationships


def _module_values(module_titles: Iterable[str], top_level_module_titles: Iterable[str]) -> list[str]:
    preferred = [_clean(value) for value in top_level_module_titles if _clean(value)]
    values = preferred or [_clean(value) for value in module_titles if _clean(value)]
    return list(dict.fromkeys(values))


def _structural_fallback(*, visual_structure: str, title: str, module_titles: Iterable[str], top_level_module_titles: Iterable[str]) -> list[dict[str, object]]:
    text = _clean(visual_structure)
    modules = _module_values(module_titles, top_level_module_titles)
    if len(modules) < 2:
        return []

    subject = _clean(title) or "本页业务对象"
    if any(token in text for token in ("并列分类", "并列结构", "并列存在", "相互独立", "分类结构")):
        return [{
            "subject": subject,
            "relation": "peer_classification",
            "objects": modules,
            "direction": "one_to_many",
            "condition": "",
            "modality": "",
            "basis": "derived_from_script_visual_structure",
            "confidence": "high",
            "relation_label": "并列分类",
            "authority_ref": "final-script.visual-structure",
        }]

    if any(token in text for token in ("顺序流程", "推进路径", "演进路径", "依次推进", "先后顺序")):
        return [_relation_record(left, right, "顺序衔接") for left, right in zip(modules, modules[1:])]

    if "闭环" in text:
        relations = [_relation_record(left, right, "顺序衔接") for left, right in zip(modules, modules[1:])]
        relations.append(_relation_record(modules[-1], modules[0], "反馈回流"))
        return relations

    if any(token in text for token in ("分层结构", "分层架构", "层级结构", "层级关系")):
        return [{
            "subject": subject,
            "relation": "layered_as",
            "objects": modules,
            "direction": "one_to_many",
            "condition": "",
            "modality": "",
            "basis": "derived_from_script_visual_structure",
            "confidence": "high",
            "relation_label": "分层结构",
            "authority_ref": "final-script.visual-structure",
        }]
    return []


def derive_business_relationships(*, visual_structure: str, title: str = "", module_titles: Iterable[str] = (), top_level_module_titles: Iterable[str] = ()) -> tuple[dict[str, object], ...]:
    """Return Stage 02 internal relations without changing the source script."""

    explicit = _explicit_arrow_relations(visual_structure)
    if explicit:
        return tuple(explicit)
    return tuple(_structural_fallback(
        visual_structure=visual_structure,
        title=title,
        module_titles=module_titles,
        top_level_module_titles=top_level_module_titles,
    ))
