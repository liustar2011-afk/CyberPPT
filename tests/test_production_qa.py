from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from cyberppt.commands.production_qa import validate_assembly_bundle


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _write_minimal_pptx(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("ppt/slides/slide1.xml", "<p:sld/>")
        archive.writestr("ppt/notesSlides/notesSlide1.xml", "<p:notes/>")
    return path


class ProductionQaTests(unittest.TestCase):
    def test_validates_complete_approved_assembly_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            full = (root / "page_001_full.png")
            full.write_bytes(b"approved-image")
            template_manifest = _write_json(
                root / "template_image_manifest.json",
                {"tasks": [{"page_number": 1, "image_path": str(full), "notes_text": "approved notes"}]},
            )
            pptx = _write_minimal_pptx(root / "assembled.pptx")

            report = validate_assembly_bundle(
                {
                    "project": str(root),
                    "exported_pptx": str(pptx),
                    "template_image_manifest": str(template_manifest),
                    "approved_images": {1: str(full)},
                },
                [1],
            )

        self.assertTrue(report["valid"])
        self.assertTrue(report["checks"]["pptx_readable"])
        self.assertTrue(report["checks"]["notes_complete"])

    def test_rejects_assembly_bundle_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            outside = Path(directory) / "outside.pptx"
            _write_minimal_pptx(outside)

            report = validate_assembly_bundle(
                {
                    "project": str(root),
                    "exported_pptx": str(outside),
                    "template_image_manifest": str(outside),
                    "approved_images": {},
                },
                [1],
            )

        self.assertFalse(report["valid"])
        self.assertIn("output_outside_project", report["failures"])


if __name__ == "__main__":
    unittest.main()
