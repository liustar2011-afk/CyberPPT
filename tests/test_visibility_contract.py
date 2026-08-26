from __future__ import annotations

from cyberppt.script_quality.models import ScriptPage
from cyberppt.script_quality.visibility_contract import (
    _mapping_labels_equal,
    _onscreen_visibility_contract_issues,
)


def _page(*, module: str, mapping: str) -> ScriptPage:
    return ScriptPage(
        page_id="p09",
        sequence=9,
        heading="院校市场",
        page_type="content",
        title="院校市场",
        main_message="按院校类型匹配教学产品",
        full_prose="院校类型对应教学产品。",
        selection_notes="保留院校类型。",
        evidence_map=mapping,
        evidence_map_refs=("ST0092",),
        source_refs=("ST0092",),
        boundary_source_refs=(),
        boundary="",
        visual_structure="院校类型连接建议产品。",
        onscreen_text=module,
        module_titles=(module,),
    )


def _contract(*, visibility: str = "prose_only") -> dict[str, object]:
    return {
        "page_consumption_contract_mode": "required",
        "content_units": [
            {"source_refs": ["ST0092"], "visibility": visibility}
        ],
    }


def test_p09_parallel_connector_variants_match_in_order() -> None:
    page = _page(
        module="电力类高职高专、职业本科",
        mapping="电力类高职高专及职业本科→ST0092",
    )

    issues = _onscreen_visibility_contract_issues(page, _contract())

    assert [issue.code for issue in issues] == [
        "ONSCREEN_VISIBILITY_CONTRACT_BREACH"
    ]


def test_parallel_connector_normalization_preserves_order() -> None:
    assert _mapping_labels_equal("需求及供给", "需求与供给")
    assert _mapping_labels_equal("需求和供给", "需求、供给")
    assert not _mapping_labels_equal("需求与供给", "供给与需求")


def test_bare_business_labels_match_explicit_display_decorations() -> None:
    assert _mapping_labels_equal("首期试点", "②首期试点")
    assert _mapping_labels_equal("首期试点", "首期试点｜第2—4个月")
    assert _mapping_labels_equal("首期试点", "②首期试点｜第2—4个月")
    assert _mapping_labels_equal("③复制验证｜第4—6个月", "复制验证")
    assert _mapping_labels_equal("成熟放大", "④成熟放大｜验证通过后")
    assert _mapping_labels_equal("需求及供给", "②需求与供给｜第2—4个月")


def test_two_decorated_labels_do_not_collapse_to_the_same_business_core() -> None:
    assert not _mapping_labels_equal(
        "②首期试点｜第2—4个月",
        "③首期试点｜第4—6个月",
    )
    assert not _mapping_labels_equal(
        "②首期试点｜第2—4个月",
        "②首期试点｜第4—6个月",
    )


def test_decorated_label_matching_requires_the_complete_business_label() -> None:
    decorated = "②首期试点｜第2—4个月"

    assert not _mapping_labels_equal("试点", decorated)
    assert not _mapping_labels_equal("首期试点结论", decorated)
    assert not _mapping_labels_equal("首期试点", "首期试点｜")


def test_unrelated_similar_labels_do_not_match() -> None:
    assert not _mapping_labels_equal(
        "电力类高职高专及职业本科",
        "电力类高职高专与普通本科",
    )
    assert not _mapping_labels_equal("中华人民共和国", "中华人民共、国")


def test_exact_label_and_onscreen_visibility_still_pass() -> None:
    page = _page(module="应用型本科", mapping="应用型本科→ST0092")

    assert _onscreen_visibility_contract_issues(
        page,
        _contract(visibility="supporting_onscreen"),
    ) == []


def test_exact_label_offscreen_promotion_still_fails() -> None:
    page = _page(module="应用型本科", mapping="应用型本科→ST0092")

    issues = _onscreen_visibility_contract_issues(page, _contract())

    assert [issue.code for issue in issues] == [
        "ONSCREEN_VISIBILITY_CONTRACT_BREACH"
    ]


def test_p12_decorated_titles_detect_all_offscreen_promotions() -> None:
    page = ScriptPage(
        page_id="p12",
        sequence=12,
        heading="分阶段建设路径",
        page_type="content",
        title="分阶段建设路径",
        main_message="按验证结果逐步扩大建设范围。",
        full_prose="首期试点后开展复制验证，验证通过后成熟放大。",
        selection_notes="保留三个阶段。",
        evidence_map=(
            "首期试点→ST0121；复制验证→ST0122；成熟放大→ST0123"
        ),
        evidence_map_refs=("ST0121", "ST0122", "ST0123"),
        source_refs=("ST0121", "ST0122", "ST0123"),
        boundary_source_refs=(),
        boundary="",
        visual_structure="三个阶段按时间推进。",
        onscreen_text=(
            "②首期试点｜第2—4个月\n"
            "③复制验证｜第4—6个月\n"
            "④成熟放大｜验证通过后"
        ),
        module_titles=(
            "②首期试点｜第2—4个月",
            "③复制验证｜第4—6个月",
            "④成熟放大｜验证通过后",
        ),
    )
    contract = {
        "page_consumption_contract_mode": "required",
        "content_units": [
            {"source_refs": ["ST0121"], "visibility": "prose_only"},
            {"source_refs": ["ST0122"], "visibility": "notes_only"},
            {"source_refs": ["ST0123"], "visibility": "trace_only"},
        ],
    }

    issues = _onscreen_visibility_contract_issues(page, contract)

    assert [issue.source_ids for issue in issues] == [
        ("ST0121",),
        ("ST0122",),
        ("ST0123",),
    ]
