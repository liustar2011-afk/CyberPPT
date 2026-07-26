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
    def test_body_region_keeps_1680_944_slot_below_master_red_divider(self) -> None:
        module = load_template_image_ppt_export()
        brand_body_region = {"x": 100, "y": 89, "width": 1080, "height": 607}

        adjusted = module.inset_content_region(brand_body_region)

        self.assertEqual(brand_body_region, adjusted)
        self.assertEqual(adjusted["y"] - 87, 2)  # 2px below red bottom (84+3)
        self.assertEqual(698 - (adjusted["y"] + adjusted["height"]), 2)
        self.assertAlmostEqual(adjusted["width"] / adjusted["height"], 1680 / 944, delta=0.002)

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


if __name__ == "__main__":
    unittest.main()
