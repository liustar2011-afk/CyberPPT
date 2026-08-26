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
    # references/visual-system.md's Style 09 section was simplified again
    # 2026-08-18 (background moved from ivory to pure white, and the locked
    # Chinese text rule loosened into a content-fidelity + verbatim-text
    # contract); this checks the section's actual current title and key
    # scene-led/terminal properties, not a stale draft's exact wording.
    assert "扩展风格9：纯白 + 深蓝领导汇报" in reference
    assert "默认8种风格仍保持1—8不变" in reference
    assert "#FFFFFF" in style09
    assert "#12355B" in style09
    assert "semantic scene-led editorial business-report style" in style09
    assert "最终执行锁" in style09
    terminal_lock = style09.split("【风格09最终执行锁｜最高优先级】", 1)[1]
    assert "make glyphs visibly wider and flatter" in terminal_lock
    assert "legibility at small sizes" in terminal_lock
    assert "Typography: establish one clear hierarchy" in terminal_lock
    assert "page title or main conclusion the largest text" in terminal_lock
    assert "sources, notes and evidence codes the smallest" in terminal_lock
