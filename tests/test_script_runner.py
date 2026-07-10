from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from cyberppt.commands.analysis_expression_gate import adopt_analysis_expression_contract
from cyberppt.commands.script_runner import SCRIPT_ALIASES, run_script, script_path


class ScriptRunnerTests(unittest.TestCase):
    def test_known_aliases_resolve_to_existing_files(self) -> None:
        for alias in SCRIPT_ALIASES:
            self.assertTrue(script_path(alias).exists(), alias)

    def test_body_blueprint_prompt_alias_is_registered(self) -> None:
        self.assertEqual("body_blueprint_prompt.py", script_path("body-blueprint-prompts").name)

    def test_pair_manifest_alias_is_registered(self) -> None:
        self.assertEqual("cyberppt_pair_manifest.py", script_path("pair-manifest").name)

    def test_image_ppt_alias_is_registered(self) -> None:
        path = script_path("image-ppt")

        self.assertEqual("template_image_ppt_export.py", path.name)

    def test_unknown_alias_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            script_path("missing-command")

    def test_project_bearing_stage_2_generation_aliases_require_analysis_approval(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            adopt_analysis_expression_contract(project)

            for alias in ("body-blueprint-prompts", "image-ppt", "pair-manifest", "source-capture", "template-rebuild"):
                with self.subTest(alias):
                    with patch("cyberppt.commands.script_runner.subprocess.run") as run:
                        with self.assertRaisesRegex(ValueError, "source_analysis approval is required"):
                            run_script(alias, ["--project-path", str(project)])

                    run.assert_not_called()

    def test_generation_alias_rejects_unapproved_equals_form_project_path_before_subprocess(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            adopt_analysis_expression_contract(project)

            with patch("cyberppt.commands.script_runner.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "source_analysis approval is required"):
                    run_script("pair-manifest", [f"--project-path={project}"])

            run.assert_not_called()
