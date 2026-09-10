"""Single Stage 01 semantic-contract audit entry point."""

from __future__ import annotations

from typing import Any

from .compatibility import collect_provenance_compatibility_diagnostics
from .diagnostics import partition_diagnostics
from .provenance import validate_final_script_provenance


def audit_final_script_semantic_contract(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> tuple[list[str], list[str], list[dict[str, object]]]:
    """Run the structured semantic contract through one Final Script entry point.

    Phase 1 provenance validation remains source-compatible and is folded into
    the blocking result here. Typed Phase 2 diagnostics use the unified
    structured diagnostic model.
    """

    provenance_issues = validate_final_script_provenance(
        final_script, plan, foundation
    )
    compatibility = collect_provenance_compatibility_diagnostics(
        final_script, foundation
    )
    blockers, review_required, structured = partition_diagnostics(compatibility)
    return [*provenance_issues, *blockers], review_required, structured
