from __future__ import annotations
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_style_nine_sample_and_reference_are_available() -> None:
    sample = ROOT / "assets" / "palette-samples" / "palette-09.png"
    reference = (ROOT / "references" / "visual-system.md").read_text(encoding="utf-8")

    assert sample.exists()
    with Image.open(sample) as image:
        ratio = image.width / image.height
        # Palette sample may be 16:9 (slide) or 2:1 (ImageGen canvas).
        assert abs(ratio - 16 / 9) < 0.01 or abs(ratio - 2.0) < 0.01
    assert "扩展风格9：象牙白 + 深蓝领导汇报" in reference
    assert "默认8种风格仍保持1—8不变" in reference
    assert "演讲辅助" in reference
    assert "风格只约束气质" in reference
    assert "抽象主题" in reference
    assert "精细中文排版" in reference
    assert "场景是条件性辅助层" in reference
    assert "档案柜、文件夹、牛皮纸" in reference
    assert "气质归风格，媒介归页面语义" in reference
