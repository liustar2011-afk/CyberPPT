from __future__ import annotations

from copy import deepcopy

from script_engine.analysis_audit import audit_deck_plan, audit_final_script
from script_engine.contracts import validate_deck_plan


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


def _page() -> dict:
    return {
        "id": "P01",
        "question": "标准如何落地",
        "message": "标准覆盖共同语言与资源治理",
        "logic": "并列",
        "content": ["术语", "质量"],
        "source_refs": ["ST1", "ST2", "ST3"],
        "source_consumption": {
            "mode": "strict",
            "detail_refs": ["ST3"],
            "full_prose_anchors": [
                {"source_ref": "ST2", "anchors": ["数据质量", "全过程质量控制"], "minimum_hits": 2}
            ],
            "onscreen_refs": ["ST1"],
        },
        "onscreen_contract": {
            "relation": "parallel",
            "detail_axis": "standard_scope",
            "modules": [
                {"heading": "基础通用", "evidence_refs": ["ST1"], "required_signals": ["术语定义"]},
                {"heading": "数据资源", "evidence_refs": ["ST2"], "required_signals": ["全过程质量控制"]},
            ],
        },
    }


def _plan(page: dict | None = None) -> dict:
    return {"communication_goal": "说明标准范围", "chapters": [], "pages": [page or _page()]}


def _final(full_copy: str | None = None) -> dict:
    return {
        "slides": [{
            "id": "P01", "page_type": "content", "title": "标准范围",
            "core_message": "标准覆盖共同语言与资源治理",
            "full_copy": full_copy or "统一电力数据基础设施术语定义并衔接国家参考架构。制定电力数据质量评价指标体系，覆盖全过程质量控制。",
            "onscreen": [
                {"heading": "基础通用", "items": ["统一术语定义"]},
                {"heading": "数据资源", "items": ["覆盖全过程质量控制"]},
            ],
        }]
    }


def test_legacy_page_without_source_consumption_remains_compatible() -> None:
    page = _page()
    page.pop("source_consumption")
    issues, _ = audit_final_script(_final("完全无关的完整稿"), _plan(page), _foundation())
    assert not any("source_consumption" in issue for issue in issues)


def test_schema_and_plan_audit_reject_invalid_mode_and_outside_ref() -> None:
    page = _page()
    page["source_consumption"]["mode"] = "required"
    page["source_consumption"]["detail_refs"] = ["ST9"]
    assert validate_deck_plan(_plan(page))
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    joined = "\n".join(issues)
    assert "must be 'strict'" in joined
    assert "outside refs ['ST9']" in joined


def test_detail_ref_is_exempt_from_full_copy() -> None:
    issues, _ = audit_final_script(_final(), _plan(), _foundation())
    assert not any("ST3" in issue and "full_copy gap" in issue for issue in issues)


def test_specific_intentional_omission_passes_but_short_reason_fails() -> None:
    page = _page()
    page["source_consumption"]["detail_refs"] = []
    page["source_consumption"]["intentional_omissions"] = [
        {"source_refs": ["ST3"], "reason": "该项保留到后续资产管理专题页面展开"}
    ]
    assert validate_deck_plan(_plan(page)) == []
    issues, _ = audit_final_script(_final(), _plan(page), _foundation())
    assert not any("ST3" in issue and "full_copy gap" in issue for issue in issues)

    bad = deepcopy(page)
    bad["source_consumption"]["intentional_omissions"][0]["reason"] = "后续再说"
    assert validate_deck_plan(_plan(bad))
    issues, _ = audit_deck_plan(_plan(bad), _foundation())
    assert any("at least 8 characters" in issue for issue in issues)


def test_missing_and_sufficient_full_prose_anchors() -> None:
    issues, _ = audit_final_script(
        _final("统一电力数据基础设施术语定义并衔接国家参考架构。仅说明数据质量。"),
        _plan(), _foundation(),
    )
    assert any("ST2" in issue and "全过程质量控制" in issue for issue in issues)

    issues, _ = audit_final_script(_final(), _plan(), _foundation())
    assert not any("ST2" in issue and "full_copy gap" in issue for issue in issues)


def test_unanchored_required_source_uses_statement_overlap() -> None:
    page = _page()
    page["source_consumption"]["full_prose_anchors"] = []
    issues, _ = audit_final_script(_final("全过程质量控制与术语都没讲清楚"), _plan(page), _foundation())
    assert any("ST1" in issue and "overlap=" in issue for issue in issues)


def test_onscreen_ref_requires_contract_and_module_mapping() -> None:
    page = _page()
    page.pop("onscreen_contract")
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("requires an onscreen_contract" in issue for issue in issues)

    page = _page()
    page["onscreen_contract"]["modules"][0]["evidence_refs"] = ["ST2"]
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("unmapped refs ['ST1']" in issue for issue in issues)


def test_mapped_onscreen_ref_requires_visible_signal() -> None:
    issues, _ = audit_final_script(_final(), _plan(), _foundation())
    assert not any("required signal" in issue for issue in issues)

    bad = _final()
    bad["slides"][0]["onscreen"][0]["items"] = ["统一架构"]
    issues, _ = audit_final_script(bad, _plan(), _foundation())
    assert any("required signal '术语定义'" in issue for issue in issues)


def test_onscreen_ref_cannot_be_detail_or_omitted() -> None:
    page = _page()
    page["source_consumption"]["detail_refs"] = ["ST1"]
    issues, _ = audit_deck_plan(_plan(page), _foundation())
    assert any("detail and onscreen" in issue for issue in issues)
