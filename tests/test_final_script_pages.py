from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.init_project import init_project


class FinalScriptPagesTests(unittest.TestCase):
    def test_compiles_pages_7_8_from_final_script_with_traceable_artifacts(self) -> None:
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
            script = root / "script-final.md"
            script.write_text("## 第7页：态势感知能力\n组件A：内容\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "请选择一个 CyberPPT 默认视觉风格"):
                run_final_script_pages(project=project, script=script, pages_raw="7")

    def test_run_rebuild_passes_semantic_plan_dir_to_template_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            semantic_plan_dir = root / "semantic-plans"
            semantic_plan_dir.mkdir()
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
                run.return_value = Mock(returncode=0)
                summary = run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    semantic_plan_dir=semantic_plan_dir,
                    run_rebuild=True,
                )

            command = run.call_args.args[0]

        self.assertIn("--semantic-plan-dir", command)
        self.assertIn(str(semantic_plan_dir.resolve()), command)
        self.assertEqual(str(semantic_plan_dir.resolve()), summary["artifacts"]["semantic_plan_dir"])
        self.assertIn("page_quality_report", summary["rebuild"]["artifacts"])

    def test_run_rebuild_failure_reports_quality_gate_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            (project / "analysis").mkdir(exist_ok=True)
            (project / "analysis/template_rebuild_readiness.json").write_text(
                json.dumps(
                    {
                        "valid": False,
                        "status": "source_capture_rework_required",
                        "checks": {
                            "template_gate_pass": True,
                            "source_capture_gate_pass": False,
                            "scene_graph_gate_pass": True,
                        },
                        "artifacts": {"exported_pptx": str(project / "exports/intermediate.pptx")},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (project / "analysis/source_capture_gate.json").write_text(
                json.dumps(
                    {
                        "valid": False,
                        "gap_counts": {"semantic_plan_gate_failed": 3},
                        "blocking_gaps": [
                            {
                                "page_number": 7,
                                "code": "semantic_plan_gate_failed",
                                "message": "Explicit semantic container plan is invalid.",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (project / "analysis/page_quality_report.json").write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.dual_image.page_quality_report.v1",
                        "valid": False,
                        "blocking_errors": [
                            {
                                "id": "template.source_capture_gate_pass",
                                "description": "Template rebuild must consume source_capture and pass its gate.",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
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
                        run_rebuild=True,
                    )

        message = str(caught.exception)
        self.assertIn("source_capture_rework_required", message)
        self.assertIn("source_capture_gate_pass", message)
        self.assertIn("semantic_plan_gate_failed=3", message)
        self.assertIn("page 7: semantic_plan_gate_failed", message)
        self.assertIn("page_quality_report:", message)
        self.assertIn("template.source_capture_gate_pass", message)
        self.assertIn("intermediate artifact only", message)


if __name__ == "__main__":
    unittest.main()
