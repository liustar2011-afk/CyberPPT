import importlib.util
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from argparse import Namespace

from PIL import Image


def load_page_image_pair_batch():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "skills" / "ppt-master" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module_path = scripts_dir / "page_image_pair_batch.py"
    spec = importlib.util.spec_from_file_location("page_image_pair_batch", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PageImagePairBatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_page_image_pair_batch()

    def test_pair_manifest_defaults_to_template_content_region_generation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script-imagegen-compact.md"
            script.write_text(
                "## 第4页：可行性基础\n\n"
                "【内容锁定】\n"
                "标题：四维可行性基础已具备\n"
                "模块一：政策可行性\n"
                "国办函〔1988〕80号明确授权中电联履行成果转化法定职能\n\n"
                "【构图指令】\n"
                "四个维度平行呈现。\n",
                encoding="utf-8",
            )

            pages = self.module.parse_page_blocks(script)
            manifest = self.module.build_pair_manifest(
                script,
                [4],
                pages,
                base / "images",
                aspect_ratio=self.module.DEFAULT_ASPECT_RATIO,
                image_size=self.module.DEFAULT_IMAGE_SIZE,
                canvas=self.module.DEFAULT_CANVAS,
            )

        pair = manifest["pairs"][0]
        prompt = pair["full"]["prompt"]

        self.assertEqual(pair["full"]["canvas"], "2432x1184")
        self.assertNotIn("background", pair)
        self.assertNotIn("pair_generation", pair)
        self.assertEqual(pair["full"]["image_size"], "2x-content-region")
        self.assertEqual(pair["full"]["aspect_ratio"], "content-region")
        self.assertIn("输出画布尺寸为 2432×1184", prompt)
        self.assertIn("模板坐标 x=32, y=98, w=1216, h=589", prompt)
        self.assertIn("不要生成完整 PPT 页面", prompt)
        self.assertIn("不要画标题、副标题", prompt)
        self.assertEqual(manifest["image_style"]["name"], "象牙白 + 深蓝图文分离摄影彩色")
        self.assertIn("【风格预设：象牙白 + 深蓝图文分离摄影彩色】", prompt)
        self.assertIn("#FFFFFF", prompt)
        self.assertIn("#F7FAFF", prompt)
        self.assertIn("#F2F6FF", prompt)
        self.assertIn("#002880", prompt)
        self.assertIn("#D00000", prompt)
        self.assertIn("#B8C7E6", prompt)
        self.assertIn("PPT text-separated visual background source", prompt)
        self.assertIn("Photographic-feeling visuals are allowed", prompt)
        self.assertIn("semantic_colors", prompt)
        self.assertIn("#16A34A", prompt)
        self.assertIn("not as a strict vector-redraw source image", prompt)
        self.assertIn("gray fog", prompt)
        self.assertIn("文字预留区必须保持纯白、近白或极浅干净底色", prompt)
        self.assertIn("4K 级 Office 截图视觉精度", prompt)
        self.assertIn("这是清晰度目标，不是实际输出尺寸要求", prompt)
        self.assertIn("真实 PowerPoint 可编辑文本的视觉效果", prompt)
        self.assertIn("100% 不透明实色填充", prompt)
        self.assertIn("边缘锐利，横平竖直，基线整齐", prompt)
        self.assertIn("最多不超过 3 个", prompt)
        self.assertIn("禁止每个流程节点、阶段节点或模块卡片都配一个图标", prompt)
        self.assertIn("流程链条、阶段轴、九环节加工链、五阶段生命周期节点禁止使用图标", prompt)
        self.assertIn("流程关系必须优先用连续路径轴、泳道、分层带、编号节点、线性证据链", prompt)
        self.assertIn("优先使用 1-4 个与页面内容直接相关的语义中型配图承载区", prompt)
        self.assertIn("one main semantic visual/photo-like carrier", prompt)
        self.assertIn("avoid icon arrays", prompt)
        self.assertIn("layout_blueprints 仅作为构图候选", prompt)
        self.assertIn("PPT可识别源图", prompt)
        self.assertIn("不得按海报、插画、网页首屏或复杂视觉合成图生成", prompt)
        self.assertIn("清晰边界", prompt)
        self.assertIn("闭合轮廓", prompt)
        self.assertIn("正交布局", prompt)
        self.assertIn("可裁切分离特征", prompt)
        self.assertIn("独立矩形或圆角矩形承载区", prompt)
        self.assertNotIn("1280×720", prompt)
        self.assertNotIn("标题区固定左上", prompt)
        self.assertNotIn("模块一", prompt)
        self.assertNotIn("模块二", prompt)

    def test_pair_manifest_includes_background_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script-imagegen-compact.md"
            script.write_text(
                "## 第4页：可行性基础\n\n"
                "【内容锁定】\n标题：四维可行性基础已具备\n\n"
                "【构图指令】\n四个维度平行呈现。\n",
                encoding="utf-8",
            )
            pages = self.module.parse_page_blocks(script)
            manifest = self.module.build_pair_manifest(
                script,
                [4],
                pages,
                base / "images",
                aspect_ratio=self.module.DEFAULT_ASPECT_RATIO,
                image_size=self.module.DEFAULT_IMAGE_SIZE,
                canvas=self.module.DEFAULT_CANVAS,
                include_background=True,
            )

        pair = manifest["pairs"][0]
        self.assertEqual(manifest["output_variants"], ["full", "background"])
        self.assertEqual(pair["background"]["canvas"], "2432x1184")
        self.assertIn("pair_generation", pair)

    def test_dual_image_manifest_expands_each_pair_full_then_background(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script-imagegen-compact.md"
            script.write_text(
                "## 第5页：总体思路与建设目标\n\n"
                "【内容锁定】\n"
                "标题：\n"
                "“1+2+6+N”总体思路与三阶段建设目标\n\n"
                "副标题：行业主导、可信为基、需求导向，分步实施迭代优化\n\n"
                "【构图指令】\n"
                "时间轴呈现。\n",
                encoding="utf-8",
            )
            image_dir = base / "images"
            image_dir.mkdir()
            full = image_dir / "page_005_full.png"
            background = image_dir / "page_005_background.png"
            Image.new("RGB", (2432, 1184), "white").save(full)
            Image.new("RGB", (2432, 1184), "#F8FBFF").save(background)
            pair_manifest = {
                "source_script": str(script),
                "generation_contract": {"generation_size": {"width": 2432, "height": 1184}},
                "pairs": [
                    {
                        "page_number": 5,
                        "title": "总体思路与建设目标",
                        "full": {"path": str(full), "status": self.module.STATUS_GENERATED},
                        "background": {"path": str(background), "status": self.module.STATUS_GENERATED},
                    }
                ],
            }

            manifest = self.module.build_dual_image_template_manifest(pair_manifest)

        self.assertEqual(manifest["mode"], "page-image-pair-dual-image-ppt")
        self.assertEqual(len(manifest["tasks"]), 2)
        first, second = manifest["tasks"]
        self.assertEqual(first["image_variant"], "full")
        self.assertEqual(first["image_variant_label"], "完整图")
        self.assertEqual(second["image_variant"], "background")
        self.assertEqual(second["image_variant_label"], "底图")
        self.assertEqual(first["slide_title"], second["slide_title"])
        self.assertEqual(first["subtitle"], second["subtitle"])
        self.assertEqual(first["slide_title"], "“1+2+6+N”总体思路与三阶段建设目标")
        self.assertEqual(first["subtitle"], "行业主导、可信为基、需求导向，分步实施迭代优化")
        self.assertEqual(first["render_mode"], "content-image")
        self.assertEqual(second["render_mode"], "content-image")

    def test_pair_manifest_accepts_custom_image_style_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            style = base / "custom_style.json"
            style.write_text(
                '{\n'
                '  "style_name": "自定义测试风",\n'
                '  "visual_direction": "precise structured test style",\n'
                '  "color_palette": {"primary": "cyan"},\n'
                '  "layout_patterns": ["matrix"],\n'
                '  "visual_elements": {"allowed": "thin rules", "avoid": "neon"},\n'
                '  "rendering_constraints": ["No unrelated logo"]\n'
                '}\n',
                encoding="utf-8",
            )
            script = base / "script-imagegen-compact.md"
            script.write_text(
                "## 第4页：可行性基础\n\n"
                "【内容锁定】\n"
                "标题：四维可行性基础已具备\n"
                "政策可行性\n\n"
                "【构图指令】\n"
                "四个维度平行呈现。\n",
                encoding="utf-8",
            )

            pages = self.module.parse_page_blocks(script)
            manifest = self.module.build_pair_manifest(
                script,
                [4],
                pages,
                base / "images",
                aspect_ratio=self.module.DEFAULT_ASPECT_RATIO,
                image_size=self.module.DEFAULT_IMAGE_SIZE,
                canvas=self.module.DEFAULT_CANVAS,
                image_style_name=str(style),
            )

        prompt = manifest["pairs"][0]["full"]["prompt"]
        self.assertEqual(manifest["image_style"]["name"], "自定义测试风")
        self.assertEqual(manifest["image_style"]["source_path"], str(style.resolve()))
        self.assertIn("【风格预设：自定义测试风】", prompt)
        self.assertIn("precise structured test style", prompt)
        self.assertIn("中文文字采用接近微软雅黑特征", prompt)

    def test_pair_manifest_accepts_text_separated_photographic_color_style(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script-imagegen-compact.md"
            script.write_text(
                "## 第4页：可行性基础\n\n"
                "【内容锁定】\n"
                "标题：四维可行性基础已具备\n"
                "政策可行性\n\n"
                "【构图指令】\n"
                "四个维度平行呈现。\n",
                encoding="utf-8",
            )

            pages = self.module.parse_page_blocks(script)
            manifest = self.module.build_pair_manifest(
                script,
                [4],
                pages,
                base / "images",
                aspect_ratio=self.module.DEFAULT_ASPECT_RATIO,
                image_size=self.module.DEFAULT_IMAGE_SIZE,
                canvas=self.module.DEFAULT_CANVAS,
                image_style_name="象牙白深蓝图文分离摄影彩色",
            )

        prompt = manifest["pairs"][0]["full"]["prompt"]
        self.assertEqual(manifest["image_style"]["name"], "象牙白 + 深蓝图文分离摄影彩色")
        self.assertIn("【风格预设：象牙白 + 深蓝图文分离摄影彩色】", prompt)
        self.assertIn("PPT text-separated visual background source", prompt)
        self.assertIn("Photographic-feeling visuals are allowed", prompt)
        self.assertIn("semantic_colors", prompt)
        self.assertIn("#16A34A", prompt)
        self.assertIn("text reservation areas", prompt)
        self.assertIn("not as a strict vector-redraw source image", prompt)

    def test_generate_pairs_runs_different_pages_in_parallel(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            manifest_path = base / "page_image_pairs.json"
            pairs = []
            for page_number in (1, 2):
                pairs.append(
                    {
                        "page_number": page_number,
                        "full": {
                            "path": str(base / f"page_{page_number}_full.png"),
                            "prompt": "full",
                            "canvas": "32x18",
                        }
                    }
                )
            self.module.write_json(manifest_path, {"pairs": pairs})

            lock = threading.Lock()
            active = 0
            max_active = 0

            def fake_run_codex_image(*, output_path, **_kwargs):
                nonlocal active, max_active
                with lock:
                    active += 1
                    max_active = max(max_active, active)
                time.sleep(0.05)
                Image.new("RGB", (32, 18), "white").save(output_path)
                with lock:
                    active -= 1

            self.module.run_codex_image = fake_run_codex_image
            rc = self.module.generate_pairs(
                Namespace(
                    manifest=manifest_path,
                    model="gpt-image-2",
                    size=None,
                    quality="medium",
                    background_method="codex-edit",
                    timeout=30,
                    full_retries=0,
                    background_retries=0,
                    force=False,
                    dry_run=False,
                    parallel_pages=2,
                )
            )

        self.assertEqual(rc, 0)
        self.assertGreaterEqual(max_active, 2)

    def test_default_generation_does_not_create_background_images(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            manifest_path = base / "page_image_pairs.json"
            background = base / "page_1_background.png"
            self.module.write_json(
                manifest_path,
                {
                    "pairs": [
                        {
                            "page_number": 1,
                            "full": {
                                "path": str(base / "page_1_full.png"),
                                "prompt": "full",
                                "canvas": "32x18",
                            },
                            "background": {
                                "path": str(background),
                                "prompt": "background",
                                "canvas": "32x18",
                            },
                        }
                    ],
                },
            )
            calls = []

            def fake_run_codex_image(*, output_path, image_paths, **_kwargs):
                calls.append((Path(output_path).name, list(image_paths)))
                Image.new("RGB", (32, 18), "white").save(output_path)

            self.module.run_codex_image = fake_run_codex_image
            rc = self.module.generate_pairs(
                Namespace(
                    manifest=manifest_path,
                    model="gpt-image-2",
                    size=None,
                    quality="medium",
                    background_method="codex-edit",
                    timeout=30,
                    full_retries=0,
                    background_retries=0,
                    force=False,
                    dry_run=False,
                    parallel_pages=1,
                    include_background=False,
                )
            )

        self.assertEqual(rc, 0)
        self.assertEqual(calls, [("page_1_full.png", [])])
        self.assertFalse(background.exists())

    def test_full_only_template_manifest_exports_one_slide_per_page(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script-imagegen-compact.md"
            script.write_text(
                "## 第5页：总体思路与建设目标\n\n"
                "【内容锁定】\n标题：\n“1+2+6+N”总体思路与三阶段建设目标\n\n"
                "副标题：行业主导、可信为基、需求导向，分步实施迭代优化\n\n"
                "【构图指令】\n时间轴呈现。\n",
                encoding="utf-8",
            )
            full = base / "page_005_full.png"
            Image.new("RGB", (2432, 1184), "white").save(full)
            pair_manifest = {
                "source_script": str(script),
                "generation_contract": {"generation_size": {"width": 2432, "height": 1184}},
                "pairs": [
                    {
                        "page_number": 5,
                        "title": "总体思路与建设目标",
                        "full": {"path": str(full), "status": self.module.STATUS_GENERATED},
                    }
                ],
            }

            manifest = self.module.build_template_image_manifest(pair_manifest)

        self.assertEqual(manifest["mode"], "page-image-full-only-ppt")
        self.assertEqual(len(manifest["tasks"]), 1)
        self.assertEqual(manifest["tasks"][0]["image_variant"], "full")
        self.assertEqual(manifest["tasks"][0]["slide_title"], "“1+2+6+N”总体思路与三阶段建设目标")

    def test_draft_mode_applies_medium_quality_without_overriding_explicit_quality(self) -> None:
        default_args = Namespace(
            draft=True,
            quality="high",
            image_size=self.module.DEFAULT_IMAGE_SIZE,
            canvas=self.module.DEFAULT_CANVAS,
        )
        self.module.apply_run_speed_options(default_args)
        self.assertEqual(default_args.quality, "medium")
        self.assertEqual(default_args.image_size, self.module.DRAFT_IMAGE_SIZE)
        self.assertEqual(default_args.canvas, self.module.DRAFT_CANVAS)

        explicit_args = Namespace(draft=True, quality="low", image_size="custom-size", canvas="800x450")
        self.module.apply_run_speed_options(explicit_args)
        self.assertEqual(explicit_args.quality, "low")
        self.assertEqual(explicit_args.image_size, "custom-size")
        self.assertEqual(explicit_args.canvas, "800x450")

    def test_resume_reuses_existing_manifest_without_replanning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            script = base / "script-imagegen-compact.md"
            script.write_text(
                "## 第1页：旧标题\n\n【内容锁定】\n旧内容\n\n【构图指令】\n旧构图\n",
                encoding="utf-8",
            )
            output_dir = base / "images"
            output_dir.mkdir()
            manifest_path = output_dir / "page_image_pairs.json"
            self.module.write_json(
                manifest_path,
                {
                    "source_script": str(script),
                    "pairs": [
                        {
                            "page_number": 99,
                            "title": "already planned",
                            "full": {"path": str(output_dir / "full.png")},
                            "background": {"path": str(output_dir / "background.png")},
                        }
                    ],
                },
            )

            _manifest, actual_manifest_path, page_numbers = self.module._create_plan(
                script_path=script,
                pages_raw="1",
                output_dir=output_dir,
                aspect_ratio=self.module.DEFAULT_ASPECT_RATIO,
                image_size=self.module.DEFAULT_IMAGE_SIZE,
                canvas=self.module.DEFAULT_CANVAS,
                resume=True,
            )

        self.assertEqual(actual_manifest_path, manifest_path.resolve())
        self.assertEqual(page_numbers, [99])


if __name__ == "__main__":
    unittest.main()
