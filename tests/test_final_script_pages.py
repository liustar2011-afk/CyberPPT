from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cyberppt.commands.analysis_expression_gate import approve_analysis_artifact, stage_analysis_artifact
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.init_project import init_project


OPTIONS = [
    {"id": "leadership_review", "label": "领导审定型"},
    {"id": "execution_alignment", "label": "执行对齐型"},
]


def _approve_all_analysis_expression_gates(project: Path) -> None:
    artifacts = (
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
            "## 第1页：供需预测分析\n### 业务内容\n2026年最大负荷预计为1000万千瓦，供需总体平衡。\n"
            "### 非上屏：证据链\n- E-01\n### 来源位置\n- 年度供需预测报告第3页\n"
            "### 非上屏：完整性校核\n- 事实：供需总体平衡\n- 数字：1000万千瓦\n- 分类：最大负荷预测\n"
            "- 边界：2026年\n- 请求事项：请审定预测结论\n### 非上屏：信息密度\n- 最少呈现3项供需指标\n",
            "business script",
        ),
        (
            "drawing_script",
            "## 第1页：供需预测分析\n### 上屏文字\n- 2026年最大负荷1000万千瓦\n- 供需总体平衡\n- 请审定预测结论\n"
            "### 组件关系\n指标卡与结论卡通过箭头关联。\n### 信息密度\n- 最少呈现3项供需指标\n"
            "### 禁止项\n- 不使用装饰性图标\n### 非上屏：证据链\n- E-01\n### 来源位置\n- 年度供需预测报告第3页\n"
            "### 非上屏：完整性校核\n- 事实：供需总体平衡\n- 数字：1000万千瓦\n- 分类：最大负荷预测\n"
            "- 边界：2026年\n- 请求事项：请审定预测结论\n",
            "drawing script",
        ),
    )
    for gate, source, recommendation in artifacts:
        stage_analysis_artifact(project, gate, source, recommendation, OPTIONS)
        approve_analysis_artifact(project, gate, "leadership_review")


