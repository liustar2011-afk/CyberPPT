import tempfile
import unittest
import importlib.util
import sys
from pathlib import Path

from PIL import Image


def load_script_text_overlay():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "skills" / "ppt-master" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module_path = scripts_dir / "script_text_overlay.py"
    spec = importlib.util.spec_from_file_location("script_text_overlay", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ScriptTextOverlayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_script_text_overlay()

    def test_extract_script_truth_strips_module_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第5页：测试页\n\n"
                "【内容锁定】\n"
                "标题：\n可编辑标题\n\n"
                "模块一：数据可信\n"
                "- 授权可信\n\n"
                "【构图指令】\n左右布局。\n",
                encoding="utf-8",
            )

            lines = self.module.extract_script_truth_lines(script, 5)

        self.assertIn("可编辑标题", lines)
        self.assertIn("数据可信", lines)
        self.assertIn("授权可信", lines)
        self.assertNotIn("模块一：数据可信", lines)

    def test_build_overlay_boxes_scales_ocr_boxes_to_body_region(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第5页：测试页\n\n"
                "【内容锁定】\n标题：\n数据来源方\n\n【构图指令】\n无。\n",
                encoding="utf-8",
            )
            layout = {
                "image_size": {"width": 200, "height": 100},
                "items": [{"text": "数据来原方", "bbox": [20, 10, 100, 30], "confidence": 0.8}],
            }

            boxes = self.module.build_overlay_boxes(
                script,
                5,
                layout,
                body_region={"x": 10, "y": 20, "width": 400, "height": 200},
            )

        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].text, "数据来源方")
        self.assertEqual((boxes[0].x, boxes[0].y, boxes[0].w, boxes[0].h), (50.0, 40.0, 160.0, 40.0))

    def test_build_overlay_boxes_uses_white_text_on_dark_background_and_minimum_size(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第6页：测试页\n\n"
                "【内容锁定】\n标题：\n可信数据空间底座\n\n【构图指令】\n无。\n",
                encoding="utf-8",
            )
            background = Path(td) / "background.png"
            Image.new("RGB", (200, 100), "#062A5C").save(background)
            layout = {
                "image_size": {"width": 200, "height": 100},
                "items": [{"text": "可信数据空间底座", "bbox": [20, 10, 120, 20], "confidence": 0.9}],
            }

            boxes = self.module.build_overlay_boxes(
                script,
                6,
                layout,
                body_region={"x": 0, "y": 0, "width": 200, "height": 100},
                background_image=background,
            )

        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].fill, "#FFFFFF")
        self.assertGreaterEqual(boxes[0].font_size, 10.0)

    def test_build_overlay_boxes_snaps_same_row_text_to_remove_ocr_jitter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第6页：测试页\n\n"
                "【内容锁定】\n标题：\n成果可信\n\n成果价值\n\n【构图指令】\n无。\n",
                encoding="utf-8",
            )
            layout = {
                "image_size": {"width": 200, "height": 100},
                "items": [
                    {"text": "成果可信", "bbox": [20, 40, 70, 52], "confidence": 0.9},
                    {"text": "成果价值", "bbox": [90, 42, 140, 54], "confidence": 0.9},
                ],
            }

            boxes = self.module.build_overlay_boxes(
                script,
                6,
                layout,
                body_region={"x": 0, "y": 0, "width": 200, "height": 100},
            )

        self.assertEqual(len(boxes), 2)
        self.assertEqual(boxes[0].y, boxes[1].y)
        self.assertEqual(boxes[0].font_size, boxes[1].font_size)

    def test_build_overlay_boxes_centers_dark_base_title_as_semantic_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第6页：测试页\n\n"
                "【内容锁定】\n标题：\n电力行业科技成果转化可信数据空间底座\n\n【构图指令】\n无。\n",
                encoding="utf-8",
            )
            background = Path(td) / "background.png"
            image = Image.new("RGB", (400, 100), "white")
            for x in range(400):
                for y in range(72, 100):
                    image.putpixel((x, y), (6, 42, 92))
            image.save(background)
            layout = {
                "image_size": {"width": 400, "height": 100},
                "items": [
                    {
                        "text": "电力行业科技成果转化可信数据空间底座",
                        "bbox": [140, 80, 260, 88],
                        "confidence": 0.9,
                    }
                ],
            }

            boxes = self.module.build_overlay_boxes(
                script,
                6,
                layout,
                body_region={"x": 0, "y": 0, "width": 400, "height": 100},
                background_image=background,
            )

        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].fill, "#FFFFFF")
        self.assertEqual(boxes[0].align, "center")
        self.assertEqual((boxes[0].x, boxes[0].w), (0.0, 400.0))
        self.assertGreaterEqual(boxes[0].font_size, 16.0)

    def test_infer_semantic_containers_detects_dark_foundation_band(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            background = Path(td) / "background.png"
            image = Image.new("RGB", (200, 100), "white")
            for x in range(18, 182):
                for y in range(72, 96):
                    image.putpixel((x, y), (6, 42, 92))
            image.save(background)

            containers = self.module.infer_semantic_containers(
                background,
                {"image_size": {"width": 200, "height": 100}, "items": []},
                body_region={"x": 0, "y": 0, "width": 200, "height": 100},
            )

        self.assertEqual(len(containers), 1)
        self.assertEqual(containers[0].role, "foundation_base")
        self.assertEqual(containers[0].background, "dark")
        self.assertLessEqual(containers[0].x, 20)
        self.assertGreaterEqual(containers[0].w, 160)

    def test_extract_semantic_plan_uses_script_modules_as_roles(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第6页：总体架构设计\n\n"
                "【内容锁定】\n"
                "标题：\n\"1+2+6+N\"总体架构\n\n"
                "模块一：1个底座\n"
                "- 电力行业科技成果转化可信数据空间底座\n"
                "- 实现可信存证、权属管理、隐私计算、安全流通\n\n"
                "模块二：2套支撑体系\n"
                "- 标准规范体系\n"
                "- 安全保障体系\n\n"
                "模块三：6大核心场景\n"
                "- 成果可信存证与鉴定、成果价值可信评估\n\n"
                "模块四：N个生态节点\n"
                "- 覆盖成果供给方、需求方、服务方\n\n"
                "【构图指令】\n分层承接。\n",
                encoding="utf-8",
            )

            plan = self.module.extract_semantic_plan(script, 6)

        roles = [layer.role for layer in plan.layers]
        self.assertEqual(roles, ["foundation_base", "support_system", "application_scenario", "ecosystem_node"])
        self.assertEqual(plan.layers[1].expected_count, 2)
        self.assertEqual(plan.layers[2].expected_count, 6)
        self.assertIn("可信数据空间底座", "".join(plan.layers[0].keywords))

    def test_infer_semantic_containers_uses_script_plan_to_role_dark_bands(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第6页：总体架构设计\n\n"
                "【内容锁定】\n模块一：1个底座\n- 可信数据空间底座\n\n"
                "模块二：2套支撑体系\n- 标准规范体系\n- 安全保障体系\n\n"
                "【构图指令】\n无。\n",
                encoding="utf-8",
            )
            plan = self.module.extract_semantic_plan(script, 6)
            background = Path(td) / "background.png"
            image = Image.new("RGB", (200, 100), "white")
            for x in range(0, 200):
                for y in range(50, 62):
                    image.putpixel((x, y), (6, 80, 120))
                for y in range(78, 96):
                    image.putpixel((x, y), (6, 42, 92))
            image.save(background)

            containers = self.module.infer_semantic_containers(
                background,
                {"image_size": {"width": 200, "height": 100}, "items": []},
                body_region={"x": 0, "y": 0, "width": 200, "height": 100},
                semantic_plan=plan,
            )

        roles = [container.role for container in containers]
        self.assertIn("support_system", roles)
        self.assertIn("foundation_base", roles)

    def test_container_layout_fits_long_text_inside_assigned_container(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第6页：测试页\n\n"
                "【内容锁定】\n标题：\n电力行业科技成果转化可信数据空间底座能力说明\n\n【构图指令】\n无。\n",
                encoding="utf-8",
            )
            background = Path(td) / "background.png"
            image = Image.new("RGB", (200, 100), "white")
            for x in range(40, 160):
                for y in range(72, 96):
                    image.putpixel((x, y), (6, 42, 92))
            image.save(background)
            layout = {
                "image_size": {"width": 200, "height": 100},
                "items": [
                    {
                        "text": "电力行业科技成果转化可信数据空间底座能力说明",
                        "bbox": [80, 80, 120, 88],
                        "confidence": 0.9,
                    }
                ],
            }

            boxes = self.module.build_overlay_boxes(
                script,
                6,
                layout,
                body_region={"x": 0, "y": 0, "width": 200, "height": 100},
                background_image=background,
            )

        self.assertEqual(len(boxes), 1)
        self.assertGreaterEqual(boxes[0].x, 40)
        self.assertLessEqual(boxes[0].x + boxes[0].w, 160)
        estimated_width = len(boxes[0].text) * boxes[0].font_size * 0.56
        self.assertLessEqual(estimated_width, boxes[0].w)

    def test_foundation_container_does_not_absorb_non_title_description_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第6页：测试页\n\n"
                "【内容锁定】\n标题：\n实现可信存证、权属管理、隐私计算\n\n【构图指令】\n无。\n",
                encoding="utf-8",
            )
            background = Path(td) / "background.png"
            image = Image.new("RGB", (200, 100), "white")
            for x in range(0, 200):
                for y in range(72, 96):
                    image.putpixel((x, y), (6, 42, 92))
            image.save(background)
            layout = {
                "image_size": {"width": 200, "height": 100},
                "items": [
                    {
                        "text": "实现可信存证、权属管理、隐私计算",
                        "bbox": [45, 84, 155, 92],
                        "confidence": 0.9,
                    }
                ],
            }

            boxes = self.module.build_overlay_boxes(
                script,
                6,
                layout,
                body_region={"x": 0, "y": 0, "width": 200, "height": 100},
                background_image=background,
            )

        self.assertEqual(len(boxes), 1)
        self.assertGreater(boxes[0].x, 0)
        self.assertLess(boxes[0].w, 200)

    def test_regular_text_is_fit_after_row_snap_instead_of_overflowing_box(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "script.md"
            script.write_text(
                "## 第5页：测试页\n\n"
                "【内容锁定】\n标题：\n1000项以上成果入库\n\n短标签\n\n【构图指令】\n无。\n",
                encoding="utf-8",
            )
            layout = {
                "image_size": {"width": 200, "height": 100},
                "items": [
                    {"text": "1000项以上成果入库", "bbox": [20, 40, 95, 58], "confidence": 0.9},
                    {"text": "短标签", "bbox": [110, 41, 165, 61], "confidence": 0.9},
                ],
            }

            boxes = self.module.build_overlay_boxes(
                script,
                5,
                layout,
                body_region={"x": 0, "y": 0, "width": 200, "height": 100},
            )

        long_box = next(box for box in boxes if "1000" in box.text)
        self.assertLessEqual(self.module._text_estimated_width(long_box.text, long_box.font_size), long_box.w * 0.96)

    def test_render_overlay_svg_contains_background_and_text(self) -> None:
        svg = self.module.render_overlay_svg(
            background_href="../images/bg.png",
            canvas={"width": 1280, "height": 720},
            body_region={"x": 32, "y": 98, "width": 1216, "height": 589},
            slide_title="标题",
            subtitle="副标题",
            text_boxes=[
                self.module.OverlayTextBox(
                    text="数据可信",
                    x=100,
                    y=120,
                    w=160,
                    h=40,
                    font_size=18,
                    font_family="Microsoft YaHei",
                    fill="#0057C7",
                    font_weight="700",
                )
            ],
        )

        self.assertIn('href="../images/bg.png"', svg)
        self.assertIn("数据可信", svg)
        self.assertIn("标题", svg)


if __name__ == "__main__":
    unittest.main()
