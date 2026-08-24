"""Derive Stage 02 business relationships from canonical final-script Markdown semantics.

CyberPPT-Script keeps the audience-facing Markdown clean: it exposes semantic
relationships through ``### 视觉结构`` instead of the legacy hidden
``content_relations`` receipt. Stage 02 owns the adapter from that script
semantics into its internal ``business_relationships`` model. This module is
deliberately deterministic and conservative: explicit visual relationship
lines win; structural fallbacks are used only when the script itself declares
a classification, sequence, loop, or layered structure.
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


def _canonical_relation(label: str) -> str:
    """Map script wording onto the small relation vocabulary Stage 02 understands."""

    text = label.lower()
    if any(token in text for token in ("因果", "导致", "引发", "驱动")):
        return "causes"
    if any(token in text for token in ("顺序", "衔接", "进入下一", "推进至", "转入", "先后")):
        return "sequence_before"
    if any(token in text for token in ("反馈", "回流", "回到", "回返")):
        return "sequence_after"
    if any(token in text for token in ("覆盖", "贯穿")):
        return "covers"
    if any(token in text for token in ("支撑", "承托", "托底")):
        return "supports"
    if any(token in text for token in ("映射", "对应", "回应", "匹配", "适配")):
        return "corresponds_to"
    if any(token in text for token in ("并列", "分类", "同类")):
        return "classified_as"
    if any(token in text for token in ("分层", "层级")):
        return "layered_as"
    if any(token in text for token in ("边界", "约束", "护栏")):
        return "bounded_by"
    if any(token in text for token in ("形成", "转化", "生成", "产出", "构成", "汇聚")):
        return "provides_to"
    return "corresponds_to"


def _relation_record(
    subject: str,
    object_: str,
    label: str,
    *,
    confidence: str = "high",
) -> dict[str, object]:
    normalized_label = _clean_relation_label(label) or "语义关联"
    return {
        "subject": subject,
        "relation": _canonical_relation(normalized_label),
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


def _module_values(
    module_titles: Iterable[str], top_level_module_titles: Iterable[str]
) -> list[str]:
    preferred = [_clean(value) for value in top_level_module_titles if _clean(value)]
    values = preferred or [_clean(value) for value in module_titles if _clean(value)]
    return list(dict.fromkeys(values))


def _structural_fallback(
    *,
    visual_structure: str,
    title: str,
    module_titles: Iterable[str],
    top_level_module_titles: Iterable[str],
) -> list[dict[str, object]]:
    """Derive only relationships explicitly declared by visual-structure prose."""

    text = _clean(visual_structure)
    modules = _module_values(module_titles, top_level_module_titles)
    if len(modules) < 2:
        return []

    subject = _clean(title) or "本页业务对象"
    if any(token in text for token in ("并列分类", "并列结构", "并列存在", "相互独立", "分类结构")):
        return [{
            "subject": subject,
            "relation": "classified_as",
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
        return [
            _relation_record(left, right, "顺序衔接")
            for left, right in zip(modules, modules[1:])
        ]

    if "闭环" in text:
        relations = [
            _relation_record(left, right, "顺序衔接")
            for left, right in zip(modules, modules[1:])
        ]
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


def derive_business_relationships(
    *,
    visual_structure: str,
    title: str = "",
    module_titles: Iterable[str] = (),
    top_level_module_titles: Iterable[str] = (),
) -> tuple[dict[str, object], ...]:
    """Return Stage 02 internal relations without changing the source script.

    Explicit ``A → B：relation`` lines are the strongest canonical Markdown
    signal and are consumed first. If there are none, a small set of explicit
    structural statements can be projected from the page's module set. When
    neither signal exists the result stays empty so genuinely ambiguous pages
    can still be reviewed instead of receiving invented business logic.
    """

    explicit = _explicit_arrow_relations(visual_structure)
    if explicit:
        return tuple(explicit)
    return tuple(
        _structural_fallback(
            visual_structure=visual_structure,
            title=title,
            module_titles=module_titles,
            top_level_module_titles=top_level_module_titles,
        )
    )
