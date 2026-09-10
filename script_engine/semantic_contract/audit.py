"""Single Stage 01 semantic-contract audit entry point."""

from __future__ import annotations

from typing import Any

from .compatibility import collect_provenance_compatibility_diagnostics
from .diagnostics import partition_diagnostics
from .protected_payload import collect_protected_payload_diagnostics
from .provenance import validate_final_script_provenance


def audit_final_script_semantic_contract(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> tuple[list[str], list[str], list[dict[str, object]]]:
    """Run all structured Final Script semantic checks through one entry point."""

    provenance_issues = validate_final_script_provenance(
        final_script, plan, foundation
    )
    diagnostics = [
        *collect_provenance_compatibility_diagnostics(final_script, foundation),
        *collect_protected_payload_diagnostics(final_script, foundation),
    ]
    blockers, review_required, structured = partition_diagnostics(diagnostics)
    return [*provenance_issues, *blockers], review_required, structured
