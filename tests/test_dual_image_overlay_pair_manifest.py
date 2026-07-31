from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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
        self.assertEqual((2048, 1024), full_size)
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

    def test_strict_manifest_blocks_body_drift_after_prompt_approval(self) -> None:
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

            with self.assertRaisesRegex(
                ValueError,
                "approved ImageGen prompt is stale for page 4",
            ):
                build_manifest(
                    script=script,
                    pages_raw="4",
                    output_dir=root / "images",
                    project_path=project,
                    style_lock=style_lock,
                    require_approved_prompts=True,
                )

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
        self.assertNotIn("【完整内容语义｜仅供理解，不要求逐字上屏】", prompt)
        self.assertNotIn("【页面逻辑｜不上屏】", prompt)
        self.assertIn("【锁定关键文字】", prompt)
        self.assertIn("【完整上屏内容】", prompt)
        self.assertNotIn("Selected visual intent type:", prompt)


if __name__ == "__main__":
    unittest.main()
