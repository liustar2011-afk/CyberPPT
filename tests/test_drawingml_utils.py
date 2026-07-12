from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "scripts"
    / "dual_image_overlay"
    / "rebuild_engine"
    / "svg_to_pptx"
    / "drawingml_utils.py"
)


def load_drawingml_utils():
    package_root = str(ROOT / "scripts" / "dual_image_overlay")
    if package_root not in sys.path:
        sys.path.insert(0, package_root)
    from rebuild_engine.svg_to_pptx import drawingml_utils

    return drawingml_utils


class DrawingmlFontFamilyTest(unittest.TestCase):
    def test_source_han_sans_cn_is_preserved_as_east_asian_font(self) -> None:
        module = load_drawingml_utils()

        fonts = module.parse_font_family("Source Han Sans CN, PingFang SC, sans-serif")

        self.assertEqual(fonts["ea"], "Source Han Sans CN")
        self.assertEqual(
            module.resolve_text_run_fonts("中文", fonts)["ea"],
            "Source Han Sans CN",
        )


if __name__ == "__main__":
    unittest.main()
