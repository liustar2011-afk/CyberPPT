"""Resolve verified business relations into layout-neutral semantic topology.

This module answers only "what relationship graph does the page express?".
It never selects a PowerPoint layout, card pattern or image carrier.  Visual
expression selection happens later in :mod:`cyberppt.onscreen_expression` and
the registered visual-structure Skill.
"""
from __future__ import annotations

from collections import defaultdict
import re
from typing import Mapping, Sequence


_PEER_RELATIONS = {"peer_classification", "classified_as", "optional_progression"}
_SUPPORT_RELATIONS = {"evidence_supports", "supports"}
_SEQUENCE_RELATIONS = {"sequence_before", "sequence_after"}
_FEEDBACK_RELATIONS = {"feedback", "feeds_back", "feeds_back_to", "returns_to", "iterates", "loops_to"}
_LAYER_RELATIONS = {"layered_as", "layer_supports"}
_MAPPING_RELATIONS = {"problem_response", "semantic_mapping", "corresponds_to"}
_CONTAINMENT_RELATIONS = {"composed_of", "contains", "part_of"}
_DIRECTED_RELATIONS = {
    "directed_dependency",
    "directed_relation",
    "causes",
    "transforms_to",
    *_SUPPORT_RELATIONS,
    *_SEQUENCE_RELATIONS,
    *_FEEDBACK_RELATIONS,
}
_DIRECTIONAL_VALUES = {
    "subject_to_objects",
    "left_to_right",
    "right_to_left",
    "top_to_bottom",
    "bottom_to_top",
}
_MATRIX_RE = re.compile(r"象限|二维|双维|两维|高低|分群")


def _text(value: object) -> str:
    return str(value or "").strip()


def _names(records: Sequence[Mapping[str, object]]) -> set[str]:
    return {_text(item.get("relation")) for item in records if _text(item.get("relation"))}


def _edges(records: Sequence[Mapping[str, object]]) -> tuple[tuple[str, str, str], ...]:
    edges: list[tuple[str, str, str]] = []
    for item in records:
        subject = _text(item.get("subject"))
        relation = _text(item.get("relation"))
        objects = item.get("objects")
        if not subject or not isinstance(objects, (list, tuple)):
            continue
        for raw in objects:
            object_ = _text(raw)
            if object_ and object_ != subject:
                edges.append((subject, object_, relation))
    return tuple(edges)


def _has_dependency_chain(edges: Sequence[tuple[str, str, str]]) -> bool:
    subjects = {left for left, _, _ in edges}
    return any(right in subjects for _, right, _ in edges)


def _multi_source_targets(edges: Sequence[tuple[str, str, str]]) -> dict[str, set[str]]:
    incoming: dict[str, set[str]] = defaultdict(set)
    for left, right, _ in edges:
        incoming[right].add(left)
    return {target: sources for target, sources in incoming.items() if len(sources) >= 2}


def _authority_rank(value: str) -> int:
    return {"soft": 1, "strong": 2, "hard": 3}.get(value, 1)


def _relevant_authority(records: Sequence[Mapping[str, object]], relation_names: set[str]) -> str:
    levels = [
        _text(item.get("constraint_authority")) or "soft"
        for item in records
        if _text(item.get("relation")) in relation_names
    ]
    return max(levels, key=_authority_rank) if levels else "soft"


def _relevant_confidence(records: Sequence[Mapping[str, object]], relation_names: set[str]) -> float:
    values = [
        float(item.get("confidence") or 0.0)
        for item in records
        if _text(item.get("relation")) in relation_names
    ]
    return round(min(values), 2) if values else 0.0


def _candidate(
    topology: str,
    score: float,
    evidence: Sequence[str],
    authority: str,
) -> dict[str, object]:
    return {
        "topology": topology,
        "score": round(max(0.0, min(score, 0.99)), 2),
        "evidence": list(dict.fromkeys(str(value) for value in evidence if str(value))),
        "constraint_authority": authority,
    }


