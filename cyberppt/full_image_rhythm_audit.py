"""Deck-level rhythm checks over image-derived Stage 02 visual signatures."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


RHYTHM_QA_SCHEMA = "cyberppt.full_image_deck_rhythm_qa.v1"


def _hash_distance(left: str, right: str) -> int:
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError as exc:
        raise ValueError("visual signature structure_hash must be hexadecimal") from exc


def _gravity_key(signature: Mapping[str, object]) -> tuple[str, str]:
    gravity = signature.get("gravity")
    gravity = gravity if isinstance(gravity, Mapping) else {}
    return (str(gravity.get("horizontal") or ""), str(gravity.get("vertical") or ""))


def _composition_key(signature: Mapping[str, object]) -> tuple[str, str, str, str]:
    horizontal, vertical = _gravity_key(signature)
    return (
        str(signature.get("skeleton_3x3") or ""),
        horizontal,
        vertical,
        str(signature.get("density") or ""),
    )


def _validate_signatures(signatures: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    if not signatures:
        raise ValueError("deck rhythm QA requires at least one visual signature")
    ordered = sorted(signatures, key=lambda item: int(item.get("page_number") or 0))
    pages = [int(item.get("page_number") or 0) for item in ordered]
    if any(page <= 0 for page in pages) or len(pages) != len(set(pages)):
        raise ValueError("deck rhythm QA requires unique positive page numbers")
    for item in ordered:
        skeleton = str(item.get("skeleton_3x3") or "")
        if len(skeleton) != 9 or any(char not in "01" for char in skeleton):
            raise ValueError("deck rhythm QA requires a nine-bit skeleton_3x3")
        if str(item.get("density") or "") not in {"sparse", "medium", "dense"}:
            raise ValueError("deck rhythm QA requires sparse/medium/dense density")
        if not str(item.get("structure_hash") or ""):
            raise ValueError("deck rhythm QA requires structure_hash")
    return ordered


def audit_deck_visual_rhythm(
    signatures: Sequence[Mapping[str, object]],
    *,
    adjacent_hash_distance: int = 12,
    triple_hash_distance: int = 8,
) -> dict[str, Any]:
    """Detect actual-image rhythm repetition without changing accepted pages."""

    ordered = _validate_signatures(signatures)
    findings: list[dict[str, Any]] = []

    for left, right in zip(ordered, ordered[1:]):
        if (
            _composition_key(left) == _composition_key(right)
            and _hash_distance(str(left["structure_hash"]), str(right["structure_hash"])) <= adjacent_hash_distance
        ):
            findings.append({
                "code": "ADJACENT_COMPOSITION_REPEAT",
                "severity": "warning",
                "pages": [int(left["page_number"]), int(right["page_number"])],
                "message": "Adjacent full images have near-identical composition skeleton, gravity and density.",
            })

    for first, second, third in zip(ordered, ordered[1:], ordered[2:]):
        same_composition = _composition_key(first) == _composition_key(second) == _composition_key(third)
        same_medium = str(first.get("visual_medium") or "") == str(second.get("visual_medium") or "") == str(third.get("visual_medium") or "")
        near_hash = (
            _hash_distance(str(first["structure_hash"]), str(second["structure_hash"])) <= triple_hash_distance
            and _hash_distance(str(second["structure_hash"]), str(third["structure_hash"])) <= triple_hash_distance
        )
        if same_composition and same_medium and near_hash:
            findings.append({
                "code": "TRIPLE_RHYTHM_REPEAT",
                "severity": "block",
                "pages": [int(first["page_number"]), int(second["page_number"]), int(third["page_number"])],
                "message": "Three consecutive full images repeat the same composition, gravity, density and visual medium.",
            })

    for start in range(0, max(0, len(ordered) - 3)):
        run = ordered[start:start + 4]
        if len(run) == 4 and len({str(item.get("density")) for item in run}) == 1:
            findings.append({
                "code": "DENSITY_FLATLINE",
                "severity": "warning",
                "pages": [int(item["page_number"]) for item in run],
                "message": "Four consecutive full images use the same visual density level.",
            })
        media = {str(item.get("visual_medium") or "unspecified") for item in run}
        if len(run) == 4 and len(media) == 1 and "unspecified" not in media:
            findings.append({
                "code": "MEDIUM_STREAK",
                "severity": "warning",
                "pages": [int(item["page_number"]) for item in run],
                "message": "Four consecutive full images use the same audited visual medium.",
            })

    if len(ordered) >= 6:
        media_counts = Counter(str(item.get("visual_medium") or "unspecified") for item in ordered)
        medium, count = media_counts.most_common(1)[0]
        if medium != "unspecified" and count / len(ordered) >= 0.75:
            findings.append({
                "code": "MEDIUM_DOMINANCE",
                "severity": "warning",
                "pages": [int(item["page_number"]) for item in ordered if str(item.get("visual_medium")) == medium],
                "message": f"Visual medium {medium!r} dominates at least 75% of the reviewed deck.",
            })

    blockers = [item for item in findings if item["severity"] == "block"]
    warnings = [item for item in findings if item["severity"] == "warning"]
    status = "blocked" if blockers else ("passed_with_warnings" if warnings else "passed")
    return {
        "schema": RHYTHM_QA_SCHEMA,
        "status": status,
        "page_count": len(ordered),
        "findings": findings,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "review_basis": "actual_full_image_edge_activity_plus_audited_visual_medium",
    }


__all__ = ["RHYTHM_QA_SCHEMA", "audit_deck_visual_rhythm"]
