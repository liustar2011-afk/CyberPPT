from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

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
    def test_expanded_body_region_stays_below_master_red_divider(self) -> None:
        module = load_template_image_ppt_export()
        brand_body_region = {"x": 58, "y": 122, "width": 1164, "height": 554}

        adjusted = module.inset_content_region(brand_body_region)

        self.assertEqual({"x": 20, "y": 104, "width": 1240, "height": 592}, adjusted)
        self.assertGreaterEqual(adjusted["y"], 104)

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
