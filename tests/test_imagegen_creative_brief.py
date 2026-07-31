from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import json

import pytest

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.dual_image_overlay.imagegen_handoff import (
    CONTENT_FIRST_ONSCREEN_STORY_CONTRACT,
    CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT,
    CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT,
    build_page_creative_brief,
    build_page_prompt,
    compile_page_prompt,
    diagnostic_onscreen_text,
    locked_onscreen_text,
    PresentationDecision,
    resolve_presentation_decision,
    resolve_onscreen_judgment_mode,
    select_image_locked_text,
    select_page_visual_intent_type,
)
from scripts.dual_image_overlay.prompt_diagnostics import analyze_prompt
from scripts.dual_image_overlay.style_library import write_project_style_lock
from scripts.dual_image_overlay.visual_grammar import creative_brief_visual_grammar


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


def test_presentation_decision_honors_explicit_page_values() -> None:
    page = replace(_page(), layout_motif="process_atlas", scene_role="no_scene")
    decision = resolve_presentation_decision(page, "phase")
    assert decision.layout_motif == "process_atlas"
    assert decision.scene_role == "no_scene"
    assert decision.source == "script"


def test_presentation_decision_ignores_adjacent_motif() -> None:
    page = _page()
    first = resolve_presentation_decision(page, "capability_relationship")
    second = resolve_presentation_decision(page, "capability_relationship", (first,))
    assert first.layout_motif == second.layout_motif


def test_presentation_decision_ignores_recent_scene_density() -> None:
    page = _page()
    prior = (
        PresentationDecision("control_room_bridge", "primary_scene", "auto", ""),
        PresentationDecision("evidence_landscape", "primary_scene", "auto", ""),
    )
    decision = resolve_presentation_decision(page, "closed_loop", prior)
    assert decision.scene_role == "primary_scene"


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
    assert "【完整上屏内容】均需进入 full 图" not in implicit
    assert "使用生成式图形形态、路径、层次和必要画面组织附近文字与业务关系" not in implicit
    assert "【事实与范围边界｜仅供约束，不上屏】" not in implicit
    assert "【内容与视觉要求｜不上屏】" not in implicit
    assert "【输出与风格｜不上屏】" in implicit
    assert "扩展风格9：象牙白 + 深蓝领导汇报" in implicit
    assert "风格适用语境" not in implicit
    assert "风格约定（仅约束视觉表达，不覆盖本页内容与主导关系）" not in implicit
    assert "通过行业对象、设施设备、专业环境" in implicit
    assert "【页面逻辑｜不上屏】" not in implicit
    assert "不使用等权卡片、通用图标流程或逐项配图" not in implicit
    assert "每个锁定模块及其名称只出现一次" not in implicit
    assert "Do not show frontal faces" not in implicit
    assert "解释性正文由后续 PPT 可编辑文字层承载" not in implicit
    assert "领导汇报" in implicit
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
    assert "可编辑文字层承载" not in red.prompt
    assert "ID 1" not in red.prompt
    assert "classic_red_consulting" not in red.prompt


def test_style_nine_content_first_rejects_stale_scene_first_lock_wording() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        payload = json.loads(lock.read_text(encoding="utf-8"))
        payload["style"]["imagegen_signature"] = [
            "允许轻微立体层次、浅阴影和扩大场景。"
        ]
        payload["style"]["scope_rule"] = "允许场景感成为主叙事。"
        lock.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        prompt = build_page_prompt(page, lock)

    assert "允许轻微立体层次、浅阴影和扩大场景" not in prompt
    assert "允许场景感成为主叙事" not in prompt
    assert "禁止霓虹蓝、透明玻璃、发光底座、HUD 面板" not in prompt
    assert "生成式图形构图负责组织页面主线" not in prompt
    assert "少量实景、近实景或物件型语义图仅作点缀" not in prompt
    assert "文字是页面主体" not in prompt
    assert "不得占据约半幅页面" not in prompt
    assert "图标不是默认视觉载体" not in prompt


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

    locked = prompt.split("【锁定关键文字】", 1)[1].split(
        "【完整上屏内容】", 1
    )[0]
    semantics = prompt.split("【完整上屏内容】", 1)[1]
    assert page.onscreen_judgment not in locked
    assert "数据治理｜质量与授权" in locked
    assert "数据治理" in semantics


