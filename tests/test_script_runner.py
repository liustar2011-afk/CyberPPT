from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from cyberppt.commands.analysis_expression_gate import adopt_analysis_expression_contract
from cyberppt.commands.script_runner import (
    SCRIPT_ALIASES,
    _STAGE_2_PLUS_GENERATION_ALIASES,
    run_script,
    script_path,
)


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

    def test_speaker_notes_alias_is_registered(self) -> None:
        self.assertEqual("speaker_notes.py", script_path("speaker-notes").name)

    def test_unknown_alias_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            script_path("missing-command")

    def test_generation_aliases_require_explicit_project(self) -> None:
        for alias in _STAGE_2_PLUS_GENERATION_ALIASES:
            with self.subTest(alias):
                with patch("cyberppt.commands.script_runner.subprocess.run") as run:
                    with self.assertRaises(ValueError) as error:
                        run_script(alias, ["run", "--script", "outside.md", "-o", "new-output"])

                self.assertEqual(
                    "production-capable aliases require exactly one --project <path>",
                    str(error.exception),
                )
                run.assert_not_called()

    def test_generation_alias_rejects_non_project_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with patch("cyberppt.commands.script_runner.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "CyberPPT project contract"):
                    run_script("image-ppt", ["--project", temp, "run", "--script", "outside.md", "-o", "out"])

            run.assert_not_called()

    def test_generation_alias_rejects_trailing_bare_project_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            contract = project / "workbench" / "analysis_expression" / "contract.json"
            contract.parent.mkdir(parents=True)
            contract.write_text("{}", encoding="utf-8")

            with patch("cyberppt.commands.script_runner.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "require exactly one --project"):
                    run_script("image-ppt", ["--project", str(project), "--project"])

            run.assert_not_called()

    def test_generation_alias_rejects_duplicate_project_flag_and_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            contract = project / "workbench" / "analysis_expression" / "contract.json"
            contract.parent.mkdir(parents=True)
            contract.write_text("{}", encoding="utf-8")

            with patch("cyberppt.commands.script_runner.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "require exactly one --project"):
                    run_script("image-ppt", ["--project", str(project), "--project", str(project)])

            run.assert_not_called()

    def test_generation_alias_rejects_mixed_project_option_forms(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            contract = project / "workbench" / "analysis_expression" / "contract.json"
            contract.parent.mkdir(parents=True)
            contract.write_text("{}", encoding="utf-8")

            with patch("cyberppt.commands.script_runner.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "require exactly one --project"):
                    run_script("image-ppt", [f"--project={project}", "--project", str(project)])

            run.assert_not_called()

    def test_generation_aliases_strip_explicit_project_before_forwarding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            contract = project / "workbench" / "analysis_expression" / "contract.json"
            contract.parent.mkdir(parents=True)
            contract.write_text("{}", encoding="utf-8")

            for alias in _STAGE_2_PLUS_GENERATION_ALIASES:
                with self.subTest(alias):
                    with (
                        patch("cyberppt.commands.script_runner.assert_analysis_expression_ready") as ready,
                        patch("cyberppt.commands.script_runner.subprocess.run") as run,
                    ):
                        run.return_value.returncode = 0
                        result = run_script(alias, ["--project", str(project), "run", "--script", "outside.md", "-o", "out"])

                    self.assertEqual(0, result)
                    ready.assert_called_once_with(project.resolve())
                    self.assertEqual(
                        ["run", "--script", "outside.md", "-o", "out"],
                        run.call_args.args[0][2:],
                    )

    def test_generation_alias_strips_equals_project_before_forwarding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            contract = project / "workbench" / "analysis_expression" / "contract.json"
            contract.parent.mkdir(parents=True)
            contract.write_text("{}", encoding="utf-8")

            with (
                patch("cyberppt.commands.script_runner.assert_analysis_expression_ready") as ready,
                patch("cyberppt.commands.script_runner.subprocess.run") as run,
            ):
                run.return_value.returncode = 0
                result = run_script("image-ppt", [f"--project={project}", "run", "--script", "outside.md"])

        self.assertEqual(0, result)
        ready.assert_called_once_with(project.resolve())
        self.assertEqual(["run", "--script", "outside.md"], run.call_args.args[0][2:])

    def test_non_generation_alias_forwards_project_option_unchanged(self) -> None:
        with patch("cyberppt.commands.script_runner.subprocess.run") as run:
            run.return_value.returncode = 0
            result = run_script("validate", ["--project", "/tmp/outside", "presentation.pptx"])

        self.assertEqual(0, result)
        self.assertEqual(
            ["--project", "/tmp/outside", "presentation.pptx"],
            run.call_args.args[0][2:],
        )

    def test_generation_aliases_require_analysis_approval_after_project_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "client-report"
            adopt_analysis_expression_contract(project)

            for alias in _STAGE_2_PLUS_GENERATION_ALIASES:
                with self.subTest(alias):
                    with patch("cyberppt.commands.script_runner.subprocess.run") as run:
                        with self.assertRaisesRegex(ValueError, "source_analysis approval is required"):
                            run_script(alias, ["--project", str(project)])

                    run.assert_not_called()
