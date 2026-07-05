from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def _pptx_texts(path: Path) -> list[str]:
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    texts: list[str] = []
    with zipfile.ZipFile(path) as package:
        slide_xml = package.read("ppt/slides/slide1.xml")
    root = ET.fromstring(slide_xml)
    for node in root.findall(".//a:t", ns):
        if node.text:
            texts.append(node.text)
    return texts


class DualImageOverlayRendererTest(unittest.TestCase):
    def test_renderer_writes_background_and_editable_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            background = tmp_path / "background.png"
            Image.new("RGB", (1280, 720), "#F2F3EF").save(background)
            output = tmp_path / "overlay.pptx"
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
                                "text": "核心结论",
                                "bbox": [80, 40, 600, 110],
                                "font_size": 24,
                                "font_family": "Arial",
                                "fill": "#111111",
                                "bold": True,
                                "align": "left",
                                "v_align": "mid",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts" / "dual_image_overlay" / "render_overlay.mjs"),
                    str(job),
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertTrue(output.is_file())
            with zipfile.ZipFile(output) as package:
                names = package.namelist()
                self.assertIn("ppt/slides/slide1.xml", names)
                self.assertTrue(any(name.startswith("ppt/media/") for name in names))
            self.assertEqual(_pptx_texts(output), ["核心结论"])

    def test_renderer_can_disable_text_wrapping_for_office_fidelity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            background = tmp_path / "background.png"
            Image.new("RGB", (1280, 720), "#FFFFFF").save(background)
            output = tmp_path / "overlay.pptx"
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
                                "text": "企业/业务数据",
                                "bbox": [80, 40, 148, 56],
                                "font_size": 8,
                                "font_family": "Arial",
                                "fill": "#111111",
                                "wrap": False,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    "node",
                    str(ROOT / "scripts" / "dual_image_overlay" / "render_overlay.mjs"),
                    str(job),
                ],
                cwd=ROOT,
                check=True,
            )

            with zipfile.ZipFile(output) as package:
                slide_xml = package.read("ppt/slides/slide1.xml").decode("utf-8")
            self.assertIn('wrap="none"', slide_xml)


if __name__ == "__main__":
    unittest.main()
