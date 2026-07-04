import tempfile
import unittest
import importlib.util
import sys
from pathlib import Path

from PIL import Image


def load_ocr_text_locator():
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = repo / "skills" / "ppt-master" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module_path = scripts_dir / "ocr_text_locator.py"
    spec = importlib.util.spec_from_file_location("ocr_text_locator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OcrTextLocatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_ocr_text_locator()

    def test_none_backend_returns_empty_layout_with_image_size(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "slide.png"
            Image.new("RGB", (320, 180), "white").save(image)

            layout = self.module.locate_text(image, backend="none")

        self.assertEqual(layout["image_size"], {"width": 320, "height": 180})
        self.assertEqual(layout["items"], [])

    def test_normalize_layout_accepts_bbox_items(self) -> None:
        layout = self.module.normalize_layout(
            {
                "image_size": {"width": 100, "height": 50},
                "items": [
                    {"text": "数据来源方", "bbox": [1, 2, 30, 20], "confidence": "0.91"}
                ],
            }
        )

        self.assertEqual(layout["items"][0]["text"], "数据来源方")
        self.assertEqual(layout["items"][0]["bbox"], [1.0, 2.0, 30.0, 20.0])
        self.assertEqual(layout["items"][0]["confidence"], 0.91)

    def test_normalize_layout_rejects_invalid_bbox(self) -> None:
        with self.assertRaises(ValueError):
            self.module.normalize_layout(
                {
                    "image_size": {"width": 100, "height": 50},
                    "items": [{"text": "坏框", "bbox": [30, 2, 1, 20]}],
                }
            )

    def test_extract_json_from_fenced_vision_output(self) -> None:
        parsed = self.module.parse_json_output(
            "```json\n{\"image_size\":{\"width\":10,\"height\":5},\"items\":[]}\n```"
        )

        self.assertEqual(parsed["image_size"], {"width": 10, "height": 5})


if __name__ == "__main__":
    unittest.main()
