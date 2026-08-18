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
    _render_visual_review_summary,
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
    def test_selected_visual_thesis_and_scene_policy_reach_executable_spec(self) -> None:
        source = {
            "page_id": "p01",
            "page_number": 1,
            "page_title": "Title",
            "argument_role": "content",
            "page_mission": "Explain how governed inputs become an auditable result",
            "core_judgment": "Unified governance turns inputs into results.",
            "locked_text_items": [
                {"text_id": "P01-T01", "text": "Governed input"},
                {"text_id": "P01-T02", "text": "Auditable result"},
            ],
            "business_relationships": [
                {"subject": "Governance hub", "relation": "transforms", "objects": ["Auditable result"]}
            ],
            "expression_constraints": expression_constraints("flow_3_5"),
            "body_image_canvas": {"width": 2048, "height": 1024, "ratio": "2:1"},
            "title_render_mode": "external_text_layer",
            "subtitle_render_mode": "external_text_layer",
        }
        candidates = [
            {
                "id": f"c{index}",
                "visual_thesis": "Inputs converge through one governance hub and emerge as an auditable result.",
                "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
                "reading_sequence": ["input", "result"],
                "spatial_grammar": ["convergence"],
                "topology": "causal_convergence",
                "direction": "outside_to_anchor",
                "visual_intent_type": "input_to_result",
                "expression_fit": {
                    "form": "flow_3_5",
                    "constraint_status": "default_profile",
                    "satisfied_constraints": ["ordered_progression"],
                    "reading_relation": "input converges into an auditable result",
                    "balance_strategy": "one dominant result",
                    "changed_constraints": [],
                    "deviation_reason": "",
                },
            }
            for index in range(1, 4)
        ]
        decision = {
            "page_id": "p01",
            "evidence_units": [
                {"key": "input", "summary": "Governed input", "text_ids": ["P01-T01"]},
                {"key": "result", "summary": "Auditable result", "text_ids": ["P01-T02"]},
            ],
            "candidates": candidates,
            "selected_candidate": "c1",
            "execution_design": {
                "business_object": "governance hub in an operating environment",
                "visual_focus": "the auditable result leaving the hub",
                "text_integration_method": "attach each locked phrase to its related input or result",
                "spatial_organization": "inputs converge on the hub before one result exits",
                "relationship_encoding": "convergence and output direction encode transformation",
                "semantic_role": "the operating hub proves that governance creates the result",
                "use_scene": True,
                "scene_type": "integrated governance operations scene",
            },
        }

        page = _build_executable_page(source, decision)

        self.assertEqual(candidates[0]["visual_thesis"], page["visual_decision"]["visual_thesis"])
        self.assertNotEqual(source["core_judgment"], page["visual_decision"]["visual_thesis"])
        self.assertTrue(page["image_plan"]["use_scene"])
        self.assertEqual("integrated governance operations scene", page["image_plan"]["scene_type"])
        self.assertEqual(
            "the operating hub proves that governance creates the result",
            page["image_plan"]["semantic_role"],
        )

    def test_structural_decision_cannot_carry_a_second_topology_authority(self) -> None:
        """semantic_graph is the only page topology/relation authority.

        structural_decision may not redeclare topology/primary_relation/nodes/
        edges -- that would recreate the "second page semantics authority"
        the visual-structure-fidelity plan forbids. additionalProperties:
        false on structural_decision should already reject these keys; this
        test pins that guarantee against accidental schema loosening.
        """

        import jsonschema

        source = {
            "page_id": "p01", "page_number": 1, "page_title": "Title",
            "page_mission": "Explain how the input relationship field supports the result.",
            "core_judgment": "Input visibly supports the result through one relationship field.",
            "locked_text_items": [
                {"text_id": "P01-T01", "text": "Input"},
                {"text_id": "P01-T02", "text": "Result"},
            ],
            "business_relationships": [{"subject": "Input", "relation": "supports", "objects": ["Result"]}],
            "expression_constraints": expression_constraints("flow_3_5"),
        }
        decision = {
            "page_id": "p01",
            "evidence_units": [
                {"key": "input", "summary": "Input supports the result.", "text_ids": ["P01-T01"]},
                {"key": "result", "summary": "The result the input supports.", "text_ids": ["P01-T02"]},
            ],
            "candidates": [
                {"id": f"c{index}", "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
                 "reading_sequence": ["input", "result"], "spatial_grammar": ["path"],
                 "topology": "directed_flow",
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
        }
        page = _build_executable_page(source, decision)
        schema_path = _skill_root() / "assets" / "page-visual-spec.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)

        self.assertEqual([], list(validator.iter_errors(page)))

        for leaking_field, value in (
            ("topology", "directed_flow"),
            ("primary_relation", "flow"),
            ("nodes", page["semantic_graph"]["nodes"]),
            ("edges", page["semantic_graph"]["edges"]),
        ):
            tainted = json.loads(json.dumps(page))
            tainted["structural_decision"][leaking_field] = value
            errors = list(validator.iter_errors(tainted))
            self.assertTrue(
                errors,
                f"structural_decision.{leaking_field} should be rejected by the schema",
            )

    def test_business_relationships_compile_to_plain_relation_sentence(self) -> None:
        source = {
            "page_id": "p01",
            "page_number": 1,
            "page_title": "Title",
            "page_mission": "Explain the governed service relationship",
            "core_judgment": "Governance enables service delivery.",
            "locked_text_items": [
                {"text_id": "P01-T01", "text": "Input"},
                {"text_id": "P01-T02", "text": "Result"},
            ],
            "business_relationships": [
                {"subject": "Input", "relation": "supports", "objects": ["Result", "Audit"]}
            ],
            "expression_constraints": expression_constraints("flow_3_5"),
        }
        candidates = [
            {
                "id": f"c{index}",
                "visual_thesis": "Input visibly supports both the result and its audit trail.",
                "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
                "reading_sequence": ["input", "result"],
                "spatial_grammar": ["path"],
                "topology": "directed_flow",
                "direction": "left_to_right",
                "visual_intent_type": "support_relationship",
                "expression_fit": {
                    "form": "flow_3_5",
                    "constraint_status": "default_profile",
                    "satisfied_constraints": ["ordered_progression"],
                    "reading_relation": "input supports the result",
                    "balance_strategy": "one result remains primary",
                    "changed_constraints": [],
                    "deviation_reason": "",
                },
            }
            for index in range(1, 4)
        ]
        page = _build_executable_page(
            source,
            {
                "page_id": "p01",
                "evidence_units": [
                    {"key": "input", "summary": "Input", "text_ids": ["P01-T01"]},
                    {"key": "result", "summary": "Result", "text_ids": ["P01-T02"]},
                ],
                "candidates": candidates,
                "selected_candidate": "c1",
                "execution_design": {
                    "business_object": "input-to-result relationship field",
                    "visual_focus": "Result",
                    "text_integration_method": "attach text to the related object",
                    "spatial_organization": "Input leads to Result with Audit as a secondary outcome",
                    "relationship_encoding": "directed support relationship",
                    "semantic_role": "the relationship field proves traceable support",
                    "use_scene": False,
                    "scene_type": "flat business relationship field",
                },
            },
        )

        relationship = page["semantic_graph"]["decision_relationship"]
        self.assertEqual("Input supports Result；Input supports Audit", relationship)
        self.assertNotIn("[{", relationship)
        self.assertEqual(
            source["business_relationships"],
            page["semantic_graph"]["business_relationships"],
        )
        self.assertNotEqual(
            page["semantic_graph"]["business_relationships"], page["connectors"]
        )

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
                 "topology": "directed_flow",
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
        self.assertEqual("pending_audit", page["qa"]["status"])
        self.assertIsNone(page["qa"]["score"])
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
                "topology": "causal_convergence",
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

        self.assertEqual(
            {"status": "pending_audit", "score": None, "blocking_issues": [], "warnings": []},
            page["qa"],
        )

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

    def test_review_summary_contains_p3_minimum_package(self) -> None:
        spec = {
            "deck_title": "Test",
            "pages": [{
                "page_id": "P01", "page_number": 1, "page_title": "Title", "page_mission": "Mission",
                "quality_contract": {"generation_feasibility": {"score": 100, "risks": []}, "text_capacity": {"locked_text_count": 2, "risk_level": "low", "risks": []}, "relationship_coverage": {"total": 1}, "focus_competition": {"status": "passed"}},
                "semantic_graph": {"edges": [{"from": "E1", "to": "E2", "relation": "flow"}]},
                "structural_decision": {"semantic_focus": {"ref": "E2"}},
            }],
        }
        decisions = {"pages": [{"page_id": "p01", "selected_candidate": "C1", "candidates": [{"id": "C1"}, {"id": "C2", "rejection_rationale": "relation clarity is weaker"}]}]}
        summary = _render_visual_review_summary(spec, decisions, {"deck_rhythm": {"status": "passed", "blocking_issues": [], "warnings": []}})
        for heading in ("页面使命", "选中候选", "候选取舍", "关系草图", "锁定文字容量", "可生成性", "关系/焦点风险", "整套节奏结论"):
            self.assertIn(heading, summary)

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
        relationships = [{
            "subject": "Foundation",
            "objects": ["Pilot"],
            "relation": "supports",
            "direction": "subject_to_objects",
            "condition": "when ready",
            "modality": "proposed",
            "basis": "explicit",
            "confidence": "high",
            "source_refs": ["S001"],
            "authority_ref": "R001",
        }]
        outline = {
            "argument_role": "evidence",
            "source_heading_ids": ["sec-0002"],
            "primary_source_heading_id": "sec-0002",
            "subtitle_policy": {"mode": "not_needed", "subtitle": ""},
            "content_relations": relationships,
        }

        record = _page_record(page, outline)
        visual = record["stage02_visual_input"]

        self.assertEqual(relationships, visual["business_relationships"])
        self.assertEqual(["sec-0002"], record["source_heading_ids"])
        self.assertEqual("sec-0002", record["primary_source_heading_id"])
        self.assertEqual(outline["subtitle_policy"], record["subtitle_policy"])
        self.assertEqual("five horizontal lanes with a bottom result area", visual["author_visual_notes"])
        self.assertEqual("framework_4", record["expression_constraints"]["form"])
        self.assertEqual(record["expression_constraints"], visual["expression_constraints"])
        self.assertEqual("advisory_only", visual["author_visual_notes_authority"])
        self.assertEqual("stage01_semantic_handoff", visual["stage01_relationship_features"]["authority"])
        self.assertEqual("Foundation", visual["stage01_relationship_features"]["actors"][0])
        self.assertEqual("supports", visual["stage01_relationship_features"]["actions"][0]["relation"])
        self.assertEqual(
            "subject_to_objects",
            visual["stage01_relationship_features"]["actions"][0]["direction"],
        )
        self.assertEqual(
            "explicit",
            visual["stage01_relationship_features"]["actions"][0]["basis"],
        )
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
                "review_summary",
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

    def test_prompt_inputs_hash_ignores_style_lock_but_tracks_the_spec(self) -> None:
        """Replacing only the Style lock must not change the structural-freshness
        binding; changing the compiled spec (structure) must.
        """

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            script = project / "script.md"
            script.write_text(
                "## 第1页：Title\n- 页面类型：内容页\n- 页面标题：Title\n"
                "- 核心结论：Message\n- 完整文字稿：Prose\n- 上屏文字：\n  - Text\n",
                encoding="utf-8",
            )
            skill_root = _skill_root()
            artifact_keys = ("design_input", "decisions", "execution_receipt", "spec_json", "spec_markdown")
            for key in artifact_keys:
                path = project / VISUAL_FILES[key]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(key + "\n", encoding="utf-8")

            before = _prompt_inputs_sha256(project, script, skill_root)

            style_lock = project / "workbench" / "locks" / "visual_style_lock.json"
            style_lock.parent.mkdir(parents=True, exist_ok=True)
            style_lock.write_text(json.dumps({"style": {"id": 9}}), encoding="utf-8")
            after_style_change = _prompt_inputs_sha256(project, script, skill_root)
            self.assertEqual(before, after_style_change)

            style_lock.write_text(json.dumps({"style": {"id": 10}}), encoding="utf-8")
            after_second_style_change = _prompt_inputs_sha256(project, script, skill_root)
            self.assertEqual(before, after_second_style_change)

            (project / VISUAL_FILES["spec_json"]).write_text("spec_json changed\n", encoding="utf-8")
            after_structure_change = _prompt_inputs_sha256(project, script, skill_root)
            self.assertNotEqual(before, after_structure_change)


if __name__ == "__main__":
    unittest.main()
