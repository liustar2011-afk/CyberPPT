from __future__ import annotations

from cyberppt.script_quality.models import ScriptDocument, ScriptPage
from cyberppt.script_quality.semantic_adapter import (
    audit_legacy_script_semantics,
    project_legacy_semantic_artifacts,
)


def _page(
    *,
    full_prose: str = "来源事实用于说明服务输出。",
    onscreen_text: str = "来源事实用于说明服务输出",
    receipt: dict[str, object] | None = None,
) -> ScriptPage:
    return ScriptPage(
        page_id="P01",
        sequence=1,
        heading="",
        page_type="content",
        title="服务输出",
        main_message="来源事实支撑服务输出",
        full_prose=full_prose,
        selection_notes="",
        evidence_map="",
        evidence_map_refs=("R1",),
        source_refs=("R1",),
        boundary_source_refs=("R2",),
        boundary="",
        visual_structure="A → B → C",
        onscreen_text=onscreen_text,
        module_titles=("服务输出",),
        speaker_notes="",
        contract_receipt=receipt,
    )


def _outline() -> dict[str, object]:
    return {
        "title": "历史项目",
        "communication_goal": "验证旧脚本语义",
        "authoring_mode": "faithful",
        "source_consumption_policy": "required",
        "pages": [
            {
                "page_id": "P01",
                "page_type": "content",
                "source_refs": ["R1"],
                "boundary_refs": ["R2"],
                "primary_relation": {
                    "type": "parallel",
                    "scope": ["A", "B"],
                },
            }
        ],
    }


def _source_truth() -> dict[str, object]:
    return {
        "records": [
            {
                "id": "R1",
                "statement": "来源事实用于说明服务输出。",
                "status": "规划",
                "conditions": ["满足条件后实施"],
                "visibility": "external_ok",
                "number_refs": ["N1"],
            },
            {
                "id": "R2",
                "statement": "边界事实仅用于限定适用范围。",
                "visibility": "internal_only",
            },
        ],
        "numbers": [{"id": "N1", "value": 2028, "unit": "年"}],
    }


def test_legacy_adapter_preserves_explicit_ids_boundaries_and_typed_fields() -> None:
    script = ScriptDocument(pages=(_page(),))

    final_script, plan, foundation = project_legacy_semantic_artifacts(
        script,
        _outline(),
        _source_truth(),
    )

    slide = final_script["slides"][0]
    plan_page = plan["pages"][0]
    records = {item["id"]: item for item in foundation["facts"]}

    assert final_script["version"] == "1.0"
    assert slide["source_refs"] == ["R1", "R2"]
    assert plan_page["source_refs"] == ["R1", "R2"]
    assert foundation["source_consumption_policy"] == "required"
    assert records["R1"]["status"] == "规划"
    assert records["R1"]["conditions"] == ["满足条件后实施"]
    assert records["R1"]["visibility"] == "external_ok"
    assert records["R1"]["number_refs"] == ["N1"]
    assert records["R2"]["visibility"] == "internal_only"


def test_legacy_adapter_does_not_infer_relationships_from_visual_structure() -> None:
    script = ScriptDocument(pages=(_page(),))

    final_script, _, _ = project_legacy_semantic_artifacts(
        script,
        _outline(),
        _source_truth(),
    )

    assert "relationships" not in final_script["slides"][0]


def test_legacy_adapter_projects_only_explicit_receipt_relationships() -> None:
    receipt = {
        "content_relations": [
            {"from": "A", "to": "B", "relation": "支撑"}
        ]
    }
    script = ScriptDocument(pages=(_page(receipt=receipt),))

    final_script, _, _ = project_legacy_semantic_artifacts(
        script,
        _outline(),
        _source_truth(),
    )

    assert final_script["slides"][0]["relationships"] == [
        {"from": "A", "to": "B", "relation": "支撑"}
    ]


def test_legacy_adapter_does_not_invent_missing_typed_semantics() -> None:
    source_truth = {
        "records": [{"id": "R1", "statement": "普通来源事实。"}]
    }
    script = ScriptDocument(pages=(_page(),))

    _, _, foundation = project_legacy_semantic_artifacts(
        script,
        _outline(),
        source_truth,
    )

    record = foundation["facts"][0]
    assert set(record) == {"id", "statement"}


def test_legacy_adapter_can_run_authoritative_semantic_entry() -> None:
    source_truth = {
        "records": [
            {"id": "R1", "statement": "来源事实用于说明服务输出。"},
            {"id": "R2", "statement": "边界事实用于限定范围。"},
        ]
    }
    script = ScriptDocument(
        pages=(
            _page(
                full_prose="来源事实用于说明服务输出，并新增9项要求。",
                onscreen_text="新增9项要求",
            ),
        )
    )

    issues, _, diagnostics = audit_legacy_script_semantics(
        script,
        _outline(),
        source_truth,
    )

    assert any(
        "COMPOSED_TRACE_SOURCE_BOUNDARY" in issue and "9" in issue
        for issue in issues
    )
    assert isinstance(diagnostics, list)
