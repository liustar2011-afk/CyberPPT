from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cyberppt.commands.outline_audit import run_outline_audit
from cyberppt.commands.init_project import init_project


def invalid_outline(attempt: int, strategy: str) -> dict[str, object]:
    return {
        "schema": "cyberppt.outline.v1",
        "material_type": "建设方案",
        "audience": "项目组内部讨论",
        "architecture_mode": "consulting",
        "architecture_reason": "default",
        "user_requested_architecture": False,
        "source_section_weights": {},
        "pages": [],
        "retry": {"attempt": attempt, "max_attempts": 3, "strategy": strategy},
    }


class OutlineAuditCommandTests(unittest.TestCase):
    def _write(self, root: Path, payload: dict[str, object]) -> Path:
        target = root / "outline.json"
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return target

    def test_failed_attempt_persists_retry_directive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            code, report = run_outline_audit(project, self._write(root, invalid_outline(1, "consulting_default")))
            stage = project / "workbench" / "stages" / "01-analysis"
            self.assertEqual(4, code)
            self.assertEqual(2, report["remaining_attempts"])
            self.assertTrue(report["retry_directive"])
            self.assertTrue((stage / "outline-contract.json").exists())
            self.assertTrue((stage / "outline-audit.json").exists())
            self.assertTrue((stage / "proposition-graph.json").exists())
            self.assertTrue((stage / "outline-attempts" / "attempt-01.json").exists())
            readable = stage / "01-outline-readable.md"
            self.assertTrue(readable.exists())
            text = readable.read_text(encoding="utf-8")
            self.assertIn("逐页大纲（人类审阅稿）", text)
            self.assertIn("JSON 仅作为机器审计合同", text)

    def test_strict_audit_loads_explicit_source_truth_and_reports_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            payload = invalid_outline(1, "source_native")
            payload.update(
                {
                    "architecture_mode": "solution",
                    "argument_contract_mode": "strict",
                }
            )
            source_truth = root / "source-truth.json"
            source_truth.write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.source_truth.v1",
                        "argument_contract_mode": "strict",
                        "sources": [],
                        "coverage_targets": [],
                        "records": [],
                        "conclusions": [],
                        "pages": [],
                        "retry": {
                            "attempt": 1,
                            "max_attempts": 3,
                            "strategy": "section_sweep",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            code, report = run_outline_audit(
                project,
                self._write(root, payload),
                source_truth_path=source_truth,
            )

            self.assertEqual(0, code)
            self.assertEqual("strict", report["argument_contract_mode"])
            self.assertEqual(str(source_truth.resolve()), report["checked_source_truth"])
            self.assertEqual([], report["argument_graph"]["edges"])
            self.assertEqual([], report["failed_edges"])
            self.assertEqual([], report["retry_scope"])

    def test_loaded_semantic_argument_model_is_passed_to_outline_contract_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            semantic_gate = {"semantic_argument_model_sha256": "model-hash"}
            argument_model = {"schema": "cyberppt.semantic_argument_model.v1"}

            with (
                patch(
                    "cyberppt.commands.outline_audit.assert_semantic_understanding_ready",
                    return_value=semantic_gate,
                ),
                patch(
                    "cyberppt.commands.outline_audit.load_model",
                    return_value=argument_model,
                ),
                patch(
                    "cyberppt.commands.outline_audit.audit_outline",
                    return_value=[],
                ) as contract_audit,
                patch(
                    "cyberppt.commands.outline_audit.audit_outline_consumption",
                    return_value=[],
                ),
            ):
                run_outline_audit(
                    project,
                    self._write(root, invalid_outline(1, "source_native")),
                )

            self.assertIs(contract_audit.call_args.args[2], argument_model)

    def test_third_failure_escalates_instead_of_abandoning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            code, report = run_outline_audit(project, self._write(root, invalid_outline(3, "source_native")))
            self.assertEqual(5, code)
            self.assertEqual("user_decision_required", report["status"])
            self.assertGreaterEqual(len(report["options"]), 2)
            self.assertLessEqual(len(report["options"]), 3)
            self.assertTrue((project / "workbench" / "stages" / "01-analysis" / "outline-escalation.json").exists())

    def test_max_attempts_must_be_between_one_and_five(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            with self.assertRaisesRegex(ValueError, "1 through 5"):
                run_outline_audit(project, self._write(root, invalid_outline(1, "x")), max_attempts=6)

    def test_project_scaffold_contains_outline_attempt_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            init_project(project)
            self.assertTrue((project / "workbench" / "stages" / "01-analysis" / "outline-attempts").is_dir())
            self.assertTrue(
                (
                    project
                    / "workbench"
                    / "stages"
                    / "01-analysis"
                    / "source-truth-attempts"
                ).is_dir()
            )
            readme = (project / "README.md").read_text(encoding="utf-8")
            self.assertIn("outline-audit", readme)
            self.assertIn("source-truth-audit", readme)
            self.assertIn("argument_contract_mode: strict", readme)
            self.assertIn("editorial_control_mode: required", readme)
            self.assertIn("audience_question", readme)
            self.assertIn("must_not_include", readme)
            self.assertIn("split_risk", readme)
            self.assertIn("page types and claim taxonomies do not determine the page meaning", readme)
            self.assertIn("--source-truth", readme)
            self.assertIn("never a mandatory chapter template", readme)

    def test_lightweight_audit_reports_business_issues_without_control_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            model_dir = project / "workbench/stages/00-semantic-understanding"
            model_dir.mkdir(parents=True)
            (model_dir / "semantic-argument-model.json").write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.semantic_argument_model.v1",
                        "section_nodes": [],
                        "subsection_nodes": [],
                    }
                ),
                encoding="utf-8",
            )

            code, report = run_outline_audit(
                project,
                self._write(root, invalid_outline(3, "source_native")),
                lightweight=True,
            )
            stage = project / "workbench/stages/01-analysis"

            self.assertEqual(4, code)
            self.assertEqual("rewrite_required", report["status"])
            self.assertEqual("lightweight", report["mode"])
            self.assertIn("argument_graph", report)
            self.assertIn("retry_directive", report)
            self.assertNotIn("attempt", report)
            self.assertFalse((stage / "outline-audit.json").exists())
            self.assertFalse((stage / "outline-attempts").exists())
            self.assertFalse((stage / "outline-escalation.json").exists())
            self.assertFalse((stage / "proposition-graph.json").exists())


if __name__ == "__main__":
    unittest.main()
