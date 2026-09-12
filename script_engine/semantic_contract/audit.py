"""Single Stage 01 semantic-contract audit entry point."""

from __future__ import annotations

from typing import Any

from .authorization import validate_authoring_mode_authorization
from .compatibility import collect_provenance_compatibility_diagnostics
from .content_route import collect_content_route_diagnostics
from .delivery_cleanliness import collect_delivery_cleanliness_diagnostics
from .delivery_readiness import collect_delivery_readiness_diagnostics
from .diagnostics import partition_diagnostics
from .onscreen_composition import collect_onscreen_composition_diagnostics
from .onscreen_contract import collect_onscreen_contract_diagnostics
from .protected_payload import collect_protected_payload_diagnostics
from .provenance import validate_final_script_provenance
from .relationships import validate_relationship_shape
from .source_boundary import collect_source_boundary_diagnostics
from .source_scope import validate_source_scope
from .source_structure import validate_source_structure_preservation
from .visibility import collect_visibility_diagnostics
from .voice_policy import collect_voice_policy_diagnostics


def _legacy_review_warning(issue: str) -> str:
    """Render residual compatibility findings without granting blocking authority."""

    return f"[LEGACY_COMPATIBILITY_REVIEW_REQUIRED] {issue}"


def _stage1_owns_onscreen(final_script: dict[str, Any]) -> bool:
    """Return whether the Final Script version still authors presentation copy."""

    return str(final_script.get("version") or "1.0").strip() in {"1.0", "1.1"}


def audit_final_script_semantic_contract(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> tuple[list[str], list[str], list[dict[str, object]]]:
    """Run the authoritative Final Script semantic audit through one entry point.

    Structured authorization, source scope, relationship shape/topology,
    source-structure preservation, provenance, typed compatibility, protected
    payload, objective source boundaries, explicit PLAN content-route contracts,
    delivery cleanliness and voice policy, and explicit visibility are the
    blocking semantic authority.

    Final Script 1.0/1.1 additionally own authored onscreen composition, PLAN
    onscreen contracts and Stage 01 delivery-readiness modules. Final Script 1.2
    moves presentation-copy derivation and those readiness decisions to Stage 02,
    so the Stage 01 onscreen validators are not applicable there.

    During Phase 4 the historical Final Script auditor remains attached only as a
    compatibility review adapter. Any residual ``legacy_issues`` are surfaced as
    warnings so old code cannot silently regain formal blocking authority. Raw
    legacy callers remain unchanged because they call the legacy orchestrator
    directly with ``compatibility_mode=False``.
    """

    authorization_issues = validate_authoring_mode_authorization(final_script, plan)
    source_scope_issues = validate_source_scope(final_script, plan, foundation)
    relationship_issues = validate_relationship_shape(final_script, plan)
    source_structure_issues = validate_source_structure_preservation(
        final_script, plan, foundation
    )
    provenance_issues = validate_final_script_provenance(
        final_script, plan, foundation
    )
    diagnostics = [
        *collect_provenance_compatibility_diagnostics(final_script, foundation),
        *collect_protected_payload_diagnostics(final_script, foundation, plan),
        *collect_source_boundary_diagnostics(final_script, foundation),
        *collect_content_route_diagnostics(final_script, plan),
    ]
    if _stage1_owns_onscreen(final_script):
        diagnostics.extend(
            [
                *collect_onscreen_composition_diagnostics(final_script, plan),
                *collect_onscreen_contract_diagnostics(final_script, plan, foundation),
                *collect_delivery_readiness_diagnostics(final_script, plan),
            ]
        )
    diagnostics.extend(
        [
            *collect_delivery_cleanliness_diagnostics(final_script, plan, foundation),
            *collect_voice_policy_diagnostics(final_script, plan),
            *collect_visibility_diagnostics(final_script, plan, foundation),
        ]
    )
    structured_blockers, review_required, structured = partition_diagnostics(
        diagnostics
    )

    # Import lazily to keep the structured semantic package independent from the
    # legacy helper graph at module-import time. Compatibility mode preserves old
    # review signals while formal blocking remains owned by semantic_contract.
    from script_engine.analysis_audits.final_orchestrator import (
        audit_final_script as audit_legacy_final_script,
    )

    legacy_issues, legacy_warnings = audit_legacy_final_script(
        final_script,
        plan if isinstance(plan, dict) else {},
        foundation if isinstance(foundation, dict) else {},
        compatibility_mode=True,
    )
    legacy_review_warnings = [
        _legacy_review_warning(issue) for issue in legacy_issues
    ]

    issues = list(
        dict.fromkeys(
            [
                *authorization_issues,
                *source_scope_issues,
                *relationship_issues,
                *source_structure_issues,
                *provenance_issues,
                *structured_blockers,
            ]
        )
    )
    warnings = list(
        dict.fromkeys(
            [
                *legacy_warnings,
                *legacy_review_warnings,
                *review_required,
            ]
        )
    )
    return issues, warnings, structured
