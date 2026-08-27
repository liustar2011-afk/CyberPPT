from __future__ import annotations

from cyberppt.content_route import audit_content_route, resolve_content_route
from cyberppt.page_logic_contract import render_page_logic_contract
from script_engine.analysis_audit import audit_deck_plan, audit_final_script
from script_engine.contracts import validate_deck_plan


def _page(**overrides: object) -> dict[str, object]:
    page: dict[str, object] = {
        "id": "P06",
        "question": "标准体系建设的差距集中在哪些方面？",
        "message": "共性规则与场景供给需要协同完善。",
        "logic": "差距归纳",
        "content": ["共性规则", "场景供给"],
    }
    page.update(overrides)
    return page


def _plan(page: dict[str, object]) -> dict[str, object]:
    return {
        "communication_goal": "说明建设重点",
        "evidence_fit_review_mode": "strict",
        "chapters": [],
        "pages": [page],
    }


def _foundation() -> dict[str, object]:
    return {
        "source_structure": [],
        "facts": [],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }


def test_page_keeps_source_native_fallback_without_route_audit_change() -> None:
    page = _page()
    assert resolve_content_route(page).primary == "source_native"
    assert validate_deck_plan(_plan(page)) == []
    issues, warnings = audit_deck_plan(_plan(page), _foundation())
    assert issues == []
    assert warnings == []


def test_explicit_author_route_wins_over_inference() -> None:
    page = _page(
        argument_role="gap",
        content_route={
            "primary": "diagnosis",
            "facets": ["current", "risk"],
            "confidence": "high",
            "basis": ["argument_role", "page_mission"],
            "rationale": "页面归纳当前差距及其影响。",
            "meaning_signals": ["服务供给风险"],
        },
    )
    decision = resolve_content_route(page)
    assert decision.primary == "diagnosis"
    assert decision.source == "author"
    assert audit_content_route(page) == []


def test_argument_role_maps_only_to_a_route_hint() -> None:
    assert resolve_content_route(_page(argument_role="foundation")).primary == "state"
    assert resolve_content_route(_page(argument_role="solution")).primary == "system"
    assert resolve_content_route(_page(argument_role="implementation")).primary == "action"


def test_ambiguous_page_logic_falls_back_without_title_keyword_guessing() -> None:
    page = _page(
        title="下一步推进安排",
        page_logic_contract={
            "nodes": [
                {"role": "context"},
                {"role": "requirement"},
            ]
        },
    )
    decision = resolve_content_route(page)
    assert decision.primary == "source_native"
    assert decision.source == "fallback"


def test_schema_and_audit_reject_invalid_or_structural_routes() -> None:
    invalid = _page(
        content_route={
            "primary": "consulting",
            "facets": ["current", "current"],
            "basis": [],
            "rationale": "test",
        }
    )
    assert validate_deck_plan(_plan(invalid))
    structural = _page(
        page_role="chapter",
        content_route={
            "primary": "state",
            "basis": ["page_mission"],
            "rationale": "章节导航。",
        },
    )
    assert any("structural pages" in issue for issue in audit_content_route(structural))


def test_explicit_route_conflicting_with_declared_role_is_an_error() -> None:
    page = _page(
        argument_role="gap",
        content_route={
            "primary": "action",
            "basis": ["argument_role"],
            "rationale": "尝试按工作安排组织。",
        },
    )
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("conflicts" in issue for issue in issues)


def test_required_page_logic_can_only_conflict_when_it_has_one_clear_route() -> None:
    page = _page(
        page_logic_contract_mode="required",
        page_logic_contract={"nodes": [{"role": "requirement"}]},
        content_route={
            "primary": "system",
            "basis": ["page_logic_contract.nodes"],
            "rationale": "测试已锁定逻辑冲突。",
        },
    )
    assert any("conflicts" in issue for issue in audit_content_route(page))


def test_explicit_route_requires_declared_evidence_instead_of_a_character_floor() -> None:
    page = _page(
        content_route={
            "primary": "state",
            "basis": ["page_mission"],
            "rationale": "说明当前建设基础。",
        },
    )
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("no declared source evidence" in issue for issue in issues)


def test_declared_business_meaning_must_survive_final_authoring() -> None:
    foundation = _foundation()
    foundation["facts"] = [{"id": "F1", "statement": "建立协同机制。"}]
    page = _page(
        source_refs=["F1"],
        content_route={
            "primary": "action",
            "facets": ["coordination"],
            "basis": ["argument_role"],
            "rationale": "说明协同安排。",
            "meaning_signals": ["协同推进"],
        },
    )
    final = {
        "slides": [{
            "id": "P06",
            "page_type": "content",
            "title": "推进安排",
            "core_message": "明确工作安排。",
            "full_copy": "建立协同机制并明确责任。",
            "onscreen": [{"heading": "协同机制", "items": ["明确责任分工"]}],
        }]
    }
    issues, _ = audit_final_script(final, _plan(page), foundation)
    assert any("meaning signal" in issue for issue in issues)
    final["slides"][0]["onscreen"][0]["items"].append("协同推进")
    issues, _ = audit_final_script(final, _plan(page), foundation)
    assert not any("meaning signal" in issue for issue in issues)


