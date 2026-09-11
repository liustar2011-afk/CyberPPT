from __future__ import annotations

import unittest

from cyberppt.outline_audit_semantics import _semantic_derivation_issues
from cyberppt.semantic_fidelity import (
    audit_composition_relations,
    audit_current_output_objects,
    audit_relation_shape,
    audit_semantic_strength,
)


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

    def test_current_output_object_words_are_not_a_global_taxonomy(self) -> None:
        """Untyped nouns must not become a deterministic current-output gate."""

        issues = audit_current_output_objects(
            "阶段一形成服务包、应用组件和运营工具。",
            "阶段一形成服务包和应用组件；满足条件后再研究运营工具。",
        )

        self.assertEqual([], issues)

    def test_negative_or_future_object_wording_is_left_to_typed_contracts(self) -> None:
        self.assertEqual(
            [],
            audit_current_output_objects(
                "阶段一不建设独立工具，不新增专职岗位。",
                "阶段一不建设独立工具，不新增专职岗位。",
            ),
        )

    def test_actor_role_nouns_do_not_create_a_global_substitution_rule(self) -> None:
        self.assertEqual(
            [],
            audit_semantic_strength(
                "采购角色已经明确。",
                "培训角色已经明确。",
            ),
        )

    def test_ordinary_business_abstraction_does_not_invent_actor_role(self) -> None:
        self.assertEqual(
            [],
            audit_semantic_strength(
                "首轮访谈明确对象、痛点与预算。",
                "访谈需要明确对象、当前痛点和预算来源。",
            ),
        )

    def test_argument_chain_rejects_unsupported_generic_composition(self) -> None:
        pages = [
            {
                "page_id": "p08",
                "page_type": "content",
                "argument_chain": [
                    {
                        "role": "implementation",
                        "statement": "分析组件作为交付模块。",
                        "evidence": {
                            "normalized_fact_ids": ["NF-0077", "NF-0078"]
                        },
                    }
                ],
            }
        ]
        truth = {
            "facts": [
                {
                    "normalized_fact_id": "NF-0077",
                    "statement": "分析组件、校核组件和展示组件并列列示。",
                },
                {
                    "normalized_fact_id": "NF-0078",
                    "statement": "阶段一先验证后交付。",
                },
            ]
        }

        codes = {
            issue.code
            for issue in _semantic_derivation_issues({}, pages, truth)
        }

        self.assertIn("COMPOSITION_RELATION_UNSUPPORTED", codes)

    def test_argument_chain_accepts_sourced_generic_composition(self) -> None:
        pages = [
            {
                "page_id": "p10",
                "page_type": "content",
                "argument_chain": [
                    {
                        "role": "mechanism",
                        "statement": "分析组件、校核组件作为交付模块共同交付。",
                        "evidence": {
                            "normalized_fact_ids": ["NF-0118", "NF-0123"]
                        },
                    }
                ],
            }
        ]
        truth = {
            "facts": [
                {
                    "normalized_fact_id": "NF-0118",
                    "statement": "分析组件作为交付模块。",
                },
                {
                    "normalized_fact_id": "NF-0123",
                    "statement": "校核组件作为交付模块。",
                },
            ]
        }

        codes = {
            issue.code
            for issue in _semantic_derivation_issues({}, pages, truth)
        }

        self.assertNotIn("COMPOSITION_RELATION_UNSUPPORTED", codes)

    def test_plain_object_list_does_not_assert_composition(self) -> None:
        self.assertEqual(
            [],
            audit_composition_relations(
                "可选对象包括分析组件、校核组件和展示组件。",
                "分析组件、校核组件和展示组件。",
            ),
        )

    def test_ordinary_module_noun_does_not_assert_composition(self) -> None:
        self.assertEqual(
            [],
            audit_composition_relations(
                "分析模块覆盖数据处理、结果比较和偏差复核。",
                "对象覆盖数据处理、结果比较和偏差复核。",
            ),
        )

    def test_generic_composition_module_label_does_not_assert_relationship(self) -> None:
        self.assertEqual(
            [],
            audit_composition_relations(
                "主结果承载正式名称，集成模块只说明若干对象的归属。",
                "分析对象和校核对象并列列示。",
            ),
        )

    def test_equivalent_generic_composition_wording_is_supported(self) -> None:
        self.assertEqual(
            [],
            audit_composition_relations(
                "分析组件并入交付模块。",
                "分析组件作为交付模块。",
            ),
        )


if __name__ == "__main__":
    unittest.main()
