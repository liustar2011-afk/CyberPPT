from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dual_image_overlay.deliverable_prompt import (
    compile_page_blocks,
    compile_pages,
    fit_template_title,
    layout_density_directives,
    parse_content_locks,
    parse_page_blocks,
    template_title,
    visible_deliverable_lines,
)
from scripts.dual_image_overlay.style_library import write_project_style_lock


ROOT = Path(__file__).resolve().parents[1]


class DualImageOverlayDeliverablePromptTests(unittest.TestCase):
    def test_parse_supports_p_style_and_chinese_page_headings(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text(
                "## P2 核心结论\n正文A\n\n## 第3页：环境变化\n正文B\n",
                encoding="utf-8",
            )

            pages = parse_page_blocks(script)

        self.assertEqual(sorted(pages), [2, 3])
        self.assertEqual("核心结论", pages[2].title)
        self.assertEqual("环境变化", pages[3].title)

    def test_compile_removes_evidence_caveats_and_placeholder_language(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            style = root / "stage2_visual_lock.md"
            script.write_text(
                """## P2 核心结论
```
标题占位条（顶部通栏，纯色墨绿底，条内不绘制任何文字）。本页结论标题（仅供参考、核对内容用，不要求作为图内文字渲染）："建议由中电联牵头"
组件A（结论标题下方）——总体判断框，标签"(E106)"：
"电力产业链企业出海能力证明体系建设已具备推进必要性"
小字caveat（紧贴此框）："注：现有材料以方法论与框架设计为主"
组件B（主体）——七点结论清单，右下角小标签"(E107)"：
1. 补齐企业能力可信表达短板
2. 坚持分角色、分场景、分维度、重证据
组件C（底部墨绿通栏）——SO WHAT行动提示：
"建议按'规则先行—试点验证—常态运营—规模推广'路径启动首阶段工作"
```
""",
                encoding="utf-8",
            )
            style.write_text("背景 `#F2F3EF`，强调 `#1F5B4D`，正文 `#333333`。", encoding="utf-8")

            prompt = compile_pages(script, [2], style_lock_path=style)

        self.assertIn("正式内部汇报", prompt)
        self.assertIn("【内容锁定】", prompt)
        self.assertIn("## 第2页：建议由中电联牵头", prompt)
        self.assertNotIn("\n标题：", prompt)
        self.assertNotIn("\n副标题：", prompt)
        self.assertIn("【构图指令】", prompt)
        self.assertIn("【结构密度】", prompt)
        self.assertIn("七点结论清单", prompt)
        self.assertIn("底部墨绿通栏", prompt)
        self.assertNotIn("组件A", prompt)
        self.assertNotIn("组件B", prompt)
        self.assertNotIn("组件C", prompt)
        self.assertIn("视觉锁定：核心色板", prompt)
        self.assertIn("完整保留本页内容", prompt)
        self.assertIn("页面类型不得改作通用内容页", prompt)
        self.assertNotIn("可被后续 PPT 文本层覆盖", prompt)
        self.assertNotIn("适合作为无字背景保留", prompt)
        self.assertIn("#F2F3EF", prompt)
        self.assertIn("电力产业链企业出海能力证明体系建设已具备推进必要性", prompt)
        self.assertIn("补齐企业能力可信表达短板", prompt)
        self.assertNotIn("(E106)", prompt)
        self.assertNotIn("(E107)", prompt)
        self.assertNotIn("小字caveat", prompt)
        self.assertNotIn("现有材料以方法论", prompt)
        self.assertNotIn("标题占位条（顶部通栏", prompt)
        self.assertNotIn("仅供参考", prompt)
        self.assertNotIn("[通用风格前缀]", prompt)

    def test_style_contract_excludes_style_scenarios_and_sample_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            script.write_text("## 第1页：封面\n页面类型：封面\n组件A：\n测试\n", encoding="utf-8")
            style_lock = write_project_style_lock(project=root, style_id=4)

            prompt = compile_pages(script, [1], style_lock_path=style_lock)

        self.assertIn("背景#F7F6F0", prompt)
        self.assertIn("正式内部汇报语气", prompt)
        self.assertNotIn("科技、SaaS", prompt)
        self.assertNotIn("palette-04.png", prompt)
        self.assertNotIn("SO WHAT", prompt)

    def test_layout_density_directives_keep_component_structure_without_evidence_labels(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text(
                """## 第3页：环境变化
组件A（左上或上方并排，两个背景数字卡片）：
卡片1，标签"(E001)"："2025年全球能源投资总额 3.3万亿美元"
组件B（主图，占主要版面）——三段式横向流程图，标签"(E008-E013)"：
小字caveat（紧贴流程图）："注：过程说明"
组件C（底部墨绿结论条）——SO WHAT：
""",
                encoding="utf-8",
            )
            page = parse_page_blocks(script)[3]

            directives = layout_density_directives(page)

        self.assertEqual(
            directives,
            [
                "左上或上方并排，两个背景数字卡片",
                "主图，占主要版面，三段式横向流程图",
                "底部墨绿结论条，SO WHAT",
            ],
        )

    def test_page_type_is_a_non_visible_composition_instruction(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text(
                "## 第3页：建设背景与基础\n页面类型：章节过渡页\n组件A（正文区中部，主标题）——\n建设背景与基础\n01\n",
                encoding="utf-8",
            )
            style = Path(directory) / "style.json"
            style.write_text('{"style": {"prompt_contract": "正式"}}', encoding="utf-8")

            prompt = compile_pages(script, [3], style_lock_path=style)

        self.assertIn("【页面类型】", prompt)
        self.assertIn("本页类型：章节过渡页。此信息只用于构图，不得作为页面可见文字。", prompt)
        self.assertEqual(1, prompt.count("章节过渡页"))

    def test_template_title_extracts_conclusion_title_for_template_layer(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text(
                """## 第3页：环境变化
标题占位条（顶部通栏）。本页结论标题（仅供参考、核对内容用，不要求作为图内文字渲染）："海外市场从单点机会转向体系化能力竞争"
组件A：正文内容
""",
                encoding="utf-8",
            )
            page = parse_page_blocks(script)[3]

            title = template_title(page)
            lines = visible_deliverable_lines(page)

        self.assertEqual(title, "海外市场从单点机会转向体系化能力竞争")
        self.assertEqual(lines, ["正文内容"])

    def test_fit_template_title_keeps_header_away_from_brand_logo(self) -> None:
        title = (
            "建议由中电联牵头，用'六位一体'体系和四阶段试点，"
            "把电力产业链企业出海能力证明从'自证'转向'可信证据'"
        )

        fitted = fit_template_title(title)

        self.assertEqual(fitted, "建议由中电联牵头，建设出海能力可信证明体系")
        self.assertLessEqual(len(fitted), 42)

    def test_visible_lines_keep_business_content_but_drop_process_markers(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text(
                """## 第2页：核心结论
组件A——总体判断框，标签"(E106)"：
"总体判断"
注：过程说明
组件B——清单：
1. 业务内容
""",
                encoding="utf-8",
            )
            page = parse_page_blocks(script)[2]

            lines = visible_deliverable_lines(page)

        self.assertEqual(lines, ['"总体判断"', "1. 业务内容"])

    def test_cli_writes_manifest_policy(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            out = root / "out.md"
            manifest = root / "manifest.json"
            style_lock = write_project_style_lock(project=root / "project", style_id=4, source_script=script)
            script.write_text("## P2 核心结论\n组件A：最终内容\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/deliverable_prompt.py"),
                    "--script",
                    str(script),
                    "--pages",
                    "2",
                    "--style-lock",
                    str(style_lock),
                    "--out",
                    str(out),
                    "--manifest",
                    str(manifest),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertTrue(payload["policy"]["final_deliverable_only"])
        self.assertTrue(payload["policy"]["forbid_external_style_preset"])
        self.assertTrue(payload["policy"]["forbid_evidence_ids"])

    def test_compile_requires_style_lock(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text("## P2 核心结论\n组件A：最终内容\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing visual style lock"):
                compile_pages(script, [2])

    def test_compile_from_content_locks_uses_clean_truth(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            locks = root / "locks"
            locks.mkdir()
            style_lock = write_project_style_lock(project=root / "project", style_id=5)
            (locks / "slide-04-content-lock.json").write_text(
                json.dumps(
                    {
                        "slide": 4,
                        "title": "统一入口、统一证据、统一评价和统一结果应用体系",
                        "subtitle": "建设定位页",
                        "content_sections": [
                            {
                                "heading": "中心定位框",
                                "text": "面向海外电力产业链企业发展能力评价场景\n以电力领域数据基础设施为底座",
                            },
                            {
                                "heading": "右侧｜建设任务",
                                "text": "1. 建设企业海外发展评价数据底座\n2. 建设企业发展能力评价指标模型",
                            },
                        ],
                        "annotations": ["左右两侧信息通过短箭头指向中心定位框。"],
                        "required_components": ["中心定位框1个", "左侧信息框3个"],
                        "evidence_ids": ["E05"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            blocks = parse_content_locks(locks)
            prompt = compile_page_blocks(blocks, [4], style_lock_path=style_lock)

        self.assertIn("## 第4页：统一入口、统一证据、统一评价和统一结果应用体系", prompt)
        self.assertIn("中心定位框", prompt)
        self.assertIn("左右两侧信息通过短箭头指向中心定位框", prompt)
        self.assertIn("中心定位框1个", prompt)
        self.assertIn("采用正式内部汇报语气、清晰层级、克制图形和紧凑信息密度", prompt)
        self.assertIn("版式必须服从本页内容锁定和构图要求", prompt)
        self.assertNotIn("E05", prompt)
        self.assertNotIn("【用途】", prompt)
        self.assertNotIn("目标语言", prompt)


if __name__ == "__main__":
    unittest.main()
