from __future__ import annotations

from cyberppt.script_quality.models import (
    LEGACY_HEURISTIC_WARNING_CODES,
    ScriptPage,
    _issue,
)


def _page() -> ScriptPage:
    return ScriptPage(
        page_id="P01",
        sequence=1,
        heading="示例页",
        page_type="content",
        title="示例页",
        main_message="示例判断",
        full_prose="示例完整文字稿。",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=(),
        boundary_source_refs=(),
        boundary="",
        visual_structure="",
        onscreen_text="示例上屏文字",
        module_titles=("示例模块",),
    )


def test_audit_named_legacy_heuristics_are_forced_to_warning() -> None:
    expected = {
        "OFF_TOPIC_CONSTRAINT_MODULE",
        "FACT_CERTAINTY_LOST",
        "ONSCREEN_FALSE_PARENT_CHILD_RELATION",
        "ONSCREEN_FALSE_PARALLEL_SEMANTICS",
        "ONSCREEN_COMPLETE_PROPOSITION_UNGROUNDED",
        "ONSCREEN_DETAIL_PHRASE_TOO_LONG",
        "ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL",
        "ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY",
        "ONSCREEN_GROUP_ROLE_REPETITION",
        "ONSCREEN_MODULE_INDEX_RESTATEMENT",
        "CONTENT_PAGE_TOO_SPARSE",
        "VISIBLE_NODE_OVERLOAD",
    }
    assert expected <= LEGACY_HEURISTIC_WARNING_CODES

    page = _page()
    for code in expected:
        issue = _issue(code, page, "review", "review", severity="error")
        assert issue.severity == "warning", code


def test_unregistered_structural_and_delivery_findings_remain_blocking() -> None:
    page = _page()
    for code in (
        "ONSCREEN_MARKDOWN_LEAK",
        "ONSCREEN_BACKEND_META_LEAK",
        "ONSCREEN_JUDGMENT_MODE_INVALID",
        "ONSCREEN_UNDECLARED_ORDER_SIGNAL",
        "ONSCREEN_GROUP_SEMANTIC_CONTRACT_CONFLICT",
        "DECLARED_COUNT_MISMATCH",
    ):
        assert code not in LEGACY_HEURISTIC_WARNING_CODES
        issue = _issue(code, page, "blocking", "fix", severity="error")
        assert issue.severity == "error", code


def test_explicit_warning_cannot_be_promoted_by_the_legacy_policy() -> None:
    page = _page()
    issue = _issue(
        "ONSCREEN_REDUNDANT_RESTATEMENT",
        page,
        "review",
        "review",
        severity="warning",
    )
    assert issue.severity == "warning"
