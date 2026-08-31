from __future__ import annotations

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


def _case_id(case: AuthoringRelationCase) -> str:
    return case.name


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


def test_fixture_catalog_has_eight_unique_positive_and_negative_cases() -> None:
    assert len(_CORRECT_CASES) == 8
    assert len({case.name for case in _CORRECT_CASES}) == 8
    assert len(_FAILURE_CASES) == 8
    assert len({case.name for case in _FAILURE_CASES}) == 8


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
    derived = derive_business_relationships(
        visual_structure=case.visual_structure,
        title="统一预测体系",
        module_titles=case.module_titles,
        top_level_module_titles=case.module_titles,
    )

    assert derived, f"Stage2 failed to recover authored relationships for {case.name}"
    assert set(case.module_titles).issubset(_endpoints(derived))

    decision = resolve_relation_expression(
        relationships=derived,
        module_count=case.module_count,
    )
    assert decision is not None
    assert decision[0] == case.expected_expression_form


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
    roadmap = next(case for case in _CORRECT_CASES if case.name == "roadmap")

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
