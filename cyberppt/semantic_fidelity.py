"""Source-grounded semantic fidelity checks for Stage 01 page contracts."""

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
# Source Material Foundation keeps a richer, source-native relationship
# vocabulary.  Handoff is a projection boundary and must preserve those
# labels verbatim; accepting them here prevents the downstream audit from
# rewriting or inventing a relationship merely to satisfy its older list.
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

# Composition is a source relationship, not a harmless wording choice.  Keep
# this vocabulary deliberately narrow: ordinary mentions of a course or a
# module, and descriptions of what a course covers, must not become relation
# claims merely because they use those nouns.
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
    "课程",
    "能力",
    "两类",
    "相关",
)

CURRENT_OUTPUT_VERBS = (
    "形成", "产出", "建成", "建设", "推出", "取得", "获得", "完成",
)
CONDITIONAL_OUTPUT_MARKERS = (
    "满足条件后", "条件成熟后", "验证通过后", "完成验证后", "后续", "未来",
    "再研究", "另行研究", "第二阶段", "成熟后", "逐步",
)
RESTRICTED_EVIDENCE_MARKERS = (
    "不建设", "不形成", "不纳入", "不新增", "无需", "不得", "禁止", "尚未",
    "未形成", "后置", "再研究", "后续", "未来", "另行", "第二阶段",
    "验证通过后", "完成验证后", "成熟后",
)
POSITIVE_OUTPUT_MARKERS = (
    "形成", "产出", "目标是", "交付", "建成", "建设", "推出", "完成", "取得",
    "获得", "先做", "销售", "首期安排", "首期主产品",
)
OUTPUT_OBJECT_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("付费试点", ("付费试点", "付费项目")),
    ("实训场景", ("实训场景", "场景")),
    ("课程", ("课程",)),
    ("平台", ("平台", "SaaS")),
    ("产品", ("产品",)),
    ("系统", ("系统",)),
    ("团队", ("团队",)),
)
ACTOR_ROLE_TERMS = (
    "采购主体", "培训对象", "付费主体", "交付主体", "运营主体", "责任主体", "使用对象",
)


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
    claimed_roles = tuple(term for term in ACTOR_ROLE_TERMS if term in output)
    evidenced_roles = tuple(term for term in ACTOR_ROLE_TERMS if term in evidence)
    for role in claimed_roles:
        if role not in evidenced_roles and evidenced_roles:
            issues.append(FidelityIssue(
                "ACTOR_ROLE_SUBSTITUTED",
                f"Core meaning substitutes the cited actor role {', '.join(evidenced_roles)} with unsupported role {role}.",
            ))
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
        if _composition_marker_present(unit)
        and _composition_shingles(unit)
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


def _composition_unit_supported(claim: str, evidence_units: tuple[str, ...]) -> bool:
    claim_tokens = _composition_shingles(claim)
    if not claim_tokens:
        return False
    required_overlap = 1 if len(claim_tokens) == 1 else 2
    return any(
        len(claim_tokens & _composition_shingles(evidence_unit))
        >= required_overlap
        for evidence_unit in evidence_units
    )


def audit_composition_relations(output: str, evidence: str) -> list[FidelityIssue]:
    """Require explicit composition claims to be present in cited evidence.

    A relation is supported only when a cited sentence/structural unit also
    contains an equivalent composition marker and shares a business-object
    phrase with the claim.  This prevents a course list or a bare module noun
    from being promoted into an invented parent-child relationship.
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
            "Composition or membership is not supported by cited evidence in the same sentence or structural unit: "
            + "；".join(unsupported),
        )
    ]


def audit_current_output_objects(output: str, evidence: str) -> list[FidelityIssue]:
    """Audit only high-confidence current-output object claims.

    The check is intentionally narrow: it runs when a statement explicitly
    asserts an output verb and does not itself declare a future/conditional
    state.  An object is supported only by cited evidence that also uses a
    positive output predicate.  Mere mention, prohibition, or future research
    cannot be promoted into a current deliverable.
    """

    output_clauses = tuple(
        clause.strip()
        for clause in re.split(r"[。！？；;\n]+", output)
        if clause.strip()
    )
    claimed = [
        (canonical, aliases)
        for canonical, aliases in OUTPUT_OBJECT_ALIASES
        if any(
            any(alias in clause for alias in aliases)
            and any(verb in clause for verb in CURRENT_OUTPUT_VERBS)
            and not any(marker in clause for marker in CONDITIONAL_OUTPUT_MARKERS)
            and not any(marker in clause for marker in RESTRICTED_EVIDENCE_MARKERS)
            for clause in output_clauses
        )
    ]
    if not claimed:
        return []
    clauses = tuple(
        clause.strip()
        for clause in re.split(r"[。！？；;\n]+", evidence)
        if clause.strip()
    )
    issues: list[FidelityIssue] = []
    for canonical, aliases in claimed:
        mentions = tuple(
            clause for clause in clauses if any(alias in clause for alias in aliases)
        )
        positive = tuple(
            clause
            for clause in mentions
            if any(marker in clause for marker in POSITIVE_OUTPUT_MARKERS)
            and not any(marker in clause for marker in RESTRICTED_EVIDENCE_MARKERS)
        )
        if positive:
            continue
        restricted = tuple(
            clause
            for clause in mentions
            if any(marker in clause for marker in RESTRICTED_EVIDENCE_MARKERS)
        )
        if restricted:
            issues.append(FidelityIssue(
                "ARGUMENT_CHAIN_OUTPUT_POLARITY_CONFLICT",
                f"Current output {canonical} is cited only in negative, future, or conditional evidence.",
            ))
        else:
            issues.append(FidelityIssue(
                "ARGUMENT_CHAIN_OUTPUT_UNSUPPORTED",
                f"Current output {canonical} has no cited fact that positively supports producing it.",
            ))
    return issues


def strong_relation_supported(relation: str, evidence: str) -> bool:
    return any(marker in evidence for marker in RELATION_SOURCE_MARKERS.get(relation, ()))
