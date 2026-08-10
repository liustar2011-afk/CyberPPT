from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from cyberppt.commands.init_project import init_project
from cyberppt.commands.visual_structure_stage import (
    VISUAL_FILES,
    _prompt_inputs_sha256,
    _sha256,
    _skill_root,
    assert_visual_structure_ready,
    visual_structure_required,
)
from cyberppt.stage02_handoff import audit_stage02_handoff
from cyberppt.stage02_handoff import _page_record
from cyberppt.script_quality_contract import ScriptPage


class VisualStructureStageTests(unittest.TestCase):
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
        self.assertEqual("advisory_only", visual["author_visual_notes_authority"])
        self.assertEqual("P06-T01", visual["locked_text_items"][0]["text_id"])
        self.assertNotIn("approved_stage01_visual_structure", visual)

    def test_handoff_audit_ignores_source_hash_drift(self) -> None:
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
                        "stage02_visual_input": {
                            "locked_text_items": [
                                {"text_id": "P01-T01", "text": "Text", "ordinal": 1}
                            ],
                            "business_relationships": [],
                            "author_visual_notes_authority": "advisory_only",
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

        self.assertEqual("passed", report["status"])
        self.assertNotIn("handoff_sha256", report)

    def test_new_projects_register_required_visual_structure_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            init_project(project)
            self.assertTrue(visual_structure_required(project))
            self.assertTrue((project / "visual").is_dir())

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
            handoff = project / "workbench" / "stages" / "02-handoff" / "stage02-handoff.json"
            handoff.parent.mkdir(parents=True)
            handoff.write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.stage02_handoff.v1",
                        "source_bindings": {"script": {"path": str(script)}},
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
                                "stage02_visual_input": {
                                    "locked_text_items": [
                                        {"text_id": "P01-T01", "text": "Text", "ordinal": 1}
                                    ],
                                    "business_relationships": [],
                                    "author_visual_notes_authority": "advisory_only",
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
            with self.assertRaisesRegex(ValueError, "prompt inputs changed"):
                assert_visual_structure_ready(project, script)


if __name__ == "__main__":
    unittest.main()
