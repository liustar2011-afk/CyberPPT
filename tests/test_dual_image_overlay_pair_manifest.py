from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from cyberppt.commands.init_project import init_project
from cyberppt.commands.script_gate import approve_script, stage_script
from scripts.dual_image_overlay.cyberppt_pair_manifest import build_manifest, main, require_generated
from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks, render_prompt
from scripts.dual_image_overlay.style_library import write_project_style_lock


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
        self.assertEqual((1680, 944), full_size)
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
        self.assertEqual({"width": 1672, "height": 941}, manifest["generation_contract"]["slide_canvas"])
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

    def test_strict_manifest_uses_hash_bound_approved_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            init_project(project)
            script = root / "script.md"
            script.write_text("## 第2页：严格审批\n正文模块\n", encoding="utf-8")
            style_lock = write_project_style_lock(project=project, style_id=4, source_script=script)
            page = parse_page_blocks(script)[2]
            prompt = root / "prompt.md"
            prompt.write_text(render_prompt(page, style_lock_path=style_lock), encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
