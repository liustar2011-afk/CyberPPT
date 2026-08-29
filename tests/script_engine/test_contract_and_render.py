from __future__ import annotations
import copy, json, re
from pathlib import Path
from script_engine.contracts import validate_deck_plan, validate_final_script, collect_foundation_source_codes, validate_source_refs_coverage, lint_final_script, check_onscreen_structure, check_full_copy_duplication, outline_final_script, check_speaker_notes_length, check_declared_count, check_onscreen_detail_length, check_onscreen_terminal_punctuation
from script_engine.render import render_stage02_markdown
ROOT = Path(__file__).resolve().parents[2]

def _example() -> dict:
    return json.loads((ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8"))

def _deck_plan_example() -> dict:
    return json.loads((ROOT / "examples" / "deck-plan.example.json").read_text(encoding="utf-8"))

def _foundation_example() -> dict:
    return json.loads((ROOT / "examples" / "foundation.example.json").read_text(encoding="utf-8"))

def test_example_validates() -> None:
    assert validate_final_script(_example()) == []

def test_validate_final_script_rejects_content_page_missing_required_fields() -> None:
    payload = copy.deepcopy(_example())
    del payload["slides"][0]["core_message"]
    issues = validate_final_script(payload)
    assert issues
    assert any("core_message" in issue for issue in issues)

def test_validate_final_script_rejects_empty_onscreen_on_content_page() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = []
    issues = validate_final_script(payload)
    assert issues
    assert any("onscreen" in issue for issue in issues)

def test_validate_final_script_rejects_unknown_page_type() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["page_type"] = "sidebar"
    issues = validate_final_script(payload)
    assert issues
    assert any("page_type" in issue for issue in issues)

def test_validate_final_script_rejects_malformed_page_id() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["id"] = "page-one"
    issues = validate_final_script(payload)
    assert issues
    assert any("id" in issue for issue in issues)

def test_validate_final_script_rejects_missing_slides() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"] = []
    issues = validate_final_script(payload)
    assert issues

def test_validate_final_script_rejects_wrong_contract_name() -> None:
    payload = copy.deepcopy(_example())
    payload["contract"] = "cyberppt.deck-plan"
    issues = validate_final_script(payload)
    assert issues

def test_validate_deck_plan_example_passes() -> None:
    assert validate_deck_plan(_deck_plan_example()) == []

def test_validate_deck_plan_rejects_missing_pages() -> None:
    payload = copy.deepcopy(_deck_plan_example())
    del payload["pages"]
    issues = validate_deck_plan(payload)
    assert issues
    assert any("pages" in issue for issue in issues)

def test_validate_deck_plan_rejects_invalid_content_load_enum() -> None:
    payload = copy.deepcopy(_deck_plan_example())
    payload["pages"][0]["content_load"] = "extreme"
    issues = validate_deck_plan(payload)
    assert issues
    assert any("content_load" in issue for issue in issues)

def test_validate_deck_plan_rejects_page_missing_required_field() -> None:
    payload = copy.deepcopy(_deck_plan_example())
    del payload["pages"][0]["message"]
    issues = validate_deck_plan(payload)
    assert issues
    assert any("message" in issue for issue in issues)

def test_stage02_markdown_uses_compatible_page_heading() -> None:
    markdown = render_stage02_markdown(_example())
    assert re.search(r"^## P01 .+$", markdown, flags=re.MULTILINE)
    assert "- 页面类型：内容页" in markdown
    assert "- 核心结论：" in markdown
    assert "### 完整文字稿" in markdown
    assert "### 上屏文字" in markdown
    assert "### 视觉结构" in markdown
    assert "### 演讲者备注" in markdown

def test_stage02_boundary_does_not_leak_internal_artifacts() -> None:
    markdown = render_stage02_markdown(_example())
    forbidden = ("foundation.json", "deck-plan.json", "source-truth.json", "semantic-argument-model.json", "outline-audit")
    assert all(token not in markdown for token in forbidden)

def test_render_uses_index_when_id_has_no_digits() -> None:
    payload = {"deck": {"title": "T", "communication_goal": "G"}, "slides": [{"id": "cover", "page_type": "cover", "title": "封面"}]}
    markdown = render_stage02_markdown(payload)
    assert "## P01 封面" in markdown

def test_render_pads_multi_digit_page_number_from_id() -> None:
    payload = {"deck": {"title": "T", "communication_goal": "G"}, "slides": [{"id": "P12", "page_type": "content", "title": "第十二页", "mission": "m", "core_message": "c", "onscreen": [{"heading": "h"}]}]}
    markdown = render_stage02_markdown(payload)
    assert "## P12 第十二页" in markdown

def test_render_skips_relationship_missing_from_or_to() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["relationships"] = [{"from": "A", "relation": "有关"}, {"from": "X", "to": "Y", "relation": "因果"}]
    markdown = render_stage02_markdown(payload)
    assert "X → Y：因果" in markdown
    assert "A →" not in markdown

def test_render_omits_optional_sections_when_absent() -> None:
    payload = {"deck": {"title": "T", "communication_goal": "G"}, "slides": [{"id": "P01", "page_type": "content", "title": "标题", "mission": "m", "core_message": "c", "onscreen": [{"heading": "h"}]}]}
    markdown = render_stage02_markdown(payload)
    assert "### 完整文字稿" not in markdown
    assert "### 视觉结构" not in markdown
    assert "### 演讲者备注" not in markdown

def test_render_handles_no_slides() -> None:
    payload = {"deck": {"title": "T", "communication_goal": "G"}, "slides": []}
    markdown = render_stage02_markdown(payload)
    assert markdown.strip().startswith("# T")

def test_render_passes_through_blank_line_paragraph_breaks_in_full_copy() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["full_copy"] = "第一段。\n\n第二段。"
    markdown = render_stage02_markdown(payload)
    assert "第一段。\n\n第二段。" in markdown

def test_collect_foundation_source_codes_gathers_all_citable_sections() -> None:
    codes = collect_foundation_source_codes(_foundation_example())
    assert codes == {
        "F1",
        "F2",
        "F3",
        "F4",
        "C1",
        "R1",
        "A1",
        "ST001",
        "ST002",
        "ST003",
        "ST004",
    }

def test_validate_source_refs_coverage_passes_when_all_known() -> None:
    assert validate_source_refs_coverage(_example(), _foundation_example()) == []

def test_validate_source_refs_coverage_flags_orphaned_code() -> None:
    final_payload = copy.deepcopy(_example())
    final_payload["slides"][0]["source_refs"] = ["ST999"]
    issues = validate_source_refs_coverage(final_payload, _foundation_example())
    assert issues
    assert any("ST999" in issue for issue in issues)

def test_validate_source_refs_coverage_ignores_slides_without_refs() -> None:
    final_payload = copy.deepcopy(_example())
    del final_payload["slides"][0]["source_refs"]
    assert validate_source_refs_coverage(final_payload, _foundation_example()) == []

def test_render_source_refs_have_own_heading_after_speaker_notes() -> None:
    markdown = render_stage02_markdown(_example())
    notes_index = markdown.index("### 演讲者备注")
    source_index = markdown.index("### 内容来源")
    assert source_index > notes_index

def test_render_source_refs_not_attached_to_onscreen_section() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "h", "text": "t"}]
    markdown = render_stage02_markdown(payload)
    onscreen_index = markdown.index("### 上屏文字")
    next_heading_index = markdown.index("###", onscreen_index + 1)
    onscreen_block = markdown[onscreen_index:next_heading_index]
    assert "证据" not in onscreen_block
    assert "内容来源" not in onscreen_block

