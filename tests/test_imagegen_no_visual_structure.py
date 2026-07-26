"""Compiled ImageGen / deliverable prompts must not inject 视觉结构 or thesis fields."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.dual_image_overlay.deliverable_prompt import PageBlock, render_prompt
from scripts.dual_image_overlay.imagegen_handoff import (
    _page_visual_intent_overrides,
    build_page_prompt,
    build_page_visual_intent,
    content_lock_text,
)
from scripts.dual_image_overlay.style_library import write_project_style_lock


SCRIPT_WITH_VISUAL_STRUCTURE = """## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 完整文字稿：建设方向初步定位为面向行业的公共能力。
- 文字稿取舍说明：不展开细节。
- 证据映射：公共能力定位→S015
- 上屏文字：

  初步定位为面向行业的公共能力。

  **行业公共能力**

  - 服务行业研判。

- 证据：S015
- 边界：正式范围待后续确定。
- 视觉结构：判断证据支撑——中央公共能力定位，两侧职责边界托举。
- 讲解提示：先说定位再说边界。
"""


def _visual_intent_page(
    main_message: str,
    mission: str,
    modules: str,
):
    page = parse_script_markdown(
        f"""## 第19页：测试页

- 页面类型：内容页
- 页面标题：测试页
- 主判断：{main_message}
- 上屏文字：

