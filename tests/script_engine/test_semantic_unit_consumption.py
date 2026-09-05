from __future__ import annotations

from script_engine.analysis_audit import audit_deck_plan, audit_final_script


def _foundation() -> dict:
    return {
        "source_consumption_policy": "required",
        "source_structure": [],
        "facts": [
            {
                "id": "ST0001",
                "statement": "国家数据基础设施建设进入全面实施阶段，明确总体架构和数据全生命周期要求。",
                "status": "来源陈述",
                "semantic_units": [
                    {"id": "ST0001#0", "text": "国家数据基础设施建设进入全面实施阶段", "claim_role": "fact"},
                ],
            },
            {
                "id": "ST0002",
                "statement": "电力行业已形成六项配套技术文件，为标准落地提供统一依据。",
                "status": "来源陈述",
                "number_refs": ["N0001"],
            },
            {
                "id": "ST0003",
                "statement": "行业协会负责统筹标准宣贯与执行监督工作。",
                "status": "来源陈述",
                "entity_refs": ["E0001"],
            },
            {
                "id": "ST0004",
                "statement": "试点单位已完成首批数据接口改造并进入验收阶段。",
                "status": "来源陈述",
                "conditions": ["完成首批接口改造后方可验收"],
            },
        ],
        "numbers": [
            {"id": "N0001", "value": "6", "unit": "项"},
        ],
        "entities": [
            {"id": "E0001", "name": "中国电力企业联合会"},
        ],
        "concepts": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
    }


def _page(source_refs: list[str] | None = None) -> dict:
    """A v2 lean Deck Plan page: only the source_refs boundary, no AUTHOR fields."""
    return {
        "id": "P01",
        "title": "国家部署",
        "page_role": "content",
        "question": "国家部署提供了哪些建设依托",
        "logic": "并列",
        "source_refs": source_refs if source_refs is not None else ["ST0001", "ST0002", "ST0003", "ST0004"],
    }


def _plan(page: dict | None = None) -> dict:
    return {
        "communication_goal": "说明国家部署背景",
        "plan_contract_version": 2,
        "planning_profile": "lean",
        "source_structure_mode": "preserve",
        "chapters": [],
        "pages": [page or _page()],
    }


def _final(source_refs: list[str], full_copy: str, onscreen_items: list[str] | None = None) -> dict:
    return {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "国家部署",
                "core_message": "国家部署明确总体架构与配套依据",
                "source_refs": source_refs,
                "full_copy": full_copy,
                "onscreen": [
                    {
                        "heading": "国家环境",
                        "items": onscreen_items or ["国家建设进入全面实施阶段"],
                    }
                ],
            }
        ]
    }


def test_lean_plan_only_requires_source_refs_boundary() -> None:
    """PLAN must not be blocked by any AUTHOR-owned source_consumption contract:
    that field is forbidden on PLAN pages and is audited post-hoc against the
    Final Script instead."""
    issues, _ = audit_deck_plan(_plan(), _foundation())
    assert not any("SOURCE_CONSUMPTION" in issue for issue in issues)
    assert not any("AUTHOR_FIELDS_FORBIDDEN" in issue for issue in issues)


def test_final_requires_slide_to_declare_actual_source_refs() -> None:
    final = _final([], "国家数据基础设施建设进入全面实施阶段，明确总体架构。")
    issues, _ = audit_final_script(final, _plan(), _foundation())
    assert any("AUTHOR_SOURCE_CONSUMPTION_MISSING" in issue for issue in issues)


def test_final_rejects_declared_ref_outside_plan_scope() -> None:
    page = _page(["ST0001", "ST0002", "ST0003"])
    final = _final(
        ["ST0001", "ST0002", "ST0003", "ST0004"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。"
        "电力行业已形成六项配套技术文件，为标准落地提供统一依据。"
        "行业协会负责统筹标准宣贯与执行监督工作。",
    )
    issues, _ = audit_final_script(final, _plan(page), _foundation())
    assert any("AUTHOR_SOURCE_REF_OUTSIDE_PLAN_SCOPE" in issue and "ST0004" in issue for issue in issues)


def test_final_rejects_unknown_source_ref() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003", "ST9999"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。"
        "电力行业已形成六项配套技术文件，为标准落地提供统一依据。"
        "行业协会负责统筹标准宣贯与执行监督工作。",
    )
    issues, _ = audit_final_script(final, _plan(), _foundation())
    assert any("AUTHOR_SOURCE_REF_UNKNOWN" in issue and "ST9999" in issue for issue in issues)


