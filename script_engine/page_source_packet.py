"""Derived per-page exact-source context for Stage 01 AUTHOR.

A Page Source Packet is runtime context, not a fourth semantic authority. It
resolves a Deck Plan page's Foundation refs back to exact ``source-index.v2``
units so AUTHOR does not draft precise faithful copy from long-mode previews.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


_CITABLE_KEYS = (
    "facts",
    "concepts",
    "entities",
    "relations",
    "arguments",
    "constraints",
    "numbers",
)
_TEXT_KEYS = ("statement", "claim", "definition", "relation", "term", "context", "value")


def _text(value: object) -> str:
    return str(value or "").strip()


def _foundation_items(
    foundation: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    items: dict[str, dict[str, Any]] = {}
    kinds: dict[str, str] = {}
    for key in _CITABLE_KEYS:
        kind = key[:-1] if key.endswith("s") else key
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            item_id = _text(item.get("id"))
            if not item_id:
                continue
            items[item_id] = item
            kinds[item_id] = kind
    return items, kinds


def _source_unit_refs(item: dict[str, Any]) -> list[str]:
    """Return stable source-unit refs in author order without requiring a prefix."""

    refs: list[str] = []

    def add(value: object) -> None:
        ref = _text(value)
        if ref and ref not in refs:
            refs.append(ref)

    for value in item.get("source_unit_refs") or []:
        add(value)
    for value in item.get("source_refs") or []:
        add(value)
    for semantic_unit in item.get("semantic_units") or []:
        if not isinstance(semantic_unit, dict):
            continue
        add(semantic_unit.get("source_unit_ref"))
        for value in semantic_unit.get("source_unit_refs") or []:
            add(value)
    return refs


def _item_surface(item: dict[str, Any]) -> str:
    for key in _TEXT_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if key == "value" and value is not None and not isinstance(value, (dict, list)):
            return str(value).strip()
    return ""


def _protected_payload(
    item: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    numbers: list[dict[str, Any]] = []
    for number_ref in item.get("number_refs") or []:
        number = items.get(_text(number_ref))
        if not isinstance(number, dict):
            continue
        numbers.append(
            {
                "id": _text(number.get("id")),
                "value": deepcopy(number.get("value")),
                "unit": _text(number.get("unit")),
                "context": _text(number.get("context")),
            }
        )

    actors: list[dict[str, str]] = []
    for entity_ref in item.get("entity_refs") or []:
        entity = items.get(_text(entity_ref))
        if not isinstance(entity, dict):
            continue
        name = _text(entity.get("name"))
        if name:
            actors.append({"id": _text(entity.get("id")), "name": name})

    return {
        "actors": actors,
        "numbers": numbers,
        "conditions": [
            _text(value) for value in item.get("conditions") or [] if _text(value)
        ],
        "status": _text(item.get("status")),
        "strength": _text(item.get("strength") or item.get("priority")),
        "claim_origin": _text(item.get("claim_origin") or item.get("basis")),
        "visibility": _text(item.get("visibility")),
    }


def build_page_source_packet(
    page: dict[str, Any],
    foundation: dict[str, Any],
    source_index: dict[str, Any],
) -> dict[str, Any]:
    """Resolve one Deck Plan page to exact source units and protected payload.

    The returned packet is intentionally derived and disposable. Its ``authority``
    field documents that Foundation, Deck Plan and source files remain authoritative.
    Unknown page refs are blocking issues; missing exact source-unit bindings are
    warnings because strict/legacy or compatibility Foundations may use another
    source-reference namespace.
    """

    items, kinds = _foundation_items(foundation)
    units = {
        _text(item.get("unit_id")): item
        for item in source_index.get("units") or []
        if isinstance(item, dict) and _text(item.get("unit_id"))
    }
    page_refs = [
        _text(value) for value in page.get("source_refs") or [] if _text(value)
    ]

    issues: list[str] = []
    warnings: list[str] = []
    evidence: list[dict[str, Any]] = []

    for ref in page_refs:
        item = items.get(ref)
        if item is None:
            unit = units.get(ref)
            if unit is not None:
                evidence.append(
                    {
                        "foundation_ref": None,
                        "kind": "source_unit",
                        "statement": _text(unit.get("text")),
                        "source_unit_refs": [ref],
                        "exact_source_units": [
                            {
                                "unit_id": ref,
                                "source_id": _text(unit.get("source_id")),
                                "kind": _text(unit.get("kind")),
                                "heading_id": _text(unit.get("heading_id")),
                                "text": _text(unit.get("text")),
                                "locator": deepcopy(unit.get("locator") or {}),
                            }
                        ],
                        "protected": {
                            "actors": [],
                            "numbers": [],
                            "conditions": [],
                            "status": "",
                            "strength": "",
                            "claim_origin": "",
                            "visibility": "",
                        },
                    }
                )
                continue
            issues.append(f"PAGE_SOURCE_REF_UNKNOWN: page source ref '{ref}' is not in Foundation or source index")
            continue

        source_refs = _source_unit_refs(item)
        exact_units: list[dict[str, Any]] = []
        unresolved: list[str] = []
        for source_ref in source_refs:
            unit = units.get(source_ref)
            if unit is None:
                unresolved.append(source_ref)
                continue
            exact_units.append(
                {
                    "unit_id": source_ref,
                    "source_id": _text(unit.get("source_id")),
                    "kind": _text(unit.get("kind")),
                    "heading_id": _text(unit.get("heading_id")),
                    "text": _text(unit.get("text")),
                    "locator": deepcopy(unit.get("locator") or {}),
                }
            )

        if source_refs and not exact_units:
            warnings.append(
                f"PAGE_SOURCE_EXACT_TEXT_UNRESOLVED: {ref} has source refs {source_refs} but none resolve in source-index.v2"
            )
        elif unresolved:
            warnings.append(
                f"PAGE_SOURCE_EXACT_TEXT_PARTIAL: {ref} has unresolved source refs {unresolved}"
            )
        elif not source_refs:
            warnings.append(
                f"PAGE_SOURCE_UNIT_BINDING_MISSING: {ref} has no source-unit refs; AUTHOR can use Foundation text but exact source text is unavailable"
            )

        evidence.append(
            {
                "foundation_ref": ref,
                "kind": kinds.get(ref, "item"),
                "statement": _item_surface(item),
                "source_unit_refs": source_refs,
                "exact_source_units": exact_units,
                "semantic_units": deepcopy(item.get("semantic_units") or []),
                "protected": _protected_payload(item, items),
            }
        )

    return {
        "schema": "cyberppt.page_source_packet.v1",
        "authority": "derived_runtime_context",
        "authoritative_chain": ["source", "foundation", "deck_plan", "final_script"],
        "page_id": _text(page.get("id")),
        "page_title": _text(page.get("title")),
        # PLAN owns the mission. This runtime copy is not a new content authority.
        "page_mission": _text(page.get("logic")),
        "authoring_mode": _text(page.get("authoring_mode")) or "faithful",
        "page_source_refs": page_refs,
        "evidence": evidence,
        "status": "passed" if not issues else "rewrite_required",
        "issues": issues,
        "warnings": warnings,
    }


__all__ = ["build_page_source_packet"]
