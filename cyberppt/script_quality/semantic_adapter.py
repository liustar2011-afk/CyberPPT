"""Mechanical adapter from legacy Script Quality artifacts to Stage 01 semantics.

Phase 4 keeps :mod:`cyberppt.script_quality` readable for historical Markdown /
Outline projects while moving semantic authority to :mod:`script_engine`.
This module is deliberately a projection layer, not a third semantic engine:

- it copies explicit IDs, source boundaries and typed source fields;
- it never infers actor/status/relation/visibility from authored prose;
- it emits Final Script 1.0 because legacy pages have no module provenance;
- it projects only explicitly stored relationship edges, never Stage 02 derived
  visual relationships.

The public legacy audit is not routed through this adapter yet. Keeping the
projection side-effect free lets Phase 4 validate equivalence before changing a
production entry point.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import ScriptDocument, ScriptPage


_FOUNDATION_PASSTHROUGH_FIELDS = (
    "statement",
    "claim",
    "definition",
    "term",
    "context",
    "strength",
    "status",
    "semantic_status",
    "argument_duty",
    "argument_role",
    "claim_role",
    "claim_origin",
    "actors",
    "actor",
    "conditions",
    "condition",
    "entity_refs",
    "number_refs",
    "visibility",
    "protected_literals",
    "formal_document_name",
    "document_name",
    "instrument_name",
    "semantic_units",
    "source_refs",
    "source_unit_refs",
    "source_unit_ref",
    "coverage_anchors",
)


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _merged_refs(*values: object) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for value in values:
        for ref in _strings(value):
            if ref in seen:
                continue
            seen.add(ref)
            refs.append(ref)
    return refs


def _outline_pages(outline: dict[str, object]) -> list[dict[str, object]]:
    value = outline.get("pages")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _truth_records(source_truth: dict[str, object]) -> list[dict[str, object]]:
    value = source_truth.get("records")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _project_foundation_record(record: dict[str, object]) -> dict[str, object] | None:
    record_id = str(record.get("id") or "").strip()
    if not record_id:
        return None
    projected: dict[str, object] = {"id": record_id}
    for field in _FOUNDATION_PASSTHROUGH_FIELDS:
        if field in record:
            projected[field] = deepcopy(record[field])
    if not any(
        str(projected.get(field) or "").strip()
        for field in ("statement", "claim", "definition", "term", "context")
    ):
        label = str(record.get("label") or record.get("name") or "").strip()
        if label:
            projected["statement"] = label
    return projected


def project_source_truth_to_foundation(
    source_truth: dict[str, object],
    *,
    outline: dict[str, object] | None = None,
) -> dict[str, object]:
    """Project explicit legacy source records into a minimal Foundation payload."""

    facts = [
        projected
        for record in _truth_records(source_truth)
        if (projected := _project_foundation_record(record)) is not None
    ]
    foundation: dict[str, object] = {
        "sources": deepcopy(source_truth.get("sources") or []),
        "source_structure": deepcopy(source_truth.get("source_structure") or []),
        "facts": facts,
        "concepts": deepcopy(source_truth.get("concepts") or []),
        "entities": deepcopy(source_truth.get("entities") or []),
        "relations": deepcopy(source_truth.get("relations") or []),
        "arguments": deepcopy(source_truth.get("arguments") or []),
        "constraints": deepcopy(source_truth.get("constraints") or []),
        "numbers": deepcopy(source_truth.get("numbers") or []),
    }
    policy = str(source_truth.get("source_consumption_policy") or "").strip()
    if not policy and isinstance(outline, dict):
        policy = str(outline.get("source_consumption_policy") or "").strip()
    if policy == "required":
        foundation["source_consumption_policy"] = "required"
    return foundation


def _project_plan_page(page: dict[str, object]) -> dict[str, object] | None:
    page_id = str(page.get("page_id") or page.get("id") or "").strip()
    if not page_id:
        return None
    projected: dict[str, object] = {
        "id": page_id,
        "page_role": str(page.get("page_type") or page.get("page_role") or "content"),
        "source_refs": _merged_refs(page.get("source_refs"), page.get("boundary_refs")),
    }
    for field in ("primary_relation", "secondary_relations"):
        if field in page:
            projected[field] = deepcopy(page[field])
    return projected


def project_outline_to_deck_plan(outline: dict[str, object]) -> dict[str, object]:
    """Project only the PLAN fields consumed by the semantic-contract adapter."""

    pages = [
        projected
        for page in _outline_pages(outline)
        if (projected := _project_plan_page(page)) is not None
    ]
    plan: dict[str, object] = {
        "authoring_mode": str(outline.get("authoring_mode") or "faithful"),
        "pages": pages,
    }
    audience_scope = str(outline.get("audience_scope") or "").strip()
    if audience_scope:
        plan["audience_scope"] = audience_scope
    source_structure_mode = str(outline.get("source_structure_mode") or "").strip()
    if source_structure_mode:
        plan["source_structure_mode"] = source_structure_mode
    chapters = outline.get("chapters")
    if isinstance(chapters, list):
        plan["chapters"] = deepcopy(chapters)
    return plan


def _explicit_relationships(page: ScriptPage) -> list[dict[str, object]]:
    receipt = page.contract_receipt if isinstance(page.contract_receipt, dict) else {}
    relations = receipt.get("content_relations")
    if not isinstance(relations, list):
        return []
    return [deepcopy(item) for item in relations if isinstance(item, dict)]


def _project_onscreen(page: ScriptPage) -> list[dict[str, object]]:
    text = str(page.onscreen_text or "").strip()
    judgment = str(page.onscreen_judgment or "").strip()
    if not text and not judgment:
        return []
    module: dict[str, object] = {
        "heading": judgment or str(page.title or "内容").strip() or "内容",
    }
    if text:
        module["text"] = text
    return [module]


def _project_slide(page: ScriptPage) -> dict[str, object]:
    slide: dict[str, object] = {
        "id": page.page_id,
        "page_type": page.page_type,
        "title": page.title or page.heading or page.page_id,
        "source_refs": _merged_refs(page.source_refs, page.boundary_source_refs),
    }
    if page.main_message:
        slide["core_message"] = page.main_message
    if page.full_prose:
        slide["full_copy"] = page.full_prose
    onscreen = _project_onscreen(page)
    if onscreen:
        slide["onscreen"] = onscreen
    if page.speaker_notes:
        slide["speaker_notes"] = page.speaker_notes
    relationships = _explicit_relationships(page)
    if relationships:
        slide["relationships"] = relationships
    return slide


def project_script_document_to_final_script(
    script: ScriptDocument,
    *,
    outline: dict[str, object] | None = None,
) -> dict[str, object]:
    """Project a legacy ScriptDocument into provenance-less Final Script 1.0."""

    outline = outline if isinstance(outline, dict) else {}
    return {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {
            "authoring_mode": str(outline.get("authoring_mode") or "faithful"),
            "title": str(outline.get("title") or "Legacy Script Quality projection"),
            "communication_goal": str(
                outline.get("communication_goal") or "Legacy semantic compatibility audit"
            ),
        },
        "slides": [_project_slide(page) for page in script.pages],
    }


def project_legacy_semantic_artifacts(
    script: ScriptDocument,
    outline: dict[str, object],
    source_truth: dict[str, object],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Return ``(final_script, deck_plan, foundation)`` without semantic inference."""

    final_script = project_script_document_to_final_script(script, outline=outline)
    plan = project_outline_to_deck_plan(outline)
    foundation = project_source_truth_to_foundation(source_truth, outline=outline)
    return final_script, plan, foundation


def audit_legacy_script_semantics(
    script: ScriptDocument,
    outline: dict[str, object],
    source_truth: dict[str, object],
) -> tuple[list[str], list[str], list[dict[str, object]]]:
    """Run legacy artifacts through the authoritative Stage 01 semantic entry."""

    from script_engine.semantic_contract import audit_final_script_semantic_contract

    final_script, plan, foundation = project_legacy_semantic_artifacts(
        script,
        outline,
        source_truth,
    )
    return audit_final_script_semantic_contract(final_script, plan, foundation)


__all__ = [
    "audit_legacy_script_semantics",
    "project_legacy_semantic_artifacts",
    "project_outline_to_deck_plan",
    "project_script_document_to_final_script",
    "project_source_truth_to_foundation",
]
