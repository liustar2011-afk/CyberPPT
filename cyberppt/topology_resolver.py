"""Resolve verified business relations into layout-neutral semantic topology.

The resolver answers only what relationship graph a page expresses. It does
not select a PowerPoint layout, card pattern, scene, or carrier. Expression
selection happens later in :mod:`cyberppt.onscreen_expression`.
"""
from __future__ import annotations

from collections import defaultdict
import re
from typing import Mapping, Sequence


_PEER_RELATIONS = {"peer_classification", "classified_as", "optional_progression"}
_SUPPORT_RELATIONS = {"evidence_supports", "supports"}
_SEQUENCE_RELATIONS = {"sequence_before", "sequence_after"}
_FEEDBACK_RELATIONS = {
    "feedback", "feeds_back", "feeds_back_to", "returns_to", "iterates", "loops_to"
}
_LAYER_RELATIONS = {"layered_as", "layer_supports"}
_MAPPING_RELATIONS = {"problem_response", "semantic_mapping", "corresponds_to"}
_CONTAINMENT_RELATIONS = {"composed_of", "contains", "part_of"}
_DIRECTED_RELATIONS = {
    "directed_dependency", "directed_relation", "causes", "transforms_to",
    *_SUPPORT_RELATIONS, *_SEQUENCE_RELATIONS, *_FEEDBACK_RELATIONS,
}
_CONFIDENCE_LEVELS = {
    "high": 1.0,
    "medium": 0.7,
    "low": 0.4,
}

# Candidate topologies are coarse render-carrier families, not detailed
# Stage2 expressions. Every semantic topology emitted by this resolver must
# map to at least one existing carrier family; detailed expression selection
# remains in ``cyberppt.onscreen_expression``.
CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY = {
    "peer_set": {"parallel_set"},
    "feedback_loop": {"lifecycle_loop"},
    "support_convergence": {"causal_convergence", "conclusion_anchor"},
    "sequence": {"directed_flow"},
    "dependency_chain": {"directed_flow"},
    # A mapping identifies correspondence. It does not imply a temporal
    # sequence; directed_flow remains available only to explicit sequence or
    # verified dependency-chain semantics.
    "mapping": {"parallel_set", "conclusion_anchor"},
    "causal_chain": {"directed_flow", "causal_convergence"},
    "layered_structure": {"layered_architecture"},
    "comparison": {"parallel_set"},
    "containment": {"layered_architecture"},
    "matrix": {"parallel_set"},
}
_DIRECTIONAL_VALUES = {
    "subject_to_objects", "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"
}
_MATRIX_RE = re.compile(r"象限|二维|双维|两维|高低|分群")
_ANTI_FLOW_RE = re.compile(r"保持并列|顺序不代表|不代表实施先后|对应关系|支撑范围|相互独立")


def _text(value: object) -> str:
    return str(value or "").strip()


def _names(records: Sequence[Mapping[str, object]]) -> set[str]:
    return {_text(item.get("relation")) for item in records if _text(item.get("relation"))}


def _edges(records: Sequence[Mapping[str, object]]) -> tuple[tuple[str, str, str], ...]:
    result: list[tuple[str, str, str]] = []
    for item in records:
        subject = _text(item.get("subject"))
        relation = _text(item.get("relation"))
        objects = item.get("objects")
        if not subject or not isinstance(objects, (list, tuple)):
            continue
        for raw in objects:
            object_ = _text(raw)
            if object_ and object_ != subject:
                result.append((subject, object_, relation))
    return tuple(result)


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
    values = [
        _text(item.get("constraint_authority")) or "soft"
        for item in records
        if _text(item.get("relation")) in relation_names
    ]
    return max(values, key=_authority_rank) if values else "soft"


def _confidence_value(value: object) -> float:
    """Normalize numeric and adapter-style confidence values to 0..1."""

    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))

    text = _text(value).lower()
    if text in _CONFIDENCE_LEVELS:
        return _CONFIDENCE_LEVELS[text]
    if not text:
        return 0.0
    try:
        return max(0.0, min(float(text), 1.0))
    except ValueError:
        return 0.0


