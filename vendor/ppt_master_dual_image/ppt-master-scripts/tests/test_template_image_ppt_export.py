import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


def load_template_image_ppt_export():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "skills" / "ppt-master" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module_path = scripts_dir / "template_image_ppt_export.py"
    spec = importlib.util.spec_from_file_location("template_image_ppt_export", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TemplateImagePptExportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_template_image_ppt_export()

    def test_page_notes_text_uses_explicit_notes_section(self) -> None:
        block = self.module.PageBlock(
            page_number=1,
            title="测试",
            text="## 第1页：测试\n\n【内容锁定】\n标题：A\n\n【讲稿】\n这里是讲稿。\n",
        )

        self.assertEqual(self.module.page_notes_text(block), "这里是讲稿。")

    def test_build_manifest_keeps_original_page_script_as_notes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script.md"
            script.write_text(
                "## 第1页：测试页\n\n"
                "【内容锁定】\n标题：\n测试标题\n\n"
                "保真约束：不得新增画面文字。\n\n"
                "【构图指令】\n核心语义关系：用于测试。\n",
                encoding="utf-8",
            )

            pages = self.module.parse_page_blocks(script)
            manifest = self.module.build_manifest(script, [1], pages, base / "out")

        task = manifest["tasks"][0]
        self.assertIn("本页围绕“测试标题”展开。", task["notes_text"])
        self.assertNotIn("【内容锁定】", task["notes_text"])
        self.assertNotIn("【构图指令】", task["notes_text"])
        self.assertNotIn("## 第1页", task["notes_text"])

    def test_cover_and_ending_pages_use_templates_not_image_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script.md"
            script.write_text(
                "## 第1页：封面\n\n"
                "【内容锁定】\n标题：\n项目标题\n\n汇报单位：测试单位\n\n汇报日期：2026年6月\n\n"
                "【构图指令】\n封面构图。\n\n"
                "## 第2页：封底\n\n"
                "【内容锁定】\n标题：感谢聆听\n\n"
                "【构图指令】\n封底构图。\n",
                encoding="utf-8",
            )

            pages = self.module.parse_page_blocks(script)
            manifest = self.module.build_manifest(script, [1, 2], pages, base / "out")

        for task in manifest["tasks"]:
            self.assertEqual(task["render_mode"], "brand-template")
            self.assertEqual(task["status"], "Template")
            self.assertNotIn("prompt", task)
            self.assertNotIn("image_path", task)

    def test_page_notes_text_strips_page_separator(self) -> None:
        block = self.module.PageBlock(
            page_number=1,
            title="测试",
            text="## 第1页：测试\n\n【内容锁定】\n标题：A\n\n---\n",
        )

        self.assertEqual(self.module.page_notes_text(block), "本页围绕“A”展开。")

    def test_template_body_region_is_pulled_close_to_divider(self) -> None:
        region = {"x": 58, "y": 122, "width": 1164, "height": 554}

        adjusted = self.module.inset_content_region(region)

        self.assertEqual(adjusted, {"x": 32, "y": 98, "width": 1216, "height": 589})

    def test_generation_size_is_twice_content_region(self) -> None:
        region = {"x": 32, "y": 98, "width": 1216, "height": 589}

        size = self.module.generation_size_for_region(region)

        self.assertEqual(size, {"width": 2432, "height": 1184})

    def test_generated_image_size_is_normalized_after_backend_return(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image_path = Path(td) / "generated.png"
            Image.new("RGB", (1798, 875), "white").save(image_path)

            normalized = self.module.normalize_generated_image_size(image_path, "2432x1184")

            self.assertEqual(normalized, (2432, 1184))
            with Image.open(image_path) as image:
                self.assertEqual(image.size, (2432, 1184))

    def test_cover_prompt_allows_title_inside_content_image(self) -> None:
        block = self.module.PageBlock(
            page_number=1,
            title="封面",
            text="## 第1页：封面\n\n【内容锁定】\n标题：\n主标题\n\n副标题：副标题文本\n\n汇报单位：A\n\n【构图指令】\n正式封面。\n",
        )
        content = self.module.extract_content(block)

        prompt = self.module.content_prompt(
            block,
            content,
            {"x": 32, "y": 98, "width": 1216, "height": 589},
            {"width": 1216, "height": 592},
            "cover",
        )

        self.assertIn("封面/封底标题、副标题允许作为图片正文区文字生成", prompt)
        self.assertIn("主标题", prompt)
        self.assertIn("副标题文本", prompt)
        self.assertIn("汇报单位：A", prompt)

    def test_image_prompt_strips_module_prefix_from_visible_text_only(self) -> None:
        block = self.module.PageBlock(
            page_number=2,
            title="测试页",
            text="## 第2页：测试页\n\n"
            "【内容锁定】\n标题：正文标题\n\n"
            "模块一：政策可行性\n"
            "模块二：技术可行性\n"
            "一、正式章节标题\n\n"
            "【构图指令】\n模块一作为左侧分区，模块二作为右侧分区。\n",
        )
        content = self.module.extract_content(block)

        prompt = self.module.content_prompt(
            block,
            content,
            {"x": 32, "y": 98, "width": 1216, "height": 589},
            {"width": 1216, "height": 592},
            "body",
        )

        self.assertIn("【风格预设：象牙白 + 深蓝图文分离摄影彩色】", prompt)
        self.assertIn("#FFFFFF", prompt)
        self.assertIn("#002880", prompt)
        self.assertIn("PPT text-separated visual background source", prompt)
        self.assertIn("文字预留区必须保持纯白、近白或极浅干净底色", prompt)
        self.assertIn("layout_blueprints 仅作为构图候选", prompt)
        visible_text = prompt.split("正文内容：", 1)[1].split("构图要求：", 1)[0]
        self.assertNotIn("模块一", prompt)
        self.assertNotIn("模块二", prompt)
        self.assertNotIn("模块一", visible_text)
        self.assertNotIn("模块二", visible_text)
        self.assertIn("政策可行性", visible_text)
        self.assertIn("技术可行性", visible_text)
        self.assertIn("一、正式章节标题", visible_text)
        self.assertEqual(content.body.splitlines()[0], "模块一：政策可行性")

    def test_composition_interface_alias_is_not_visible_text(self) -> None:
        block = self.module.PageBlock(
            page_number=12,
            title="场景五",
            text=(
                "## 第12页：场景五\n\n"
                "【内容锁定】\n"
                "标题：场景五\n"
                "主判断：全周期保护。\n\n"
                "【保真约束】\n"
                "不得作为新增画面文字生成。\n\n"
                "【构图接口】\n"
                "核心语义关系：五阶段横向路径。\n"
            ),
        )

        content = self.module.extract_content(block)

        self.assertIn("主判断：全周期保护。", content.body)
        self.assertNotIn("保真约束", content.body)
        self.assertNotIn("构图接口", content.body)
        self.assertEqual(
            self.module.extract_composition_instruction(block),
            "核心语义关系：五阶段横向路径。",
        )

    def test_write_project_recovers_notes_from_source_script_for_old_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script.md"
            script.write_text(
                "## 第1页：旧Manifest页\n\n"
                "【内容锁定】\n标题：\n旧标题\n\n"
                "【构图指令】\n核心语义关系：旧manifest也应回读脚本。\n",
                encoding="utf-8",
            )
            image_path = base / "image.png"
            Image.new("RGB", (320, 180), "white").save(image_path)
            manifest = {
                "source_script": str(script),
                "canvas": {"width": 1280, "height": 720},
                "body_region": {"x": 58, "y": 144, "width": 1164, "height": 524},
                "tasks": [
                    {
                        "page_number": 1,
                        "page_role": "body",
                        "title": "旧Manifest页",
                        "slide_title": "旧标题",
                        "subtitle": "",
                        "body_text": "这不是应写入备注的临时摘要。",
                        "image_path": str(image_path),
                    }
                ],
            }

            project = self.module.write_project(manifest, base / "out", "notes_case")
            notes = (project / "notes" / "page_001_旧Manifest页.md").read_text(encoding="utf-8")

        self.assertIn("本页围绕“旧标题”展开。", notes)
        self.assertNotIn("核心语义关系：旧manifest也应回读脚本。", notes)
        self.assertNotIn("这不是应写入备注的临时摘要。", notes)

    def test_manifest_records_custom_markdown_image_style(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            style = base / "清爽专业风.md"
            style.write_text(
                "# 清爽专业风\n\n"
                "```json\n"
                "{\n"
                '  "style_name": "清爽专业风",\n'
                '  "visual_direction": "clean modern professional deck",\n'
                '  "color_palette": {"primary": "blue"},\n'
                '  "layout_patterns": ["timeline"],\n'
                '  "visual_elements": {"allowed": "cards", "avoid": "stickers"},\n'
                '  "rendering_constraints": ["No watermark"]\n'
                "}\n"
                "```\n",
                encoding="utf-8",
            )
            script = base / "script.md"
            script.write_text(
                "## 第2页：测试页\n\n"
                "【内容锁定】\n标题：正文标题\n\n"
                "政策可行性\n\n"
                "【构图指令】\n时间轴呈现。\n",
                encoding="utf-8",
            )

            pages = self.module.parse_page_blocks(script)
            manifest = self.module.build_manifest(
                script,
                [2],
                pages,
                base / "out",
                image_style_name=str(style),
            )

        self.assertEqual(manifest["image_style"]["name"], "清爽专业风")
        self.assertEqual(manifest["image_style"]["source_path"], str(style.resolve()))
        prompt = manifest["tasks"][0]["prompt"]
        self.assertIn("【风格预设：清爽专业风】", prompt)
        self.assertIn("clean modern professional deck", prompt)
        self.assertIn("中文文字采用接近微软雅黑特征", prompt)

    def test_new_cover_project_uses_brand_template_without_content_image(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            image_path = base / "image.png"
            Image.new("RGB", (320, 180), "white").save(image_path)
            manifest = {
                "canvas": {"width": 1280, "height": 720},
                "body_region": {"x": 32, "y": 98, "width": 1216, "height": 589},
                "tasks": [
                    {
                        "page_number": 1,
                        "page_role": "cover",
                        "title": "封面",
                        "slide_title": "主标题",
                        "subtitle": "副标题",
                        "body_text": "汇报单位：A",
                        "notes_text": "封面备注",
                        "image_path": str(image_path),
                    }
                ],
            }

            project = self.module.write_project(manifest, base / "out", "cover_case")
            svg = (project / "svg_output" / "page_001_封面.svg").read_text(encoding="utf-8")

        self.assertIn('data-brand-template="01_cover"', svg)
        self.assertIn(">主标题</text>", svg)
        self.assertIn("../images/cover_bg.jpg", svg)
        self.assertNotIn('x="32" y="98" width="1216" height="589"', svg)

    def test_long_cover_title_wraps_inside_brand_template(self) -> None:
        title = "基于电力行业可信数据空间的科技成果转化场景建设运营方案"
        svg = self.module.render_brand_template_svg(
            {
                "page_role": "cover",
                "template": "cover",
                "title": "封面",
                "slide_title": title,
                "subtitle": "",
                "body_text": "汇报单位：中国电力企业联合会科技服务中心\n汇报日期：2026年6月",
            },
            self.module.load_brand_rules(),
        )

        self.assertNotIn("{{TITLE}}", svg)
        self.assertNotIn(f">{title}</text>", svg)
        self.assertGreaterEqual(svg.count('font-weight="700" fill="#1F2933"'), 2)


if __name__ == "__main__":
    unittest.main()
