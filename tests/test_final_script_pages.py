from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.analysis_expression_gate import approve_analysis_artifact, stage_analysis_artifact
from cyberppt.commands.blueprint_gate import (
    approve_blueprint_input,
    approve_blueprint_image_review,
    approve_speaker_notes_review,
    approve_visual_style,
    assert_blueprint_image_review_ready,
    assert_blueprint_input_ready,
    assert_speaker_notes_review_ready,
    stage_blueprint_input,
    stage_blueprint_image_review,
    stage_speaker_notes_review,
    stage_visual_style_options,
)
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.init_project import init_project


OPTIONS = [
    {"id": "leadership_review", "label": "领导审定型"},
    {"id": "execution_alignment", "label": "执行对齐型"},
]


def _approve_all_analysis_expression_gates(project: Path) -> None:
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


def _approve_stage02_input(project: Path, script: Path) -> None:
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


def _approve_stage02_images(project: Path, script: Path, pages: str) -> Path:
    summary = run_final_script_pages(project=project, script=script, pages_raw=pages)
    manifest_path = Path(summary["artifacts"]["page_image_pairs"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for pair in manifest["pairs"]:
        Path(pair["full"]["path"]).write_bytes(b"png")
    stage_blueprint_image_review(project, manifest_path)
    approve_blueprint_image_review(project, "confirm_blueprint_images")
    return Path(summary["artifacts"]["speaker_notes_manifest"])


def _approve_stage02_speaker_notes(project: Path, manifest_path: Path, pages: str) -> None:
    stage_speaker_notes_review(project, manifest_path, pages)
    approve_speaker_notes_review(project, "confirm_speaker_notes")


class FinalScriptPagesTests(unittest.TestCase):
    def test_rejects_unapproved_new_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "source_analysis approval is required"):
                run_final_script_pages(project=project, script=script, pages_raw="1", style_id=4)

    def test_legacy_project_remains_compatible_until_adopted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "legacy-report"
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")

            summary = run_final_script_pages(project=project, script=script, pages_raw="1", style_id=4)

        self.assertEqual([1], summary["pages"])

    def test_image_review_stages_generated_images_without_ocr_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            manifest_path = root / "page_image_pairs.json"
            image = root / "page_001_full.png"
            image.write_bytes(b"png")
            manifest_path.write_text(
                json.dumps(
                    {
                        "pairs": [
                            {
                                "page_number": 1,
                                "full": {
                                    "path": str(image),
                                    "prompt": "【内容锁定】\n- 供需预测\n\n【构图指令】\n正式内部汇报",
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            pending = stage_blueprint_image_review(project, manifest_path)
            self.assertTrue(pending.is_file())

            revision = approve_blueprint_image_review(project, "revise_blueprint_images", "regenerate page 1")

            self.assertFalse(json.loads(revision.read_text(encoding="utf-8"))["approved"])
            with self.assertRaisesRegex(ValueError, "blueprint image review approval is required"):
                assert_blueprint_image_review_ready(project, json.loads(manifest_path.read_text(encoding="utf-8")))

            approval = approve_blueprint_image_review(project, "confirm_blueprint_images")

            self.assertTrue(json.loads(approval.read_text(encoding="utf-8"))["approved"])
            assert_blueprint_image_review_ready(project, json.loads(manifest_path.read_text(encoding="utf-8")))

    def test_speaker_notes_review_requires_current_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            manifest = root / "speaker_notes_manifest.json"
            manifest.write_text('{"notes": ["briefing"]}\n', encoding="utf-8")

            pending = stage_speaker_notes_review(project, manifest, "1-3")

            self.assertTrue(pending.is_file())
            pending_data = json.loads(pending.read_text(encoding="utf-8"))
            self.assertEqual(str(manifest.resolve()), pending_data["manifest"])
            self.assertEqual("1-3", pending_data["pages_raw"])
            self.assertIsNone(pending_data["option_id"])
            with self.assertRaisesRegex(ValueError, "speaker notes approval is required"):
                assert_speaker_notes_review_ready(project, "1-3")

            revision = approve_speaker_notes_review(project, "revise_speaker_notes", "expand page 2")

            self.assertFalse(json.loads(revision.read_text(encoding="utf-8"))["approved"])
            with self.assertRaisesRegex(ValueError, "speaker notes approval is required"):
                assert_speaker_notes_review_ready(project, "1-3")

            approval = approve_speaker_notes_review(project, "confirm_speaker_notes")

            self.assertTrue(json.loads(approval.read_text(encoding="utf-8"))["approved"])
            self.assertEqual(manifest.resolve(), assert_speaker_notes_review_ready(project, "1-3"))

            manifest.write_text('{"notes": []}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "speaker notes changed"):
                assert_speaker_notes_review_ready(project, "1-3")

    def test_blueprint_input_revision_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
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

            revision = approve_blueprint_input(project, "revise_blueprint_input", "rewrite page 1")

            self.assertFalse(json.loads(revision.read_text(encoding="utf-8"))["approved"])
            approved_input = project / "workbench/stages/02-blueprint-dual-image/blueprint_input.md"
            with self.assertRaisesRegex(ValueError, "blueprint input approval is required"):
                assert_blueprint_input_ready(project, approved_input, None)

            approval = approve_blueprint_input(project, "confirm_blueprint_input")

            self.assertTrue(json.loads(approval.read_text(encoding="utf-8"))["approved"])
            self.assertTrue(assert_blueprint_input_ready(project, approved_input, None).is_file())

    def test_speaker_notes_review_invalidates_business_and_page_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            manifest = root / "speaker_notes_manifest.json"
            manifest.write_text('{"notes": ["briefing"]}\n', encoding="utf-8")
            stage_speaker_notes_review(project, manifest, "1-3")
            approve_speaker_notes_review(project, "confirm_speaker_notes")

            with self.assertRaisesRegex(ValueError, "current page selection"):
                assert_speaker_notes_review_ready(project, "2-3")

            stage_analysis_artifact(
                project,
                "business_script",
                "## 第1页：章节过渡\n更新后的讲稿\n### 非上屏：证据链\n- E-01\n"
                "### 来源位置\n- 年度供需预测报告第4页\n### 非上屏：完整性校核\n- 更新后的业务依据。\n",
                "business script",
                OPTIONS,
            )
            approve_analysis_artifact(project, "business_script", "leadership_review")

            with self.assertRaisesRegex(ValueError, "business script changed"):
                assert_speaker_notes_review_ready(project, "1-3")

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
            _approve_stage02_input(project, script)

            summary = run_final_script_pages(project=project, script=script, pages_raw="7-8")

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

    def test_requires_approved_visual_style_and_blueprint_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：态势感知能力\n组件A：内容\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "visual style approval is required"):
                run_final_script_pages(project=project, script=script, pages_raw="7")

    def test_rejects_post_approval_blueprint_input_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            _approve_all_analysis_expression_gates(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n组件A：内容\n", encoding="utf-8")
            _approve_stage02_input(project, script)
            _approve_stage02_images(project, script, "1")
            script.write_text(script.read_text(encoding="utf-8") + "\n<!-- post-approval edit -->\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "script must match the approved blueprint input"):
                run_final_script_pages(project=project, script=script, pages_raw="1")

            self.assertTrue(any(project.rglob("visual_style_lock.json")))

    def test_production_build_is_rejected_in_favor_of_produce_assemble(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "legacy-report"
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n组件A：内容\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "produce assemble"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="1",
                    style_id=4,
                    production_build=True,
                )

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

if __name__ == "__main__":
    unittest.main()
