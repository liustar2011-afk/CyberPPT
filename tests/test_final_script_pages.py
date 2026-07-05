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

    def test_production_build_records_required_tool_consumption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")

            summary = run_final_script_pages(
                project=project,
                script=script,
                pages_raw="1",
                style_id=4,
                production_build=True,
            )

        self.assertEqual("02-production-build", summary["stage"])
        self.assertIn("tool_consumption", summary)
        self.assertEqual("production_rework_required", summary["status"])

    def test_production_build_consumes_existing_stage02_rebuild_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _write_stage02_production_artifacts(project)
            script = root / "script-final.md"
            script.write_text(
                """# 终稿脚本

## 第1页：测试
正文
""",
                encoding="utf-8",
            )

            summary = run_final_script_pages(
                project=project,
                script=script,
                pages_raw="1",
                style_id=4,
                production_build=True,
            )

        self.assertEqual("production_ready", summary["status"])
        self.assertTrue(summary["production_readiness"]["valid"])
        consumed = summary["tool_consumption"]
        self.assertTrue(all(item["ran"] for item in consumed.values()))
        self.assertTrue(consumed["semantic_binding"]["artifact"].endswith("semantic_binding_index.json"))
        self.assertTrue(consumed["editable_pptx"]["artifact"].endswith("stage02-output.pptx"))

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

            with (
                patch("cyberppt.commands.final_script_pages.require_generated"),
                patch("cyberppt.commands.final_script_pages.subprocess.run") as run,
            ):
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

    def test_run_rebuild_requires_dual_image_assets_before_template_rebuild(self) -> None:
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

            with self.assertRaises(FileNotFoundError) as caught:
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    run_rebuild=True,
                )

        self.assertIn("CyberPPT image files are not generated yet", str(caught.exception))

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

            with (
                patch("cyberppt.commands.final_script_pages.require_generated"),
                patch("cyberppt.commands.final_script_pages.subprocess.run") as run,
            ):
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


def _write_stage02_production_artifacts(project: Path) -> None:
    analysis = project / "analysis"
    exports = project / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    (exports / "stage02-output.pptx").write_bytes(b"pptx")
    artifacts = {
        "source_capture.json": {"schema": "cyberppt.dual_image.source_capture.v1", "valid": True},
        "source_capture_gate.json": {"schema": "cyberppt.dual_image.source_capture_gate.v1", "valid": True},
        "template_rebuild_readiness.json": {
            "schema": "cyberppt.dual_image.template_rebuild_readiness.v1",
            "valid": True,
            "status": "ready_for_delivery",
            "artifacts": {
                "exported_pptx": str(exports / "stage02-output.pptx"),
                "render_compare": str(analysis / "page_001_render_compare.json"),
                "visual_qa_gate": str(analysis / "visual_qa_gate.json"),
                "semantic_binding": str(analysis / "semantic_binding/semantic_binding_index.json"),
                "semantic_plan_dir": str(analysis / "semantic_plan"),
                "container_workspace": str(analysis / "container_workspace/container_workspace_index.json"),
                "workspace_assignment": str(analysis / "workspace_assignment/workspace_assignment_index.json"),
            },
        },
        "page_001_render_compare.json": {"schema": "cyberppt.render_compare.v1", "passed": True},
        "page_quality_report.json": {"schema": "cyberppt.dual_image.page_quality_report.v1", "valid": True},
        "visual_qa_gate.json": {"schema": "cyberppt.visual_qa_gate.v1", "valid": True},
        "office_textbox_fit.json": {"schema": "cyberppt.dual_image.office_textbox_fit.v1", "valid": True},
    }
    for relative, payload in artifacts.items():
        path = analysis / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    nested = {
        "semantic_binding/semantic_binding_index.json": {
            "schema": "cyberppt.dual_image.semantic_binding_set.v1",
            "valid": True,
        },
        "semantic_plan/page_001_semantic_plan.json": {
            "schema": "cyberppt.explicit_semantic_plan.v1",
            "valid": True,
        },
        "scene_graph_gate/page_001_scene_graph_gate.json": {
            "schema": "cyberppt.scene_graph_gate.v1",
            "valid": True,
        },
        "visual_registry/page_001_visual_element_registry.json": {
            "schema": "cyberppt.visual_element_registry.v1",
            "valid": True,
        },
        "container_workspace/container_workspace_index.json": {
            "schema": "cyberppt.dual_image.container_workspace_set.v1",
            "valid": True,
        },
        "workspace_assignment/workspace_assignment_index.json": {
            "schema": "cyberppt.dual_image.workspace_assignment_set.v1",
            "valid": True,
        },
    }
    for relative, payload in nested.items():
        path = analysis / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
