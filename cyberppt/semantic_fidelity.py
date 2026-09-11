"""Source-grounded semantic fidelity checks for legacy Stage 01 contracts.

This module remains as a compatibility surface for historical Outline audits.
New Final Script semantic authority lives in ``script_engine.semantic_contract``.
Legacy lexical checks must therefore stay domain-neutral and must not encode
customer, industry, product, course, platform, or project-specific noun lists.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
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
SOURCE_FOUNDATION_RELATIONS = frozenset(
    {
        "flows_to",
        "outputs",
        "precedes",
        "measures",
        "governs",
        "provides",
        "operates",
        "collaborates_with",
        "serves",
        "constrains",
        "relates_to",
    }
)
VALID_RELATIONS = OBJECTIVE_RELATIONS | STRONG_RELATIONS | SOURCE_FOUNDATION_RELATIONS

# Legacy review vocabulary only. Structured provenance/compatibility checks are
# authoritative for new projects; these markers may not be expanded with
# business-specific nouns to fix a single regression.
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

# Composition markers describe a generic semantic relation. The supporting
# comparison intentionally strips only relation syntax and generic structural
# words. It does not maintain a vocabulary of historical business objects.
COMPOSITION_RELATION_MARKERS = (
    "集成",
    "并入",
    "纳入",
    "归入",
    "编入",
    "划入",
    "组合为",
    "组合成",
    "整合为",
    "整合成",
)
_AS_MODULE_RE = re.compile(r"作为[^。！？；;\n]{0,18}(?:模块|组成部分)")
_COMPOSITION_NOISE = (
    *COMPOSITION_RELATION_MARKERS,
    "作为",
    "组成部分",
    "共同交付",
    "模块",
)


@dataclass(frozen=True)
class FidelityIssue:
    code: str
    message: str


def source_text(
    source_refs: Iterable[object],
    records: Mapping[str, Mapping[str, object]],
) -> str:
    return "\n".join(
        str(records.get(str(ref), {}).get("statement") or "") for ref in source_refs
    )


def audit_relation_shape(relations: object) -> list[FidelityIssue]:
    if not isinstance(relations, list) or not relations:
        return [
            FidelityIssue(
                "CONTENT_RELATIONS_MISSING",
                "Content pages must declare their source-supported content relations.",
            )
        ]
    issues: list[FidelityIssue] = []
    for index, item in enumerate(relations, 1):
        if not isinstance(item, dict):
            issues.append(
                FidelityIssue(
                    "CONTENT_RELATION_INVALID",
                    f"Content relation {index} must be an object.",
                )
            )
            continue
        relation = str(item.get("relation") or "")
        refs = item.get("source_refs")
        if relation not in VALID_RELATIONS:
            issues.append(
                FidelityIssue(
                    "CONTENT_RELATION_INVALID",
                    f"Unsupported content relation: {relation or '<empty>'}.",
                )
            )
        if not isinstance(refs, list) or not refs:
            issues.append(
                FidelityIssue(
                    "CONTENT_RELATION_UNSUPPORTED",
                    f"Content relation {index} must cite source_refs.",
                )
            )
    return issues


def audit_semantic_strength(output: str, evidence: str) -> list[FidelityIssue]:
    """Return legacy lexical review findings without business-object taxonomies."""

    issues: list[FidelityIssue] = []
    for term in HIGH_RISK_TERMS:
        if term in output and term not in evidence:
            issues.append(
                FidelityIssue(
                    "MODALITY_STRENGTH_UPGRADED",
                    "Core meaning introduces a possible unsupported necessity, "
                    f"certainty, or exclusivity marker: {term}",
                )
            )
    for term in PROMOTED_RELATION_TERMS:
        if term in output and term not in evidence:
            issues.append(
                FidelityIssue(
                    "RELATION_STRENGTH_UPGRADED",
                    f"Core meaning introduces a possible unsupported relationship marker: {term}",
                )
            )
    issues.extend(audit_composition_relations(output, evidence))
    return issues


def _semantic_units(text: str) -> tuple[str, ...]:
    return tuple(
        unit.strip()
        for unit in re.split(r"[。！？；;\n]+", str(text or ""))
        if unit.strip()
    )


def _composition_marker_present(unit: str) -> bool:
    if _AS_MODULE_RE.search(unit):
        return True
    for marker in COMPOSITION_RELATION_MARKERS:
        candidate = unit.replace("集成模块", "") if marker == "集成" else unit
        if marker in candidate:
            return True
    return False


def composition_relation_units(text: str) -> tuple[str, ...]:
    """Return structural units that explicitly assert composition."""

    return tuple(
        unit
        for unit in _semantic_units(text)
        if _composition_marker_present(unit) and _composition_shingles(unit)
    )


def _composition_shingles(text: str) -> set[str]:
    compact = str(text or "")
    for marker in _COMPOSITION_NOISE:
        compact = compact.replace(marker, "")
    compact = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", compact).lower()
    if len(compact) < 2:
        return {compact} if compact else set()
    size = 2
    return {
        compact[index : index + size]
        for index in range(len(compact) - size + 1)
    }


def _composition_unit_supported(
    claim: str,
    evidence_units: tuple[str, ...],
) -> bool:
    claim_tokens = _composition_shingles(claim)
    if not claim_tokens:
        return False
    required_overlap = 1 if len(claim_tokens) == 1 else 2
    return any(
        len(claim_tokens & _composition_shingles(evidence_unit)) >= required_overlap
        for evidence_unit in evidence_units
    )


def audit_composition_relations(output: str, evidence: str) -> list[FidelityIssue]:
    """Review explicit composition claims against cited structural evidence.

    The fallback is intentionally lexical and domain-neutral. New projects should
    rely on typed relation/provenance contracts; this function exists only so
    legacy Outline inputs do not silently invent a parent-child relation.
    """

    claimed_units = composition_relation_units(output)
    if not claimed_units:
        return []
    evidence_units = composition_relation_units(evidence)
    unsupported = tuple(
        unit
        for unit in claimed_units
        if not _composition_unit_supported(unit, evidence_units)
    )
    if not unsupported:
        return []
    return [
        FidelityIssue(
            "COMPOSITION_RELATION_UNSUPPORTED",
            "Composition or membership is not supported by cited evidence in "
            "the same sentence or structural unit: " + "；".join(unsupported),
        )
    ]


def audit_current_output_objects(output: str, evidence: str) -> list[FidelityIssue]:
    """Legacy compatibility stub for removed global output-object heuristics.

    Previous versions encoded a fixed noun list for particular projects and then
    guessed whether those nouns represented current outputs. That cannot be made
    domain-general from two untyped strings. New projects must express output
    status through Foundation typed records and Final Script provenance. Legacy
    callers receive no deterministic finding here; Critic may still review the
    supplied text.
    """

    del output, evidence
    return []


def strong_relation_supported(relation: str, evidence: str) -> bool:
    return any(
        marker in evidence for marker in RELATION_SOURCE_MARKERS.get(relation, ())
    )
