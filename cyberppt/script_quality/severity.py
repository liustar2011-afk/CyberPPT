"""Public severity policy for the legacy Script Quality compatibility surface."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .models import LEGACY_HEURISTIC_WARNING_CODES, ScriptQualityIssue


# These Stage 02-facing expression checks were already advisory at the legacy
# audit boundary before the broader Phase 3 isolation. Keep them in the same
# normalization layer so public callers have one severity authority.
_STAGE02_EXPRESSION_WARNING_CODES = frozenset(
    {
        "ONSCREEN_HEADING_LENGTH_IMBALANCED",
        "ONSCREEN_LINE_TOO_LONG",
        "VISIBLE_NODE_OVERLOAD",
        "VISUAL_STRUCTURE_TOO_THIN",
        "DECLARED_RELATION_NOT_VISIBLE",
        "ONSCREEN_FALSE_RELATION_PARALLEL",
        "ONSCREEN_FLOW_ACTION_MISSING",
        "ONSCREEN_LAYOUT_META_LEAK",
        "ONSCREEN_RELATION_ISOMORPHISM",
        "ONSCREEN_MECHANICAL_LABEL_TEMPLATE",
    }
)

PUBLIC_WARNING_CODES = (
    LEGACY_HEURISTIC_WARNING_CODES | _STAGE02_EXPRESSION_WARNING_CODES
)


def normalize_public_issue_severity(
    issues: Iterable[ScriptQualityIssue],
) -> list[ScriptQualityIssue]:
    """Downgrade governed legacy heuristics at the public audit boundary.

    Low-level helpers intentionally retain their historical local severity so
    tests and diagnostic callers can reason about the rule that fired. The
    production compatibility surface owns the final severity decision. Unknown
    codes remain fail-closed; only explicitly governed codes can be downgraded.
    """

    return [
        replace(issue, severity="warning")
        if issue.code in PUBLIC_WARNING_CODES and issue.severity == "error"
        else issue
        for issue in issues
    ]