def _peer_eligibility(
    records: Sequence[Mapping[str, object]],
    names: set[str],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not names:
        reasons.append("no_verified_relation")
    non_peer = names - _PEER_RELATIONS
    if non_peer:
        reasons.append("non_peer_relations:" + ",".join(sorted(non_peer)))
    if any(_text(item.get("direction")) in _DIRECTIONAL_VALUES for item in records):
        reasons.append("explicit_direction_present")
    if names & ({"causes"} | _SEQUENCE_RELATIONS | _FEEDBACK_RELATIONS | _LAYER_RELATIONS | _MAPPING_RELATIONS | _CONTAINMENT_RELATIONS | _SUPPORT_RELATIONS):
        reasons.append("non_peer_semantics_present")
    return not reasons, reasons


def resolve_semantic_topology(
    verified_relationships: Sequence[Mapping[str, object]],
    *,
    module_count: int = 0,
    page_text: str = "",
) -> dict[str, object]:
    """Return ranked semantic topology candidates from verified relations."""

    records = [item for item in verified_relationships if isinstance(item, Mapping)]
    names = _names(records)
    edges = _edges(records)
    candidates: list[dict[str, object]] = []
    peer_allowed, peer_reasons = _peer_eligibility(records, names)

    if names & _FEEDBACK_RELATIONS:
        relation_names = names & _FEEDBACK_RELATIONS
        confidence = _relevant_confidence(records, relation_names)
        candidates.append(_candidate(
            "feedback_loop",
            0.82 + 0.16 * confidence,
            ["feedback_relation", *sorted(relation_names)],
            _relevant_authority(records, relation_names),
        ))

    if "causes" in names:
        confidence = _relevant_confidence(records, {"causes"})
        candidates.append(_candidate(
            "causal_chain",
            0.80 + 0.16 * confidence,
            ["causal_relation", "causes"],
            _relevant_authority(records, {"causes"}),
        ))

    if names & _SEQUENCE_RELATIONS:
        relation_names = names & _SEQUENCE_RELATIONS
        confidence = _relevant_confidence(records, relation_names)
        candidates.append(_candidate(
            "sequence",
            0.78 + 0.16 * confidence,
            ["sequence_relation", *sorted(relation_names)],
            _relevant_authority(records, relation_names),
        ))

    if names & _LAYER_RELATIONS:
        relation_names = names & _LAYER_RELATIONS
        confidence = _relevant_confidence(records, relation_names)
        candidates.append(_candidate(
            "layered_structure",
            0.76 + 0.16 * confidence,
            ["layer_relation", *sorted(relation_names)],
            _relevant_authority(records, relation_names),
        ))

    if "comparison" in names:
        confidence = _relevant_confidence(records, {"comparison"})
        candidates.append(_candidate(
            "comparison",
            0.78 + 0.14 * confidence,
            ["comparison_relation"],
            _relevant_authority(records, {"comparison"}),
        ))

    if names & _MAPPING_RELATIONS:
        relation_names = names & _MAPPING_RELATIONS
        confidence = _relevant_confidence(records, relation_names)
        candidates.append(_candidate(
            "mapping",
            0.76 + 0.14 * confidence,
            ["mapping_relation", *sorted(relation_names)],
            _relevant_authority(records, relation_names),
        ))

    if names & _CONTAINMENT_RELATIONS:
        relation_names = names & _CONTAINMENT_RELATIONS
        confidence = _relevant_confidence(records, relation_names)
        candidates.append(_candidate(
            "containment",
            0.72 + 0.14 * confidence,
            ["containment_relation", *sorted(relation_names)],
            _relevant_authority(records, relation_names),
        ))

    support_edges = [edge for edge in edges if edge[2] in _SUPPORT_RELATIONS]
    convergence_targets = _multi_source_targets(support_edges)
    if convergence_targets:
        confidence = _relevant_confidence(records, names & _SUPPORT_RELATIONS)
        candidates.append(_candidate(
            "support_convergence",
            0.80 + 0.16 * confidence,
            ["multi_source_same_target", *sorted(convergence_targets)],
            _relevant_authority(records, names & _SUPPORT_RELATIONS),
        ))

    directed_names = names & _DIRECTED_RELATIONS
    directed_declared = any(_text(item.get("direction")) in _DIRECTIONAL_VALUES for item in records)
    if (
        _has_dependency_chain(edges)
        or names & {"directed_dependency", "directed_relation"}
        or (directed_declared and directed_names)
    ):
        confidence = _relevant_confidence(records, directed_names or names)
        candidates.append(_candidate(
            "dependency_chain",
            0.72 + 0.16 * confidence + (0.06 if _has_dependency_chain(edges) else 0.0),
            ["directed_dependency", *("graph_chain",) if _has_dependency_chain(edges) else ()],
            _relevant_authority(records, directed_names or names),
        ))

    if peer_allowed:
        confidence = _relevant_confidence(records, names & _PEER_RELATIONS)
        candidates.append(_candidate(
            "peer_set",
            0.76 + 0.16 * confidence,
            ["verified_peer_relations", *sorted(names & _PEER_RELATIONS)],
            _relevant_authority(records, names & _PEER_RELATIONS),
        ))

    if module_count == 4 and _MATRIX_RE.search(page_text):
        candidates.append(_candidate(
            "matrix",
            0.68,
            ["two_axis_surface_signal"],
            "soft",
        ))

    candidates.sort(key=lambda item: (-float(item["score"]), str(item["topology"])))
    if not candidates or float(candidates[0]["score"]) < 0.60:
        primary = "unknown"
        confidence = float(candidates[0]["score"]) if candidates else 0.0
        authority = "soft"
    else:
        primary = str(candidates[0]["topology"])
        confidence = float(candidates[0]["score"])
        authority = str(candidates[0]["constraint_authority"])

    return {
        "schema": "cyberppt.semantic_topology.v1",
        "primary_topology": primary,
        "confidence": round(confidence, 2),
        "constraint_authority": authority,
        "candidates": candidates,
        "eligibility": {
            "peer_set": {
                "allowed": peer_allowed,
                "reasons": peer_reasons,
            }
        },
    }


__all__ = ["resolve_semantic_topology"]
