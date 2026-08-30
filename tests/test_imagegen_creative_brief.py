from __future__ import annotations

from tests._imagegen_creative_brief_base import *
from tests import _imagegen_creative_brief_base as _base
from scripts.imagegen_pipeline.runtime_style_contract import load_runtime_style_contract


def test_content_first_treats_visible_judgment_as_body_conclusion_with_style_typography_lock() -> None:
    page = _base.replace(_base._page(), onscreen_judgment_mode="locked")
    with _base.TemporaryDirectory() as directory:
        lock = _base.write_project_style_lock(project=_base.Path(directory), style_id=9)
        prompt = _base.build_page_prompt(page, lock)
        style_contract = _base.json.loads(lock.read_text(encoding="utf-8"))["style"][
            "prompt_contract"
        ]
        runtime = load_runtime_style_contract(lock)

    assert "如【锁定关键文字】含正文结论句" in prompt
    assert "不得通栏放大" in prompt
    assert "标题竖线、横线等装饰" in prompt

    hierarchy_lock = (
        "Create hierarchy through crop, overlap, scale contrast, tonal separation, "
        "alignment, deep-blue emphasis and shallow foreground–background relationships."
    )
    assert style_contract.count(hierarchy_lock) == 1
    assert prompt.count(hierarchy_lock) == 1

    terminal = runtime.terminal_lock.strip()
    assert terminal
    assert prompt.rstrip().endswith(terminal)
    assert prompt.count("【最终视觉执行约束｜最高优先级】") == 1

    assert "1.6—1.8倍" not in prompt
    assert "1.25—1.4倍" not in prompt
