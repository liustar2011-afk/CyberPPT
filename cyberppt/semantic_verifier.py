"""Verify upstream semantic relationship proposals before visual decisions.

The verifier is deliberately narrower than Stage 01 analysis.  It does not
rewrite the page or invent a new argument.  It checks whether an upstream
relationship proposal is structurally consistent with its own direction,
evidence and neighbouring relation graph, then returns accepted/refined/
rejected/unresolved verdicts with authority-aware constraints.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Mapping, Sequence


_PEER_RELATIONS = {"peer_classification", "classified_as"}
_SUPPORT_RELATIONS = {"evidence_supports", "supports"}
_SEQUENCE_RELATIONS = {"sequence_before", "sequence_after"}
_FEEDBACK_RELATIONS = {"feedback", "feeds_back", "feeds_back_to", "returns_to", "iterates", "loops_to"}
_LAYER_RELATIONS = {"layered_as", "layer_supports"}
_MAPPING_RELATIONS = {"problem_response", "semantic_mapping", "corresponds_to"}
_DIRECTIONAL_RELATIONS = {
    "directed_dependency",
    "directed_relation",
    "causes",
    "transforms_to",
    *_SUPPORT_RELATIONS,
    *_SEQUENCE_RELATIONS,
    *_FEEDBACK_RELATIONS,
}


def _text(value: object) -> str:
    return str(value or "").strip()


def _edges(records: Sequence[Mapping[str, object]]) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for item in records:
        subject = _text(item.get("subject"))
        objects = item.get("objects")
        if not subject or not isinstance(objects, (list, tuple)):
            continue
        for raw in objects:
            object_ = _text(raw)
            if object_ and object_ != subject:
                result.append((subject, object_))
    return tuple(result)


def _has_child_direction_conflict(
    peer: Mapping[str, object],
    directed_edges: Sequence[tuple[str, str]],
) -> bool:
    children = {_text(value) for value in peer.get("objects") or [] if _text(value)}
    if len(children) < 2:
        return False
    return any(left in children and right in children for left, right in directed_edges)


def _constraint_tokens(relation: str) -> tuple[str, ...]:
    if relation in _PEER_RELATIONS:
        return ("preserve_peer_equivalence",)
    if relation in _SEQUENCE_RELATIONS:
        return ("preserve_direction", "preserve_order", "forbid_peer_equivalence")
    if relation == "causes":
        return ("preserve_direction", "preserve_causality", "forbid_peer_equivalence")
    if relation in _FEEDBACK_RELATIONS:
        return ("preserve_direction", "preserve_feedback", "forbid_peer_equivalence")
    if relation in _LAYER_RELATIONS:
        return ("preserve_layering", "forbid_peer_equivalence")
    if relation in _MAPPING_RELATIONS:
        return ("preserve_mapping",)
    if relation == "comparison":
        return ("preserve_comparison",)
    if relation in {"composed_of", "contains", "part_of"}:
        return ("preserve_containment",)
    if relation in _DIRECTIONAL_RELATIONS:
        return ("preserve_direction", "forbid_peer_equivalence")
    return ()


def verify_semantic_proposals(
    proposals: Sequence[Mapping[str, object]],
    *,
    page_text: str = "",
    visual_notes: str = "",
) -> dict[str, object]:
    """Verify normalized proposals and return canonical Stage 02 relations."""

    _ = page_text, visual_notes  # reserved for evidence-aware extensions
    verdicts: list[dict[str, object]] = []

    for proposal in proposals:
        proposed = _text(proposal.get("proposed_relation")) or "semantic_association"
        relation = proposed
        verdict = "accepted"
        codes: list[str] = []
        rationale: list[str] = []
        directional = bool(proposal.get("directional"))

        if proposed in _PEER_RELATIONS and directional:
            verdict = "rejected"
            relation = "directed_relation"
            codes.append("PEER_CONFLICTS_WITH_EXPLICIT_DIRECTION")
            rationale.append("A peer classification cannot simultaneously assert a directed subject-to-object edge.")
        elif proposed == "semantic_association" and directional:
            verdict = "refined"
            relation = "directed_relation"
            codes.append("UNDIRECTED_ASSOCIATION_REFINED_FROM_DIRECTION")
            rationale.append("The relation family was vague, but the declared edge direction must be preserved.")
        elif proposed == "directed_relation" and not directional:
            verdict = "unresolved"
            relation = "semantic_association"
            codes.append("DIRECTED_RELATION_WITHOUT_DIRECTION")
            rationale.append("A directed relation was proposed without a declared direction.")
        elif not proposed:
            verdict = "unresolved"
            relation = "directed_relation" if directional else "semantic_association"
            codes.append("RELATION_TYPE_UNRESOLVED")
            rationale.append("The upstream proposal does not identify a relation family.")

        confidence = float(proposal.get("confidence") or 0.0)
        if verdict in {"refined", "rejected"}:
            confidence = max(0.0, confidence - 0.08)
        elif verdict == "unresolved":
            confidence = min(confidence, 0.55)

        verdicts.append({
            "proposal_id": _text(proposal.get("proposal_id")),
            "subject": _text(proposal.get("subject")),
            "objects": [str(value).strip() for value in proposal.get("objects") or [] if str(value).strip()],
            "proposed_relation": proposed,
            "verified_relation": relation,
            "direction": _text(proposal.get("direction")) or "unspecified",
            "basis": _text(proposal.get("basis")),
            "origin": _text(proposal.get("origin")),
            "authority": _text(proposal.get("authority")),
            "constraint_authority": _text(proposal.get("constraint_authority")) or "soft",
            "confidence": round(confidence, 2),
            "evidence_text": _text(proposal.get("evidence_text")),
            "relation_label": _text(proposal.get("relation_label")),
            "condition": _text(proposal.get("condition")),
            "modality": _text(proposal.get("modality")),
            "source_refs": list(proposal.get("source_refs") or []),
            "authority_ref": _text(proposal.get("authority_ref")),
            "verdict": verdict,
            "conflict_codes": codes,
            "rationale": rationale,
        })

    # A declared peer set is invalid when the same children also carry an
    # explicit directed relation.  This catches the exact class of failure
    # where A→B→C is later flattened into a peer taxonomy.
    provisional = [
        {
            "subject": item["subject"],
            "objects": item["objects"],
            "relation": item["verified_relation"],
        }
        for item in verdicts
        if item["verdict"] != "rejected"
    ]
    directed_edges = []
    for item in verdicts:
        if item["verdict"] == "rejected":
            continue
        relation = str(item["verified_relation"])
        direction = str(item["direction"])
        if relation in _DIRECTIONAL_RELATIONS or direction in {
            "subject_to_objects", "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"
        }:
            for object_ in item["objects"]:
                directed_edges.append((str(item["subject"]), str(object_)))

    for item in verdicts:
        if item["verified_relation"] not in _PEER_RELATIONS:
            continue
        if _has_child_direction_conflict(item, directed_edges):
            item["verdict"] = "rejected"
            item["conflict_codes"] = list(dict.fromkeys([
                *item["conflict_codes"],
                "PEER_CONFLICTS_WITH_CHILD_DIRECTION_CHAIN",
            ]))
            item["rationale"] = [
                *item["rationale"],
                "Children declared as peers also participate in a directed chain; the peer claim is discarded.",
            ]

    verified: list[dict[str, object]] = []
    for item in verdicts:
        if item["verdict"] == "rejected":
            # A rejected peer-with-direction record was already refined to a
            # directed relation above and remains useful; pure conflicting
            # peer taxonomies are omitted rather than propagated.
            if item["verified_relation"] in _PEER_RELATIONS:
                continue
        verified.append({
            "subject": item["subject"],
            "relation": item["verified_relation"],
            "objects": list(item["objects"]),
            "direction": item["direction"],
            "condition": item["condition"],
            "modality": item["modality"],
            "basis": item["basis"],
            "origin": item["origin"],
            "authority": item["authority"],
            "constraint_authority": item["constraint_authority"],
            "confidence": item["confidence"],
            "relation_label": item["relation_label"],
            "evidence_text": item["evidence_text"],
            "source_refs": list(item["source_refs"]),
            "authority_ref": item["authority_ref"],
            "proposal_id": item["proposal_id"],
            "proposal_verdict": item["verdict"],
            "proposed_relation": item["proposed_relation"],
        })

    hard_constraints: list[str] = []
    strong_constraints: list[str] = []
    soft_constraints: list[str] = []
    for relation in verified:
        tokens = _constraint_tokens(str(relation.get("relation") or ""))
        authority = str(relation.get("constraint_authority") or "soft")
        target = hard_constraints if authority == "hard" else strong_constraints if authority == "strong" else soft_constraints
        for token in tokens:
            if token not in target:
                target.append(token)

    if not verdicts:
        status = "unresolved"
    elif not verified:
        status = "rejected"
    elif any(item["verdict"] in {"refined", "rejected"} for item in verdicts):
        status = "refined"
    elif any(item["verdict"] == "unresolved" for item in verdicts):
        status = "unresolved"
    else:
        status = "accepted"

    confidences = [float(item.get("confidence") or 0.0) for item in verified]
    overall_confidence = round(min(confidences), 2) if confidences else 0.0
    conflict_codes = list(dict.fromkeys(
        code
        for item in verdicts
        for code in item.get("conflict_codes") or []
    ))

    return {
        "schema": "cyberppt.semantic_verification.v1",
        "status": status,
        "confidence": overall_confidence,
        "verdicts": verdicts,
        "verified_relationships": verified,
        "conflict_codes": conflict_codes,
        "hard_constraints": hard_constraints,
        "strong_constraints": strong_constraints,
        "soft_constraints": soft_constraints,
    }


__all__ = ["verify_semantic_proposals"]