def test_render_includes_subtitle_line_right_after_title_when_present() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["subtitle"] = "五层两贯穿"
    markdown = render_stage02_markdown(payload)
    title_index = markdown.index("- 页面标题：")
    subtitle_index = markdown.index("- 页面副标题：五层两贯穿")
    mission_index = markdown.index("- 页面使命：")
    assert title_index < subtitle_index < mission_index

def test_render_omits_subtitle_line_when_absent() -> None:
    markdown = render_stage02_markdown(_example())
    assert "页面副标题" not in markdown

def test_validate_final_script_accepts_optional_subtitle() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["subtitle"] = "五层两贯穿"
    assert validate_final_script(payload) == []

def test_render_collapses_embedded_newline_in_onscreen_heading() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "标题\n换行", "text": "正文"}]
    markdown = render_stage02_markdown(payload)
    assert "- 标题 换行：正文" in markdown
    assert "标题\n换行" not in markdown

def test_render_avoids_double_colon_when_heading_already_ends_with_colon() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "小结：", "text": "正文"}]
    markdown = render_stage02_markdown(payload)
    assert "- 小结：正文" in markdown
    assert "：：" not in markdown

def test_render_source_refs_omitted_when_absent() -> None:
    payload = {"deck": {"title": "T", "communication_goal": "G"}, "slides": [{"id": "P01", "page_type": "content", "title": "标题", "mission": "m", "core_message": "c", "onscreen": [{"heading": "h"}]}]}
    markdown = render_stage02_markdown(payload)
    assert "### 内容来源" not in markdown

