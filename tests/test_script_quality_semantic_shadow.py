from __future__ import annotations

from cyberppt.script_quality import audit_script_quality
from cyberppt.script_quality.models import ScriptDocument, ScriptPage
from cyberppt.script_quality.semantic_shadow import build_semantic_shadow_report


def _page(*, full_prose: str, onscreen_text: str) -> ScriptPage:
    return ScriptPage(
        page_id="P01",
        sequence=1,
        heading="",
        page_type="content",
        title="服务输出",
        main_message="来源事实支撑服务输出",
        full_prose=full_prose,
        selection_notes="保留来源事实，压缩表达。",
        evidence_map="R1：来源事实",
        evidence_map_refs=("R1",),
        source_refs=("R1",),
        boundary_source_refs=(),
        boundary="",
        visual_structure="来源事实 → 服务输出",
        onscreen_text=onscreen_text,
        module_titles=("服务输出",),
        speaker_notes="说明来源事实与服务输出之间的关系。",
    )


def _outline() -> dict[str, object]:
    return {
        "authoring_mode": "faithful",
        "pages": [
            {
                "page_id": "P01",
                "sequence": 1,
                "page_type": "content",
                "source_refs": ["R1"],
            }
        ],
    }


def _source_truth() -> dict[str, object]:
    return {
        "records": [{"id": "R1", "statement": "来源事实用于说明服务输出。"}]
    }


def test_shadow_report_keeps_legacy_as_effective_gate() -> None:
    script = ScriptDocument(
        pages=(
            _page(
                full_prose="来源事实用于说明服务输出。",
                onscreen_text="来源事实用于说明服务输出",
            ),
        )
    )

    legacy = audit_script_quality(script, _outline(), _source_truth())
    report = build_semantic_shadow_report(script, _outline(), _source_truth())

    expected_blockers = sorted(issue.code for issue in legacy if issue.severity == "error")
    expected_warnings = sorted(issue.code for issue in legacy if issue.severity != "error")
    assert report["effective_gate"] == "legacy"
    assert report["legacy"]["blocker_codes"] == sorted(set(expected_blockers))
    assert report["legacy"]["warning_codes"] == sorted(set(expected_warnings))
    expected_status = (
        "blocked"
        if expected_blockers
        else "passed_with_warnings"
        if expected_warnings
        else "passed"
    )
    assert report["status"] == expected_status


def test_shadow_semantic_blocker_does_not_replace_legacy_gate() -> None:
    script = ScriptDocument(
        pages=(
            _page(
                full_prose="来源事实用于说明服务输出，并新增99项要求。",
                onscreen_text="新增99项要求",
            ),
        )
    )

    report = build_semantic_shadow_report(script, _outline(), _source_truth())

    assert "FINAL_NUMBER_OUTSIDE_FOUNDATION" in report["semantic_shadow"]["blocker_codes"]
    assert report["effective_gate"] == "legacy"
    assert report["status"] == (
        "blocked"
        if report["legacy"]["blockers"]
        else "passed_with_warnings"
        if report["legacy"]["warnings"]
        else "passed"
    )


def test_shadow_report_exposes_code_level_divergence() -> None:
    script = ScriptDocument(
        pages=(
            _page(
                full_prose="来源事实用于说明服务输出，并新增 AlphaModel 表述。",
                onscreen_text="新增 AlphaModel 表述",
            ),
        )
    )

    report = build_semantic_shadow_report(script, _outline(), _source_truth())

    assert "COMPOSED_TRACE_IDENTIFIER_REVIEW_REQUIRED" in report["semantic_shadow"]["review_codes"]
    assert isinstance(report["diff"]["blocker_codes_only_legacy"], list)
    assert isinstance(report["diff"]["blocker_codes_only_semantic"], list)
    assert isinstance(report["diff"]["common_blocker_codes"], list)
