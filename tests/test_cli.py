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
from cyberppt.commands.analysis_expression_gate import approve_analysis_artifact, stage_analysis_artifact
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
        self.assertIn("final-script-pages", help_text)
        self.assertIn("produce", help_text)

    def test_legacy_rebuild_is_not_registered(self) -> None:
        help_text = build_parser().format_help()

        self.assertNotIn("template-rebuild", SCRIPT_ALIASES)
        self.assertNotIn("template-rebuild", help_text)
        self.assertNotIn("rebuild-dual-image", help_text)

    def test_help_lists_analysis_expression_commands(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("stage-business-script", help_text)
        self.assertIn("analysis-expression-status", help_text)
        self.assertIn("adopt-analysis-expression-contract", help_text)

    def test_help_lists_speaker_notes_review_commands(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("stage-speaker-notes-review", help_text)
        self.assertIn("approve-speaker-notes-review", help_text)
        self.assertIn("image-text-qa", help_text)

    def test_imagegen_run_rejects_free_prompt(self) -> None:
        with self.assertRaises(SystemExit) as raised, redirect_stderr(io.StringIO()):
            main(["imagegen-run", "/tmp/project", "--pages", "4", "--prompt", "free text"])

        self.assertEqual(2, raised.exception.code)

    def test_imagegen_run_rejects_prompt_file(self) -> None:
        with self.assertRaises(SystemExit) as raised, redirect_stderr(io.StringIO()):
            main(["imagegen-run", "/tmp/project", "--pages", "4", "--prompt-file", "/tmp/prompt.txt"])

        self.assertEqual(2, raised.exception.code)

    def test_imagegen_run_rejects_output_override(self) -> None:
        with self.assertRaises(SystemExit) as raised, redirect_stderr(io.StringIO()):
            main(["imagegen-run", "/tmp/project", "--pages", "4", "--out", "/tmp/override.png"])

        self.assertEqual(2, raised.exception.code)

    def test_imagegen_run_rejects_multi_page_selection(self) -> None:
        buffer = io.StringIO()

        with redirect_stderr(buffer):
            code = main(["imagegen-run", "/tmp/project", "--pages", "4-5"])

        self.assertEqual(2, code)
        self.assertIn("imagegen-run accepts exactly one page", buffer.getvalue())

    def test_image_text_qa_command_writes_summary_from_fixture_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / "workbench/stages/02-blueprint-dual-image/pages_001_001"
            stage.mkdir(parents=True)
            image = stage / "page_001_测试_full.png"
            image.write_bytes(b"full-image")
            script = stage / "imagegen_script.md"
            script.write_text(
                """## 第1页：测试

【页面类型】
本页类型：内容页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 资源保障
- 风险管控

【构图指令】
生成正文内容区。

【结构密度】
- 两项并列
""",
                encoding="utf-8",
            )
            (stage / "page_image_pairs.json").write_text(
                json.dumps(
                    {
                        "imagegen_script": str(script),
                        "pairs": [{"page_number": 1, "full": {"path": str(image)}}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ocr = root / "ocr.json"
            ocr.write_text(json.dumps({"1": "资源保障\n风险管控"}, ensure_ascii=False), encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["image-text-qa", str(root), "--pages", "1", "--ocr-json", str(ocr)])

            summary_path = stage / "image_text_qa/image_text_qa_summary.json"
            self.assertEqual(0, code)
            self.assertTrue(summary_path.is_file())
            self.assertEqual("passed", json.loads(summary_path.read_text(encoding="utf-8"))["status"])

    def test_speaker_notes_review_commands_print_record_paths(self) -> None:
        pending = Path("/tmp/speaker_notes_review.pending-confirmation.json")
        approval = Path("/tmp/speaker_notes_review.approved.json")
        output = io.StringIO()

        with (
            patch("cyberppt.cli.stage_speaker_notes_review", return_value=pending) as stage,
            redirect_stdout(output),
        ):
            stage_code = main(
                [
                    "stage-speaker-notes-review",
                    "/tmp/project",
                    "--manifest",
                    "/tmp/speaker_notes_manifest.json",
                    "--pages",
                    "1-3",
                ]
            )

        self.assertEqual(0, stage_code)
        self.assertIn(str(pending), output.getvalue())
        stage.assert_called_once_with(Path("/tmp/project"), Path("/tmp/speaker_notes_manifest.json"), "1-3")

        output = io.StringIO()
        with (
            patch("cyberppt.cli.approve_speaker_notes_review", return_value=approval) as approve,
            redirect_stdout(output),
        ):
            approve_code = main(
                [
                    "approve-speaker-notes-review",
                    "/tmp/project",
                    "--option-id",
                    "confirm_speaker_notes",
                    "--note",
                    "ready",
                ]
            )

        self.assertEqual(0, approve_code)
        self.assertIn(str(approval), output.getvalue())
        approve.assert_called_once_with(Path("/tmp/project"), "confirm_speaker_notes", "ready")

    def test_produce_verify_routes_to_status_machine(self) -> None:
        output = io.StringIO()
        with (
            patch(
                "cyberppt.cli.verify_production",
                return_value={"schema": "cyberppt.production_readiness.v1", "status": "deliverable_ready"},
            ) as verify,
            redirect_stdout(output),
        ):
            code = main(["produce", "verify", "/tmp/project", "--pages", "1"])

        self.assertEqual(0, code)
        self.assertEqual("deliverable_ready", json.loads(output.getvalue())["status"])
        verify.assert_called_once_with(Path("/tmp/project"), "1")

    def test_production_alias_help_requires_explicit_project(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()

        for alias in (
            "body-blueprint-prompts",
            "image-ppt",
            "pair-manifest",
            "speaker-notes",
        ):
            with self.subTest(alias):
                self.assertIn(f"{alias} requires --project <path>", help_text)

    def test_analysis_expression_status_json_includes_pending_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "client-report"
            init_project(project)
            stage_analysis_artifact(
                project,
                "source_analysis",
                "## 输入盘点\n源文件\n## 证据表\n| ID | 论点 | 来源位置 |\n|---|---|---|\n| E01 | 供需平衡 | 第3页 |\n"
                "## 开放数据冲突\n无\n## 内容脑暴\n方向比较\n## 页面物料池\n供需平衡\n",
                "证据完整",
                [{"id": "leadership_review", "label": "领导审定型"}],
            )
            approve_analysis_artifact(project, "source_analysis", "leadership_review")
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

    def test_image_ppt_help_requires_project_context(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "cyberppt", "image-ppt", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("production-capable aliases require exactly one --project <path>", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
