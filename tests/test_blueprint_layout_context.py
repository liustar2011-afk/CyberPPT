from __future__ import annotations

import unittest

from scripts.blueprint_layout_context import build_layout_context, px_rect_to_inches


class BlueprintLayoutContextTests(unittest.TestCase):
    def test_converts_normalized_pixels_to_inches(self) -> None:
        rect = {"x": 25.64, "y": 84.0, "w": 1226.8, "h": 520.24}

        converted = px_rect_to_inches(rect)

        self.assertEqual(converted, {"x": 0.267, "y": 0.875, "w": 12.779, "h": 5.419})

    def test_builds_layout_context_from_learning_report(self) -> None:
        context = build_layout_context(
            {
                "blueprint_dir": "blueprints",
                "learned_rules": {
                    "canvas": {"width": 1280, "height": 720},
                    "safe_body_zone_median": {"x": 25.64, "y": 84.0, "w": 1226.8, "h": 520.24},
                    "lower_so_what_band_bbox_median": {"x": 25.64, "y": 618.24, "w": 1228.33, "h": 49.35},
                    "top_badge_bbox_median": {"x": 0.0, "y": 0.0, "w": 179.14, "h": 143.85},
                },
            }
        )

        self.assertEqual(context["schema"], "cyberppt.blueprint_layout_context.v1")
        self.assertEqual(context["safe_body_zone"]["x"], 0.267)
        self.assertEqual(context["so_what_band"]["y"], 6.44)
        self.assertEqual(context["so_what_center_y"], 6.697)
        self.assertTrue(context["policy"]["blueprint_text_is_placeholder"])


if __name__ == "__main__":
    unittest.main()
