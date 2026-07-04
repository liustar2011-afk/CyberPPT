from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"


class DualImageRebuildEngineAssetsTest(unittest.TestCase):
    def test_rebuild_engine_required_files_exist(self) -> None:
        required = [
            "editable_overlay_rebuild.py",
            "ocr_text_locator.py",
            "script_text_overlay.py",
            "template_image_ppt_export.py",
            "svg_quality_checker.py",
            "finalize_svg.py",
            "svg_to_pptx.py",
            "svg_to_pptx/__init__.py",
            "svg_finalize/__init__.py",
            "templates/brands/中电联公共元素_轻量版/brand_rules.json",
            "templates/brands/中电联公共元素_轻量版/master_elements.svg",
        ]

        missing = [path for path in required if not (ENGINE / path).is_file()]

        self.assertEqual([], missing)

    def test_dual_image_runtime_does_not_reference_legacy_paths(self) -> None:
        runtime = ROOT / "scripts" / "dual_image_overlay"
        offenders = []
        forbidden = (
            "/Volumes/DOC/" + "ppt-" + "master",
            "vendor/" + "ppt_" + "master_dual_image",
            "vendor." + "ppt_" + "master_dual_image",
            "page_image_" + "pair_batch",
        )

        for suffix in ("*.py", "*.mjs"):
            for path in runtime.rglob(suffix):
                text = path.read_text(encoding="utf-8")
                if any(item in text for item in forbidden):
                    offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
