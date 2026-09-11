"""Single Stage 01 semantic-contract audit entry point."""

from __future__ import annotations

from typing import Any

from .authorization import validate_authoring_mode_authorization
from .compatibility import collect_provenance_compatibility_diagnostics
from .content_route import collect_content_route_diagnostics
from .delivery_cleanliness import collect_delivery_cleanliness_diagnostics
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


def audit_final_script_semantic_contract(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> tuple[list[str], list[str], list[dict[str, object]]]:
    """Run the authoritative Final Script semantic audit through one entry point.

    Structured authorization, source scope, relationship shape/topology,
    source-structure preservation, provenance, typed compatibility, protected
    payload, objective source boundaries, explicit PLAN content-route/onscreen
    contracts, delivery cleanliness and voice policy, and explicit visibility are
    the new semantic authority. During Phase 4, the historical Final Script auditor
    is invoked here as a compatibility adapter so formal callers no longer need to
    orchestrate two independent semantic engines. Its remaining capabilities can
    now be migrated here one by one without changing the public audit boundary.
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
        *collect_onscreen_composition_diagnostics(final_script, plan),
        *collect_onscreen_contract_diagnostics(final_script, plan, foundation),
        *collect_delivery_cleanliness_diagnostics(final_script, plan, foundation),
        *collect_voice_policy_diagnostics(final_script, plan),
        *collect_visibility_diagnostics(final_script, plan, foundation),
    ]
    structured_blockers, review_required, structured = partition_diagnostics(
        diagnostics
    )

    # Import lazily to keep the structured semantic package independent from the
    # legacy helper graph at module-import time. Phase 4 removes this adapter as
    # its remaining deterministic responsibilities are migrated here. The adapter
    # runs in compatibility mode so checks already owned by structured validators
    # are not recomputed by legacy code.
    from script_engine.analysis_audits.final_orchestrator import (
        audit_final_script as audit_legacy_final_script,
    )

    legacy_issues, legacy_warnings = audit_legacy_final_script(
        final_script,
        plan if isinstance(plan, dict) else {},
        foundation if isinstance(foundation, dict) else {},
        compatibility_mode=True,
    )

    issues = list(
        dict.fromkeys(
            [
                *authorization_issues,
                *source_scope_issues,
                *relationship_issues,
                *source_structure_issues,
                *provenance_issues,
                *structured_blockers,
                *legacy_issues,
            ]
        )
    )
    warnings = list(dict.fromkeys([*legacy_warnings, *review_required]))
    return issues, warnings, structured
