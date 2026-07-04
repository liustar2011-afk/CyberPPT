from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.dual_image_overlay.cyberppt_pair_manifest import main


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


if __name__ == "__main__":
    unittest.main()
