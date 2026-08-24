"""Resolve business-semantic relations into layout-neutral reading contracts.

This module sits between Script business semantics and Stage 02 visual topology.
A relation name never selects a visual topology directly. The resolver only
chooses an on-screen reading contract from relation type, cardinality, labels,
and the authored module structure. The visual-structure designer retains
responsibility for the actual topology and composition.
"""
from __future__ import annotations

from typing import Mapping, Sequence


_FEEDBACK_LABELS = ("反馈", "回流", "回到", "回返", "循环", "迭代")
_COMPARISON_LABELS = ("对照", "比较", "差异", "优劣", "高于", "低于")
_MAPPING_LABELS = ("回应", "映射", "对应", "匹配", "适配", "问题")
_LAYER_LABELS = ("分层", "层级", "底座", "承托", "上下")
_CLASSIFICATION_LABELS = ("并列", "分类", "同类", "相互独立")


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


def _cardinality(relationships: Sequence[Mapping[str, object]]) -> tuple[int, int]:
    subjects: set[str] = set()
    objects: set[str] = set()
    for item in relationships:
        if not isinstance(item, Mapping):
            continue
        subject = _text(item.get("subject"))
        if subject:
            subjects.add(subject)
        raw_objects = item.get("objects")
        if isinstance(raw_objects, (list, tuple)):
            objects.update(_text(value) for value in raw_objects if _text(value))
        else:
            object_ = _text(item.get("object"))
            if object_:
                objects.add(object_)
    return len(subjects), len(objects)


def resolve_relation_expression(
    *,
    relationships: Sequence[Mapping[str, object]],
    module_count: int,
) -> tuple[str, tuple[str, ...]] | None:
    """Return ``(expression_form, evidence)`` without selecting visual topology.

    The decision is intentionally conditional. Ambiguous support or mapping
    relations remain neutral rather than being forced into a four-card
    framework, hierarchy, or two-column comparison.
    """

    if not relationships:
        return None

    names = _relation_names(relationships)
    labels = _labels(relationships)
    subject_count, object_count = _cardinality(relationships)
    evidence = tuple(sorted(names))

    if any(token in labels for token in _FEEDBACK_LABELS) or names & {
        "feedback", "feeds_back", "feeds_back_to", "returns_to", "iterates", "loops_to"
    }:
        return "operation_loop", ("semantic:feedback", *evidence)

    if "causes" in names:
        return "causal_chain", ("semantic:causal", *evidence)

    if names & {"sequence_before", "sequence_after"}:
        return "flow_3_5", ("semantic:sequence", *evidence)

    if names & {"layered_as", "part_of", "layer_supports"} or any(token in labels for token in _LAYER_LABELS):
        return "architecture_layers", ("semantic:layered", *evidence)

    if names & {"peer_classification", "classified_as"} or any(token in labels for token in _CLASSIFICATION_LABELS):
        return "parallel_classification_3_6", ("semantic:classification", *evidence)

    if names & {"evidence_supports", "supports"}:
        if subject_count >= 2 and object_count == 1:
            return "support_convergence_3_6", ("semantic:many_to_one_support", *evidence)
        if any(token in labels for token in _LAYER_LABELS):
            return "architecture_layers", ("semantic:layer_support", *evidence)
        return "parallel_classification_3_6", ("semantic:peer_support", *evidence)

    if names & {"problem_response", "semantic_mapping", "corresponds_to"}:
        if "corresponds_to" in names and any(token in labels for token in _COMPARISON_LABELS) and module_count == 2:
            return "comparison_2col", ("semantic:comparison", *evidence)
        return "mapping_2_6", ("semantic:mapping", *evidence)

    if "comparison" in names:
        if module_count == 2:
            return "comparison_2col", ("semantic:comparison", *evidence)
        return "mapping_2_6", ("semantic:multi_item_comparison", *evidence)

    if names & {"composed_of", "contains"}:
        return "parallel_classification_3_6", ("semantic:composition", *evidence)

    # A generic transform is directional but not necessarily a multi-step
    # flow; let surface structure decide unless there are enough modules to
    # make a directed reading contract meaningful.
    if "transforms_to" in names and 3 <= module_count <= 6:
        return "flow_3_5", ("semantic:transformation", *evidence)

    return None
