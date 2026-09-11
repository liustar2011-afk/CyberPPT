from __future__ import annotations

from cyberppt.script_quality import audit_script_semantic_contract
from cyberppt.script_quality.models import ScriptDocument, ScriptPage


def test_public_legacy_semantic_entry_routes_through_script_engine() -> None:
    page = ScriptPage(
        page_id="P01",
        sequence=1,
        heading="",
        page_type="content",
        title="服务输出",
        main_message="来源事实支撑服务输出",
        full_prose="来源事实用于说明服务输出，并新增9项要求。",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=("R1",),
        source_refs=("R1",),
        boundary_source_refs=(),
        boundary="",
        visual_structure="",
        onscreen_text="新增9项要求",
        module_titles=("服务输出",),
    )
    script = ScriptDocument(pages=(page,))
    outline = {
        "authoring_mode": "faithful",
        "pages": [
            {"page_id": "P01", "page_type": "content", "source_refs": ["R1"]}
        ],
    }
    source_truth = {
        "records": [{"id": "R1", "statement": "来源事实用于说明服务输出。"}]
    }

    issues, warnings, diagnostics = audit_script_semantic_contract(
        script,
        outline,
        source_truth,
    )

    assert any(
        "[FINAL_NUMBER_OUTSIDE_FOUNDATION]" in issue and "9" in issue
        for issue in issues
    )
    assert any(
        diagnostic["code"] == "FINAL_NUMBER_OUTSIDE_FOUNDATION"
        for diagnostic in diagnostics
    )
    assert isinstance(warnings, list)
    assert isinstance(diagnostics, list)
