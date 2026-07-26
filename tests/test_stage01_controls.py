from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from cyberppt.commands.outline_audit import run_outline_audit
from cyberppt.stage01_controls import (
    assert_confirmation_request_ready,
    assert_escalation_resolved,
    assert_stage01_script_approval,
    snapshot_reference_gate,
    validate_confirmation_request,
    write_confirmation_request,
    write_escalation_decision,
    write_stage01_approval,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


class Stage01ControlsTests(unittest.TestCase):
    def test_reference_gate_snapshot_includes_sha256(self) -> None:
        snapshot = snapshot_reference_gate("script")
        self.assertEqual(snapshot["schema"], "cyberppt.reference_gate.v1")
        self.assertEqual(snapshot["status"], "complete")
        names = {item["name"] for item in snapshot["files"]}
        self.assertIn("script-quality.md", names)
        for item in snapshot["files"]:
            self.assertTrue(item["present"])
            self.assertIn("sha256", item)
            self.assertEqual(len(item["sha256"]), 64)

    def test_open_escalation_blocks_until_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            escalation = (
                project
                / "workbench"
                / "stages"
                / "01-analysis"
                / "source-truth-escalation.json"
            )
            _write_json(
                escalation,
                {
                    "status": "user_decision_required",
                    "options": [
                        {
                            "id": "accept_documented_gaps",
                            "label": "保留缺口继续规划",
                        }
                    ],
                },
            )
            _write_json(
                project
                / "workbench"
                / "stages"
                / "01-analysis"
                / "source-truth-audit.json",
                {"status": "user_decision_required"},
            )
            with self.assertRaises(ValueError) as raised:
                assert_escalation_resolved(project, "source_truth")
            self.assertIn("open Stage 01 escalation", str(raised.exception))

            decision = write_escalation_decision(
                project,
                gate="source_truth",
                option_id="accept_documented_gaps",
                note="keep gaps",
            )
            self.assertTrue(decision.is_file())
            assert_escalation_resolved(project, "source_truth")

    def test_passed_audit_clears_stale_escalation_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            _write_json(
                project
                / "workbench"
                / "stages"
                / "01-analysis"
                / "source-truth-escalation.json",
                {"status": "user_decision_required", "options": []},
            )
            _write_json(
                project
                / "workbench"
                / "stages"
                / "01-analysis"
                / "source-truth-audit.json",
                {"status": "passed"},
            )
            assert_escalation_resolved(project, "source_truth")

    def test_confirmation_request_requires_three_sections(self) -> None:
        missing = validate_confirmation_request("# hi\n\n## 请回复\n\n1. ok\n")
        self.assertIn("审计摘要（或 审计状态）", missing)
        self.assertIn("开放问题（或 缺口与 caveat / 开放缺口）", missing)

        ok = validate_confirmation_request(
            "# Stage 01\n\n## 审计状态\n\n- ok\n\n## 缺口与 caveat\n\n1. gap\n\n## 请回复\n\n1. go\n"
        )
        self.assertEqual(ok, [])

    def test_write_and_approve_stage01_outline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            analysis = project / "workbench" / "stages" / "01-analysis"
            _write_json(
                analysis / "source-truth-audit.json",
                {"status": "passed", "attempt": 1, "issues": []},
            )
            _write_json(
                analysis / "outline-audit.json",
                {"status": "passed", "attempt": 1, "issues": []},
            )
            request = write_confirmation_request(project, "outline")
            self.assertTrue(request.is_file())
            assert_confirmation_request_ready(project, "outline")
            approval = write_stage01_approval(
                project, kind="outline", note="approved for test"
            )
            self.assertTrue(approval.is_file())
            self.assertIn("approve_outline", approval.read_text(encoding="utf-8"))

    def test_script_approval_is_bound_to_script_outline_and_source_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            analysis = project / "workbench" / "stages" / "01-analysis"
            script = Path(directory) / "final-script.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")
            outline = analysis / "outline.json"
            source_truth = analysis / "source-truth.json"
            analysis.mkdir(parents=True, exist_ok=True)
            outline.write_text("outline\n", encoding="utf-8")
            source_truth.write_text("source\n", encoding="utf-8")
            _write_json(
                project / "workbench/scripts/audits/script-audit.json",
                {
                    "status": "passed",
                    "input": str(script),
                    "outline": str(outline),
                    "source_truth": str(source_truth),
                },
            )
            write_confirmation_request(project, "script")
            approvals = project / "workbench/approvals"
            approvals.mkdir(parents=True, exist_ok=True)
            (approvals / "stage01-outline-approved.md").write_text("# approved\n", encoding="utf-8")
            write_stage01_approval(project, kind="script")

            assert_stage01_script_approval(project, script)
            script.write_text("## 第1页：测试\n内容已改\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match the current script"):
                assert_stage01_script_approval(project, script)

    def test_outline_audit_blocked_by_open_source_truth_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            analysis = project / "workbench" / "stages" / "01-analysis"
            outline = analysis / "outline.json"
            _write_json(
                analysis / "source-truth-escalation.json",
                {
                    "status": "user_decision_required",
                    "options": [{"id": "accept_documented_gaps", "label": "keep"}],
                },
            )
            _write_json(
                analysis / "source-truth-audit.json",
                {"status": "user_decision_required"},
            )
            _write_json(
                outline,
                {
                    "schema": "cyberppt.outline.v1",
                    "material_type": "solution",
                    "audience": "project_team",
                    "architecture_mode": "solution",
                    "architecture_reason": "formal solution workflow",
                    "source_section_weights": {},
                    "pages": [
                        {
                            "page_id": "p01",
                            "sequence": 1,
                            "page_type": "cover",
                            "title": "封面",
                        }
                    ],
                },
            )
            with self.assertRaises(ValueError) as raised:
                run_outline_audit(project, outline)
            self.assertIn("source_truth", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
