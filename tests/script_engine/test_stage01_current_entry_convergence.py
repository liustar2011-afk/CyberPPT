from __future__ import annotations

import copy
import json
from pathlib import Path

import script_engine.analysis_audit as analysis_audit_facade
import script_engine.analysis_audits as analysis_audits
from script_engine.audit_reports import final_audit_report
from script_engine.semantic_contract import audit_final_script_semantic_contract


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"


def _current_contract_examples() -> tuple[dict, dict, dict]:
    final_script = json.loads(
        (EXAMPLES / "final-script-v1.1.example.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (EXAMPLES / "deck-plan.example.json").read_text(encoding="utf-8")
    )
    foundation = json.loads(
        (EXAMPLES / "foundation.example.json").read_text(encoding="utf-8")
    )
    return final_script, plan, foundation


def _authorization_blocker_case() -> tuple[dict, dict, dict]:
    final_script, plan, foundation = _current_contract_examples()
    final_script = copy.deepcopy(final_script)
    plan = copy.deepcopy(plan)
    final_script["deck"]["authoring_mode"] = "analytical"
    plan["authoring_mode"] = "faithful"
    return final_script, plan, foundation


def test_current_semantic_api_entries_have_identical_blocking_results() -> None:
    final_script, plan, foundation = _authorization_blocker_case()

    semantic_issues, semantic_warnings, _ = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )
    package_issues, package_warnings = analysis_audits.audit_final_script(
        final_script,
        plan,
        foundation,
    )
    facade_issues, facade_warnings = analysis_audit_facade.audit_final_script(
        final_script,
        plan,
        foundation,
    )

    assert semantic_issues
    assert any("AUTHORING_MODE_NOT_AUTHORIZED" in issue for issue in semantic_issues)
    assert set(package_issues) == set(semantic_issues)
    assert set(facade_issues) == set(semantic_issues)
    assert set(package_warnings) == set(semantic_warnings)
    assert set(facade_warnings) == set(semantic_warnings)


def test_current_file_report_adds_preflight_gate_without_changing_semantic_blockers(
    tmp_path: Path,
) -> None:
    final_script, plan, foundation = _authorization_blocker_case()
    semantic_issues, semantic_warnings, _ = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    final_path = tmp_path / "final-script.json"
    plan_path = tmp_path / "deck-plan.json"
    foundation_path = tmp_path / "foundation.json"
    final_path.write_text(json.dumps(final_script, ensure_ascii=False), encoding="utf-8")
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    foundation_path.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")

    report, exit_code = final_audit_report(
        final_path,
        plan_path,
        foundation_path,
    )

    assert exit_code == 1
    assert set(semantic_issues) <= set(report["issues"])
    gate_issues = [
        issue for issue in report["issues"] if issue.startswith("AUTHOR_PREFLIGHT_GATE:")
    ]
    assert gate_issues
    assert any("AUTHOR_PREFLIGHT_SOURCE_INDEX_MISSING" in issue for issue in gate_issues)
    assert report["author_preflight"]["status"] == "failed"
    assert set(report["warnings"]) == set(semantic_warnings)
