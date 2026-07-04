from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from scripts.dual_image_overlay.blueprint_image_miner import mine_blueprint_images


class BlueprintImageMinerTests(unittest.TestCase):
    def test_mines_blueprint_chrome_and_manifest_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            blueprint_dir = Path(tmp)
            (blueprint_dir / "blueprint-manifest.json").write_text(
                json.dumps(
                    {
                        "slides": [
                            {
                                "slide": 1,
                                "title": "测试页",
                                "role": "测试",
                                "density_target": "internal high-density briefing page",
                                "chart_plan": "测试矩阵",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            image = Image.new("RGB", (1672, 941), (247, 246, 240))
            draw = ImageDraw.Draw(image)
            dark_blue = (18, 53, 91)
            draw.rectangle((0, 0, 82, 70), fill=dark_blue)
            draw.rectangle((60, 120, 1600, 780), outline=dark_blue, width=4)
            draw.rectangle((50, 830, 1620, 905), fill=dark_blue)
            image.save(blueprint_dir / "slide-01-blueprint.png")

            report = mine_blueprint_images(blueprint_dir)

        self.assertEqual(report["sample_count"], 1)
        self.assertEqual(report["slides"][0]["title"], "测试页")
        self.assertEqual(report["slides"][0]["role"], "测试")
        self.assertIsNotNone(report["slides"][0]["top_badge_bbox"])
        self.assertIsNotNone(report["slides"][0]["lower_dark_band_bbox"])
        self.assertIsNotNone(report["learned_rules"]["safe_body_zone_median"])
        self.assertEqual(report["learned_rules"]["roles_seen"], ["测试"])


if __name__ == "__main__":
    unittest.main()
