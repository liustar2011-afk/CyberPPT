from __future__ import annotations

from cyberppt.script_quality.models import ScriptDocument, ScriptPage
from cyberppt.script_quality.semantic_adapter import (
    audit_legacy_script_semantics,
    project_legacy_semantic_artifacts,
    project_outline_to_deck_plan,
)


def _page(*, content_load: str = "", onscreen_text: str = "") -> ScriptPage:
    return ScriptPage(
        page_id="P01",
        sequence=1,
        heading="执行安排",
        page_type="content",
        title="执行安排",
        main_message="来源事实用于说明执行安排",
        full_prose="来源事实用于说明执行安排。",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=("F1",),
        boundary_source_refs=(),
        boundary="",
        visual_structure="",
        onscreen_text=onscreen_text,
        module_titles=(),
        subtitle="执行安排副标题",
        content_load=content_load,
    )


def _truth() -> dict[str, object]:
    return {
        "records": [{"id": "F1", "statement": "来源事实用于说明执行安排。"}],
        "source_structure": [],
    }


def test_outline_projection_preserves_explicit_semantic_contract_fields() -> None:
    outline = {
        "authoring_mode": "faithful",
        "delivery_mode": "presenter_led",
        "audience_scope": "internal",
        "pages": [
            {
                "page_id": "P01",
                "page_type": "content",
                "source_refs": ["F1"],
                "content_load": "dense",
                "content_route": {"meaning_signals": ["关键条件"]},
                "onscreen_composition": {"mode": "evidence_first", "lead_budget": 0},
                "onscreen_contract": {
                    "expression_mode": "mixed",
                    "modules": [],
                },
                "proof": {"evidence_refs": ["F1"]},
                "analysis_basis": {"supports": ["F1"]},
            }
        ],
    }

    plan = project_outline_to_deck_plan(outline)
    page = plan["pages"][0]

    assert plan["delivery_mode"] == "presenter_led"
    assert plan["audience_scope"] == "internal"
    assert page["content_load"] == "dense"
    assert page["content_route"] == {"meaning_signals": ["关键条件"]}
    assert page["onscreen_composition"] == {
        "mode": "evidence_first",
        "lead_budget": 0,
    }
    assert page["onscreen_contract"] == {
        "expression_mode": "mixed",
        "modules": [],
    }
    assert page["proof"] == {"evidence_refs": ["F1"]}
    assert page["analysis_basis"] == {"supports": ["F1"]}


def test_final_projection_preserves_delivery_mode_subtitle_and_content_load() -> None:
    final_script, plan, _ = project_legacy_semantic_artifacts(
        ScriptDocument(pages=(_page(content_load="light"),)),
        {
            "authoring_mode": "faithful",
            "delivery_mode": "presenter_led",
            "pages": [
                {
                    "page_id": "P01",
                    "page_type": "content",
                    "source_refs": ["F1"],
                    "content_load": "light",
                }
            ],
        },
        _truth(),
    )

    assert final_script["deck"]["delivery_mode"] == "presenter_led"
    assert final_script["slides"][0]["subtitle"] == "执行安排副标题"
    assert final_script["slides"][0]["content_load"] == "light"
    assert plan["delivery_mode"] == "presenter_led"
    assert plan["pages"][0]["content_load"] == "light"


def test_presenter_led_projection_does_not_create_false_self_read_blocker() -> None:
    blockers, _, _ = audit_legacy_script_semantics(
        ScriptDocument(pages=(_page(),)),
        {
            "authoring_mode": "faithful",
            "delivery_mode": "presenter_led",
            "pages": [
                {
                    "page_id": "P01",
                    "page_type": "content",
                    "source_refs": ["F1"],
                }
            ],
        },
        _truth(),
    )

    assert not any("ONSCREEN_SELF_READ_PAYLOAD_MISSING" in item for item in blockers)


def test_light_self_read_projection_does_not_create_false_payload_blocker() -> None:
    blockers, _, _ = audit_legacy_script_semantics(
        ScriptDocument(pages=(_page(content_load="light"),)),
        {
            "authoring_mode": "faithful",
            "delivery_mode": "self_read",
            "pages": [
                {
                    "page_id": "P01",
                    "page_type": "content",
                    "source_refs": ["F1"],
                    "content_load": "light",
                }
            ],
        },
        _truth(),
    )

    assert not any("ONSCREEN_SELF_READ_PAYLOAD_MISSING" in item for item in blockers)
