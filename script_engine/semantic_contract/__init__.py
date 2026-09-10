"""Structured semantic-contract primitives for Stage 01."""

from .audit import audit_final_script_semantic_contract
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
from .provenance import validate_final_script_provenance
from .provenance_markdown import (
    PROVENANCE_MARKDOWN_HEADING,
    parse_provenance_markdown,
    provenance_records,
    render_provenance_markdown,
)

__all__ = [
    "FoundationIndex",
    "FoundationRecord",
    "PROVENANCE_DERIVATIONS",
    "PROVENANCE_MARKDOWN_HEADING",
    "PROVENANCE_RELATIONS",
    "RELATION_ALLOWED_EVIDENCE_ROLES",
    "SemanticDiagnostic",
    "audit_final_script_semantic_contract",
    "collect_provenance_compatibility_diagnostics",
    "dedupe_diagnostics",
    "parse_provenance_markdown",
    "partition_diagnostics",
    "provenance_records",
    "render_provenance_markdown",
    "validate_final_script_provenance",
    "validate_provenance_compatibility",
]
