"""Build the in-memory Stage 01 working set used by Outline authors."""

from __future__ import annotations

from typing import Any


_NODE_FIELDS = (
    "id", "parent_id", "source_heading_id", "source_heading", "section_thesis",
    "argument_role", "argument_weight", "level", "status", "evidence_refs",
    "actor_refs", "primary_consumer", "subsection_ids", "allowed_merges",
    "claim_origin", "source_gap_ids",
)


def _items(payload: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = payload.get(field)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Keep P0/P1 statements verbatim; P2 is addressed through structured lookup data."""
    priority = str(record.get("priority") or "")
    summary: dict[str, Any] = {
        "id": record.get("id"),
        "priority": priority,
        "source_unit_refs": record.get("source_unit_refs", []),
        "source_locator": record.get("source_locator", {}),
        "status": record.get("status", ""),
        "claim_role": record.get("claim_role", record.get("type", "")),
    }
    if priority in {"P0", "P1"}:
        summary["statement"] = record.get("statement", "")
    else:
        semantic_units = record.get("semantic_units")
        summary["summary"] = semantic_units if isinstance(semantic_units, list) else record.get("statement", "")
    return summary


def build_outline_authoring_projection(
    semantic_argument_model: dict[str, Any], source_truth: dict[str, Any]
) -> dict[str, Any]:
    """Return a de-duplicated, ID-addressable authoring view without writing artifacts."""
    raw_nodes = _items(semantic_argument_model, "section_nodes") + _items(
        semantic_argument_model, "subsection_nodes"
    )
    nodes = [
        {field: node[field] for field in _NODE_FIELDS if field in node}
        for node in raw_nodes
    ]
    records = _items(source_truth, "records")
    records_by_node: dict[str, list[str]] = {}
    summarized_records: dict[str, dict[str, Any]] = {}
    for node in nodes:
        node_id = str(node.get("id") or "")
        evidence_refs = {str(ref) for ref in node.get("evidence_refs", [])}
        matched = [
            str(record.get("id"))
            for record in records
            if node_id in {str(ref) for ref in record.get("semantic_node_ids", [])}
            or evidence_refs.intersection(str(ref) for ref in record.get("source_unit_refs", []))
        ]
        records_by_node[node_id] = matched
        for record in records:
            record_id = str(record.get("id") or "")
            if record_id in matched:
                summarized_records[record_id] = _record_summary(record)
    return {
        "schema": "cyberppt.outline_authoring_projection.v1",
        "authority_lookup": {
            "semantic_understanding": "workbench/stages/00-semantic-understanding/semantic-understanding.md",
            "semantic_argument_model": "workbench/stages/00-semantic-understanding/semantic-argument-model.json",
            "source_truth": "workbench/stages/01-analysis/source-truth.json",
            "lookup_rule": "Use SU/ST IDs in this projection to retrieve complete authority context; do not alter those files.",
        },
        "document_semantics": semantic_argument_model.get(
            "document_semantics", source_truth.get("document_semantics", {})
        ),
        "document_thesis": semantic_argument_model.get("document_thesis", {}),
        "nodes": nodes,
        "relations": _items(semantic_argument_model, "argument_relations"),
        "source_gaps": _items(semantic_argument_model, "source_gaps"),
        "source_truth_records": summarized_records,
        "source_truth_refs_by_node": records_by_node,
    }
