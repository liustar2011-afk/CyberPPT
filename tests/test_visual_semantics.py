from __future__ import annotations

from cyberppt.script_quality.audit import audit_script_quality
from cyberppt.script_quality.models import ScriptDocument, ScriptPage
from cyberppt.script_quality.visual_semantics import (
    _author_visual_semantic_strength_issues,
)


def _page(*, visual_structure: str, visual_proof: str = "") -> ScriptPage:
    return ScriptPage(
        page_id="p09",
        sequence=9,
        heading="院校市场",
        page_type="content",
        title="院校市场",
        main_message="按院校类型匹配教学产品",
        full_prose="院校类型对应教学需求与建议产品。" * 12,
        selection_notes="保留业务匹配关系。",
        evidence_map="院校类型→ST0092",
        evidence_map_refs=("ST0092",),
        source_refs=("ST0092",),
        boundary_source_refs=(),
        boundary="",
        visual_structure=visual_structure,
        visual_proof=visual_proof,
        onscreen_text="院校类型\n  建议产品：课程包",
        module_titles=("院校类型",),
    )


def _contract(**updates: object) -> dict[str, object]:
    contract: dict[str, object] = {
        "page_id": "p09",
        "sequence": 9,
        "page_type": "content",
        "core_message": "按院校类型匹配教学产品",
        "page_mission": "说明院校类型与建议产品的匹配关系",
        "source_refs": ["ST0092"],
        "page_consumption_contract_mode": "legacy",
    }
    contract.update(updates)
    return contract


def _records(statement: str) -> dict[str, dict[str, object]]:
    return {"ST0092": {"id": "ST0092", "statement": statement}}


def test_p09_visual_structure_rejects_unsupported_decision_modality() -> None:
    page = _page(visual_structure="主关系是院校类型决定首期教学产品匹配。")

    issues = _author_visual_semantic_strength_issues(
        page,
        _contract(),
        _records("电力类高职高专、职业本科：课程包与实训场景"),
    )

    assert [issue.code for issue in issues] == [
        "AUTHOR_VISUAL_MODALITY_STRENGTH_UPGRADED"
    ]
    assert issues[0].evidence[0] == "field=visual_structure"


def test_visual_proof_is_also_checked() -> None:
    page = _page(
        visual_structure="院校类型连接建议产品。",
        visual_proof="三类院校必然形成首期市场。",
    )

    issues = _author_visual_semantic_strength_issues(
        page,
        _contract(),
        _records("三类院校对应不同建议产品。"),
    )

    assert [issue.code for issue in issues] == [
        "AUTHOR_VISUAL_MODALITY_STRENGTH_UPGRADED"
    ]
    assert issues[0].evidence[0] == "field=visual_proof"


def test_visual_relation_strength_is_checked() -> None:
    page = _page(
        visual_structure="院校类型驱动首期教学产品匹配。",
    )

    issues = _author_visual_semantic_strength_issues(
        page,
        _contract(),
        _records("三类院校对应不同建议产品。"),
    )

    assert [issue.code for issue in issues] == [
        "AUTHOR_VISUAL_RELATION_STRENGTH_UPGRADED"
    ]


def test_approved_page_relation_supports_visual_relation() -> None:
    page = _page(
        visual_structure="院校类型导致教学产品差异。",
    )
    contract = _contract(
        content_relations=[
            {"relation": "causes", "source_refs": ["ST0092"]},
        ],
    )

    issues = _author_visual_semantic_strength_issues(
        page,
        contract,
        _records("三类院校对应不同建议产品。"),
    )

    assert issues == []


def test_p12_condition_gate_supports_deciding_whether_to_scale() -> None:
    page = _page(
        visual_structure="依据交付与单位经济结果决定是否放大。",
    )
    contract = _contract(
        page_id="p12",
        core_message="依次验证付费交付和第二客户复制",
        page_mission="明确验证产出和放大条件",
        argument_chain=[
            {"statement": "验证通过后再进入成熟放大。"},
        ],
    )

    issues = _author_visual_semantic_strength_issues(
        page,
        contract,
        _records("成熟放大：验证通过后"),
    )

    assert issues == []


def test_layout_only_strength_wording_is_ignored() -> None:
    page = _page(
        visual_structure="内容数量决定卡片行列位置；入口连接中心。",
    )

    issues = _author_visual_semantic_strength_issues(
        page,
        _contract(),
        _records("院校类型对应建议产品。"),
    )

    assert issues == []


def test_layout_phrase_does_not_hide_business_strength_in_same_unit() -> None:
    page = _page(
        visual_structure="内容数量决定卡片行列位置，同时院校类型决定首期产品匹配。",
    )

    issues = _author_visual_semantic_strength_issues(
        page,
        _contract(),
        _records("院校类型对应建议产品。"),
    )

    assert [issue.code for issue in issues] == [
        "AUTHOR_VISUAL_MODALITY_STRENGTH_UPGRADED"
    ]


def test_main_script_audit_calls_visual_semantic_gate() -> None:
    page = _page(visual_structure="院校类型决定首期教学产品匹配。")
    outline = {"pages": [_contract()]}
    truth = {"records": list(_records("院校类型对应建议产品。").values())}

    codes = {
        issue.code
        for issue in audit_script_quality(
            ScriptDocument((page,)),
            outline,
            truth,
        )
    }

    assert "AUTHOR_VISUAL_MODALITY_STRENGTH_UPGRADED" in codes
