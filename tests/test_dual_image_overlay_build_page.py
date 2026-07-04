from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class DualImageOverlayBuildPageTests(unittest.TestCase):
    def test_build_page_creates_pptx_and_qa_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            full = tmp_path / "full.png"
            background = tmp_path / "background.png"
            Image.new("RGB", (1672, 941), "#F2F3EF").save(full)
            Image.new("RGB", (1672, 941), "#F2F3EF").save(background)
            semantic = tmp_path / "semantic_plan.json"
            semantic.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1672, "height": 941},
                        "containers": [
                            {
                                "id": "title",
                                "role": "title",
                                "bbox": [80, 40, 900, 150],
                                "text_safe_bbox": [90, 50, 880, 140],
                            }
                        ],
                        "items": [
                            {
                                "source_text": "核心结论",
                                "display_text": "核心结论",
                                "role": "title",
                                "container_id": "title",
                                "relative_bbox": [0, 0, 1, 1],
                                "font_size": 18,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            out_dir = tmp_path / "page"
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/build_page.py"),
                    "--full",
                    str(full),
                    "--background",
                    str(background),
                    "--semantic-plan",
                    str(semantic),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            self.assertTrue((out_dir / "normalized/full-1280x720.png").is_file())
            self.assertTrue((out_dir / "normalized/background-1280x720.png").is_file())
            self.assertTrue((out_dir / "exports/page.pptx").is_file())
            self.assertTrue((out_dir / "analysis/visual_preview.json").is_file())
            readiness = json.loads(
                (out_dir / "analysis/production_readiness.json").read_text(encoding="utf-8")
            )
        self.assertFalse(readiness["valid"])
        self.assertTrue(readiness["structural_valid"])
        self.assertEqual("visual_review_required", readiness["status"])
        self.assertTrue(readiness["checks"]["text_content_matches_lock"])
        self.assertTrue(readiness["checks"]["layout_qa_pass"])
        self.assertFalse(readiness["checks"]["visual_preview_generated"])
        self.assertFalse(readiness["checks"]["human_visual_review_pass"])
        self.assertEqual("semantic_plan_containers", readiness["geometry_source"])
        self.assertEqual("semantic-container-geometry", readiness["alignment"]["model"])


if __name__ == "__main__":
    unittest.main()