def test_lint_final_script_passes_on_clean_example() -> None:
    assert lint_final_script(_example()) == []

def test_lint_final_script_flags_contrastive_reveal_in_full_copy() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["full_copy"] = "这不是一次简单的升级，而是一次结构性的重塑。"
    issues = lint_final_script(payload)
    assert issues
    assert any("contrastive-reveal" in issue for issue in issues)

def test_lint_final_script_flags_self_reference_in_onscreen() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "下一步", "text": "启动对接（对应第五章第一步）"}]
    issues = lint_final_script(payload)
    assert issues
    assert any("self-reference" in issue for issue in issues)

def test_lint_final_script_flags_audience_facing_meta_in_core_and_onscreen() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["core_message"] = "本页核心结论是形成统一治理体系。"
    payload["slides"][0]["onscreen"][0]["heading"] = "汇合点"
    issues = lint_final_script(payload)
    assert sum("audience-facing-meta" in issue for issue in issues) == 2


def test_lint_final_script_flags_underspecified_business_object() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["core_message"] = "中电联承担电力行业能力建设和标准验证。"
    payload["slides"][0]["onscreen"] = [
        {"heading": "推进相关工作", "text": "统一目录、身份和标识"}
    ]

    issues = lint_final_script(payload)

    assert sum("underspecified-business-object" in issue for issue in issues) == 2


def test_lint_final_script_flags_semantically_incomplete_onscreen_headings() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {"heading": "国家统一基础", "text": "四大方向、八项能力和六项技术文件"},
        {"heading": "方法底座", "text": "采用GB/T 13016组织标准体系"},
        {"heading": "共同目标", "text": "形成可持续更新的行业标准体系"},
    ]

    issues = lint_final_script(payload)

    assert sum("ONSCREEN_HEADING_INCOMPLETE" in issue for issue in issues) == 3


def test_lint_final_script_allows_claim_and_formal_taxonomy_headings() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {"heading": "国家规则已明确建设要求", "text": "四大方向、八项能力和六项技术文件"},
        {"heading": "A 基础通用", "text": "统一术语、架构、标识和目录"},
    ]

    issues = lint_final_script(payload)

    assert not any("ONSCREEN_HEADING_INCOMPLETE" in issue for issue in issues)


def test_lint_final_script_flags_heading_that_omits_the_business_matter() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {"heading": "国家已明确建设内容、进度和技术规则", "text": "四大方向、八项能力和三个阶段"},
        {"heading": "后续推进四项工作", "text": "完善体系、研制标准、实施评估、项目统筹"},
    ]

    issues = lint_final_script(payload)

    assert sum("ONSCREEN_HEADING_OBJECT_OMITTED" in issue for issue in issues) == 2


def test_lint_final_script_allows_heading_with_explicit_business_matter() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {
            "heading": "国家部署已明确数据基础设施建设内容、进度和技术规则",
            "text": "四大方向、八项能力和三个阶段",
        }
    ]

    issues = lint_final_script(payload)

    assert not any("ONSCREEN_HEADING_OBJECT_OMITTED" in issue for issue in issues)


def test_lint_final_script_flags_incomplete_full_copy_topic_sentence() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["full_copy"] = "实践基础。企业已经形成数据治理积累。\n\n国家层面已经把建设任务具体化。"

    issues = lint_final_script(payload)

    assert sum("FULL_COPY_TOPIC_INCOMPLETE" in issue for issue in issues) == 2


