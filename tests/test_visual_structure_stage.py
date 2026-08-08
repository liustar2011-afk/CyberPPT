from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cyberppt.commands.init_project import init_project
from cyberppt.commands.visual_structure_stage import (
    assert_visual_structure_ready,
    visual_structure_required,
)
from cyberppt.stage02_handoff import audit_stage02_handoff


class VisualStructureStageTests(unittest.TestCase):
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
                        "stage02_visual_input": {
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

    def test_gate_binds_visual_artifacts_to_current_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            (project / "manifest.yml").write_text(
                "gates:\n  visual_structure_designer: required\n", encoding="utf-8"
            )
            script = project / "script.md"
            script.write_text("approved script\n", encoding="utf-8")
            visual = project / "visual"
            visual.mkdir()
            artifacts = {
                "spec_json": visual / "deck-visual-spec.json",
                "spec_markdown": visual / "script-visual-structure.md",
                "generation_prompts": visual / "generation-prompts.md",
            }
            for key, path in artifacts.items():
                path.write_text(key + "\n", encoding="utf-8")
            digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            (visual / "validation-report.json").write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.visual_structure_stage.v1",
                        "status": "passed",
                        "script_sha256": digest(script),
                        "artifact_sha256": {
                            key: digest(path) for key, path in artifacts.items()
                        },
                    }
                ),
                encoding="utf-8",
            )
            self.assertIsNotNone(assert_visual_structure_ready(project, script))
            script.write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                assert_visual_structure_ready(project, script)


if __name__ == "__main__":
    unittest.main()
