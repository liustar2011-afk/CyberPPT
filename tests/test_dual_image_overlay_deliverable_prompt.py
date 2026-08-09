from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dual_image_overlay.deliverable_prompt import (
    PageBlock,
    compile_page_blocks,
    compile_pages,
    fit_template_title,
    layout_density_directives,
    parse_content_locks,
    parse_page_blocks,
    render_prompt,
    template_title,
    visible_deliverable_lines,
)
from scripts.dual_image_overlay.style_library import (
    resolve_default_style,
    write_project_style_lock,
)


ROOT = Path(__file__).resolve().parents[1]


class DualImageOverlayDeliverablePromptTests(unittest.TestCase):
    def test_style_four_does_not_prescribe_page_structures(self) -> None:
        forbidden = (
            "正式内部汇报结构",
            "正式内部汇报风格",
            "紧凑矩阵",
            "右侧栏",
            "编号 chips",
            "流程轴",
            "SO WHAT",
        )
        style = resolve_default_style(style_id=4)
        registry_text = json.dumps(style, ensure_ascii=False)
        standalone_preset_text = (
            ROOT
            / "scripts"
            / "dual_image_overlay"
            / "style_presets"
            / "ivory_deep_blue.json"
        ).read_text(encoding="utf-8")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script-final.md"
            script.write_text(
                "## 第1页：测试\n- 上屏文字：\n\n  **按语义构图**\n",
                encoding="utf-8",
            )
            lock = write_project_style_lock(
                project=root / "project",
                style_id=4,
                source_script=script,
            )
            lock_text = lock.read_text(encoding="utf-8")
            prompt = compile_pages(script, [1], style_lock_path=lock)

        for phrase in forbidden:
            self.assertNotIn(phrase, registry_text)
            self.assertNotIn(phrase, standalone_preset_text)
            self.assertNotIn(phrase, lock_text)
            self.assertNotIn(phrase, prompt)
        self.assertIn("象牙白", prompt)
        self.assertIn("#F7F6F0", prompt)
        self.assertIn("#12355B", prompt)

    def test_style_nine_safety_rules_are_injected_into_imagegen_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            style = write_project_style_lock(project=root / "project", style_id=9)
            script.write_text("## 第1页：测试\n组件A：业务内容\n", encoding="utf-8")

            prompt = compile_pages(script, [1], style_lock_path=style)

        self.assertIn("默认不出现人物；禁止正脸、围桌会议、多人讨论及摆拍办公场景。", prompt)
        self.assertIn("organization names, logos, seals, signage", prompt)
        self.assertIn("editable text layer only", prompt)
        self.assertIn("non-evidentiary", prompt)
        self.assertIn("locked on-screen text faithfully in the main composition", prompt)
        self.assertIn("may use a small amount of clear Chinese labels", prompt)
        self.assertIn("dense pseudo-Chinese", prompt)
        self.assertIn("禁止宽箭头带", prompt)
        self.assertIn("虚线只表达反馈或弱关系", prompt)
        self.assertEqual(1, prompt.count("端点准确落在对象边界"))

    def test_compile_pages_uses_only_onscreen_block_from_final_manuscript(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script-final.md"
            style = write_project_style_lock(project=root / "project", style_id=4)
            script.write_text(
                "## 第1页：测试\n- 页面类型：内容页\n- 完整文字稿：不可送图\n- 上屏文字：\n\n  **可画模块**\n\n  - 可画要点\n\n- 证据：S001\n- 边界：不可送图\n【演讲者备注】\n不可送图\n",
                encoding="utf-8",
            )
            prompt = compile_pages(script, [1], style_lock_path=style)
        self.assertIn("可画模块", prompt)
        self.assertIn("可画要点", prompt)
        self.assertIn("【页面编码】P01｜测试", prompt)
        self.assertNotIn("完整文字稿", prompt)
        self.assertNotIn("不可送图", prompt)
    def test_compile_removes_authoring_row_markers_from_visible_copy(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script-final.md"
            style = write_project_style_lock(project=root / "project", style_id=4)
            script.write_text(
                "## P19 服务交付与服务等级\n"
                "严格上屏文字\n"
                "    第1行｜访问与成果交付方式\n"
                "        API/网关调用：通过API取得结果。\n"
                "    第X行｜部署运行环境\n",
                encoding="utf-8",
            )
            prompt = compile_pages(script, [19], style_lock_path=style)

        self.assertIn("访问与成果交付方式", prompt)
        self.assertIn("部署运行环境", prompt)
        self.assertNotRegex(prompt, r"第\s*(?:\d+|[Xx])\s*行\s*[｜|:]")

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

        self.assertIn("只生成正文内容区成稿图", prompt)
        self.assertIn("2048×1024", prompt)
        self.assertIn("No evidence IDs, watermarks, debug marks, or placeholders.", prompt)
        self.assertNotIn("不得出现证据编号", prompt)
        self.assertIn("【内容锁定】", prompt)
        self.assertNotIn("## 第2页：", prompt)
        self.assertNotIn("\n标题：", prompt)
        self.assertNotIn("\n副标题：", prompt)
        self.assertIn("【构图指令】", prompt)
        self.assertNotIn("【设计目标与叙事】", prompt)
        self.assertNotIn("请先理解", prompt)
        self.assertNotIn("页面使命", prompt)
        self.assertNotIn("母版", prompt)
        self.assertNotIn("可编辑文字层", prompt)
        self.assertIn("【结构密度】", prompt)
        self.assertIn("七点结论清单", prompt)
        self.assertIn("底部墨绿通栏", prompt)
        self.assertNotIn("不使用外部风格 preset", prompt)
        self.assertNotIn("风格只约束视觉表达", prompt)
        self.assertNotIn("确认样张", prompt)
        self.assertNotIn("密度：不改变【内容锁定】结构/组件/箭头/文字清单", prompt)
        self.assertNotIn("页面角色", prompt)
        self.assertIn("近义替换", prompt)
        self.assertIn("忠实于【内容锁定】", prompt)
        self.assertNotIn("可被后续 PPT 文本层覆盖", prompt)
        self.assertNotIn("适合作为可字背景保留", prompt)
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
                "组件A（左上或上方并排，两个背景数字卡片）",
                "组件B（主图，占主要版面）——三段式横向流程图",
                "组件C（底部墨绿结论条）——SO WHAT",
            ],
        )

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

        self.assertNotIn("## 第4页：", prompt)
        self.assertIn("中心定位框", prompt)
        self.assertIn("左右两侧信息通过短箭头指向中心定位框", prompt)
        self.assertIn("中心定位框1个", prompt)
        self.assertNotIn("风格只约束色彩、材质、线条、图标克制度和视觉语气", prompt)
        self.assertNotIn("密度：不改变【内容锁定】结构/组件/箭头/文字清单", prompt)
        self.assertNotIn("确认样张", prompt)
        self.assertNotIn("不使用外部风格 preset", prompt)
        self.assertNotIn("【设计目标与叙事】", prompt)
        self.assertNotIn("页面角色", prompt)
        self.assertIn("浅灰白 + 墨绿", prompt)
        self.assertIn("忠实于【内容锁定】", prompt)
        self.assertNotIn("E05", prompt)
        self.assertNotIn("【用途】", prompt)
        self.assertNotIn("目标语言", prompt)

    def test_render_prompt_omits_core_judgment_and_boundary(self) -> None:
        with TemporaryDirectory() as directory:
            style_lock = write_project_style_lock(project=Path(directory) / "project", style_id=9)
            prompt = render_prompt(
                PageBlock(
                    page_number=5,
                    title="研判变化",
                    text=(
                        "核心判断：供需分析已扩展到综合判断\n"
                        "上屏文字\n"
                        "**关键变化**\n"
                        "- 全社会用电量增长。\n"
                        "Boundary (do not show on slide): 三项数字保留2025年、全国口径"
                    ),
                ),
                style_lock_path=style_lock,
            )

        self.assertNotIn("核心判断：供需分析已扩展到综合判断", prompt)
        self.assertNotIn("供需分析已扩展到综合判断", prompt)
        self.assertNotIn("禁止项", prompt)
        self.assertNotIn("Boundary (do not show on slide)", prompt)
        self.assertNotIn("三项数字保留2025年、全国口径", prompt)
        self.assertNotIn("Boundary text must not appear on the slide", prompt)
        self.assertIn("上屏文字", prompt)
        self.assertIn("关键变化", prompt)
        self.assertIn("不要生成页面标题、副标题、Logo、页脚", prompt)
        self.assertIn("No evidence IDs, watermarks, debug marks, or placeholders.", prompt)
        self.assertNotIn("不得出现证据编号", prompt)


if __name__ == "__main__":
    unittest.main()
