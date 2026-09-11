from __future__ import annotations

from script_engine.semantic_contract import validate_relationship_shape


def _final(source: str = "A", target: str = "B") -> dict:
    return {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "relationships": [
                    {"from": source, "to": target, "relation": "支撑"}
                ],
            }
        ]
    }


def _plan(page: dict) -> dict:
    return {"pages": [{"id": "P01", **page}]}


def test_relationship_topology_is_opt_in_when_plan_declares_none() -> None:
    assert validate_relationship_shape(_final(), _plan({})) == []


def test_explicit_secondary_pair_is_authorized() -> None:
    plan = _plan(
        {
            "secondary_relations": [
                {"from": "A", "to": "B", "relation": "supports"}
            ]
        }
    )

    assert validate_relationship_shape(_final(), plan) == []


def test_sequence_primary_scope_authorizes_scoped_edge() -> None:
    plan = _plan(
        {
            "primary_relation": {
                "type": "sequence",
                "scope": ["A", "B", "C"],
            }
        }
    )

    assert validate_relationship_shape(_final("A", "C"), plan) == []


def test_parallel_scope_does_not_silently_authorize_directed_edge() -> None:
    plan = _plan(
        {
            "primary_relation": {
                "type": "parallel",
                "scope": ["A", "B"],
            }
        }
    )

    issues = validate_relationship_shape(_final(), plan)

    assert any("AUTHOR_RELATIONSHIP_OUTSIDE_PLAN_TOPOLOGY" in issue for issue in issues)


def test_scoped_edge_outside_primary_scope_is_rejected() -> None:
    plan = _plan(
        {
            "primary_relation": {
                "type": "hierarchy",
                "scope": ["A", "B"],
            }
        }
    )

    issues = validate_relationship_shape(_final("A", "C"), plan)

    assert any("AUTHOR_RELATIONSHIP_OUTSIDE_PLAN_TOPOLOGY" in issue for issue in issues)


def test_explicit_primary_pair_is_authorized_without_scope_inference() -> None:
    plan = _plan(
        {
            "primary_relation": {
                "type": "dependency",
                "from": "A",
                "to": "B",
            }
        }
    )

    assert validate_relationship_shape(_final(), plan) == []
