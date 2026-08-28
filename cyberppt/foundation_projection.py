"""Project CyberPPT's existing Source Truth into a CyberPPT-Script foundation.json.

CyberPPT's own source-material understanding (Word/OCR extraction, chapter
structure, semantic argument modeling -> ``source-truth.json``) stays the
authority for UNDERSTAND: it is more mature than script_engine's own
``source_index.py``, which only indexes text a caller has already extracted.
This module is the one-way, mechanical bridge from that authority into the
vendored script_engine's PLAN/AUTHOR pipeline, so nothing downstream needs to
re-derive source structure or facts from prose.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

FOUNDATION_SCHEMA_ID = "https://cyberppt.local/contracts/foundation.schema.json"

_CONSTRAINT_TYPES = {"B"}
_EXPLICIT_ORIGINS = {"source_explicit"}


def _text(value: object) -> str:
    return str(value or "").strip()


def _record_visibility(record: dict[str, Any]) -> str:
    forbidden = record.get("forbidden_page_roles") or []
    if isinstance(forbidden, list) and any("internal" in _text(role) for role in forbidden):
        return "internal_only"
    return "unspecified"


def _record_basis(record: dict[str, Any]) -> str:
    return "explicit" if _text(record.get("claim_origin")) in _EXPLICIT_ORIGINS else "inferred"


def _project_sources(source_truth: dict[str, Any]) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for source in source_truth.get("sources") or []:
        if not isinstance(source, dict):
            continue
        projected.append({
            "id": _text(source.get("id")),
            "title": _text(source.get("file") or source.get("original_source_file")),
            "type": _text(source.get("role") or "primary"),
            "path": _text(source.get("original_source_file") or source.get("file")),
            "visibility": "external_ok",
        })
    return projected


def _project_facts_and_constraints(
    source_truth: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    facts: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    entities: dict[str, dict[str, Any]] = {}
    numbers: list[dict[str, Any]] = []

    for record in source_truth.get("records") or []:
        if not isinstance(record, dict):
            continue
        record_id = _text(record.get("id"))
        statement = _text(record.get("statement"))
        if not record_id or not statement:
            continue
        source_refs = [
            _text(ref) for ref in record.get("source_unit_refs") or [] if _text(ref)
        ]
        visibility = _record_visibility(record)
        item: dict[str, Any] = {
            "id": record_id,
            "statement": statement,
            "source_refs": source_refs,
            "strength": _text(record.get("priority")) or _text(record.get("verification_status")),
            "visibility": visibility,
        }
        for field in (
            "claim_role",
            "status",
            "semantic_status",
            "semantic_argument_role",
            "source_argument_role",
            "argument_duty",
            "normalized_fact_type",
            "normalized_semantic_role",
        ):
            value = _text(record.get(field))
            if value:
                item[field] = value
        for field in (
            "atomic_item_id",
            "claim_origin",
            "semantic_units",
            "coverage_anchors",
            "conditions",
            "source_locator",
            "allowed_page_roles",
            "forbidden_page_roles",
        ):
            if field in record:
                item[field] = deepcopy(record[field])
        if isinstance(record.get("table_context"), dict):
            item["table_context"] = deepcopy(record["table_context"])

        entity_refs: list[str] = []
        for actor in record.get("actors") or []:
            name = _text(actor if isinstance(actor, str) else (actor or {}).get("name"))
            if not name:
                continue
            entity = entities.get(name)
            if entity is None:
                entity = {
                    "id": f"E-{len(entities) + 1:03d}",
                    "name": name,
                    "source_refs": list(source_refs),
                    "fact_refs": [],
                    "visibility": visibility,
                }
                entities[name] = entity
            else:
                entity["source_refs"] = list(
                    dict.fromkeys([*entity.get("source_refs", []), *source_refs])
                )
                if visibility == "internal_only":
                    entity["visibility"] = visibility
            if record_id not in entity["fact_refs"]:
                entity["fact_refs"].append(record_id)
            if entity["id"] not in entity_refs:
                entity_refs.append(entity["id"])

        number_refs: list[str] = []
        for index, numeric in enumerate(record.get("numeric_facts") or []):
            if not isinstance(numeric, dict):
                continue
            number = {
                "id": f"{record_id}-N{index + 1}",
                "value": numeric.get("value"),
                "unit": _text(numeric.get("unit")),
                "context": _text(numeric.get("context")) or statement,
                "source_refs": source_refs,
                "fact_ref": record_id,
                "visibility": visibility,
            }
            numbers.append(number)
            number_refs.append(number["id"])

        if entity_refs:
            item["entity_refs"] = entity_refs
        if number_refs:
            item["number_refs"] = number_refs
        if _text(record.get("type")) in _CONSTRAINT_TYPES:
            constraints.append(item)
        else:
            facts.append(item)

    return facts, constraints, list(entities.values()), numbers


def _project_relations(source_truth: dict[str, Any]) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for record in source_truth.get("records") or []:
        if not isinstance(record, dict):
            continue
        record_id = _text(record.get("id"))
        if not record_id:
            continue
        basis = _record_basis(record)
        source_refs = [
            _text(ref) for ref in record.get("source_unit_refs") or [] if _text(ref)
        ]
        for target in record.get("depends_on") or []:
            target_id = _text(target)
            if not target_id:
                continue
            relations.append({
                "id": f"R-{record_id}-depends_on-{target_id}",
                "from": record_id,
                "to": target_id,
                "relation": "depends_on",
                "basis": basis,
                "confidence": "medium",
                "support": [record_id],
                "source_refs": source_refs,
            })
        for target in record.get("supports") or []:
            target_id = _text(target)
            if not target_id:
                continue
            relations.append({
                "id": f"R-{record_id}-supports-{target_id}",
                "from": record_id,
                "to": target_id,
                "relation": "supports",
                "basis": basis,
                "confidence": "medium",
                "support": [record_id],
                "source_refs": source_refs,
            })
    return relations


def _project_arguments(source_truth: dict[str, Any]) -> list[dict[str, Any]]:
    arguments: list[dict[str, Any]] = []
    for conclusion in source_truth.get("conclusions") or []:
        if not isinstance(conclusion, dict):
            continue
        claim = _text(conclusion.get("statement"))
        if not claim:
            continue
        support = [_text(ref) for ref in conclusion.get("source_refs") or [] if _text(ref)]
        arguments.append({
            "id": _text(conclusion.get("id")) or f"A-{len(arguments) + 1:03d}",
            "claim": claim,
            "support": support,
            "basis": "explicit" if support else "inferred",
            "confidence": "high" if support else "medium",
            "source_refs": support,
        })
    return arguments


def _project_source_structure(source_truth: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in source_truth.get("source_structure") or []
        if isinstance(item, dict)
    ]


def _project_concepts(source_truth: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in source_truth.get("semantic_concepts") or []
        if isinstance(item, dict)
    ]


def _project_semantic_relations(source_truth: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in source_truth.get("semantic_relations") or []
        if isinstance(item, dict)
    ]


def project_source_truth_to_foundation(source_truth: dict[str, Any]) -> dict[str, Any]:
    """Return a foundation.json payload built from an already-validated Source Truth.

    This is a mechanical field projection, not a re-analysis: every fact,
    constraint, relation and argument it emits already exists in
    ``source_truth`` with its own source references. It adds nothing the
    Source Truth did not already establish.
    """

    facts, constraints, entities, numbers = _project_facts_and_constraints(source_truth)
    return {
        "source_consumption_policy": "required",
        "sources": _project_sources(source_truth),
        "source_structure": _project_source_structure(source_truth),
        "facts": facts,
        "concepts": _project_concepts(source_truth),
        "entities": entities,
        "relations": [
            *_project_relations(source_truth),
            *_project_semantic_relations(source_truth),
        ],
        "arguments": _project_arguments(source_truth),
        "constraints": constraints,
        "numbers": numbers,
        "open_questions": [
            _text(item)
            for item in source_truth.get("open_questions") or []
            if _text(item)
        ],
    }
