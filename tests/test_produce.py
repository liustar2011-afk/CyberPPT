from __future__ import annotations

import io
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from cyberppt.cli import main
from cyberppt.commands.analysis_expression_gate import approve_analysis_artifact, stage_analysis_artifact
from cyberppt.commands.blueprint_gate import (
    approve_blueprint_image_review,
    approve_blueprint_input,
    approve_speaker_notes_review,
    approve_visual_style,
    stage_blueprint_image_review,
    stage_blueprint_input,
    stage_speaker_notes_review,
    stage_visual_style_options,
)
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.init_project import init_project
from cyberppt.commands.produce import assemble_production, get_production_status, prepare_production


OPTIONS = [
    {"id": "leadership_review", "label": "领导审定型"},
    {"id": "execution_alignment", "label": "执行对齐型"},
]


def _approve_analysis(project: Path) -> None:
    artifacts = (
        (
            "source_analysis",
            "## 输入盘点\n年度供需预测报告\n## 证据表\n| ID | 论点 | 来源位置 |\n|---|---|---|\n| E01 | 供需总体平衡 | 年度供需预测报告第3页 |\n"
            "## 开放数据冲突\n无重大冲突\n## 内容脑暴\n领导审定型、执行对齐型\n## 页面物料池\n最大负荷、供需平衡\n",
            "evidence complete",
        ),
        (
            "reporting_direction",
            "## 汇报对象\n分管领导\n## 汇报目的\n审定工作安排\n## 内容重点\n供需研判\n"
            "## 证据\n预测数据\n## 优势\n基础扎实\n## 边界\n不替代执行方案\n## 推荐方向\n领导审定型\n",
            "领导审定型",
        ),
        (
            "report_structure",
            "## 模块一\n形势研判\n## 模块二\n供需预测\n## 模块三\n风险提示\n## 模块四\n工作安排\n",
            "four modules",
        ),
        (
            "page_design",
            "## 封面\n项目名称\n## 目录\n章节导航\n## 过渡页\n进入供需预测\n## 内容页\n供需预测结论\n## 封底\n请审阅\n",
            "page design",
        ),
        (
            "business_script",
            "## 第1页：章节过渡\n第一章\n### 非上屏：证据链\n- E-01\n"
            "### 来源位置\n- 年度供需预测报告第3页\n### 非上屏：完整性校核\n- 本页不承载业务内容。\n",
            "business script",
        ),
    )
    for gate, source, recommendation in artifacts:
        stage_analysis_artifact(project, gate, source, recommendation, OPTIONS)
        approve_analysis_artifact(project, gate, "leadership_review")


def _approved_project() -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    temporary_directory = tempfile.TemporaryDirectory()
    root = Path(temporary_directory.name)
    project = root / "client-report"
    init_project(project)
    _approve_analysis(project)
    script = root / "script-final.md"
    script.write_text("## 第1页：测试\n组件A：内容\n", encoding="utf-8")
    stage_visual_style_options(project)
    approve_visual_style(project, "style_4")
    stage_blueprint_input(
        project,
        script.read_text(encoding="utf-8"),
        "confirm_blueprint_input",
        [
            {"id": "confirm_blueprint_input", "label": "确认蓝图输入"},
            {"id": "revise_blueprint_input", "label": "返回调整"},
        ],
    )
    approve_blueprint_input(project, "confirm_blueprint_input")
    return project, temporary_directory


class ProduceTests(unittest.TestCase):
    def test_prepare_production_stages_inputs_and_speaker_notes_confirmation(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            summary = prepare_production(project, "1")

            self.assertEqual("production_inputs_prepared", summary["status"])
            self.assertTrue(Path(summary["artifacts"]["template_text_lock"]).is_file())
            self.assertTrue(Path(summary["artifacts"]["speaker_notes_pending_confirmation"]).is_file())
            self.assertTrue(Path(summary["artifacts"]["production_prepare"]).is_file())
            self.assertEqual(
                "speaker_notes_approval_required",
                get_production_status(project, "1")["next_gate"],
            )

    def test_status_json_and_prepare_commands_are_available(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            prepare_output = io.StringIO()
            with redirect_stdout(prepare_output):
                prepare_code = main(["produce", "prepare", str(project), "--pages", "1"])

            status_output = io.StringIO()
            with redirect_stdout(status_output):
                status_code = main(["produce", "status", str(project), "--pages", "1", "--json"])

            self.assertEqual(0, prepare_code)
            self.assertEqual(0, status_code)
            self.assertEqual("production_inputs_prepared", json.loads(prepare_output.getvalue())["status"])
            self.assertEqual("speaker_notes_approval_required", json.loads(status_output.getvalue())["next_gate"])

    def test_final_script_pages_rejects_production_build_with_produce_assemble_recovery(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            approved_input = project / "workbench/stages/02-blueprint-dual-image/blueprint_input.md"
            with self.assertRaisesRegex(ValueError, "produce assemble"):
                run_final_script_pages(project=project, script=approved_input, pages_raw="1", production_build=True)

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(
                    [
                        "final-script-pages",
                        str(project),
                        "--script",
                        str(approved_input),
                        "--pages",
                        "1",
                        "--production-build",
                    ]
                )

            self.assertEqual(2, code)
            self.assertIn("produce assemble", stderr.getvalue())

    def test_assemble_rejects_zero_return_code_without_required_artifacts(self) -> None:
        project, temporary_directory = _approved_project()
        with temporary_directory:
            prepared = prepare_production(project, "1")
            pairs = Path(prepared["artifacts"]["page_image_pairs"])
            manifest = json.loads(pairs.read_text(encoding="utf-8"))
            for pair in manifest["pairs"]:
                Path(pair["full"]["path"]).write_bytes(b"approved-image")
            stage_blueprint_image_review(project, pairs)
            approve_blueprint_image_review(project, "confirm_blueprint_images")
            notes = Path(prepared["artifacts"]["speaker_notes_manifest"])
            stage_speaker_notes_review(project, notes, "1")
            approve_speaker_notes_review(project, "confirm_speaker_notes")

            with patch("cyberppt.commands.produce.subprocess.run", return_value=Mock(returncode=0)):
                with self.assertRaisesRegex(RuntimeError, "assembly_artifact_missing"):
                    assemble_production(project, "1")


if __name__ == "__main__":
    unittest.main()
