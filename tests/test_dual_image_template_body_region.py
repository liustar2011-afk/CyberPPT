from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "scripts"
    / "dual_image_overlay"
    / "rebuild_engine"
    / "template_image_ppt_export.py"
)


def load_template_image_ppt_export():
    scripts_dir = SCRIPT.parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location("template_image_ppt_export_for_region_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


class DualImageTemplateBodyRegionTest(unittest.TestCase):
    def test_expanded_body_region_stays_below_master_red_divider(self) -> None:
        module = load_template_image_ppt_export()
        brand_body_region = {"x": 58, "y": 122, "width": 1164, "height": 554}

        adjusted = module.inset_content_region(brand_body_region)

        self.assertEqual({"x": 20, "y": 104, "width": 1240, "height": 592}, adjusted)
        self.assertGreaterEqual(adjusted["y"], 104)

    def test_normalize_generated_image_size_rejects_portrait_output(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "portrait.png"
            Image.new("RGB", (1024, 1536), "#f7f6f0").save(image_path)

            with self.assertRaisesRegex(ValueError, "portrait|aspect"):
                module.normalize_generated_image_size(image_path, "1680x944")

    def test_normalize_generated_image_size_contains_close_landscape_without_distortion(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "landscape.png"
            Image.new("RGB", (1672, 941), "#12355b").save(image_path)

            normalized = module.normalize_generated_image_size(image_path, "1680x944")

            self.assertEqual((1680, 944), normalized)
            with Image.open(image_path) as image:
                self.assertEqual((1680, 944), image.size)


if __name__ == "__main__":
    unittest.main()
