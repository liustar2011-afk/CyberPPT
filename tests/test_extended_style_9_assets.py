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
    assert "连接关系保持少量、纤细、清楚并避开文字" in style09
    assert "保持纯白底、深蓝主关系、平面2D信息结构和无图标优先" in style09
