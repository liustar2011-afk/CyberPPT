from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from scripts.dual_image_overlay.background_text_scan import scan_background_text
from scripts.dual_image_overlay.layout_qa import check_layout
from scripts.dual_image_overlay.semantic_plan import load_semantic_plan
from scripts.dual_image_overlay.text_content_qa import build_text_content_qa


ROOT = Path(__file__).resolve().parents[1]


def _render_fixture(tmp_path: Path, text: str) -> Path:
    background = tmp_path / "background.png"
    Image.new("RGB", (1280, 720), "#FFFFFF").save(background)
    output = tmp_path / "out.pptx"
    job = tmp_path / "job.json"
    job.write_text(
        json.dumps(
            {
                "canvas": {"width": 1280, "height": 720},
                "slide": {"width_in": 13.333, "height_in": 7.5},
                "background": str(background),
                "output_pptx": str(output),
                "boxes": [
                    {
                        "text": text,
                        "bbox": [80, 40, 500, 100],
                        "font_size": 18,
                        "font_family": "Arial",
                        "fill": "#111111",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    subprocess.run(
        ["node", str(ROOT / "scripts/dual_image_overlay/render_overlay.mjs"), str(job)],
        cwd=ROOT,
        check=True,
    )
    return output


class DualImageOverlayQaTests(unittest.TestCase):
    def test_text_content_qa_compares_pptx_text_to_expected(self) -> None:
        with TemporaryDirectory() as directory:
            pptx = _render_fixture(Path(directory), "核心结论")
            report = build_text_content_qa(pptx, ["核心结论"])
        self.assertTrue(report["valid"])
        self.assertTrue(report["checks"]["pptx_text_matches_expected"])

    def test_background_text_scan_fails_when_ocr_items_exist(self) -> None:
        with TemporaryDirectory() as directory:
            layout = Path(directory) / "background_layout.json"
            layout.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1280, "height": 720},
                        "items": [{"text": "残字", "bbox": [1, 1, 20, 20]}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report = scan_background_text(layout)
        self.assertFalse(report["valid"])
        self.assertEqual(report["error_count"], 1)

    def test_layout_qa_detects_container_overflow(self) -> None:
        with TemporaryDirectory() as directory:
            semantic = Path(directory) / "semantic_plan.json"
            semantic.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1280, "height": 720},
                        "containers": [
                            {
                                "id": "c1",
                                "role": "body",
                                "bbox": [100, 100, 300, 200],
                                "text_safe_bbox": [100, 100, 300, 200],
                            }
                        ],
                        "items": [
                            {
                                "display_text": "正文",
                                "source_text": "正文",
                                "role": "body",
                                "container_id": "c1",
                                "bbox": [90, 100, 310, 200],
                                "font_size": 12,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report = check_layout(load_semantic_plan(semantic))
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(issue["code"] == "text_box_outside_container" for issue in report["issues"])
        )


if __name__ == "__main__":
    unittest.main()
