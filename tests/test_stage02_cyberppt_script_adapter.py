from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.script_quality_contract import parse_script_path
from cyberppt.stage02_handoff import build_stage02_handoff
from cyberppt.stage02_relationship_adapter import derive_business_relationships


def _write_script(path: Path, pages: str) -> None:
    path.write_text(pages.strip() + "\n", encoding="utf-8")


def test_derives_explicit_visual_structure_arrows() -> None:
    relationships = derive_business_relationships(
        visual_structure="""
三项压力构成并列分类，共同支撑统一数据基础设施的必要性。
业务需求持续增长 → 统一数据基础设施的必要性：并列支撑
行业资源较为分散 → 统一数据基础设施的必要性：并列支撑
规模化服务机制仍需完善 → 统一数据基础设施的必要性：并列支撑
""",
        title="行业为何需要统一的数据基础设施",
        module_titles=("业务需求持续增长", "行业资源较为分散", "规模化服务机制仍需完善"),
    )

    assert len(relationships) == 3
    assert relationships[0]["subject"] == "业务需求持续增长"
    assert relationships[0]["objects"] == ["统一数据基础设施的必要性"]
    assert relationships[0]["relation"] == "supports"
    assert relationships[0]["basis"] == "derived_from_script_visual_structure"


def test_strips_legacy_evidence_grade_and_preserves_problem_response_semantics() -> None:
    relationships = derive_business_relationships(
        visual_structure="资源分散 → 行业节点：问题回应（inferred，源文未逐一显式配对）",
        title="平台总体定位",
    )

    assert len(relationships) == 1
    assert relationships[0]["relation"] == "responds_to"
    assert relationships[0]["relation_label"] == "问题回应"


def test_derives_declared_parallel_classification_when_no_arrow_exists() -> None:
    relationships = derive_business_relationships(
        visual_structure="五类基础服务能力为并列分类，覆盖不同技术层次。",
        title="总体服务体系",
        module_titles=("数据获取服务", "知识内容服务", "模型与智能服务"),
        top_level_module_titles=("数据获取服务", "知识内容服务", "模型与智能服务"),
    )

    assert relationships[0]["relation"] == "classified_as"
    assert relationships[0]["objects"] == ["数据获取服务", "知识内容服务", "模型与智能服务"]
    assert relationships[0]["direction"] == "one_to_many"


def test_ambiguous_page_without_script_relation_stays_empty() -> None:
    assert derive_business_relationships(
        visual_structure="本页展示平台能力。",
        title="平台能力",
        module_titles=("能力一", "能力二"),
    ) == ()


def test_cyberppt_script_canonical_markdown_populates_stage02_business_relationships() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        script = root / "final-script.md"
        _write_script(
            script,
            """
## P04 行业为何需要统一的数据基础设施

- 页面类型：内容页
- 页面标题：行业为何需要统一的数据基础设施
- 页面使命：说明电力行业当前面临的三方面资源协同压力。
- 核心结论：三方面压力共同指向统一数据基础设施的需要。
- 主论证链：问题诊断｜业务需求增长 → 资源分散 → 服务机制待完善 → 统一基础设施的必要性

### 完整文字稿

电力行业当前同时面临业务需求增长、资源分散和规模化服务机制仍需完善三方面压力。

### 上屏文字

- 业务需求持续增长：多重驱动提高协同要求
- 行业资源较为分散：资源分布在不同主体和系统
- 规模化服务机制仍需完善：供需双方需要稳定服务机制

### 视觉结构

三项压力构成并列分类，共同支撑统一数据基础设施的必要性。
业务需求持续增长 → 统一数据基础设施的必要性：并列支撑
行业资源较为分散 → 统一数据基础设施的必要性：并列支撑
规模化服务机制仍需完善 → 统一数据基础设施的必要性：并列支撑

### 演讲者备注

三方面压力共同形成建设统一数据基础设施的现实需要。

### 内容来源

- S1.1
""",
        )

        document = parse_script_path(script)
        assert len(document.pages) == 1
        assert len(document.pages[0].content_relations) == 3

        payload = build_stage02_handoff(root / "project", script=script)
        page = payload["pages"][0]
        relationships = page["stage02_visual_input"]["business_relationships"]

    assert len(relationships) == 3
    assert all(item["basis"] == "derived_from_script_visual_structure" for item in relationships)
    assert page["onscreen_expression"]["form"] == "pyramid_argument"
    assert page["expression_constraints"]["reading_requirement"] == "convergent"
    assert page["stage02_visual_input"]["author_visual_notes"]


def test_legacy_page_contract_relations_keep_priority_over_derived_visual_structure() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        script = root / "legacy-script.md"
        _write_script(
            script,
            """
## P01 旧合同页

- 页面类型：内容页
- 页面标题：旧合同页
- 核心结论：旧合同关系继续优先。
- 完整文字稿：旧合同关系继续优先。
- 上屏文字：
  - 甲
  - 乙
- 视觉结构：甲 → 乙：视觉结构推导关系
<!-- cyberppt-page-contract {"content_relations":[{"subject":"甲","relation":"supports","objects":["乙"],"basis":"explicit","confidence":"high"}]} -->
""",
        )
        page = parse_script_path(script).pages[0]

    assert len(page.content_relations) == 1
    assert page.content_relations[0]["basis"] == "explicit"
    assert page.content_relations[0]["relation"] == "supports"