def test_closed_loop_contract_avoids_equal_stages_and_bottom_summary() -> None:
    page = replace(
        _page(),
        visual_structure="输入、处理、校验、反馈形成闭环回流。",
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "do not turn the modules into equally spaced stages" not in prompt
    assert "never as a separate bottom summary zone" not in prompt


def test_content_first_omits_auxiliary_label_budget() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【辅助标签预算｜不上屏】" not in prompt
    assert "本页辅助标签白名单为空" not in prompt


def test_content_first_omits_removed_interface_visual_language_rules() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "界面化表达不受禁止" not in prompt
    assert "不得默认套用仪表盘或模板化界面" not in prompt


def test_creative_brief_visual_grammar_defaults_to_empty_auxiliary_allowlist() -> None:
    grammar = creative_brief_visual_grammar()

    assert "empty auxiliary-label allowlist" in grammar
    assert "only when the upstream script explicitly supplies a non-empty" in grammar
    assert "use at most two short labels" not in grammar


@pytest.mark.parametrize(
    ("title", "main_message", "onscreen_text", "expected"),
    (
        (
            "平台定位与业务架构",
            "平台连接三类业务并由治理能力贯穿全链",
            "纵向关系：数据资产 → 知识加工 → 智能能力 → 三类应用；横向治理贯穿每层。",
            "crosscutting_chain",
        ),
        (
            "教师智能数字助教",
            "教师端串联教学生产流程并保留最终责任",
            "工作流：资料上传 → 解析 → 诊断 → 生成 → 审核发布 → 效果回收。",
            "closed_loop",
        ),
        (
            "总体技术路线",
            "技术体系沿四层主链逐步建设",
            "四层贯通：治理、解析检索、模型编排、应用反馈持续迭代。",
            "closed_loop",
        ),
        (
            "智能应用技术引擎",
            "三类引擎按业务任务分工并共同受控",
            "分工关系：学生引擎服务学习闭环，教师引擎服务教学工作流，"
            "学校引擎服务规划分析，统一治理连接三者。",
            "capability_relationship",
        ),
    ),
)
def test_visual_intent_uses_explicit_relationship_lines_from_reliable_copy(
    title: str,
    main_message: str,
    onscreen_text: str,
    expected: str,
) -> None:
    page = replace(
        _page(),
        title=title,
        main_message=main_message,
        onscreen_text=onscreen_text,
        module_titles=(),
        visual_structure="",
    )

    assert select_page_visual_intent_type(page, "") == expected


def test_crosscutting_chain_requires_primary_and_transverse_signals() -> None:
    page = replace(
        _page(),
        main_message="平台连接三类业务",
        onscreen_text="纵向关系：数据资产 → 知识加工 → 智能能力 → 三类应用。",
        module_titles=(),
        visual_structure="",
    )

    assert select_page_visual_intent_type(page, "") != "crosscutting_chain"


def test_locked_text_preserves_supplied_relationship_annotation_labels() -> None:
    page = replace(
        _page(),
        onscreen_text=(
            "纵向关系：数据资产 → 知识加工 → 智能能力 → 三类应用。\n"
            "工作流：资料上传 → 解析 → 审核发布。\n"
            "业务含义：教师保留最终责任。"
        ),
        module_titles=("01｜数据资产层", "02｜知识加工层"),
    )

    locked = locked_onscreen_text(page)

    assert "纵向关系" in locked
    assert "工作流" in locked
    assert "业务含义" not in locked


def test_content_first_keeps_relationship_annotations_atomic() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "上述关系说明是不可拆分的原子注释块" not in prompt
    assert "不得从中提炼、拆出或派生第二套阶段名" not in prompt
    assert "底部分类、图例或短标签" not in prompt


def test_content_first_full_reference_keeps_complete_onscreen_content() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    full = prompt.split("【完整上屏内容】", 1)[1].split(
        "【结论句要求｜不上屏】", 1
    )[0]
    assert "保持滚动验证和误差复盘" in full
    assert "权限、日志和发布审核共同保障运行" in full
    assert "解释性正文由后续 PPT 可编辑文字层承载" not in prompt
    assert "不要求 ImageGen 逐字生成" not in prompt


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

    assert "如【锁定关键文字】含正文结论句" in prompt
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
    assert "解释性正文由后续 PPT 可编辑文字层承载" not in prompt
    assert "【完整上屏内容】均需进入 full 图" not in prompt
    assert prompt.count("【页面逻辑｜不上屏】") == 0
    assert "【只读构图语义｜不得上屏】" not in prompt
    assert "不得从本区抽取任何新标题、栏目名、图内标签" not in prompt
    assert "页面构图和信息组织仍由" not in prompt


def test_content_first_text_rule_keeps_locked_names_and_numbers_authoritative() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【锁定关键文字】中的每一项都必须逐字准确" not in prompt
    assert "完整上屏内容已有的数字、单位、专有名词、业务术语和否定含义必须准确" not in prompt
    assert "不得自行补充限定信息" not in prompt
    assert "不得新增未经页面内容支持的上屏文字" not in prompt


def test_content_first_locks_only_conclusion_and_numeric_fact_lines() -> None:
    page = _page()
    locked = locked_onscreen_text(page)
    assert page.onscreen_judgment in locked
    assert all(title in locked for title in page.module_titles)
    assert "2025年完成率 95%" in locked
    assert "保持滚动验证和误差复盘" not in locked


def test_image_locked_text_stays_bitmap_safe_and_preserves_short_labels() -> None:
    page = _page()
    selected = select_image_locked_text(page)
    assert page.onscreen_judgment not in selected
    assert "数据治理｜质量与授权" in selected
    assert "2025年完成率 95%" in selected
    assert all(len(line.replace(" ", "")) <= 14 for line in selected.splitlines())


def test_content_first_records_presentation_and_editable_body() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(page, lock)
    metadata = compiled.build_metadata()
    assert metadata["presentation"]["layout_motif"] in {
        "evidence_landscape", "control_room_bridge", "process_atlas",
        "decision_canvas", "layered_system",
    }
    assert metadata["image_locked_text"] == select_image_locked_text(page)
    assert metadata["editable_body_text"] == page.onscreen_text.strip()
    assert "【版式与场景策略｜不上屏】" not in compiled.prompt


def test_auto_presentation_decision_stays_in_metadata_only() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(page, lock)

    assert compiled.presentation is not None
    assert compiled.presentation.source == "auto"
    assert compiled.presentation.layout_motif not in compiled.prompt
    assert compiled.presentation.scene_role not in compiled.prompt
    assert "【版式与场景策略｜不上屏】" not in compiled.prompt


def test_explicit_presentation_override_reaches_prompt() -> None:
    page = replace(_page(), layout_motif="process_atlas", scene_role="no_scene")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(page, lock)

    assert "【人工版式覆盖｜不上屏】" in compiled.prompt
    assert "process_atlas" in compiled.prompt
    assert "no_scene" in compiled.prompt


def test_semantic_only_keeps_judgment_in_semantics_but_not_locked_copy() -> None:
    page = replace(_page(), onscreen_judgment_mode="semantic_only")
    locked = locked_onscreen_text(page)
    assert page.onscreen_judgment not in locked
    assert "2025年完成率 95%" in locked
    assert page.onscreen_judgment in diagnostic_onscreen_text(page)
    assert resolve_onscreen_judgment_mode(page) == "semantic_only"


def test_semantic_only_with_no_numeric_facts_omits_empty_locked_section() -> None:
    page = replace(
        _page(),
        onscreen_judgment_mode="semantic_only",
        onscreen_text="- 服务行业共性需求",
        module_titles=(),
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【锁定关键文字】" not in prompt
    assert CONTENT_FIRST_ONSCREEN_STORY_CONTRACT not in prompt
    assert CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT in prompt
    assert "不得从【页面任务】【核心判断】或【页面逻辑】中自行抽取整句" in prompt


def test_semantic_only_still_locks_business_module_labels() -> None:
    page = replace(
        _page(),
        onscreen_judgment_mode="semantic_only",
        onscreen_text="**行业公共能力**\n- 服务行业共性需求",
        module_titles=("行业公共能力",),
    )
    locked = locked_onscreen_text(page)
    assert page.onscreen_judgment not in locked
    assert "行业公共能力" in locked
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)
    assert CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT in prompt
    assert "中的每一项都必须逐字准确" not in prompt
    assert "【完整上屏内容】仍须完整表达" in prompt


def test_style_nine_compiles_short_refinement_signature() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "审美签名：" not in prompt
    assert "禁止霓虹蓝、透明玻璃、发光底座、HUD 面板" not in prompt
    assert "由本页内容关系决定的清晰阅读主线" not in prompt
    assert "不得预设中央主体、等宽分栏、卡片阵列或其他固定版式" not in prompt
    assert "不得为了追求跨页差异而强制改变构图" not in prompt


def test_page_number_does_not_select_a_layout_family() -> None:
    page_four = replace(_page(), page_id="P04")
    page_five = replace(_page(), page_id="P05")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt_four = build_page_prompt(page_four, lock)
        prompt_five = build_page_prompt(page_five, lock)

    assert "页面逻辑｜不上屏" not in prompt_four
    assert "页面逻辑｜不上屏" not in prompt_five


def test_judgment_evidence_layout_is_content_driven() -> None:
    page = replace(_page(), page_id="P06")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(
            page,
            lock,
            visual_context={"visual_intent_type": "judgment_evidence"},
        )

    assert "let the content determine position, scale, grouping, and visual carrier" not in prompt
    assert "layout skeleton selected independently of the page content" not in prompt


def test_locked_judgment_is_not_repeated_in_complete_page_semantics() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert prompt.count(page.onscreen_judgment.strip()) == 1


def test_semantic_only_numeric_fact_is_locked_but_not_called_a_conclusion() -> None:
    page = replace(
        _page(),
        onscreen_judgment_mode="semantic_only",
        onscreen_text="**公共能力**\n- 2025年完成率 95%",
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【锁定关键文字】" in prompt
    assert "2025年完成率 95%" in prompt
    assert CONTENT_FIRST_ONSCREEN_STORY_CONTRACT not in prompt
    assert CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT in prompt


def test_outline_context_can_select_semantic_only_without_page_specific_code() -> None:
    page = _page()
    context = {"onscreen_judgment_mode": "semantic_only"}
    assert page.onscreen_judgment not in locked_onscreen_text(page, context)
    assert resolve_onscreen_judgment_mode(page, context) == "semantic_only"


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("relationship", "semantic_only"),
        ("positioning", "semantic_only"),
        ("boundary", "semantic_only"),
        ("mechanism", "semantic_only"),
        ("fact", "locked"),
        ("metric", "locked"),
        ("milestone", "locked"),
        ("acceptance", "locked"),
        ("prohibition", "locked"),
    ],
)
def test_judgment_role_derives_default_display_mode(role: str, expected: str) -> None:
    page = replace(_page(), onscreen_judgment_mode="")
    assert resolve_onscreen_judgment_mode(page, {"judgment_role": role}) == expected


