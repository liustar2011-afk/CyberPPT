from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cyberppt.image_enhancer import enhance_image, enhance_manifest_images


class ImageEnhancerBridgeTests(unittest.TestCase):
    def test_enhance_image_invokes_registered_entrypoint_and_reads_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "page.png"
            output = root / "result.png"
            source.write_bytes(b"source")

            def fake_run(command, **_kwargs):
                Path(command[command.index("--output") + 1]).write_bytes(b"enhanced")
                Path(command[command.index("--report") + 1]).write_text(
                    json.dumps({"super_resolution_backend": "builtin", "warnings": []}),
                    encoding="utf-8",
                )
                return type("Completed", (), {"returncode": 0})()

            with patch("cyberppt.image_enhancer.subprocess.run", side_effect=fake_run):
                result = enhance_image(source, output=output, backend="builtin")

        self.assertEqual(str(output.resolve()), result["output"])
        self.assertEqual("builtin", result["backend"])

    def test_manifest_outputs_are_promoted_without_overwriting_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "p04.png"
            source.write_bytes(b"source")
            manifest = {
                "pairs": [{"page_number": 4, "full": {"path": str(source), "status": "Generated"}}]
            }
            result = {
                "source": str(source),
                "output": str(source.parent / "enhanced" / "p04_enhanced.png"),
                "report": str(source.parent / "enhanced" / "p04_enhanced.png.report.json"),
                "backend": "builtin", "warnings": [], "command": [],
            }
            with patch("cyberppt.image_enhancer.enhance_image", return_value=result):
                summary = enhance_manifest_images(manifest, backend="builtin", scale=1.0)

        item = manifest["pairs"][0]["full"]
        self.assertEqual(result["output"], item["path"])
        self.assertEqual(str(source), item["enhancement"]["source_path"])
        self.assertEqual(1, len(summary["images"]))

    def test_exact_target_size_is_forwarded_to_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "page.png"
            source.write_bytes(b"source")

            def fake_run(command, **_kwargs):
                self.assertIn("2048x1024", command)
                source.write_bytes(b"enhanced")
                source.with_suffix(".png.report.json").write_text(
                    json.dumps({"super_resolution_backend": "builtin", "warnings": []}),
                    encoding="utf-8",
                )
                return type("Completed", (), {"returncode": 0})()

            with patch("cyberppt.image_enhancer.subprocess.run", side_effect=fake_run):
                enhance_image(source, output=source, target_size=(2048, 1024))

    def test_windows_unicode_paths_are_staged_through_ascii_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "建设基础.png"
            output = root / "合作方案.png"
            source.write_bytes(b"source")

            def fake_run(command, **_kwargs):
                run_source = Path(command[2])
                run_output = Path(command[command.index("--output") + 1])
                run_report = Path(command[command.index("--report") + 1])
                self.assertTrue(str(run_source).isascii())
                self.assertTrue(str(run_output).isascii())
                run_output.write_bytes(b"enhanced")
                run_report.write_text(
                    json.dumps({"super_resolution_backend": "builtin", "warnings": []}),
                    encoding="utf-8",
                )
                return type("Completed", (), {"returncode": 0})()

            with (
                patch("cyberppt.image_enhancer.sys.platform", "win32"),
                patch("cyberppt.image_enhancer.subprocess.run", side_effect=fake_run),
            ):
                result = enhance_image(source, output=output, backend="builtin")
            self.assertEqual(b"enhanced", output.read_bytes())
            self.assertEqual(str(output.resolve()), result["output"])
