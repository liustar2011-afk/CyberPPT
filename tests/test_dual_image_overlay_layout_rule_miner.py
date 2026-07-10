from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.dual_image_overlay.layout_rule_miner import mine_layout_rules


class DualImageOverlayLayoutRuleMinerTests(unittest.TestCase):
    def test_mines_breaks_baseline_groups_and_alignment_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            ocr_dir = project_dir / "analysis" / "ocr"
            svg_dir = project_dir / "svg_output"
            ocr_dir.mkdir(parents=True)
            svg_dir.mkdir()
            (ocr_dir / "page_004_text_mapping.json").write_text(
                json.dumps(
                    {
                        "page_number": 4,
                        "boxes": [
                            _box("主体治理与\n合规", 640, 220, 80, 40, "center"),
                            _box("行业\n特性", 70, 509, 40, 43, "center"),
                            _box("系统性", 238, 509, 50, 17, "center"),
                            _box("长周期属性", 433, 509, 76, 17, "center"),
                            _box("强合规属性", 650, 509, 76, 17, "center"),
                            _box("E&S/HSE：项目关键条件", 110, 468, 160, 18, "left"),
                            _box("E&S/HSE：环境、安全、劳工社区", 424, 440, 170, 18, "left"),
                            _box("版本难追溯：来源与时点不清", 728, 468, 170, 18, "left"),
                            _box("供应链准入：质量与交付证明", 1028, 468, 170, 18, "left"),
                            _box("E&S/ESG/HSE与\n供应链责任", 617, 371, 106, 40, "left"),
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (svg_dir / "page_004.svg").write_text(
                """<svg>
<text x="682.52" y="379.89" text-anchor="middle" font-size="16.67">E&amp;S/ESG/HSE与供应链责任</text>
</svg>""",
                encoding="utf-8",
            )

            report = mine_layout_rules(project_dir)

        phrase_breaks = report["line_break"]["phrase_breaks"]
        self.assertIn(
            {"compact_text": "主体治理与合规", "break_text": "主体治理与\n合规", "support": 1},
            phrase_breaks,
        )
        self.assertTrue(any(group["support"] >= 3 and "系统性" in group["labels"] for group in report["baseline_groups"]))
        self.assertTrue(
            any(
                group.get("source") == "repeated_column_body_rows"
                and group["support"] == 4
                and "E&S/HSE：环境、安全、劳工社区" in group["labels"]
                for group in report["baseline_groups"]
            )
        )
        self.assertEqual(report["alignment_issues"][0]["suggested_text_anchor"], "middle")
        self.assertEqual(report["alignment_issues"][0]["current_svg_anchor"], "middle")


def _box(text: str, x: float, y: float, w: float, h: float, align: str) -> dict[str, object]:
    return {
        "text": text,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "font_size": 10,
        "fill": "#0B1F3D",
        "font_weight": "700",
        "align": align,
        "word_wrap": True,
        "confidence": 0.96,
    }


if __name__ == "__main__":
    unittest.main()
