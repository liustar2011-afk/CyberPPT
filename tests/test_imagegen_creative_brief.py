from __future__ import annotations

from tests._imagegen_creative_brief_base import *
from tests import _imagegen_creative_brief_base as _base
from scripts.imagegen_pipeline.runtime_style_contract import load_runtime_style_contract
from script_engine.render import render_stage02_markdown
import pytest


@pytest.mark.parametrize("text_render_mode", ["full_image", "semantic_visual"])
def test_stage01_full_copy_is_nonvisible_imagegen_context(text_render_mode: str) -> None:
    full_copy = "平台提供数据服务。\n\n内部补充条件仅供理解，不作为展示文案。"
    markdown = render_stage02_markdown({"slides": [{
        "id": "P01", "title": "数据服务", "page_type": "content",
        "full_copy": full_copy,
        "onscreen": [{"heading": "平台服务", "items": ["平台提供数据服务。"]}],
    }]})
    page = _base.parse_script_markdown(markdown).pages[0]
    assert page.full_prose == full_copy
    with _base.TemporaryDirectory() as directory:
        lock = _base.write_project_style_lock(project=_base.Path(directory), style_id=9)
        compiled = _base.compile_page_prompt(page, lock, text_render_mode=text_render_mode)
    assert compiled.prompt.count(full_copy) == 1
    context = compiled.prompt.split("【完整文字稿（不上屏）】", 1)[1]
    assert full_copy in context.split("【", 1)[0]
    assert "不得将本段直接排版或改写为额外上屏文案" in context
    assert "内部补充条件" not in compiled.editable_body_text
    assert "平台提供数据服务。" in compiled.editable_body_text
    assert "内部补充条件" not in compiled.image_locked_text
    if text_render_mode == "full_image":
        assert "内部补充条件" not in compiled.prompt.split("【页面内容素材｜允许提炼、改写、重组】", 1)[1]


def test_missing_full_copy_omits_nonvisible_context_section() -> None:
    page = _base.replace(_base._page(), full_prose="")
    with _base.TemporaryDirectory() as directory:
        lock = _base.write_project_style_lock(project=_base.Path(directory), style_id=9)
        prompt = _base.build_page_prompt(page, lock)
    assert "【完整文字稿（不上屏）】" not in prompt


def test_content_first_treats_visible_judgment_as_body_conclusion_with_style_typography_lock() -> None:
    page = _base.replace(_base._page(), onscreen_judgment_mode="locked")
    with _base.TemporaryDirectory() as directory:
        lock = _base.write_project_style_lock(project=_base.Path(directory), style_id=9)
        prompt = _base.build_page_prompt(page, lock)
        style_contract = _base.json.loads(lock.read_text(encoding="utf-8"))["style"][
            "prompt_contract"
        ]
        runtime = load_runtime_style_contract(lock)

    assert "【结论句要求｜不上屏】" in prompt
    assert "结论先行、层级清晰" in prompt
    assert "不得新增事实" in prompt
    assert "第一眼必须识别正文主焦点" in style_contract
    assert prompt.count("第一眼必须识别正文主焦点") == 1

    terminal = runtime.terminal_lock.strip()
    assert terminal
    assert prompt.rstrip().endswith(terminal)
    assert prompt.count("【最终视觉执行约束｜最高优先级】") == 1

    assert "1.6—1.8倍" not in prompt
    assert "1.25—1.4倍" not in prompt
