import json
from pathlib import Path

from script_engine.analysis_audits.final_fidelity import (
    faithful_relation_promotion_issues,
)
from script_engine.contracts import validate_deck_plan, validate_final_script
from script_engine.source_index_validation import validate_foundation_semantic_promotions


def test_contracts_accept_explicit_authoring_modes() -> None:
    plan = {
        "communication_goal": "忠实整理",
        "plan_contract_version": 2,
        "planning_profile": "lean",
        "authoring_mode": "faithful",
        "source_structure_mode": "preserve",
        "chapters": [],
        "pages": [
            {
                "id": "p01",
                "title": "标题",
                "question": "讲什么？",
                "logic": "忠实呈现",
                "page_role": "content",
                "source_refs": ["ST1"],
            }
        ],
    }
    final = json.loads(
        (Path(__file__).resolve().parents[1] / "examples" / "final-script.example.json")
        .read_text(encoding="utf-8")
    )
    final.setdefault("deck", {})["authoring_mode"] = "analytical"

    assert validate_deck_plan(plan) == []
    assert validate_final_script(final) == []


def test_faithful_mode_rejects_author_created_necessity() -> None:
    slide = {
        "core_message": "首批场景建设需要在国家节点下形成实际应用",
    }
    evidence = [
        {"statement": "为确保达到验收时间节点要求，组织开展首批场景建设工作。"},
        {"statement": "以实际应用牵引基础设施完善。"},
    ]

    issues = faithful_relation_promotion_issues(slide, evidence)

    assert any(
        "FAITHFUL_RELATION_PROMOTED" in issue and "需要" in issue
        for issue in issues
    )


def test_faithful_mode_accepts_source_explicit_relation() -> None:
    slide = {"core_message": "以实际应用牵引基础设施完善"}
    evidence = [{"statement": "坚持以实际应用牵引基础设施完善。"}]

    assert faithful_relation_promotion_issues(slide, evidence) == []


def test_foundation_rejects_reversed_acceptance_relationship() -> None:
    foundation = {
        "document_semantics": {
            "primary_thesis": "首批场景建设为国家验收节点提供实际应用支撑",
            "author_purpose": "组织开展首批场景建设",
            "argument_method": [],
        },
        "facts": [],
        "constraints": [],
        "argument_nodes": [],
    }
    source_index = {
        "units": [
            {
                "unit_id": "SU-1",
                "text": "为确保达到国家能源局初验时间节点要求，组织开展首批场景建设工作。",
            }
        ]
    }

    issues = validate_foundation_semantic_promotions(foundation, source_index)

    assert any("FOUNDATION_SEMANTIC_RELATION_PROMOTED" in issue for issue in issues)
