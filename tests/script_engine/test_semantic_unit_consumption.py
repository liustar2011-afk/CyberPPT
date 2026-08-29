from __future__ import annotations

from copy import deepcopy

from script_engine.analysis_audit import audit_deck_plan, audit_final_script


def _foundation() -> dict:
    return {
        "source_consumption_policy": "required",
        "source_structure": [],
        "facts": [
            {
                "id": "ST0001",
                "statement": "国家数据基础设施建设进入全面实施阶段，明确总体架构和数据全生命周期要求。",
                "coverage_anchors": ["全面实施阶段", "总体架构"],
                "semantic_units": [
                    {"id": "ST0001#0", "text": "国家数据基础设施建设进入全面实施阶段", "claim_role": "fact"},
                    {"id": "ST0001#1", "text": "明确总体架构和数据全生命周期要求", "claim_role": "fact"},
                    {"id": "ST0001#2", "text": "形成六项配套技术文件为行业建设提供统一依据", "claim_role": "fact"},
                ],
            },
        ],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }


def _page() -> dict:
    return {
        "id": "P01",
        "page_type": "content",
        "question": "国家部署提供了哪些建设依托",
        "message": "国家部署明确总体架构与配套依据",
        "logic": "并列",
        "content": ["国家部署"],
        "source_refs": ["ST0001"],
        "source_consumption": {
            "mode": "strict",
            "full_prose_anchors": [
                {"source_ref": "ST0001", "anchors": ["全面实施阶段", "总体架构"], "minimum_hits": 2}
            ],
            "onscreen_refs": ["ST0001"],
            "unit_dispositions": [
                {"source_ref": "ST0001", "unit_id": "ST0001#0", "disposition": "full_copy"},
                {"source_ref": "ST0001", "unit_id": "ST0001#1", "disposition": "full_copy"},
                {"source_ref": "ST0001", "unit_id": "ST0001#2", "disposition": "full_copy"},
            ],
        },
        "onscreen_contract": {
            "relation": "hierarchy",
            "detail_axis": "国家部署",
            "modules": [
                {
                    "heading": "国家环境",
                    "evidence_refs": ["ST0001"],
                    "required_signals": ["全面实施阶段"],
                }
            ],
        },
    }


def _plan(page: dict | None = None) -> dict:
    return {
        "communication_goal": "说明国家部署背景",
        "evidence_fit_review_mode": "strict",
        "chapters": [],
        "pages": [page or _page()],
    }


def _final(full_copy: str | None = None, onscreen_items: list[str] | None = None) -> dict:
    return {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "国家部署",
                "core_message": "国家部署明确总体架构与配套依据",
                "full_copy": full_copy
                or (
                    "国家数据基础设施建设进入全面实施阶段。明确总体架构和数据全生命周期要求。"
                    "形成六项配套技术文件为行业建设提供统一依据。"
                ),
                "onscreen": [
                    {
                        "heading": "国家环境",
                        "items": onscreen_items or ["国家建设进入全面实施阶段"],
                    }
                ],
            }
        ]
    }


def test_plan_requires_every_unit_of_a_full_copy_source_to_have_a_disposition() -> None:
    page = _page()
    page["source_consumption"]["unit_dispositions"].pop()  # drop ST0001#2
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any(
        "SOURCE_CONSUMPTION_UNIT_MISSING" in issue and "ST0001#2" in issue for issue in issues
    )


def test_plan_rejects_boilerplate_reason_on_reserved_unit() -> None:
    page = _page()
    page["source_consumption"]["unit_dispositions"][-1] = {
        "source_ref": "ST0001",
        "unit_id": "ST0001#2",
        "disposition": "reserved_for_later",
        "reason": "后续再说",
    }
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("SOURCE_CONSUMPTION_UNIT_REASON_MISSING" in issue for issue in issues)


def test_plan_accepts_specific_reason_on_reserved_unit() -> None:
    page = _page()
    page["source_consumption"]["unit_dispositions"][-1] = {
        "source_ref": "ST0001",
        "unit_id": "ST0001#2",
        "disposition": "reserved_for_later",
        "reason": "六项配套技术文件的具体内容留给后续标准清单页展开",
    }
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert not any("SOURCE_CONSUMPTION_UNIT" in issue for issue in issues)


def test_plan_flags_unknown_unit_id() -> None:
    page = _page()
    page["source_consumption"]["unit_dispositions"].append(
        {"source_ref": "ST0001", "unit_id": "ST0001#99", "disposition": "full_copy"}
    )
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("SOURCE_CONSUMPTION_UNIT_UNKNOWN" in issue for issue in issues)


def test_author_flags_semantic_unit_gap_when_full_copy_drops_a_unit() -> None:
    """Reproduces the root-cause report's 137-char counterexample: record-level anchors
    and protected fields survive, but a whole semantic unit silently disappears."""
    page = _page()
    plan = _plan(page)
    foundation = _foundation()
    # full_copy keeps the anchor phrases (full_prose_anchors still pass) but drops the
    # third semantic unit (six supporting technical documents) entirely.
    final = _final("国家数据基础设施建设进入全面实施阶段，明确总体架构和数据全生命周期要求。")

    issues, _ = audit_final_script(final, plan, foundation)
    assert not any("FULL_COPY_SOURCE_ANCHOR_MISSING" in issue for issue in issues)
    assert any(
        "FULL_COPY_SEMANTIC_UNIT_GAP" in issue and "ST0001#2" in issue for issue in issues
    )


