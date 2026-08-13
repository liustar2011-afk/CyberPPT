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
