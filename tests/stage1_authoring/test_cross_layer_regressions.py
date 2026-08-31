from __future__ import annotations

from pathlib import Path

import pytest

from cyberppt.relation_semantics import resolve_relation_expression
from cyberppt.stage02_relationship_adapter import derive_business_relationships
from cyberppt.topology_resolver import (
    CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY,
    resolve_semantic_topology,
)
from script_engine.contracts import lint_final_script

from .failure_fixtures import build_lint_failure_payload, failure_cases
from .fixtures import AuthoringRelationCase, correct_relationship_cases


_CORRECT_CASES = correct_relationship_cases()
_FAILURE_CASES = failure_cases()
_REPO_ROOT = Path(__file__).resolve().parents[2]
_GOLDEN_PAGE_DIR = (
    _REPO_ROOT
    / ".agents"
    / "skills"
    / "cyberppt-script-workflow"
    / "references"
)
_GOLDEN_PAGE_FILES = {
    "parallel_mece": "golden-page-parallel.md",
    "flow_feedback": "golden-page-flow.md",
    "causal_chain": "golden-page-causal.md",
    "support_convergence": "golden-page-convergence.md",
    "mapping": "golden-page-mapping.md",
    "comparison": "golden-page-comparison.md",
    "roadmap": "golden-page-roadmap.md",
    "governance_boundary": "golden-page-governance.md",
}


def _case_id(case: AuthoringRelationCase) -> str:
    return case.name


def _case(name: str) -> AuthoringRelationCase:
    return next(case for case in _CORRECT_CASES if case.name == name)


def _endpoints(relationships: tuple[dict[str, object], ...]) -> set[str]:
    values: set[str] = set()
    for item in relationships:
        subject = str(item.get("subject") or "").strip()
        if subject:
            values.add(subject)
        objects = item.get("objects")
        if isinstance(objects, (list, tuple)):
            values.update(str(value).strip() for value in objects if str(value).strip())
    return values


def _relation_names(relationships: tuple[dict[str, object], ...]) -> set[str]:
    return {
        str(item.get("relation") or "").strip()
        for item in relationships
        if str(item.get("relation") or "").strip()
    }


def _markdown_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    assert marker in text, f"missing markdown section: {heading}"
    tail = text.split(marker, 1)[1]
    return tail.split("\n## ", 1)[0]


def _derive_case_relationships(case: AuthoringRelationCase) -> tuple[dict[str, object], ...]:
    return derive_business_relationships(
        visual_structure=case.visual_structure,
        title="统一预测体系",
        module_titles=case.module_titles,
        top_level_module_titles=case.module_titles,
    )


def _derived_topology(case: AuthoringRelationCase) -> str:
    relationships = _derive_case_relationships(case)
    result = resolve_semantic_topology(
        relationships,
        module_count=case.module_count,
        page_text=case.page_text,
    )
    return str(result["primary_topology"])


def test_fixture_catalog_has_eight_unique_positive_and_negative_cases() -> None:
    assert len(_CORRECT_CASES) == 8
    assert len({case.name for case in _CORRECT_CASES}) == 8
    assert len(_FAILURE_CASES) == 8
    assert len({case.name for case in _FAILURE_CASES}) == 8
    assert set(_GOLDEN_PAGE_FILES) == {case.name for case in _CORRECT_CASES}


@pytest.mark.parametrize("case", _CORRECT_CASES, ids=_case_id)
def test_golden_page_docs_stay_aligned_with_executable_relation_fixtures(
    case: AuthoringRelationCase,
) -> None:
    path = _GOLDEN_PAGE_DIR / _GOLDEN_PAGE_FILES[case.name]
    assert path.is_file(), path

    text = path.read_text(encoding="utf-8")
    topology_section = _markdown_section(text, "Argument Topology")
    visual_section = _markdown_section(text, "视觉结构")

    assert f"`{case.authoring_topology}`" in topology_section
    assert "关系语义" in visual_section
    assert "方向 / Cardinality" in visual_section
    assert "分组 / 层级" in visual_section
    assert "禁止误读" in visual_section

    if case.name == "parallel_mece":
        assert "并列分类" in visual_section
        assert "无方向" in visual_section
        for title in case.module_titles:
            assert title in visual_section
    else:
        for relation_line in case.visual_structure.splitlines():
            assert relation_line in visual_section, (case.name, relation_line)