def test_lint_final_script_flags_source_strength_replaced_by_summary_dimensions() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["full_copy"] = (
        "国家部署已经形成覆盖建设内容、阶段进度和技术规则的数据基础设施建设安排。"
    )

    issues = lint_final_script(payload)

    assert any("FULL_COPY_TOPIC_SOURCE_STRENGTH_ABSTRACTED" in issue for issue in issues)

def test_lint_final_script_flags_flat_long_multi_step_full_copy() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["full_copy"] = payload["slides"][0]["full_copy"].replace("\n\n", "")
    issues = lint_final_script(payload)
    assert any("FULL_COPY_STRUCTURE_FLAT" in issue for issue in issues)

def test_lint_final_script_flags_onscreen_unrelated_to_core_message() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {"heading": "组织保障", "text": "明确牵头单位与协作职责"},
        {"heading": "资源保障", "text": "落实经费投入与人才配置"},
    ]
    issues = lint_final_script(payload)
    assert any("ONSCREEN_CORE_MISALIGNED" in issue for issue in issues)

def test_lint_final_script_allows_onscreen_projection_without_verbatim_repetition() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["core_message"] = "统一目录和身份管理共同支撑可追溯的数据流通。"
    payload["slides"][0]["onscreen"] = [
        {"heading": "目录与身份管理", "text": "共同建立可追溯的数据流通基础"}
    ]
    issues = lint_final_script(payload)
    assert not any("ONSCREEN_CORE_MISALIGNED" in issue for issue in issues)


def test_lint_final_script_flags_dangling_onscreen_modifier() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {
            "heading": "电力行业亟需构建覆盖全生命周期的标准体系",
            "text": "以《国家数据基础设施建设指引》为总纲，结合电力行业专业特点",
            "items": ["建设依据：以国家数据基础设施建设指引为总纲"],
        }
    ]

    issues = lint_final_script(payload)

    assert sum("ONSCREEN_DANGLING_MODIFIER" in issue for issue in issues) == 2


def test_lint_final_script_allows_complete_label_relation_and_modifier_clause() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {
            "heading": "电力行业亟需构建覆盖全生命周期的标准体系",
            "text": "本项研究以国家指引为依据构建电力行业标准体系",
            "items": [
                "覆盖范围：电力数据全生命周期和全产业链",
                "通过标准验证检验标准适用性",
                "数据资产管理：通过DCMM最高等级评价",
            ],
        }
    ]

    issues = lint_final_script(payload)

    assert not any("ONSCREEN_DANGLING_MODIFIER" in issue for issue in issues)


def test_lint_final_script_flags_generic_label_tail() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {"heading": "标准体系建设需要明确依据", "items": ["建设依据：国家政策"]}
    ]

    issues = lint_final_script(payload)

    assert any("ONSCREEN_DETAIL_GENERIC" in issue for issue in issues)


def test_lint_final_script_flags_taxonomy_codes_without_business_names() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {
            "heading": "关键子体系对应先行先试项目四类能力",
            "items": ["三统一：A3 + D3", "安全保障：F类"],
        }
    ]

    issues = lint_final_script(payload)

    assert sum("ONSCREEN_CODE_WITHOUT_NAME" in issue for issue in issues) == 2


def test_lint_final_script_allows_taxonomy_codes_with_business_names() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [
        {
            "heading": "关键子体系对应先行先试项目四类能力",
            "items": [
                "三统一：A3标识与目录 + D3身份与接入",
                "安全保障：F类安全保障标准",
            ],
        }
    ]

    issues = lint_final_script(payload)

    assert not any("ONSCREEN_CODE_WITHOUT_NAME" in issue for issue in issues)

def test_lint_final_script_flags_restating_aside_in_speaker_notes() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["speaker_notes"] = "也就是说，这一页的结论是可以直接复用的。"
    issues = lint_final_script(payload)
    assert issues
    assert any("restating-aside" in issue for issue in issues)

def test_lint_final_script_exempts_mission_from_self_reference_rule() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["mission"] = "收束全篇，呼应第一章确立的行业问题与平台定位。"
    issues = lint_final_script(payload)
    assert not any("self-reference" in issue for issue in issues)

