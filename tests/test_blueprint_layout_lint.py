from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.blueprint_layout_lint import lint_plan_layout


class BlueprintLayoutLintTests(unittest.TestCase):
    def test_accepts_plan_matching_layout_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = root / "context.json"
            plan = root / "plan.json"
            context.write_text(json.dumps(_context()), encoding="utf-8")
            plan.write_text(json.dumps(_plan(context)), encoding="utf-8")

            report = lint_plan_layout(plan, context)

        self.assertTrue(report["valid"])
        self.assertEqual(report["issues"], [])

    def test_flags_plan_region_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = root / "context.json"
            plan = root / "plan.json"
            context.write_text(json.dumps(_context()), encoding="utf-8")
            payload = _plan(context)
            payload["blueprint_layout_context"]["so_what_band_in"]["y"] = 6.2
            plan.write_text(json.dumps(payload), encoding="utf-8")

            report = lint_plan_layout(plan, context)

        self.assertFalse(report["valid"])
        self.assertEqual(report["issues"][0]["code"], "plan_layout_region_drift")


def _context() -> dict[str, object]:
    return {
        "safe_body_zone": {"x": 0.267, "y": 0.875, "w": 12.779, "h": 5.419},
        "so_what_band": {"x": 0.267, "y": 6.44, "w": 12.795, "h": 0.514},
    }


def _plan(context: Path) -> dict[str, object]:
    return {
        "blueprint_layout_context": {
            "source": str(context),
            "safe_body_zone_in": {"x": 0.267, "y": 0.875, "w": 12.779, "h": 5.419},
            "so_what_band_in": {"x": 0.267, "y": 6.44, "w": 12.795, "h": 0.514},
            "final_text_source": "content-lock",
        }
    }


if __name__ == "__main__":
    unittest.main()
