"""Normalize upstream Stage 01 relationship claims into auditable proposals.

Stage 02 must distinguish facts that are explicit in source/author contracts from
relationships inferred by CyberPPT-Script or by a compatibility adapter.  This
module therefore does not decide whether a relation is true.  It records the
proposal, its evidence and its authority so the semantic verifier can accept,
refine, reject or leave it unresolved.
"""
from __future__ import annotations

import re
from typing import Mapping, Sequence


AUTHORITY_LEVELS = {
    "source_explicit",
    "author_explicit",
    "structured_extract",
    "script_inference",
    "adapter_inference",
}

_AUTHORITY_CONFIDENCE_CAP = {
    "source_explicit": 1.00,
    "author_explicit": 1.00,
    "structured_extract": 0.92,
    "script_inference": 0.82,
    "adapter_inference": 0.65,
}

_DIRECTIONAL_VALUES = {
    "subject_to_objects",
    "left_to_right",
    "right_to_left",
    "top_to_bottom",
    "bottom_to_top",
}


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _objects(item: Mapping[str, object]) -> list[str]:
    raw = item.get("objects")
    if isinstance(raw, (list, tuple)):
        values = [_text(value) for value in raw if _text(value)]
    else:
        value = _text(item.get("object"))
        values = [value] if value else []
    return list(dict.fromkeys(values))


def _confidence(value: object, default: float = 0.72) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    label = _text(value).lower()
    return {
        "high": 0.90,
        "medium": 0.75,
        "low": 0.60,
        "explicit": 0.95,
        "inferred": 0.72,
        "speculative": 0.50,
    }.get(label, default)


def _infer_authority(item: Mapping[str, object], *, origin: str) -> str:
    declared = _text(item.get("authority"))
    if declared in AUTHORITY_LEVELS:
        return declared

    basis = _text(item.get("basis")).lower()
    authority_ref = _text(item.get("authority_ref")).lower()
    source_refs = [str(value).strip() for value in item.get("source_refs") or [] if str(value).strip()]

    if basis in {"source_explicit", "explicit_source"}:
        return "source_explicit"
    if basis in {"author_explicit", "explicit_author"} or "author" in authority_ref:
        return "author_explicit"
    # Legacy Stage 01 contracts frequently used basis=explicit for relations
    # extracted from an authoritative source-backed outline.
    if basis == "explicit" and source_refs:
        return "source_explicit"
    if any(token in basis for token in ("structured", "outline", "schema_extract")):
        return "structured_extract"
    if "derived_from_script_visual_structure" in basis or "final-script" in authority_ref:
        return "script_inference"
    if origin == "adapter" or "adapter" in basis:
        return "adapter_inference"
    return "script_inference"


def _constraint_authority(authority: str, confidence: float) -> str:
    if authority in {"source_explicit", "author_explicit"} and confidence >= 0.90:
        return "hard"
    if authority == "structured_extract" and confidence >= 0.80:
        return "strong"
    return "soft"


def normalize_semantic_proposals(
    relationships: Sequence[Mapping[str, object]],
    *,
    default_source_refs: Sequence[str] = (),
    origin: str = "stage01",
) -> tuple[dict[str, object], ...]:
    """Return normalized relation proposals without asserting they are correct."""

    proposals: list[dict[str, object]] = []
    for index, item in enumerate(relationships, start=1):
        if not isinstance(item, Mapping):
            continue
        subject = _text(item.get("subject"))
        objects = _objects(item)
        if not subject or not objects:
            continue
        proposed_relation = _text(item.get("relation")) or "semantic_association"
        direction = _text(item.get("direction")) or "unspecified"
        authority = _infer_authority(item, origin=origin)
        confidence = min(
            _confidence(item.get("confidence")),
            _AUTHORITY_CONFIDENCE_CAP[authority],
        )
        source_refs = list(dict.fromkeys(
            [str(value).strip() for value in item.get("source_refs") or [] if str(value).strip()]
            or [str(value).strip() for value in default_source_refs if str(value).strip()]
        ))
        evidence_text = _text(item.get("evidence_text") or item.get("relation_label"))
        proposal_origin = _text(item.get("origin")) or origin
        proposals.append({
            "proposal_id": f"R{index:02d}",
            "subject": subject,
            "objects": objects,
            "proposed_relation": proposed_relation,
            "direction": direction,
            "directional": direction in _DIRECTIONAL_VALUES,
            "basis": _text(item.get("basis")),
            "origin": proposal_origin,
            "authority": authority,
            "constraint_authority": _constraint_authority(authority, confidence),
            "confidence": round(confidence, 2),
            "evidence_text": evidence_text,
            "relation_label": _text(item.get("relation_label")),
            "condition": _text(item.get("condition")),
            "modality": _text(item.get("modality")),
            "source_refs": source_refs,
            "authority_ref": _text(item.get("authority_ref")),
        })
    return tuple(proposals)


__all__ = [
    "AUTHORITY_LEVELS",
    "normalize_semantic_proposals",
]
