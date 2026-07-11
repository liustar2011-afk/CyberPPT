from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REBUILD_ENGINE_DIR = ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"
if str(REBUILD_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(REBUILD_ENGINE_DIR))

from scripts.dual_image_overlay.rebuild_engine import ocr_text_locator  # noqa: E402


def _payload(*texts: str) -> str:
    import json

    return json.dumps(
        {
            "image_size": {"width": 1672, "height": 941},
            "items": [
                {"text": text, "bbox": [10.0 + index, 10.0, 100.0 + index, 30.0], "confidence": 0.9}
                for index, text in enumerate(texts)
            ],
        }
    )


class OcrTextLocatorTests(unittest.TestCase):
    def test_transient_network_error_is_retried_and_recovers(self) -> None:
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "full.png"
            Image.new("RGB", (1672, 941), "#ffffff").save(image_path)

            calls = {"count": 0}

            def flaky(**_kwargs: object) -> str:
                calls["count"] += 1
                if calls["count"] == 1:
                    raise RuntimeError("SSL: UNEXPECTED_EOF_WHILE_READING")
                return _payload("一", "二")

            with patch.object(ocr_text_locator, "run_codex_vision_text", side_effect=flaky), \
                    patch.object(ocr_text_locator.time, "sleep", return_value=None):
                layout = ocr_text_locator.locate_text(image_path, backend="vision-json")

        self.assertEqual(calls["count"], 2)
        self.assertEqual(len(layout["items"]), 2)

    def test_gives_up_after_exhausting_transient_retries(self) -> None:
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "full.png"
            Image.new("RGB", (1672, 941), "#ffffff").save(image_path)

            def always_fails(**_kwargs: object) -> str:
                raise RuntimeError("SSL: UNEXPECTED_EOF_WHILE_READING")

            with patch.object(ocr_text_locator, "run_codex_vision_text", side_effect=always_fails), \
                    patch.object(ocr_text_locator.time, "sleep", return_value=None):
                with self.assertRaises(RuntimeError):
                    ocr_text_locator.locate_text(image_path, backend="vision-json")

    def test_resamples_when_item_count_looks_under_detected(self) -> None:
        # Reproduces the real defect: one OCR call merges four bullet lines
        # into a single blob (1 item), a second call separates them properly
        # (4 items). With a min_expected_items floor, the under-detected first
        # attempt should trigger a resample and the better attempt should win.
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "full.png"
            Image.new("RGB", (1672, 941), "#ffffff").save(image_path)

            responses = [
                _payload("经营管理数据项目执行数据合同订单数据绩效与指标数据"),
                _payload("经营管理数据", "项目执行数据", "合同订单数据", "绩效与指标数据"),
            ]

            with patch.object(ocr_text_locator, "run_codex_vision_text", side_effect=responses), \
                    patch.object(ocr_text_locator.time, "sleep", return_value=None):
                layout = ocr_text_locator.locate_text(
                    image_path,
                    backend="vision-json",
                    min_expected_items=3,
                )

        self.assertEqual(len(layout["items"]), 4)
        self.assertEqual(layout["quality_retry_attempts"], 2)

    def test_does_not_resample_when_no_expectation_given(self) -> None:
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "full.png"
            Image.new("RGB", (1672, 941), "#ffffff").save(image_path)

            calls = {"count": 0}

            def respond(**_kwargs: object) -> str:
                calls["count"] += 1
                return _payload("单独一段合并文字")

            with patch.object(ocr_text_locator, "run_codex_vision_text", side_effect=respond):
                layout = ocr_text_locator.locate_text(image_path, backend="vision-json")

        self.assertEqual(calls["count"], 1)
        self.assertNotIn("quality_retry_attempts", layout)
        self.assertEqual(len(layout["items"]), 1)

    def test_stops_resampling_once_expected_count_is_met(self) -> None:
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "full.png"
            Image.new("RGB", (1672, 941), "#ffffff").save(image_path)

            calls = {"count": 0}

            def respond(**_kwargs: object) -> str:
                calls["count"] += 1
                return _payload("一", "二", "三")

            with patch.object(ocr_text_locator, "run_codex_vision_text", side_effect=respond):
                layout = ocr_text_locator.locate_text(
                    image_path,
                    backend="vision-json",
                    min_expected_items=3,
                )

        self.assertEqual(calls["count"], 1)
        self.assertEqual(len(layout["items"]), 3)

    def test_local_backend_does_not_call_remote_vision(self) -> None:
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "full.png"
            Image.new("RGB", (100, 80), "#ffffff").save(image_path)
            with patch.object(ocr_text_locator, "run_codex_vision_text", side_effect=AssertionError("remote called")), \
                    patch.object(ocr_text_locator, "run_local_ocr", return_value={
                        "image_size": {"width": 100, "height": 80}, "items": [], "raw_items": [],
                        "backend": "paddleocr-local", "runtime": directory,
                    }):
                layout = ocr_text_locator.locate_text(image_path, backend="paddleocr-local")
        self.assertEqual(layout["items"], [])


if __name__ == "__main__":
    unittest.main()
