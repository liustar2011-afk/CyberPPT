from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pptx import Presentation
from pptx.util import Inches

from scripts.presentation_qa.render_page import check_pptx_geometry


class PresentationQaTests(unittest.TestCase):
    def test_clean_deck_has_no_geometry_failures(self) -> None:
        with TemporaryDirectory() as directory:
            pptx_path = Path(directory) / "deck.pptx"
            presentation = Presentation()
            presentation.slide_width = Inches(13.333)
            presentation.slide_height = Inches(7.5)
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            first = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(3), Inches(0.5))
            first.text_frame.text = "标题"
            second = slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(3), Inches(0.5))
            second.text_frame.text = "正文"
            presentation.save(str(pptx_path))

            report = check_pptx_geometry(pptx_path)

        self.assertTrue(report["valid"])
        self.assertEqual(0, report["slides"][0]["overlap_count"])
        self.assertEqual(0, report["slides"][0]["out_of_bounds_count"])

    def test_overlapping_text_boxes_fail_geometry_gate(self) -> None:
        with TemporaryDirectory() as directory:
            pptx_path = Path(directory) / "deck.pptx"
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            first = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(2), Inches(0.4))
            first.text_frame.text = "授权管理"
            second = slide.shapes.add_textbox(Inches(1.05), Inches(1.1), Inches(2), Inches(0.4))
            second.text_frame.text = "访问主体"
            presentation.save(str(pptx_path))

            report = check_pptx_geometry(pptx_path)

        self.assertFalse(report["valid"])
        self.assertEqual(1, report["slides"][0]["overlap_count"])


if __name__ == "__main__":
    unittest.main()