def test_final_requires_minimum_distinct_facts_for_a_multi_source_page() -> None:
    """A strict sourced page with several available facts cannot rest the whole
    argument on a single declared record."""
    final = _final(["ST0001"], "国家数据基础设施建设进入全面实施阶段。")
    issues, _ = audit_final_script(final, _plan(), _foundation())
    assert any("AUTHOR_SOURCE_CONSUMPTION_TOO_NARROW" in issue for issue in issues)


def test_final_lowers_the_distinct_fact_floor_for_a_short_sourced_page() -> None:
    """A page whose PLAN scope only has one source_ref cannot be held to the
    three-fact floor (v2 lean's own evidence-selection freedom)."""
    page = _page(["ST0001"])
    final = _final(["ST0001"], "国家数据基础设施建设进入全面实施阶段，明确总体架构和数据全生命周期要求。")
    issues, _ = audit_final_script(final, _plan(page), _foundation())
    assert not any("AUTHOR_SOURCE_CONSUMPTION_TOO_NARROW" in issue for issue in issues)


def test_final_flags_semantics_lost_when_full_copy_ignores_a_declared_source() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。今年工作稳步推进，各方持续关注进展。",
    )
    issues, _ = audit_final_script(final, _plan(), _foundation())
    assert any("AUTHOR_SOURCE_SEMANTICS_LOST" in issue and "ST0002" in issue for issue in issues)
    assert any("AUTHOR_SOURCE_SEMANTICS_LOST" in issue and "ST0003" in issue for issue in issues)


def test_final_flags_protected_number_lost() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。"
        "电力行业已形成配套技术文件，为标准落地提供统一依据。"
        "行业协会负责统筹标准宣贯与执行监督工作。",
    )
    issues, _ = audit_final_script(final, _plan(), _foundation())
    assert any("AUTHOR_NUMBER_OR_DATE_LOST" in issue and "ST0002" in issue for issue in issues)


def test_final_flags_protected_entity_lost() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。"
        "电力行业已形成六项配套技术文件，为标准落地提供统一依据。"
        "有关方面负责统筹标准宣贯与执行监督工作。",
    )
    issues, _ = audit_final_script(final, _plan(), _foundation())
    assert any("AUTHOR_RESPONSIBILITY_LOST" in issue and "ST0003" in issue for issue in issues)


def test_final_flags_protected_condition_lost() -> None:
    page = _page(["ST0004"])
    final = _final(["ST0004"], "试点单位已完成首批数据接口改造并进入验收阶段。")
    issues, _ = audit_final_script(final, _plan(page), _foundation())
    assert any("AUTHOR_CONDITION_LOST" in issue and "ST0004" in issue for issue in issues)


def test_final_passes_for_a_well_authored_lean_page() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构和数据全生命周期要求。"
        "电力行业已形成6项配套技术文件，为标准落地提供统一依据。"
        "行业协会（中国电力企业联合会）负责统筹标准宣贯与执行监督工作。",
        onscreen_items=["国家建设进入全面实施阶段", "电力行业已形成6项配套技术文件"],
    )
    issues, _ = audit_final_script(final, _plan(), _foundation())
    assert not any(
        issue.split(": ", 1)[-1].startswith("AUTHOR_SOURCE")
        or "AUTHOR_NUMBER_OR_DATE_LOST" in issue
        or "AUTHOR_RESPONSIBILITY_LOST" in issue
        or "AUTHOR_CONDITION_LOST" in issue
        for issue in issues
    )


def test_pages_without_source_refs_are_not_subject_to_the_strict_gate() -> None:
    """A page that carries no source_refs at all (e.g. a purely narrative page) is
    outside requires_source_consumption's scope and must not be blocked."""
    page = _page([])
    plan = _plan(page)
    final = _final([], "本页不引用任何 Foundation 记录。")
    plan_issues, _ = audit_deck_plan(plan, _foundation())
    final_issues, _ = audit_final_script(final, plan, _foundation())
    assert not any("SOURCE_CONSUMPTION" in issue for issue in plan_issues)
    assert not any(code in issue for issue in final_issues for code in ("AUTHOR_SOURCE_CONSUMPTION_MISSING",))


