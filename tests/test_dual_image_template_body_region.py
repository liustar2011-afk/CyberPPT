from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
