"""Stage-specific deterministic analysis audits.

``audit_final_script`` is the public Phase 4 entry and routes through the single
structured semantic contract. The historical implementation remains available at
``final_script_runtime.audit_final_script`` for compatibility-only callers.
"""
from __future__ import annotations

from typing import Any

from .foundation import audit_foundation_analysis
from .deck_plan import audit_deck_plan
from .source_index import validate_source_index_coverage
from ..semantic_contract import audit_final_script_semantic_contract


def audit_final_script(
    final_script: dict[str, Any],
    plan: dict[str, Any],
    foundation: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Run Final Script semantic audit through the single structured entry."""

    issues, warnings, _ = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )
    return issues, warnings


__all__ = [
    "audit_foundation_analysis",
    "audit_deck_plan",
    "audit_final_script",
    "validate_source_index_coverage",
]
