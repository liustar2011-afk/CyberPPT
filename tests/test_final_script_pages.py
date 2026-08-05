from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cyberppt.commands.final_script_pages import (
    BODY_IMAGE_CANVAS_CONTRACT,
    _generate_manifest_images,
    _page_range_slug,
    run_final_script_pages,
)
from cyberppt.commands.init_project import init_project
from cyberppt.stage01_controls import write_confirmation_request, write_stage01_approval
from cyberppt.commands.script_gate import stage_script
from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks, render_prompt
from scripts.dual_image_overlay.imagegen_handoff import build_page_prompt
from cyberppt.script_quality_contract import parse_script_markdown
from scripts.dual_image_overlay.style_library import write_project_style_lock


class FinalScriptPagesTests(unittest.TestCase):
    def test_long_discontinuous_page_set_uses_windows_safe_slug(self) -> None:
        pages = [4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 25, 26, 27]
        slug = _page_range_slug(pages)
        self.assertLessEqual(len(slug), 80)
        self.assertTrue(slug.startswith("pages_004_027_21p_"))
        self.assertEqual(slug, _page_range_slug(pages))

    def test_semantic_only_judgment_moves_to_subtitle_not_body_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            judgment = "30个电力学科、约30万条题目和40年行业数据构成核心资产基础"
            subtitle = "30个学科、30万道题目、40年数据，夯实智能应用底座"
            script.write_text(
                f"""## 第4页：知识资产基础
- 页面类型：内容页
- 页面标题：知识资产基础
- 副标题：{subtitle}
- 主判断：{judgment}
- 上屏结论模式：semantic_only
- 上屏结论：{judgment}
- 上屏文字：

  **01｜30个电力学科**
  - 覆盖专业知识与规范
""",
                encoding="utf-8",
            )
            page = parse_script_markdown(script.read_text(encoding="utf-8")).pages[0]
            style_lock = write_project_style_lock(
                project=project,
                style_id=9,
                source_script=script,
            )
            prompt = build_page_prompt(page, style_lock)

        body = prompt.split("【完整上屏内容】", 1)[1].split(
            "【核心意思表达要求", 1
        )[0]
        self.assertNotIn(judgment, body)
        self.assertNotIn(subtitle, body)
        self.assertIn("01｜30个电力学科", body)

    def test_subtitle_migration_preserves_existing_body_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            judgment = "三类知识资产共同构成智能应用基础"
            original_body = (
                "**01｜30个电力学科**\n"
                "  - 原有说明文字保持不变\n"
                "  **02｜约30万条题目**\n"
                "  - 原有证据关系保持不变\n"
                "  **03｜40年行业数据**"
            )
            script.write_text(
                f"""## 第4页：知识资产基础
- 页面类型：内容页
- 页面标题：知识资产基础
- 副标题：三类知识资产夯实智能应用底座
- 主判断：{judgment}
- 上屏结论模式：semantic_only
- 上屏结论：{judgment}
- 上屏文字：

  {original_body}
""",
                encoding="utf-8",
            )
            page = parse_script_markdown(script.read_text(encoding="utf-8")).pages[0]
            style_lock = write_project_style_lock(
                project=project,
                style_id=9,
                source_script=script,
            )
            prompt = build_page_prompt(page, style_lock)

        body = prompt.split("【完整上屏内容】", 1)[1].split(
            "【核心意思表达要求", 1
        )[0]
        normalized_original = "\n".join(
            line.strip() for line in original_body.splitlines()
        )
        normalized_body = "\n".join(
            line.strip() for line in body.strip().splitlines()
        )
        self.assertEqual(normalized_original, normalized_body)
        self.assertNotIn(judgment, body)

    def test_full_image_payload_forces_body_region_two_to_one_canvas(self) -> None:
        manifest = {
            "production_mode": "full-image",
            "pairs": [
                {
                    "page_number": 4,
                    "full": {
                        "path": "page-004.png",
                        "prompt": "页面正文提示词",
                        "canvas": "2048x1024",
                    },
                }
            ],
        }
        with patch("cyberppt.commands.final_script_pages.run_codex_image") as generate:
            _generate_manifest_images(
                manifest,
                full_reference_images=[Path("palette-09.png")],
                model="gpt-image-2",
                quality="high",
                timeout=600,
                force=False,
                dry_run=True,
            )

        kwargs = generate.call_args.kwargs
        self.assertTrue(kwargs["prompt"].startswith(BODY_IMAGE_CANVAS_CONTRACT))
        self.assertIn("不得输出16:9", kwargs["prompt"])
        self.assertEqual("2048x1024", kwargs["size"])
        self.assertEqual([Path("palette-09.png")], kwargs["image_paths"])

    def _approve_inputs_and_prompts(self, project: Path, script: Path, style_id: int = 4) -> None:
        manifest = project / "manifest.yml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                "semantic_understanding: required",
                "semantic_understanding: optional",
            ).replace(
                "communication_strategy: required",
                "communication_strategy: optional",
            ),
            encoding="utf-8",
        )
        analysis = project / "workbench" / "stages" / "01-analysis"
        outline = analysis / "outline.json"
        source_truth = analysis / "source-truth.json"
        outline.write_text("{}\n", encoding="utf-8")
        source_truth.write_text("{}\n", encoding="utf-8")
        audit = project / "workbench" / "scripts" / "audits" / "script-audit.json"
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "input": str(script.resolve()),
                    "outline": str(outline.resolve()),
                    "source_truth": str(source_truth.resolve()),
                }
            ),
            encoding="utf-8",
        )
        review_input = project / "workbench" / "scripts" / "audits" / "chapter-review-input.json"
        review_input.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.chapter_review_input.v1",
                    "level": "script",
                    "input_path": str(script.resolve()),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        chapter_review = project / "workbench" / "scripts" / "audits" / "chapter-review-audit.json"
        chapter_review.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.chapter_review_audit.v1",
                    "status": "passed",
                    "input": str(review_input.resolve()),
                    "input_sha256": hashlib.sha256(review_input.read_bytes()).hexdigest(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        visual_dir = project / "visual"
        visual_dir.mkdir(parents=True, exist_ok=True)
        spec_json = visual_dir / "deck-visual-spec.json"
        spec_md = visual_dir / "script-visual-structure.md"
        generation_prompts = visual_dir / "generation-prompts.md"
        spec_json.write_text(json.dumps({"schema": "cyberppt.visual_spec.v1"}), encoding="utf-8")
        spec_md.write_text("# visual structure\n", encoding="utf-8")
        prompt_pages = []
        for page_number in range(1, 31):
            prompt_pages.append(
                "\n".join(
                    [
                        f"# Page {page_number}: fixture",
                        "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.",
                        "Use the approved page relationship.",
                        "[Connector map]",
                        "Keep the main relation clear.",
                        "[Text rendering]",
                        "Render locked text verbatim.",
                        "[Style]",
                        "Use the project style lock.",
                        "[Negative constraints]",
                        "Do not add slide chrome.",
                        "---",
                    ]
                )
            )
        generation_prompts.write_text("\n".join(prompt_pages) + "\n", encoding="utf-8")
        visual_report = visual_dir / "validation-report.json"
        visual_report.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.visual_structure_stage.v1",
                    "status": "passed",
                    "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                    "artifact_sha256": {
                        "spec_json": hashlib.sha256(spec_json.read_bytes()).hexdigest(),
                        "spec_markdown": hashlib.sha256(spec_md.read_bytes()).hexdigest(),
                        "generation_prompts": hashlib.sha256(generation_prompts.read_bytes()).hexdigest(),
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        write_confirmation_request(project, "script")
        approvals = project / "workbench" / "approvals"
        approvals.mkdir(parents=True, exist_ok=True)
        (approvals / "stage01-outline-approved.md").write_text("# approved\n", encoding="utf-8")
        write_stage01_approval(project, kind="script", note="test")
        style_lock = write_project_style_lock(project=project, style_id=style_id, source_script=script)
        script_pages = {
            int(page.page_id[1:]): page
            for page in parse_script_markdown(script.read_text(encoding="utf-8")).pages
        }
        for page_number in parse_page_blocks(script):
            prompt = project / f"prompt-{page_number}.md"
            prompt.write_text(
                build_page_prompt(script_pages[page_number], style_lock),
                encoding="utf-8",
            )
            stage_script(project, page_number, "imagegen", "final", prompt)
        for page_number in parse_page_blocks(script):
            from cyberppt.commands.script_gate import approve_script

            approve_script(project, page_number, "imagegen", note="test")

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
            self._approve_inputs_and_prompts(project, script)

            summary = run_final_script_pages(project=project, script=script, pages_raw="7-8", style_id=4)

            manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text(encoding="utf-8"))
            lock = json.loads(Path(summary["artifacts"]["template_text_lock"]).read_text(encoding="utf-8"))
            visual_lock = json.loads(Path(summary["artifacts"]["visual_style_lock"]).read_text(encoding="utf-8"))
            build_context = json.loads(Path(summary["artifacts"]["build_context"]).read_text(encoding="utf-8"))
            prompt = Path(summary["artifacts"]["compiled_deliverable_prompt"]).read_text(encoding="utf-8")
            ledger = json.loads((project / "workbench/artifact-ledger.json").read_text(encoding="utf-8"))

            self.assertEqual([7, 8], summary["pages"])
            self.assertEqual(summary["build_id"], build_context["build_id"])
            self.assertEqual([7, 8], build_context["page_set"])
            self.assertEqual(summary["source_script_sha256"], build_context["source_script_sha256"])
            self.assertIn("page_image_pairs", build_context["artifacts"])
            self.assertEqual([7, 8], [pair["page_number"] for pair in manifest["pairs"]])
            self.assertEqual(4, visual_lock["style"]["id"])
            self.assertEqual(manifest["style_lock"], summary["artifacts"]["visual_style_lock"])
            self.assertIn("#12355B", prompt)
            self.assertNotIn("【完整内容语义｜仅供理解，不要求逐字上屏】", prompt)
            self.assertNotIn("【页面逻辑｜不上屏】", prompt)
            self.assertIn("【锁定关键文字】", prompt)
            self.assertIn("【完整上屏内容】", prompt)
            self.assertEqual("态势感知能力要从工具堆叠转向风险闭环", lock["records"][0]["title"])
            self.assertEqual("运营保障机制需要责任、流程和审计同时落地", lock["records"][1]["title"])
            self.assertIn("presentation", lock["records"][0])
            self.assertIn("editable_body_text", lock["records"][0])
            self.assertTrue(Path(summary["artifacts"]["compiled_deliverable_prompt"]).exists())
            self.assertTrue(Path(summary["artifacts"]["page_image_pairs"]).exists())
            self.assertTrue(Path(summary["artifacts"]["template_text_lock"]).exists())
            self.assertIn("--pages 7-8", summary["resume_command"])
            self.assertIn("--style-lock", summary["resume_command"])
            ledger_paths = {item["path"] for item in ledger["artifacts"]}
            self.assertIn(summary["artifacts"]["page_image_pairs"], ledger_paths)
            self.assertIn(summary["artifacts"]["template_text_lock"], ledger_paths)
            self.assertIn(summary["artifacts"]["visual_style_lock"], ledger_paths)

    def test_external_script_does_not_require_stage01_or_per_page_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "stage2-only"
            script = root / "vendor-script.md"
            script.write_text(
                "## P01 外部脚本页面\n"
                "本页结论：外部脚本可以直接进入 Stage 02。\n"
                "组件A：输入与输出关系\n",
                encoding="utf-8",
            )

            summary = run_final_script_pages(
                project=project,
                script=script,
                pages_raw="1",
                style_id=4,
                external_script=True,
            )

            manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text(encoding="utf-8"))
            context = json.loads(Path(summary["artifacts"]["build_context"]).read_text(encoding="utf-8"))
            manifest_created = (project / "manifest.yml").is_file()

        self.assertEqual("external_script", summary["source_mode"])
        self.assertTrue(summary["project_created"])
        self.assertEqual("external_script", context["source_mode"])
        self.assertTrue(context["project_created"])
        self.assertEqual("stage2-only", Path(summary["project"]).name)
        self.assertTrue(manifest_created)
        self.assertEqual("external_script", manifest["source_mode"])
        self.assertEqual(summary["source_script_sha256"], manifest["source_script_sha256"])
        self.assertFalse(manifest["prompt_contract"]["approved_prompt_is_source"])
        self.assertTrue(summary["artifacts"]["compiled_deliverable_prompt"].endswith(".md"))
        self.assertIn("--external-script", summary["resume_command"])

    def test_requires_default_style_selection_or_explicit_style_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：态势感知能力\n组件A：内容\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            with self.assertRaisesRegex(ValueError, "请选择一个 CyberPPT 默认视觉风格"):
                run_final_script_pages(project=project, script=script, pages_raw="7")

    def test_production_build_runs_template_image_ppt_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

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

    def test_run_rebuild_requires_editable_overlay_mode(self) -> None:
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
            self._approve_inputs_and_prompts(project, script)

            with self.assertRaisesRegex(ValueError, "--run-rebuild requires an editable-overlay"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    run_rebuild=True,
                )

    def test_semantic_plan_dir_requires_editable_overlay_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            semantic_plan_dir = root / "semantic-plans"
            semantic_plan_dir.mkdir()
            script = root / "script-final.md"
            script.write_text("## 第7页：态势感知能力\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            with self.assertRaisesRegex(ValueError, "--semantic-plan-dir requires an editable-overlay"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    semantic_plan_dir=semantic_plan_dir,
                )

    def test_triple_image_mode_builds_full_background_and_ocr_reference_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：测试\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            summary = run_final_script_pages(
                project=project,
                script=script,
                pages_raw="7",
                style_id=4,
                production_mode="editable-overlay-text-reference",
            )

            manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text(encoding="utf-8"))
            pair = manifest["pairs"][0]

        self.assertEqual("editable-overlay-text-reference", summary["production_mode"])
        self.assertEqual(["full", "background", "text_reference"], manifest["output_variants"])
        self.assertEqual("edit", pair["background"]["operation"])
        self.assertEqual("edit", pair["text_reference"]["operation"])
        self.assertFalse(pair["text_reference"]["visible_in_ppt"])

    def test_main_chain_routes_all_triple_image_variants_through_codex_oauth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：测试\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            with patch("cyberppt.commands.final_script_pages.run_codex_image") as generate:
                summary = run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=4,
                    production_mode="editable-overlay-text-reference",
                    generate_images=True,
                    dry_run_images=True,
                )

            calls = generate.call_args_list

        self.assertEqual(3, len(calls))
        self.assertEqual([], calls[0].kwargs["image_paths"])
        self.assertEqual(1, len(calls[1].kwargs["image_paths"]))
        self.assertEqual(1, len(calls[2].kwargs["image_paths"]))
        self.assertEqual("codex_oauth_image", summary["image_generation"]["backend"])

    def test_production_build_failure_reports_image_ppt_command(self) -> None:
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
            self._approve_inputs_and_prompts(project, script, style_id=5)

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

                self.assertEqual(
                    Path(__file__).resolve().parents[1],
                    run.call_args.kwargs["cwd"],
                )

        message = str(caught.exception)
        self.assertIn("image-ppt production build failed with exit code 3", message)
        self.assertIn("image-ppt", message)
        self.assertNotIn("source_capture", message)
        self.assertNotIn("semantic_plan", message)


if __name__ == "__main__":
    unittest.main()
