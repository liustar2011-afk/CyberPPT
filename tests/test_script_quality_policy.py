from __future__ import annotations

from script_engine.quality_policy import (
    ADVISORY,
    BLOCKER,
    classify_issue,
    issue_code,
    partition_issues,
)


def test_visual_wording_heuristic_is_advisory() -> None:
    finding = classify_issue("AUTHOR_VISUAL_THESIS_NONRELATIONAL: slides.1.visual_thesis: no visible relation verb")
    assert finding["severity"] == ADVISORY


def test_structural_required_field_remains_blocker() -> None:
    finding = classify_issue("AUTHOR_FIELD_REQUIRED: slides.1.full_copy: content pages require a non-empty full_copy")
    assert finding["severity"] == BLOCKER


def test_unknown_findings_fail_closed() -> None:
    finding = classify_issue("SOME_NEW_GATE: future deterministic issue")
    assert finding["severity"] == BLOCKER


def test_banned_phrase_rule_code_can_be_extracted() -> None:
    assert issue_code("slides.0.full_copy: [self-reference] matched wording") == "self-reference"


def test_partition_issues_separates_only_registered_advisories() -> None:
    blocker = "AUTHOR_FIELD_REQUIRED: slides.1.full_copy: missing"
    advisory = "AUTHOR_MISSION_GENERIC: slides.1.mission: wording heuristic"

    blockers, advisories = partition_issues([advisory, blocker])

    assert blockers == [blocker]
    assert advisories == [advisory]


def test_partition_issues_keeps_unstructured_findings_blocking() -> None:
    issue = "plain deterministic failure without a registered code"

    blockers, advisories = partition_issues([issue])

    assert blockers == [issue]
    assert advisories == []
