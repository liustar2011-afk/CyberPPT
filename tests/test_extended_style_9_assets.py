from __future__ import annotations
from pathlib import Path

from PIL import Image

from scripts.imagegen_pipeline.style_library import resolve_default_style


ROOT = Path(__file__).resolve().parents[1]


def test_style_nine_sample_is_available_and_matches_runtime_registry() -> None:
    style = resolve_default_style(style_id=9)
    sample = ROOT / style["sample"]

    assert style["name"] == "纯白 + 深蓝领导汇报"
    assert style["colors"]["background"] == "#FFFFFF"
    assert style["colors"]["accent"] == "#12355B"
    assert style["colors"]["secondary_accent"] == "#D9772B"
    assert sample == ROOT / "assets" / "palette-samples" / "palette-09.png"
    assert sample.exists()
    with Image.open(sample) as image:
        ratio = image.width / image.height
        assert image.size == (2048, 1024)
        assert abs(ratio - 2.0) < 0.01
