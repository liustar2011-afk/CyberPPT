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
            background_status = pair["background"]["status"]

        self.assertEqual(code, 0)
        self.assertEqual("Generated", full_status)
        self.assertEqual(b"approved-blueprint", full_bytes)
        self.assertEqual("Pending", background_status)

    def test_background_manifest_requires_edit_from_corresponding_full(self) -> None:
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
        self.assertEqual("text_to_image_generate_full", pair["full"]["generation_method"])
        self.assertEqual("image_to_image_edit_from_full", pair["background"]["generation_method"])
        self.assertEqual(pair["full"]["path"], pair["background"]["depends_on_full_path"])
        self.assertEqual("full", pair["background"]["input_variant"])
        self.assertTrue(pair["background"]["requires_input_image"])

    def test_require_generated_rejects_background_without_full_derivation_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full = root / "page_full.png"
            background = root / "page_background.png"
            full.write_bytes(b"full")
            background.write_bytes(b"background")
            manifest = {
                "pairs": [
                    {
                        "page_number": 1,
                        "full": {"path": str(full), "status": "Generated"},
                        "background": {"path": str(background), "status": "Generated"},
                    }
                ]
            }

            with self.assertRaisesRegex(ValueError, "image_to_image_edit_from_full"):
                require_generated(manifest)


if __name__ == "__main__":
    unittest.main()
