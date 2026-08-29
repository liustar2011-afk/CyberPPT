from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from cyberppt.onscreen_expression import resolve_onscreen_expression
from cyberppt.script_quality_contract import parse_script_path
from cyberppt.stage02_handoff import _page_record, build_stage02_handoff
from cyberppt.stage02_relationship_adapter import derive_business_relationships
from cyberppt.script_quality.parsing import parse_semantic_annotations


def _write_script(path: Path, pages: str) -> None:
    path.write_text(pages.strip() + "\n", encoding="utf-8")


def _page(*modules: str):
    return SimpleNamespace(
        onscreen_expression_form="",
        top_level_module_titles=modules,
        onscreen_judgment="",
    )


def test_derives_explicit_visual_structure_arrows_as_business_semantics() -> None:
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
    assert relationships[0]["relation"] == "evidence_supports"
    assert relationships[0]["basis"] == "derived_from_script_visual_structure"


def test_problem_response_is_not_collapsed_into_comparison() -> None:
    relationships = derive_business_relationships(
        visual_structure="资源分散 → 行业节点：问题回应（inferred，源文未逐一显式配对）",
        title="平台总体定位",
    )

    assert len(relationships) == 1
    assert relationships[0]["relation"] == "problem_response"
    assert relationships[0]["relation_label"] == "问题回应"


def test_derives_declared_parallel_classification_when_no_arrow_exists() -> None:
    relationships = derive_business_relationships(
        visual_structure="五类基础服务能力为并列分类，覆盖不同技术层次。",
        title="总体服务体系",
        module_titles=("数据获取服务", "知识内容服务", "模型与智能服务"),
        top_level_module_titles=("数据获取服务", "知识内容服务", "模型与智能服务"),
    )

    assert relationships[0]["relation"] == "peer_classification"
    assert relationships[0]["objects"] == ["数据获取服务", "知识内容服务", "模型与智能服务"]


def test_ambiguous_page_without_script_relation_stays_empty() -> None:
    assert derive_business_relationships(
        visual_structure="本页展示平台能力。",
        title="平台能力",
        module_titles=("能力一", "能力二"),
    ) == ()


def test_parses_optional_three_level_stage02_annotations() -> None:
    annotations = parse_semantic_annotations(
        """
- 一级：标准体系
  - 二级：A 基础通用
    - 三级：A1 术语与概念
""",
        "- 推荐结构：三级层级树。\n- 不表达先后关系。",
    )
    assert annotations["topology"] == "hierarchy"
    assert annotations["nodes"] == [
        {"id": "标准体系", "label": "标准体系", "level": 1, "parent": ""},
        {"id": "A 基础通用", "label": "A 基础通用", "level": 2, "parent": "标准体系"},
        {"id": "A1 术语与概念", "label": "A1 术语与概念", "level": 3, "parent": "A 基础通用"},
    ]


def test_stage02_rejects_noun_headings_when_clause_mode_is_declared() -> None:
    from cyberppt.stage02_input import build_stage02_input

    with TemporaryDirectory() as directory:
        root = Path(directory)
        script = root / "final-script.md"
        _write_script(
            script,
            """
## P11 体系
- 页面类型：内容页
- 页面使命：展示体系
- 核心结论：形成标准体系
### 上屏文字
- 建设框架：四大方向、八项能力
### 文字表达规则
- 小标题必须使用完整判断句。
""",
        )
        try:
            build_stage02_input(root / "project", script=script)
        except ValueError as exc:
            assert "semantic heading contract failed" in str(exc)
        else:
            raise AssertionError("noun heading should fail clause mode")


def test_p04_many_to_one_support_uses_convergent_reading_not_framework() -> None:
    relationships = [
        {"subject": "业务需求增长", "relation": "evidence_supports", "objects": ["统一基础设施必要性"], "relation_label": "并列支撑"},
        {"subject": "资源分散", "relation": "evidence_supports", "objects": ["统一基础设施必要性"], "relation_label": "并列支撑"},
        {"subject": "机制待完善", "relation": "evidence_supports", "objects": ["统一基础设施必要性"], "relation_label": "并列支撑"},
    ]
    decision = resolve_onscreen_expression(
        _page("业务需求增长", "资源分散", "机制待完善"),
        business_relationships=relationships,
    )
    assert decision.form == "support_convergence_3_6"
    assert decision.source == "relation"
    assert "semantic:many_to_one_support" in decision.evidence


def test_p05_problem_response_mapping_is_not_two_column_comparison() -> None:
    relationships = [
        {"subject": "资源分散", "relation": "problem_response", "objects": ["行业节点"], "relation_label": "问题回应"},
        {"subject": "可信使用条件不足", "relation": "problem_response", "objects": ["运营平台"], "relation_label": "问题回应"},
        {"subject": "协同机制待完善", "relation": "problem_response", "objects": ["协同载体"], "relation_label": "问题回应"},
    ]
    decision = resolve_onscreen_expression(
        _page("行业节点", "运营平台", "协同载体"),
        business_relationships=relationships,
    )
    assert decision.form == "mapping_2_6"
    assert decision.form != "comparison_2col"


def test_p16_five_peer_categories_have_a_valid_parallel_contract() -> None:
    relationships = [{
        "subject": "总体服务体系",
        "relation": "peer_classification",
        "objects": ["数据获取", "知识内容", "模型智能", "分析监测", "数据治理"],
        "relation_label": "并列分类",
    }]
    decision = resolve_onscreen_expression(
        _page("数据获取", "知识内容", "模型智能", "分析监测", "数据治理"),
        business_relationships=relationships,
    )
    assert decision.form == "parallel_classification_3_6"


