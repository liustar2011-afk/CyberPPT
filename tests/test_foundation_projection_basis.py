from __future__ import annotations

from cyberppt.foundation_projection import project_source_truth_to_foundation


def _project(conclusion: dict) -> dict:
    source_truth = {
        "sources": [],
        "records": [],
        "conclusions": [conclusion],
        "source_structure": [],
        "semantic_concepts": [],
        "semantic_relations": [],
        "semantic_argument_nodes": [],
        "semantic_argument_relations": [],
    }
    return project_source_truth_to_foundation(source_truth)["arguments"][0]


def test_inferred_conclusion_with_source_refs_stays_inferred() -> None:
    argument = _project(
        {
            "id": "C1",
            "statement": "该关系可以作为后续分析假设。",
            "basis": "inferred",
            "source_refs": ["SU-001", "SU-002"],
        }
    )

    assert argument["support"] == ["SU-001", "SU-002"]
    assert argument["source_refs"] == ["SU-001", "SU-002"]
    assert argument["basis"] == "inferred"
    assert argument["confidence"] == "medium"


def test_source_explicit_claim_origin_projects_as_explicit() -> None:
    argument = _project(
        {
            "id": "C2",
            "statement": "治理和可信使用共同支撑服务输出。",
            "claim_origin": "source_explicit",
            "source_refs": ["SU-003"],
        }
    )

    assert argument["basis"] == "explicit"
    assert argument["confidence"] == "high"


def test_explicit_basis_is_respected_without_source_refs() -> None:
    argument = _project(
        {
            "id": "C3",
            "statement": "来源明确给出该结论。",
            "basis": "explicit",
            "source_refs": [],
        }
    )

    assert argument["basis"] == "explicit"
    assert argument["confidence"] == "high"


def test_inferred_basis_with_refs_and_explicit_looking_support_is_not_promoted() -> None:
    argument = _project(
        {
            "id": "C4",
            "statement": "该综合判断由作者推断。",
            "basis": "inferred",
            "claim_origin": "source_explicit",
            "confidence": "low",
            "source_refs": ["SU-004"],
        }
    )

    assert argument["basis"] == "inferred"
    assert argument["confidence"] == "low"
