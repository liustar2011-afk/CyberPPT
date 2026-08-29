from cyberppt.script_quality.models import ScriptPage
from cyberppt.script_quality.presentation import _presentation_issues


def _page(onscreen: str) -> ScriptPage:
    return ScriptPage(
        page_id="p02",
        sequence=2,
        heading="先行先试项目",
        page_type="content",
        title="先行先试项目为标准验证提供实践依托",
        main_message="重点场景用于检验标准适用性",
        full_prose="先行先试项目以重点场景验证标准适用性和可操作性",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=("ST001", "ST002"),
        boundary_source_refs=(),
        boundary="",
        visual_structure="并列场景",
        onscreen_text=onscreen,
        raw_onscreen_text=onscreen,
        module_titles=("重点验证场景",),
    )


def _contract(*, list_only_allowed: bool = False, rich: bool = True) -> dict:
    statements = (
        [
            "绿色低碳场景用于检验标准在电碳业务中的适用性和可操作性",
            "科技创新场景用于检验标准对科研数据流通和成果应用的支撑能力",
        ]
        if rich
        else ["重点场景包括行业治理、市场运行、绿色低碳、科技创新"]
    )
    return {
        "content_load": "standard",
        "label_only_onscreen_allowed": list_only_allowed,
        "content_units": [
            {
                "unit_id": f"U{index}",
                "statement": statement,
                "source_refs": [f"ST{index:03d}"],
                "onscreen_required": True,
            }
            for index, statement in enumerate(statements, start=1)
        ],
    }


def test_page_lint_blocks_source_detail_collapsed_to_label() -> None:
    page = _page("重点验证场景\n  绿色低碳\n  科技创新")

    codes = {issue.code for issue in _presentation_issues(page, _contract())}

    assert "ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" in codes


def test_page_lint_blocks_label_enumeration_that_hides_item_detail() -> None:
    page = _page("重点验证场景\n  绿色低碳、科技创新")

    codes = {issue.code for issue in _presentation_issues(page, _contract())}

    assert "ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" in codes


def test_page_lint_accepts_label_with_explanation_and_no_terminal_punctuation() -> None:
    page = _page(
        "重点验证场景\n"
        "  绿色低碳：检验标准在电碳业务中的适用性\n"
        "  科技创新：检验标准对科研数据流通的支撑能力"
    )

    codes = {issue.code for issue in _presentation_issues(page, _contract())}

    assert "ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" not in codes


def test_page_lint_allows_explicit_label_only_taxonomy_for_thin_source() -> None:
    page = _page("重点验证场景\n  行业治理\n  市场运行\n  绿色低碳\n  科技创新")

    codes = {
        issue.code
        for issue in _presentation_issues(
            page,
            _contract(list_only_allowed=True, rich=False),
        )
    }

    assert "ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL" not in codes


def test_page_lint_rejects_source_colocation_as_institution_hierarchy() -> None:
    page = _page(
        "能源制度\n"
        "  绿色低碳：提出数据采集流通应用要求\n"
        "  分类分级：实行一般重要核心三级管理"
    )
    contract = {
        "content_units": [
            {
                "unit_id": "ST0053",
                "statement": "行动计划将绿色低碳列为重点行动领域，"
                "对数据采集、流通、应用提出要求",
                "source_refs": ["SU-001"],
            },
            {
                "unit_id": "ST0054",
                "statement": "能源行业数据分类分级指南实行一般重要核心三级管理",
                "source_refs": ["SU-001"],
            },
        ],
        "onscreen_contract": {
            "modules": [
                {
                    "heading": "能源制度",
                    "evidence_refs": ["ST0053", "ST0054"],
                }
            ]
        },
    }

    codes = {issue.code for issue in _presentation_issues(page, contract)}

    assert "ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY" in codes
