from __future__ import annotations

from script_engine.quality_policy import ADVISORY, BLOCKER, classify_issue, issue_code


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