def test_stage02_readiness_validates_stage01_preservation_without_running_stage02() -> None:
    page = _page(
        stage02_readiness={
            "continuous_sentence_signals": ["建设任务需要协同推进。"],
            "containers": [{"id": "coordination", "heading": "协同推进", "role": "module"}],
            "tables": [{"container_id": "coordination", "header_rows": 1}],
        },
    )
    final = {
        "slides": [{
            "id": "P06",
            "page_type": "content",
            "title": "推进安排",
            "core_message": "建设任务需要协同推进。",
            "full_copy": "协同机制明确各方责任。",
            "onscreen": [{"heading": "协同推进", "items": ["明确责任分工"]}],
        }]
    }
    assert validate_deck_plan(_plan(page)) == []
    issues, _ = audit_final_script(final, _plan(page), _foundation())
    assert issues == []
    final["slides"][0]["onscreen"][0]["heading"] = "工作安排"
    issues, _ = audit_final_script(final, _plan(page), _foundation())
    assert any("container heading" in issue for issue in issues)


def test_onscreen_composition_validates_mode_and_lead_budget() -> None:
    invalid = _page(onscreen_composition={"mode": "all_sentence_led"})
    assert validate_deck_plan(_plan(invalid))
    issues, _ = audit_deck_plan(_plan(invalid), _foundation())
    assert any("onscreen_composition.mode" in issue for issue in issues)

    missing_budget = _page(onscreen_composition={"mode": "selective_lead"})
    assert validate_deck_plan(_plan(missing_budget))
    issues, _ = audit_deck_plan(_plan(missing_budget), _foundation())
    assert any("positive integer lead_budget" in issue for issue in issues)


def test_onscreen_composition_enforces_evidence_first_and_selective_leads() -> None:
    final = {
        "slides": [{
            "id": "P06",
            "page_type": "content",
            "title": "验证场景",
            "core_message": "重点场景提供实践验证依托。",
            "full_copy": "重点场景用于检验标准的适用性和可操作性。",
            "onscreen": [
                {"heading": "行业治理", "text": "验证行业治理相关标准", "items": ["治理场景"]},
                {"heading": "市场运行", "text": "验证市场运行相关标准", "items": ["市场场景"]},
            ],
        }]
    }
    evidence_first = _page(onscreen_composition={"mode": "evidence_first"})
    issues, _ = audit_final_script(final, _plan(evidence_first), _foundation())
    assert sum("forbids module lead text" in issue for issue in issues) == 2

    selective = _page(onscreen_composition={"mode": "selective_lead", "lead_budget": 1})
    issues, _ = audit_final_script(final, _plan(selective), _foundation())
    assert any("permits at most 1 module lead" in issue for issue in issues)
    final["slides"][0]["onscreen"][1].pop("text")
    issues, _ = audit_final_script(final, _plan(selective), _foundation())
    assert not any("onscreen_composition" in issue for issue in issues)


def test_evidence_first_rejects_a_hidden_first_item_lead() -> None:
    final = {
        "slides": [{
            "id": "P06",
            "page_type": "content",
            "title": "建设要求",
            "core_message": "国家要求需要转化为行业标准。",
            "full_copy": "国家要求明确总体方向和技术基础。",
            "onscreen": [{
                "heading": "技术文件",
                "items": [
                    "参考架构、标识、目录和接入要求需要转化为行业细则",
                    "明确基础能力边界",
                    "衔接电力专业对象",
                ],
            }],
        }]
    }
    page = _page(onscreen_composition={"mode": "evidence_first"})
    issues, _ = audit_final_script(final, _plan(page), _foundation())
    assert any("lead-like first item" in issue for issue in issues)

    final["slides"][0]["onscreen"][0]["items"] = [
        "参考架构",
        "标识管理与目录描述",
        "接入连接器",
    ]
    issues, _ = audit_final_script(final, _plan(page), _foundation())
    assert not any("lead-like first item" in issue for issue in issues)


def test_evidence_first_keeps_parallel_complete_facts() -> None:
    final = {
        "slides": [{
            "id": "P06",
            "page_type": "content",
            "title": "阶段安排",
            "core_message": "建设安排按阶段推进。",
            "full_copy": "近期、中期和远期分别承担不同任务。",
            "onscreen": [{
                "heading": "建设节奏",
                "items": [
                    "近期阶段完成顶层设计并启动应用试点",
                    "中期阶段面向规模化建设完善标准供给",
                    "远期阶段形成完整数据基础设施能力",
                ],
            }],
        }]
    }
    page = _page(onscreen_composition={"mode": "evidence_first"})
    issues, _ = audit_final_script(final, _plan(page), _foundation())
    assert not any("lead-like first item" in issue for issue in issues)


def test_page_logic_review_renders_resolved_content_route() -> None:
    lines = render_page_logic_contract(_page(argument_role="solution"))
    assert any("内容路由：system" in line for line in lines)
