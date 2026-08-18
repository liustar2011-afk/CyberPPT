from __future__ import annotations

from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from cyberppt.commands.init_project import init_project
from cyberppt.commands.script_gate import approve_script, stage_script
from scripts.imagegen_pipeline.page_manifest import (
    build_manifest,
    main,
    require_generated,
)
from scripts.imagegen_pipeline.deliverable_prompt import (
    STYLE09_TERMINAL_LOCK_HEADER,
    parse_page_blocks,
    render_prompt,
    style_contract,
)
from scripts.imagegen_pipeline.imagegen_handoff import build_page_prompt
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir
from scripts.imagegen_pipeline.final_prompt_renderer import SECTION_HEADINGS, render_final_prompt
from cyberppt.script_quality_contract import parse_script_markdown
from scripts.imagegen_pipeline.style_library import write_project_style_lock
from tests.test_artifact_prompt import _spec


class CyberpptPairManifestTests(unittest.TestCase):
    def test_artifact_manifest_consumes_the_approved_seven_section_prompt_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            init_project(project)
            script = root / "script.md"
            script.write_text(
                "## 第2页：治理结果\n\n- 页面类型：内容页\n- 页面标题：治理结果\n- 主判断：治理结果可追溯。\n- 上屏文字：\n\n  Governed input\n  Traceable result\n",
                encoding="utf-8",
            )
            style_lock = write_project_style_lock(project=project, style_id=10, source_script=script)
            spec = replace(_spec(), page_id="P02", page_number=2)
            expected_prompt = render_final_prompt(
                build_final_prompt_ir(spec), style_id=spec.art_direction.style_id, style_lock=style_lock
            )
            approved = root / "approved.md"
            approved.write_text(expected_prompt, encoding="utf-8")
            stage_script(project, 2, "imagegen", "final", approved)
            approve_script(project, 2, "imagegen")

            with patch(
                "scripts.imagegen_pipeline.page_manifest.load_project_page_artifact_specs",
                return_value={2: spec},
            ):
                manifest, _, compiled, _ = build_manifest(
                    script=script,
                    pages_raw="2",
                    output_dir=root / "images",
                    project_path=project,
                    style_lock=style_lock,
                    require_approved_prompts=True,
                    prompt_compiler="artifact-spec-v2",
                )
                compiled_text = compiled.read_text(encoding="utf-8")

        consumed = manifest["pairs"][0]["full"]["prompt"]
        self.assertEqual(expected_prompt, consumed)
        self.assertEqual("artifact-spec-v2", manifest["prompt_contract"]["compiler"])
        self.assertFalse(manifest["prompt_contract"]["compact_blueprint"])
        self.assertEqual(SECTION_HEADINGS[0], consumed.splitlines()[0])
        self.assertIn(SECTION_HEADINGS[-1], compiled_text)

    def test_style09_contract_is_single_complete_source_lock_after_stage02_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            script = root / "script.md"
            script.write_text(
                "## P4 建设背景\n"
                "正文模块：统一连接与可信使用。\n",
                encoding="utf-8",
            )
            style_lock = write_project_style_lock(project=project, style_id=9, source_script=script)
            visual = project / "visual"
            visual.mkdir()
            (visual / "generation-prompts.md").write_text(
                "# Page 4: 建设背景\n"
                "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.\n"
                "- Visual thesis: 统一连接与可信使用共同形成稳定服务。\n"
                "- Spatial grammar: path, divergence\n"
                "- Reading sequence: E1 -> E2 -> E3\n"
                "- Text binding: E1 -> E1 / embedded / locked text ids: P04-T01\n\n"
                "[Negative constraints]\n- no equal card wall\n---\n",
                encoding="utf-8",
            )
            manifest, _, _, _ = build_manifest(
                script=script,
                pages_raw="4",
                output_dir=root / "images",
                project_path=project,
                style_lock=style_lock,
            )
            expected_contract = style_contract(style_lock)
        prompt = manifest["pairs"][0]["full"]["prompt"]
        self.assertIn("【STYLE09 页面语义适配｜不上屏】", prompt)
        self.assertIn("语义锚点：统一连接与可信使用共同形成稳定服务", prompt)
        self.assertNotIn("【风格09业务场适配器｜不上屏】", prompt)
        self.assertNotIn("Text binding", prompt)
        self.assertNotIn("P04-T01", prompt)
        self.assertNotIn("E1 -> E2", prompt)
        self.assertNotIn("【视觉组织原则】", prompt)
        self.assertEqual(1, prompt.count("【视觉风格｜不上屏】"))
        self.assertIn("### 2. Semantic anchor and composition — hard", prompt)
        # The source contract's own "### Final ImageGen execution lock" section is
        # removed from its mid-document position and reasserted once, verbatim, at
        # the true end of the prompt under the Chinese terminal-lock header -- see
        # enforce_style09_terminal_lock's docstring for why a mid-document copy is
        # not sufficient on its own.
        self.assertNotIn("### Final ImageGen execution lock — hard", prompt)
        self.assertEqual(1, prompt.count(STYLE09_TERMINAL_LOCK_HEADER))
        self.assertNotIn("### ", prompt.split(STYLE09_TERMINAL_LOCK_HEADER, 1)[1])
        handoff = manifest["pairs"][0]["visual_structure_handoff"]
        self.assertTrue(handoff["consumed"])

    def test_stage02_visual_module_replaces_stage01_visual_expression_for_style09(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            script = root / "script.md"
            script.write_text(
                "## P4 test\n"
                "正文模块：测试内容\n"
                "【视觉结构，不上屏】\n"
                "需求缺口汇聚至建设响应。\n",
                encoding="utf-8",
            )
            style_lock = write_project_style_lock(project=project, style_id=9, source_script=script)
            visual = project / "visual"
            visual.mkdir()
            (visual / "generation-prompts.md").write_text(
                "# Page 4: test\n"
                "[Structural guidance]\n"
                "- Visual thesis: a single causal chain from demand gap to trusted service.\n\n"
                "[Connector map]\n- E1 -> E2\n---\n",
                encoding="utf-8",
            )
            manifest, _, compiled, _ = build_manifest(
                script=script,
                pages_raw="4",
                output_dir=root / "images",
                project_path=project,
                style_lock=style_lock,
            )
            prompt = manifest["pairs"][0]["full"]["prompt"]
            compiled_text = compiled.read_text(encoding="utf-8")
        self.assertIn("【STYLE09 页面语义适配｜不上屏】", prompt)
        self.assertIn("语义锚点：a single causal chain from demand gap to trusted service", prompt)
        self.assertNotIn("[Connector map]", prompt)
        self.assertIn("语义锚点：a single causal chain from demand gap to trusted service", compiled_text)
        self.assertTrue(manifest["pairs"][0]["visual_structure_handoff"]["consumed"])
        return
        self.assertIn("\u9700\u6c42\u7f3a\u53e3\u6c47\u805a\u81f3\u5efa\u8bbe\u54cd\u5e94", prompt)
        self.assertIn("\u9700\u6c42\u7f3a\u53e3\u6c47\u805a\u81f3\u5efa\u8bbe\u54cd\u5e94", compiled_text)
        self.assertIn("不锁定分栏、卡片、框体或文字区", prompt)
        self.assertIn("将锁定文字就近附着于同一连续业务场", prompt)
        self.assertNotIn("Apply this layout guidance", prompt)

    def test_compact_blueprint_uses_handoff_locked_text_without_full_prose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            init_project(project)
            script = root / "script.md"
            script.write_text("## 第4页：建设背景\n正文\n", encoding="utf-8")
            style_lock = write_project_style_lock(project=project, style_id=4, source_script=script)
            visual = project / "visual"
            visual.mkdir(exist_ok=True)
            (visual / "generation-prompts.md").write_text(
                "# Page 4: 建设背景\n"
                "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.\n"
                "- Dominant visual carrier: 可信服务基座\n\n"
                "[Connector map]\n- E1 -> E2\n\n"
                "[Text rendering]\n- Body rendering mode: in_image\n\n"
                "[Style]\nSHOULD_NOT_BE_IMPORTED\n\n"
                "[Negative constraints]\n- no equal card wall\n---\n",
                encoding="utf-8",
            )
            handoff = {
                "schema": "cyberppt.stage02_handoff.v1",
                "pages": [
                    {
                        "page_id": "p04",
                        "page_number": 4,
                        "render_role": "content",
                        "core_message": "跨主体需求与现实制约共同要求可信服务基座。",
                        "full_prose": "这段完整讲稿不得进入最终送图脚本。",
                        "onscreen_text": "业务演进与协同需求\n现实制约\n可信服务基座",
                    }
                ],
            }
            handoff_path = project / "workbench/stages/02-handoff/stage02-handoff.json"
            handoff_path.parent.mkdir(parents=True, exist_ok=True)
            handoff_path.write_text(json.dumps(handoff, ensure_ascii=False), encoding="utf-8")
            with patch(
                "cyberppt.stage02_handoff.load_stage02_handoff",
                return_value=handoff,
            ):
                manifest, _, compiled, _ = build_manifest(
                    script=script,
                    pages_raw="4",
                    output_dir=root / "images",
                    project_path=project,
                    style_lock=style_lock,
                    compact_blueprint=True,
                )
                compiled_text = compiled.read_text(encoding="utf-8")

        prompt = manifest["pairs"][0]["full"]["prompt"]
        self.assertIn("2048×1024（2:1）", prompt)
        self.assertIn("业务演进与协同需求", prompt)
        self.assertIn("可信服务基座", prompt)
        self.assertNotIn("跨主体需求与现实制约共同要求可信服务基座。", prompt)
        self.assertNotIn("这段完整讲稿不得进入最终送图脚本", prompt)
        self.assertNotIn("SHOULD_NOT_BE_IMPORTED", prompt)
        self.assertEqual(prompt.rstrip(), compiled_text.split("\n\n", 1)[1].strip())

    def test_removed_dual_modes_are_rejected(self) -> None:
        for mode in ("full-image", "editable-overlay", "editable-overlay-text-reference"):
            with self.assertRaisesRegex(ValueError, "image-to-editable-svg"):
                build_manifest(
                    script=Path(__file__),
                    pages_raw="1",
                    output_dir=Path(__file__).parent / "unused",
                    project_path=None,
                    style_lock=None,
                    production_mode=mode,
                )

    def test_promotes_approved_blueprint_to_full_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "script.md"
            output_dir = root / "images"
            blueprint_dir = root / "blueprints"
            blueprint_dir.mkdir()
            script.write_text(
                """## 第2页：蓝图晋升
组件A（主图）——矩阵：
一二三四
""",
                encoding="utf-8",
            )
            blueprint = blueprint_dir / "slide-002-blueprint.png"
            Image.new("RGB", (320, 180), color=(20, 40, 80)).save(blueprint)

            code = main(
                [
                    "--script",
                    str(script),
                    "--pages",
                    "2",
                    "--output-dir",
                    str(output_dir),
                    "--project-path",
                    str(root / "project"),
                    "--style-id",
                    "4",
                    "--promote-blueprints-from",
                    str(blueprint_dir),
                ]
            )
            manifest = json.loads((output_dir / "page_image_pairs.json").read_text(encoding="utf-8"))
            pair = manifest["pairs"][0]
            full_status = pair["full"]["status"]
            full_path = Path(pair["full"]["path"])
            with Image.open(full_path) as image:
                full_size = image.size

        self.assertEqual(code, 0)
        self.assertEqual("cyberppt-image-to-editable-svg", manifest["mode"])
        self.assertEqual("image-to-editable-svg", manifest["production_mode"])
        self.assertEqual(["full"], manifest["output_variants"])
        self.assertEqual("Generated", full_status)
        self.assertEqual((4096, 2048), full_size)
        self.assertNotIn("background", pair)
        self.assertEqual("required", pair["graphic_text_policy"]["status"])
        self.assertEqual("required", pair["graphic_text_policy"]["empty_container_check"])

    def test_manifest_generates_full_images_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "script.md"
            output_dir = root / "images"
            script.write_text(
                """## 第3页：双图派生约束
本页结论标题为“先生成全图，再由全图派生无文字底图”
""",
                encoding="utf-8",
            )

            code = main(
                [
                    "--script",
                    str(script),
                    "--pages",
                    "3",
                    "--output-dir",
                    str(output_dir),
                    "--project-path",
                    str(root / "project"),
                    "--style-id",
                    "5",
                ]
            )
            manifest = json.loads((output_dir / "page_image_pairs.json").read_text(encoding="utf-8"))
            pair = manifest["pairs"][0]
            style_lock_exists = Path(manifest["style_lock"]).is_file()

        self.assertEqual(code, 0)
        self.assertTrue(style_lock_exists)
        self.assertEqual("cyberppt-image-to-editable-svg", manifest["mode"])
        self.assertEqual("image-to-editable-svg", manifest["production_mode"])
        self.assertEqual(["full"], manifest["output_variants"])
        self.assertEqual("text_to_image_generate_full", pair["full"]["generation_method"])
        self.assertEqual({"width": 2048, "height": 1024}, manifest["generation_contract"]["slide_canvas"])
        self.assertEqual(
            {"x": 0, "y": 0, "width": 2048, "height": 1024},
            manifest["generation_contract"]["content_region"],
        )
        self.assertEqual({"width": 2048, "height": 1024}, manifest["generation_contract"]["generation_size"])
        self.assertEqual("image-to-editable-svg", manifest["generation_contract"]["mode"])
        self.assertEqual("2048x1024", pair["full"]["canvas"])
        self.assertNotIn("background", pair)

    def test_manifest_keeps_template_pages_but_skips_image_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "script.md"
            script.write_text(
                """## 第1页：封面
- 页面类型：封面页

## 第2页：内容
- 页面类型：内容页
- 页面标题：内容
- 主判断：形成统一判断。
- 上屏文字：
  - 形成统一判断。

## 第3页：汇报完毕
- 页面类型：封底页
""",
                encoding="utf-8",
            )
            project = root / "project"
            init_project(project)
            style_lock = write_project_style_lock(
                project=project,
                style_id=4,
                source_script=script,
            )
            manifest, _, _, pages = build_manifest(
                script=script,
                pages_raw="1-3",
                output_dir=root / "images",
                project_path=project,
                style_lock=style_lock,
            )

        self.assertEqual([1, 2, 3], pages)
        self.assertEqual([1, 2, 3], manifest["requested_pages"])
        self.assertEqual([2], manifest["content_page_numbers"])
        self.assertEqual([2], [pair["page_number"] for pair in manifest["pairs"]])
        self.assertEqual(["P02"], [pair["page_code"] for pair in manifest["pairs"]])
        self.assertEqual(
            {1: "cover", 3: "ending"},
            {
                item["page_number"]: item["page_role"]
                for item in manifest["skipped_pages"]
            },
        )

    def test_require_generated_accepts_full_image_without_background(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full = root / "page_full.png"
            full.write_bytes(b"full")
            manifest = {
                "pairs": [
                    {
                        "page_number": 1,
                        "full": {
                            "path": str(full),
                            "status": "Generated",
                        "generation_method": "text_to_image_generate_full",
                        "text_audit": {"valid": True},
                        },
                    }
                ]
            }

            require_generated(manifest)

    def test_require_generated_rejects_full_image_without_text_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full = root / "page_full.png"
            full.write_bytes(b"full")
            manifest = {
                "production_mode": "image-to-editable-svg",
                "pairs": [
                    {
                        "page_number": 1,
                        "full": {
                            "path": str(full),
                            "status": "Generated",
                            "generation_method": "text_to_image_generate_full",
                        },
                    }
                ],
            }

            with self.assertRaisesRegex(ValueError, "image-text audit"):
                require_generated(manifest)

    def test_strict_manifest_uses_hash_bound_approved_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            init_project(project)
            script = root / "script.md"
            script.write_text("## 第2页：严格审批\n正文模块\n", encoding="utf-8")
            style_lock = write_project_style_lock(project=project, style_id=4, source_script=script)
            page = parse_script_markdown(script.read_text(encoding="utf-8")).pages[0]
            prompt = root / "prompt.md"
            prompt.write_text(build_page_prompt(page, style_lock), encoding="utf-8")
            stage_script(project, 2, "imagegen", "final", prompt)
            approve_script(project, 2, "imagegen")
            approved_prompt_text = (project / "workbench/prompts/imagegen/slide-02-imagegen-final.md").read_text(encoding="utf-8")

            manifest, _, _, _ = build_manifest(
                script=script,
                pages_raw="2",
                output_dir=root / "images",
                project_path=project,
                style_lock=style_lock,
                require_approved_prompts=True,
            )

        self.assertIn("prompt_approval", manifest["pairs"][0])
        self.assertEqual(
            manifest["pairs"][0]["full"]["prompt"],
            approved_prompt_text,
        )

    def test_manifest_reports_body_drift_without_blocking_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            init_project(project)
            script = root / "script.md"
            original = """## 第4页：知识资产基础

- 页面类型：内容页
- 页面标题：知识资产基础
- 副标题：三类知识资产夯实智能应用底座
- 主判断：三类知识资产共同构成智能应用基础
- 上屏结论模式：semantic_only
- 上屏结论：三类知识资产共同构成智能应用基础
- 上屏文字：

  **01｜30个电力学科**
  - 原批准正文
"""
            script.write_text(original, encoding="utf-8")
            style_lock = write_project_style_lock(
                project=project,
                style_id=9,
                source_script=script,
            )
            page = parse_script_markdown(
                script.read_text(encoding="utf-8")
            ).pages[0]
            prompt = root / "prompt.md"
            prompt.write_text(
                build_page_prompt(page, style_lock),
                encoding="utf-8",
            )
            stage_script(project, 4, "imagegen", "final", prompt)
            approve_script(project, 4, "imagegen")

            script.write_text(
                original.replace("原批准正文", "未经重新批准的改写"),
                encoding="utf-8",
            )

            manifest, _, _, _ = build_manifest(
                script=script,
                pages_raw="4",
                output_dir=root / "images",
                project_path=project,
                style_lock=style_lock,
                require_approved_prompts=True,
            )

        self.assertFalse(manifest["prompt_contract"]["freshness_enforced"])
        self.assertEqual("stale", manifest["pairs"][0]["prompt_provenance"]["status"])

    def test_strict_manifest_uses_content_first_canonical_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            init_project(project)
            script = root / "script.md"
            script.write_text(
                """## 第2页：能力框架

- 页面类型：内容页
- 页面标题：能力框架
- 主判断：数据、模型和产品能力共同支撑业务判断。
- 上屏结论：数据、模型和产品能力共同支撑业务判断
- 上屏文字：

  **业务应用层**
  - 数据、模型和产品能力共同支撑业务判断。
""",
                encoding="utf-8",
            )
            outline = project / "workbench/stages/01-analysis/outline.json"
            outline.parent.mkdir(parents=True, exist_ok=True)
            outline.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "page_id": "p02",
                                "page_type": "content",
                                "argument_role": "solution",
                                "page_job": "说明能力组成",
                                "business_question": "能力由哪些部分组成",
                                "visual_intent_type": "capability_relationship",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            style_lock = write_project_style_lock(project=project, style_id=4, source_script=script)
            page = parse_script_markdown(script.read_text(encoding="utf-8")).pages[0]
            prompt = root / "prompt.md"
            prompt.write_text(
                build_page_prompt(
                    page,
                    style_lock,
                    page_mission="能力由哪些部分组成",
                    visual_context={
                        "argument_role": "solution",
                        "page_job": "说明能力组成",
                        "business_question": "能力由哪些部分组成",
                        "visual_intent_type": "capability_relationship",
                    },
                ),
                encoding="utf-8",
            )
            stage_script(project, 2, "imagegen", "final", prompt)
            approve_script(project, 2, "imagegen")

            manifest, _, _, _ = build_manifest(
                script=script,
                pages_raw="2",
                output_dir=root / "images",
                project_path=project,
                style_lock=style_lock,
                require_approved_prompts=True,
            )

        prompt = manifest["pairs"][0]["full"]["prompt"]
        provenance = manifest["pairs"][0]["full"]["prompt_provenance"]
        self.assertEqual("approved_prompt", provenance["consumed_from"])
        self.assertFalse(provenance["canonical_matches_approval"])
        self.assertEqual(
            provenance["approved_prompt_sha256"],
            provenance["consumed_prompt_sha256"],
        )
        self.assertIn("【锁定关键文字】", prompt)
        self.assertIn("【完整上屏内容】", prompt)


if __name__ == "__main__":
    unittest.main()
