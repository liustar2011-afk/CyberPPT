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
        self.assertIn("rebuild-dual-image", help_text)
        self.assertIn("final-script-pages", help_text)
        self.assertIn("outline-audit", help_text)
        self.assertIn("source-truth-audit", help_text)
        self.assertIn("prepare-semantic-understanding", help_text)
        self.assertIn("semantic-check", help_text)
        self.assertIn("record-semantic-generation", help_text)
        self.assertIn("approve-semantic-understanding", help_text)
        self.assertIn("script-audit", help_text)
        self.assertIn("prepare-chapter-review", help_text)
        self.assertIn("chapter-review-audit", help_text)
        self.assertIn("prepare-visual-structure", help_text)
        self.assertIn("visual-structure-audit", help_text)

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
                "--attempt",
                "2",
            ]
        )

        self.assertEqual("outline.json", args.outline)
        self.assertEqual("source-truth.json", args.source_truth)
        self.assertEqual(2, args.attempt)

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

    def test_final_script_pages_requires_explicit_style_choice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            script = root / "script-final.md"
            script.write_text("## 第3页：测试页\n组件A：内容\n", encoding="utf-8")
            buffer = io.StringIO()

            with (
                patch(
                    "cyberppt.stage01_controls.assert_escalation_resolved"
                ),
                patch(
                    "cyberppt.stage01_controls.assert_stage01_script_approval"
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
                    ]
                )

        self.assertEqual(2, code)
        self.assertIn("请选择一个 CyberPPT 默认视觉风格", buffer.getvalue())
        self.assertIn("4. 象牙白 + 深蓝强调", buffer.getvalue())

    def test_rebuild_dual_image_routes_to_template_rebuild(self) -> None:
        with patch("cyberppt.cli.run_script", return_value=3) as run_script:
            code = main(["rebuild-dual-image", "page_image_pairs.json", "--no-export"])

        self.assertEqual(3, code)
        run_script.assert_called_once_with("template-rebuild", ["page_image_pairs.json", "--no-export"])

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

    def test_image_ppt_help_is_forwarded_to_underlying_script(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "cyberppt", "image-ppt", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Generate image-based PPT inside the CEC template", completed.stdout)
