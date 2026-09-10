from __future__ import annotations

import json
from pathlib import Path

from script_engine.audit_reports import final_audit_report


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"


def test_final_audit_report_surfaces_structured_role_diagnostic(tmp_path: Path) -> None:
    final_script = json.loads(
        (EXAMPLES / "final-script-v1.1.example.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (EXAMPLES / "deck-plan.example.json").read_text(encoding="utf-8")
    )
    foundation = json.loads(
        (EXAMPLES / "foundation.example.json").read_text(encoding="utf-8")
    )
    foundation["facts"][1]["argument_duty"] = "response"

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
    assert any(
        "[EVIDENCE_ROLE_INCOMPATIBLE]" in issue for issue in report["issues"]
    )
    assert any(
        finding["code"] == "EVIDENCE_ROLE_INCOMPATIBLE"
        and finding["severity"] == "blocking"
        and finding["evidence_refs"] == ["F2"]
        for finding in report["semantic_diagnostics"]
    )
