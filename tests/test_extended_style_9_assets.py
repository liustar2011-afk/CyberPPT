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
        assert image.size == (2048, 1024)
        assert abs(ratio - 2.0) < 0.01
    assert "扩展风格9：纯白 + 深蓝领导汇报" in reference
    assert "默认8种风格仍保持1—8不变" in reference
    assert "#FFFFFF" in style09
    assert "#12355B" in style09
    assert "semantic editorial executive-report style" in style09
    assert "Treat those declarations as the only content truth" in style09
    assert "Let genuinely parallel content receive equal visual treatment" in style09
    assert "最终执行锁" in style09
    terminal_lock = style09.split("【风格09最终执行锁｜最高优先级】", 1)[1]
    assert "精确上屏文字、事实边界和业务关系" in terminal_lock
    assert "真实并列项可以等权处理" in terminal_lock
    assert "参考图只提供色板、线条工艺、留白节奏和整体克制度" in terminal_lock
