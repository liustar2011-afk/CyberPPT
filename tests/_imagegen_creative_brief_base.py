from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

try:
    import pytest
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("pytest is not installed") from exc

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.imagegen_pipeline.imagegen_handoff import (
    CONTENT_FIRST_ONSCREEN_STORY_CONTRACT,
    CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT,
    build_page_creative_brief,
    build_page_prompt,
    compile_page_prompt,
    diagnostic_onscreen_text,
    locked_onscreen_text,
    PresentationDecision,
    resolve_presentation_decision,
    resolve_visual_medium,
    select_dense_supporting_facts,
    resolve_onscreen_judgment_mode,
    select_image_locked_text,
    select_page_visual_intent_type,
)
from scripts.imagegen_pipeline.prompt_diagnostics import analyze_prompt
from scripts.imagegen_pipeline.style_library import write_project_style_lock
from scripts.imagegen_pipeline.visual_grammar import creative_brief_visual_grammar


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
    assert decision.scene_role == "no_scene"


def test_abstract_relations_do_not_default_to_scenes() -> None:
    page = _page()
    assert resolve_presentation_decision(page, "judgment_evidence").scene_role == "no_scene"
    assert resolve_presentation_decision(page, "hierarchy_support").scene_role == "no_scene"


def test_scenario_application_still_defaults_to_a_scene() -> None:
    page = _page()
    decision = resolve_presentation_decision(page, "scenario_application")
    assert decision.scene_role == "primary_scene"
    assert decision.visual_medium == "semantic_scene"


def test_abstract_page_uses_editorial_typographic_medium() -> None:
    page = _page()
    assert resolve_visual_medium(page, "capability_relationship") == "editorial_typographic"
    decision = resolve_presentation_decision(page, "capability_relationship")
    assert decision.visual_medium == "editorial_typographic"
    assert decision.scene_role == "no_scene"


def test_dense_editorial_page_does_not_inject_must_onscreen_fact_layer() -> None:
    page = replace(
        _page(),
        full_prose=(
            "按30个学科管理约30万条题目及相关教材、教案和知识内容。"
            "每次查询同时校验题目状态、安全等级和授权用途。"
            "普通业务结合行级安全策略和服务端权限校验实现多组织隔离。"
            "跨组织共享需明确资产范围、使用目的、有效期和撤销机制。"
            "外部系统通过受控接口访问，服务端根据授权范围筛选数据。"
        )
        * 4,
    )
    assert resolve_visual_medium(page, "capability_relationship") == "editorial_dense"
    # Helper may still score prose for diagnostics, but content-first prompts
    # must not re-promote recovered facts into a must-onscreen contract.
    assert select_dense_supporting_facts(page)
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock, page_mission="如何治理知识底座")
    assert "【补充事实层｜必须上屏】" not in prompt
    onscreen_section = prompt.split("【完整上屏内容】", 1)[1].split(
        "【结论表达要求｜不上屏】", 1
    )[0]
    assert "多组织隔离" not in onscreen_section


def test_default_compiler_is_content_first_and_legacy_requires_opt_in() -> None:
    page = replace(_page(), onscreen_judgment_mode="locked")
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
    assert "【视觉风格｜不上屏】" in implicit
    assert "扩展风格9：" not in implicit
    assert "不进入默认候选" not in implicit
    assert "ivory_deep_blue_scene" not in implicit
    assert "风格适用语境" not in implicit
    assert "风格约定（仅约束视觉表达，不覆盖本页内容与主导关系）" not in implicit
    assert "【视觉媒介路由｜不上屏】" not in implicit
    assert "媒介类型：editorial_typographic" not in implicit
    assert "editorial_dense" not in implicit
    assert "【页面逻辑｜不上屏】" not in implicit
    assert "不使用等权卡片、通用图标流程或逐项配图" not in implicit
    assert "每个锁定模块及其名称只出现一次" not in implicit
    assert "Do not show frontal faces" not in implicit
    assert "解释性正文由后续 PPT 可编辑文字层承载" not in implicit
    assert "领导汇报" in implicit or "executive briefing" in implicit
    assert "style.selected_lock" in (
        implicit_compiled.build_metadata()["injected_rule_ids"]
    )
    assert (
        implicit_compiled.build_metadata()["style_selection"]["name"]
        == "纯白 + 深蓝领导汇报"
    )
    assert "[Mandatory composition guidance]" not in implicit
    assert "semantic_structure" not in implicit_compiled.build_metadata()


