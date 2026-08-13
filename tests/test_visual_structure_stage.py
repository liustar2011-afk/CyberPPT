from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cyberppt.commands.visual_structure_stage import (
    VISUAL_FILES,
    _build_executable_page,
    _decision_execution_design,
    _prompt_inputs_sha256,
    _render_visual_structure_markdown,
    _sha256,
    _skill_root,
    _write_visual_design_input,
    _write_skill_request,
    assert_visual_structure_ready,
    prepare_visual_structure_stage,
    visual_structure_required,
)
from cyberppt.stage02_handoff import audit_stage02_handoff
from cyberppt.stage02_handoff import _page_record
from cyberppt.script_quality_contract import ScriptPage
from cyberppt.semantic_digest import outline_semantic_digest, script_semantic_digest
from cyberppt.onscreen_expression import expression_constraints
from cyberppt.onscreen_expression import expression_constraints_sha256


class VisualStructureStageTests(unittest.TestCase):
    def test_visual_design_input_carries_expression_as_semantic_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            handoff = project / "handoff.json"
            handoff.write_text(json.dumps({
                "pages": [{
                    "page_id": "p01", "page_number": 1, "render_role": "content",
                    "title": "标题", "argument_role": "framework", "page_mission": "说明体系",
                    "core_message": "形成能力体系", "full_prose": "说明",
                    "onscreen_text": "权属确认\n授权管理\n流转审计\n责任闭环",
                    "onscreen_items": ["权属确认", "授权管理", "流转审计", "责任闭环"],
                    "source_refs": ["S001"],
                    "onscreen_expression": {"form": "framework_4", "source": "relation", "confidence": 0.92, "evidence": ["relation:composed_of"]},
                    "stage02_visual_input": {"locked_text_items": [], "business_relationships": [], "stage01_relationship_features": {}},
                }]
            }, ensure_ascii=False), encoding="utf-8")
            output = _write_visual_design_input(project, handoff)
            page = json.loads(output.read_text(encoding="utf-8"))["pages"][0]
        self.assertEqual("framework_4", page["onscreen_expression"]["form"])
        self.assertEqual("framework_4", page["expression_constraints"]["form"])
        self.assertEqual([4, 4], page["expression_constraints"]["node_range"])
        self.assertNotIn("layout", page["onscreen_expression"])
        self.assertEqual(["S001"], page["trace_refs"])

    def test_trace_refs_are_audit_only_and_compilation_is_ungraded(self) -> None:
        source = {
            "page_id": "p01", "page_number": 1, "page_title": "Title",
            "argument_role": "content", "page_mission": "Mission",
            "core_judgment": "Judgment", "trace_refs": ["TRACE-ONLY-001"],
            "locked_text_items": [{"text_id": "P01-T01", "text": "Locked text"}],
            "business_relationships": [{"subject": "Input", "relation": "supports", "objects": ["Result"]}],
            "expression_constraints": expression_constraints("flow_3_5"),
            "body_image_canvas": {"width": 2048, "height": 1024, "ratio": "2:1"},
            "title_render_mode": "external_text_layer", "subtitle_render_mode": "external_text_layer",
        }
        decision = {
            "page_id": "p01",
            "evidence_units": [{"key": "e1", "summary": "Evidence", "text_ids": ["P01-T01"]}],
            "candidates": [
                {"id": f"c{index}", "semantic_focus": {"evidence_key": "e1"},
                 "reading_sequence": ["e1"], "spatial_grammar": ["path"],
                 "direction": "left_to_right", "visual_intent_type": "relationship_field",
                 "expression_fit": {
                     "form": "flow_3_5", "constraint_status": "default_profile",
                     "satisfied_constraints": ["ordered_progression"],
                     "reading_relation": "Input progresses to Result",
                     "balance_strategy": "one focal progression",
                     "changed_constraints": [], "deviation_reason": "",
                 }}
                for index in range(1, 4)
            ],
            "selected_candidate": "c1",
            "execution_design": {
                "business_object": "Input to Result relationship", "visual_focus": "Result",
                "text_integration_method": "Attach text to Result", "spatial_organization": "Input flows to Result",
                "relationship_encoding": "Show Input supporting Result",
            },
        }
        page = _build_executable_page(source, decision)
        self.assertEqual("TRACE-ONLY-001", page["evidence_units"][0]["source_ref"])
        self.assertEqual("draft", page["qa"]["status"])
        self.assertEqual(0, page["qa"]["score"])
        with tempfile.TemporaryDirectory() as directory:
            spec = Path(directory) / "deck.json"
            prompt = Path(directory) / "prompt.md"
            spec.write_text(json.dumps({"pages": [page]}, ensure_ascii=False), encoding="utf-8")
            subprocess.run(
                [sys.executable, str(_skill_root() / "scripts" / "build_generation_prompt.py"), str(spec), "--output", str(prompt)],
                check=True,
            )
            self.assertNotIn("TRACE-ONLY-001", prompt.read_text(encoding="utf-8"))

    def test_skill_request_assigns_specs_to_the_compiler(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            script = project / "script.md"
            script.write_text(
                "## 第1页：Title\n- 页面类型：内容页\n- 页面标题：Title\n"
                "- 核心结论：Message\n- 完整文字稿：Prose\n- 上屏文字：\n  - Text\n",
                encoding="utf-8",
            )
            design_input = project / VISUAL_FILES["design_input"]
            design_input.parent.mkdir()
            design_input.write_text("{}", encoding="utf-8")
            request = json.loads(_write_skill_request(project, script, design_input).read_text(encoding="utf-8"))

        self.assertEqual(["visual/visual-design-decisions.json"], request["required_outputs"])
        self.assertEqual(
            ["visual/deck-visual-spec.json", "visual/script-visual-structure.md"],
            request["compiler_outputs"],
        )

    def test_executable_spec_rejects_more_than_seven_evidence_nodes(self) -> None:
        source = {
            "page_id": "p01",
            "page_number": 1,
            "page_title": "Title",
            "page_mission": "Mission",
            "core_judgment": "Judgment",
            "locked_text_items": [
                {"text_id": f"P01-T{index:02d}", "text": f"Text {index}"}
                for index in range(1, 9)
            ],
        }
        evidence = [
            {"key": f"e{index}", "summary": f"Evidence {index}", "text_ids": [f"P01-T{index:02d}"]}
            for index in range(1, 9)
        ]
        decision = {
            "page_id": "p01",
            "evidence_units": evidence,
            "candidates": [
                {
                    "id": f"c{index}",
                    "semantic_focus": {"evidence_key": "e1"},
                    "reading_sequence": [item["key"] for item in evidence],
                    "spatial_grammar": ["path"],
                    "direction": "left_to_right",
                    "visual_intent_type": "data_flow_value_chain",
                }
                for index in range(1, 4)
            ],
            "selected_candidate": "c1",
        }

        with self.assertRaisesRegex(ValueError, "at most 7 business evidence units"):
            _build_executable_page(source, decision)

    def test_executable_spec_retains_selected_expression_contract(self) -> None:
        source = {
            "page_id": "p01", "page_number": 1, "page_title": "Title",
            "page_mission": "Mission detail", "core_judgment": "Judgment",
            "locked_text_items": [
                {"text_id": "P01-T01", "text": "Cause"},
                {"text_id": "P01-T02", "text": "Response"},
            ],
            "business_relationships": [{"subject": "Cause", "objects": ["Response"], "relation": "causes"}],
            "expression_constraints": expression_constraints("causal_chain"),
        }
        fit = {
            "form": "causal_chain", "constraint_status": "adapted",
            "satisfied_constraints": ["directed_causal_chain"],
            "reading_relation": "two parallel causes converge before the response",
            "balance_strategy": "parallel causes have equal weight before convergence",
            "changed_constraints": ["reading_requirement"],
            "deviation_reason": "the convergence preserves the causal core",
        }
        candidates = [
            {
                "id": candidate_id, "semantic_focus": {"kind": "outcome", "evidence_key": "response"},
                "reading_sequence": ["cause", "response"], "spatial_grammar": [grammar],
                "direction": "left_to_right", "visual_intent_type": "causal_response",
                "expression_fit": fit,
            }
            for candidate_id, grammar in (("candidate-a", "path"), ("candidate-b", "convergence"), ("candidate-c", "control"))
        ]
        decision = {
            "page_id": "p01", "candidates": candidates, "selected_candidate": "candidate-b",
            "evidence_units": [
                {"key": "cause", "summary": "Cause", "text_ids": ["P01-T01"]},
                {"key": "response", "summary": "Response", "text_ids": ["P01-T02"]},
            ],
        }

        page = _build_executable_page(source, decision)

        self.assertEqual({
            "form": "causal_chain",
            "constraints_sha256": expression_constraints_sha256(source["expression_constraints"]),
            "selected_candidate_id": "candidate-b",
            "fit_status": "adapted",
            "reading_relation": "two parallel causes converge before the response",
            "balance_strategy": "parallel causes have equal weight before convergence",
            "deviation_reason": "the convergence preserves the causal core",
        }, page["expression_contract"])
        markdown = _render_visual_structure_markdown({"deck_title": "Test", "pages": [page]})
        self.assertIn("上屏表达结构与候选取舍", markdown)
        self.assertIn("causal_chain", markdown)
        schema_path = Path(__file__).resolve().parents[1] / "vendor/skills/ppt-visual-structure-designer/assets/page-visual-spec.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        contract_schema = schema["properties"]["expression_contract"]
        self.assertEqual(set(page["expression_contract"]), set(contract_schema["required"]))
        self.assertFalse(contract_schema["additionalProperties"])

    def test_corrupted_optional_execution_design_falls_back_to_concise_relation_design(self) -> None:
        source = {
            "business_relationships": [{"subject": "服务运营", "objects": ["very long audit-only evidence"]}],
            "core_judgment": "服务运营以订单履行形成一致结算依据。",
        }
        decision = {
            "execution_design": {"business_object": "???"},
            "evidence_units": [{"key": "E2", "summary": "订单履行｜购买约定、服务执行与计量结算保持一致 / 其余审计细节"}],
        }
        design = _decision_execution_design(source, decision, {"semantic_focus": {"evidence_key": "E2"}}, "P11")
        self.assertIn("订单履行", design["business_object"])
        self.assertNotIn("very long audit-only evidence", design["business_object"])
        self.assertLess(len(design["business_object"]), 64)

    def test_handoff_separates_business_relations_from_author_layout_notes(self) -> None:
        page = ScriptPage(
            page_id="p06",
            sequence=6,
            heading="Page 6",
            page_type="content",
            title="Title",
            main_message="Message",
            full_prose="Prose",
            selection_notes="",
            evidence_map="",
            evidence_map_refs=(),
            source_refs=("S001",),
            boundary_source_refs=(),
            boundary="",
            visual_structure="five horizontal lanes with a bottom result area",
            onscreen_text="Group\nDetail",
            module_titles=(),
            contract_receipt={"page_mission": "Mission"},
        )
        relationships = [
            {"subject": "Foundation", "objects": ["Pilot"], "relation": "supports"}
        ]

        record = _page_record(page, {"argument_role": "evidence", "content_relations": relationships})
        visual = record["stage02_visual_input"]

        self.assertEqual(relationships, visual["business_relationships"])
        self.assertEqual("five horizontal lanes with a bottom result area", visual["author_visual_notes"])
        self.assertEqual("framework_4", record["expression_constraints"]["form"])
        self.assertEqual(record["expression_constraints"], visual["expression_constraints"])
        self.assertEqual("advisory_only", visual["author_visual_notes_authority"])
        self.assertEqual("stage01_semantic_handoff", visual["stage01_relationship_features"]["authority"])
        self.assertEqual("Foundation", visual["stage01_relationship_features"]["actors"][0])
        self.assertEqual("supports", visual["stage01_relationship_features"]["actions"][0]["relation"])
        self.assertEqual("P06-T01", visual["locked_text_items"][0]["text_id"])
        self.assertNotIn("approved_stage01_visual_structure", visual)
        self.assertNotIn("source_refs", visual)

    def test_lightweight_handoff_falls_back_to_outline_contract_fields(self) -> None:
        page = ScriptPage(
            page_id="p06",
            sequence=6,
            heading="Page 6",
            page_type="content",
            title="Title",
            main_message="Message",
            full_prose="Prose",
            selection_notes="",
            evidence_map="",
            evidence_map_refs=(),
            source_refs=("S001",),
            boundary_source_refs=(),
            boundary="",
            visual_structure="Relation",
            onscreen_text="Group\nDetail",
            module_titles=(),
            contract_receipt={},
        )

        record = _page_record(
            page,
            {
                "page_mission": "Outline mission",
                "must_not_include": ["Excluded claim"],
                "content_units": [{"unit_id": "p06-U01"}],
            },
        )

        self.assertEqual("Outline mission", record["page_mission"])
        self.assertEqual(["Excluded claim"], record["must_not_include"])
        self.assertEqual(["p06-U01"], record["consumed_content_unit_ids"])
        self.assertEqual("Outline mission", record["stage02_visual_input"]["page_mission"])

    def test_handoff_audit_reports_source_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            source = project / "script.md"
            source.write_text("current script\n", encoding="utf-8")
            payload = {
                "schema": "cyberppt.stage02_handoff.v1",
                "source_bindings": {
                    "script": {
                        "path": str(source),
                        "sha256": "0" * 64,
                        "semantic_sha256": "1" * 64,
                    }
                },
                "pages": [
                    {
                        "page_id": "p01",
                        "page_number": 1,
                        "render_role": "content",
                        "title": "Title",
                        "page_mission": "Mission",
                        "core_message": "Message",
                        "onscreen_text": "Text",
                        "onscreen_items": ["Text"],
                        "onscreen_expression": {
                            "form": "key_points_3", "source": "fallback", "confidence": 0.2,
                        },
                        "expression_constraints": expression_constraints("key_points_3"),
                        "stage02_visual_input": {
                            "locked_text_items": [
                                {"text_id": "P01-T01", "text": "Text", "ordinal": 1}
                            ],
                            "business_relationships": [],
                            "stage01_relationship_features": {
                                "authority": "stage01_semantic_handoff",
                                "actors": ["Input"],
                                "actions": [{"subject": "Input", "relation": "supports", "object": "Result"}],
                                "directions": [], "conditions": [], "branches": [], "feedback": [],
                                "source_visual_notes": "",
                            },
                            "author_visual_notes_authority": "advisory_only",
                            "expression_constraints": expression_constraints("key_points_3"),
                            "body_image_canvas": {
                                "width": 2048,
                                "height": 1024,
                                "ratio": "2:1",
                            }
                        },
                    }
                ],
            }

            report = audit_stage02_handoff(project, payload)

        self.assertEqual("failed", report["status"])
        self.assertIn("HANDOFF_BINDING_STALE", {item["code"] for item in report["blocking_issues"]})

    def test_prepare_reuse_rejects_a_stale_handoff_before_writing_visual_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            script = project / "script.md"
            script.write_text(
                "## 第1页：Title\n- 页面类型：内容页\n- 页面标题：Title\n"
                "- 核心结论：Message\n- 完整文字稿：Prose\n- 上屏文字：\n  - Text\n",
                encoding="utf-8",
            )
            handoff = project / "workbench" / "stages" / "02-handoff" / "stage02-handoff.json"
            handoff.parent.mkdir(parents=True)
            handoff.write_text(
                json.dumps({
                    "schema": "cyberppt.stage02_handoff.v1",
                    "source_bindings": {"script": {"path": str(script), "sha256": "0" * 64, "semantic_sha256": "0" * 64}},
                    "pages": [],
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "HANDOFF_BINDING_STALE"):
                prepare_visual_structure_stage(project, script, reuse_current_handoff=True)

            self.assertFalse((project / VISUAL_FILES["design_input"]).exists())

    def test_existing_project_with_visual_artifacts_requires_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            visual = project / "visual"
            visual.mkdir(parents=True)
            (project / "manifest.yml").write_text("mode: lightweight\n", encoding="utf-8")
            (visual / "skill-request.json").write_text("{}\n", encoding="utf-8")
            self.assertTrue(visual_structure_required(project))

    def test_gate_binds_prompt_inputs_and_invalidates_script_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            (project / "manifest.yml").write_text(
                "gates:\n  visual_structure_designer: required\n", encoding="utf-8"
            )
            script = project / "script.md"
            script.write_text(
                "## 第1页：Title\n"
                "- 页面类型：内容页\n"
                "- 页面标题：Title\n"
                "- 核心结论：Message\n"
                "- 完整文字稿：Prose\n"
                "- 上屏文字：\n"
                "  - Text\n",
                encoding="utf-8",
            )
            stage01 = project / "workbench" / "stages" / "01-analysis"
            stage01.mkdir(parents=True)
            outline = stage01 / "outline.json"
            outline.write_text('{"schema":"outline.v1","pages":[]}', encoding="utf-8")
            handoff = project / "workbench" / "stages" / "02-handoff" / "stage02-handoff.json"
            handoff.parent.mkdir(parents=True)
            handoff.write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.stage02_handoff.v1",
                        "source_bindings": {
                            "script": {
                                "path": str(script),
                                "sha256": _sha256(script),
                                "semantic_sha256": script_semantic_digest(script),
                            },
                            "outline": {
                                "path": str(outline),
                                "sha256": _sha256(outline),
                                "semantic_sha256": outline_semantic_digest(outline),
                            },
                        },
                        "pages": [
                            {
                                "page_id": "p01",
                                "page_number": 1,
                                "render_role": "content",
                                "title": "Title",
                                "page_mission": "Mission",
                                "core_message": "Message",
                                "onscreen_text": "Text",
                                "onscreen_items": ["Text"],
                                "onscreen_expression": {
                                    "form": "key_points_3", "source": "fallback", "confidence": 0.2,
                                },
                                "expression_constraints": expression_constraints("key_points_3"),
                                "stage02_visual_input": {
                                    "locked_text_items": [
                                        {"text_id": "P01-T01", "text": "Text", "ordinal": 1}
                                    ],
                                    "business_relationships": [],
                                    "stage01_relationship_features": {
                                        "authority": "stage01_semantic_handoff",
                                        "actors": ["Input"],
                                        "actions": [{"subject": "Input", "relation": "supports", "object": "Result"}],
                                        "directions": [], "conditions": [], "branches": [], "feedback": [],
                                        "source_visual_notes": "",
                                    },
                                    "author_visual_notes_authority": "advisory_only",
                                    "expression_constraints": expression_constraints("key_points_3"),
                                    "body_image_canvas": {
                                        "width": 2048,
                                        "height": 1024,
                                        "ratio": "2:1",
                                    },
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            visual = project / "visual"
            visual.mkdir()
            artifact_keys = (
                "design_input",
                "skill_request",
                "decisions",
                "execution_receipt",
                "spec_json",
                "spec_markdown",
                "generation_prompts",
            )
            artifacts = {
                key: project / VISUAL_FILES[key]
                for key in artifact_keys
            }
            for key, path in artifacts.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(key + "\n", encoding="utf-8")
            (visual / "validation-report.json").write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.visual_structure_stage.v2",
                        "status": "passed",
                        "artifact_sha256": {
                            key: _sha256(path) for key, path in artifacts.items()
                        },
                        "prompt_inputs_sha256": _prompt_inputs_sha256(
                            project, script, _skill_root()
                        ),
                    }
                ),
                encoding="utf-8",
            )
            self.assertIsNotNone(assert_visual_structure_ready(project, script))
            script.write_text(
                "## 第1页：Title\n"
                "- 页面类型：内容页\n"
                "- 页面标题：Title\n"
                "- 核心结论：Changed message\n"
                "- 完整文字稿：Changed prose\n"
                "- 上屏文字：\n"
                "  - Changed text\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "HANDOFF_BINDING_STALE"):
                assert_visual_structure_ready(project, script)


if __name__ == "__main__":
    unittest.main()
