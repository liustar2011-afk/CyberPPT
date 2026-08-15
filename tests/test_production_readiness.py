from __future__ import annotations

import unittest

from scripts.imagegen_pipeline.production_readiness import build_production_readiness


class ProductionReadinessTests(unittest.TestCase):
    def test_current_editable_ppt_artifacts_can_reach_production_ready(self) -> None:
        required = ("svg_output", "text_content_qa", "render_compare", "exported_pptx")
        readiness = build_production_readiness(
            stage="02-production-build",
            artifacts={name: f"/tmp/{name}" for name in required},
            reports={
                "text_content_qa": {"valid": True},
                "render_compare": {"passed": True},
            },
            required_tools=required,
        )

        self.assertTrue(readiness["valid"])
        self.assertEqual("production_ready", readiness["status"])
        self.assertEqual([], readiness["blocking_errors"])

    def test_missing_artifact_and_failed_report_are_both_blocking(self) -> None:
        readiness = build_production_readiness(
            stage="02-production-build",
            artifacts={"svg_output": None, "render_compare": "/tmp/render.json"},
            reports={"render_compare": {"passed": False}},
            required_tools=("svg_output", "render_compare"),
        )

        self.assertFalse(readiness["valid"])
        self.assertEqual(
            [
                {"tool": "svg_output", "code": "tool_not_consumed"},
                {"tool": "render_compare", "code": "tool_report_failed"},
            ],
            readiness["blocking_errors"],
        )


if __name__ == "__main__":
    unittest.main()