def test_visual_structure_review_mode_is_explicit_and_auditable() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(
            page,
            lock,
            visual_structure_mode="review",
        )
    metadata = compiled.build_metadata()
    assert "[Mandatory composition guidance]" in compiled.prompt
    assert "- Reading path:" in compiled.prompt
    assert "- Dominant visual carrier:" in compiled.prompt
    assert compiled.prompt.index("【完整上屏内容】") < compiled.prompt.index(
        "[Mandatory composition guidance]"
    ) < compiled.prompt.index("【呈现文案改写授权｜上屏】")
    assert metadata["semantic_structure"]["mode"] == "review"
    assert len(metadata["semantic_structure"]["visual_carrier"]["candidates"]) == 3
    assert "semantic_structure.composition" in metadata["injected_rule_ids"]


def test_visual_structure_review_mode_rejects_non_content_first_compiler() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        with pytest.raises(ValueError, match="requires content-first-v1"):
            compile_page_prompt(
                page,
                lock,
                prompt_compiler="legacy",
                visual_structure_mode="review",
            )


def test_visual_structure_review_replaces_legacy_logic_instruction() -> None:
    page = replace(_page(), visual_structure="分层剖面——底座向上支撑业务应用")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        default = compile_page_prompt(page, lock)
        review = compile_page_prompt(page, lock, visual_structure_mode="review")
    assert "【页面逻辑｜不上屏】" in default.prompt
    assert "【页面逻辑｜不上屏】" not in review.prompt
    assert "[Mandatory composition guidance]" in review.prompt


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

    semantics = prompt.split("【完整上屏内容】", 1)[1]
    assert "【锁定关键文字】" not in prompt
    assert "【呈现文案改写授权｜上屏】" in prompt
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
    ("title", "main_message", "full_prose", "expected"),
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
    full_prose: str,
    expected: str,
) -> None:
    page = replace(
        _page(),
        title=title,
        main_message=main_message,
        onscreen_text="- 支撑内容",
        full_prose=full_prose,
        module_titles=(),
        visual_structure="",
    )

    assert select_page_visual_intent_type(page, "") == expected


def test_crosscutting_chain_requires_primary_and_transverse_signals() -> None:
    page = replace(
        _page(),
        main_message="平台连接三类业务",
        onscreen_text="- 支撑内容",
        full_prose="纵向关系：数据资产 → 知识加工 → 智能能力 → 三类应用。",
        module_titles=(),
        visual_structure="",
    )

    assert select_page_visual_intent_type(page, "") != "crosscutting_chain"


def test_locked_text_strips_backend_relation_meta_labels() -> None:
    page = replace(
        _page(),
        onscreen_text=(
            "01｜数据资产层\n"
            "纵向关系：数据资产 → 知识加工 → 智能能力 → 三类应用。\n"
            "工作流：资料上传 → 解析 → 审核发布。\n"
            "业务含义：教师保留最终责任。"
        ),
        module_titles=("01｜数据资产层", "02｜知识加工层"),
    )

    locked = locked_onscreen_text(page)

    assert "01｜数据资产层" in locked
    assert "纵向关系" not in locked
    assert "工作流" not in locked
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


def test_content_first_accepts_content_page_without_visible_judgment() -> None:
    page = replace(_page(), onscreen_judgment="")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)
    assert "不得自行补写结论、因果、必要性或结果承诺" not in prompt or page.main_message
    assert "2025年完成率 95%" in prompt
    assert "权限、日志和发布审核共同保障运行" in prompt


def test_content_first_treats_visible_judgment_as_body_conclusion_with_style_typography_lock() -> None:
    page = replace(_page(), onscreen_judgment_mode="locked")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)
        style_contract = json.loads(lock.read_text(encoding="utf-8"))["style"][
            "prompt_contract"
        ]

    assert "将【完整上屏内容】改写为结论先行、层级清晰的页面表达" in prompt
    assert "【锁定关键文字】" not in prompt
    assert "Rewrite the supplied source copy into concise, conclusion-first Chinese presentation text." in style_contract
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
    page = replace(_page(), onscreen_judgment_mode="locked")
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
    assert "image_locked_text" not in metadata
    assert metadata["editable_body_text"] == page.onscreen_text.strip()
    assert "【版式与场景策略｜不上屏】" not in compiled.prompt