def test_p31_six_step_sequence_stays_a_directed_reading_contract() -> None:
    relationships = [
        {"subject": f"步骤{i}", "relation": "sequence_before", "objects": [f"步骤{i+1}"], "relation_label": "顺序衔接"}
        for i in range(1, 6)
    ]
    decision = resolve_onscreen_expression(
        _page("意向登记", "资源对接", "成熟度评估", "方案深化", "试点验证", "正式运营"),
        business_relationships=relationships,
    )
    assert decision.form == "flow_3_5"


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

- SU-EXAMPLE-PARAGRAPH-01
""",
        )

        document = parse_script_path(script)
        assert len(document.pages) == 1
        assert len(document.pages[0].content_relations) == 3

        payload = build_stage02_handoff(root / "project", script=script)
        page = payload["pages"][0]
        relationships = page["stage02_visual_input"]["business_relationships"]

    assert len(relationships) == 3
    assert all(item["relation"] == "evidence_supports" for item in relationships)
    assert all(item["basis"] == "derived_from_script_visual_structure" for item in relationships)
    assert page["onscreen_expression"]["form"] == "support_convergence_3_6"
    assert page["page_mission"] == "说明电力行业当前面临的三方面资源协同压力。"
    assert page["page_mission"] != page["core_message"]
    assert page["argument_chain"].startswith("问题诊断｜")
    assert page["provenance_refs"] == ["SU-EXAMPLE-PARAGRAPH-01"]
    assert page["prompt_mode"] == "semantic_brief"


def test_project_final_script_consumes_matching_deck_plan_boundaries() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory) / "project"
        script = project / "script" / "dist" / "final-script.md"
        script.parent.mkdir(parents=True)
        _write_script(
            script,
            """
## P01 项目页

- 页面类型：内容页
- 页面标题：项目页
- 页面使命：说明项目任务边界。
- 核心结论：项目任务具有明确边界。
- 主论证链：任务回应｜项目依据 → 任务边界

### 完整文字稿

项目依据明确了任务边界和适用条件。

### 上屏文字

- 项目依据：明确任务来源
- 任务边界：限定实施范围

### 视觉结构

项目依据 → 任务边界：限定

### 内容来源

- SU-PROJECT-PARAGRAPH-01
""",
        )
        (project / "script" / "deck-plan.json").write_text(
            json.dumps(
                {
                    "pages": [
                        {
                            "id": "P01",
                            "title": "项目页",
                            "message": "项目任务具有明确边界。",
                            "logic": "说明项目任务边界。",
                            "page_role": "scope",
                            "argument_chain": "项目依据 → 任务边界",
                            "source_refs": ["ST0030"],
                            "must_not_include": ["不得扩展到未批准任务"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        page = build_stage02_handoff(project, script=script)["pages"][0]

    assert page["argument_role"] == "scope"
    assert page["source_refs"] == ["ST0030"]
    assert page["provenance_refs"] == ["SU-PROJECT-PARAGRAPH-01"]
    assert page["must_not_include"] == ["不得扩展到未批准任务"]


def test_stage02_ignores_lean_deck_plan_wording_and_uses_locked_script() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory) / "project"
        script = project / "script" / "dist" / "final-script.md"
        script.parent.mkdir(parents=True)
        _write_script(
            script,
            """
## P01 最终脚本标题

- 页面类型：内容页
- 页面标题：最终脚本标题
- 页面使命：以最终脚本确定页面任务。
- 核心结论：AUTHOR完成后形成最终判断。
- 主论证链：任务回应｜来源依据 → 最终判断

### 完整文字稿

最终脚本是Stage 02的内容输入。

### 上屏文字

- 来源依据：保留事实边界
- 最终判断：由AUTHOR形成

### 视觉结构

来源依据 → 最终判断：支撑

### 内容来源

- SU-FINAL-PARAGRAPH-01
""",
        )
        (project / "script" / "deck-plan.json").write_text(
            json.dumps(
                {
                    "plan_contract_version": 2,
                    "planning_profile": "lean",
                    "pages": [{"id": "P01", "title": "暂定标题", "logic": "暂定使命", "source_refs": ["ST0001"]}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        page = build_stage02_handoff(project, script=script)["pages"][0]

    assert page["title"] == "最终脚本标题"
    assert page["page_mission"] == "以最终脚本确定页面任务。"
    assert page["source_refs"] == []
    assert page["provenance_refs"] == ["SU-FINAL-PARAGRAPH-01"]


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


def test_source_explicit_directed_relation_upgrades_prompt_mode() -> None:
    with TemporaryDirectory() as directory:
        script = Path(directory) / "directed-script.md"
        _write_script(
            script,
            """
## P01 明确流程页

- 页面类型：内容页
- 页面标题：明确流程页
- 页面使命：说明甲到乙的明确先后关系。
- 核心结论：甲完成后进入乙。
- 完整文字稿：来源明确规定甲完成后进入乙。
- 上屏文字：
  - 甲
  - 乙
- 视觉结构：甲 → 乙：先后
<!-- cyberppt-page-contract {"content_relations":[{"subject":"甲","relation":"sequence_before","objects":["乙"],"direction":"subject_to_objects","basis":"explicit","confidence":"high","source_refs":["ST001"]}]} -->
""",
        )
        page = parse_script_path(script).pages[0]

    record = _page_record(page, None)
    assert record["prompt_mode"] == "directed_composition"
    assert record["stage02_visual_input"]["semantic_topology"]["constraint_authority"] == "hard"
