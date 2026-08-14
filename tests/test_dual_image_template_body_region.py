from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw


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
    def test_existing_template_project_is_preserved_without_overwrite(self) -> None:
        module = load_template_image_ppt_export()
        manifest = {
            "canvas": {"width": 1280, "height": 720},
            "body_region": {"x": 33, "y": 89, "width": 1214, "height": 607},
            "tasks": [
                {
                    "page_number": 1,
                    "title": "封面",
                    "slide_title": "电力数据服务",
                    "body_text": "- 主标题：电力数据服务",
                    "page_role": "cover",
                    "render_mode": "brand-template",
                    "template": "cover",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            project = module.write_project(manifest, output_dir, "deck")
            marker = project / "user-marker.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                module.write_project(manifest, output_dir, "deck")
            self.assertEqual("keep", marker.read_text(encoding="utf-8"))

            replacement = module.write_project(manifest, output_dir, "deck", overwrite=True)
            backups = list((output_dir / "backup").rglob("user-marker.txt"))
            self.assertTrue(replacement.is_dir())
            self.assertEqual(1, len(backups))
            self.assertEqual("keep", backups[0].read_text(encoding="utf-8"))

    def test_export_consumes_explicit_output_and_writes_pointer(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "svg_output").mkdir(parents=True)
            output = project.parent / "delivery" / "deck.pptx"

            def fake_run(command, check=False):
                if "--output" in command:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"pptx")
                return type("Completed", (), {"returncode": 0})()

            with patch.object(module.subprocess, "run", side_effect=fake_run):
                result = module.run_export(project, output_path=output)
                module.run_export(project, output_path=output, overwrite=True)

            pointer = json.loads((project / "analysis" / "export_artifact.json").read_text(encoding="utf-8"))
            output_backups = list((project.parent / "backup").rglob("deck.pptx"))

        self.assertEqual(output.resolve(), result)
        self.assertEqual(str(output.resolve()), pointer["path"])
        self.assertEqual("cyberppt.dual_image.export_artifact.v1", pointer["schema"])
        self.assertEqual(1, len(output_backups))

    def test_generation_helper_is_wired(self) -> None:
        module = load_template_image_ppt_export()

        self.assertTrue(callable(module.run_codex_image))

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

    def test_content_page_svg_has_no_body_mask(self) -> None:
        module = load_template_image_ppt_export()

        svg = module.render_content_page_svg(
            {
                "slide_title": "知识资产基础",
                "subtitle": "30个学科、30万道题目、40年数据，夯实智能应用底座",
            },
            target_image=Path("page_004_知识资产基础_full.png"),
            header={"x": 58, "y": 16},
            body={"x": 33, "y": 89, "width": 1214, "height": 607},
        )

        self.assertNotIn("<rect", svg)
        self.assertNotIn("#F7F6F0", svg)
        self.assertIn("<image", svg)

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

    def test_extract_content_reads_title_and_subtitle_from_final_script_fields(self) -> None:
        module = load_template_image_ppt_export()
        block = module.PageBlock(
            4,
            "知识资产基础",
            (
                "- 页面类型：内容页\n"
                "- 页面标题：知识资产基础\n"
                "- 副标题：30个学科、30万道题目、40年数据，夯实智能应用底座\n"
                "- 主判断：三类知识资产构成平台智能化应用基础\n"
                "- 上屏文字：\n"
                "  **01｜30个电力学科**\n"
            ),
        )

        content = module.extract_content(block)

        self.assertEqual("知识资产基础", content.title)
        self.assertEqual(
            "30个学科、30万道题目、40年数据，夯实智能应用底座",
            content.subtitle,
        )

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

    def test_normalize_generated_image_size_rejects_portrait_output(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "portrait.png"
            Image.new("RGB", (1024, 1536), "#f7f6f0").save(image_path)

            with self.assertRaisesRegex(ValueError, "portrait|aspect"):
                module.normalize_generated_image_size(image_path, "1680x944")

    def test_normalize_generated_image_size_contains_close_landscape_without_distortion(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "landscape.png"
            Image.new("RGB", (1672, 941), "#12355b").save(image_path)

            normalized = module.normalize_generated_image_size(image_path, "1680x944")

            self.assertEqual((1680, 944), normalized)
            with Image.open(image_path) as image:
                self.assertEqual((1680, 944), image.size)

    def test_generated_content_fill_rejects_centered_small_page(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "centered.png"
            image = Image.new("RGB", (2480, 1184), "#ffffff")
            ImageDraw.Draw(image).rectangle((360, 60, 2120, 1120), fill=(20, 60, 100))
            image.save(image_path)

            with self.assertRaisesRegex(ValueError, "internal horizontal whitespace"):
                module.assert_generated_content_fill(image_path)

    def test_generated_content_fill_accepts_full_width_body_layout(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "full.png"
            image = Image.new("RGB", (2480, 1184), "#ffffff")
            ImageDraw.Draw(image).rectangle((120, 60, 2360, 1120), fill=(20, 60, 100))
            image.save(image_path)

            report = module.assert_generated_content_fill(image_path)

            self.assertGreaterEqual(report["content_width_ratio"], 0.90)
            self.assertLessEqual(report["left_margin_ratio"], 0.06)
            self.assertLessEqual(report["right_margin_ratio"], 0.06)

    def test_content_prompt_demands_full_width_body_canvas(self) -> None:
        module = load_template_image_ppt_export()
        page = module.PageBlock(4, "测试页", "## 第4页：测试页\n【内容锁定】\n内容")
        content = module.PageContent(title="测试页", subtitle="", body="内容")

        prompt = module.content_prompt(
            page,
            content,
            {"x": 20, "y": 104, "width": 1240, "height": 592},
            {"width": 2480, "height": 1184},
            "body",
        )

        self.assertIn("有效内容整体宽度不少于画布宽度 90%", prompt)
        self.assertIn("不要把内容缩成居中的", prompt)

    def test_image_prompt_rejects_evidence_chain_text(self) -> None:
        module = load_template_image_ppt_export()

        with self.assertRaisesRegex(ValueError, "non-visual provenance"):
            module.validate_image_prompt_text(4, "请绘制供需形势，相关判断重点对应E01。")

    def test_non_visible_evidence_sections_do_not_enter_content_prompt(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.md"
            script.write_text(
                "\n".join(
                    [
                        "## 第4页：工作背景",
                        "【内容锁定】",
                        "- 全国全社会用电量103682亿千瓦时",
                        "### 非上屏：证据链",
                        "- E01、E02",
                    ]
                ),
                encoding="utf-8",
            )
            pages = module.parse_page_blocks(script)

            manifest = module.build_manifest(script, [4], pages, Path(tmp))

        prompt = manifest["tasks"][0]["prompt"]
        self.assertIn("全国全社会用电量103682亿千瓦时", prompt)
        self.assertNotIn("证据链", prompt)
        self.assertNotIn("E01", prompt)

    def test_agenda_and_section_pages_use_brand_templates_not_images(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.md"
            script.write_text(
                "\n".join(
                    [
                        "## 第1页：封面",
                        "【内容锁定】",
                        "标题：测试汇报",
                        "## 第2页：目录",
                        "【内容锁定】",
                        "目录",
                        "## 第3页：第一章 建设背景与基础",
                        "【内容锁定】",
                        "第一章",
                        "建设背景与基础",
                        "## 第4页：内容页",
                        "【内容锁定】",
                        "正文内容",
                        "## 第5页：封底",
                        "【内容锁定】",
                        "感谢聆听",
                    ]
                ),
                encoding="utf-8",
            )
            pages = module.parse_page_blocks(script)

            manifest = module.build_manifest(script, [1, 2, 3, 4, 5], pages, Path(tmp))

        tasks = {task["page_number"]: task for task in manifest["tasks"]}
        self.assertEqual("cover", tasks[1]["template"])
        self.assertEqual("agenda", tasks[2]["template"])
        self.assertEqual("section", tasks[3]["template"])
        self.assertEqual("content-image", tasks[4]["render_mode"])
        self.assertEqual("ending", tasks[5]["template"])
        self.assertNotIn("image_path", tasks[2])
        self.assertNotIn("image_path", tasks[3])
        self.assertNotIn("prompt", tasks[2])
        self.assertNotIn("prompt", tasks[3])
        self.assertEqual([{"label": "第一章", "title": "建设背景与基础"}], tasks[2]["agenda_items"])
        self.assertEqual("第一章", tasks[3]["section_no"])
        self.assertEqual("建设背景与基础", tasks[3]["section_title"])

    def test_exported_agenda_and_section_svg_do_not_reference_content_images(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            manifest = {
                "mode": "template-image-ppt",
                "canvas": {"width": 1280, "height": 720},
                "body_region": {"x": 20, "y": 104, "width": 1240, "height": 592},
                "tasks": [
                    {
                        "page_number": 2,
                        "page_role": "agenda",
                        "title": "目录",
                        "slide_title": "目录",
                        "render_mode": "brand-template",
                        "template": "agenda",
                        "agenda_items": [{"label": "第一章", "title": "建设背景与基础"}],
                    },
                    {
                        "page_number": 3,
                        "page_role": "section",
                        "title": "第一章 建设背景与基础",
                        "slide_title": "第一章 建设背景与基础",
                        "render_mode": "brand-template",
                        "template": "section",
                        "section_no": "第一章",
                        "section_title": "建设背景与基础",
                        "notes_text": "",
                    },
                ],
            }

            project = module.write_project(manifest, output, "template_pages")
            agenda_svg = (project / "svg_output/page_002_目录.svg").read_text(encoding="utf-8")
            section_svg = (project / "svg_output/page_003_第一章_建设背景与基础.svg").read_text(encoding="utf-8")
            section_notes = (project / "notes/page_003_第一章_建设背景与基础.md").read_text(encoding="utf-8")
            written_manifest = json.loads((project / "template_image_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("建设背景与基础", agenda_svg)
        self.assertIn("第一章", section_svg)
        self.assertNotIn("<image", agenda_svg)
        self.assertNotIn("<image", section_svg)
        self.assertNotIn("本页围绕", section_notes)
        self.assertNotIn("汇报要点", section_notes)
        self.assertEqual("agenda", written_manifest["tasks"][0]["template"])

    def test_empty_speaker_note_manifest_record_disables_fallback(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "script.md"
            script.write_text(
                "\n".join(
                    [
                        "## 第3页：第一章 建设背景与基础",
                        "【内容锁定】",
                        "- 第一章",
                        "- 建设背景与基础",
                    ]
                ),
                encoding="utf-8",
            )
            notes = root / "notes.json"
            notes.write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "page_number": 3,
                                "title": "建设背景与基础",
                                "page_role": "section",
                                "notes_text": "",
                                "source": "business_rule_draft",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            pages = module.parse_page_blocks(script)

            manifest = module.build_manifest(script, [3], pages, root, speaker_notes_manifest=notes)

        self.assertEqual("", manifest["tasks"][0]["notes_text"])
        self.assertEqual("business_rule_draft", manifest["tasks"][0]["notes_source"])

    def test_cover_template_and_notes_use_script_content_not_role_label(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.md"
            script.write_text(
                "\n".join(
                    [
                        "## 第1页：封面",
                        "【内容锁定】",
                        "- 关于开展电力供需形势预测工作的整体方案",
                        "- 中电联统计与数智部电力供需分析处",
                        "- 2026 年 7 月",
                    ]
                ),
                encoding="utf-8",
            )
            pages = module.parse_page_blocks(script)
            manifest = module.build_manifest(script, [1], pages, Path(tmp))

            project = module.write_project(manifest, Path(tmp), "cover_page")
            cover_svg = (project / "svg_output/page_001_封面.svg").read_text(encoding="utf-8")
            cover_notes = (project / "notes/page_001_封面.md").read_text(encoding="utf-8")

        self.assertIn("关于开展电力供需形势预测工作的整体方案", cover_svg)
        self.assertIn("中电联统计与数智部电力供需分析处", cover_svg)
        self.assertIn("2026年7月", cover_svg)
        self.assertNotIn(">封面</text>", cover_svg)
        self.assertTrue(cover_notes.startswith("# 关于开展电力供需形势预测工作的整体方案"))
        self.assertIn("本页围绕“关于开展电力供需形势预测工作的整体方案”展开。", cover_notes)
        self.assertIn("- 中电联统计与数智部电力供需分析处", cover_notes)

    def test_cover_date_textbox_keeps_pptx_width_from_template(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.md"
            script.write_text(
                "\n".join(
                    [
                        "## 第1页：封面",
                        "【内容锁定】",
                        "- 关于开展电力供需形势预测工作的整体方案",
                        "- 中电联统计与数智部电力供需分析处",
                        "- 2026 年 7 月",
                    ]
                ),
                encoding="utf-8",
            )
            pages = module.parse_page_blocks(script)
            manifest = module.build_manifest(script, [1], pages, Path(tmp))
            project = module.write_project(manifest, Path(tmp), "cover_page_width")
            pptx = module.run_export(project)

            with zipfile.ZipFile(pptx) as package:
                slide_xml = package.read("ppt/slides/slide1.xml").decode("utf-8")

        self.assertIn("<a:t>2026年7月</a:t>", slide_xml)
        self.assertIn('<a:ext cx="2286000"', slide_xml)

    def test_speaker_notes_manifest_overrides_fallback_notes(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "script.md"
            script.write_text(
                "## 第4页：形势变化和工作要求\n【内容锁定】\n- 机械清单不应进入最终备注\n",
                encoding="utf-8",
            )
            notes_manifest = root / "speaker_notes_manifest.json"
            notes_manifest.write_text(
                json.dumps(
                    {
                        "schema": "cyberppt.speaker_notes_manifest.v1",
                        "notes": [
                            {
                                "page_number": 4,
                                "title": "形势变化和工作要求",
                                "notes_text": "这一页向各位领导汇报外部形势变化以及对供需预测工作的要求。",
                                "source": "business_rule_draft",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            pages = module.parse_page_blocks(script)
            manifest = module.build_manifest(
                script,
                [4],
                pages,
                root,
                speaker_notes_manifest=notes_manifest,
            )
            image_path = Path(manifest["tasks"][0]["image_path"])
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (1680, 944), "#ffffff").save(image_path)
            manifest["tasks"][0]["status"] = "Generated"
            project = module.write_project(manifest, root, "speaker_notes")
            notes = (project / "notes/page_004_形势变化和工作要求.md").read_text(encoding="utf-8")

        self.assertIn("这一页向各位领导汇报外部形势变化", notes)
        self.assertNotIn("机械清单不应进入最终备注", notes)


if __name__ == "__main__":
    unittest.main()