def test_auto_visual_medium_decision_stays_out_of_prompt() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(page, lock)

    assert compiled.presentation is not None
    assert compiled.presentation.source == "auto"
    assert compiled.presentation.layout_motif not in compiled.prompt
    assert "【视觉媒介路由｜不上屏】" not in compiled.prompt
    assert "媒介类型：" not in compiled.prompt
    assert "editorial_dense" not in compiled.prompt
    assert "【版式与场景策略｜不上屏】" not in compiled.prompt


def test_explicit_presentation_override_reaches_prompt() -> None:
    page = replace(_page(), layout_motif="process_atlas", scene_role="no_scene")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(page, lock)

    assert "【人工版式覆盖｜不上屏】" in compiled.prompt
    assert "process_atlas" in compiled.prompt
    assert "no_scene" in compiled.prompt
    assert "媒介类型：" in compiled.prompt


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

    assert "\n【锁定关键文字】\n" not in prompt
    assert CONTENT_FIRST_ONSCREEN_STORY_CONTRACT not in prompt
    assert CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT in prompt
    assert "可依据【完整上屏内容】、【页面任务】、【核心意思】和【页面逻辑】形成结论句" in prompt


def test_semantic_only_handoff_preserves_thesis_logic_and_relations() -> None:
    page = replace(
        _page(),
        onscreen_judgment_mode="semantic_only",
        subtitle="多源知识归一后，由分层数据服务支撑应用",
        visual_structure="贯穿主链——来源 → 对象 → 服务 → 应用出口。",
        module_titles=(
            "01｜三类知识来源",
            "02｜统一知识对象",
            "03｜分层数据服务",
            "04｜质量与生命周期",
        ),
        full_prose=(
            "从业务关系看，三类知识来源先归一为统一知识对象，再由分层数据服务供给应用。"
            "统一知识对象连接来源、版本、权限和质量状态。"
        ),
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock, page_mission="如何治理多源知识")

    assert page.core_message not in prompt
    assert "页面任务与核心意思用于推导语义关系，也可用于生成结论、总结框或标题" in prompt
    assert "【页面逻辑｜不上屏】" in prompt
    assert "主导关系：路径转化。" in prompt
    assert "判断—证据" not in prompt
    assert "从业务关系看，三类知识来源先归一为统一知识对象" in prompt
    assert "统一知识对象连接来源、版本、权限和质量状态" in prompt
    assert "质量与生命周期" not in prompt.split("【页面语义关系｜仅供理解，不上屏】", 1)[1].split(
        "【页面逻辑｜不上屏】", 1
    )[0]


