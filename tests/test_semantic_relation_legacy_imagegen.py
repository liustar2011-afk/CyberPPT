from __future__ import annotations

from cyberppt.script_quality.models import ScriptPage
from scripts.imagegen_pipeline.handoff.semantics import resolve_page_visual_intent


def _page(*, title: str, visual_structure: str, modules: tuple[str, ...]) -> ScriptPage:
    return ScriptPage(
        page_id="P01",
        sequence=1,
        heading=title,
        page_type="content",
        title=title,
        main_message=title,
        full_prose="",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=(),
        boundary_source_refs=(),
        boundary="",
        visual_structure=visual_structure,
        onscreen_text="\n".join(modules),
        module_titles=modules,
        top_level_module_titles=modules,
    )


def test_taxonomy_does_not_reenter_legacy_hierarchy_intent() -> None:
    page = _page(
        title="总体服务体系",
        visual_structure="五类基础服务能力为并列分类，覆盖不同技术层次。",
        modules=("数据获取", "知识内容", "模型智能", "分析监测", "数据治理核验"),
    )
    intent, source = resolve_page_visual_intent(page, "说明五类并列服务能力")
    assert intent == "judgment_evidence"
    assert source == "contract_relation_profile"
    assert intent != "hierarchy_support"


def test_problem_response_does_not_reenter_legacy_comparison_intent() -> None:
    page = _page(
        title="平台总体定位",
        visual_structure=(
            "资源分散 → 行业节点：问题回应\n"
            "可信使用条件不足 → 运营平台：问题回应\n"
            "协同机制待完善 → 协同载体：问题回应"
        ),
        modules=("行业节点", "运营平台", "协同载体"),
    )
    intent, source = resolve_page_visual_intent(page, "说明三方面问题与平台定位的对应关系")
    assert intent == "capability_relationship"
    assert source == "contract_relation_profile"
    assert intent != "comparison"