def test_lint_final_script_flags_additional_contrastive_reveal_variants() -> None:
    payload = copy.deepcopy(_example())
    for sentence in (
        "定位的可信度不在于表述本身，而在于能否找到支撑证据。",
        "与其等平台建成再介入，不如现在就开始对接。",
        "宁可从小范围试点开始，也不一次性签约重型流程。",
        "这三种形态既非互不相关，也非固定不变。",
    ):
        payload["slides"][0]["full_copy"] = sentence
        issues = lint_final_script(payload)
        assert any("contrastive-reveal" in issue for issue in issues), sentence

def test_lint_final_script_flags_slide_meta_reference_in_speaker_notes() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["speaker_notes"] = "这一页说明的是平台的三重定位与上一页压力的对应关系。"
    issues = lint_final_script(payload)
    assert any("speaker-notes-slide-meta" in issue for issue in issues)

def test_lint_final_script_flags_host_meta_framing_in_speaker_notes() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["speaker_notes"] = "各位同事，接下来看平台的运行机制。"
    issues = lint_final_script(payload)
    assert any("speaker-notes-host-meta" in issue for issue in issues)

def test_lint_final_script_flags_third_person_audience_reference_in_speaker_notes() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["speaker_notes"] = "便于听众判断自己最关心哪个环节。"
    issues = lint_final_script(payload)
    assert issues
    assert any("third-person-audience-reference" in issue for issue in issues)

def test_lint_final_script_flags_stage_direction_label_in_speaker_notes() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["speaker_notes"] = "过渡语：接下来说明平台的运行机制。"
    issues = lint_final_script(payload)
    assert issues
    assert any("stage-direction-label" in issue for issue in issues)

def test_lint_final_script_third_person_audience_reference_scoped_to_speaker_notes_only() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["full_copy"] = "本材料的目标受众是尚未深入了解平台的潜在合作伙伴。"
    issues = lint_final_script(payload)
    assert not any("third-person-audience-reference" in issue for issue in issues)

def test_lint_final_script_ignores_source_refs_and_relationship_labels() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["source_refs"] = ["也就是说"]
    payload["slides"][0]["relationships"] = [{"from": "也就是说", "to": "也就是说", "relation": "有关"}]
    assert lint_final_script(payload) == []

def test_check_onscreen_structure_passes_on_clean_example() -> None:
    assert check_onscreen_structure(_example()) == []

def test_check_onscreen_structure_flags_duplicate_heading_on_same_slide() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "同名模块", "text": "a"}, {"heading": "同名模块", "text": "b"}]
    issues = check_onscreen_structure(payload)
    assert issues
    assert any("同名模块" in issue for issue in issues)

def test_check_onscreen_structure_ignores_headings_across_different_slides() -> None:
    payload = copy.deepcopy(_example())
    heading = payload["slides"][0]["onscreen"][0]["heading"]
    if len(payload["slides"]) > 1 and payload["slides"][1].get("onscreen"):
        payload["slides"][1]["onscreen"][0]["heading"] = heading
    assert check_onscreen_structure(payload) == []

def test_check_full_copy_duplication_passes_on_clean_example() -> None:
    assert check_full_copy_duplication(_example()) == []

def test_check_full_copy_duplication_flags_restated_sentence() -> None:
    """Regression fixture: the real repeated sentence found in P04's full_copy during the
    2026-08-28 content-density root-cause investigation (see
    projects/power-data-infrastructure-standard-system-research-20260828-002/
    workbench/analysis/p04-stage01-content-density-code-root-cause-analysis.md)."""
    payload = copy.deepcopy(_example())
    payload["slides"][0]["full_copy"] = (
        "与此同时，国家能源局发布《能源行业数据分类分级指南（2026年版）》等制度安排，"
        "进一步补充能源数据分类分级和安全管理要求。"
        "与此同时，国家能源局发布《能源行业数据分类分级指南（2026年版）》等制度安排，"
        "进一步补充能源数据分类分级和安全管理要求。"
    )
    issues = check_full_copy_duplication(payload)
    assert issues
    assert any("FULL_COPY_DUPLICATION" in issue for issue in issues)

def test_check_full_copy_duplication_ignores_short_unrelated_sentences() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["full_copy"] = "现状如此。因此如此。"
    assert check_full_copy_duplication(payload) == []

