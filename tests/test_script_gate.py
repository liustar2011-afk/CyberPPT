from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.commands.script_gate import approve_script, get_script_status, stage_script


class ScriptGateTests(unittest.TestCase):
    def test_init_project_creates_stage_artifact_ledger_and_stage_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"

            init_project(project)

            ledger = json.loads((project / "workbench/artifact-ledger.json").read_text(encoding="utf-8"))

            self.assertEqual("cyberppt.artifact_ledger.v1", ledger["schema"])
            self.assertEqual([], ledger["artifacts"])
            manifest = (project / "manifest.yml").read_text(encoding="utf-8")
            self.assertIn("template_text_locks: workbench/locks/template_text", manifest)
            self.assertTrue((project / "workbench/stages/01-analysis").is_dir())
            self.assertTrue((project / "workbench/stages/02-blueprint-dual-image").is_dir())
            self.assertTrue((project / "workbench/stages/03-overlay").is_dir())
            self.assertTrue((project / "workbench/stages/04-template-rebuild").is_dir())
            self.assertTrue((project / "workbench/stages/05-qa-delivery").is_dir())
            self.assertTrue((project / "workbench/runs").is_dir())
            self.assertTrue((project / "workbench/archive").is_dir())
            self.assertTrue((project / "workbench/tmp").is_dir())
            self.assertTrue((project / "workbench/locks/template_text").is_dir())

    def test_stage_script_saves_draft_and_manifest_without_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            source = Path(temp) / "build_slide_02.js"
            source.write_text("console.log('draft');\n", encoding="utf-8")

            target = stage_script(project, slide=2, kind="pptx", phase="draft", source=source)
            status = get_script_status(project, slide=2, kind="pptx")

            self.assertTrue(target.exists())
            self.assertIn("slide-02-pptx-draft.js", str(target))
            self.assertFalse(status.ready_to_generate)
            self.assertEqual(status.reason, "final script is not saved")
            self.assertTrue((project / "workbench/scripts/script-manifest.json").exists())

    def test_final_script_requires_user_approval_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            source = Path(temp) / "build_slide_02.js"
            source.write_text("console.log('final');\n", encoding="utf-8")

            stage_script(project, slide=2, kind="pptx", phase="final", source=source)
            status = get_script_status(project, slide=2, kind="pptx")
            self.assertFalse(status.ready_to_generate)
            self.assertEqual(status.reason, "user approval is not recorded")

            approval = approve_script(project, slide=2, kind="pptx", note="user confirmed")
            status = get_script_status(project, slide=2, kind="pptx")

            self.assertTrue(approval.exists())
            self.assertTrue(status.ready_to_generate)

    def test_imagegen_script_is_saved_as_plaintext_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            init_project(project)
            source = Path(temp) / "slide_02_prompt.md"
            source.write_text("# ImageGen prompt\n\n中文提示词。\n", encoding="utf-8")

            target = stage_script(project, slide=2, kind="imagegen", phase="draft", source=source)

            self.assertEqual((project / "workbench/prompts/imagegen/slide-02-imagegen-draft.md").resolve(), target)
            self.assertIn("中文提示词", target.read_text(encoding="utf-8"))