def test_v2_composition_relation_routes_without_inventing_judgment_evidence() -> None:
    page = replace(
        _page(),
        onscreen_judgment="",
        onscreen_judgment_mode="semantic_only",
        contract_receipt={
            "schema": "cyberppt.page_contract_receipt.v2",
            "core_message": "总体能力框架由五个层次构成，各层分别承担相应职责",
            "content_relations": [
                {
                    "relation": "composed_of",
                    "subject": "总体能力框架",
                    "objects": ["业务应用", "成果服务", "模型分析", "数据治理", "运行保障"],
                    "source_refs": ["S021"],
                }
            ],
        },
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(page, lock)

    assert compiled.relation == "hierarchy_support"
    assert "核心意思：" not in compiled.prompt
    assert "页面任务与核心意思用于推导语义关系，也可用于生成结论、总结框或标题" in compiled.prompt
    assert "改写并列项时，保留原文中共享谓词、限定语和父级说明的适用范围" in compiled.prompt
    assert "【呈现文案改写授权｜上屏】" in compiled.prompt
    assert "composed_of" in compiled.prompt
    assert "判断—证据" not in compiled.prompt


def test_path_chain_hard_hint_from_visual_structure() -> None:
    page = replace(
        _page(),
        main_message="多源知识先归一再服务应用",
        visual_structure="贯穿主链——来源 → 对象 → 服务 → 应用。",
        module_titles=(),
        onscreen_text="- 支撑内容",
    )
    assert select_page_visual_intent_type(page, "如何治理多源知识") == "path_chain"


def test_crosscutting_hard_hint_when_transverse_clause_present() -> None:
    page = replace(
        _page(),
        main_message="多源知识先归一再服务应用，质量治理贯穿主链",
        visual_structure=(
            "贯穿主链——来源归一为对象再进入服务供给；质量与生命周期贯穿主链。"
        ),
        module_titles=(),
        onscreen_text="- 支撑内容",
    )
    assert select_page_visual_intent_type(page, "如何治理多源知识") == "crosscutting_chain"


def test_crosscutting_hard_hint_for_layered_with_horizontal_governance() -> None:
    page = replace(
        _page(),
        main_message="统一底座连接三类应用，横向治理贯穿全链",
        full_prose="从业务关系看，数据资产经过知识加工形成智能能力，横向治理贯穿每一层。",
        visual_structure=(
            "分层剖面——自下而上依次呈现数据资产层、知识加工层、智能能力层、"
            "三类应用层、横向治理层；一级模块与上屏文字一致。"
        ),
        module_titles=(),
        onscreen_text="- 支撑内容",
    )
    assert select_page_visual_intent_type(page, "平台如何组织") == "crosscutting_chain"


def test_script_visual_intent_type_field_is_explicit_override() -> None:
    page = replace(
        _page(),
        visual_structure="",
        visual_intent_type="path_chain",
        main_message="普通支撑判断",
        onscreen_text="- 支撑内容",
        module_titles=(),
    )
    assert select_page_visual_intent_type(page, "") == "path_chain"


def test_contract_receipt_visual_intent_type_is_honored() -> None:
    page = replace(
        _page(),
        visual_structure="",
        contract_receipt={"visual_intent_type": "closed_loop"},
        main_message="普通支撑判断",
        onscreen_text="- 支撑内容",
        module_titles=(),
    )
    assert select_page_visual_intent_type(page, "") == "closed_loop"


def test_low_confidence_fallback_omits_logic_contract_even_for_semantic_only() -> None:
    page = replace(
        _page(),
        onscreen_judgment_mode="semantic_only",
        subtitle="普通副标题",
        visual_structure="",
        speaker_notes="补充讲解。",
        full_prose="普通说明文字。",
        main_message="形成稳定的行业公共能力",
        onscreen_text="- 支撑内容",
        module_titles=(),
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【页面逻辑｜不上屏】" not in prompt
    assert "主导关系：判断—证据" not in prompt


def test_business_relations_outrank_module_title_chains() -> None:
    from scripts.imagegen_pipeline.imagegen_handoff import _page_semantic_relations

    page = replace(
        _page(),
        visual_structure=(
            "贯穿主链——三类知识来源 → 统一知识对象 → 分层数据服务 → 质量与生命周期；"
        ),
        module_titles=(
            "01｜三类知识来源",
            "02｜统一知识对象",
            "03｜分层数据服务",
            "04｜质量与生命周期",
        ),
        full_prose=(
            "从业务关系看，三类知识来源先归一为统一知识对象，再由分层数据服务面向应用供给能力。"
            "统一知识对象连接来源、版本、权限和质量状态。"
        ),
        onscreen_text="",
        speaker_notes="",
    )
    relations = _page_semantic_relations(page)
    assert "从业务关系看" in relations
    assert "统一知识对象连接" in relations
    assert "质量与生命周期" not in relations


def test_semantic_keeps_subject_before_structure_verb_marker() -> None:
    from scripts.imagegen_pipeline.imagegen_handoff import _page_semantic_relations

    page = replace(
        _page(),
        visual_structure=(
            "贯穿主链——来源归一为对象再进入服务供给；质量与生命周期贯穿主链。"
        ),
        module_titles=(
            "01｜三类知识来源",
            "02｜统一知识对象",
            "03｜分层数据服务",
            "04｜质量与生命周期",
        ),
        full_prose=(
            "从业务关系看，三类知识来源先归一为统一知识对象，"
            "再由分层数据服务面向检索、事件计算和分析应用供给能力。"
        ),
        onscreen_text="",
        speaker_notes="",
    )
    relations = _page_semantic_relations(page)
    assert "质量与生命周期贯穿主链" in relations
    assert "- 贯穿主链。" not in relations
    assert not any(
        line.strip() in {"- 贯穿主链。", "- 贯穿主链"}
        for line in relations.splitlines()
    )


def test_labeled_relation_keeps_semicolon_clauses_together() -> None:
    from scripts.imagegen_pipeline.imagegen_handoff import _page_semantic_relations

    page = replace(
        _page(),
        visual_structure="受控边界——由外向内设置受控入口；一级模块与上屏文字一致。",
        onscreen_text=(
            "责任关系：数据所有者定用途与范围；业务人员按授权使用；"
            "平台负责访问与内容治理；运维仅保留必要权限。\n"
            "业务含义：统一准入原则把知识来源、审核责任和服务等级前置到业务运行入口。"
        ),
        full_prose="",
        speaker_notes="",
        module_titles=(),
    )
    relations = _page_semantic_relations(page)
    assert "业务人员按授权使用" in relations
    assert "运维仅保留必要权限" in relations
    assert "组件关系" not in relations
    assert not any(
        line.rstrip().endswith("；") for line in relations.splitlines()
    )


def test_component_relation_semicolon_clauses_stay_intact() -> None:
    from scripts.imagegen_pipeline.imagegen_handoff import _page_semantic_relations

    page = replace(
        _page(),
        visual_structure="",
        onscreen_text=(
            "组件关系：关系库、缓存、检索索引支撑在线事务；"
            "对象存储、消息队列支撑异步事件；分析库承接离线计算。\n"
            "业务含义：三条运行链按实时性和计算特征分工。"
        ),
        full_prose="",
        speaker_notes="",
        module_titles=(),
    )
    relations = _page_semantic_relations(page)
    assert "对象存储、消息队列支撑异步事件" in relations
    assert "分析库承接离线计算" in relations
    assert not any(
        line.strip() == "- 组件关系：关系库、缓存、检索索引支撑在线事务；"
        or line.strip() == "- 组件关系：关系库、缓存、检索索引支撑在线事务。"
        for line in relations.splitlines()
    )


def test_semantic_relations_dedupe_bullet_leftovers_from_onscreen() -> None:
    from scripts.imagegen_pipeline.imagegen_handoff import _page_semantic_relations

    meaning = (
        "业务含义：统一底座和横向治理使三类应用共享知识标准，"
        "同时保留各自权限、交互方式和解释口径。"
    )
    page = replace(
        _page(),
        visual_structure="分层剖面——自下而上依次呈现数据层与应用层。",
        onscreen_text=(
            "01｜数据资产层\n"
            f"  - {meaning}\n"
            "02｜三类应用层\n"
        ),
        full_prose=(
            "从业务关系看，数据资产经过知识加工形成智能能力并服务三类应用，"
            "横向治理贯穿每一层。"
        ),
        speaker_notes="",
        module_titles=("01｜数据资产层", "02｜三类应用层"),
    )
    relations = _page_semantic_relations(page)
    assert relations.count(meaning) == 1
    assert "- - " not in relations
    assert "从业务关系看，数据资产经过知识加工" in relations


def test_page_logic_contract_uses_chinese_spatial_rules() -> None:
    from scripts.imagegen_pipeline.imagegen_handoff import render_page_logic_contract

    page = replace(
        _page(),
        visual_structure="分层剖面——自下而上依次呈现支撑层与结果层；一级模块与上屏文字一致。",
        main_message="上层结果依赖下层支撑",
        onscreen_text="- 支撑内容",
        module_titles=(),
    )
    relation, source, contract = render_page_logic_contract(
        page, page_mission="体系如何成立"
    )
    assert relation == "hierarchy_support"
    assert source == "hint"
    assert "主导关系：分层支撑。" in contract
    assert "结构形态：分层剖面——自下而上依次呈现支撑层与结果层" in contract
    assert "一级模块与上屏文字一致" not in contract
    # Drawing recipes must not reach ImageGen.
    assert "空间组织：" not in contract
    assert "本页避免：" not in contract
    assert "视觉证明：" not in contract
    assert "Build an asymmetric" not in contract
    assert "A software architecture stack" not in contract


def test_page_logic_contract_passes_expression_roles_and_labels_without_layout_recipe() -> None:
    from scripts.imagegen_pipeline.imagegen_handoff import render_page_logic_contract

    page = replace(
        _page(),
        contract_receipt={
            "onscreen_expression_ir": {
                "schema": "cyberppt.onscreen_expression_ir.v1",
                "pattern": "parallel_states_to_foundation",
                "reading_order": ["state", "foundation"],
                "nodes": [
                    {"id": "state", "role": "current_state", "render": "statement_stack"},
                    {"id": "foundation", "role": "conclusion", "render": "landing"},
                ],
                "edges": [{"id": "e1", "from": "state", "to": "foundation", "visible_label": "共同构成"}],
            }
        },
    )

    _, _, contract = render_page_logic_contract(page, page_mission="建设背景如何形成")

    assert "上屏表达模式：parallel_states_to_foundation。" in contract
    assert "阅读顺序：current_state／statement_stack → conclusion／landing。" in contract
    assert "以“共同构成”连接" in contract
    assert "坐标" not in contract
    assert "卡片" not in contract


def test_style09_hides_page_layout_recipe_but_keeps_semantic_relation() -> None:
    page = replace(
        _page(),
        visual_structure=(
            "贯穿主链——四行矩阵表：主视觉顶部呈现横向五节点控制链，"
            "下方以泳道呈现分类，底部设置收束条。"
        ),
        main_message="控制链与分类共同界定业务边界",
        onscreen_text="- 控制链与权利边界",
        module_titles=(),
    )
    with TemporaryDirectory() as style09_directory, TemporaryDirectory() as style08_directory:
        style09_lock = write_project_style_lock(project=Path(style09_directory), style_id=9)
        style08_lock = write_project_style_lock(project=Path(style08_directory), style_id=8)
        style09_prompt = build_page_prompt(page, style09_lock)
        style08_prompt = build_page_prompt(page, style08_lock)

    assert "主导关系：" in style09_prompt
    assert "结构形态：" not in style09_prompt
    # The adapter is Style 09-specific; other style compilers retain the
    # existing authoring contract for backward compatibility.
    assert "结构形态：" in style08_prompt


def test_visual_center_reaches_prompt_and_proof_fallback() -> None:
    from scripts.imagegen_pipeline.imagegen_handoff import build_page_prompt

    page = replace(
        _page(),
        visual_structure="分层剖面——支撑与结果。",
        visual_proof="",
        onscreen_text="- 支撑内容",
        module_titles=(),
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(
            page,
            lock,
            page_mission="体系如何成立",
            visual_context={
                "visual_center": "数据资产层到应用层的五层架构与横向治理带",
                "visual_intent_type": "hierarchy_support",
            },
        )
    # Visual center is authoring metadata only — never injected into ImageGen.
    assert "【视觉中心｜不上屏】" not in prompt
    assert "数据资产层到应用层的五层架构与横向治理带" not in prompt
    assert "以「数据资产层到应用层的五层架构与横向治理带」作为主视觉落点证明本页判断。" not in prompt
    assert "主导关系：分层支撑。" in prompt



def test_visual_carrier_never_injected_into_imagegen() -> None:
    carrier = (
        "以一条连续的“知识资产归一与服务供给”叙事作为主视觉载体。"
        "不得将统一知识对象绘制成软件产品包装、服务器机箱或电子证照。"
    )
    page = replace(_page(), visual_carrier=carrier)
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【视觉载体｜不上屏】" not in prompt
    assert "主视觉载体" not in prompt
    assert "软件产品包装" not in prompt
    assert "服务器机箱" not in prompt


def test_visual_carrier_override_also_stays_out_of_imagegen() -> None:
    page = replace(_page(), visual_carrier="页面字段载体")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(
            page,
            lock,
            visual_intent_override={"visual_carrier": "覆盖载体指引"},
        )
    assert "覆盖载体指引" not in prompt
    assert "页面字段载体" not in prompt
    assert "【视觉载体｜不上屏】" not in prompt


def test_pages_without_visual_carrier_omit_the_section() -> None:
    page = replace(_page(), visual_carrier="")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)
    assert "【视觉载体｜不上屏】" not in prompt


def test_script_parses_visual_carrier_field() -> None:
    text = """## 第9页：载体页

- 页面类型：内容页
- 页面标题：载体页
- 主判断：主判断成立
- 上屏结论：主判断成立
- 上屏文字：
  **模块A**
  - 要点
- 视觉载体：连续叙事主视觉；不得逐项配图标。
"""
    page = parse_script_markdown(text).pages[0]
    assert page.visual_carrier == "连续叙事主视觉；不得逐项配图标。"


def test_semantic_only_allows_stage02_copy_authoring() -> None:
    page = replace(
        _page(),
        onscreen_judgment_mode="semantic_only",
        onscreen_text="**行业公共能力**\n- 服务行业共性需求",
        module_titles=("行业公共能力",),
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)
    assert CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT in prompt
    assert "【呈现文案改写授权｜上屏】" in prompt
    assert "允许改写、提炼、合并、拆分、重排与重设标题层级" in prompt


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
    page = replace(_page(), onscreen_judgment_mode="locked")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert prompt.count(page.onscreen_judgment.strip()) == 1


def test_semantic_only_numeric_fact_is_available_for_stage02_copy_authoring() -> None:
    page = replace(
        _page(),
        onscreen_judgment_mode="semantic_only",
        onscreen_text="**公共能力**\n- 2025年完成率 95%",
    )
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    assert "【锁定关键文字】" not in prompt
    assert "2025年完成率 95%" in prompt
    assert CONTENT_FIRST_ONSCREEN_STORY_CONTRACT not in prompt
    assert "【呈现文案改写授权｜上屏】" in prompt


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