@pytest.mark.parametrize("case", _CORRECT_CASES, ids=_case_id)
def test_verified_authoring_relationships_resolve_to_expected_semantic_topology(
    case: AuthoringRelationCase,
) -> None:
    result = resolve_semantic_topology(
        case.verified_relationships,
        module_count=case.module_count,
        page_text=case.page_text,
    )

    assert result["primary_topology"] == case.expected_semantic_topology
    assert case.expected_semantic_topology in CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY
    assert CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY[case.expected_semantic_topology]


@pytest.mark.parametrize("case", _CORRECT_CASES, ids=_case_id)
def test_stage2_adapter_relationships_resolve_to_expected_semantic_topology(
    case: AuthoringRelationCase,
) -> None:
    derived = _derive_case_relationships(case)
    assert derived, f"Stage2 failed to recover authored relationships for {case.name}"

    result = resolve_semantic_topology(
        derived,
        module_count=case.module_count,
        page_text=case.page_text,
    )

    assert result["primary_topology"] == case.expected_semantic_topology, (
        case.name,
        result,
    )


@pytest.mark.parametrize("case", _CORRECT_CASES, ids=_case_id)
def test_verified_authoring_relationships_resolve_to_expected_expression_form(
    case: AuthoringRelationCase,
) -> None:
    decision = resolve_relation_expression(
        relationships=case.verified_relationships,
        module_count=case.module_count,
    )

    assert decision is not None
    assert decision[0] == case.expected_expression_form


@pytest.mark.parametrize("case", _CORRECT_CASES, ids=_case_id)
def test_final_script_visual_structure_preserves_relationships_for_stage2(
    case: AuthoringRelationCase,
) -> None:
    derived = _derive_case_relationships(case)

    assert derived, f"Stage2 failed to recover authored relationships for {case.name}"
    assert set(case.module_titles).issubset(_endpoints(derived))

    decision = resolve_relation_expression(
        relationships=derived,
        module_count=case.module_count,
    )
    assert decision is not None
    assert decision[0] == case.expected_expression_form


def test_parallel_and_convergence_remain_distinct_after_stage2_adapter() -> None:
    parallel = _case("parallel_mece")
    convergence = _case("support_convergence")

    parallel_relations = _derive_case_relationships(parallel)
    convergence_relations = _derive_case_relationships(convergence)

    assert _derived_topology(parallel) == "peer_set"
    assert _derived_topology(convergence) == "support_convergence"
    assert _relation_names(parallel_relations) == {"peer_classification"}
    assert _relation_names(convergence_relations) == {"evidence_supports"}

    convergence_result = resolve_semantic_topology(
        convergence_relations,
        module_count=convergence.module_count,
    )
    assert convergence_result["eligibility"]["peer_set"]["allowed"] is False


def test_flow_causal_and_roadmap_keep_distinct_edge_semantics() -> None:
    flow = _case("flow_feedback")
    causal = _case("causal_chain")
    roadmap = _case("roadmap")

    flow_relations = _derive_case_relationships(flow)
    causal_relations = _derive_case_relationships(causal)
    roadmap_relations = _derive_case_relationships(roadmap)

    assert _derived_topology(flow) == "feedback_loop"
    assert _derived_topology(causal) == "causal_chain"
    assert _derived_topology(roadmap) == "sequence"

    assert "feeds_back_to" in _relation_names(flow_relations)
    assert _relation_names(causal_relations) == {"causes"}
    assert _relation_names(roadmap_relations) == {"sequence_before"}

    assert "交接物" in flow.visual_structure
    assert "进入条件" in roadmap.visual_structure
    assert "因果导致" in causal.visual_structure
    assert "进入条件" not in flow.visual_structure
    assert "交接物" not in roadmap.visual_structure


def test_mapping_and_comparison_keep_direction_and_pairing_distinct() -> None:
    mapping = _case("mapping")
    comparison = _case("comparison")

    mapping_relations = _derive_case_relationships(mapping)
    comparison_relations = _derive_case_relationships(comparison)

    assert _derived_topology(mapping) == "mapping"
    assert _derived_topology(comparison) == "comparison"
    assert _relation_names(mapping_relations) == {"problem_response"}
    assert _relation_names(comparison_relations) == {"comparison"}
    assert all(item["direction"] == "subject_to_objects" for item in mapping_relations)
    assert all(item["direction"] == "unspecified" for item in comparison_relations)
    assert "→" in mapping.visual_structure
    assert " vs " in comparison.visual_structure


