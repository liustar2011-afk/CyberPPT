from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract
from script_engine.semantic_contract.onscreen_composition import (
    collect_onscreen_composition_diagnostics,
)


def _foundation() -> dict:
    return {
        "facts": [{"id": "F1", "statement": "来源事实用于说明执行安排。"}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }


def _plan(composition: dict) -> dict:
    return {
        "authoring_mode": "faithful",
        "delivery_mode": "presenter_led",
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "source_refs": ["F1"],
                "onscreen_composition": composition,
            }
        ],
    }


def _final(modules: list[dict]) -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {"authoring_mode": "faithful", "delivery_mode": "presenter_led"},
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "执行安排",
                "source_refs": ["F1"],
                "full_copy": "来源事实用于说明执行安排。",
                "onscreen": modules,
            }
        ],
    }


def test_evidence_first_lead_text_is_structured_blocker() -> None:
    final_script = _final(
        [{"heading": "执行安排", "text": "来源事实用于说明执行安排。"}]
    )
    plan = _plan({"mode": "evidence_first", "lead_budget": 0})

    diagnostics = collect_onscreen_composition_diagnostics(final_script, plan)
    assert any(
        diagnostic.code == "ONSCREEN_MODULE_LEAD_FORBIDDEN"
        and diagnostic.target == "text"
        for diagnostic in diagnostics
    )

    issues, _, structured = audit_final_script_semantic_contract(
        final_script, plan, _foundation()
    )
    assert sum("ONSCREEN_MODULE_LEAD_FORBIDDEN" in issue for issue in issues) == 1
    assert any(
        diagnostic["code"] == "ONSCREEN_MODULE_LEAD_FORBIDDEN"
        for diagnostic in structured
    )


def test_raw_legacy_keeps_historical_composition_blocker() -> None:
    final_script = _final(
        [{"heading": "执行安排", "text": "来源事实用于说明执行安排。"}]
    )
    plan = _plan({"mode": "evidence_first", "lead_budget": 0})

    issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        _foundation(),
        compatibility_mode=False,
    )

    assert any(
        "onscreen_composition='evidence_first' forbids module lead text" in issue
        for issue in issues
    )


def test_selective_lead_budget_is_structured_blocker() -> None:
    final_script = _final(
        [
            {"heading": "模块甲", "text": "来源事实甲"},
            {"heading": "模块乙", "text": "来源事实乙"},
        ]
    )
    plan = _plan({"mode": "selective_lead", "lead_budget": 1})

    diagnostics = collect_onscreen_composition_diagnostics(final_script, plan)

    assert any(
        diagnostic.code == "ONSCREEN_LEAD_BUDGET_EXCEEDED"
        and "got 2" in diagnostic.message
        for diagnostic in diagnostics
    )


def test_invalid_composition_definition_is_structured_blocker() -> None:
    final_script = _final([{"heading": "执行安排", "items": ["来源事实"]}])
    plan = _plan({"mode": "selective_lead", "lead_budget": 0})

    diagnostics = collect_onscreen_composition_diagnostics(final_script, plan)

    assert any(
        diagnostic.code == "ONSCREEN_COMPOSITION_INVALID"
        and diagnostic.target == "onscreen_composition.lead_budget"
        for diagnostic in diagnostics
    )


def test_lead_like_first_item_stays_review_only_in_formal_path() -> None:
    final_script = _final(
        [
            {
                "heading": "执行安排",
                "items": [
                    "该项工作需要建立统一管理机制并持续推动实施落地",
                    "基础数据",
                ],
            }
        ]
    )
    plan = _plan({"mode": "evidence_first", "lead_budget": 0})

    issues, warnings, structured = audit_final_script_semantic_contract(
        final_script, plan, _foundation()
    )

    assert not any(
        "AUTHOR_EVIDENCE_FIRST_HIERARCHY_HEURISTIC" in issue for issue in issues
    )
    assert any(
        "AUTHOR_EVIDENCE_FIRST_HIERARCHY_HEURISTIC" in warning
        for warning in warnings
    )
    assert not any(
        diagnostic["code"] == "AUTHOR_EVIDENCE_FIRST_HIERARCHY_HEURISTIC"
        for diagnostic in structured
    )
