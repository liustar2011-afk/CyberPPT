from __future__ import annotations

from script_engine.semantic_contract import audit_final_script_semantic_contract


def test_single_semantic_entry_enforces_explicit_plan_relationship_topology() -> None:
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": [],
                "full_copy": "A与B并列呈现。",
                "onscreen": [{"heading": "并列事项", "text": "A与B并列呈现"}],
                "relationships": [
                    {"from": "A", "to": "B", "relation": "驱动"}
                ],
            }
        ]
    }
    plan = {
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "source_refs": [],
                "primary_relation": {
                    "type": "parallel",
                    "scope": ["A", "B"],
                },
            }
        ]
    }
    foundation = {
        "facts": [],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }

    issues, warnings, diagnostics = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    assert any("AUTHOR_RELATIONSHIP_OUTSIDE_PLAN_TOPOLOGY" in issue for issue in issues)
    assert not any("AUTHOR_RELATIONSHIP_OUTSIDE_PLAN_TOPOLOGY" in warning for warning in warnings)
    assert diagnostics == []
