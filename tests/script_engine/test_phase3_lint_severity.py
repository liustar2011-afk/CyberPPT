from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.analysis_audit import audit_final_script
from script_engine.contracts import lint_final_script
from script_engine.quality_policy import ADVISORY, BLOCKER, classify_issue, partition_issues


ROOT = Path(__file__).resolve().parents[2]


def _legacy() -> dict:
    return json.loads(
        (ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8")
    )


def _v11() -> dict:
    return json.loads(
        (ROOT / "examples" / "final-script-v1.1.example.json").read_text(encoding="utf-8")
    )


def _analysis_triplet() -> tuple[dict, dict, dict]:
    foundation = json.loads(
        (ROOT / "examples" / "foundation.example.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (ROOT / "examples" / "deck-plan.example.json").read_text(encoding="utf-8")
    )
    final = _legacy()
    plan["authoring_mode"] = "analytical"
    final["deck"]["authoring_mode"] = "analytical"
    return foundation, plan, final


def test_generic_business_object_hint_remains_visible_but_nonblocking() -> None:
    payload = copy.deepcopy(_legacy())
    payload["slides"][0]["core_message"] = "本单位承担能力建设和标准验证。"
    payload["slides"][0]["onscreen"] = [
        {"heading": "推进相关工作", "text": "统一目录、身份和标识"}
    ]

    findings = lint_final_script(payload)
    hints = [item for item in findings if "underspecified-business-object" in item]
    blockers, advisories = partition_issues(findings)

    assert len(hints) == 2
    assert not any("underspecified-business-object" in item for item in blockers)
    assert sum("underspecified-business-object" in item for item in advisories) == 2


def test_semantic_heading_predicate_guess_is_advisory() -> None:
    payload = copy.deepcopy(_legacy())
    payload["slides"][0]["onscreen"] = [
        {"heading": "建设框架", "text": "覆盖相关工作范围"}
    ]

    findings = lint_final_script(payload)
    heading_findings = [item for item in findings if "ONSCREEN_HEADING_INCOMPLETE" in item]

    assert heading_findings
    assert all(classify_issue(item)["severity"] == ADVISORY for item in heading_findings)


def test_structural_author_contract_error_remains_blocking() -> None:
    payload = copy.deepcopy(_legacy())
    payload["slides"][0]["argument"]["pattern"] = "unregistered-topology"

    findings = lint_final_script(payload)
    structural = [
        item for item in findings if "AUTHOR_ARGUMENT_PATTERN_UNREGISTERED" in item
    ]

    assert structural
    assert all(classify_issue(item)["severity"] == BLOCKER for item in structural)


def test_final_script_11_object_items_are_scanned_for_delivery_cleanliness() -> None:
    payload = _v11()
    target_item = None
    for module in payload["slides"][0]["onscreen"]:
        for item in module.get("items") or []:
            if isinstance(item, dict):
                target_item = item
                break
        if target_item is not None:
            break
    assert target_item is not None
    target_item["text"] = "本页用于展示后台逻辑。"

    findings = lint_final_script(payload)
    meta = [item for item in findings if "audience-facing-meta" in item]

    assert meta
    assert any(".items[" in item and ".text" in item for item in meta)
    assert all(classify_issue(item)["severity"] == BLOCKER for item in meta)


def test_warning_phrasing_registry_is_applied_by_central_policy() -> None:
    finding = "slides.0 (P01).full_copy: [restating-aside] review — matched '也就是说'"
    assert classify_issue(finding)["severity"] == ADVISORY


def test_progression_regex_is_review_only_in_final_semantic_audit() -> None:
    foundation, plan, final = _analysis_triplet()
    plan["pages"][0]["analysis_basis"] = {"model": "classification"}
    final["slides"][0]["full_copy"] += " A事项与B事项依次递进。"

    issues, warnings = audit_final_script(final, plan, foundation)

    assert not any("FINAL_PROGRESSION_HEURISTIC" in item for item in issues)
    assert any("FINAL_PROGRESSION_HEURISTIC" in item for item in warnings)


def test_optionality_regex_is_review_only_in_final_semantic_audit() -> None:
    foundation, plan, final = _analysis_triplet()
    foundation["facts"][0]["statement"] = "方案可以独立采用，也可以随着合作逐步深化。"

    issues, warnings = audit_final_script(final, plan, foundation)

    assert not any("FINAL_OPTIONALITY_HEURISTIC" in item for item in issues)
    assert any("FINAL_OPTIONALITY_HEURISTIC" in item for item in warnings)


def test_group_strength_wording_is_review_only_in_final_semantic_audit() -> None:
    foundation, plan, final = _analysis_triplet()
    final["slides"][0]["core_message"] = "所有事项已完成。"

    issues, warnings = audit_final_script(final, plan, foundation)

    assert not any("FINAL_GROUP_STRENGTH_HEURISTIC" in item for item in issues)
    assert any("FINAL_GROUP_STRENGTH_HEURISTIC" in item for item in warnings)


def test_gap_regex_is_review_only_in_final_semantic_audit() -> None:
    foundation, plan, final = _analysis_triplet()
    final["slides"][0]["core_message"] = "目前距离目标还有明显缺口。"

    issues, warnings = audit_final_script(final, plan, foundation)

    assert not any("FINAL_GAP_HEURISTIC" in item for item in issues)
    assert any("FINAL_GAP_HEURISTIC" in item for item in warnings)