{modules}
"""
    ).pages[0]
    return page, mission


class ImageGenNoVisualStructureTests(unittest.TestCase):
    def test_visual_intent_classifies_decision_and_admission(self) -> None:
        page, mission = _visual_intent_page(
            "首期场景由成熟度条件共同决定",
            "首期场景如何选定、后续场景如何分期推进",
            """  **筛选依据｜五维共同决定**
  - 按成熟度选择。
  **首期取舍｜双场景**
  - 首期进入。
  **后续准入｜条件成熟再纳入**
  - 后续验证。""",
        )
        intent = build_page_visual_intent(page, mission)
        self.assertIn("[Prompt context] Page-specific visual intent", intent)
        self.assertIn("readiness gates", intent)
        self.assertIn("decision structure, not an implementation process", intent)
        self.assertIn("Five equal-weight criterion cards", intent)

    def test_visual_intent_classifies_causal_closed_loop_and_phase(self) -> None:
        cases = [
            ("为什么现有研判不足", "问题、原因与影响共同形成能力需求", "cause-and-effect"),
            ("业务如何形成闭环", "输入、处理、输出、反馈与复盘", "closed-loop"),
            ("能力如何分期推进", "当前、近期和中长期分阶段建设", "stage progression"),
        ]
        for mission, message, marker in cases:
            page, _ = _visual_intent_page(
                message,
                mission,
                "  **支撑模块**\n  - 支撑内容。",
            )
            self.assertIn(marker, build_page_visual_intent(page, mission))

    def test_visual_intent_uses_safe_fallback_and_partial_override(self) -> None:
        page, mission = _visual_intent_page(
            "形成稳定的行业公共能力",
            "拟建设什么能力",
            "  **能力基础**\n  - 形成支撑。",
        )
        intent = build_page_visual_intent(
            page,
            mission,
            {"recommended_composition": "Use one evidence-led editorial composition."},
        )
        self.assertIn("judgment supported by evidence", intent)
        self.assertIn("Use one evidence-led editorial composition.", intent)
        self.assertIn("Avoid on this page:", intent)

    def test_page_prompt_places_visual_intent_after_onscreen_before_style(self) -> None:
        page = parse_script_markdown(SCRIPT_WITH_VISUAL_STRUCTURE).pages[0]
        with TemporaryDirectory() as directory:
            lock = write_project_style_lock(project=Path(directory), style_id=9)
            prompt = build_page_prompt(
                page,
                lock,
                page_mission="首期场景如何选择",
                visual_intent_override={
                    "visual_thesis": "Explain the approved page-specific decision."
                },
            )
        self.assertLess(prompt.index("上屏文字"), prompt.index("Page-specific visual intent"))
        self.assertLess(
            prompt.index("Page-specific visual intent"),
            prompt.index("Industry scene and imagery:"),
        )
        self.assertIn("Explain the approved page-specific decision.", prompt)
        self.assertIn("do not render field names or instruction text", prompt)

    def test_page_visual_intent_override_loader_ignores_invalid_values(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            outline = project / "workbench/stages/01-analysis/outline.json"
            outline.parent.mkdir(parents=True)
            outline.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "page_id": "p19",
                                "visual_intent": {
                                    "visual_thesis": "  Approved thesis.  ",
                                    "decision_relationship": "",
                                    "unknown_field": "ignored",
                                },
                            },
                            {"page_id": "p20", "visual_intent": "invalid"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            overrides = _page_visual_intent_overrides(project)
        self.assertEqual(
            {"p19": {"visual_thesis": "Approved thesis."}},
            overrides,
        )

    def test_content_lock_omits_visual_structure_even_when_parsed(self) -> None:
        page = parse_script_markdown(SCRIPT_WITH_VISUAL_STRUCTURE).pages[0]
        self.assertTrue(page.visual_structure.strip())
        self.assertTrue(page.boundary.strip())
        lock = content_lock_text(page, page_mission="拟建什么性质的能力")
        self.assertNotIn("视觉结构", lock)
        self.assertNotIn("视觉结构：", lock)
        self.assertNotIn("页面角色", lock)
        self.assertNotIn("不写边界旁白", lock)
        self.assertNotIn("不要写成正文模块标题", lock)
        self.assertIn("页面使命", lock)
        self.assertIn("拟建什么性质的能力", lock)
        self.assertIn("核心判断", lock)
        self.assertNotIn("禁止项", lock)
        self.assertNotIn("Boundary (do not show on slide)", lock)
        self.assertNotIn("正式范围待后续确定", lock)
        self.assertIn("上屏文字", lock)
        self.assertIn("行业公共能力", lock)
        self.assertIn("初步定位为面向行业的公共能力", lock)

    def test_build_page_prompt_omits_visual_structure(self) -> None:
        page = parse_script_markdown(SCRIPT_WITH_VISUAL_STRUCTURE).pages[0]
        with TemporaryDirectory() as directory:
            lock = write_project_style_lock(project=Path(directory), style_id=4)
            prompt = build_page_prompt(
                page,
                lock,
                page_mission="拟建什么性质的能力",
            )
        self.assertNotIn("视觉结构：", prompt)
        self.assertNotIn("视觉结构", prompt)
        self.assertNotIn("【设计目标与叙事】", prompt)
        self.assertNotIn("不使用外部风格 preset", prompt)
        self.assertNotIn("确认样张", prompt)
        self.assertNotIn("页面角色", prompt)
        self.assertNotIn("## 第9页：", prompt)
        self.assertIn("象牙白 + 深蓝强调", prompt)
        self.assertIn("页面使命", prompt)
        self.assertIn("拟建什么性质的能力", prompt)
        self.assertIn("核心判断", prompt)
        self.assertNotIn("禁止项", prompt)
        self.assertNotIn("Boundary (do not show on slide)", prompt)
        self.assertNotIn("正式范围待后续确定", prompt)
        self.assertNotIn("Boundary text must not appear on the slide", prompt)
        self.assertIn("上屏文字", prompt)
        self.assertIn(
            "Do not invent section labels like meta headers; only render 上屏文字 modules.",
            prompt,
        )
        self.assertIn("不要生成页面标题、副标题、Logo、页脚", prompt)
        self.assertIn("No evidence IDs, watermarks, debug marks, or placeholders.", prompt)
        self.assertNotIn("不得出现证据编号", prompt)

    def test_render_prompt_template_omits_visual_structure(self) -> None:
        with TemporaryDirectory() as directory:
            lock = write_project_style_lock(project=Path(directory), style_id=4)
            prompt = render_prompt(
                PageBlock(
                    page_number=9,
                    title="总体定位",
                    text=(
                        "页面角色：内容页\n"
                        "核心判断：测试判断\n"
                        "上屏文字：要点\n"
                        "Boundary (do not show on slide): 不要画成页脚"
                    ),
                ),
                style_lock_path=lock,
            )
        self.assertNotIn("视觉结构：", prompt)
        self.assertNotIn("视觉结构", prompt)
        self.assertNotIn("【设计目标与叙事】", prompt)
        self.assertNotIn("不使用外部风格 preset", prompt)
        self.assertNotIn("确认样张", prompt)
        self.assertNotIn("密度：不改变【内容锁定】", prompt)
        self.assertNotIn("页面角色", prompt)
        self.assertNotIn("## 第9页：", prompt)
        self.assertIn("【内容锁定】", prompt)
        self.assertNotIn("核心判断", prompt)
        self.assertNotIn("测试判断", prompt)
        self.assertIn("上屏文字", prompt)
        self.assertIn("要点", prompt)
        self.assertIn("忠实于【内容锁定】", prompt)
        self.assertNotIn("请先理解", prompt)
        self.assertNotIn("页面使命", prompt)
        self.assertNotIn("禁止项", prompt)
        self.assertNotIn("Boundary (do not show on slide)", prompt)
        self.assertNotIn("不要画成页脚", prompt)
        self.assertNotIn("Boundary text must not appear on the slide", prompt)
        self.assertIn(
            "Do not invent section labels like meta headers; only render 上屏文字 modules.",
            prompt,
        )

    def test_render_prompt_drops_legacy_禁止项_header(self) -> None:
        with TemporaryDirectory() as directory:
            lock = write_project_style_lock(project=Path(directory), style_id=4)
            prompt = render_prompt(
                PageBlock(
                    page_number=9,
                    title="总体定位",
                    text="上屏文字：要点\n禁止项\n不要画成页脚",
                ),
                style_lock_path=lock,
            )
        self.assertNotIn("禁止项", prompt)
        self.assertNotIn("Boundary (do not show on slide)", prompt)
        self.assertNotIn("不要画成页脚", prompt)
        self.assertIn("上屏文字", prompt)
        self.assertIn("要点", prompt)


if __name__ == "__main__":
    unittest.main()
