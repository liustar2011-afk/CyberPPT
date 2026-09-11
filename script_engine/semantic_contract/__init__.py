"""Structured semantic-contract primitives for Stage 01."""

from .audit import audit_final_script_semantic_contract
from .authorization import validate_authoring_mode_authorization
from .compatibility import (
    RELATION_ALLOWED_EVIDENCE_ROLES,
    collect_provenance_compatibility_diagnostics,
    validate_provenance_compatibility,
)
from .diagnostics import dedupe_diagnostics, partition_diagnostics
from .foundation_index import FoundationIndex
from .models import (
    PROVENANCE_DERIVATIONS,
    PROVENANCE_RELATIONS,
    FoundationRecord,
    SemanticDiagnostic,
)
from .protected_payload import collect_protected_payload_diagnostics
from .provenance import validate_final_script_provenance
from .provenance_markdown import (
    PROVENANCE_MARKDOWN_HEADING,
    parse_provenance_markdown,
    provenance_records,
    render_provenance_markdown,
)
from .source_structure import validate_source_structure_preservation

__all__ = [
    "FoundationIndex",
    "FoundationRecord",
    "PROVENANCE_DERIVATIONS",
    "PROVENANCE_MARKDOWN_HEADING",
    "PROVENANCE_RELATIONS",
    "RELATION_ALLOWED_EVIDENCE_ROLES",
    "SemanticDiagnostic",
    "audit_final_script_semantic_contract",
    "collect_protected_payload_diagnostics",
    "collect_provenance_compatibility_diagnostics",
    "dedupe_diagnostics",
    "parse_provenance_markdown",
    "partition_diagnostics",
    "provenance_records",
    "render_provenance_markdown",
    "validate_authoring_mode_authorization",
    "validate_final_script_provenance",
    "validate_provenance_compatibility",
    "validate_source_structure_preservation",
]
