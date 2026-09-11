from __future__ import annotations

from script_engine.analysis_audits.final_orchestrator import (
    audit_final_script as audit_legacy_final_script,
)
from script_engine.semantic_contract import audit_final_script_semantic_contract
from script_engine.semantic_contract.onscreen_contract import (
    collect_onscreen_contract_diagnostics,
)


def _foundation(*, colocation: bool = False) -> dict:
    if colocation:
        facts = [
            {
                "id": "F1",
                "statement": "行动计划推进重点应用场景建设。",
                "source_refs": ["SU1"],
            },
            {
                "id": "F2",
                "statement": "管理办法明确安全责任和制度安排。",
                "source_refs": ["SU1"],
            },
        ]
    else:
        facts = [
            {"id": "F1", "statement": "甲模块应保留甲信号。"},
            {"id": "F2", "statement": "乙模块应保留乙信号。"},
        ]
    return {
        "facts": facts,
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }


def _plan(*, colocation: bool = False) -> dict:
    if colocation:
        modules = [
            {
                "heading": "管理制度",
                "evidence_refs": ["F1", "F2"],
                "required_signals": ["安全责任"],
            }
        ]
    else:
        modules = [
            {
                "heading": "甲模块",
                "evidence_refs": ["F1"],
                "required_signals": ["甲信号"],
                "forbidden_signals": ["乙信号"],
            },
            {
                "heading": "乙模块",
                "evidence_refs": ["F2"],
                "required_signals": ["乙信号"],
            },
        ]
    return {
        "authoring_mode": "faithful",
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "source_refs": ["F1", "F2"],
                "onscreen_contract": {
                    "relation": "parallel" if not colocation else "group",
                    "scope_mode": "exclusive" if not colocation else "shared",
                    "expression_mode": "phrase_led",
                    "modules": modules,
                    "detail_policy": {},
                },
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
                "title": "合同检查",
                "source_refs": ["F1", "F2"],
                "full_copy": "甲模块保留甲信号，乙模块保留乙信号。",
                "onscreen": modules,
            }
        ],
    }


def test_required_signal_is_owned_by_structured_diagnostic() -> None:
    final_script = _final(
        [
            {"heading": "甲模块", "text": "未保留要求"},
            {"heading": "乙模块", "text": "乙信号"},
        ]
    )
    plan = _plan()
    foundation = _foundation()

    diagnostics = collect_onscreen_contract_diagnostics(
        final_script, plan, foundation
    )
    assert any(
        diagnostic.code == "ONSCREEN_REQUIRED_SIGNAL_MISSING"
        and diagnostic.module_id == "onscreen[0]"
        and diagnostic.evidence_refs == ("F1",)
        for diagnostic in diagnostics
    )

    issues, _, structured = audit_final_script_semantic_contract(
        final_script, plan, foundation
    )
    assert sum("ONSCREEN_REQUIRED_SIGNAL_MISSING" in issue for issue in issues) == 1
    assert any(
        diagnostic["code"] == "ONSCREEN_REQUIRED_SIGNAL_MISSING"
        for diagnostic in structured
    )


def test_raw_legacy_keeps_historical_onscreen_contract_behavior() -> None:
    final_script = _final(
        [
            {"heading": "甲模块", "text": "未保留要求"},
            {"heading": "乙模块", "text": "乙信号"},
        ]
    )

    issues, _ = audit_legacy_final_script(
        final_script,
        _plan(),
        _foundation(),
        compatibility_mode=False,
    )

    assert any("ONSCREEN_REQUIRED_SIGNAL_MISSING" in issue for issue in issues)


def test_explicit_forbidden_signal_and_exclusive_scope_are_blocking() -> None:
    final_script = _final(
        [
            {"heading": "甲模块", "text": "甲信号，同时包含乙信号和乙模块"},
            {"heading": "乙模块", "text": "乙信号"},
        ]
    )

    diagnostics = collect_onscreen_contract_diagnostics(
        final_script, _plan(), _foundation()
    )
    codes = {diagnostic.code for diagnostic in diagnostics}

    assert "ONSCREEN_FORBIDDEN_SIGNAL_PRESENT" in codes
    assert "ONSCREEN_EXCLUSIVE_SCOPE_VIOLATION" in codes


def test_v11_object_items_are_checked_against_explicit_role_policy() -> None:
    plan = _plan()
    contract = plan["pages"][0]["onscreen_contract"]
    contract["detail_policy"] = {
        "role_markers": {"forbidden": ["禁止角色"], "allowed": ["允许角色"]},
        "allowed_roles": ["allowed"],
        "forbidden_roles": ["forbidden"],
    }
    final_script = _final(
        [
            {
                "id": "M01",
                "heading": "甲模块",
                "items": [{"id": "M01-I01", "text": "甲信号：禁止角色"}],
            },
            {
                "id": "M02",
                "heading": "乙模块",
                "items": [{"id": "M02-I01", "text": "乙信号：允许角色"}],
            },
        ]
    )
    final_script["version"] = "1.1"

    diagnostics = collect_onscreen_contract_diagnostics(
        final_script, plan, _foundation()
    )

    assert any(
        diagnostic.code == "ONSCREEN_DETAIL_ROLE_DISALLOWED"
        and diagnostic.module_id == "M01"
        and "forbidden" in diagnostic.message
        for diagnostic in diagnostics
    )


def test_colocation_word_classifier_is_review_only_in_formal_path() -> None:
    plan = _plan(colocation=True)
    foundation = _foundation(colocation=True)
    final_script = _final(
        [{"heading": "管理制度", "text": "安全责任与应用场景"}]
    )

    formal_issues, formal_warnings, structured = (
        audit_final_script_semantic_contract(final_script, plan, foundation)
    )
    assert not any(
        "ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY" in issue
        for issue in formal_issues
    )
    assert any(
        "ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY_REVIEW_REQUIRED" in warning
        for warning in formal_warnings
    )
    assert not any(
        diagnostic["code"] == "ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY"
        for diagnostic in structured
    )

    raw_issues, _ = audit_legacy_final_script(
        final_script,
        plan,
        foundation,
        compatibility_mode=False,
    )
    assert any(
        "ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY" in issue
        for issue in raw_issues
    )
