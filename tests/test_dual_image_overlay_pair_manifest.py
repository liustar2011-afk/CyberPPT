from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.dual_image_overlay.cyberppt_pair_manifest import main, require_generated


class CyberpptPairManifestTests(unittest.TestCase):
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

        self.assertEqual(code, 0)
        self.assertTrue(style_lock_exists)
        self.assertTrue(imagegen_script_exists)
        self.assertEqual(str(imagegen_script), manifest["source_script"])
        self.assertIn("imagegen_script_sha256", manifest)
        self.assertIn("## 第3页：先生成全图，再由全图派生无文字底图", imagegen_text)
        self.assertEqual(pair["page_script"], pair["full"]["prompt"])
        self.assertIn(pair["full"]["prompt"], imagegen_text)
        self.assertEqual("cyberppt-full-image-only", manifest["mode"])
        self.assertEqual(["full"], manifest["output_variants"])
        self.assertEqual("text_to_image_generate_full", pair["full"]["generation_method"])
        self.assertEqual({"width": 1672, "height": 941}, manifest["generation_contract"]["slide_canvas"])
        self.assertEqual({"width": 1672, "height": 941}, manifest["generation_contract"]["generation_size"])
        self.assertEqual("full-image-only", manifest["generation_contract"]["mode"])
        self.assertEqual("1672x941", pair["full"]["canvas"])
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


if __name__ == "__main__":
    unittest.main()
