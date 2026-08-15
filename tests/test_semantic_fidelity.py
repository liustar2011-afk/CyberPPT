from __future__ import annotations

import unittest

from cyberppt.outline_audit_semantics import _semantic_derivation_issues
from cyberppt.semantic_fidelity import audit_relation_shape


class SemanticFidelityTests(unittest.TestCase):
    def test_projection_outline_allows_empty_content_relations(self) -> None:
        outline = {
            "schema": "cyberppt.outline.v2",
            "authority_mode": "projection_only",
        }
        pages = [
            {
                "page_id": "p01",
                "page_type": "content",
                "core_message": "页面判断",
                "source_refs": ["ST0001"],
                "core_message_derivation": {
                    "source_refs": ["ST0001"],
                    "supporting_statements": ["来源事实"],
                    "derivation": "投影保留来源判断。",
                },
            }
        ]
        source_truth = {"records": [{"id": "ST0001", "statement": "来源事实"}]}

        issues = _semantic_derivation_issues(outline, pages, source_truth)

        self.assertNotIn("CONTENT_RELATIONS_MISSING", {issue.code for issue in issues})

    def test_source_foundation_relation_types_are_accepted_by_runtime_shape_check(self) -> None:
        relations = [
            {"relation": "flows_to", "source_refs": ["ST0001"]},
            {"relation": "constrains", "source_refs": ["ST0001"]},
            {"relation": "collaborates_with", "source_refs": ["ST0001"]},
        ]

        self.assertEqual([], audit_relation_shape(relations))


if __name__ == "__main__":
    unittest.main()
