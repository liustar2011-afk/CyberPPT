from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.outline_contract import audit_outline
from cyberppt.semantic_cross_audit import semantic_evidence_cross_issues
from cyberppt.semantic_understanding import (
    SEMANTIC_ARGUMENT_MODEL,
    SEMANTIC_ARTIFACT,
    run_semantic_understanding_audit,
)
from cyberppt.source_argument_model import SCHEMA
from cyberppt.source_document_map import (
    SOURCE_HEADING_TREE,
    SOURCE_UNITS,
    prepare_source_map,
)
from cyberppt.source_truth_contract import audit_source_truth, load_source_truth
from cyberppt.stage01_compiler import compile_outline_draft, compile_source_truth


class Stage01CompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "project"
        init_project(self.project, lightweight=True)
        (self.project / "source" / "material.md").write_text(
            "# 建设方案\n\n## 建设基础\n\n现有行业数据资源和专业能力构成首期建设基础。\n",
            encoding="utf-8",
        )
        prepare_source_map(self.project)
        headings = json.loads(
            (self.project / SOURCE_HEADING_TREE).read_text(encoding="utf-8")
        )["headings"]
        units = [
            json.loads(line)
            for line in (self.project / SOURCE_UNITS).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        paragraph = next(item for item in units if item["kind"] != "heading")
        top, child = headings
        evidence = paragraph["unit_id"]
        model = {
            "schema": SCHEMA,
            "version": 1,
            "interpretation_contract_mode": "strict",
            "source_truth_projection_mode": "required",
            "document_semantics": {
                "document_role": "建设方案",
                "subject_of_report": "行业数据资源与专业能力建设",
                "primary_thesis": "现有行业数据资源和专业能力构成首期建设基础。",
                "decision_boundary": "后续范围和责任仍需确认，不得写成既定承诺。",
                "author_purpose": "推动相关方理解现有基础并确认后续建设动作。",
                "argument_method": [{"statement": "先说明建设基础，再讨论后续动作。", "source_refs": [evidence]}],
                "supporting_basis": [{"statement": "正文列明行业数据资源和专业能力。", "source_refs": [evidence]}],
                "business_objects": ["行业数据资源", "专业能力"],
                "scope": "首期建设基础及其后续确认事项。",
                "decision_intent": "理解现有基础并确认后续动作。",
            },
            "document_thesis": {
                "statement": "现有行业数据资源和专业能力构成首期建设基础。",
                "argument_role": "thesis",
                "argument_weight": "core",
                "status": "existing",
                "evidence_refs": [evidence],
                "actor_refs": ["建设相关方"],
                "claim_origin": "source_explicit",
            },
            "heading_semantic_cards": [
                {
                    "heading_id": top["heading_id"],
                    "source_unit_id": top["unit_id"],
                    "source_heading": top["title"],
                    "level": top["level"],
                    "semantic_function": "提出建设方案总题",
                    "author_claim": "建设方案需要说明建设基础。",
                    "argument_role": "foundation",
                    "argument_weight": "core",
                    "claim_origin": "source_explicit",
                    "evidence_refs": [top["unit_id"]],
                },
                {
                    "heading_id": child["heading_id"],
                    "source_unit_id": child["unit_id"],
                    "source_heading": child["title"],
                    "level": child["level"],
                    "semantic_function": "说明建设基础",
                    "author_claim": "现有资源和能力构成建设基础。",
                    "argument_role": "foundation",
                    "argument_weight": "supporting",
                    "claim_origin": "source_explicit",
                    "evidence_refs": [child["unit_id"]],
                },
            ],
            "section_nodes": [
                {
                    "id": "c01",
                    "source_heading_id": top["heading_id"],
                    "source_heading": top["title"],
                    "section_thesis": "建设方案以现有资源和能力为基础。",
                    "argument_role": "foundation",
                    "argument_weight": "core",
                    "level": 1,
                    "status": "existing",
                    "evidence_refs": [evidence],
                    "actor_refs": ["建设相关方"],
                    "primary_consumer": "chapter-1",
                    "subsection_ids": ["c01-s01"],
                    "allowed_merges": [],
                    "claim_origin": "source_explicit",
                }
            ],
            "subsection_nodes": [
                {
                    "id": "c01-s01",
                    "parent_id": "c01",
                    "source_heading_id": child["heading_id"],
                    "source_heading": child["title"],
                    "section_thesis": "现有行业数据资源和专业能力构成首期建设基础。",
                    "argument_role": "foundation",
                    "argument_weight": "supporting",
                    "level": 2,
                    "status": "existing",
                    "evidence_refs": [evidence],
                    "actor_refs": ["建设相关方"],
                    "primary_consumer": "建设基础",
                    "allowed_merges": [],
                    "claim_origin": "source_explicit",
                }
            ],
            "argument_relations": [
                {
                    "id": "r01",
                    "from": "c01-s01",
                    "to": "c01",
                    "relation": "supports",
                    "weight_effect": "none",
                    "explanation": "建设基础支撑方案总题。",
                    "evidence_refs": [evidence],
                    "claim_origin": "source_explicit",
                }
            ],
            "argument_weighting": {
                "definition": "core保留总题，supporting保留展开事项。",
                "core_node_ids": ["c01"],
                "supporting_node_ids": ["c01-s01"],
                "detail_node_ids": [],
                "constraint_node_ids": [],
                "review_notes": [],
            },
            "mece_rules": {
                "partition_basis": "按来源标题层级划分。",
                "exhaustive_scope": "覆盖建设方案和建设基础。",
                "overlap_policy": "父子节点通过支持关系连接。",
                "groups": [
                    {
                        "parent_id": "c01",
                        "node_ids": ["c01-s01", "c01"],
                        "partition_basis": "按来源子标题划分。",
                        "exhaustive_scope": "覆盖建设基础正文。",
                        "overlap_policy": "一个来源事项只保留一个主要语义归属。",
                    }
                ],
                "review_notes": [],
            },
            "inference_register": [],
            "concept_occurrence_graph": {"concepts": [], "relations": [], "review_notes": []},
            "semantic_content_unit_coverage_mode": "required",
            "source_coverage": {
                "assignments": [
                    {
                        "source_unit_refs": [evidence],
                        "semantic_node_ids": ["c01", "c01-s01"],
                        "summary": "正文说明首期建设基础。",
                        "atomic_items": [
                            {
                                "item_id": "AI-001",
                                "statement": "现有行业数据资源和专业能力构成首期建设基础。",
                                "source_unit_refs": [evidence],
                                "claim_role": "foundation",
                                "evidence_role": "fact",
                                "evidence_priority": "P0",
                                "importance": "core",
                                "status": "existing",
                                "claim_origin": "source_explicit",
                                "coverage_anchors": ["行业数据资源", "专业能力"],
                                "actors": ["建设相关方"],
                                "conditions": ["首期建设"],
                                "numeric_facts": [],
                            },
                            {
                                "item_id": "AI-002",
                                "statement": "现有专业能力构成首期建设基础。",
                                "source_unit_refs": [evidence],
                                "claim_role": "foundation",
                                "evidence_role": "fact",
                                "evidence_priority": "P1",
                                "importance": "constraint",
                                "status": "existing",
                                "claim_origin": "source_explicit",
                                "coverage_anchors": ["专业能力", "首期建设基础"],
                                "actors": ["建设相关方"],
                                "conditions": ["首期建设"],
                                "numeric_facts": [],
                            },
                            {
                                "item_id": "AI-003",
                                "statement": "行业数据资源用于首期建设基础。",
                                "source_unit_refs": [evidence],
                                "claim_role": "foundation",
                                "evidence_role": "fact",
                                "evidence_priority": "P2",
                                "importance": "detail",
                                "status": "existing",
                                "claim_origin": "source_explicit",
                                "coverage_anchors": ["行业数据资源", "首期建设基础"],
                                "actors": ["建设相关方"],
                                "conditions": ["首期建设"],
                                "numeric_facts": [],
                            }
                        ],
                    }
                ],
                "intentional_omissions": [],
                "review_notes": [],
            },
            "source_gaps": [],
        }
        model_path = self.project / SEMANTIC_ARGUMENT_MODEL
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
        self.model = model
        self.unit_ids = {item["unit_id"] for item in units}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_lightweight_semantic_check_renders_review_from_canonical_model(self) -> None:
        self.assertFalse((self.project / SEMANTIC_ARTIFACT).exists())

        code, report = run_semantic_understanding_audit(self.project, lightweight=True)

        self.assertEqual(0, code, report["issues"])
        review = (self.project / SEMANTIC_ARTIFACT).read_text(encoding="utf-8")
        self.assertIn("本文由 semantic-argument-model.json 确定性渲染", review)
        self.assertIn("行业数据资源", review)
        self.assertFalse((self.project / "workbench/stages/00-semantic-understanding/semantic-understanding-audit.json").exists())

    def test_source_truth_and_outline_are_compiled_without_reauthoring(self) -> None:
        truth_path = compile_source_truth(self.project)
        truth = load_source_truth(truth_path)

        self.assertEqual([], audit_source_truth(truth))
        self.assertEqual(
            [],
            semantic_evidence_cross_issues(self.model, truth, source_unit_ids=self.unit_ids),
        )
        self.assertEqual("AI-001", truth["records"][0]["atomic_item_id"])
        self.assertEqual("fact", truth["records"][0]["claim_role"])
        self.assertEqual(3, len(truth["records"]))
        self.assertNotIn("retry", truth)
        self.assertTrue(all(record["page_refs"] == [] for record in truth["records"]))

        outline_path = compile_outline_draft(
            self.project,
            communication_goal="面向建设相关方说明现有基础并确认后续动作。",
        )
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        issues = audit_outline(outline, truth, self.model)

        self.assertEqual([], [item.to_dict() for item in issues])
        self.assertEqual("consumption_manifest", outline["source_truth_mapping_mode"])
        self.assertNotIn("retry", outline)
        self.assertEqual("ending", outline["pages"][-1]["page_type"])
        self.assertEqual(
            ["cover", "agenda", "chapter", "content", "ending"],
            [page["page_type"] for page in outline["pages"]],
        )
        content_page = next(page for page in outline["pages"] if page["page_type"] == "content")
        self.assertEqual(["c01", "c01-s01"], content_page["source_argument_node_ids"])
        self.assertEqual(
            {record["id"] for record in truth["records"]},
            set(content_page["source_refs"]),
        )
        consumed_refs = {
            source_ref
            for unit in content_page["content_units"]
            for source_ref in unit["source_refs"]
        } | set(content_page["detail_refs"])
        self.assertEqual(set(content_page["source_refs"]), consumed_refs)
        self.assertLess(len(content_page["content_units"]), len(content_page["source_refs"]))
        self.assertEqual(
            {
                "node_id": "c01-s01",
                "disposition": "merged_page",
                "page_id": content_page["page_id"],
                "rationale": "建设基础与父章节主张共同建立本章起始判断。",
                "merge_reason": "父章节主张与首个子节点构成同一来源主题和同一支撑关系。",
                "shared_page_topic": "建设基础",
            },
            outline["argument_node_dispositions"][0],
        )

    def test_missing_projection_fields_block_audit_and_compilation(self) -> None:
        del self.model["source_coverage"]["assignments"][0]["atomic_items"][0]["evidence_role"]
        model_path = self.project / SEMANTIC_ARGUMENT_MODEL
        model_path.write_text(json.dumps(self.model, ensure_ascii=False, indent=2), encoding="utf-8")

        code, report = run_semantic_understanding_audit(self.project, lightweight=True)

        self.assertEqual(4, code)
        self.assertIn(
            "SEMANTIC_SOURCE_TRUTH_PROJECTION_FIELDS_MISSING",
            {item["code"] for item in report["issues"]},
        )
        with self.assertRaisesRegex(
            ValueError,
            "SEMANTIC_SOURCE_TRUTH_PROJECTION_FIELDS_MISSING",
        ):
            compile_source_truth(self.project)

    def test_official_cli_executes_new_lightweight_path_without_control_artifacts(self) -> None:
        goal = "面向建设相关方说明现有基础并确认后续动作。"

        commands = (
            ["compile-source-truth", str(self.project), "--lightweight"],
            [
                "source-truth-audit",
                str(self.project),
                "--input",
                str(self.project / "workbench/stages/01-analysis/source-truth.json"),
                "--lightweight",
            ],
            [
                "compile-outline-draft",
                str(self.project),
                "--communication-goal",
                goal,
                "--lightweight",
            ],
            [
                "outline-audit",
                str(self.project),
                "--input",
                str(self.project / "workbench/stages/01-analysis/outline.json"),
                "--lightweight",
            ],
        )
        for argv in commands:
            completed = subprocess.run(
                [sys.executable, "-m", "cyberppt", *argv],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
            self.assertEqual("", completed.stderr)
        forbidden = (
            "workbench/artifact-ledger.json",
            "workbench/approvals",
            "workbench/decisions",
            "workbench/runs",
            "workbench/stages/00-semantic-understanding/semantic-generation-receipt.json",
            "workbench/stages/00-semantic-understanding/semantic-understanding-audit.json",
            "workbench/stages/01-analysis/source-truth-audit.json",
            "workbench/stages/01-analysis/source-truth-attempts",
            "workbench/stages/01-analysis/source-truth-escalation.json",
            "workbench/stages/01-analysis/outline-audit.json",
            "workbench/stages/01-analysis/outline-attempts",
            "workbench/stages/01-analysis/outline-escalation.json",
        )
        self.assertEqual(
            [],
            [relative for relative in forbidden if (self.project / relative).exists()],
        )

    def test_compiler_cli_requires_explicit_lightweight_mode(self) -> None:
        commands = (
            ["compile-source-truth", str(self.project)],
            [
                "compile-outline-draft",
                str(self.project),
                "--communication-goal",
                "说明建设基础。",
            ],
        )
        for argv in commands:
            completed = subprocess.run(
                [sys.executable, "-m", "cyberppt", *argv],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(2, completed.returncode)
            self.assertIn("requires --lightweight", completed.stderr)

    def test_outline_recompile_changes_only_the_outline_artifact(self) -> None:
        model_path = self.project / SEMANTIC_ARGUMENT_MODEL
        truth_path = compile_source_truth(self.project)
        model_before = model_path.read_bytes()
        truth_before = truth_path.read_bytes()

        compile_outline_draft(
            self.project,
            communication_goal="先说明现有基础。",
        )
        outline_path = compile_outline_draft(
            self.project,
            communication_goal="说明现有基础并确认后续动作。",
        )

        self.assertEqual(model_before, model_path.read_bytes())
        self.assertEqual(truth_before, truth_path.read_bytes())
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        self.assertEqual("说明现有基础并确认后续动作。", outline["communication_goal"])


if __name__ == "__main__":
    unittest.main()
