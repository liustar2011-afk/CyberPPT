"""Layer-four status gates.

The validation status answers whether the JSON contract is sound. The gate
status answers whether the artifact is eligible for authoring handoff.
"""

from __future__ import annotations

from typing import Any


def build_layer4_status(
    deck: dict[str, Any],
    plan: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    errors = [item for item in validation.get("errors") or [] if isinstance(item, dict)]
    structural_status = "ok" if not errors else "error"
    authoring_complete = (
        deck.get("editorial_authoring_mode") == "author_driven"
        and plan.get("editorial_authoring_mode") == "author_driven"
        and deck.get("editorial_authoring_status") == "author_edited"
        and plan.get("editorial_authoring_status") == "author_edited"
    )
    authoring_status = "passed" if authoring_complete and structural_status == "ok" else (
        "pending" if not authoring_complete else "error"
    )
    source_binding_status = "error" if any(
        str(item.get("code") or "").startswith(("unknown_", "missing_direct_fact", "stale_", "workpack_", "source_", "semantic_"))
        for item in errors
    ) else "ok"
    blocking_reasons = [str(item.get("code") or "OUTLINE_VALIDATION_FAILED") for item in errors]
    if not authoring_complete:
        blocking_reasons.append("OUTLINE_AUTHORING_INCOMPLETE")
    handoff_status = "passed" if structural_status == "ok" and authoring_complete else "blocked"
    return {
        "structural_status": structural_status,
        "source_binding_status": source_binding_status,
        "authoring_status": authoring_status,
        "handoff_status": handoff_status,
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
    }


__all__ = ["build_layer4_status"]
