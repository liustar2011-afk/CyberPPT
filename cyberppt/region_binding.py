"""Bind exact Stage 02 locked text to Region Graph semantic regions."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from cyberppt.region_graph import validate_region_graph


def _text_ids(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    result = tuple(str(item or "").strip() for item in value)
    if any(not item for item in result) or len(result) != len(set(result)):
        raise ValueError(f"{field} must contain unique non-empty text ids")
    return result


def bind_region_graph_text(
    region_graph: Mapping[str, object],
    *,
    evidence_text_ids: Mapping[str, Sequence[str]],
    required_text_ids: Sequence[str],
) -> dict[str, Any]:
    """Attach each exact locked text id to the region owning its evidence unit.

    The function never changes Region Graph topology, role, anchor, weight or
    relations. It only projects the already-audited evidence ownership into
    ``regions[].text_ids``.
    """

    graph = validate_region_graph(region_graph).to_dict()
    required = _text_ids(required_text_ids, field="required_text_ids")
    required_set = set(required)

    region_owners: dict[str, list[str]] = {}
    for region in graph["regions"]:
        for evidence_id in region["semantic_refs"]:
            region_owners.setdefault(evidence_id, []).append(region["id"])

    normalized_evidence: dict[str, tuple[str, ...]] = {}
    all_bound: list[str] = []
    for raw_evidence_id, raw_ids in evidence_text_ids.items():
        evidence_id = str(raw_evidence_id or "").strip()
        if not evidence_id:
            raise ValueError("evidence_text_ids contains an empty evidence id")
        owners = region_owners.get(evidence_id, [])
        if len(owners) != 1:
            raise ValueError(
                f"evidence {evidence_id!r} must belong to exactly one Region Graph region"
            )
        ids = _text_ids(raw_ids, field=f"evidence_text_ids[{evidence_id}]")
        if not ids:
            raise ValueError(f"evidence {evidence_id!r} has no locked text ids")
        normalized_evidence[evidence_id] = ids
        all_bound.extend(ids)

    if len(all_bound) != len(set(all_bound)):
        raise ValueError("locked text ids are bound to more than one evidence unit")
    if set(all_bound) != required_set or len(all_bound) != len(required):
        missing = [item for item in required if item not in set(all_bound)]
        extra = [item for item in all_bound if item not in required_set]
        raise ValueError(
            f"Region Graph text binding must cover exact required text ids: missing={missing}, extra={extra}"
        )

    order = {text_id: index for index, text_id in enumerate(required)}
    for region in graph["regions"]:
        owned = [
            text_id
            for evidence_id in region["semantic_refs"]
            for text_id in normalized_evidence.get(evidence_id, ())
        ]
        region["text_ids"] = sorted(owned, key=order.__getitem__)
        if not region["text_ids"]:
            raise ValueError(f"Region Graph region {region['id']!r} has no locked text ownership")

    return validate_region_graph(graph).to_dict()


def region_text_owner_map(region_graph: Mapping[str, object]) -> dict[str, str]:
    """Return exact ``text_id -> region_id`` ownership from a bound Region Graph."""

    graph = validate_region_graph(region_graph).to_dict()
    owners: dict[str, str] = {}
    for region in graph["regions"]:
        region_id = region["id"]
        raw_ids = region.get("text_ids")
        if not isinstance(raw_ids, (list, tuple)) or not raw_ids:
            raise ValueError(f"Region Graph region {region_id!r} has no text_ids")
        ids = _text_ids(raw_ids, field=f"region[{region_id}].text_ids")
        for text_id in ids:
            if text_id in owners:
                raise ValueError(f"locked text id {text_id!r} belongs to multiple regions")
            owners[text_id] = region_id
    return owners


__all__ = ["bind_region_graph_text", "region_text_owner_map"]
