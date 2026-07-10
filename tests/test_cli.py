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
from cyberppt.commands.analysis_expression_gate import stage_analysis_artifact
from cyberppt.commands.init_project import init_project
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

    def test_help_lists_analysis_expression_commands(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("stage-business-script", help_text)
        self.assertIn("analysis-expression-status", help_text)
        self.assertIn("adopt-analysis-expression-contract", help_text)

    def test_analysis_expression_status_json_includes_pending_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "client-report"
            init_project(project)
            source = (
                "## 汇报对象\n分管领导\n## 汇报目的\n审定工作安排\n## 内容重点\n供需研判\n"
                "## 证据\n预测数据\n## 优势\n基础扎实\n## 边界\n不替代执行方案\n"
                "## 推荐方向\n领导审定型\n"
            )
            stage_analysis_artifact(
                project,
                "reporting_direction",
                source,
                "领导审定型",
                [
                    {"id": "leadership_review", "label": "领导审定型"},
                    {"id": "execution_alignment", "label": "执行对齐型"},
                ],
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                code = main(["analysis-expression-status", str(project), "--json"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(3, code)
        self.assertEqual("reporting_direction", payload["next_gate"])
        self.assertEqual("pending_confirmation", payload["gates"]["reporting_direction"]["status"])
        self.assertIn("question", payload["gates"]["reporting_direction"])
        self.assertEqual([], payload["gates"]["reporting_direction"]["validation_failures"])
        self.assertEqual("leadership_review", payload["gates"]["reporting_direction"]["options"][0]["id"])

    def test_final_script_pages_requires_explicit_style_choice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            script = root / "script-final.md"
            script.write_text("## 第3页：测试页\n组件A：内容\n", encoding="utf-8")
            buffer = io.StringIO()

            with redirect_stderr(buffer):
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