def test_final_rejects_thin_single_block_for_multi_fact_page() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段。电力行业已形成6项配套技术文件。"
        "中国电力企业联合会负责标准宣贯与执行监督。",
        onscreen_items=["国家建设进入全面实施阶段", "电力行业已形成6项配套技术文件"],
    )

    issues, _ = audit_final_script(final, _plan(), _foundation())

    assert any("AUTHOR_FULL_COPY_TOO_THIN" in issue for issue in issues)


def test_final_rejects_onscreen_claim_absent_from_full_copy() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。\n\n"
        "电力行业已形成6项配套技术文件，中国电力企业联合会负责标准宣贯与监督。",
        onscreen_items=["平台已经自动完成全部模型审批", "各省已经进入实时调度运行"],
    )

    issues, _ = audit_final_script(final, _plan(), _foundation())

    assert any("AUTHOR_ONSCREEN_FULL_COPY_DISCONNECTED" in issue for issue in issues)


def test_final_rejects_protected_full_copy_number_lost_from_onscreen() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。\n\n"
        "电力行业已形成6项配套技术文件，中国电力企业联合会负责标准宣贯与监督。",
        onscreen_items=["国家建设进入全面实施阶段", "行业协会负责标准宣贯与监督"],
    )

    issues, _ = audit_final_script(final, _plan(), _foundation())

    assert any("AUTHOR_ONSCREEN_NUMBER_OR_DATE_LOST" in issue and "6项" in issue for issue in issues)


def test_final_rejects_protected_responsibility_lost_from_onscreen() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。\n\n"
        "电力行业已形成6项配套技术文件，中国电力企业联合会负责标准宣贯与监督。",
        onscreen_items=["国家建设进入全面实施阶段", "电力行业已形成6项配套技术文件"],
    )

    issues, _ = audit_final_script(final, _plan(), _foundation())

    assert any("AUTHOR_ONSCREEN_RESPONSIBILITY_LOST" in issue for issue in issues)


def test_final_accepts_verbatim_full_copy_as_safe_onscreen_fallback() -> None:
    full_copy = (
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。\n\n"
        "电力行业已形成6项配套技术文件，中国电力企业联合会负责标准宣贯与监督。"
    )
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        full_copy,
        onscreen_items=[full_copy],
    )
    final["slides"][0]["onscreen"][0]["heading"] = final["slides"][0]["core_message"]

    issues, _ = audit_final_script(final, _plan(), _foundation())

    assert not any("AUTHOR_ONSCREEN_" in issue for issue in issues)


def test_final_rejects_relationship_that_exists_only_in_metadata() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。\n\n"
        "电力行业已形成6项配套技术文件，中国电力企业联合会负责标准宣贯与监督。",
        onscreen_items=["国家建设进入全面实施阶段", "电力行业已形成6项配套技术文件"],
    )
    final["slides"][0]["relationships"] = [
        {"from": "数据底座", "to": "政策发布", "relation": "自动驱动"}
    ]

    issues, _ = audit_final_script(final, _plan(), _foundation())

    assert any("AUTHOR_RELATIONSHIP_METADATA_ONLY" in issue for issue in issues)


def test_final_rejects_relation_claim_without_materialized_edge() -> None:
    final = _final(
        ["ST0001", "ST0002", "ST0003"],
        "国家数据基础设施建设进入全面实施阶段，明确总体架构。\n\n"
        "配套技术文件与协会统筹工作共同支撑标准落地，形成执行闭环。",
        onscreen_items=["总体架构明确建设边界", "配套文件与协会统筹形成执行闭环"],
    )
    final["slides"][0]["core_message"] = "总体架构与配套机制贯通形成执行闭环"

    issues, _ = audit_final_script(final, _plan(), _foundation())

    assert any("AUTHOR_RELATIONSHIP_NOT_MATERIALIZED" in issue for issue in issues)
