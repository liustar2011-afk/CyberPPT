from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.dual_image_overlay.imagegen_handoff import (
    CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT,
    CONTENT_FIRST_ONSCREEN_STORY_CONTRACT,
    build_page_creative_brief,
    build_page_prompt,
    compile_page_prompt,
    diagnostic_onscreen_text,
)
from scripts.dual_image_overlay.prompt_diagnostics import analyze_prompt
from scripts.dual_image_overlay.style_library import write_project_style_lock


SCRIPT = """## 第18页：平台支撑与安全运行

- 页面类型：内容页
- 页面标题：平台支撑与安全运行
- 主判断：数据、模型、产品和安全能力共同支撑稳定业务运行。
- 上屏结论：统一底座让数据、模型、产品和安全能力共同支撑稳定运行
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


def test_default_compiler_is_content_first_and_legacy_requires_opt_in() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        implicit = build_page_prompt(page, lock, page_mission="平台如何稳定支撑业务")
        explicit = build_page_prompt(
            page,
            lock,
            page_mission="平台如何稳定支撑业务",
            prompt_compiler="content-first-v1",
        )
        legacy = build_page_prompt(
            page,
            lock,
            page_mission="平台如何稳定支撑业务",
            prompt_compiler="legacy",
        )
        implicit_compiled = compile_page_prompt(page, lock)
    assert implicit == explicit
    assert implicit != legacy
    assert "【完整内容语义｜仅供理解，不要求逐字上屏】" in implicit
    assert CONTENT_FIRST_ONSCREEN_STORY_CONTRACT in implicit
    assert "必须完整、准确、清晰地呈现，不得再次摘要、删减" in implicit
    assert "【事实与范围边界｜仅供约束，不上屏】" in implicit
    assert CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT in implicit
    assert "【视觉风格】" in implicit
    assert "象牙白 + 深蓝领导汇报" in implicit
    assert "style.selected_lock" in (
        implicit_compiled.build_metadata()["injected_rule_ids"]
    )


def test_content_first_uses_the_selected_style_lock_instead_of_fixed_colors() -> None:
    page = _page()
    with TemporaryDirectory() as red_directory, TemporaryDirectory() as purple_directory:
        red_lock = write_project_style_lock(
            project=Path(red_directory),
            style_id=1,
        )
        purple_lock = write_project_style_lock(
            project=Path(purple_directory),
            style_id=8,
        )
        red = compile_page_prompt(page, red_lock)
        purple = compile_page_prompt(page, purple_lock)

    assert "经典深红咨询风" in red.prompt
    assert "#8B1E1E" in red.prompt
    assert "#12355B" not in red.prompt
    assert "冷白灰 + 深紫" in purple.prompt
    assert "#4B2E83" in purple.prompt
    assert red.prompt != purple.prompt
    assert red.build_metadata()["style_selection"]["id"] == 1
    assert purple.build_metadata()["style_selection"]["id"] == 8
    assert "不预设页面构图与信息组织" in red.prompt
    assert "风格锁" not in red.prompt
    assert "后期叠字" not in red.prompt
    assert "可编辑文字层" not in red.prompt
    assert "ID 1" not in red.prompt
    assert "classic_red_consulting" not in red.prompt


def test_content_first_diagnostics_use_the_compiled_locked_text() -> None:
    page = _page()
    locked = diagnostic_onscreen_text(page)
    assert locked.startswith(page.onscreen_judgment)
    assert "**数据治理｜质量与授权**" in locked
    assert diagnostic_onscreen_text(page, "legacy") == page.onscreen_text


def test_content_first_prompt_places_visible_judgment_before_support_modules() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    required = prompt.split("【必须上屏文字】", 1)[1]
    assert required.index(page.onscreen_judgment) < required.index("数据治理")


def test_content_first_treats_visible_judgment_as_body_conclusion_without_font_sizes() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "第一段是正文区结论句，不是页面标题或副标题" in prompt
    assert "不得按页面标题样式处理" in prompt
    assert "不得与 PPT 模板层标题争夺视觉层级" in prompt
    assert "字号" not in prompt
    assert "1.6—1.8倍" not in prompt
    assert "1.25—1.4倍" not in prompt


def test_content_first_omits_tracking_metadata_and_avoids_repeated_rules() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【页面编码】" not in prompt
    assert "P18" not in prompt
    assert "以上仅用于按页追踪" not in prompt
    assert page.title not in prompt
    assert prompt.count("再次摘要、删减") == 1
    assert prompt.count("改变原意") == 1
    assert prompt.count("新增事实") == 1
    assert prompt.count("自主决定构图") == 1
    assert "页面构图和信息组织仍由" not in prompt


def test_content_first_scene_text_rule_does_not_hide_locked_names_or_numbers() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "本限制仅适用于插图内部的环境文字" in prompt
    assert "不适用于【必须上屏文字】" in prompt
    assert "必须上屏的组织名称、业务术语和数字仍须准确、清晰地呈现" in prompt


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
    assert "many-to-one support argument" not in (
        brief.semantic_contract.relationship_invariant
    )
    assert "must not degrade into unrelated peer modules" in (
        brief.semantic_contract.relationship_invariant
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
    assert "Auxiliary imagery may use clear supporting words" in prompt
    assert "does not need to duplicate the locked wording" in prompt
    assert "Every visual carrier must explain" not in prompt
    assert "Visual hierarchy:" not in prompt
    assert "Evidence bindings:" not in prompt
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
    assert "Auxiliary text may appear" in prompt
    assert "one-to-one mapping" in prompt
    assert "Do not generate any text, number, chart label" not in prompt


def test_foundation_relation_is_locked_as_many_to_one_without_prescribing_layout() -> None:
    page = _page()
    brief = build_page_creative_brief(
        page,
        "现有基础如何支撑稳定业务运行",
        override={"visual_intent_type": "multi_semantic_foundation"},
    )

    invariant = brief.semantic_contract.relationship_invariant
    assert "many-to-one support argument" in invariant
    assert "all 3 required meanings" in invariant
    assert "single core judgment" in invariant
    assert "not a required diagram layout" in invariant


def test_creative_prompt_cleans_full_image_legacy_language_globally() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(
            page,
            lock,
            page_mission="平台如何稳定支撑业务",
            prompt_compiler="creative-brief-v1",
        )

    assert "editable text layer only" not in prompt
    assert "Do not introduce organization or person names beyond" in prompt
    assert "Generic, non-location-specific facilities" not in prompt
    assert "supporting labels may organize the composition freely" in prompt
    assert "不要求沿用原始列表、卡片、栏位或段落排布形式" in prompt
    assert "整体构图、视觉隐喻和辅助表达均可自由发挥" in prompt
    assert "equal cards, equal columns, or equal stacked sections" not in prompt
