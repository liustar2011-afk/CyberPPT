from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "ppt_master_dual_image"


class DualImageVendorAssetsTest(unittest.TestCase):
    def test_vendor_manifest_required_files_exist(self) -> None:
        manifest_path = VENDOR / "vendor_manifest.json"
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        missing = [
            path
            for path in manifest["required_files"]
            if not (VENDOR / path).is_file()
        ]

        self.assertEqual([], missing)

    def test_vendor_snapshot_excludes_transient_files(self) -> None:
        forbidden_names = {".DS_Store", ".uuid.LCK"}
        forbidden_parts = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".venv",
            "projects",
            "exports",
            "qa_pdf",
        }
        offenders = []

        for path in VENDOR.rglob("*"):
            relative = path.relative_to(VENDOR)
            if path.name in forbidden_names:
                offenders.append(str(path.relative_to(ROOT)))
            if any(part in forbidden_parts for part in relative.parts):
                offenders.append(str(path.relative_to(ROOT)))
            if path.name.startswith(".uuid.TMP-"):
                offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual([], offenders)

    def test_formal_runtime_does_not_import_vendor_modules(self) -> None:
        runtime = ROOT / "scripts" / "dual_image_overlay"
        if not runtime.exists():
            return

        offenders = []
        for path in runtime.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if (
                "/Volumes/DOC/ppt-master" in text
                or "vendor.ppt_master_dual_image" in text
                or "vendor/ppt_master_dual_image" in text
            ):
                offenders.append(str(path.relative_to(ROOT)))

        for path in runtime.rglob("*.mjs"):
            text = path.read_text(encoding="utf-8")
            if (
                "/Volumes/DOC/ppt-master" in text
                or "vendor.ppt_master_dual_image" in text
                or "vendor/ppt_master_dual_image" in text
            ):
                offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
