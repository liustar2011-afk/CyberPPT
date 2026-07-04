from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from scripts.dual_image_overlay.alignment import AlignmentTransform, estimate_alignment


class DualImageOverlayAlignmentTests(unittest.TestCase):
    def test_alignment_transform_maps_bbox_consistently(self) -> None:
        transform = AlignmentTransform(scale=1.01, dx=8, dy=-4)
        mapped = transform.map_bbox([100, 100, 200, 160])
        self.assertEqual([102.6, 93.4, 203.6, 154.0], [round(v, 1) for v in mapped])

    def test_estimate_alignment_recovers_small_translation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            full = Image.new("RGB", (1280, 720), "#FFFFFF")
            draw = ImageDraw.Draw(full)
            draw.rectangle([300, 180, 980, 540], outline="#111111", width=8)
            draw.rectangle([460, 300, 820, 360], fill="#111111")
            full_path = root / "full.png"
            full.save(full_path)

            background = Image.new("RGB", (1280, 720), "#FFFFFF")
            draw = ImageDraw.Draw(background)
            draw.rectangle([312, 174, 992, 534], outline="#111111", width=8)
            background_path = root / "background.png"
            background.save(background_path)

            layout = {"items": [{"bbox": [460, 300, 820, 360]}]}
            transform = estimate_alignment(full_path, background_path, layout)

        self.assertAlmostEqual(12, transform.dx, delta=4)
        self.assertAlmostEqual(-6, transform.dy, delta=4)


if __name__ == "__main__":
    unittest.main()
