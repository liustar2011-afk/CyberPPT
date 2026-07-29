from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.dual_image_overlay.imagegen_handoff import (
    CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT,
    CONTENT_FIRST_ONSCREEN_STORY_CONTRACT,
    build_page_creative_brief,
    build_page_prompt,
    compile_page_prompt,
    diagnostic_onscreen_text,
    select_page_visual_intent_type,
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
    assert "【完整内容语义｜仅供理解，不要求逐字上屏】" not in implicit
    assert CONTENT_FIRST_ONSCREEN_STORY_CONTRACT in implicit
    assert "不得新增、摘要、删减或改写" in implicit
    assert "【事实与范围边界｜仅供约束，不上屏】" not in implicit
    assert CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT in implicit
    assert "【输出与风格｜不上屏】" in implicit
    assert "象牙白 + 深蓝领导汇报" not in implicit
    assert "风格适用语境" not in implicit
    assert "风格约定（仅约束视觉表达，不覆盖本页内容与主导关系）" not in implicit
    assert "【页面逻辑｜不上屏】" in implicit
    assert "不使用等权卡片、通用图标流程或逐项配图" in implicit
    assert "Do not show frontal faces" not in implicit
    assert "段落正文留在 PPT 可编辑文字层" not in implicit
    assert "现代中文高端政企汇报设计气质" in implicit
    assert "style.selected_lock" in (
        implicit_compiled.build_metadata()["injected_rule_ids"]
    )
    assert (
        implicit_compiled.build_metadata()["style_selection"]["name"]
        == "象牙白 + 深蓝领导汇报"
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

    assert "经典深红咨询风" not in red.prompt
    assert "#8B1E1E" in red.prompt
    assert "#12355B" not in red.prompt
    assert "冷白灰 + 深紫" not in purple.prompt
    assert "#4B2E83" in purple.prompt
    assert red.prompt != purple.prompt
    assert red.build_metadata()["style_selection"]["id"] == 1
    assert purple.build_metadata()["style_selection"]["id"] == 8
    assert red.build_metadata()["style_selection"]["name"] == "经典深红咨询风"
    assert purple.build_metadata()["style_selection"]["name"] == "冷白灰 + 深紫"
    assert "现代中文高端政企汇报设计气质" in red.prompt
    assert "不预设页面构图与信息组织" not in red.prompt
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


def test_content_first_rejects_content_page_without_visible_judgment() -> None:
    page = replace(_page(), onscreen_judgment="")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        with pytest.raises(ValueError, match="missing 上屏结论"):
            build_page_prompt(page, lock)


def test_content_first_treats_visible_judgment_as_body_conclusion_without_font_sizes() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "第一段是正文结论句，不是页面标题" in prompt
    assert "不得通栏放大" in prompt
    assert "标题竖线、横线等装饰" in prompt
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
    assert prompt.count("不得新增、摘要、删减或改写") == 1
    assert prompt.count("【页面逻辑｜不上屏】") == 1
    assert prompt.count("以【页面逻辑】组织空间") == 1
    assert "页面构图和信息组织仍由" not in prompt


def test_content_first_text_rule_keeps_locked_names_and_numbers_authoritative() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "只允许出现【必须上屏文字】中的文字" in prompt
    assert "模块名称、数字、单位和业务术语必须准确" in prompt


def test_content_first_uses_the_compact_visual_wording() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【页面逻辑｜不上屏】" in prompt
    assert "主导关系：" in prompt
    assert "视觉证明：" in prompt
    assert "空间组织：" in prompt
    assert "本页避免：" in prompt
    assert prompt.count("视觉证明：") == 1


def test_visual_proof_prefers_page_context_and_new_relations_are_selectable() -> None:
    page = _page()
    assert select_page_visual_intent_type(
        page,
        "建设对象与专业系统的职责边界是什么",
    ) == "boundary_guardrail"
    assert select_page_visual_intent_type(
        page,
        "五层能力如何形成上下依赖和可信底座",
    ) == "hierarchy_support"
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(
            page,
            lock,
            visual_context={"visual_proof": "用共同底座托住业务结果"},
        )
    assert "视觉证明：用共同底座托住业务结果" in prompt
    assert prompt.count("视觉证明：") == 1
    assert "不使用等权卡片、通用图标流程或逐项配图" in prompt
    assert "如出现人物，仅使用远景、背影或局部" in prompt


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
