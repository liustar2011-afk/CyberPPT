from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cyberppt.page_artifact_spec import (
    build_page_artifact_spec,
    load_project_page_artifact_specs,
)


class PageArtifactSpecTests(unittest.TestCase):
    def _inputs(self, root: Path) -> tuple[dict, dict, Path]:
        style_lock = root / "style-lock.json"
        style_lock.write_text(
            json.dumps(
                {
                    "style": {
                        "id": 10,
                        "name": "White editorial",
                        "slug": "white_editorial",
                        "style_prompt_v2": "Pure white editorial art direction.",
                    }
                }
            ),
            encoding="utf-8",
        )
        handoff_page = {
            "page_id": "p07",
            "page_number": 7,
            "render_role": "content",
            "argument_role": "evidence",
            "title": "External title",
            "page_mission": "Show how governed input becomes a traceable result.",
            "core_message": "Unified governance makes the result traceable.",
            "must_not_include": ["Do not discuss the next chapter"],
            "stage02_visual_input": {
                "body_image_canvas": {"width": 2048, "height": 1024, "ratio": "2:1"},
                "title_render_mode": "external_text_layer",
                "subtitle_render_mode": "external_text_layer",
                "business_relationships": [
                    {
                        "subject": "项目",
                        "relation": "has_goal",
                        "objects": ["统一服务入口"],
                        "direction": "subject_to_objects",
                        "condition": "",
                        "modality": "",
                        "basis": "explicit",
                        "confidence": "high",
                        "source_refs": ["ST0002"],
                        "authority_ref": "rel-0001",
                    }
                ],
            },
        }
        visual_page = {
            "page_id": "P07",
            "page_number": 7,
            "page_role": "evidence",
            "page_mission": "Show how governed input becomes a traceable result.",
            "core_judgment": "Unified governance makes the result traceable.",
            "content_lock": {
                "mode": "strict",
                "locked_items": [
                    {"id": "P07-TITLE", "type": "title", "text": "External title"},
                    {"id": "P07-T01", "type": "body", "text": "Governed input"},
                    {"id": "P07-T02", "type": "body", "text": "Traceable result"},
                ],
                "allowed_transformations": ["line_break", "grouping"],
                "forbidden_transformations": ["change actors or status"],
            },
            "evidence_units": [
                {"id": "E1", "text": "Governed input enters", "kind": "process", "priority": "P0"},
                {"id": "E2", "text": "Traceable result emerges", "kind": "result", "priority": "P0"},
            ],
            "semantic_graph": {
                "primary_relation": "transform",
                "topology": "directed_flow",
                "forbidden_structures": ["equal_peer_cards", "invented_center_hub"],
                "decision_relationship": "Governance hub transforms input into traceable result",
                "business_relationships": [
                    {
                        "subject": "项目",
                        "relation": "has_goal",
                        "objects": ["统一服务入口"],
                        "direction": "subject_to_objects",
                        "condition": "",
                        "modality": "",
                        "basis": "explicit",
                        "confidence": "high",
                        "source_refs": ["ST0002"],
                        "authority_ref": "rel-0001",
                    }
                ],
            },
            "structural_decision": {
                "spatial_grammar": ["convergence", "path"],
                "reading_sequence": ["E1", "E2"],
                "semantic_tags": ["transformation"],
            },
            "visual_decision": {
                "visual_thesis": "Inputs converge through one governance hub and emerge as a traceable result.",
                "spatial_organization": "Input converges on the hub before the result exits",
                "reading_path": ["Governed input enters", "Traceable result emerges"],
                "text_integration_method": "Attach each phrase to its related object",
                "relationship_encoding": "Convergence and output direction encode transformation",
                "visual_hierarchy": {
                    "primary": "Traceable result",
                    "secondary": ["Governed input"],
                    "tertiary": [],
                },
            },
            "text_integration": {
                "title_render_mode": "external_text_layer",
                "subtitle_render_mode": "external_text_layer",
                "body_render_mode": "in_image",
                "placement_strategy": "Attach each phrase to its related object",
            },
            "geometry": {"canvas": {"width": 2048, "height": 1024, "ratio": "2:1"}},
            "image_plan": {
                "use_scene": True,
                "scene_type": "Integrated governance operations scene",
                "business_object": "Governance operations hub",
                "semantic_role": "The hub proves transformation and traceability",
                "placement": "Input converges on the hub before the result exits",
            },
            "connectors": [
                {"from": "E1", "to": "E2", "type": "transform", "direction": "left_to_right", "label": "transforms", "main_chain": True}
            ],
            "final_text": [
                {"id": "P07-T01", "text": "Governed input"},
                {"id": "P07-T02", "text": "Traceable result"},
            ],
            "generation_handoff": {
                "required_text_ids": ["P07-T01", "P07-T02"],
                "required_text": ["Governed input", "Traceable result"],
                "title_exclusion_instruction": "Do not render title or subtitle.",
            },
            "avoid": ["Do not create an independent text wall."],
        }
        return handoff_page, visual_page, style_lock

    def test_builds_nine_section_projection_without_backend_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff_page, visual_page, style_lock = self._inputs(root)

            spec = build_page_artifact_spec(
                handoff_page=handoff_page,
                visual_page=visual_page,
                style_lock=style_lock,
                handoff_sha256="a" * 64,
                visual_source_sha256="b" * 64,
                planning_policy={
                    "source_structure_mode": "locked",
                    "source_content_mode": "preserve",
                },
            )

        self.assertEqual("presentation content visual", spec.deliverable.asset_type)
        self.assertEqual((2048, 1024, "2:1"), spec.deliverable.canvas)
        self.assertEqual(handoff_page["page_mission"], spec.communication_goal.page_mission)
        self.assertEqual(visual_page["visual_decision"]["visual_thesis"], spec.visual_thesis)
        self.assertEqual(("Governed input", "Traceable result"), spec.typography.visible_text)
        self.assertEqual("Governance operations hub", spec.visual_carrier.business_object)
        self.assertTrue(spec.visual_carrier.use_scene)
        self.assertEqual("Pure white editorial art direction.", spec.art_direction.contract)
        relationship = spec.relationships[0]
        self.assertEqual("项目", relationship.subject)
        self.assertEqual("has_goal", relationship.relation)
        self.assertEqual(("统一服务入口",), relationship.objects)
        self.assertEqual("subject_to_objects", relationship.direction)
        self.assertEqual("explicit", relationship.basis)
        self.assertEqual("high", relationship.confidence)
        self.assertIn(
            "Preserve the approved source actors, relationships, conditions, status, and factual strength without reinterpretation.",
            spec.hard_constraints.page_constraints,
        )
        self.assertEqual(
            "a directed business flow moving input through processing to "
            "result, read as one continuous left-to-right flow",
            spec.composition.topology,
        )
        self.assertIn(
            "Do not render the nodes as equal-weight peer cards; the declared relationship is not a flat list.",
            spec.hard_constraints.page_constraints,
        )
        self.assertIn(
            "Do not invent a center hub or radial mechanism the declared relationship does not describe.",
            spec.hard_constraints.page_constraints,
        )

        serialized = json.dumps(spec.to_dict(), ensure_ascii=False)
        for backend_id in (
            "E1",
            "E2",
            "P07-T01",
            "P07-T02",
            "P07-TITLE",
            "ST0002",
            "rel-0001",
            "directed_flow",
            "equal_peer_cards",
            "invented_center_hub",
        ):
            self.assertNotIn(backend_id, serialized)
        self.assertNotIn("Do not discuss the next chapter", serialized)

    def test_rejects_missing_topology(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff_page, visual_page, style_lock = self._inputs(root)
            del visual_page["semantic_graph"]["topology"]

            with self.assertRaisesRegex(ValueError, "topology"):
                build_page_artifact_spec(
                    handoff_page=handoff_page,
                    visual_page=visual_page,
                    style_lock=style_lock,
                    handoff_sha256="a" * 64,
                    visual_source_sha256="b" * 64,
                )

    def test_rejects_an_unmapped_topology_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff_page, visual_page, style_lock = self._inputs(root)
            visual_page["semantic_graph"]["topology"] = "not_a_real_topology"

            with self.assertRaisesRegex(ValueError, "unmapped topology"):
                build_page_artifact_spec(
                    handoff_page=handoff_page,
                    visual_page=visual_page,
                    style_lock=style_lock,
                    handoff_sha256="a" * 64,
                    visual_source_sha256="b" * 64,
                )

    def test_rejects_an_unmapped_forbidden_structure_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff_page, visual_page, style_lock = self._inputs(root)
            visual_page["semantic_graph"]["forbidden_structures"] = ["not_a_real_forbidden_structure"]

            with self.assertRaisesRegex(ValueError, "unmapped forbidden-structure"):
                build_page_artifact_spec(
                    handoff_page=handoff_page,
                    visual_page=visual_page,
                    style_lock=style_lock,
                    handoff_sha256="a" * 64,
                    visual_source_sha256="b" * 64,
                )

    def test_rejects_business_relationship_drift_between_handoff_and_visual_spec(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff_page, visual_page, style_lock = self._inputs(root)
            changed_visual = deepcopy(visual_page)
            changed_visual["semantic_graph"]["business_relationships"][0]["objects"] = [
                "未经授权的其他目标"
            ]

            with self.assertRaisesRegex(ValueError, "business relationship"):
                build_page_artifact_spec(
                    handoff_page=handoff_page,
                    visual_page=changed_visual,
                    style_lock=style_lock,
                    handoff_sha256="a" * 64,
                    visual_source_sha256="b" * 64,
                )

    def test_legacy_empty_handoff_can_use_visual_decision_relationship(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff_page, visual_page, style_lock = self._inputs(root)
            handoff_page["stage02_visual_input"]["business_relationships"] = []
            del visual_page["semantic_graph"]["business_relationships"]

            spec = build_page_artifact_spec(
                handoff_page=handoff_page,
                visual_page=visual_page,
                style_lock=style_lock,
                handoff_sha256="a" * 64,
                visual_source_sha256="b" * 64,
            )

        self.assertEqual(
            "Governance hub transforms input into traceable result",
            spec.relationships[0].subject,
        )
        self.assertEqual("", spec.relationships[0].relation)
        self.assertEqual((), spec.relationships[0].objects)

    def test_rejects_cross_artifact_content_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff_page, visual_page, style_lock = self._inputs(root)
            visual_page["core_judgment"] = "Different judgment"

            with self.assertRaisesRegex(ValueError, "core judgment"):
                build_page_artifact_spec(
                    handoff_page=handoff_page,
                    visual_page=visual_page,
                    style_lock=style_lock,
                    handoff_sha256="a" * 64,
                    visual_source_sha256="b" * 64,
                )

    def test_project_loader_requires_visual_specs_only_for_content_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            handoff_page, visual_page, style_lock = self._inputs(project)
            handoff_path = project / "workbench/stages/02-handoff/stage02-handoff.json"
            handoff_path.parent.mkdir(parents=True)
            handoff_path.write_text("{}\n", encoding="utf-8")
            visual_path = project / "visual/deck-visual-spec.json"
            visual_path.parent.mkdir(parents=True)
            visual_path.write_text(json.dumps({"pages": [visual_page]}), encoding="utf-8")
            payload = {
                "pages": [
                    {"page_id": "p01", "page_number": 1, "render_role": "cover"},
                    handoff_page,
                ]
            }
            with patch("cyberppt.stage02_handoff.load_stage02_handoff", return_value=payload):
                specs = load_project_page_artifact_specs(project, style_lock=style_lock)

        self.assertEqual([7], sorted(specs))


if __name__ == "__main__":
    unittest.main()
