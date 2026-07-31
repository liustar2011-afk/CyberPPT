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
    assert "风格只决定页面的视觉气质" in reference
    assert "抽象主题，优先采用二维编辑结构" in reference
    assert "场景、照片或编辑式行业插画是条件性载体" in reference
    assert "不得默认使用档案柜、文件夹、牛皮纸" in reference
    assert "默认采用“编辑排版型”媒介" in reference
    assert "不默认绘制节点、链路、箭头、光束或技术面板" in reference