class FinalScriptPagesTests(unittest.TestCase):
    def test_rejects_unapproved_new_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "reporting_direction approval is required"):
                run_final_script_pages(project=project, script=script, pages_raw="1", style_id=4)

    def test_legacy_project_remains_compatible_until_adopted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "legacy-report"
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")

            summary = run_final_script_pages(project=project, script=script, pages_raw="1", style_id=4)

        self.assertEqual([1], summary["pages"])

    def test_compiles_pages_7_8_from_final_script_with_traceable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            script = root / "script-final.md"
            script.write_text(
                """# 终稿脚本

## 第7页：态势感知能力
本页结论标题为“态势感知能力要从工具堆叠转向风险闭环”
组件A（左侧主图）——三层能力链：
数据接入、模型研判、处置反馈

## 第8页：运营保障机制
本页结论标题为“运营保障机制需要责任、流程和审计同时落地”
组件A（中部流程）——责任闭环：
授权、执行、复盘、追踪
""",
                encoding="utf-8",
            )

            summary = run_final_script_pages(project=project, script=script, pages_raw="7-8", style_id=4)

            manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text(encoding="utf-8"))
            lock = json.loads(Path(summary["artifacts"]["template_text_lock"]).read_text(encoding="utf-8"))
            visual_lock = json.loads(Path(summary["artifacts"]["visual_style_lock"]).read_text(encoding="utf-8"))
            prompt = Path(summary["artifacts"]["compiled_deliverable_prompt"]).read_text(encoding="utf-8")
            ledger = json.loads((project / "workbench/artifact-ledger.json").read_text(encoding="utf-8"))

            self.assertEqual([7, 8], summary["pages"])
            self.assertEqual([7, 8], [pair["page_number"] for pair in manifest["pairs"]])
            self.assertEqual(4, visual_lock["style"]["id"])
            self.assertEqual(manifest["style_lock"], summary["artifacts"]["visual_style_lock"])
            self.assertIn("象牙白 + 深蓝强调", prompt)
            self.assertIn("#12355B", prompt)
            self.assertEqual("态势感知能力要从工具堆叠转向风险闭环", lock["records"][0]["title"])
            self.assertEqual("运营保障机制需要责任、流程和审计同时落地", lock["records"][1]["title"])
            self.assertTrue(Path(summary["artifacts"]["compiled_deliverable_prompt"]).exists())
            self.assertTrue(Path(summary["artifacts"]["page_image_pairs"]).exists())
            self.assertTrue(Path(summary["artifacts"]["template_text_lock"]).exists())
            self.assertIn("--pages 7-8", summary["resume_command"])
            self.assertIn("--style-lock", summary["resume_command"])
            ledger_paths = {item["path"] for item in ledger["artifacts"]}
            self.assertIn(summary["artifacts"]["page_image_pairs"], ledger_paths)
            self.assertIn(summary["artifacts"]["template_text_lock"], ledger_paths)
            self.assertIn(summary["artifacts"]["visual_style_lock"], ledger_paths)

    def test_requires_default_style_selection_or_explicit_style_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：态势感知能力\n组件A：内容\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "请选择一个 CyberPPT 默认视觉风格"):
                run_final_script_pages(project=project, script=script, pages_raw="7")

    def test_rejects_post_approval_drawing_script_edit_before_creating_style_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            drawing_script = project / "workbench/analysis_expression/drawing_script.md"
            drawing_script.write_text(
                drawing_script.read_text(encoding="utf-8") + "\n<!-- post-approval edit -->\n",
                encoding="utf-8",
            )
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "approved drawing_script has changed; approve drawing_script again"):
                run_final_script_pages(project=project, script=script, pages_raw="1", style_id=4)

            self.assertFalse(any(project.rglob("visual_style_lock.json")))

    def test_production_build_runs_template_image_ppt_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")

            with patch("cyberppt.commands.final_script_pages.subprocess.run") as run:
                run.return_value = Mock(returncode=0)
                summary = run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="1",
                    style_id=4,
                    production_build=True,
                )

            command = run.call_args.args[0]

        self.assertEqual("02-production-build", summary["stage"])
        self.assertEqual("production_ready", summary["status"])
        self.assertEqual("completed", summary["image_ppt_build"]["status"])
        self.assertIn("-m", command)
        self.assertIn("cyberppt", command)
        self.assertIn("image-ppt", command)
        self.assertIn("run", command)
        self.assertIn("--script", command)
        self.assertIn(str(script.resolve()), command)
        self.assertIn("--pages", command)
        self.assertIn("1", command)
        self.assertIn(str(Path(summary["artifacts"]["image_ppt_output_dir"])), command)
        self.assertIsNone(summary["rebuild"])
        self.assertEqual({}, summary["tool_consumption"])
        self.assertIsNone(summary["production_readiness"])

    def test_run_rebuild_is_no_longer_supported_by_final_script_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text(
                """# 终稿脚本

## 第7页：态势感知能力
本页结论标题为“态势感知能力要从工具堆叠转向风险闭环”
组件A（左侧主图）——三层能力链：
数据接入、模型研判、处置反馈
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "--run-rebuild is no longer supported"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    run_rebuild=True,
                )

    def test_semantic_plan_dir_is_no_longer_supported_by_final_script_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            semantic_plan_dir = root / "semantic-plans"
            semantic_plan_dir.mkdir()
            script = root / "script-final.md"
            script.write_text("## 第7页：态势感知能力\n正文\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "--semantic-plan-dir is no longer supported"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    semantic_plan_dir=semantic_plan_dir,
                )

    def test_production_build_failure_reports_image_ppt_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            script = root / "script-final.md"
            script.write_text(
                """# 终稿脚本

## 第7页：态势感知能力
本页结论标题为“态势感知能力要从工具堆叠转向风险闭环”
组件A（左侧主图）——三层能力链：
数据接入、模型研判、处置反馈
""",
                encoding="utf-8",
            )

            with patch("cyberppt.commands.final_script_pages.subprocess.run") as run:
                run.return_value = Mock(returncode=3)
                with self.assertRaises(RuntimeError) as caught:
                    run_final_script_pages(
                        project=project,
                        script=script,
                        pages_raw="7",
                        style_id=5,
                        production_build=True,
                    )

        message = str(caught.exception)
        self.assertIn("image-ppt production build failed with exit code 3", message)
        self.assertIn("image-ppt", message)
        self.assertNotIn("source_capture", message)
        self.assertNotIn("semantic_plan", message)


if __name__ == "__main__":
    unittest.main()