def _relevant_confidence(records: Sequence[Mapping[str, object]], relation_names: set[str]) -> float:
    values = [
        _confidence_value(item.get("confidence"))
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
    records: Sequence[Mapping[str, object]], names: set[str]
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not names:
        reasons.append("no_verified_relation")
    non_peer = names - _PEER_RELATIONS
    if non_peer:
        reasons.append("non_peer_relations:" + ",".join(sorted(non_peer)))
    if any(_text(item.get("direction")) in _DIRECTIONAL_VALUES for item in records):
        reasons.append("explicit_direction_present")
    if names & (
        {"causes"}
        | _SEQUENCE_RELATIONS
        | _FEEDBACK_RELATIONS
        | _LAYER_RELATIONS
        | _MAPPING_RELATIONS
        | _CONTAINMENT_RELATIONS
        | _SUPPORT_RELATIONS
    ):
        reasons.append("non_peer_semantics_present")
    return not reasons, reasons


def resolve_semantic_topology(
    verified_relationships: Sequence[Mapping[str, object]],
    *,
    module_count: int = 0,
    page_text: str = "",
) -> dict[str, object]:
    """Return ranked topology candidates from verified relations."""

    records = [item for item in verified_relationships if isinstance(item, Mapping)]
    names = _names(records)
    edges = _edges(records)
    candidates: list[dict[str, object]] = []
    peer_allowed, peer_reasons = _peer_eligibility(records, names)

    def add(topology: str, relation_names: set[str], base: float, bonus: float, evidence: list[str]) -> None:
        confidence = _relevant_confidence(records, relation_names)
        candidates.append(_candidate(
            topology,
            base + bonus * confidence,
            evidence,
            _relevant_authority(records, relation_names),
        ))

    feedback = names & _FEEDBACK_RELATIONS
    if feedback:
        add("feedback_loop", feedback, 0.82, 0.16, ["feedback_relation", *sorted(feedback)])

    if "causes" in names:
        add("causal_chain", {"causes"}, 0.80, 0.16, ["causal_relation", "causes"])

    sequence = names & _SEQUENCE_RELATIONS
    if sequence:
        add("sequence", sequence, 0.78, 0.16, ["sequence_relation", *sorted(sequence)])

    layered = names & _LAYER_RELATIONS
    if layered:
        add("layered_structure", layered, 0.76, 0.16, ["layer_relation", *sorted(layered)])

    if "comparison" in names:
        add("comparison", {"comparison"}, 0.78, 0.14, ["comparison_relation"])

    mapping = names & _MAPPING_RELATIONS
    if mapping:
        add("mapping", mapping, 0.76, 0.14, ["mapping_relation", *sorted(mapping)])

    containment = names & _CONTAINMENT_RELATIONS
    if containment:
        add("containment", containment, 0.72, 0.14, ["containment_relation", *sorted(containment)])

    support_edges = [edge for edge in edges if edge[2] in _SUPPORT_RELATIONS]
    convergence_targets = _multi_source_targets(support_edges)
    support = names & _SUPPORT_RELATIONS
    if convergence_targets and support:
        add(
            "support_convergence",
            support,
            0.80,
            0.16,
            ["multi_source_same_target", *sorted(convergence_targets)],
        )

    directed_names = names & _DIRECTED_RELATIONS
    chain = _has_dependency_chain(edges)
    # A verified graph chain may imply a generic dependency carrier, but an
    # explicit sequence relation is stronger semantic evidence and already has
    # its own topology. Do not let an equal-scored generic dependency candidate
    # displace ``sequence`` merely because of lexical tie-breaking.
    if chain and not sequence:
        relation_names = directed_names or names
        confidence = _relevant_confidence(records, relation_names)
        evidence = ["directed_dependency", "graph_chain"]
        candidates.append(_candidate(
            "dependency_chain",
            0.72 + 0.16 * confidence + 0.06,
            evidence,
            _relevant_authority(records, relation_names),
        ))

    # Independent directed/mapping statements retain correspondence semantics
    # and must be rendered as a set or conclusion anchor until a real chain is
    # evidenced.
    if directed_names and not chain and not sequence:
        add(
            "mapping",
            directed_names,
            0.70,
            0.14,
            ["independent_directed_relations", *sorted(directed_names)],
        )

    if peer_allowed:
        peer_names = names & _PEER_RELATIONS
        add("peer_set", peer_names, 0.76, 0.16, ["verified_peer_relations", *sorted(peer_names)])

    if module_count == 4 and _MATRIX_RE.search(page_text):
        candidates.append(_candidate("matrix", 0.68, ["two_axis_surface_signal"], "soft"))

    # Authored anti-flow language is a hard boundary for the render carrier.
    # Preserve the relationship facts while preventing a layout sequence from
    # being presented as implementation order.
    if _ANTI_FLOW_RE.search(page_text):
        had_flow = any(
            str(item.get("topology")) in {"dependency_chain", "sequence"}
            for item in candidates
        )
        candidates = [
            item for item in candidates
            if str(item.get("topology")) not in {"dependency_chain", "sequence"}
        ]
        if had_flow and directed_names:
            add(
                "mapping",
                directed_names,
                0.74,
                0.12,
                ["authored_anti_flow_signal", *sorted(directed_names)],
            )

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
            "peer_set": {"allowed": peer_allowed, "reasons": peer_reasons},
        },
    }


__all__ = ["CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY", "resolve_semantic_topology"]
