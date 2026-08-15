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
        self.assertIn("outline-audit", help_text)
        self.assertIn("source-truth-audit", help_text)
        self.assertIn("prepare-source-map", help_text)
        self.assertIn("source-map-check", help_text)
        self.assertIn("prepare-semantic-understanding", help_text)
        self.assertIn("semantic-check", help_text)
        self.assertIn("script-audit", help_text)
        self.assertIn("prepare-visual-structure", help_text)
        self.assertIn("record-visual-structure-execution", help_text)
        self.assertIn("visual-structure-audit", help_text)
        self.assertIn("run-autonomous", help_text)

    def test_run_autonomous_accepts_contract_and_image_switch(self) -> None:
        args = build_parser().parse_args(
            ["run-autonomous", "contract.json", "--skip-image-generation", "--image-timeout", "120", "--resume"]
        )

        self.assertEqual("contract.json", args.contract)
        self.assertTrue(args.skip_image_generation)
        self.assertTrue(args.resume)
        self.assertEqual(120, args.image_timeout)

    def test_script_audit_accepts_contract_options(self) -> None:
        args = build_parser().parse_args(
            [
                "script-audit",
                "project",
                "--input",
                "script.md",
                "--outline",
                "outline.json",
                "--source-truth",
                "source-truth.json",
            ]
        )

        self.assertEqual("outline.json", args.outline)
        self.assertEqual("source-truth.json", args.source_truth)

    def test_lightweight_init_omits_control_and_stage02_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "lightweight"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["init", str(project)])

            self.assertEqual(0, code)
            self.assertIn("mode: lightweight", (project / "manifest.yml").read_text(encoding="utf-8"))
            self.assertTrue((project / "workbench/stages/01-analysis").is_dir())
            self.assertTrue((project / "workbench/scripts/drafts").is_dir())
            self.assertFalse((project / "workbench/artifact-ledger.json").exists())
            self.assertFalse((project / "workbench/approvals").exists())
            self.assertFalse((project / "workbench/decisions").exists())
            self.assertFalse((project / "workbench/runs").exists())
            self.assertFalse((project / "workbench/stages/02-visual").exists())
            self.assertFalse((project / "workbench/stages/01-analysis/outline-attempts").exists())

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

    def test_script_audit_input_error_returns_two(self) -> None:
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = main(
                [
                    "script-audit",
                    "missing-project",
                    "--input",
                    "missing-script.md",
                ]
            )

        self.assertEqual(2, code)
        self.assertIn("project does not exist", buffer.getvalue())

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

    def test_outline_audit_accepts_source_truth_option(self) -> None:
        args = build_parser().parse_args(
            [
                "outline-audit",
                "project",
                "--input",
                "outline.json",
                "--source-truth",
                "source-truth.json",
            ]
        )

        self.assertEqual("source-truth.json", args.source_truth)

    def test_outline_audit_returns_rewrite_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            outline = root / "outline.json"
            outline.write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.outline.v1",
                        "material_type": "建设方案",
                        "audience": "项目组内部讨论",
                        "architecture_mode": "consulting",
                        "architecture_reason": "default",
                        "user_requested_architecture": False,
                        "source_section_weights": {},
                        "pages": [],
                        "retry": {"attempt": 1, "max_attempts": 3, "strategy": "consulting_default"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["outline-audit", str(project), "--input", str(outline)])
        self.assertEqual(4, code)
        self.assertIn('"status": "rewrite_required"', buffer.getvalue())

    def test_final_script_pages_requires_stage02_handoff_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            script = root / "script-final.md"
            script.write_text("## 第3页：测试页\n组件A：内容\n", encoding="utf-8")
            buffer = io.StringIO()

            with (
                patch(
                    "cyberppt.commands.script_audit.run_script_audit",
                    return_value=(0, {"status": "passed"}),
                ),
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
        self.assertIn("Stage 02 handoff is missing requested page 3", buffer.getvalue())

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
