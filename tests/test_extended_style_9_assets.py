from __future__ import annotations
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_style_nine_sample_and_reference_are_available() -> None:
    sample = ROOT / "assets" / "palette-samples" / "palette-09.png"
    reference = (ROOT / "references" / "visual-system.md").read_text(encoding="utf-8")
    style09 = reference.split("## 扩展风格10：")[0]

    assert sample.exists()
    with Image.open(sample) as image:
        ratio = image.width / image.height
        assert abs(ratio - 16 / 9) < 0.01 or abs(ratio - 2.0) < 0.01
    assert "扩展风格9：象牙白 + 深蓝领导汇报" in reference
    assert "默认8种风格仍保持1—8不变" in reference
    assert "#F7F6F0" in style09
    assert "#12355B" in style09
    assert "基础组件表达规范（通用）" in style09
    assert "线条" in style09 and "虚线不作装饰节点链" in style09
    assert "边框" in style09 and "禁止胶囊" in style09
    assert "箭头" in style09 and "禁止宽箭头带" in style09
    assert "形状" in style09 and "低矮、哑光、正视" in style09