def test_outline_final_script_reports_module_count_matching_headings() -> None:
    rows = outline_final_script(_example())
    assert rows
    for row in rows:
        assert row["onscreen_module_count"] == len(row["onscreen_headings"])

def test_check_speaker_notes_length_flags_placeholder_stub() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["speaker_notes"] = "过渡。"
    issues = check_speaker_notes_length(payload)
    assert issues
    assert "3 characters" in issues[0] or "characters" in issues[0]

def test_check_speaker_notes_length_ignores_absent_field() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0].pop("speaker_notes", None)
    assert check_speaker_notes_length(payload) == []

def test_check_speaker_notes_length_passes_normal_note() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["speaker_notes"] = "这一页说明的是平台运行机制的整体轮廓。"
    assert check_speaker_notes_length(payload) == []

def test_check_declared_count_flags_mismatch_between_subtitle_and_modules() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["subtitle"] = "五方面基础"
    payload["slides"][0]["onscreen_expected_peer_count"] = 5
    payload["slides"][0]["onscreen"] = [{"heading": h} for h in ("一", "二", "三", "四")]
    warnings = check_declared_count(payload)
    assert warnings
    assert "expects 5 visible peers" in warnings[0]

def test_check_declared_count_matches_when_addendum_excluded() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["subtitle"] = "五个维度"
    payload["slides"][0]["onscreen_expected_peer_count"] = 5
    payload["slides"][0]["onscreen"] = [{"heading": h} for h in ("一", "二", "三", "四", "五", "此外：储备方向")]
    assert check_declared_count(payload) == []

def test_check_declared_count_skips_ambiguous_compound_subtitle() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["subtitle"] = "六类角色·四类模式"
    payload["slides"][0]["onscreen"] = [{"heading": h} for h in ("一", "二", "三")]
    assert check_declared_count(payload) == []


def test_check_declared_count_skips_intrinsic_title_count_without_visible_peer_contract() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["title"] = "形成七大类标准体系框架"
    payload["slides"][0]["onscreen"] = [{"heading": "研究结论"}]
    assert check_declared_count(payload) == []

def test_check_onscreen_detail_length_flags_overlong_item() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "模块", "items": ["需求识别到持续优化经过八个连续环节层层推进形成完整闭环缺一不可"]}]
    issues = check_onscreen_detail_length(payload)
    assert issues
    assert "meaningful characters (> 30)" in issues[0]

def test_check_onscreen_detail_length_allows_complete_proposition_as_module_lead() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{
        "heading": "模块",
        "text": "国家技术文件明确基础能力边界并规定行业实施细则的转化方向和接口衔接要求",
    }]
    assert check_onscreen_detail_length(payload) == []

def test_check_onscreen_detail_length_allows_unpunctuated_module_lead() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{
        "heading": "模块",
        "text": "国家技术文件明确基础能力边界并规定行业实施细则的转化方向和接口衔接要求",
    }]
    assert check_onscreen_detail_length(payload) == []

def test_check_onscreen_terminal_punctuation_rejects_visible_terminal_glyphs() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{
        "heading": "模块：",
        "text": "标准体系需要保持层次清晰。",
        "items": ["目录描述；"],
    }]
    issues = check_onscreen_terminal_punctuation(payload)
    assert len(issues) == 3
    assert all("must not end" in issue for issue in issues)

def test_check_onscreen_detail_length_blocks_complete_proposition_above_sentence_ceiling() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "模块", "items": ["判" * 91 + "。"]}]
    issues = check_onscreen_detail_length(payload)
    assert issues
    assert "meaningful characters (> 30)" in issues[0]

def test_check_onscreen_detail_length_checks_each_separator_delimited_phrase() -> None:
    """The 30-char ceiling applies per punctuation-separated phrase, not to the whole line: a PPT
    line legitimately holds several short parallel phrases (e.g. '供得出、流得动、用得好、保安全')
    whose concatenated length exceeds 30, distinct from a Word-style run-on sentence."""
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "模块", "items": ["需求识别、资源组织、产品形成、客户订购、授权交付、计量结算、运营评价、持续优化"]}]
    assert check_onscreen_detail_length(payload) == []

