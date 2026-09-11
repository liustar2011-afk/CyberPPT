from __future__ import annotations

import cyberppt.script_quality.semantic_shadow as shadow
from cyberppt.commands.semantic_shadow import (
    render_semantic_shadow_summary,
    semantic_shadow_exit_code,
)
from cyberppt.script_quality.models import ScriptDocument, ScriptQualityIssue


def _legacy_error(code: str = "LEGACY_BLOCK") -> ScriptQualityIssue:
    return ScriptQualityIssue(
        code=code,
        severity="error",
        message="legacy blocker",
    )


def test_shadow_reports_matching_blocking_outcome(monkeypatch) -> None:
    monkeypatch.setattr(
        shadow,
        "_audit_script_quality",
        lambda *args, **kwargs: [_legacy_error()],
    )
    monkeypatch.setattr(
        shadow,
        "audit_legacy_script_semantics",
        lambda *args, **kwargs: (
            ["[SEMANTIC_BLOCK] P01: semantic blocker"],
            [],
            [],
        ),
    )

    report = shadow.build_semantic_shadow_report(
        ScriptDocument(pages=()),
        {},
        {},
    )

    assert report["legacy"]["status"] == "blocked"
    assert report["semantic_shadow"]["status"] == "blocked"
    assert report["diff"]["legacy_blocked"] is True
    assert report["diff"]["semantic_blocked"] is True
    assert report["diff"]["blocking_outcome_matches"] is True
    assert report["diff"]["blocker_code_sets_match"] is False
    assert semantic_shadow_exit_code(report) == 1
    assert "blocking outcome: match" in render_semantic_shadow_summary(report)


def test_semantic_only_blocker_is_observational_but_marks_divergence(monkeypatch) -> None:
    monkeypatch.setattr(
        shadow,
        "_audit_script_quality",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        shadow,
        "audit_legacy_script_semantics",
        lambda *args, **kwargs: (
            ["[SEMANTIC_ONLY_BLOCK] P01: semantic blocker"],
            [],
            [],
        ),
    )

    report = shadow.build_semantic_shadow_report(
        ScriptDocument(pages=()),
        {},
        {},
    )

    assert report["status"] == "passed"
    assert report["legacy"]["status"] == "passed"
    assert report["semantic_shadow"]["status"] == "blocked"
    assert report["diff"]["blocking_outcome_matches"] is False
    assert semantic_shadow_exit_code(report) == 0
    summary = render_semantic_shadow_summary(report)
    assert "blocking outcome: diverged" in summary
    assert "legacy=passed" in summary
    assert "semantic=blocked" in summary
