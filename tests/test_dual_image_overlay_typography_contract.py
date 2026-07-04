from __future__ import annotations

import unittest

from scripts.dual_image_overlay.typography_contract import (
    apply_typography_to_svg_text,
    classify_text,
)


class DualImageOverlayTypographyContractTests(unittest.TestCase):
    def test_classifies_short_grid_items_as_section_titles(self) -> None:
        self.assertEqual(classify_text("1. 补齐企业能力可信表达短板", 240, 310, "#0B1F3D", "700"), "T6")
        self.assertEqual(classify_text("3.3", 400, 260, "#0B1F3D", "700"), "T13")
        self.assertEqual(classify_text("1", 120, 320, "#0B1F3D", "700"), "T4")
        self.assertEqual(classify_text("万亿美元", 580, 300, "#0B1F3D", "700"), "T6")
        self.assertEqual(classify_text("建议由中电联牵头，建设出海能力可信证明体系", 32, 46, "#123B66", "700"), "T2")
        self.assertEqual(
            classify_text('"多角色多场景特征决定评价体系必须分角色、分场景设计"', 183, 631, "#FFFFFF", "700"),
            "T8",
        )

    def test_applies_scale_and_fits_long_header(self) -> None:
        svg = """<svg>
<text x="32" y="46" font-size="25" font-weight="700" fill="#123B66">建议由中电联牵头，建设出海能力可信证明体系</text>
<text x="240" y="310" font-size="13.21" font-weight="400" fill="#0B1F3D">1. 补齐企业能力可信表达短板</text>
<text x="400" y="260" text-anchor="middle" font-size="28" font-weight="700" fill="#0B1F3D">3.3</text>
</svg>"""

        updated, decisions = apply_typography_to_svg_text(svg)

        self.assertIn('font-size="30.00"', updated)
        self.assertIn('font-size="16.67"', updated)
        self.assertIn('<tspan x="240.00"', updated)
        self.assertIn(">1.补齐企业能力</tspan>", updated)
        self.assertIn(">可信表达短板</tspan>", updated)
        self.assertIn('font-size="32.00"', updated)
        self.assertEqual([decision.role for decision in decisions], ["T2", "T6", "T13"])

    def test_fits_centered_grid_labels_to_local_cell_width(self) -> None:
        svg = """<svg>
<text x="977.32" y="232.01" text-anchor="middle" font-size="7.84" font-weight="700" fill="#0B1F3D">国际项目经验
与交付</text>
<text x="617.15" y="379.89" text-anchor="start" font-size="8.0" font-weight="700" fill="#0B1F3D">E&amp;S/ESG/HSE与
供应链责任</text>
</svg>"""

        updated, decisions = apply_typography_to_svg_text(svg)

        self.assertIn('font-size="16.67"', updated)
        self.assertIn(">国际项目经验</tspan>", updated)
        self.assertIn(">与交付</tspan>", updated)
        self.assertIn(">E&amp;S/ESG/HSE</tspan>", updated)
        self.assertIn(">与供应链责任</tspan>", updated)
        self.assertIn('x="682.52"', updated)
        self.assertIn('text-anchor="middle"', updated)
        self.assertEqual(updated.count("<tspan"), 4)
        self.assertTrue(all(decision.applied_px == 16.67 for decision in decisions))
        self.assertEqual(
            [decision.rendered_text for decision in decisions],
            ["国际项目经验\n与交付", "E&S/ESG/HSE\n与供应链责任"],
        )
        self.assertEqual(decisions[1].x, 682.52)

    def test_prefers_business_semantic_breaks_in_hexagon_labels(self) -> None:
        svg = """<svg>
<text x="165.28" y="222.63" text-anchor="middle" font-size="16" font-weight="700" fill="#0B1F3D">平台型和集成型企业</text>
<text x="165.28" y="342.08" text-anchor="middle" font-size="16" font-weight="700" fill="#0B1F3D">运维与技术服务类</text>
<text x="289.67" y="277.80" text-anchor="middle" font-size="16" font-weight="700" fill="#FFFFFF">企业类型分类</text>
</svg>"""

        updated, decisions = apply_typography_to_svg_text(svg)

        self.assertIn(">平台型和</tspan>", updated)
        self.assertIn(">集成型企业</tspan>", updated)
        self.assertIn('y="221.63"', updated)
        self.assertIn('y="239.63"', updated)
        self.assertIn(">运维与技术</tspan>", updated)
        self.assertIn(">服务类</tspan>", updated)
        self.assertIn(">企业类型</tspan>", updated)
        self.assertIn(">分类</tspan>", updated)
        self.assertEqual(
            [decision.rendered_text for decision in decisions],
            ["平台型和\n集成型企业", "运维与技术\n服务类", "企业类型\n分类"],
        )

    def test_bottom_conclusion_bar_uses_t8_upper_scale(self) -> None:
        svg = """<svg>
<text x="183.05" y="631.08" text-anchor="start" font-size="14.67" font-weight="700" fill="#FFFFFF">"多角色多场景特征决定评价体系必须分角色、分场景设计，不能用统一标准衡量所有企业"</text>
</svg>"""

        updated, decisions = apply_typography_to_svg_text(svg)

        self.assertIn('font-size="16.00"', updated)
        self.assertEqual(decisions[0].role, "T8")
        self.assertEqual(decisions[0].applied_px, 16.0)

    def test_aligns_industry_feature_row_labels_to_one_baseline(self) -> None:
        svg = """<svg>
<text x="90.07" y="517.90" text-anchor="middle" font-size="16" font-weight="700" fill="#FFFFFF">行业特性</text>
<text x="262.70" y="525.52" text-anchor="middle" font-size="16" font-weight="700" fill="#0B1F3D">系统性</text>
<text x="470.86" y="523.98" text-anchor="middle" font-size="16" font-weight="700" fill="#0B1F3D">长周期属性</text>
<text x="921.15" y="525.84" text-anchor="middle" font-size="16" font-weight="700" fill="#0B1F3D">供应链联动属性</text>
</svg>"""

        updated, decisions = apply_typography_to_svg_text(svg)

        self.assertEqual(updated.count('y="520.00"'), 4)
        self.assertTrue(all(decision.y == 520.0 for decision in decisions))

    def test_custom_rules_can_override_alignment_without_code_change(self) -> None:
        svg = """<svg>
<text x="262.70" y="525.52" text-anchor="middle" font-size="16" font-weight="700" fill="#0B1F3D">系统性</text>
</svg>"""
        rules = {
            "alignment_rules": [
                {
                    "match": {"text_equals_any": ["系统性"]},
                    "set": {"y": "518.00", "text-anchor": "middle"},
                }
            ]
        }

        updated, decisions = apply_typography_to_svg_text(svg, rules=rules)

        self.assertIn('y="518.00"', updated)
        self.assertEqual(decisions[0].y, 518.0)


if __name__ == "__main__":
    unittest.main()
