from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cyberppt.commands.prepare_stage01_input import (
    PAGE_SCRIPT_AUTHORING_RULES_PATH,
    prepare_outline_input,
    prepare_page_script_input,
)
from cyberppt.outline_authoring_projection import build_outline_authoring_projection


class PrepareStage01InputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        stage = self.project / "workbench/stages/01-analysis"
        stage.mkdir(parents=True)
        (self.project / "workbench/scripts").mkdir(parents=True)
        (stage / "source-truth.json").write_text(
            json.dumps(
                {
                    "records": [
                        {"id": "S001", "statement": "原文证据一", "status": "现状"},
                        {"id": "S002", "statement": "原文证据二", "status": "建议"},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (stage / "outline.json").write_text(
            json.dumps(
                {
                    "pages": [
                        {
                            "page_id": "p04",
                            "page_type": "content",
                            "title": "建设基础",
                            "page_job": "说明为什么现在可以启动",
                            "audience_question": "现有基础是否足以支持项目启动？",
                            "business_question": "基础是否具备",
                            "must_not_include": ["实施步骤", "投资承诺"],
                            "split_risk": "low",
                            "main_message": "已有基础支持启动",
                            "onscreen_judgment": "现有基础足以支持项目启动",
                            "new_value_vs_previous": "形成启动判断",
                            "reserved_for_later": "实施步骤留后页",
                            "visual_intent_type": "hierarchy_support",
                            "visual_proof": "用既有基础托住启动判断",
                            "source_refs": ["S001", "S002"],
                            "proof_points": [
                                {
                                    "claim": "统计基础已经具备",
                                    "source_refs": ["S001"],
                                    "consumption": "primary",
                                }
                            ],
                            "boundary_refs": ["S002"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_prepare_page_script_input_keeps_core_message_when_visible_conclusion_is_empty(self) -> None:
        outline_path = self.project / "workbench/stages/01-analysis/outline.json"
        payload = json.loads(outline_path.read_text(encoding="utf-8"))
        page = payload["pages"][0]
        page["core_message"] = "总体能力框架由五个层次构成"
        page["main_message"] = ""
        page["onscreen_judgment"] = ""
        outline_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        text = prepare_page_script_input(self.project, "p04")
        self.assertIn("- core_message: 总体能力框架由五个层次构成", text)
        self.assertIn("- onscreen_conclusion: ", text)
        self.assertIn("Never strengthen the core_message", text)

    def test_prepare_page_script_input_rejects_unknown_page(self) -> None:
        with self.assertRaisesRegex(ValueError, "content page not found"):
            prepare_page_script_input(self.project, "p99")

    def test_prepare_page_script_input_reads_static_rules_from_resource(self) -> None:
        resource = self.project / "page-script-rules.md"
        resource.write_text(
            "# Resource marker\n\nunique resource guidance\n", encoding="utf-8"
        )

        with patch(
            "cyberppt.commands.prepare_stage01_input.PAGE_SCRIPT_AUTHORING_RULES_PATH",
            resource,
        ):
            text = prepare_page_script_input(self.project, "p04")

        self.assertTrue(text.startswith("# Resource marker\n\nunique resource guidance\n"))
        self.assertIn("## p04 建设基础", text)

    def test_prepare_page_script_input_reports_missing_rules_resource(self) -> None:
        missing = self.project / "missing-page-script-rules.md"

        with patch(
            "cyberppt.commands.prepare_stage01_input.PAGE_SCRIPT_AUTHORING_RULES_PATH",
            missing,
        ):
            with self.assertRaisesRegex(FileNotFoundError, str(missing)):
                prepare_page_script_input(self.project, "p04")

    def test_prepare_page_script_input_has_no_embedded_static_rule_copy(self) -> None:
        from cyberppt.commands import prepare_stage01_input

        source = inspect.getsource(prepare_stage01_input.prepare_page_script_input)
        self.assertNotIn("Never strengthen the core_message", source)
        self.assertNotIn("Write the completed pages directly", source)

    def test_prepare_page_script_input_matches_pre_resource_output_baseline(self) -> None:
        text = prepare_page_script_input(self.project, "p04")

        self.assertEqual(len(text), 13826)
        self.assertEqual(
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "9fcd8334762bc4b9788199384902fc428590b56a743805a349818d721deef5fd",
        )

    def test_prepare_page_script_input_cli_emits_resource_backed_output(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "cyberppt",
                "prepare-page-script-input",
                str(self.project),
                "--page",
                "p04",
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("# Page script authoring input\n"))
        self.assertIn("## p04 建设基础", result.stdout)

    def test_lightweight_outline_input_embeds_director_reasoning_without_writing_control_file(self) -> None:
        semantic = self.project / "workbench/stages/00-semantic-understanding"
        semantic.mkdir(parents=True)
        (semantic / "semantic-understanding.md").write_text(
            "# 全文语义理解\n\n## 全文业务主语\n行业数据服务运营合作。\n",
            encoding="utf-8",
        )
        (semantic / "semantic-argument-model.json").write_text(
            json.dumps(
                {
                    "schema": "cyberppt.semantic_argument_model.v1",
                    "document_semantics": {"primary_thesis": "形成运营合作"},
                    "section_nodes": [],
                    "subsection_nodes": [],
                    "argument_relations": [],
                    "source_gaps": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        outline = self.project / "workbench/stages/01-analysis/outline.json"
        outline.unlink()

        text = prepare_outline_input(
            self.project,
            communication_goal="面向合作企业说明合作价值、参与方式与下一步对接事项",
        )

        self.assertIsInstance(text, str)
        self.assertIn("use one source-faithful storyline route", text)
        self.assertIn("Do not generate or ask the user to choose among multiple routes", text)
        self.assertIn("not a new source fact or source thesis", text)
        self.assertIn("Never promote a user-requested outcome", text)
        self.assertNotIn("compare 2-3 genuinely different", text)
        self.assertIn("The source is evidence, not a page inventory", text)
        self.assertIn("Prefer `source_logic_focused`", text)
        self.assertIn("Recommend `source_logic_focused` for first introductions", text)
        self.assertIn("Do not create a second route merely to manufacture a choice", text)
        self.assertIn("selected_communication_goal", text)
        self.assertIn("Outline root field `communication_goal`", text)
        self.assertIn("`architecture_reason` is required", text)
        self.assertIn("why the selected architecture fits the material and communication goal", text)
        self.assertIn("the reason must identify that explicit request", text)
        self.assertIn("required root `source_section_weights`", text)
        self.assertIn("otherwise use `{}` rather than inventing weights", text)
        self.assertIn("solution is the default architecture", text)
        self.assertIn("topic_partition_mode", text)
        self.assertIn("Topic partitioning is on by default", text)
        self.assertIn("page_sequence_mode", text)
        self.assertIn("chapter_page_orders", text)
        self.assertIn("`title_style_mode` to `formal_plain`", text)
        self.assertIn("business object + matter/mechanism/requirement", text)
        self.assertIn("Use `expressive` only when the user explicitly requests", text)
        self.assertIn("outside the authoritative Storyline Director contract", text)
        self.assertIn("definition_before_detail", text)
        self.assertIn("Keep pages with the same `topic_category` contiguous", text)
        self.assertIn("page_order_reason", text)
        self.assertIn("rebuild `ordered_page_ids`", text)
        self.assertIn("business subject and argument function", text)
        self.assertIn("Every content page must declare exactly one authoritative `topic_category`", text)
        self.assertIn("Never combine different topic categories on one page", text)
        self.assertIn("Category equality is necessary but not sufficient for aggregation", text)
        self.assertIn("A complete process may remain on one page", text)
        self.assertIn("topic_split_reason", text)
        self.assertIn("形成运营合作", text)
        self.assertIn("outline_authoring_projection", text)
        self.assertIn("Use its ST/SU IDs", text)
        self.assertNotIn("authoritative_semantic_understanding", text)
        self.assertNotIn("authoritative_source_argument_model", text)
        self.assertIn("P0 is page-forming", text)
        self.assertIn("Present the completed chapter/page Outline to the user", text)
        self.assertIn("detailed page content to the user", text)
        self.assertFalse(outline.exists())
        self.assertFalse(
            (self.project / "workbench/stages/01-analysis/outline-authoring-input.md").exists()
        )

    def test_outline_authoring_projection_keeps_nodes_relations_and_priority_lookup(self) -> None:
        model = {
            "document_semantics": {"primary_thesis": "主结论"},
            "document_thesis": {"statement": "主结论"},
            "section_nodes": [{"id": "N1", "source_heading": "章节", "section_thesis": "命题", "argument_role": "foundation", "argument_weight": "core", "status": "existing", "evidence_refs": ["SU-1"], "allowed_merges": [], "source_gap_ids": ["G1"]}],
            "subsection_nodes": [{"id": "N2", "parent_id": "N1", "source_heading": "小节", "section_thesis": "小节命题", "argument_role": "detail", "argument_weight": "supporting", "status": "planned", "evidence_refs": ["SU-2"], "allowed_merges": ["N1"]}],
            "argument_relations": [{"id": "R1", "from": "N2", "to": "N1", "relation": "supports"}],
            "source_gaps": [{"id": "G1", "statement": "待核"}],
        }
        truth = {"records": [
            {"id": "ST1", "priority": "P0", "statement": "完整 P0", "source_unit_refs": ["SU-1"], "source_locator": {"paragraph": 1}},
            {"id": "ST2", "priority": "P1", "statement": "完整 P1", "source_unit_refs": ["SU-1"], "source_locator": {"paragraph": 2}},
            {"id": "ST3", "priority": "P2", "statement": "P2 原文", "semantic_units": [{"text": "P2 摘要", "source_unit_ref": "SU-2"}], "source_unit_refs": ["SU-2"], "source_locator": {"paragraph": 3}},
        ]}

        projection = build_outline_authoring_projection(model, truth)

        self.assertEqual({"N1", "N2"}, {node["id"] for node in projection["nodes"]})
        self.assertEqual(["R1"], [item["id"] for item in projection["relations"]])
        self.assertEqual(["ST1", "ST2"], projection["source_truth_refs_by_node"]["N1"])
        self.assertEqual("完整 P0", projection["source_truth_records"]["ST1"]["statement"])
        self.assertEqual("完整 P1", projection["source_truth_records"]["ST2"]["statement"])
        self.assertEqual(["ST3"], projection["source_truth_refs_by_node"]["N2"])
        self.assertIn("summary", projection["source_truth_records"]["ST3"])

    def test_lightweight_page_input_keeps_business_rules_without_authoring_controls(self) -> None:
        text = prepare_page_script_input(self.project, "p04")

        self.assertIsInstance(text, str)
        self.assertIn("完整文字稿", text)
        self.assertIn("必留上屏/仅讲解/仅追溯", text)
        self.assertIn("业务小标题\n  完整、自然的明细句。", text)
        self.assertIn("【视觉结构，不上屏】", text)
        self.assertIn("present the detailed page content to the user", text)
        self.assertNotIn("cyberppt-page-contract", text)
        self.assertFalse(
            (self.project / "workbench/scripts/page-script-authoring.json").exists()
        )
        self.assertFalse(
            (self.project / "workbench/scripts/page-script-authoring-input-p04.md").exists()
        )


if __name__ == "__main__":
    unittest.main()
