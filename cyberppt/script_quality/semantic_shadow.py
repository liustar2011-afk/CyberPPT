"""Shadow comparison between legacy Script Quality and Stage 01 semantics.

The shadow report is observational only. Legacy Script Quality remains the
active compatibility gate; the semantic-contract result is collected beside it
so projects can measure divergence before switching authority.
"""

from __future__ import annotations

import re
from typing import Any

from .audit import audit_script_quality as _audit_script_quality
from .models import ScriptDocument, ScriptQualityIssue
from .semantic_adapter import audit_legacy_script_semantics
from .severity import normalize_public_issue_severity


_BRACKET_CODE_RE = re.compile(r"\[([A-Z][A-Z0-9_]+)\]")
_SCOPED_CODE_RE = re.compile(r"(?:^|:\s)([A-Z][A-Z0-9_]+):")


def _semantic_code(message: str) -> str:
    bracket = _BRACKET_CODE_RE.search(str(message or ""))
    if bracket:
        return bracket.group(1)
    scoped = _SCOPED_CODE_RE.search(str(message or ""))
    return scoped.group(1) if scoped else "UNKNOWN"


def _issue_dicts(issues: list[ScriptQualityIssue]) -> list[dict[str, object]]:
    return [issue.to_dict() for issue in issues]


def _codes(messages: list[str]) -> list[str]:
    return sorted({_semantic_code(message) for message in messages})


def build_semantic_shadow_report(
    script: ScriptDocument,
    outline: dict[str, object],
    source_truth: dict[str, object],
    *,
    source_units: tuple[dict[str, object], ...] = (),
) -> dict[str, Any]:
    """Compare legacy and semantic audits without changing the active gate.

    ``effective_gate`` is intentionally fixed to ``legacy`` in this phase. The
    report can therefore be introduced into existing CI or review tooling without
    changing pass/fail behavior. Only the explicit semantic entry can currently
    exercise the new semantic authority directly.
    """

    legacy_issues = normalize_public_issue_severity(
        _audit_script_quality(
            script,
            outline,
            source_truth,
            source_units=source_units,
        )
    )
    semantic_blockers, semantic_reviews, semantic_diagnostics = (
        audit_legacy_script_semantics(script, outline, source_truth)
    )

    legacy_blockers = [issue for issue in legacy_issues if issue.severity == "error"]
    legacy_warnings = [issue for issue in legacy_issues if issue.severity != "error"]
    legacy_blocker_codes = sorted({issue.code for issue in legacy_blockers})
    legacy_warning_codes = sorted({issue.code for issue in legacy_warnings})
    semantic_blocker_codes = _codes(semantic_blockers)
    semantic_review_codes = _codes(semantic_reviews)

    return {
        "schema": "cyberppt.script_quality_semantic_shadow.v1",
        "mode": "shadow",
        "effective_gate": "legacy",
        "status": (
            "blocked"
            if legacy_blockers
            else "passed_with_warnings"
            if legacy_warnings
            else "passed"
        ),
        "legacy": {
            "blockers": _issue_dicts(legacy_blockers),
            "warnings": _issue_dicts(legacy_warnings),
            "blocker_codes": legacy_blocker_codes,
            "warning_codes": legacy_warning_codes,
        },
        "semantic_shadow": {
            "blockers": list(semantic_blockers),
            "reviews": list(semantic_reviews),
            "diagnostics": list(semantic_diagnostics),
            "blocker_codes": semantic_blocker_codes,
            "review_codes": semantic_review_codes,
        },
        "diff": {
            "blocker_codes_only_legacy": sorted(
                set(legacy_blocker_codes) - set(semantic_blocker_codes)
            ),
            "blocker_codes_only_semantic": sorted(
                set(semantic_blocker_codes) - set(legacy_blocker_codes)
            ),
            "common_blocker_codes": sorted(
                set(legacy_blocker_codes) & set(semantic_blocker_codes)
            ),
        },
    }


__all__ = ["build_semantic_shadow_report"]
