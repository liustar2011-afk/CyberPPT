"""Cross-artifact authorization checks for Final Script semantic contracts."""

from __future__ import annotations

from typing import Any


def validate_authoring_mode_authorization(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
) -> list[str]:
    """Reject a Final Script that escalates beyond the PLAN-approved authoring mode.

    This check depends only on explicit contract enums. It therefore belongs to
    the structured semantic authority rather than the legacy text/heuristic
    auditor.
    """

    approved = str((plan or {}).get("authoring_mode") or "faithful")
    requested = str(
        (final_script.get("deck") or {}).get("authoring_mode") or approved
    )
    if requested == "analytical" and approved != "analytical":
        return [
            "AUTHORING_MODE_NOT_AUTHORIZED: final script requests analytical mode "
            "without analytical mode in the approved Deck Plan"
        ]
    return []
