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

    def test_atomicity_warning_does_not_change_audit_status_or_mutate_inputs(self) -> None:
        semantic = self.project / "workbench/stages/00-semantic-understanding"
        source_map = self.project / "workbench/stages/00-source-map"
        semantic.mkdir(parents=True)
        source_map.mkdir(parents=True)
        (semantic / "semantic-argument-model.json").write_text(
            json.dumps({"schema": "cyberppt.semantic_argument_model.v1", "document_thesis": {"statement": "主论点", "argument_weight": "core", "evidence_refs": ["S001"]}, "section_nodes": [], "subsection_nodes": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        (source_map / "source-units.jsonl").write_text(json.dumps({"unit_id": "SU-001", "text": "原文"}, ensure_ascii=False) + "\n", encoding="utf-8")
        payload = valid_payload()
        payload["argument_contract_mode"] = "legacy"
        payload["records"][0]["statement"] = "甲；乙；丙；丁；戊；己；庚；辛；壬；癸；" * 12
        path = self._write(payload)
        before_truth = path.read_bytes()
        before_model = (semantic / "semantic-argument-model.json").read_bytes()

        code, report = run_source_truth_audit(self.project, path)

        self.assertEqual(0, code)
        self.assertEqual("passed", report["status"])
        self.assertGreater(report["warning_count"], 0)
        self.assertEqual(before_truth, path.read_bytes())
        self.assertEqual(before_model, (semantic / "semantic-argument-model.json").read_bytes())
        self.assertNotIn(payload["records"][0]["statement"], json.dumps(report, ensure_ascii=False))

    def test_chapter_placement_diagnostic_is_advisory_and_does_not_mutate_inputs(self) -> None:
        semantic = self.project / "workbench/stages/00-semantic-understanding"
        source_map = self.project / "workbench/stages/00-source-map"
        semantic.mkdir(parents=True)
        source_map.mkdir(parents=True)
        model_path = semantic / "semantic-argument-model.json"
        model_path.write_text(
            json.dumps({
                "schema": "cyberppt.semantic_argument_model.v1",
                "document_thesis": {"statement": "主论点", "argument_weight": "core", "evidence_refs": ["S001"]},
                "section_nodes": [],
                "subsection_nodes": [{"id": "node-mechanism", "source_heading": "运行机制"}],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        (source_map / "source-units.jsonl").write_text(
            json.dumps({"unit_id": "SU-A", "heading_path": ["实施保障"]}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        outline_path = self.stage / "outline.json"
        outline_path.parent.mkdir(parents=True, exist_ok=True)
        outline_path.write_text(
            json.dumps({
                "schema": "cyberppt.outline.v1",
                "material_type": "方案",
                "audience": "负责人",
                "architecture_mode": "solution",
                "architecture_reason": "测试",
                "source_section_weights": {},
                "pages": [{
                "page_type": "content",
                "chapter_id": "mechanism",
                "source_argument_node_ids": ["node-mechanism"],
                }],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        payload = valid_payload()
        payload["records"][0].update({
            "semantic_node_ids": ["node-mechanism"],
            "source_unit_refs": ["SU-A"],
        })
        truth_path = self._write(payload)
        before_truth = truth_path.read_bytes()
        before_model = model_path.read_bytes()
        before_outline = outline_path.read_bytes()

        code, report = run_source_truth_audit(self.project, truth_path)

        self.assertEqual(0, code)
        self.assertEqual("passed", report["status"])
        self.assertEqual(1, report["repair_summary"]["chapter_placement_suggestions"])
        self.assertEqual(
            "suggest_reporting_rehome",
            report["source_chapter_placement_diagnostics"][0]["outcome"],
        )
        self.assertEqual(before_truth, truth_path.read_bytes())
        self.assertEqual(before_model, model_path.read_bytes())
        self.assertEqual(before_outline, outline_path.read_bytes())

    def test_repair_summary_counts_uncovered_protected_source_units(self) -> None:
        semantic = self.project / "workbench/stages/00-semantic-understanding"
        source_map = self.project / "workbench/stages/00-source-map"
        semantic.mkdir(parents=True)
        source_map.mkdir(parents=True)
        (semantic / "semantic-argument-model.json").write_text(
            json.dumps(
                {
                    "schema": "cyberppt.semantic_argument_model.v1",
                    "interpretation_contract_mode": "strict",
                    "document_thesis": {
                        "statement": "主论点",
                        "argument_weight": "core",
                        "evidence_refs": ["SU-001"],
                    },
                    "section_nodes": [],
                    "subsection_nodes": [{
                        "id": "sub-01-01",
                        "source_heading": "建设基础",
                        "argument_weight": "core",
                        "evidence_refs": ["SU-001", "SU-002"],
                    }],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (source_map / "source-units.jsonl").write_text(
            "\n".join(
                json.dumps({"unit_id": unit_id, "text": "原文"}, ensure_ascii=False)
                for unit_id in ("SU-001", "SU-002")
            ) + "\n",
            encoding="utf-8",
        )
        payload = valid_payload()
        record = payload["records"][0]
        record.update({
            "claim_origin": "source_explicit",
            "semantic_node_ids": ["sub-01-01"],
            "source_unit_refs": ["SU-001"],
        })

        _code, report = run_source_truth_audit(self.project, self._write(payload))

        self.assertEqual(1, report["repair_summary"]["uncovered_source_units"])

    def test_repair_summary_counts_each_diagnostic_category_end_to_end(self) -> None:
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
                        "evidence_refs": ["SU-404"],
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
        payload = valid_payload()
        payload["argument_contract_mode"] = "legacy"
        driver = payload["records"][0]
        driver.update({
            "priority": "P2",
            "argument_duty": "driver",
            "semantic_node_ids": ["N001"],
            "source_unit_refs": ["SU-001"],
            "statement": "甲；乙；丙；丁；戊；己；庚；辛；壬；癸；" * 12,
        })
        boundary = dict(driver)
        boundary.update({
            "id": "S002",
            "priority": "P0",
            "argument_duty": "boundary",
            "source_unit_refs": ["SU-002"],
            "statement": "仅说明实施边界。",
            "semantic_units": [{"text": "仅说明实施边界。", "claim_role": "fact"}],
        })
        payload["records"].append(boundary)

        _code, report = run_source_truth_audit(self.project, self._write(payload))

        self.assertEqual(1, report["repair_summary"]["unresolved_core_claims"])
        self.assertEqual(1, report["repair_summary"]["atomic_split_suggestions"])
        self.assertEqual(1, report["repair_summary"]["priority_review_suggestions"])

    def test_repair_summary_deduplicates_shared_uncovered_source_units(self) -> None:
        semantic = self.project / "workbench/stages/00-semantic-understanding"
        source_map = self.project / "workbench/stages/00-source-map"
        semantic.mkdir(parents=True)
        source_map.mkdir(parents=True)
        (semantic / "semantic-argument-model.json").write_text(
            json.dumps(
                {
                    "schema": "cyberppt.semantic_argument_model.v1",
                    "interpretation_contract_mode": "strict",
                    "section_nodes": [],
                    "subsection_nodes": [
                        {
                            "id": "sub-01-01",
                            "source_heading": "建设基础",
                            "argument_weight": "core",
                            "evidence_refs": ["SU-001", "SU-002"],
                        },
                        {
                            "id": "sub-01-02",
                            "source_heading": "建设条件",
                            "argument_weight": "core",
                            "evidence_refs": ["SU-001", "SU-002"],
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (source_map / "source-units.jsonl").write_text(
            "\n".join(
                json.dumps({"unit_id": unit_id, "text": "原文"}, ensure_ascii=False)
                for unit_id in ("SU-001", "SU-002")
            )
            + "\n",
            encoding="utf-8",
        )
        payload = valid_payload()
        payload["records"][0].update(
            {
                "claim_origin": "source_explicit",
                "semantic_node_ids": ["sub-01-01", "sub-01-02"],
                "source_unit_refs": ["SU-001"],
            }
        )

        _code, report = run_source_truth_audit(self.project, self._write(payload))

        self.assertEqual(1, report["repair_summary"]["uncovered_source_units"])


if __name__ == "__main__":
    unittest.main()
