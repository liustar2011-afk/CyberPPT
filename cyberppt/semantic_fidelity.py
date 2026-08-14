"""Source-grounded semantic fidelity checks for Stage 01 page contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


OBJECTIVE_RELATIONS = frozenset(
    {
        "composed_of",
        "contains",
        "part_of",
        "classified_as",
        "layered_as",
        "corresponds_to",
        "sequence_before",
        "sequence_after",
        "applies_to",
        "covers",
        "bounded_by",
        "provides_to",
        "supports",
    }
)
STRONG_RELATIONS = frozenset(
    {
        "causes",
        "requires",
        "depends_on",
        "enables",
        "ensures",
        "necessary_for",
        "sufficient_for",
    }
)
VALID_RELATIONS = OBJECTIVE_RELATIONS | STRONG_RELATIONS
RELATION_SOURCE_MARKERS = {
    "causes": ("导致", "造成", "引起"),
    "requires": ("需要", "必须", "要求"),
    "depends_on": ("依赖", "取决于"),
    "enables": ("使得", "能够", "有助于"),
    "ensures": ("确保", "保障"),
    "necessary_for": ("必要", "前提", "才能"),
    "sufficient_for": ("充分", "即可", "足以"),
}

HIGH_RISK_TERMS = (
    "才能",
    "必须",
    "只有",
    "决定",
    "确保",
    "必然",
    "缺一不可",
    "不可替代",
)
PROMOTED_RELATION_TERMS = ("协同", "驱动", "导致", "依赖", "实现")


@dataclass(frozen=True)
class FidelityIssue:
    code: str
    message: str


def source_text(source_refs: Iterable[object], records: Mapping[str, Mapping[str, object]]) -> str:
    return "\n".join(
        str(records.get(str(ref), {}).get("statement") or "") for ref in source_refs
    )


def audit_relation_shape(relations: object) -> list[FidelityIssue]:
    if not isinstance(relations, list) or not relations:
        return [FidelityIssue("CONTENT_RELATIONS_MISSING", "Content pages must declare their source-supported content relations.")]
    issues: list[FidelityIssue] = []
    for index, item in enumerate(relations, 1):
        if not isinstance(item, dict):
            issues.append(FidelityIssue("CONTENT_RELATION_INVALID", f"Content relation {index} must be an object."))
            continue
        relation = str(item.get("relation") or "")
        refs = item.get("source_refs")
        if relation not in VALID_RELATIONS:
            issues.append(FidelityIssue("CONTENT_RELATION_INVALID", f"Unsupported content relation: {relation or '<empty>'}."))
        if not isinstance(refs, list) or not refs:
            issues.append(FidelityIssue("CONTENT_RELATION_UNSUPPORTED", f"Content relation {index} must cite source_refs."))
    return issues


def audit_semantic_strength(output: str, evidence: str) -> list[FidelityIssue]:
    issues: list[FidelityIssue] = []
    for term in HIGH_RISK_TERMS:
        if term in output and term not in evidence:
            issues.append(FidelityIssue("MODALITY_STRENGTH_UPGRADED", f"Core meaning introduces unsupported necessity, certainty, or exclusivity: {term}"))
    for term in PROMOTED_RELATION_TERMS:
        if term in output and term not in evidence:
            issues.append(FidelityIssue("RELATION_STRENGTH_UPGRADED", f"Core meaning introduces an unsupported relationship: {term}"))
    return issues


def strong_relation_supported(relation: str, evidence: str) -> bool:
    return any(marker in evidence for marker in RELATION_SOURCE_MARKERS.get(relation, ()))
