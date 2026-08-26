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

    def test_current_output_rejects_object_supported_only_as_future_research(self) -> None:
        issues = audit_current_output_objects(
            "首期形成课程、场景、平台和付费项目四类成果。",
            "首期形成1门课程、1套实训场景和1个付费试点；满足条件后再研究平台。",
        )

        self.assertEqual(
            ["ARGUMENT_CHAIN_OUTPUT_POLARITY_CONFLICT"],
            [issue.code for issue in issues],
        )

    def test_negative_boundary_is_not_reinterpreted_as_current_output(self) -> None:
        issues = audit_current_output_objects(
            "首期不建设独立SaaS平台，不新增专职团队。",
            "首期不建设独立SaaS平台，不新增专职团队。",
        )

        self.assertEqual([], issues)

    def test_delivery_clause_does_not_promote_later_course_module_phrase(self) -> None:
        issues = audit_current_output_objects(
            "企业班先销售后交付，预测能力作为课程模块。",
            "交易与AI决策企业班先销售后交付。",
        )

        self.assertEqual([], issues)

    def test_training_audience_cannot_be_substituted_with_procurement_actor(self) -> None:
        issues = audit_semantic_strength("采购主体需要明确。", "培训对象是谁。")

        self.assertIn("ACTOR_ROLE_SUBSTITUTED", {issue.code for issue in issues})

    def test_training_audience_role_is_preserved(self) -> None:
        self.assertEqual(
            [],
            audit_semantic_strength("培训对象是谁。", "培训对象是谁。"),
        )

    def test_ordinary_business_abstraction_does_not_invent_actor_role(self) -> None:
        self.assertEqual(
            [],
            audit_semantic_strength(
                "首轮访谈需要明确对象、痛点与预算。",
                "培训对象是谁、当前痛点是什么、年度培训预算来自哪里。",
            ),
        )

    def test_p08_argument_chain_rejects_unsupported_course_composition(self) -> None:
        pages = [
            {
                "page_id": "p08",
                "page_type": "content",
                "argument_chain": [
                    {
                        "role": "implementation",
                        "statement": "预测能力作为课程模块。",
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
                    "statement": "交易与AI决策、负荷与电价预测、风光功率预测",
                },
                {
                    "normalized_fact_id": "NF-0078",
                    "statement": "单期企业班，先销售后交付",
                },
            ]
        }

        codes = {
            issue.code
            for issue in _semantic_derivation_issues({}, pages, truth)
        }

        self.assertIn("COMPOSITION_RELATION_UNSUPPORTED", codes)

    def test_p10_argument_chain_accepts_sourced_course_composition(self) -> None:
        pages = [
            {
                "page_id": "p10",
                "page_type": "content",
                "argument_chain": [
                    {
                        "role": "mechanism",
                        "statement": "负荷与电价预测、风光功率预测作为交易课程模块共同交付。",
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
                    "statement": "负荷与电价预测及量价策略实训：A，作为交易课程模块",
                },
                {
                    "normalized_fact_id": "NF-0123",
                    "statement": "风光功率预测与考核实训：A，作为交易课程模块",
                },
            ]
        }

        codes = {
            issue.code
            for issue in _semantic_derivation_issues({}, pages, truth)
        }

        self.assertNotIn("COMPOSITION_RELATION_UNSUPPORTED", codes)

    def test_course_list_does_not_assert_composition(self) -> None:
        self.assertEqual(
            [],
            audit_composition_relations(
                "适合课程包括交易与AI决策、负荷与电价预测、风光功率预测。",
                "交易与AI决策、负荷与电价预测、风光功率预测。",
            ),
        )

    def test_ordinary_module_noun_does_not_assert_composition(self) -> None:
        self.assertEqual(
            [],
            audit_composition_relations(
                "预测模块覆盖数据处理、模型比较和偏差分析。",
                "课程覆盖数据处理、模型比较和偏差分析。",
            ),
        )

    def test_generic_composition_module_label_does_not_assert_relationship(self) -> None:
        self.assertEqual(
            [],
            audit_composition_relations(
                "主MVP承载产品名称，集成模块只说明两类预测能力的课程归属。",
                "负荷与电价预测及量价策略实训。",
            ),
        )

    def test_equivalent_composition_wording_is_supported(self) -> None:
        self.assertEqual(
            [],
            audit_composition_relations(
                "负荷与电价预测并入交易课程。",
                "负荷与电价预测及量价策略实训：A，作为交易课程模块。",
            ),
        )


if __name__ == "__main__":
    unittest.main()
