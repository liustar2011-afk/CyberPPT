from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.dual_image_overlay import cyberppt_pair_manifest as module
from scripts.dual_image_overlay.cyberppt_pair_manifest import main, require_generated
from scripts.dual_image_overlay.deliverable_prompt import validate_imagegen_script


class CyberpptPairManifestTests(unittest.TestCase):
    def test_build_manifest_skips_template_only_pages_and_keeps_content_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "imagegen_script.md"
            output_dir = root / "images"
            script.write_text(
                """## 第1页：封面
【页面类型】
本页类型：封面页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 年度工作汇报

【构图指令】
正式内部汇报封面。

【结构密度】
- 单一主标题

## 第2页：目录
【页面类型】
本页类型：目录页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 一、工作回顾

【构图指令】
正式内部汇报目录。

【结构密度】
- 目录列表

## 第3页：第一章 工作回顾
【页面类型】
本页类型：章节过渡页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 章节过渡

【构图指令】
正式内部汇报章节过渡页。

【结构密度】
- 单一章节标题

## 第4页：重点成果
【页面类型】
本页类型：内容页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 完成年度重点任务。

【构图指令】
正式内部汇报正文内容区。

【结构密度】
- 一项重点成果

## 第5页：感谢
【页面类型】
本页类型：结束页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 感谢聆听

【构图指令】
正式内部汇报结束页。

【结构密度】
- 单一结束语
""",
                encoding="utf-8",
            )

            manifest, *_ = module.build_manifest(
                script=script,
                pages_raw="1-5",
                output_dir=output_dir,
                project_path=None,
                style_lock=None,
            )

        self.assertEqual([4], [pair["page_number"] for pair in manifest["pairs"]])
        self.assertEqual([1, 2, 3, 4, 5], manifest["requested_pages"])
        self.assertEqual(
            [(1, "cover"), (2, "agenda"), (3, "section"), (5, "ending")],
            [(item["page_number"], item["page_role"]) for item in manifest["skipped_pages"]],
        )

    def test_build_manifest_rejects_navigation_only_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "imagegen_script.md"
            script.write_text(
                """## 第1页：封面
【页面类型】
本页类型：封面页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 年度工作汇报

【构图指令】
正式内部汇报封面。

【结构密度】
- 单一主标题

## 第2页：目录
【页面类型】
本页类型：目录页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 一、工作回顾

【构图指令】
正式内部汇报目录。

【结构密度】
- 目录列表

## 第3页：第一章 工作回顾
【页面类型】
本页类型：章节过渡页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 章节过渡

【构图指令】
正式内部汇报章节过渡页。

【结构密度】
- 单一章节标题

## 第5页：感谢
【页面类型】
本页类型：结束页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 感谢聆听

【构图指令】
正式内部汇报结束页。

【结构密度】
- 单一结束语
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "no content pages selected for image generation"):
                module.build_manifest(
                    script=script,
                    pages_raw="1-3,5",
                    output_dir=root / "images",
                    project_path=None,
                    style_lock=None,
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
            blueprint.write_bytes(b"approved-blueprint")

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
            full_bytes = Path(pair["full"]["path"]).read_bytes()

        self.assertEqual(code, 0)
        self.assertEqual("cyberppt-full-image-only", manifest["mode"])
        self.assertEqual(["full"], manifest["output_variants"])
        self.assertEqual("Generated", full_status)
        self.assertEqual(b"approved-blueprint", full_bytes)
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
            imagegen_script = Path(manifest["imagegen_script"])
            imagegen_script_exists = imagegen_script.is_file()
            imagegen_text = imagegen_script.read_text(encoding="utf-8")
            policy_report = manifest["prompt_policy_report"]
            policy_report_exists = Path(policy_report["path"]).is_file()

        self.assertEqual(code, 0)
        self.assertTrue(style_lock_exists)
        self.assertTrue(imagegen_script_exists)
        self.assertEqual(str(imagegen_script), manifest["source_script"])
        self.assertIn("imagegen_script_sha256", manifest)
        self.assertEqual("content_lock", manifest["prompt_contract"]["visible_text_source"])
        self.assertTrue(manifest["prompt_contract"]["control_sections_non_visible"])
        self.assertTrue(manifest["prompt_contract"]["human_editable_source"])
        report = manifest["prompt_policy_report"]
        self.assertEqual("passed", report["status"])
        self.assertTrue(policy_report_exists)
        self.assertTrue(report["sha256"])
        self.assertIn("## 第3页：先生成全图，再由全图派生无文字底图", imagegen_text)
        self.assertEqual(pair["page_script"], pair["full"]["prompt"])
        self.assertIn(pair["full"]["prompt"], imagegen_text)
        self.assertEqual("cyberppt-full-image-only", manifest["mode"])
        self.assertEqual(["full"], manifest["output_variants"])
        self.assertEqual("text_to_image_generate_full", pair["full"]["generation_method"])
        self.assertEqual({"width": 1680, "height": 944}, manifest["generation_contract"]["slide_canvas"])
        self.assertEqual({"width": 1680, "height": 944}, manifest["generation_contract"]["generation_size"])
        self.assertEqual("full-image-only", manifest["generation_contract"]["mode"])
        self.assertEqual("1680x944", pair["full"]["canvas"])
        self.assertNotIn("background", pair)

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

    def test_edited_imagegen_script_recompiles_manifest_without_rewriting_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "images"
            output_dir.mkdir()
            script = output_dir / "imagegen_script.md"
            script.write_text(
                """## 第5页：人工修订页

【页面类型】
本页类型：内容页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 人工追加的生图控制语句

【构图指令】
保留用户手工修改后的构图要求，不得重新归纳。

【结构密度】
- 保持正文区信息密度
""",
                encoding="utf-8",
            )

            code = main(
                [
                    "--script",
                    str(script),
                    "--pages",
                    "5",
                    "--output-dir",
                    str(output_dir),
                    "--project-path",
                    str(root / "project"),
                    "--style-id",
                    "5",
                ]
            )
            manifest = json.loads((output_dir / "page_image_pairs.json").read_text(encoding="utf-8"))
            prompt = manifest["pairs"][0]["full"]["prompt"]

        self.assertEqual(code, 0)
        self.assertIn("人工追加的生图控制语句", prompt)
        self.assertIn("不得重新归纳", prompt)

    def test_edited_imagegen_script_with_process_text_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "imagegen_script.md"
            script.write_text(
                """## 第1页：人工修订页

【页面类型】
本页类型：内容页。此信息只用于构图，不得作为页面可见文字。

【内容锁定】
- 真实业务内容
- 本页说明：请将内容放在左侧。

【构图指令】
生成正式内部汇报正文内容区。

【结构密度】
- 左侧正文区
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "process_instruction"):
                validate_imagegen_script(script, [1])


if __name__ == "__main__":
    unittest.main()
