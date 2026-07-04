from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.body_blueprint_prompt import (
    compile_body_blueprint_prompts,
    load_style,
)
from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks


class BodyBlueprintPromptTests(unittest.TestCase):
    def test_style_is_selected_by_preset(self) -> None:
        green = load_style(preset="gray_green")
        blue = load_style(preset="ivory_deep_blue")

        self.assertEqual(green["accent"], "#1F5B4D")
        self.assertEqual(blue["accent"], "#12355B")

    def test_compiles_body_region_prompt_without_enterprise_chrome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.md"
            script.write_text(
                """## 第4页：测试页
组件A（左侧主图）——六边形分类图：
投资运营类、规划设计与咨询类
组件D（底部结论条）——SO WHAT：
"不能用统一标准衡量所有企业"
""",
                encoding="utf-8",
            )
            blocks = parse_page_blocks(script)
            output = compile_body_blueprint_prompts(script, [4], load_style(preset="ivory_deep_blue"))

        self.assertIn("象牙白 + 深蓝强调", output)
        self.assertIn("只生成正文内容区画面", output)
        self.assertIn("不要生成标题、副标题、蓝线、Logo、页脚、页码", output)
        self.assertIn("六边形分类图", output)
        self.assertNotIn("墨绿通栏", output)
        self.assertNotIn("墨绿结论条", output)
        self.assertEqual(sorted(blocks), [4])


if __name__ == "__main__":
    unittest.main()
