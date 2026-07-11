from __future__ import annotations

import json
from pathlib import Path

from cyberppt.commands.analysis_expression_gate import GATE_ORDER, approve_analysis_artifact
from cyberppt.commands.init_project import init_project
from cyberppt.phase1 import workflow


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "phase1"


def test_phase1_five_gate_fixture_flow(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    init_project(project)
    responses = [
        (FIXTURES / "source_analysis_response.json").read_text(encoding="utf-8"),
        (FIXTURES / "reporting_direction_response.json").read_text(encoding="utf-8"),
        (FIXTURES / "report_structure_response.json").read_text(encoding="utf-8"),
        (FIXTURES / "page_design_response.json").read_text(encoding="utf-8"),
        (FIXTURES / "business_script_response.json").read_text(encoding="utf-8"),
    ]
    monkeypatch.setattr(workflow, "run_codex_text", lambda **kwargs: responses.pop(0))

    for gate in GATE_ORDER:
        source = FIXTURES / "source_extract.md" if gate == "source_analysis" else None
        workflow.prepare_phase1_prompt(project, gate, source)
        result = workflow.generate_phase1_candidate(project, gate, model="fixture-model")
        assert result["status"] == "candidate_ready"
        pending = workflow.stage_phase1_candidate(
            project,
            gate,
            str(result["recommendation"]),
            list(result["options"]),
        )
        assert pending.exists()
        approve_analysis_artifact(project, gate, str(result["options"][0]["id"]))

    status = workflow.get_phase1_status(project)
    assert all(data["status"] == "candidate_ready" for data in status["gates"].values())
    for gate in GATE_ORDER:
        approval = project / "workbench/analysis_expression" / f"{gate}.approved.json"
        assert json.loads(approval.read_text(encoding="utf-8"))["approved"] is True
