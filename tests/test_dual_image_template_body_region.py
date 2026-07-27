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
    def test_body_region_uses_centered_two_to_one_slot(self) -> None:
        module = load_template_image_ppt_export()
        brand_body_region = {"x": 33, "y": 89, "width": 1214, "height": 607}

        adjusted = module.inset_content_region(brand_body_region)

        self.assertEqual(brand_body_region, adjusted)
        self.assertEqual(adjusted["y"] - 87, 2)
        self.assertEqual(698 - (adjusted["y"] + adjusted["height"]), 2)
        self.assertAlmostEqual(adjusted["width"] / adjusted["height"], 2.0, delta=0.002)
        generation_size = module.generation_size_for_region(adjusted)
        self.assertEqual({"width": 2432, "height": 1216}, generation_size)
        self.assertEqual(2.0, generation_size["width"] / generation_size["height"])

    def test_body_page_surface_has_no_template_image_overlay(self) -> None:
        module = load_template_image_ppt_export()
        rules = module.load_brand_rules()

        surface = rules["body_page_surface"]
        self.assertIsNone(surface["background"])
        self.assertEqual("solid-paper-content-surface", surface["policy"])

    def test_page_role_prefers_declared_template_roles(self) -> None:
        module = load_template_image_ppt_export()

        self.assertEqual(
            "agenda",
            module.page_role(module.PageBlock(2, "汇报安排", "- 页面类型：目录页")),
        )
        self.assertEqual(
            "section",
            module.page_role(
                module.PageBlock(8, "定位与目标", "- 页面类型：章节过渡页")
            ),
        )
        self.assertEqual(
            "ending",
            module.page_role(
                module.PageBlock(32, "汇报完毕，请审议", "- 页面类型：结束页")
            ),
        )

    def test_cover_fields_strip_script_labels(self) -> None:
        module = load_template_image_ppt_export()

        title, author, date = module.cover_content_fields(
            {
                "slide_title": "主标题：备用标题",
                "body_text": (
                    "- 主标题：电力供需预测预警服务建设研究\n"
                    "- 副标题：前期研究汇报\n"
                    "- 汇报单位：中国电力企业联合会\n"
                    "- 汇报日期：2026 年 7 月"
                ),
            }
        )

        self.assertEqual("电力供需预测预警服务建设研究", title)
        self.assertEqual("中国电力企业联合会", author)
        self.assertEqual("2026年7月", date)

    def test_page_notes_prefer_explicit_speaker_notes(self) -> None:
        module = load_template_image_ppt_export()
        block = module.PageBlock(
            4,
            "工作基础",
            (
                "- 上屏文字：可见内容\n\n"
                "【演讲者备注】\n"
                "中电联已经形成覆盖行业统计、分析和服务的工作基础。"
            ),
        )

        self.assertEqual(
            "中电联已经形成覆盖行业统计、分析和服务的工作基础。",
            module.page_notes_text(block),
        )

    def test_template_page_notes_use_role_aware_formal_narration(self) -> None:
        module = load_template_image_ppt_export()
        cases = [
            (
                module.PageBlock(
                    1,
                    "封面",
                    "- 页面类型：封面页\n- 主标题：电力供需预测预警能力建设研究",
                ),
                "下面汇报《电力供需预测预警能力建设研究》。汇报内容将按照既定目录展开。",
            ),
            (
                module.PageBlock(
                    2,
                    "目录",
                    (
                        "- 页面类型：目录页\n- 上屏文字：\n"
                        "- 第一章｜现状基础与能力需求\n"
                        "- 第二章｜定位、目标与研究安排"
                    ),
                ),
                "本次汇报分为2个部分，依次介绍现状基础与能力需求、定位、目标与研究安排。",
            ),
            (
                module.PageBlock(
                    3,
                    "第一章：现状基础与能力需求",
                    "- 页面类型：章节过渡页",
                ),
                "下面汇报“第一章：现状基础与能力需求”，重点说明本章的核心判断、主要依据和相关安排。",
            ),
            (
                module.PageBlock(32, "汇报完毕，请审议", "- 页面类型：封底页"),
                "以上为本次汇报的主要内容，请审议。",
            ),
        ]

        for block, expected in cases:
            with self.subTest(title=block.title):
                notes = module.page_notes_text(block)
                self.assertEqual(expected, notes)
                self.assertNotIn("本页围绕", notes)
                self.assertNotIn("汇报要点", notes)

    def test_agenda_and_section_templates_replace_derived_fields(self) -> None:
        module = load_template_image_ppt_export()
        rules = module.load_brand_rules()

        agenda = module.render_brand_template_svg(
            {
                "page_role": "agenda",
                "agenda_items": [
                    {"number": "01", "title": "现状基础与能力需求"},
                    {"number": "02", "title": "定位、目标与研究安排"},
                ],
            },
            rules,
        )
        section = module.render_brand_template_svg(
            {
                "page_role": "section",
                "section_no": "02",
                "section_title": "定位、目标与研究安排",
                "section_subtitle": "",
            },
            rules,
        )

        self.assertIn("现状基础与能力需求", agenda)
        self.assertIn("定位、目标与研究安排", agenda)
        self.assertNotIn("{{AGENDA_ITEMS}}", agenda)
        self.assertIn(">02</text>", section)
        self.assertIn("定位、目标与研究安排", section)
        self.assertNotIn("{{SECTION_", section)


if __name__ == "__main__":
    unittest.main()
