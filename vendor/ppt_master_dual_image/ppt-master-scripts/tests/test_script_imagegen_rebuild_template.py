import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


def load_rebuild_module():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "skills" / "ppt-master" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module_path = scripts_dir / "script_imagegen_rebuild_template.py"
    spec = importlib.util.spec_from_file_location("script_imagegen_rebuild_template", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ScriptImagegenRebuildTemplateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_rebuild_module()

    def test_rebuild_from_pair_manifest_writes_overlay_svg_and_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            image_dir = project / "images" / "script_imagegen"
            image_dir.mkdir(parents=True)
            (project / "sources").mkdir()
            script = project / "sources" / "script.md"
            script.write_text(
                "## 第12页：场景五\n\n"
                "【内容锁定】\n标题：\n知识产权全生命周期五阶段\n\n数据来源方\n\n"
                "【构图指令】\n流程图。\n",
                encoding="utf-8",
            )
            full = image_dir / "page_012_full.png"
            background = image_dir / "page_012_background.png"
            Image.new("RGB", (200, 100), "white").save(full)
            Image.new("RGB", (200, 100), "#F8FBFF").save(background)
            manifest_path = image_dir / "page_image_pairs.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "source_script": str(script),
                        "project_path": str(project),
                        "pairs": [
                            {
                                "page_number": 12,
                                "title": "场景五",
                                "full": {"path": str(full), "status": "Generated"},
                                "background": {"path": str(background), "status": "Generated"},
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            ocr_dir = project / "analysis" / "ocr"
            ocr_dir.mkdir(parents=True)
            (ocr_dir / "page_012_text_layout.json").write_text(
                json.dumps(
                    {
                        "image_size": {"width": 200, "height": 100},
                        "items": [{"text": "数据来原方", "bbox": [20, 10, 80, 30], "confidence": 0.9}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = self.module.rebuild_from_manifest(manifest_path, ocr_backend="none")

            svg_files = sorted((project / "svg_output").glob("*.svg"))
            self.assertEqual(len(svg_files), 1)
            svg = svg_files[0].read_text(encoding="utf-8")
            self.assertIn("数据来源方", svg)
            self.assertIn("知识产权全生命周期五阶段", svg)
            self.assertTrue((project / "analysis" / "ocr" / "page_012_text_mapping.json").is_file())
            self.assertTrue((project / "analysis" / "semantic_containers" / "page_012_containers.json").is_file())
            self.assertTrue((project / "analysis" / "semantic_plan" / "page_012_semantic_plan.json").is_file())
            self.assertEqual(result["slides"], 1)

    def test_rebuild_normalizes_background_to_full_image_size_and_records_qa(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            image_dir = project / "images" / "script_imagegen"
            image_dir.mkdir(parents=True)
            (project / "sources").mkdir()
            script = project / "sources" / "script.md"
            script.write_text(
                "## 第6页：总体架构\n\n"
                "【内容锁定】\n标题：\n可信数据空间底座\n\n【构图指令】\n无。\n",
                encoding="utf-8",
            )
            full = image_dir / "page_006_full.png"
            background = image_dir / "page_006_background.png"
            Image.new("RGB", (200, 100), "white").save(full)
            Image.new("RGB", (196, 102), "#062A5C").save(background)
            manifest_path = image_dir / "page_image_pairs.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "source_script": str(script),
                        "project_path": str(project),
                        "pairs": [
                            {
                                "page_number": 6,
                                "title": "总体架构",
                                "full": {"path": str(full), "status": "Generated"},
                                "background": {"path": str(background), "status": "Generated"},
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            ocr_dir = project / "analysis" / "ocr"
            ocr_dir.mkdir(parents=True)
            (ocr_dir / "page_006_text_layout.json").write_text(
                json.dumps(
                    {
                        "image_size": {"width": 200, "height": 100},
                        "items": [{"text": "可信数据空间底座", "bbox": [20, 70, 120, 86], "confidence": 0.9}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            self.module.rebuild_from_manifest(manifest_path, ocr_backend="none")

            normalized = project / "images" / "page_006_background.png"
            with Image.open(normalized) as im:
                self.assertEqual(im.size, (200, 100))
            qa_path = project / "analysis" / "rebuild_quality.json"
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            self.assertEqual(qa["pages"][0]["image_size_check"]["status"], "normalized")
            self.assertEqual(qa["pages"][0]["image_size_check"]["full_size"], [200, 100])
            self.assertEqual(qa["pages"][0]["image_size_check"]["background_size"], [196, 102])


if __name__ == "__main__":
    unittest.main()
