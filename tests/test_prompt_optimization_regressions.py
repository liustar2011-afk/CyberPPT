from __future__ import annotations

import pytest

from cyberppt.onscreen_expression import expression_constraints
from cyberppt.visual_stage.compiler import _build_executable_page


def _source(*, primary_topology: str) -> dict[str, object]:
    return {
        "page_id": "p01",
        "page_number": 1,
        "page_title": "Title",
        "page_mission": "Explain the relationship.",
        "core_judgment": "The relationship is clear.",
        "prompt_mode": "semantic_brief",
        "locked_text_items": [
            {"text_id": "P01-T01", "text": "Input"},
            {"text_id": "P01-T02", "text": "Result"},
        ],
        "business_relationships": [],
        "stage01_relationship_features": {
            "semantic_topology": {
                "primary_topology": primary_topology,
                "constraint_authority": "hard",
            }
        },
        "expression_constraints": expression_constraints("neutral_structure_1_7"),
    }


def _decision(*, topology: str, grammar: str) -> dict[str, object]:
    return {
        "page_id": "p01",
        "evidence_units": [
            {"key": "input", "summary": "Input", "text_ids": ["P01-T01"]},
            {"key": "result", "summary": "Result", "text_ids": ["P01-T02"]},
        ],
        "candidates": [
            {
                "id": "c1",
                "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
                "reading_sequence": ["input", "result"],
                "spatial_grammar": [grammar],
                "topology": topology,
                "direction": "left_to_right",
                "visual_intent_type": "relationship",
                "expression_fit": {
                    "form": "neutral_structure_1_7",
                    "constraint_status": "default_profile",
                    "satisfied_constraints": [],
                    "reading_relation": "source relationship",
                    "balance_strategy": "source balance",
                    "changed_constraints": [],
                    "deviation_reason": "",
                },
            }
        ],
        "selected_candidate": "c1",
    }


def test_parallel_topology_allows_equal_weight_nodes() -> None:
    page = _build_executable_page(
        _source(primary_topology="peer_set"),
        _decision(topology="parallel_set", grammar="peer"),
    )

    assert "equal_peer_cards" not in page["semantic_graph"]["forbidden_structures"]
    assert "forced_sequential_edge" in page["semantic_graph"]["forbidden_structures"]
    label_rule = " ".join(page["content_lock"]["forbidden_transformations"])
    assert "may use stronger typography or a line break" in label_rule


def test_feedback_constraint_requires_verified_feedback_topology() -> None:
    with pytest.raises(ValueError, match="incompatible with verified semantic topology"):
        _build_executable_page(
            _source(primary_topology="sequence"),
            _decision(topology="lifecycle_loop", grammar="feedback"),
        )