def test_author_passes_when_every_full_copy_unit_is_expressed() -> None:
    page = _page()
    issues, _ = audit_final_script(_final(), _plan(page), _foundation())
    assert not any("FULL_COPY_SEMANTIC_UNIT_GAP" in issue for issue in issues)


def test_author_flags_onscreen_detail_insufficient_for_declared_onscreen_unit() -> None:
    page = _page()
    page["source_consumption"]["unit_dispositions"][0]["disposition"] = "onscreen"
    plan = _plan(page)
    foundation = _foundation()
    final = _final(onscreen_items=["国家部署"])  # too generic, drops the specific unit text

    issues, _ = audit_final_script(final, plan, foundation)
    assert any(
        "ONSCREEN_SOURCE_DETAIL_INSUFFICIENT" in issue and "ST0001#0" in issue for issue in issues
    )


def test_positional_ids_work_when_source_truth_did_not_assign_one() -> None:
    """Real Source Truth data has no ``semantic_units[].id`` field (see
    cyberppt/stage01_compiler.py); the audit must synthesize a stable
    ``{source_ref}#{index}`` id rather than requiring one to be persisted, since
    foundation_projection.py is a deliberately pure mechanical copy that must not
    add fields Source Truth didn't provide."""
    foundation = _foundation()
    for unit in foundation["facts"][0]["semantic_units"]:
        unit.pop("id")
    page = _page()
    issues, _ = audit_deck_plan(_plan(page), foundation)
    assert not any("SOURCE_CONSUMPTION_UNIT" in issue for issue in issues)


def test_pages_without_unit_dispositions_are_unaffected() -> None:
    page = _page()
    page["source_consumption"].pop("unit_dispositions")
    plan = _plan(page)
    foundation = _foundation()
    final = _final("国家数据基础设施建设进入全面实施阶段。")

    plan_issues, _ = audit_deck_plan(plan, foundation)
    final_issues, _ = audit_final_script(final, plan, foundation)
    assert not any("SOURCE_CONSUMPTION_UNIT" in issue for issue in plan_issues)
    assert not any(
        code in issue
        for issue in final_issues
        for code in ("FULL_COPY_SEMANTIC_UNIT_GAP", "ONSCREEN_SOURCE_DETAIL_INSUFFICIENT")
    )


def test_contract_v2_requires_unit_dispositions_on_strict_pages() -> None:
    page = _page()
    page["source_consumption"].pop("unit_dispositions")
    foundation = _foundation()
    foundation["source_consumption_contract_version"] = 2

    issues, _ = audit_deck_plan(_plan(page), foundation)

    assert any("SOURCE_CONSUMPTION_UNIT_CONTRACT_MISSING" in issue for issue in issues)


def test_contract_v2_rejects_source_record_without_semantic_units() -> None:
    page = _page()
    page["source_consumption"]["unit_dispositions"] = []
    foundation = _foundation()
    foundation["source_consumption_contract_version"] = 2
    foundation["facts"][0]["semantic_units"] = []

    issues, _ = audit_deck_plan(_plan(page), foundation)

    assert any("SOURCE_CONSUMPTION_FOUNDATION_UNITS_MISSING" in issue for issue in issues)


def test_author_rejects_label_enumeration_when_source_units_carry_detail() -> None:
    page = _page()
    page["onscreen_contract"]["modules"][0]["heading"] = "标准明细"
    foundation = _foundation()
    foundation["facts"][0]["semantic_units"] = [
        {
            "id": "ST0001#0",
            "text": "参考架构明确与国家数据基础设施总体架构的映射关系",
            "claim_role": "fact",
        },
        {
            "id": "ST0001#1",
            "text": "标识目录规定电力数据标识管理和目录描述要求",
            "claim_role": "fact",
        },
    ]
    final = _final(onscreen_items=["参考架构、标识目录"])
    final["slides"][0]["onscreen"][0]["heading"] = "标准明细"

    issues, _ = audit_final_script(final, _plan(page), foundation)

    assert any("collapses source-backed" in issue for issue in issues)


def test_author_accepts_explanatory_items_for_source_backed_labels() -> None:
    page = _page()
    page["onscreen_contract"]["modules"][0]["heading"] = "标准明细"
    foundation = _foundation()
    foundation["facts"][0]["semantic_units"] = [
        {
            "id": "ST0001#0",
            "text": "参考架构明确与国家数据基础设施总体架构的映射关系",
            "claim_role": "fact",
        },
        {
            "id": "ST0001#1",
            "text": "标识目录规定电力数据标识管理和目录描述要求",
            "claim_role": "fact",
        },
    ]
    final = _final(
        onscreen_items=[
            "参考架构：明确与国家总体架构的映射关系",
            "标识目录：规定电力数据标识和目录描述要求",
        ]
    )
    final["slides"][0]["onscreen"][0]["heading"] = "标准明细"

    issues, _ = audit_final_script(final, _plan(page), foundation)

    assert not any("collapses source-backed" in issue for issue in issues)
