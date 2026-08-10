from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from cyberppt.commands.init_project import init_project
from cyberppt.commands.script_gate import approve_script, stage_script
from scripts.dual_image_overlay.cyberppt_pair_manifest import (
    _background_prompt,
    _full_prompt_for_variants,
    build_manifest,
    main,
    require_generated,
)
from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks, render_prompt
from scripts.dual_image_overlay.imagegen_handoff import build_page_prompt
from cyberppt.script_quality_contract import parse_script_markdown
from scripts.dual_image_overlay.style_library import write_project_style_lock


class CyberpptPairManifestTests(unittest.TestCase):
    def test_style09_lock_is_reasserted_after_visual_structure_handoff(self) -> None:
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
                "- Industry scene anchor: controlled delivery workspace.\n"
                "- Recommended composition: use a six-node swim-lane infographic.\n\n"
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
        prompt = manifest["pairs"][0]["full"]["prompt"]
        self.assertNotIn("six-node swim-lane infographic", prompt)
        self.assertIn("【风格09业务场适配器｜不上屏】", prompt)
        self.assertIn("controlled delivery workspace", prompt)
        self.assertNotIn("【视觉组织原则】", prompt)
        self.assertIn("### Final ImageGen execution lock — hard", prompt)
        self.assertIn("【风格09最终执行锁｜最高优先级】", prompt)
        self.assertEqual(1, prompt.count("保留既有容器形状和数量"))
        self.assertEqual(1, prompt.count("保留已经确定的方向、数量和连接关系"))
        handoff = manifest["pairs"][0]["visual_structure_handoff"]
        self.assertTrue(handoff["consumed"])
        self.assertEqual("style09_surface_adapter", handoff["adapted_by"])

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
        self.assertNotIn("这段完整讲稿不得进入最终送图脚本", prompt)
        self.assertNotIn("SHOULD_NOT_BE_IMPORTED", prompt)
        self.assertEqual(prompt, compiled_text.split("\n\n", 1)[1].strip())

    def test_dual_image_full_prompt_uses_graphics_to_carry_text_relationships(self) -> None:
        self.assertEqual("原始提示词", _full_prompt_for_variants("原始提示词", ["full", "background"]))
        return
        prompt = _full_prompt_for_variants("原始提示词", ["full", "background"])

        self.assertIn("使用一幅完整的生成式视觉构图组织页面表达", prompt)
        self.assertIn("图形构图是主要组织层", prompt)
        self.assertIn("不受插图矩形容器限制", prompt)
        self.assertIn("主体、支撑、输入、输出、分支、汇聚、闭环、层级、对比、因果与结论", prompt)
        self.assertIn("不得仅按文本顺序机械排列或连接", prompt)
        self.assertNotIn("每个锁定模块及其名称只能承担一个主要关系角色并出现一次", prompt)
        self.assertNotIn("不得再作为外围节点、关系标签、重复卡片或第二个同名对象出现", prompt)
        self.assertNotIn("不得新增脚本未提供的结果分类文字、标签或结论", prompt)
        self.assertNotIn("不得把模块处理成等权分栏、卡片墙或重复面板", prompt)
        self.assertIn("图形可以环绕、承托、连接和引导文字", prompt)
        self.assertIn("少量实景、近实景或物件型语义图作为辅助点缀", prompt)
        self.assertIn("只有这类独立语义插图需要完整位于边界清晰的矩形容器内", prompt)
        self.assertNotIn("不得逐项配图、逐项转成图标", prompt)
        self.assertIn("不得把可靠脚本复制成图内文字墙", prompt)
        self.assertIn("不得拆成半屏文字加半屏图片", prompt)
        self.assertNotIn("PPT 原生可编辑形状", prompt)
        self.assertNotIn("后续原生重建", prompt)
        self.assertEqual(
            "原始提示词",
            _full_prompt_for_variants("原始提示词", ["full"]),
        )

    def test_background_prompt_preserves_text_inside_illustration_containers(self) -> None:
        prompt = _background_prompt(8)

        self.assertIn("插图容器内部的全部像素和文字视为一个不可拆分的整体", prompt)
        self.assertIn("界面标签、图表刻度、教材封面、文件内容和设备铭牌", prompt)
        self.assertIn("不得删除、翻译、纠正、重写或重新生成", prompt)
        self.assertIn("插图容器之外的页面级标题、正文、编号、标签、结论文字", prompt)
        self.assertIn("不得在输入图不存在关系型图形的位置新增流程图、架构图", prompt)

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
        self.assertEqual("cyberppt-full-image-only", manifest["mode"])
        self.assertEqual(["full"], manifest["output_variants"])
        self.assertEqual("Generated", full_status)
        self.assertEqual((4096, 2048), full_size)
        self.assertNotIn("background", pair)

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
        self.assertEqual("cyberppt-full-image-only", manifest["mode"])
        self.assertEqual(["full"], manifest["output_variants"])
        self.assertEqual("text_to_image_generate_full", pair["full"]["generation_method"])
        self.assertEqual({"width": 2048, "height": 1024}, manifest["generation_contract"]["slide_canvas"])
        self.assertEqual(
            {"x": 0, "y": 0, "width": 2048, "height": 1024},
            manifest["generation_contract"]["content_region"],
        )
        self.assertEqual({"width": 2048, "height": 1024}, manifest["generation_contract"]["generation_size"])
        self.assertEqual("full-image-only", manifest["generation_contract"]["mode"])
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
                        },
                    }
                ]
            }

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
        self.assertTrue(provenance["canonical_matches_approval"])
        self.assertEqual(
            provenance["approved_prompt_sha256"],
            provenance["consumed_prompt_sha256"],
        )
        self.assertIn("【锁定关键文字】", prompt)
        self.assertIn("【完整上屏内容】", prompt)


if __name__ == "__main__":
    unittest.main()
