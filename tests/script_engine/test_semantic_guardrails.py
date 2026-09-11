from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.analysis_audit import audit_deck_plan, audit_final_script
from script_engine.analysis_audits.final_fidelity import (
    faithful_relation_promotion_issues,
    faithful_semantic_addition_issues,
)
from script_engine.contracts import validate_deck_plan


ROOT = Path(__file__).resolve().parents[2]


def _example() -> tuple[dict, dict, dict]:
    foundation = json.loads((ROOT / "examples/foundation.example.json").read_text(encoding="utf-8"))
    plan = json.loads((ROOT / "examples/deck-plan.example.json").read_text(encoding="utf-8"))
    final = json.loads((ROOT / "examples/final-script.example.json").read_text(encoding="utf-8"))
    return foundation, plan, final


def test_schema_rejects_author_fields_in_deck_plan() -> None:
    _, plan, _ = _example()
    plan["pages"][0]["message"] = "PLAN 不得预写作者结论"
    issues = validate_deck_plan(plan)
    assert any("Additional properties" in issue and "message" in issue for issue in issues)


def test_audit_rejects_any_non_v2_lean_plan() -> None:
    foundation, plan, _ = _example()
    plan["plan_contract_version"] = 1
    plan["planning_profile"] = "strict"
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("PLAN_CONTRACT_VERSION_INVALID" in issue for issue in issues)
    assert any("PLAN_PROFILE_INVALID" in issue for issue in issues)


def test_content_page_requires_known_source_boundary() -> None:
    foundation, plan, _ = _example()
    plan["pages"][0]["source_refs"] = ["UNKNOWN"]
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("LEAN_SOURCE_REF_UNKNOWN" in issue for issue in issues)


def test_external_plan_rejects_internal_only_source_boundary() -> None:
    foundation, plan, _ = _example()
    foundation["facts"][0]["visibility"] = "internal_only"
    plan["audience_scope"] = "external"
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("internal-only evidence" in issue for issue in issues)


def test_clean_v2_lean_example_passes_plan_and_final_audits() -> None:
    foundation, plan, final = _example()
    plan_issues, _ = audit_deck_plan(plan, foundation)
    final_issues, _ = audit_final_script(final, plan, foundation)
    assert plan_issues == []
    assert final_issues == []


def test_relationship_wording_and_overlap_checks_are_review_only() -> None:
    foundation, plan, final = _example()
    broken = copy.deepcopy(final)
    broken["slides"][0]["relationships"] = [
        {"from": "甲", "to": "乙", "relation": "甲推动乙形成闭环"}
    ]
    issues, warnings = audit_final_script(broken, plan, foundation)
    assert any(
        "AUTHOR_RELATIONSHIP_METADATA_ONLY" in issue
        or "FAITHFUL_RELATION_PROMOTED" in issue
        for issue in warnings
    )
    assert not any(
        "AUTHOR_RELATIONSHIP_METADATA_ONLY" in issue
        or "FAITHFUL_RELATION_PROMOTED" in issue
        for issue in issues
    )


def test_faithful_semantic_addition_audit_rejects_objective_additions_and_voice_drift() -> None:
    evidence = [
        {
            "id": "F1",
            "statement": "计划开展场景梳理。",
            "source_refs": ["SU-1"],
        }
    ]
    slide = {
        "title": "场景梳理",
        "full_copy": "材料指出，已完成《新增管理办法》并覆盖8类场景。",
        "onscreen": [
            {"heading": "场景梳理", "text": "已完成8类场景梳理"}
        ],
    }

    issues = faithful_semantic_addition_issues(slide, evidence, {})
    assert any("FAITHFUL_OUTSIDE_NARRATOR" in issue for issue in issues)
    assert any("FAITHFUL_STATUS_PROMOTED" in issue for issue in issues)
    assert any("FAITHFUL_FORMAL_INSTRUMENT_ADDED" in issue for issue in issues)
    assert any("FAITHFUL_NUMBER_ADDED" in issue for issue in issues)


def test_faithful_semantic_addition_audit_rejects_new_obligation_strength() -> None:
    evidence = [{"id": "F1", "statement": "可开展数据共享。"}]
    slide = {
        "full_copy": "必须开展数据共享。",
        "onscreen": [{"heading": "数据共享", "text": "必须开展数据共享"}],
    }

    issues = faithful_semantic_addition_issues(slide, evidence, {})
    assert any("FAITHFUL_MODALITY_PROMOTED" in issue for issue in issues)


def test_faithful_relation_audit_rejects_new_closed_loop_and_progression() -> None:
    evidence = [
        {"id": "F1", "statement": "A事项与B事项并列开展。"},
    ]
    slide = {
        "full_copy": "A事项与B事项形成闭环并依次递进。",
        "onscreen": [{"heading": "A事项与B事项", "text": "形成闭环并依次递进"}],
    }

    issues = faithful_relation_promotion_issues(slide, evidence)
    assert any("FAITHFUL_RELATION_PROMOTED" in issue and "闭环" in issue for issue in issues)
    assert any("FAITHFUL_RELATION_PROMOTED" in issue and "递进" in issue for issue in issues)


def test_faithful_relation_audit_allows_source_explicit_relationship() -> None:
    evidence = [
        {"id": "F1", "statement": "A事项与B事项形成闭环。"},
    ]
    slide = {
        "full_copy": "A事项与B事项形成闭环。",
        "onscreen": [{"heading": "A事项与B事项", "text": "形成闭环"}],
    }

    assert faithful_relation_promotion_issues(slide, evidence) == []
