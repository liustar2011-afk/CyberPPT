from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.analysis_audit import audit_deck_plan, audit_final_script
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


def test_relationship_metadata_cannot_replace_visible_reasoning() -> None:
    foundation, plan, final = _example()
    broken = copy.deepcopy(final)
    broken["slides"][0]["relationships"] = [
        {"from": "甲", "to": "乙", "relation": "甲推动乙形成闭环"}
    ]
    issues, _ = audit_final_script(broken, plan, foundation)
    assert any("AUTHOR_RELATIONSHIP_METADATA_ONLY" in issue for issue in issues)

