from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]


class DualImageOverlayBuildPageTests(unittest.TestCase):
    def test_build_page_creates_pptx_and_qa_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            full = tmp_path / "full.png"
            background = tmp_path / "background.png"
            Image.new("RGB", (1672, 941), "#F2F3EF").save(full)
            background_image = Image.new("RGB", (1672, 941), "#F2F3EF")
            ImageDraw.Draw(background_image).line((120, 120, 720, 120), fill="#123B66", width=10)
            background_image.save(background)
            semantic = tmp_path / "semantic_plan.json"
            semantic.write_text(
                json.dumps(
                    {
                        "image_size": {"width": 1672, "height": 941},
                        "containers": [
                            {
                                "id": "title",
                                "role": "title",
                                "bbox": [80, 40, 900, 150],
                                "text_safe_bbox": [90, 50, 880, 140],
                            }
                        ],
                        "items": [
                            {
                                "source_text": "核心结论",
                                "display_text": "核心结论",
                                "role": "title",
                                "container_id": "title",
                                "relative_bbox": [0, 0, 1, 1],
                                "font_size": 18,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            out_dir = tmp_path / "page"
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/build_page.py"),
                    "--full",
                    str(full),
                    "--background",
                    str(background),
                    "--semantic-plan",
                    str(semantic),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            self.assertTrue((out_dir / "normalized/full-1280x720.png").is_file())
            self.assertTrue((out_dir / "normalized/background-1280x720.png").is_file())
            self.assertTrue((out_dir / "exports/page.pptx").is_file())
            self.assertTrue((out_dir / "analysis/visual_preview.json").is_file())
            self.assertTrue((out_dir / "analysis/source_capture.json").is_file())
            self.assertTrue((out_dir / "analysis/source_capture_gate.json").is_file())
            self.assertTrue((out_dir / "analysis/visual_registry/page_001_visual_element_registry.json").is_file())
            self.assertTrue((out_dir / "analysis/page_quality_report.json").is_file())
            self.assertTrue((out_dir / "analysis/container_workspace/page_001_container_workspace.json").is_file())
            self.assertTrue((out_dir / "analysis/workspace_assignment/page_001_workspace_assignment.json").is_file())
            source_capture = json.loads((out_dir / "analysis/source_capture.json").read_text(encoding="utf-8"))
            source_capture_gate = json.loads((out_dir / "analysis/source_capture_gate.json").read_text(encoding="utf-8"))
            text_content_qa = json.loads((out_dir / "analysis/text_content_qa.json").read_text(encoding="utf-8"))
            page_quality = json.loads((out_dir / "analysis/page_quality_report.json").read_text(encoding="utf-8"))
            readiness = json.loads(
                (out_dir / "analysis/production_readiness.json").read_text(encoding="utf-8")
            )
        self.assertEqual("cyberppt.dual_image.source_capture.v1", source_capture["schema"])
        self.assertEqual([1], [page["page_number"] for page in source_capture["pages"]])
        self.assertEqual(1, source_capture["inputs"]["visual_registry_elements"])
        self.assertEqual(1, source_capture["inputs"]["ocr_text_mappings"])
        self.assertEqual(["核心结论"], text_content_qa["expected_texts"])
        self.assertEqual("cyberppt.dual_image.source_capture_gate.v1", source_capture_gate["schema"])
        self.assertFalse(source_capture_gate["valid"])
        self.assertIn("render_delta_not_measured", source_capture_gate["gap_counts"])
        self.assertFalse(readiness["valid"])
        self.assertTrue(readiness["structural_valid"])
        self.assertEqual("source_capture_rework_required", readiness["status"])
        self.assertTrue(readiness["checks"]["text_content_matches_lock"])
        self.assertTrue(readiness["checks"]["layout_qa_pass"])
        self.assertFalse(readiness["checks"]["visual_preview_generated"])
        self.assertFalse(readiness["checks"]["human_visual_review_pass"])
        self.assertTrue(readiness["checks"]["source_capture_available"])
        self.assertTrue(readiness["checks"]["source_capture_consumed"])
        self.assertTrue(readiness["checks"]["source_capture_text_drives_qa"])
        self.assertFalse(readiness["checks"]["source_capture_gate_pass"])
        self.assertTrue(readiness["checks"]["draft_visual_registry_generated"])
        self.assertFalse(readiness["checks"]["source_capture_gaps_resolved"])
        self.assertFalse(readiness["checks"]["page_quality_report_pass"])
        self.assertFalse(readiness["source_capture_gate"]["valid"])
        self.assertEqual("cyberppt.dual_image.page_quality_report.v1", page_quality["schema"])
        self.assertEqual("overlay", page_quality["stage"])
        self.assertFalse(page_quality["valid"])
        self.assertIn(
            "overlay.source_capture_gate_pass",
            [item["id"] for item in page_quality["blocking_errors"]],
        )
        self.assertEqual(
            str((out_dir / "analysis/source_capture.json").resolve()),
            readiness["artifacts"]["source_capture"],
        )
        self.assertEqual(
            str((out_dir / "analysis/source_capture_gate.json").resolve()),
            readiness["artifacts"]["source_capture_gate"],
        )
        self.assertEqual(
            str((out_dir / "analysis/visual_registry").resolve()),
            readiness["artifacts"]["draft_visual_registry"],
        )
        self.assertEqual(
            str((out_dir / "analysis/page_quality_report.json").resolve()),
            readiness["artifacts"]["page_quality_report"],
        )
        self.assertEqual(
            str((out_dir / "analysis/container_workspace/page_001_container_workspace.json").resolve()),
            readiness["artifacts"]["container_workspace"],
        )
        self.assertEqual(
            str((out_dir / "analysis/workspace_assignment/page_001_workspace_assignment.json").resolve()),
            readiness["artifacts"]["workspace_assignment"],
        )
        self.assertEqual("semantic_plan_containers", readiness["geometry_source"])
        self.assertEqual("semantic-container-geometry", readiness["alignment"]["model"])


if __name__ == "__main__":
    unittest.main()
