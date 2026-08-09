from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ppt_image_enhancer.config import load_config
from ppt_image_enhancer.pipeline import enhance


def test_enhance_supports_windows_unicode_paths(tmp_path: Path) -> None:
    source = tmp_path / "第002页_蓝图.png"
    output = tmp_path / "第002页_增强.png"
    image = np.full((90, 180, 3), (80, 40, 20), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    encoded.tofile(str(source))
    cfg = load_config("chart_heavy")
    cfg["output"]["target_width"] = 360
    cfg["output"]["target_height"] = 180
    cfg["super_resolution"]["backend"] = "builtin"

    report = enhance(source, output, cfg)

    assert output.is_file()
    assert report["after"]["width"] == 360
    assert report["after"]["height"] == 180
