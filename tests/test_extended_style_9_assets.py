from __future__ import annotations
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_style_nine_sample_and_reference_are_available() -> None:
    sample = ROOT / "assets" / "palette-samples" / "palette-09.png"
    reference = (ROOT / "references" / "visual-system.md").read_text(encoding="utf-8")

    assert sample.exists()
    with Image.open(sample) as image:
        assert abs(image.width / image.height - 16 / 9) < 0.01
    assert "扩展风格9：象牙白 + 深蓝领导汇报" in reference
    assert "默认8种风格仍保持1—8不变" in reference
    assert "演讲辅助" in reference
    assert "实景彩色插画" in reference
    assert "Visual logic" in reference
    assert "business capability logic" in reference
    assert "Style 9 people-expression constraint" in reference
    assert "People are supporting contextual elements only" in reference