def test_governance_convergence_and_parallel_keep_graph_shape_distinct() -> None:
    governance = _case("governance_boundary")
    convergence = _case("support_convergence")
    parallel = _case("parallel_mece")

    governance_relations = _derive_case_relationships(governance)
    convergence_relations = _derive_case_relationships(convergence)
    parallel_relations = _derive_case_relationships(parallel)

    assert _derived_topology(governance) == "dependency_chain"
    assert _derived_topology(convergence) == "support_convergence"
    assert _derived_topology(parallel) == "peer_set"

    governance_subjects = {
        str(item.get("subject") or "") for item in governance_relations
    }
    governance_targets = {
        str(value)
        for item in governance_relations
        for value in item.get("objects", [])
    }
    assert "共同控制机制" in governance_subjects & governance_targets

    convergence_subjects = {
        str(item.get("subject") or "") for item in convergence_relations
    }
    convergence_targets = {
        str(value)
        for item in convergence_relations
        for value in item.get("objects", [])
    }
    assert "综合供需风险判断" in convergence_targets
    assert "综合供需风险判断" not in convergence_subjects

    assert len(parallel_relations) == 1
    assert parallel_relations[0]["relation"] == "peer_classification"
    assert parallel_relations[0]["direction"] == "one_to_many"


def test_stage2_recovers_explicit_non_directional_comparison_pair() -> None:
    visual_structure = "比较对象｜分散预测方式 vs 统一预测体系：对照比较"

    derived = derive_business_relationships(
        visual_structure=visual_structure,
        title="预测运行能力对比",
        module_titles=("分散预测方式", "统一预测体系"),
        top_level_module_titles=("分散预测方式", "统一预测体系"),
    )

    assert len(derived) == 1
    relation = derived[0]
    assert relation["subject"] == "分散预测方式"
    assert relation["objects"] == ["统一预测体系"]
    assert relation["relation"] == "comparison"
    assert relation["direction"] == "unspecified"

    decision = resolve_relation_expression(
        relationships=derived,
        module_count=2,
    )
    assert decision is not None
    assert decision[0] == "comparison_2col"


def test_stage2_preserves_governance_chain_through_shared_control_node() -> None:
    visual_structure = "\n".join(
        (
            "业务牵头方 → 业务口径与结论边界：责任绑定",
            "数据责任方 → 数据来源与版本记录：责任绑定",
            "分析执行方 → 模型方法与计算过程：责任绑定",
            "业务口径与结论边界 → 共同控制机制：治理汇入",
            "数据来源与版本记录 → 共同控制机制：治理汇入",
            "模型方法与计算过程 → 共同控制机制：治理汇入",
            "共同控制机制 → 受保护结果：保护结果",
        )
    )

    derived = derive_business_relationships(
        visual_structure=visual_structure,
        title="统一预测治理",
        module_titles=("业务牵头方", "数据责任方", "分析执行方", "共同控制机制"),
        top_level_module_titles=("业务牵头方", "数据责任方", "分析执行方", "共同控制机制"),
    )

    assert len(derived) == 7
    assert all(item["direction"] == "subject_to_objects" for item in derived)

    incoming_to_control = [
        item
        for item in derived
        if item.get("objects") == ["共同控制机制"]
    ]
    outgoing_from_control = [
        item
        for item in derived
        if item.get("subject") == "共同控制机制"
    ]
    assert len(incoming_to_control) == 3
    assert len(outgoing_from_control) == 1
    assert outgoing_from_control[0]["objects"] == ["受保护结果"]

    decision = resolve_relation_expression(
        relationships=derived,
        module_count=4,
    )
    assert decision is not None
    assert decision[0] == "directed_dependency_2_6"


@pytest.mark.parametrize(
    "case",
    [case for case in _FAILURE_CASES if case.detection_mode == "lint"],
    ids=lambda case: case.name,
)
def test_deterministic_failure_fixtures_hit_their_stable_lint_codes(case) -> None:
    issues = lint_final_script(build_lint_failure_payload(case.name))

    for code in case.expected_lint_codes:
        assert any(code in issue for issue in issues), (case.name, code, issues)


def test_semantic_failure_fixtures_do_not_demand_new_regex_lint_codes() -> None:
    semantic_modes = {"critic", "critic_existing_contracts", "cross_layer_regression"}
    semantic_cases = [case for case in _FAILURE_CASES if case.detection_mode in semantic_modes]

    assert semantic_cases
    assert all(not case.expected_lint_codes for case in semantic_cases)


def test_multistage_roadmap_keeps_explicit_sequence_as_primary_topology() -> None:
    roadmap = _case("roadmap")

    result = resolve_semantic_topology(
        roadmap.verified_relationships,
        module_count=roadmap.module_count,
        page_text=roadmap.page_text,
    )

    assert result["primary_topology"] == "sequence"
    assert not any(
        candidate["topology"] == "dependency_chain"
        for candidate in result["candidates"]
    )
