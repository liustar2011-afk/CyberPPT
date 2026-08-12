from __future__ import annotations
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_style_nine_sample_and_reference_are_available() -> None:
    sample = ROOT / "assets" / "palette-samples" / "palette-09.png"
    reference = (ROOT / "references" / "visual-system.md").read_text(encoding="utf-8")
    style09 = reference.split("## 扩展风格9：", 1)[1].split("## 扩展风格10：", 1)[0]

    assert sample.exists()
    with Image.open(sample) as image:
        ratio = image.width / image.height
        assert abs(ratio - 16 / 9) < 0.01 or abs(ratio - 2.0) < 0.01
    assert "扩展风格9：纯白 + 深蓝领导汇报" in reference
    assert "默认8种风格仍保持1—8不变" in reference
    assert "#FFFFFF" in style09
    assert "#12355B" in style09
    assert "连接只表达真实关系并保持细、小、从属" in style09
    assert "保持扁平2D、无图标优先和克制政企气质" in style09
