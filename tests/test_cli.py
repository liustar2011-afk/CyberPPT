from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cyberppt.cli import build_parser, main
from cyberppt.commands.script_runner import SCRIPT_ALIASES


class CliTests(unittest.TestCase):
    def test_help_returns_success(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main([])
        self.assertEqual(code, 0)
        self.assertIn("CyberPPT product tooling", buffer.getvalue())

    def test_doctor_returns_success(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["doctor"])
        self.assertEqual(code, 0)
        self.assertIn("palette_samples: ok", buffer.getvalue())

    def test_all_script_aliases_are_registered(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()
        for alias in SCRIPT_ALIASES:
            self.assertIn(alias, help_text)
        self.assertIn("stage-script", help_text)
        self.assertIn("approve-script", help_text)
        self.assertIn("script-status", help_text)
        self.assertIn("image-to-editable-svg", help_text)
        self.assertNotIn("rebuild-dual-image", help_text)
        self.assertIn("final-script-pages", help_text)
        self.assertIn("enhance-image", help_text)
        self.assertIn("source-truth-audit", help_text)
        self.assertIn("project-foundation", help_text)
        self.assertIn("prepare-source-map", help_text)
        self.assertIn("prepare-source-context", help_text)
        self.assertIn("prepare-script-foundation", help_text)
        self.assertIn("source-map-check", help_text)
        self.assertIn("prepare-semantic-understanding", help_text)
        self.assertIn("semantic-check", help_text)
        self.assertIn("prepare-visual-structure", help_text)
        self.assertIn("record-visual-structure-execution", help_text)
        self.assertIn("visual-structure-audit", help_text)
        self.assertIn("prepare-stage02-handoff", help_text)

    def test_default_init_uses_strict_profile_without_runtime_control_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "strict-default"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["init", str(project)])

            self.assertEqual(0, code)
            self.assertIn("mode: lightweight", (project / "manifest.yml").read_text(encoding="utf-8"))
            self.assertIn("profile: strict", (project / "manifest.yml").read_text(encoding="utf-8"))
            self.assertIn("source_truth:", (project / "manifest.yml").read_text(encoding="utf-8"))
            self.assertTrue((project / "script/.cache").is_dir())
            self.assertFalse((project / "workbench").exists())
            readme = (project / "README.md").read_text(encoding="utf-8")
            self.assertIn("project-foundation", readme)
            self.assertNotIn("prepare-script-foundation", readme)
            self.assertFalse((project / "workbench/artifact-ledger.json").exists())
            self.assertFalse((project / "workbench/approvals").exists())
            self.assertFalse((project / "workbench/decisions").exists())
            self.assertFalse((project / "workbench/runs").exists())
            self.assertFalse((project / "workbench/stages/02-visual").exists())
            self.assertFalse((project / "workbench/stages/01-analysis/outline-attempts").exists())

    def test_explicit_script_init_keeps_lightweight_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "script"
            self.assertEqual(0, main(["init", str(project), "--profile", "script"]))

            manifest = (project / "manifest.yml").read_text(encoding="utf-8")
            readme = (project / "README.md").read_text(encoding="utf-8")
            self.assertIn("profile: script", manifest)
            self.assertNotIn("source_truth:", manifest)
            self.assertIn("prepare-script-foundation", readme)
            self.assertIn("do not run `prepare-source-map`", readme)
            self.assertIn("or `project-foundation`", readme)

    def test_lightweight_semantic_prepare_prints_plain_task_without_json_duplication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "lightweight"
            self.assertEqual(0, main(["init", str(project)]))
            (project / "source/material.txt").write_text(
                "source-native cooperation arrangement", encoding="utf-8"
            )
            self.assertEqual(0, main(["prepare-source-map", str(project)]))
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(
                    [
                        "prepare-semantic-understanding",
                        str(project),
                    ]
                )

            output = buffer.getvalue()
            self.assertEqual(0, code)
            self.assertTrue(output.startswith("# CyberPPT whole-document semantic model task"))
            self.assertIn("source-native cooperation arrangement", output)
            self.assertNotIn('"authoring_task":', output)
            self.assertNotIn("source_bundle_sha256", output)

    def test_source_truth_audit_returns_audit_exit_code(self) -> None:
        buffer = io.StringIO()
        with (
            patch(
                "cyberppt.cli.run_source_truth_audit",
                return_value=(4, {"status": "rewrite_required"}),
            ),
            redirect_stdout(buffer),
        ):
            code = main(
                [
                    "source-truth-audit",
                    "project",
                    "--input",
                    "source-truth.json",
                ]
            )
        self.assertEqual(4, code)
        self.assertIn('"status": "rewrite_required"', buffer.getvalue())

    def test_project_foundation_help_explains_strict_migration(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as raised:
                main(["project-foundation", "--help"])
        self.assertEqual(0, raised.exception.code)
        output = buffer.getvalue()
        self.assertIn("source_consumption_policy='required'", output)
        self.assertIn("one-way strict-mode migration", output)

    def test_project_foundation_warns_before_overwriting_legacy_foundation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            input_path = project / "workbench/stages/01-analysis/source-truth.json"
            output_path = project / "script/foundation.json"
            input_path.parent.mkdir(parents=True)
            output_path.parent.mkdir(parents=True)
            input_path.write_text(
                json.dumps({"sources": [], "records": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            output_path.write_text(
                json.dumps({"sources": [], "facts": [], "concepts": [], "relations": [], "arguments": []}),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["project-foundation", str(project)])

            self.assertEqual(0, code)
            self.assertIn("source_consumption_contract_version=2", stderr.getvalue())
            projected = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual("required", projected["source_consumption_policy"])
            self.assertEqual(2, projected["source_consumption_contract_version"])

    def test_stage02_handoff_check_no_write_keeps_receipt_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            receipt = project / "workbench/stages/02-handoff/stage02-handoff-audit.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text('{"status":"old"}\n', encoding="utf-8")
            report = {"status": "passed", "blocking_issues": []}
            with patch("cyberppt.cli.audit_stage02_handoff", return_value=report):
                code = main(["stage02-handoff-check", str(project), "--no-write"])

            self.assertEqual(0, code)
            self.assertEqual('{"status":"old"}\n', receipt.read_text(encoding="utf-8"))

    def test_prepare_source_map_command_compiles_stable_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "source").mkdir(parents=True)
            (project / "source" / "material.md").write_text(
                "# 主张\n证据。\n",
                encoding="utf-8",
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["prepare-source-map", str(project)])

            self.assertEqual(0, code)
            self.assertTrue(
                (project / "workbench/stages/00-source-map/source-units.jsonl").is_file()
            )
            self.assertIn('"status": "passed"', buffer.getvalue())

    def test_script_profile_commands_build_one_cache_then_print_foundation_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "source").mkdir(parents=True)
            (project / "source/material.md").write_text(
                "# 总体判断\n来源证据。\n", encoding="utf-8"
            )
            context_output = io.StringIO()
            with redirect_stdout(context_output):
                context_code = main(["prepare-source-context", str(project)])

            report = json.loads(context_output.getvalue())
            self.assertEqual(0, context_code)
            self.assertEqual("cyberppt.source_index.v2", report["schema"])
            self.assertTrue((project / "script/.cache/source-index.json").is_file())
            self.assertFalse((project / "workbench/stages/00-source-map").exists())

            task_output = io.StringIO()
            with redirect_stdout(task_output):
                task_code = main(["prepare-script-foundation", str(project)])

            self.assertEqual(0, task_code)
            self.assertIn("Foundation authoring task", task_output.getvalue())
            self.assertIn("来源证据", task_output.getvalue())

    def test_final_script_pages_requires_stage02_handoff_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            script = root / "script-final.md"
            script.write_text("## 第3页：测试页\n组件A：内容\n", encoding="utf-8")
            buffer = io.StringIO()

            with (
                patch(
                    "cyberppt.stage02_handoff.load_stage02_handoff",
                    return_value={},
                ),
                patch(
                    "cyberppt.commands.visual_structure_stage.assert_visual_structure_ready"
                ),
                redirect_stderr(buffer),
            ):
                code = main(
                    [
                        "final-script-pages",
                        str(project),
                        "--script",
                        str(script),
                        "--pages",
                        "3",
                        "--lightweight-stage01-confirmed",
                    ]
                )

        self.assertEqual(2, code)
        self.assertNotIn("Stage 02 handoff", buffer.getvalue())

    def test_removed_dual_image_rebuild_command_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            main(["rebuild-dual-image"])

    def test_final_script_pages_external_script_is_forwarded(self) -> None:
        with patch("cyberppt.cli.run_final_script_pages", return_value={}) as runner:
            code = main(
                [
                    "final-script-pages",
                    "project",
                    "--script",
                    "external.md",
                    "--pages",
                    "1",
                    "--style-id",
                    "4",
                    "--external-script",
                ]
            )

        self.assertEqual(0, code)
        self.assertTrue(runner.call_args.kwargs["external_script"])
        self.assertEqual("image-to-editable-svg", runner.call_args.kwargs["production_mode"])
        self.assertEqual("editable", runner.call_args.kwargs["assembly_mode"])

    def test_final_script_pages_accepts_deprecated_confirmation_flag_without_forwarding(self) -> None:
        with patch("cyberppt.cli.run_final_script_pages", return_value={}) as runner:
            code = main(
                [
                    "final-script-pages",
                    "project",
                    "--script",
                    "script.md",
                    "--pages",
                    "1",
                    "--style-id",
                    "9",
                    "--lightweight-stage01-confirmed",
                ]
            )

        self.assertEqual(0, code)
        self.assertNotIn("lightweight_stage01_confirmed", runner.call_args.kwargs)

    def test_final_script_pages_rejects_blueprint_only_with_production_build(self) -> None:
        buffer = io.StringIO()
        with (
            patch("cyberppt.cli.run_final_script_pages") as run_final_script_pages,
            redirect_stderr(buffer),
        ):
            code = main(
                [
                    "final-script-pages",
                    "/tmp/project",
                    "--script",
                    "/tmp/script.md",
                    "--pages",
                    "1",
                    "--style-id",
                    "4",
                    "--blueprint-only",
                    "--production-build",
                ]
            )

        self.assertEqual(2, code)
        run_final_script_pages.assert_not_called()
        self.assertIn("--blueprint-only cannot be combined with --production-build", buffer.getvalue())

    def test_script_help_is_forwarded_to_underlying_script(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "cyberppt", "validate", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Check PPTX structure", completed.stdout)