def test_check_onscreen_detail_length_measures_only_body_after_label() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "模块", "items": ["内容：" + "判" * 30]}]
    assert check_onscreen_detail_length(payload) == []
    payload["slides"][0]["onscreen"][0]["items"] = ["内容：" + "判" * 31]
    assert check_onscreen_detail_length(payload) != []

def test_check_onscreen_detail_length_passes_short_phrases() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "模块", "text": "统一规则促进流通", "items": ["内容：明确权责", "成果：形成清单"]}]
    assert check_onscreen_detail_length(payload) == []

def test_check_onscreen_detail_length_ignores_headings() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"] = [{"heading": "一个非常长的标题超过三十个字用来测试标题是否被忽略而不触发上屏文字密度检查规则"}]
    assert check_onscreen_detail_length(payload) == []

def test_power_industry_deck_final_script_passes_lint() -> None:
    """Regression test: the delivered power-industry-data-infrastructure deck previously leaked
    register drift, self-referential structure commentary, and contrastive-reveal sentences into
    the final script. Keep it clean so those specific, already-paid-for mistakes do not silently
    return."""
    path = ROOT / "tests" / "script_engine" / "fixtures" / "curated" / "power-industry-data-infrastructure-final-script.json"
    assert lint_final_script(json.loads(path.read_text(encoding="utf-8"))) == []

def test_power_industry_deck_architecture_page_uses_short_title_with_subtitle() -> None:
    """Regression test: the architecture page's title was the compound '总体架构：五层两贯穿'
    (repeating the subtitle inside the title, an Echo-test violation). Now: a short generic
    title ('总体架构') with the business-specific content only in `subtitle` ('五层两贯穿').
    Page ID for this content has moved across deck replans (was P11, now P12) — find it by
    subtitle rather than a pinned ID."""
    path = ROOT / "tests" / "script_engine" / "fixtures" / "curated" / "power-industry-data-infrastructure-final-script.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    slide = next(s for s in payload["slides"] if s.get("subtitle") == "五层两贯穿")
    assert slide["title"] == "总体架构"

def test_power_industry_deck_final_script_has_no_duplicate_onscreen_headings() -> None:
    path = ROOT / "tests" / "script_engine" / "fixtures" / "curated" / "power-industry-data-infrastructure-final-script.json"
    assert check_onscreen_structure(json.loads(path.read_text(encoding="utf-8"))) == []

def test_power_industry_deck_architecture_page_delivers_five_layer_modules_plus_marked_addendum() -> None:
    """Regression test for a count-claim bug class: a page declaring N components must show
    exactly N peer modules, with any extra material clearly marked as an addendum rather than
    silently folded in or left unmarked. The five-layer/two-cross-cutting architecture page
    (subtitle '五层两贯穿') is the deck's instance of this pattern — 5 layer modules plus one
    addendum module prefixed '此外：' for the two cross-cutting items. Page ID moves across
    deck replans (was P17, now P12); find it by subtitle rather than a pinned ID."""
    path = ROOT / "tests" / "script_engine" / "fixtures" / "curated" / "power-industry-data-infrastructure-final-script.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    slide = next(s for s in payload["slides"] if s.get("subtitle") == "五层两贯穿")
    headings = [m["heading"] for m in slide["onscreen"]]
    assert len(headings) == 6
    assert headings[-1].startswith("此外：")
    assert len([h for h in headings if not h.startswith("此外")]) == 5

def test_power_industry_deck_p06_delivers_five_basis_modules() -> None:
    """Regression test for a second count-claim bug caught by check_declared_count: subtitle said
    五方面基础 but the last two dimensions (场景储备/实施推进) had been merged into one onscreen
    module, leaving only 4 visible. Now: 5 separate modules."""
    path = ROOT / "tests" / "script_engine" / "fixtures" / "curated" / "power-industry-data-infrastructure-final-script.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    slide = next(s for s in payload["slides"] if s["id"] == "P06")
    assert len(slide["onscreen"]) == 5

def test_power_industry_deck_final_script_has_no_declared_count_warnings() -> None:
    """This deck currently has zero count-claim mismatches. Pin that state so a genuinely new
    mismatch (like the P06 bug this suite caught previously) doesn't blend in unnoticed."""
    path = ROOT / "tests" / "script_engine" / "fixtures" / "curated" / "power-industry-data-infrastructure-final-script.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert check_declared_count(payload) == []
