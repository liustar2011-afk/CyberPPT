from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from cyberppt.commands.script_runner import script_path


ROOT = Path(__file__).resolve().parents[1]
REBUILD_ENGINE_DIR = ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"
if str(REBUILD_ENGINE_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REBUILD_ENGINE_DIR))

from scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild import _prepare_page_images  # noqa: E402


class DualImageOverlayTemplateRebuildTests(unittest.TestCase):
    def test_template_rebuild_is_exposed_as_cyberppt_script_alias(self) -> None:
        self.assertEqual("template_rebuild.py", script_path("template-rebuild").name)

    def test_template_rebuild_consumes_template_project_and_source_capture(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            _write_template_project(project)
            manifest = _write_pair_manifest(root, project)

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                    str(manifest),
                    "--skip-rebuild",
                    "--no-export",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            readiness = json.loads((project / "analysis/template_rebuild_readiness.json").read_text(encoding="utf-8"))
            source_capture = json.loads((project / "analysis/source_capture.json").read_text(encoding="utf-8"))
            template_gate = json.loads((project / "analysis/template_gate.json").read_text(encoding="utf-8"))

        self.assertEqual("cyberppt.dual_image.template_rebuild_readiness.v1", readiness["schema"])
        self.assertTrue(readiness["checks"]["template_rebuild_consumed"])
        self.assertTrue(readiness["checks"]["source_capture_consumed"])
        self.assertTrue(readiness["checks"]["template_gate_pass"])
        self.assertFalse(readiness["checks"]["source_capture_gate_pass"])
        self.assertFalse(readiness["checks"]["scene_graph_gate_pass"])
        self.assertEqual(0, readiness["checks"]["scene_graph_gate_pages"])
        self.assertEqual("scene_graph_rework_required", readiness["status"])
        self.assertEqual("cyberppt.dual_image.source_capture.v1", source_capture["schema"])
        self.assertEqual([2], [page["page_number"] for page in source_capture["pages"]])
        self.assertTrue(template_gate["valid"])

    def test_template_rebuild_passes_visual_registry_dir_to_source_capture(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            registry_dir = root / "registry"
            _write_template_project(project)
            _write_visual_registry(registry_dir, page_number=2)
            manifest = _write_pair_manifest(root, project)

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                    str(manifest),
                    "--skip-rebuild",
                    "--no-export",
                    "--visual-registry-dir",
                    str(registry_dir),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            readiness = json.loads((project / "analysis/template_rebuild_readiness.json").read_text(encoding="utf-8"))
            source_capture = json.loads((project / "analysis/source_capture.json").read_text(encoding="utf-8"))
            source_capture_gate = json.loads((project / "analysis/source_capture_gate.json").read_text(encoding="utf-8"))

        self.assertEqual(str(registry_dir.resolve()), readiness["visual_registry_dir"])
        self.assertEqual(str(registry_dir.resolve()), source_capture["inputs"]["visual_registry_dir"])
        self.assertEqual(1, source_capture["inputs"]["visual_registry_elements"])
        self.assertNotIn("non_text_visuals_not_individually_detected", source_capture_gate["gap_counts"])
        self.assertIn("render_delta_not_measured", source_capture_gate["gap_counts"])

    def test_rebuild_ingress_normalizes_full_and_background_to_1280_canvas(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            source_dir = root / "source"
            source_dir.mkdir()
            full = source_dir / "page_006_full.png"
            background = source_dir / "page_006_background.png"
            Image.new("RGB", (1672, 941), "#ffffff").save(full)
            Image.new("RGB", (1672, 941), "#f8fafc").save(background)

            prepared_full, prepared_background, image_size_check = _prepare_page_images(
                full_image=full,
                background_image=background,
                project_path=project,
            )

            with Image.open(prepared_full) as full_image, Image.open(prepared_background) as background_image:
                self.assertEqual((1280, 720), full_image.size)
                self.assertEqual((1280, 720), background_image.size)

        self.assertEqual([1672, 941], image_size_check["source_full_size"])
        self.assertEqual([1672, 941], image_size_check["source_background_size"])
        self.assertEqual([1280, 720], image_size_check["output_size"])
        self.assertEqual("normalized_1280x720", image_size_check["status"])
        self.assertIn("/normalized/", str(prepared_full))
        self.assertIn("/normalized/", str(prepared_background))


def _write_template_project(project: Path) -> None:
    (project / "templates").mkdir(parents=True)
    (project / "images").mkdir(parents=True)
    (project / "svg_output").mkdir(parents=True)
    (project / "analysis/ocr").mkdir(parents=True)
    (project / "analysis/semantic_containers").mkdir(parents=True)
    (project / "analysis/typography").mkdir(parents=True)

    (project / "spec_lock.md").write_text("# Spec Lock\n", encoding="utf-8")
    (project / "templates/brand_rules.json").write_text("{}\n", encoding="utf-8")
    (project / "templates/master_elements.svg").write_text("<svg></svg>\n", encoding="utf-8")
    (project / "svg_output/page_002.svg").write_text(
        '<svg><text x="100" y="120">核心结论</text></svg>\n',
        encoding="utf-8",
    )
    (project / "analysis/ocr/page_002_text_mapping.json").write_text(
        json.dumps(
            {
                "page_number": 2,
                "boxes": [
                    {
                        "text": "核心结论",
                        "x": 100,
                        "y": 90,
                        "w": 180,
                        "h": 32,
                        "font_size": 18,
                        "font_family": "Microsoft YaHei",
                        "fill": "#123B66",
                        "font_weight": "700",
                        "align": "left",
                        "word_wrap": False,
                        "source": "script_matched",
                        "confidence": 1.0,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "analysis/semantic_containers/page_002_containers.json").write_text(
        json.dumps(
            {
                "page_number": 2,
                "containers": [
                    {
                        "id": "title",
                        "role": "title",
                        "x": 90,
                        "y": 80,
                        "w": 300,
                        "h": 60,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "analysis/typography/page_002_typography.json").write_text(
        json.dumps(
            {"decisions": [{"text": "核心结论", "rendered_text": "核心结论", "role": "T2", "applied_px": 18}]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_pair_manifest(root: Path, project: Path) -> Path:
    image_dir = root / "images"
    image_dir.mkdir()
    full = image_dir / "page_002_full.png"
    background = image_dir / "page_002_background.png"
    full.write_bytes(b"fake-full")
    background.write_bytes(b"fake-background")
    manifest = {
        "mode": "cyberppt-dual-image-pair",
        "project_path": str(project),
        "source_script": str(root / "script.md"),
        "generation_contract": {
            "mode": "template-content-region",
            "rule": "Generate content-area images only; PPT title, subtitle and enterprise chrome are handled by template/export code.",
        },
        "pairs": [
            {
                "page_number": 2,
                "title": "核心结论",
                "full": {"filename": full.name, "path": str(full), "status": "Generated"},
                "background": {"filename": background.name, "path": str(background), "status": "Generated"},
            }
        ],
    }
    path = root / "page_image_pairs.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_visual_registry(registry_dir: Path, *, page_number: int) -> None:
    registry_dir.mkdir(parents=True)
    (registry_dir / f"slide-{page_number:02d}-visual-element-registry.json").write_text(
        json.dumps(
            {
                "schema": "cyberppt.visual_element_registry.v1",
                "elements": [
                    {
                        "element_id": "shape_title_marker",
                        "priority": "P1",
                        "element_type": "shape",
                        "source_component_id": "title_marker",
                        "blueprint_bbox_px": {"x": 88, "y": 74, "w": 12, "h": 58},
                        "ppt_target_bbox_in": {"x": 0.88, "y": 0.74, "w": 0.12, "h": 0.58},
                        "tolerance_px": 4,
                        "measurement_mode": "individual_bbox",
                        "render_bbox_px": None,
                        "delta_px": None,
                        "registration_status": "pending_render_measurement",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
