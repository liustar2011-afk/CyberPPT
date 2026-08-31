from __future__ import annotations

import pytest

from cyberppt.topology_resolver import (
    CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY,
    resolve_semantic_topology,
)


def _relation(subject: str, relation: str, *objects: str) -> dict[str, object]:
    return {
        "subject": subject,
        "relation": relation,
        "objects": list(objects),
        "confidence": 1.0,
        "constraint_authority": "hard",
    }


@pytest.mark.parametrize(
    ("relationships", "module_count", "page_text", "expected"),
    [
        ([_relation("A", "peer_classification", "B")], 2, "", "peer_set"),
        ([_relation("A", "feedback", "B")], 2, "", "feedback_loop"),
        (
            [
                _relation("A", "supports", "C"),
                _relation("B", "supports", "C"),
            ],
            3,
            "",
            "support_convergence",
        ),
        ([_relation("A", "sequence_before", "B")], 2, "", "sequence"),
        (
            [
                _relation("A", "directed_relation", "B"),
                _relation("B", "directed_relation", "C"),
            ],
            3,
            "",
            "dependency_chain",
        ),
        ([_relation("A", "causes", "B")], 2, "", "causal_chain"),
        ([_relation("问题", "problem_response", "响应")], 2, "", "mapping"),
        ([_relation("上层", "layered_as", "下层")], 2, "", "layered_structure"),
        ([_relation("方案A", "comparison", "方案B")], 2, "", "comparison"),
        ([_relation("整体", "contains", "组成部分")], 2, "", "containment"),
        ([], 4, "按两个维度形成四象限矩阵", "matrix"),
    ],
)
def test_representative_resolver_outputs_have_candidate_carrier_families(
    relationships: list[dict[str, object]],
    module_count: int,
    page_text: str,
    expected: str,
) -> None:
    result = resolve_semantic_topology(
        relationships,
        module_count=module_count,
        page_text=page_text,
    )

    assert result["primary_topology"] == expected
    assert expected in CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY
    assert CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY[expected]


def test_comparison_containment_and_matrix_reuse_existing_coarse_carrier_families() -> None:
    mapping = CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY

    assert mapping["comparison"] == {"parallel_set"}
    assert mapping["containment"] == {"layered_architecture"}
    assert mapping["matrix"] == {"parallel_set"}
