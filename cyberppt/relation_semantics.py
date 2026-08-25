"""Resolve business-semantic relations into layout-neutral reading contracts.

This module sits between Script business semantics and Stage 02 visual topology.
A relation name never selects a visual topology directly. The resolver only
chooses an on-screen reading contract from relation type, cardinality, labels,
and the authored module structure. The visual-structure designer retains
responsibility for the actual topology and composition.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Mapping, Sequence


_FEEDBACK_LABELS = ("反馈", "回流", "回到", "回返", "循环", "迭代")
_COMPARISON_LABELS = ("对照", "比较", "差异", "优劣", "高于", "低于")
_LAYER_LABELS = ("分层", "层级", "底座", "承托", "上下")
_CLASSIFICATION_LABELS = ("并列", "分类", "同类", "相互独立")
_SUPPORT_RELATIONS = {"evidence_supports", "supports"}
_GENERIC_DIRECTED_RELATIONS = {
    "directed_dependency",
    "directed_relation",
    "semantic_association",
}


def _text(value: object) -> str:
    return str(value or "").strip()


def _labels(relationships: Sequence[Mapping[str, object]]) -> str:
    return " ".join(
        _text(item.get("relation_label"))
        for item in relationships
        if isinstance(item, Mapping)
    )


def _relation_names(relationships: Sequence[Mapping[str, object]]) -> set[str]:
    return {
        _text(item.get("relation"))
        for item in relationships
        if isinstance(item, Mapping) and _text(item.get("relation"))
    }


def _edges(
    relationships: Sequence[Mapping[str, object]],
) -> tuple[tuple[str, str], ...]:
    edges: list[tuple[str, str]] = []
    for item in relationships:
        if not isinstance(item, Mapping):
            continue
        subject = _text(item.get("subject"))
        if not subject:
            continue
        raw_objects = item.get("objects")
        if isinstance(raw_objects, (list, tuple)):
            objects = [_text(value) for value in raw_objects if _text(value)]
        else:
            object_ = _text(item.get("object"))
            objects = [object_] if object_ else []
        edges.extend((subject, object_) for object_ in objects if subject != object_)
    return tuple(edges)


def _cardinality(relationships: Sequence[Mapping[str, object]]) -> tuple[int, int]:
    edges = _edges(relationships)
    return len({subject for subject, _ in edges}), len({object_ for _, object_ in edges})


def _has_multi_source_convergence(edges: Sequence[tuple[str, str]]) -> bool:
    incoming: dict[str, set[str]] = defaultdict(set)
    for subject, object_ in edges:
        incoming[object_].add(subject)
    return any(len(subjects) >= 2 for subjects in incoming.values())


def _has_dependency_chain(edges: Sequence[tuple[str, str]]) -> bool:
    subjects = {subject for subject, _ in edges}
    return any(object_ in subjects for _, object_ in edges)


def _has_declared_direction(relationships: Sequence[Mapping[str, object]]) -> bool:
    return any(
        _text(item.get("direction"))
        in {"subject_to_objects", "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"}
        for item in relationships
        if isinstance(item, Mapping)
    )


def resolve_relation_expression(
    *,
    relationships: Sequence[Mapping[str, object]],
    module_count: int,
) -> tuple[str, tuple[str, ...]] | None:
    """Return a reading contract without selecting visual topology."""

    if not relationships:
        return None

    names = _relation_names(relationships)
    labels = _labels(relationships)
    subject_count, object_count = _cardinality(relationships)
    edges = _edges(relationships)
    evidence = tuple(sorted(names))

    # Optional progression is semantically peer-selectable first. A later
    # visual design may show a maturity direction, but it must not turn the
    # choices into a mandatory upgrade chain.
    if "optional_progression" in names:
        return "parallel_classification_3_6", (
            "semantic:optional_progression",
            *evidence,
        )

    if any(token in labels for token in _FEEDBACK_LABELS) or names & {
        "feedback",
        "feeds_back",
        "feeds_back_to",
        "returns_to",
        "iterates",
        "loops_to",
    }:
        return "operation_loop", ("semantic:feedback", *evidence)

    if "causes" in names:
        return "causal_chain", ("semantic:causal", *evidence)

    if names & {"sequence_before", "sequence_after"}:
        return "flow_3_5", ("semantic:sequence", *evidence)

    if names & {"layered_as", "part_of", "layer_supports"} or any(
        token in labels for token in _LAYER_LABELS
    ):
        return "architecture_layers", ("semantic:layered", *evidence)

    # Support is directional unless the source explicitly declares peer
    # classification. Preserve its graph shape: many-to-one support converges;
    # chained or one-to-one support remains a directed dependency. It must not
    # silently become a peer taxonomy.
    if names & _SUPPORT_RELATIONS:
        if _has_multi_source_convergence(edges) or (
            subject_count >= 2 and object_count == 1
        ):
            return "support_convergence_3_6", (
                "semantic:many_to_one_support",
                *evidence,
            )
        if _has_dependency_chain(edges) or "directed_dependency" in names:
            return "directed_dependency_2_6", (
                "semantic:directed_dependency",
                *evidence,
            )
        if any(token in labels for token in _LAYER_LABELS):
            return "architecture_layers", ("semantic:layer_support", *evidence)
        if _has_declared_direction(relationships):
            return "directed_dependency_2_6", (
                "semantic:directed_support",
                *evidence,
            )
        return None

    if names & {"peer_classification", "classified_as"} or any(
        token in labels for token in _CLASSIFICATION_LABELS
    ):
        return "parallel_classification_3_6", (
            "semantic:classification",
            *evidence,
        )

    if names & {"problem_response", "semantic_mapping", "corresponds_to"}:
        if (
            "corresponds_to" in names
            and any(token in labels for token in _COMPARISON_LABELS)
            and module_count == 2
        ):
            return "comparison_2col", ("semantic:comparison", *evidence)
        return "mapping_2_6", ("semantic:mapping", *evidence)

    if "comparison" in names:
        if module_count == 2:
            return "comparison_2col", ("semantic:comparison", *evidence)
        return "mapping_2_6", ("semantic:multi_item_comparison", *evidence)

    if names & {"composed_of", "contains"}:
        return "parallel_classification_3_6", (
            "semantic:composition",
            *evidence,
        )

    if "transforms_to" in names and 3 <= module_count <= 6:
        return "flow_3_5", ("semantic:transformation", *evidence)

    # Explicit arrows that could not be typed more narrowly still carry real
    # direction. Use graph shape to retain that information without inventing
    # chronology, hierarchy, or peer equivalence.
    if names & _GENERIC_DIRECTED_RELATIONS and _has_declared_direction(relationships):
        if _has_multi_source_convergence(edges):
            return "support_convergence_3_6", (
                "semantic:directed_convergence",
                *evidence,
            )
        return "directed_dependency_2_6", (
            "semantic:directed_relation",
            *evidence,
        )

    return None
