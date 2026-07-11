from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "scripts" / "dual_image_overlay" / "rebuild_engine"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

from scripts.dual_image_overlay.rebuild_engine import paddleocr_local  # noqa: E402


def test_adapter_maps_rec_boxes_and_scores(monkeypatch, tmp_path):
    image = tmp_path / "page.png"
    Image.new("RGB", (1000, 700), "white").save(image)
    monkeypatch.setattr(paddleocr_local, "_invoke_runtime", lambda **_: {
        "rec_texts": ["经营管理能力"], "rec_scores": [0.98],
        "rec_boxes": [[112, 237, 418, 276]],
        "dt_polys": [[[112, 237], [418, 237], [418, 276], [112, 276]]],
    })
    result = paddleocr_local.run_local_ocr(image, runtime_dir=tmp_path)
    assert result["items"][0]["text"] == "经营管理能力"
    assert result["items"][0]["bbox"] == [112.0, 237.0, 418.0, 276.0]
    assert result["items"][0]["confidence"] == 0.98


def test_adapter_clips_and_rejects_invalid_boxes(monkeypatch, tmp_path):
    image = tmp_path / "page.png"
    Image.new("RGB", (100, 80), "white").save(image)
    monkeypatch.setattr(paddleocr_local, "_invoke_runtime", lambda **_: {
        "rec_texts": ["clip", "bad"], "rec_scores": [0.8, 0.2],
        "rec_boxes": [[-5, -2, 120, 90], [20, 20, 10, 30]],
    })
    result = paddleocr_local.run_local_ocr(image, runtime_dir=tmp_path)
    assert result["items"][0]["bbox"] == [0.0, 0.0, 100.0, 80.0]
    assert len(result["items"]) == 1
