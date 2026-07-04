from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.commands.script_runner import script_path


ROOT = Path(__file__).resolve().parents[1]


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
                    "--skip-vendor-rebuild",
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
        self.assertEqual("source_capture_rework_required", readiness["status"])
        self.assertEqual("cyberppt.dual_image.source_capture.v1", source_capture["schema"])
        self.assertEqual([2], [page["page_number"] for page in source_capture["pages"]])
        self.assertTrue(template_gate["valid"])


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


if __name__ == "__main__":
    unittest.main()
