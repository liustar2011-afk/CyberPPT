from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.dual_image_overlay.imagegen_handoff import (
    build_page_creative_brief,
    build_page_prompt,
    compile_page_prompt,
)
from scripts.dual_image_overlay.prompt_diagnostics import analyze_prompt
from scripts.dual_image_overlay.style_library import write_project_style_lock


SCRIPT = """## 第18页：平台支撑与安全运行

- 页面类型：内容页
- 页面标题：平台支撑与安全运行
- 主判断：数据、模型、产品和安全能力共同支撑稳定业务运行。
- 上屏文字：

  **数据治理｜质量与授权**
  - 2025年完成率 95%，形成稳定、可追溯的数据输入。
  **模型生产｜验证与复盘**
  - 保持滚动验证和误差复盘。
  **安全运行｜权限与日志**
  - 权限、日志和发布审核共同保障运行——不得省略。
"""


def _page():
    return parse_script_markdown(SCRIPT).pages[0]


def test_default_compiler_remains_byte_identical_to_explicit_legacy() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        implicit = build_page_prompt(page, lock, page_mission="平台如何稳定支撑业务")
        explicit = build_page_prompt(
            page,
            lock,
            page_mission="平台如何稳定支撑业务",
            prompt_compiler="legacy",
        )
    assert implicit == explicit


def test_creative_brief_preserves_semantics_but_does_not_prescribe_layout() -> None:
    page = _page()
    brief = build_page_creative_brief(
        page,
        "平台如何稳定支撑业务",
        override={"visual_intent_type": "capability_relationship"},
    )

    assert brief.relation == "capability_relationship"
    assert brief.semantic_contract.core_judgment == page.main_message
    assert brief.semantic_contract.required_meanings == (
        "数据治理｜质量与授权",
        "模型生产｜验证与复盘",
        "安全运行｜权限与日志",
    )
    assert "2025年" in brief.semantic_contract.exact_facts
    assert "95%" in brief.semantic_contract.exact_facts
    assert len(brief.page_specific_avoids) <= 2
    assert brief.source_composition_reference == ""
    assert "No diagram topology or panel arrangement is prescribed" in (
        brief.freedom.composition
    )


def test_creative_compiler_uses_existing_prompt_path_and_clears_known_conflicts() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(
            page,
            lock,
            page_mission="平台如何稳定支撑业务",
            visual_intent_override={
                "visual_intent_type": "capability_relationship"
            },
            prompt_compiler="creative-brief-v1",
        )

    prompt = compiled.prompt
    metrics = analyze_prompt(prompt, onscreen_text=page.onscreen_text)
    assert "[Page-specific creative brief" in prompt
    assert "Recommended composition:" not in prompt
    assert "Selected visual intent type:" not in prompt
    assert page.main_message in prompt
    assert "2025年完成率 95%" in prompt
    assert "共同保障运行——不得省略" in prompt
    assert "remain editable" not in prompt
    assert "Auxiliary semantic imagery may use" not in prompt
    assert metrics.conflicts == ()
    assert metrics.locked_text_preserved is True
    assert metrics.exact_facts_preserved is True
    assert compiled.build_metadata()["compiler_version"] == "creative-brief-v1"
    assert compiled.build_metadata()["creative_brief"]["relation"] == (
        "capability_relationship"
    )


def test_creative_brief_is_included_for_compact_style_contract() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=10)
        prompt = build_page_prompt(
            page,
            lock,
            page_mission="平台如何稳定支撑业务",
            prompt_compiler="creative-brief-v1",
        )

    assert "[Page-specific creative brief" in prompt
    assert "【视觉组织原则】" in prompt
    assert "Do not generate any text, number, chart label" in prompt
