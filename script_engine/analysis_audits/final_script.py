"""Compatibility facade for deterministic Final Script audit helpers."""
from __future__ import annotations

from .final_authoring import (
    _STATUS_PRESERVATION_MARKERS,
    _STRUCTURAL_METADATA_PATTERNS,
    _status_strength_preserved,
    _onscreen_module_lines,
    _is_lead_like_evidence_item,
    _evidence_first_item_hierarchy_issues,
    _is_readable_proposition,
    _onscreen_expression_warnings,
    _looks_like_structural_metadata,
    _author_execution_issues,
    _authored_bare_label_detail_issues,
    _audit_authored_content_coverage,
    _authored_relationships_issues,
    _slide_text,
)
from .final_lean import (
    _audit_lean_authored_source_consumption,
    _onscreen_surface,
    _audit_lean_onscreen_full_copy_alignment,
    _audit_lean_relationship_visibility,
)
from .final_onscreen import (
    _audit_authored_onscreen_composition,
    _semantic_payload_units,
    _audit_self_reading_density,
    _audit_authored_onscreen_contract,
)
from .final_deck import (
    _source_text_for_refs,
    _normalize_source_chapter_title,
    _whole_deck_authoring_warnings,
)
from .final_orchestrator import audit_final_script


__all__ = [
    "_onscreen_module_lines",
    "_is_lead_like_evidence_item",
    "_evidence_first_item_hierarchy_issues",
    "_is_readable_proposition",
    "_onscreen_expression_warnings",
    "_looks_like_structural_metadata",
    "_author_execution_issues",
    "_authored_bare_label_detail_issues",
    "_audit_authored_content_coverage",
    "_authored_relationships_issues",
    "_audit_lean_authored_source_consumption",
    "_audit_lean_onscreen_full_copy_alignment",
    "_audit_lean_relationship_visibility",
    "_audit_authored_onscreen_composition",
    "_semantic_payload_units",
    "_audit_self_reading_density",
    "_audit_authored_onscreen_contract",
    "_slide_text",
    "_source_text_for_refs",
    "_normalize_source_chapter_title",
    "_whole_deck_authoring_warnings",
    "audit_final_script",
]
