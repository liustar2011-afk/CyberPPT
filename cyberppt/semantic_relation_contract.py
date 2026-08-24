"""Shared semantic-relation contract between script semantics and Stage 02 visual design.

A business semantic relation is not a visual topology. This module keeps those
layers separate and provides deterministic relation-shape evidence for Stage 02.
The visual-structure designer still owns the final topology choice.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


CANONICAL_RELATIONS = frozenset({
    "supports",
    "responds_to",
    "corresponds_to",
    "causes",
    "enables",
    "transforms_to",
    "sequence_before",
    "feedback_to",
    "classified_as",
    "composed_of",
    "part_of",
    "layered_as",
    "bounded_by",
    "covers",
    "collaborates_with",
    "provides_to",
    "applies_to",
})

LEGACY_RELATION_ALIASES = {
    "contains": "composed_of",
    "sequence_after": "sequence_before",
    "feedback": "feedback_to",
    "feeds_back": "feedback_to",
    "returns_to": "feedback_to",
    "iterates": "feedback_to",
    "loops_to": "feedback_to",
    "feedback_to": "feedback_to",
}

RELATION_FAMILY = {
    "supports": "support",
    "enables": "support",
    "responds_to": "response",
    "corresponds_to": "correspondence",
    "causes": "causal",
    "transforms_to": "transformation",
    "sequence_before": "sequence",
    "feedback_to": "feedback",
    "classified_as": "taxonomy",
    "composed_of": "composition",
    "part_of": "hierarchy",
    "layered_as": "hierarchy",
    "bounded_by": "boundary",
    "covers": "coverage",
    "collaborates_with": "collaboration",
    "provides_to": "provision",
    "applies_to": "correspondence",
}


@dataclass(frozen=True)
class SemanticRelationProfile:
    relation_names: tuple[str, ...]
    relation_families: tuple[str, ...]
    semantic_qualifiers: tuple[str, ...]
    edge_count: int
    subject_count: int
    object_count: int
    cardinality: str
    shared_target: bool
    chain_like: bool
    independent_selection: bool
    optional_progression: bool
    topology_candidates: tuple[str, ...]
    forbidden_topologies: tuple[str, ...]
    authority: str = "business_semantics_only"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "cyberppt.semantic_relation_profile.v1",
            "authority": self.authority,
            "relation_names": list(self.relation_names),
            "relation_families": list(self.relation_families),
            "semantic_qualifiers": list(self.semantic_qualifiers),
            "edge_count": self.edge_count,
            "subject_count": self.subject_count,
            "object_count": self.object_count,
            "cardinality": self.cardinality,
            "shared_target": self.shared_target,
            "chain_like": self.chain_like,
            "independent_selection": self.independent_selection,
            "optional_progression": self.optional_progression,
            "topology_candidates": list(self.topology_candidates),
            "forbidden_topologies": list(self.forbidden_topologies),
            "topology_authority": "visual_structure_designer",
        }


def normalize_relation_name(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        return ""
    return LEGACY_RELATION_ALIASES.get(name, name)


def relation_names(relationships: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    values = [
        normalize_relation_name(item.get("relation"))
        for item in relationships
        if isinstance(item, Mapping)
    ]
    return tuple(dict.fromkeys(value for value in values if value))


def relation_families(relationships: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    families = [RELATION_FAMILY.get(name, "other") for name in relation_names(relationships)]
    return tuple(dict.fromkeys(families))


def semantic_qualifiers(relationships: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    values: list[str] = []
    for item in relationships:
        if not isinstance(item, Mapping):
            continue
        raw = item.get("semantic_qualifiers")
        if isinstance(raw, (list, tuple)):
            values.extend(str(value).strip() for value in raw if str(value).strip())
    return tuple(dict.fromkeys(values))


def _edges(relationships: Sequence[Mapping[str, object]]) -> tuple[tuple[str, str], ...]:
    edges: list[tuple[str, str]] = []
    for item in relationships:
        if not isinstance(item, Mapping):
            continue
        subject = str(item.get("subject") or "").strip()
        raw_objects = item.get("objects")
        if not isinstance(raw_objects, (list, tuple)):
            raw_objects = [item.get("object")]
        for raw in raw_objects:
            object_ = str(raw or "").strip()
            if subject and object_:
                edges.append((subject, object_))
    return tuple(edges)


def _cardinality(edges: tuple[tuple[str, str], ...]) -> tuple[str, bool, bool]:
    if not edges:
        return "none", False, False
    subjects = tuple(dict.fromkeys(left for left, _ in edges))
    objects = tuple(dict.fromkeys(right for _, right in edges))
    shared_target = len(edges) >= 2 and len(subjects) >= 2 and len(objects) == 1
    one_to_many = len(subjects) == 1 and len(objects) >= 2
    paired = len(edges) >= 2 and len(subjects) == len(objects) == len(edges)
    chain_like = any(right == next_left for _, right in edges for next_left, _ in edges)
    if shared_target:
        value = "many_to_one"
    elif one_to_many:
        value = "one_to_many"
    elif paired:
        value = "paired"
    elif len(edges) == 1:
        value = "one_to_one"
    else:
        value = "many_to_many"
    return value, shared_target, chain_like


def build_semantic_relation_profile(
    relationships: Sequence[Mapping[str, object]],
) -> SemanticRelationProfile:
    names = relation_names(relationships)
    families = relation_families(relationships)
    qualifiers = semantic_qualifiers(relationships)
    edges = _edges(relationships)
    subjects = tuple(dict.fromkeys(left for left, _ in edges))
    objects = tuple(dict.fromkeys(right for _, right in edges))
    cardinality, shared_target, chain_like = _cardinality(edges)
    independent_selection = "independent_selection" in qualifiers
    optional_progression = "optional_progression" in qualifiers

    candidates: list[str] = []
    forbidden: list[str] = []
    family_set = set(families)

    if independent_selection and optional_progression:
        # Dual semantics: modes remain independently selectable while a
        # maturity/deepening path may coexist. A single mandatory flow would
        # erase the independent-selection condition.
        candidates.extend(("parallel_set", "ecosystem_map"))
        forbidden.append("directed_flow")
    elif "feedback" in family_set:
        candidates.append("lifecycle_loop")
    elif "hierarchy" in family_set:
        candidates.append("layered_architecture")
    elif "taxonomy" in family_set:
        candidates.append("parallel_set")
        forbidden.extend(("layered_architecture", "directed_flow"))
    elif "boundary" in family_set:
        candidates.append("governance_boundary")
    elif "causal" in family_set:
        candidates.append("causal_convergence" if shared_target else "directed_flow")
    elif "support" in family_set:
        if shared_target:
            candidates.append("conclusion_anchor")
            forbidden.append("layered_architecture")
        else:
            candidates.extend(("ecosystem_map", "conclusion_anchor"))
    elif family_set & {"response", "correspondence"}:
        candidates.append("ecosystem_map")
        forbidden.append("causal_convergence")
    elif "sequence" in family_set or "transformation" in family_set:
        candidates.append("directed_flow")
    elif "provision" in family_set:
        candidates.append("allocation_flow" if cardinality == "one_to_many" else "directed_flow")
    elif family_set & {"collaboration", "coverage"}:
        candidates.append("ecosystem_map")
    elif "composition" in family_set:
        candidates.append("parallel_set")
    elif edges:
        candidates.append("ecosystem_map")

    return SemanticRelationProfile(
        relation_names=names,
        relation_families=families,
        semantic_qualifiers=qualifiers,
        edge_count=len(edges),
        subject_count=len(subjects),
        object_count=len(objects),
        cardinality=cardinality,
        shared_target=shared_target,
        chain_like=chain_like,
        independent_selection=independent_selection,
        optional_progression=optional_progression,
        topology_candidates=tuple(dict.fromkeys(candidates)),
        forbidden_topologies=tuple(dict.fromkeys(forbidden)),
    )


def expression_form_hint(
    relationships: Sequence[Mapping[str, object]],
    *,
    module_count: int,
    comparison_requested: bool = False,
) -> str:
    """Return a relation-informed reading form without treating relation as layout."""

    profile = build_semantic_relation_profile(relationships)
    families = set(profile.relation_families)
    if profile.independent_selection and profile.optional_progression and 2 <= module_count <= 6:
        return "parallel_classification"
    if "feedback" in families and 3 <= module_count <= 5:
        return "operation_loop"
    if "hierarchy" in families and 3 <= module_count <= 4:
        return "architecture_layers"
    if "sequence" in families and 3 <= module_count <= 5:
        return "flow_3_5"
    if "causal" in families and 3 <= module_count <= 4:
        return "causal_chain"
    if "support" in families and profile.shared_target:
        if module_count == 3:
            return "pyramid_argument"
        if module_count == 4:
            return "framework_4"
    if "response" in families and 2 <= module_count <= 6:
        return "mapping_2_6"
    if "correspondence" in families and profile.cardinality == "paired" and 2 <= module_count <= 6:
        if comparison_requested and module_count == 2:
            return "comparison_2col"
        return "mapping_2_6"
    if "taxonomy" in families or "composition" in families:
        if 2 <= module_count <= 6:
            return "parallel_classification"
    return ""


def legacy_visual_intent_hint(
    relationships: Sequence[Mapping[str, object]],
) -> str:
    """Return a safe legacy ImageGen intent hint; final Stage 02 topology stays separate."""

    profile = build_semantic_relation_profile(relationships)
    families = set(profile.relation_families)
    if profile.independent_selection and profile.optional_progression:
        return "judgment_evidence"
    if "feedback" in families:
        return "closed_loop"
    if "hierarchy" in families:
        return "hierarchy_support"
    if "sequence" in families:
        return "phase"
    if "boundary" in families:
        return "boundary_guardrail"
    if "causal" in families:
        return "causal"
    if families & {"response", "correspondence", "collaboration", "coverage", "provision", "transformation"}:
        return "capability_relationship"
    if families & {"taxonomy", "composition"}:
        return "judgment_evidence"
    if "support" in families:
        return "judgment_evidence" if profile.shared_target else "capability_relationship"
    return ""


__all__ = [
    "CANONICAL_RELATIONS",
    "LEGACY_RELATION_ALIASES",
    "RELATION_FAMILY",
    "SemanticRelationProfile",
    "build_semantic_relation_profile",
    "expression_form_hint",
    "legacy_visual_intent_hint",
    "normalize_relation_name",
    "relation_families",
    "relation_names",
    "semantic_qualifiers",
]