def test_explicit_display_mode_overrides_judgment_role() -> None:
    page = replace(_page(), onscreen_judgment_mode="")
    assert resolve_onscreen_judgment_mode(
        page,
        {
            "judgment_role": "relationship",
            "onscreen_judgment_mode": "locked",
        },
    ) == "locked"


def test_invalid_onscreen_judgment_mode_fails_compilation() -> None:
    page = replace(_page(), onscreen_judgment_mode="sometimes")
    with pytest.raises(ValueError, match="unsupported onscreen_judgment_mode"):
        locked_onscreen_text(page)


def test_content_first_uses_the_compact_visual_wording() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【页面逻辑｜不上屏】" not in prompt
    assert "主导关系：" not in prompt
    assert "视觉证明：" not in prompt
    assert "空间组织：" not in prompt
    assert "本页避免：" not in prompt
    assert prompt.count("视觉证明：") == 0


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
    assert "视觉证明：用共同底座托住业务结果" not in prompt
    assert prompt.count("视觉证明：") == 0
    assert "不使用等权卡片、通用图标流程或逐项配图" not in prompt
    assert "如出现人物，仅使用远景、背影或局部" not in prompt


def test_visual_intent_uses_script_visual_structure_for_relationship_role() -> None:
    base = _page()
    closed_loop = replace(
        base,
        main_message="学生、教师和学校业务共享四段治理机制",
        visual_structure="闭环回流——受控输入到智能处理、校验、版本化回流，再回到起点。",
    )
    interface_collaboration = replace(
        base,
        main_message="统一网关连接多类领域接口实现跨系统协同",
        visual_structure="双侧协同——以身份组织接口为视觉中心，其余模块按支撑关系连接。",
    )
    availability_support = replace(
        base,
        main_message="三条运行链由高可用机制统一托底",
        visual_structure="主体泳道——三条运行链展开，底部设置统一支撑关系。",
    )

    assert select_page_visual_intent_type(closed_loop, "") == "closed_loop"
    assert (
        select_page_visual_intent_type(interface_collaboration, "")
        == "capability_relationship"
    )
    assert (
        select_page_visual_intent_type(availability_support, "")
        == "hierarchy_support"
    )


def test_explicit_script_visual_proof_reaches_page_logic_contract() -> None:
    page = replace(
        _page(),
        visual_proof=(
            "供需信息经过数据治理、模型推演和专家会商形成行业研判成果，"
            "再服务履职与行业共用"
        ),
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(
            page,
            lock,
            visual_context={"visual_proof": "自动生成的通用视觉证明"},
        )

    assert "视觉证明：供需信息经过数据治理、模型推演和专家会商形成行业研判成果" not in prompt
    assert "自动生成的通用视觉证明" not in prompt
    assert "视觉结构：" not in prompt


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
    assert "empty auxiliary-label allowlist" in prompt
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
