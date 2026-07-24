from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dual_image_overlay.deliverable_prompt import PageBlock, render_prompt
from scripts.dual_image_overlay.style_library import write_project_style_lock
from scripts.dual_image_overlay.visual_grammar import default_visual_grammar


def test_open_visual_grammar_allows_expression_with_business_boundaries() -> None:
    contract = default_visual_grammar()

    assert "文字框、标签、卡片、侧栏、色块和分区" in contract.container_rule
    assert "明确的业务语义" in contract.container_rule
    assert "细线、色带、渐变、光流、空间轨迹或轻微立体效果" in contract.connector_rule
    assert "不得穿过、遮挡或托载正文文字" in contract.connector_rule
    assert "干净、稳定、对比充足" in contract.image_text_rule
    assert "不同层级不得被处理成完全等权" in contract.hierarchy_rule


def test_deliverable_prompt_renders_visual_grammar_once_for_style_nine() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = render_prompt(
            PageBlock(page_number=9, title="测试", text="组件A：业务内容"),
            style_lock_path=lock,
        )

    assert prompt.count("【视觉组织原则】") == 1
    assert "允许使用文字框、标签、卡片、侧栏、色块和分区" in prompt
    assert "不得穿过、遮挡或托载正文文字" in prompt
