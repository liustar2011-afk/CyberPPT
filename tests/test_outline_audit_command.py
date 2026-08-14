from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cyberppt.commands.outline_audit import run_outline_audit


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
            model_dir = project / "workbench/stages/00-semantic-understanding"
            model_dir.mkdir(parents=True)
            (model_dir / "semantic-argument-model.json").write_text("{}\n", encoding="utf-8")
            argument_model = {"schema": "cyberppt.semantic_argument_model.v1"}

            with (
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
                ) as model_audit,
            ):
                run_outline_audit(
                    project,
                    self._write(root, invalid_outline(1, "source_native")),
                )

            self.assertIs(contract_audit.call_args.args[2], argument_model)
            self.assertEqual([], contract_audit.call_args.kwargs["argument_model_issues"])
            model_audit.assert_called_once()

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

            payload = invalid_outline(3, "source_native")
            payload.pop("retry")
            code, report = run_outline_audit(
                project,
                self._write(root, payload),
            )
            stage = project / "workbench/stages/01-analysis"

            self.assertEqual(4, code)
            self.assertEqual("rewrite_required", report["status"])
            self.assertEqual("lightweight", report["mode"])
            self.assertIn("argument_graph", report)
            self.assertIn("retry_directive", report)
            self.assertNotIn("attempt", report)
            self.assertTrue((stage / "outline-audit.json").is_file())
            self.assertTrue((stage / "outline-audit.md").is_file())
            self.assertTrue((stage / "outline-human-review.md").is_file())
            self.assertFalse((stage / "outline-attempts").exists())
            self.assertFalse((stage / "outline-escalation.json").exists())
            self.assertFalse((stage / "proposition-graph.json").exists())


if __name__ == "__main__":
    unittest.main()
