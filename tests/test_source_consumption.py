from __future__ import annotations

from copy import deepcopy

from script_engine.analysis_audit import audit_deck_plan, audit_final_script


def _foundation() -> dict:
    return {
        "source_structure": [],
        "facts": [
            {"id": "ST1", "statement": "统一电力数据基础设施术语定义并衔接国家参考架构"},
            {"id": "ST2", "statement": "制定电力数据质量评价指标体系并覆盖全过程质量控制"},
            {"id": "ST3", "statement": "制定电力数据资产登记评估和入表相关标准"},
        ],
        "concepts": [], "entities": [], "relations": [], "arguments": [],
        "constraints": [], "numbers": [],
    }


def _strict_foundation() -> dict:
    foundation = deepcopy(_foundation())
    foundation["source_consumption_policy"] = "required"
    return foundation


def _page(source_refs: list[str] | None = None, *, page_role: str | None = None) -> dict:
    """A v2 lean Deck Plan page: only the source_refs boundary, no AUTHOR fields."""
    page = {
        "id": "P01",
        "question": "标准如何落地",
        "logic": "并列",
        "source_refs": source_refs if source_refs is not None else ["ST1", "ST2", "ST3"],
    }
    if page_role:
        page["page_role"] = page_role
    return page


def _plan(page: dict | None = None) -> dict:
    return {
        "communication_goal": "说明标准范围",
        "chapters": [],
        "pages": [page or _page()],
    }


def _final(
    source_refs: list[str],
    full_copy: str | None = None,
    *,
    core_message: str = "标准覆盖共同语言与资源治理",
    onscreen: list[dict] | None = None,
) -> dict:
    return {
        "slides": [{
            "id": "P01", "page_type": "content", "title": "标准范围",
            "core_message": core_message,
            "source_refs": source_refs,
            "full_copy": full_copy or (
                "统一电力数据基础设施术语定义并衔接国家参考架构。"
                "制定电力数据质量评价指标体系，覆盖全过程质量控制。"
            ),
            "onscreen": onscreen or [
                {"heading": "基础通用", "items": ["统一术语定义"]},
                {"heading": "数据资源", "items": ["覆盖全过程质量控制"]},
            ],
        }]
    }


def test_non_strict_foundation_never_blocks_on_source_consumption() -> None:
    issues, _ = audit_final_script(_final(["ST1", "ST2", "ST3"]), _plan(), _foundation())
    assert not any("AUTHOR_SOURCE" in issue for issue in issues)


def test_author_gate_rejects_structural_metadata_concatenated_into_full_copy() -> None:
    """Independent of source_consumption: AUTHOR must not paste document front
    matter/TOC labels or semicolon-joined source rows into full_copy."""
    page = _page(["ST1", "ST2", "ST3", "META1", "META2"])
    foundation = _strict_foundation()
    foundation["facts"].extend([
        {"id": "META1", "statement": "目 录"},
        {"id": "META2", "statement": "2026年7月"},
    ])
    final = _final(
        ["ST1", "ST2", "ST3", "META1", "META2"],
        "标准覆盖共同语言与资源治理；目 录；2026年7月；基础通用；数据资源；治理要求",
    )

    issues, _ = audit_final_script(final, _plan(page), foundation)

    assert any("AUTHOR_STRUCTURAL_METADATA_LEAK" in issue for issue in issues)
    assert any("AUTHOR_MECHANICAL_SOURCE_CONCATENATION" in issue for issue in issues)


def test_strict_foundation_missing_declaration_fails_at_author_not_plan() -> None:
    """A v2 lean Deck Plan cannot carry an AUTHOR-owned source_consumption
    contract, so a strict Foundation's policy is enforced post-hoc against the
    Final Script slide, not against PLAN."""
    page = _page()
    plan_issues, _ = audit_deck_plan(_plan(page), _strict_foundation())
    final_issues, _ = audit_final_script(
        _final([], "完全无关的完整稿"), _plan(page), _strict_foundation()
    )

    assert not any("SOURCE_CONSUMPTION_CONTRACT_MISSING" in issue for issue in plan_issues)
    assert any("AUTHOR_SOURCE_CONSUMPTION_MISSING" in issue for issue in final_issues)


