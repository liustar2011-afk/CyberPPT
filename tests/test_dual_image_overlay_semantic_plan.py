from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from scripts.dual_image_overlay.normalize import (
    CANVAS,
    normalize_image,
    relative_bbox,
    scale_bbox,
)
from scripts.dual_image_overlay.semantic_plan import load_semantic_plan


class DualImageOverlaySemanticPlanTests(unittest.TestCase):
    def test_scale_bbox_from_generated_image_to_canvas(self) -> None:
        self.assertEqual(CANVAS, (1280, 720))
        bbox = scale_bbox([167.2, 94.1, 334.4, 188.2], source_size=(1672, 941))
        self.assertEqual(bbox, [128.0, 72.0, 256.0, 144.0])

    def test_relative_bbox_uses_container_safe_area(self) -> None:
        bbox = relative_bbox([100, 50, 500, 250], [0.25, 0.1, 0.75, 0.9])
        self.assertEqual(bbox, [200.0, 70.0, 400.0, 230.0])

    def test_normalize_image_writes_1280x720(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            target = root / "target.png"
            Image.new("RGB", (1672, 941), "#FFFFFF").save(source)

            normalize_image(source, target)

            with Image.open(target) as image:
                self.assertEqual(image.size, (1280, 720))

    def test_load_semantic_plan_requires_explicit_containers_and_items(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "semantic_plan.json"

            path.write_text(
                json.dumps({"image_size": {"width": 1280, "height": 720}, "items": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "semantic_plan.containers"):
                load_semantic_plan(path)

            path.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1280, "height": 720},
                        "containers": [
                            {
                                "id": "title_bar",
                                "role": "title_container",
                                "bbox": [80, 40, 600, 160],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "semantic_plan.items"):
                load_semantic_plan(path)

    def test_load_semantic_plan_scales_boxes_and_relative_items(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "semantic_plan.json"
            path.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1672, "height": 941},
                        "containers": [
                            {
                                "id": "title_bar",
                                "role": "title_container",
                                "bbox": [80, 40, 1592, 160],
                                "text_safe_bbox": [100, 60, 1570, 140],
                            }
                        ],
                        "items": [
                            {
                                "source_text": "建议由中电联牵头",
                                "display_text": "建议由中电联牵头",
                                "role": "title",
                                "container_id": "title_bar",
                                "relative_bbox": [0, 0, 1, 1],
                                "font_size": 22,
                                "fill": "#FFFFFF",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            plan = load_semantic_plan(path)

            self.assertEqual(plan.image_size, {"width": 1280, "height": 720})
            self.assertEqual(plan.containers[0].bbox, [61.244, 30.606, 1218.756, 122.423])
            self.assertEqual(plan.containers[0].text_safe_bbox, [76.555, 45.909, 1201.914, 107.12])
            self.assertEqual(plan.items[0].bbox, [76.555, 45.909, 1201.914, 107.12])
            self.assertEqual(plan.items[0].container_id, "title_bar")

    def test_load_semantic_plan_rejects_unknown_container(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "semantic_plan.json"
            path.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1280, "height": 720},
                        "containers": [
                            {"id": "title_bar", "role": "title", "bbox": [80, 40, 600, 160]}
                        ],
                        "items": [
                            {
                                "display_text": "Missing container",
                                "container_id": "missing",
                                "relative_bbox": [0, 0, 1, 1],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unknown container_id"):
                load_semantic_plan(path)


if __name__ == "__main__":
    unittest.main()
