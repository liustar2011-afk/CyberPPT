from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.source_truth_audit import run_source_truth_audit
from test_source_truth_contract import valid_payload


class SourceTruthAuditCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.stage = self.project / "workbench" / "stages" / "01-analysis"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, payload: dict[str, object]) -> Path:
        path = self.root / "source-truth.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def _invalid_payload(self, attempt: int, strategy: str) -> dict[str, object]:
        payload = valid_payload()
        payload["records"][0]["quote"] = ""
        payload["retry"] = {"attempt": attempt, "max_attempts": 3, "strategy": strategy}
        return payload

    def test_failed_attempt_persists_and_changes_direction(self) -> None:
        code, report = run_source_truth_audit(
            self.project,
            self._write(self._invalid_payload(1, "section_sweep")),
        )
        self.assertEqual(4, code)
        self.assertEqual("rewrite_required", report["status"])
        self.assertEqual("structured_fact_sweep", report["retry_directive"]["strategy"])
        self.assertTrue((self.stage / "source-truth.json").exists())
        self.assertTrue((self.stage / "source-truth-audit.json").exists())
        self.assertTrue((self.stage / "source-truth-attempts" / "attempt-01.json").exists())

    def test_third_failure_preserves_best_result_and_escalates(self) -> None:
        code, report = run_source_truth_audit(
            self.project,
            self._write(self._invalid_payload(3, "traceability_rebuild")),
        )
        self.assertEqual(5, code)
        self.assertEqual("user_decision_required", report["status"])
        self.assertTrue((self.stage / "source-truth-escalation.json").exists())
        self.assertTrue((self.stage / "source-truth.json").exists())
        self.assertGreaterEqual(len(report["options"]), 2)

    def test_passed_contract_generates_readable_markdown(self) -> None:
        code, report = run_source_truth_audit(self.project, self._write(valid_payload()))
        rendered = (self.stage / "00-source-analysis.md").read_text(encoding="utf-8")
        self.assertEqual(0, code)
        self.assertEqual("passed", report["status"])
        self.assertIn("# 源材料分析与 Source Truth Map", rendered)
        self.assertIn("| Source ID | 类型 | 优先级 |", rendered)
        self.assertIn("## 覆盖与审计结论", rendered)
        self.assertIn("## 源材料凭据", rendered)
        self.assertIn("S001", rendered)

    def test_max_attempts_must_be_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "1 through 5"):
            run_source_truth_audit(
                self.project,
                self._write(valid_payload()),
                max_attempts=6,
            )

    def test_lightweight_audit_keeps_fact_checks_without_control_writes(self) -> None:
        semantic = self.project / "workbench/stages/00-semantic-understanding"
        source_map = self.project / "workbench/stages/00-source-map"
        semantic.mkdir(parents=True)
        source_map.mkdir(parents=True)
        (semantic / "semantic-argument-model.json").write_text(
            json.dumps(
                {
                    "schema": "cyberppt.semantic_argument_model.v1",
                    "document_thesis": {
                        "statement": "主论点",
                        "argument_weight": "core",
                        "evidence_refs": ["S001"],
                    },
                    "section_nodes": [],
                    "subsection_nodes": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (source_map / "source-units.jsonl").write_text(
            json.dumps({"unit_id": "SU-001", "text": "原文"}, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        code, report = run_source_truth_audit(
            self.project,
            self._write(valid_payload()),
            lightweight=True,
        )

        self.assertEqual(0, code)
        self.assertEqual("lightweight", report["mode"])
        self.assertNotIn("attempt", report)
        self.assertFalse(any(key.endswith("sha256") for key in report))
        self.assertEqual("passed", report["semantic_evidence_cross_audit"]["status"])
        self.assertFalse((self.stage / "source-truth-audit.json").exists())
        self.assertFalse((self.stage / "source-truth-attempts").exists())
        self.assertFalse((self.stage / "source-truth-escalation.json").exists())
        self.assertFalse((self.stage / "00-source-analysis.md").exists())


if __name__ == "__main__":
    unittest.main()