def test_strict_structural_page_is_exempt_from_the_consumption_gate() -> None:
    page = _page(page_role="agenda")
    plan_issues, _ = audit_deck_plan(_plan(page), _strict_foundation())
    final_issues, _ = audit_final_script(_final([]), _plan(page), _strict_foundation())

    assert not any("SOURCE_CONSUMPTION" in issue for issue in plan_issues)
    assert not any("AUTHOR_SOURCE_CONSUMPTION_MISSING" in issue for issue in final_issues)


def test_declared_ref_outside_plan_scope_is_rejected() -> None:
    page = _page(["ST1", "ST2"])
    issues, _ = audit_final_script(_final(["ST1", "ST2", "ST3"]), _plan(page), _strict_foundation())
    assert any(
        "AUTHOR_SOURCE_REF_OUTSIDE_PLAN_SCOPE" in issue and "ST3" in issue for issue in issues
    )


def test_unknown_declared_ref_is_rejected() -> None:
    issues, _ = audit_final_script(_final(["ST1", "ST2", "ST9"]), _plan(), _strict_foundation())
    assert any("AUTHOR_SOURCE_REF_UNKNOWN" in issue and "ST9" in issue for issue in issues)


def _p01_regression_case() -> tuple[dict, dict, dict]:
    """Guards a real regression: full_copy can pass a coarse similarity check while
    silently dropping a source's protected number, condition, responsible actor or
    status strength."""
    foundation = {
        "source_consumption_policy": "required",
        "source_structure": [],
        "facts": [
            {
                "id": "ST0034",
                "statement": "标准体系应支撑绿色低碳领域具体应用。",
            },
            {
                "id": "ST0035",
                "statement": "相关要求自2026年7月1日起施行，数据分为一般、重要、核心三级。",
                "number_refs": ["N0035"],
            },
            {
                "id": "ST0036",
                "statement": "相关主体应落实安全责任，开展风险监测和应急处置。",
                "conditions": ["发生安全风险时"],
                "entity_refs": ["E-001"],
            },
            {
                "id": "ST0037",
                "statement": "推进可信数据空间建设、场景验证、标准验证和生态培育。",
                "status": "规划",
            },
        ],
        "numbers": [{"id": "N0035", "value": "2026年7月1日", "unit": "时间"}],
        "concepts": [],
        "entities": [{"id": "E-001", "name": "相关主体"}],
        "relations": [],
        "arguments": [],
        "constraints": [],
    }
    page = _page(["ST0034", "ST0035", "ST0036", "ST0037"])
    plan = _plan(page)
    return foundation, plan, page


def test_p01_compressed_copy_reports_specific_source_losses() -> None:
    foundation, plan, _ = _p01_regression_case()
    final = _final(
        ["ST0034", "ST0035", "ST0036", "ST0037"],
        "绿色发展、分类分级、安全管理和可信流通共同构成标准重点。",
    )

    issues, _ = audit_final_script(final, plan, foundation)
    joined = "\n".join(issues)

    for ref in ("ST0034", "ST0035", "ST0036", "ST0037"):
        assert ref in joined
    assert "AUTHOR_CONDITION_LOST" in joined
    assert "AUTHOR_RESPONSIBILITY_LOST" in joined
    assert "AUTHOR_STATUS_STRENGTH_LOST" in joined


def test_p01_source_specific_full_copy_passes_clean() -> None:
    foundation, plan, _ = _p01_regression_case()
    final = _final(
        ["ST0034", "ST0035", "ST0036", "ST0037"],
        "标准体系应支撑绿色低碳领域具体应用。相关要求自2026年7月1日起施行，"
        "数据分为一般、重要、核心三级。\n\n"
        "发生安全风险时，相关主体应落实安全责任，开展风险监测和应急处置。"
        "规划推进可信数据空间建设、场景验证、标准验证和生态培育。",
        core_message="标准体系覆盖绿色低碳、分类分级、安全责任与可信流通",
        onscreen=[
            {
                "heading": "分类分级与安全责任形成约束",
                "items": [
                    "相关要求自2026年7月1日起施行，数据分为一般、重要、核心三级",
                    "发生安全风险时，相关主体应落实安全责任并开展应急处置",
                ],
            },
            {
                "heading": "可信流通处于规划推进阶段",
                "items": ["规划推进可信数据空间建设、场景验证和生态培育"],
            },
        ],
    )

    issues, _ = audit_final_script(final, plan, foundation)
    source_issues = [issue for issue in issues if "AUTHOR_" in issue and "AUTHOR_MECHANICAL" not in issue]
    assert source_issues == []
