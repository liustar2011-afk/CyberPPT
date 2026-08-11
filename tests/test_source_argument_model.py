from __future__ import annotations

import unittest

from cyberppt.source_argument_model import (
    SCHEMA,
    audit_outline_consumption,
    extract_model,
    render_model_block,
    validate_model,
)


def model() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "version": 1,
        "document_thesis": {
            "statement": "依托基础设施形成可验证运营合作",
            "argument_role": "thesis",
            "argument_weight": "core",
            "status": "mixed",
            "evidence_refs": ["S001"],
            "actor_refs": ["中电联"],
        },
        "section_nodes": [
            {
                "id": "c01",
                "source_heading": "第一章",
                "section_thesis": "交代合作依托",
                "argument_role": "foundation",
                "argument_weight": "core",
                "level": 1,
                "status": "mixed",
                "evidence_refs": ["S001"],
                "actor_refs": ["中电联"],
                "primary_consumer": "chapter-1",
                "subsection_ids": ["c01-s01", "c01-s02"],
                "allowed_merges": [],
            }
        ],
        "subsection_nodes": [
        {
            "id": "c01-s01",
                "parent_id": "c01",
                "level": 2,
                "source_heading": "建设基础",
                "section_thesis": "已有平台和组织基础构成建设依托",
                "argument_role": "foundation",
                "argument_weight": "supporting",
                "status": "existing",
                "evidence_refs": ["S001"],
                "actor_refs": ["中电联"],
                "primary_consumer": "p01",
                "allowed_merges": [],
            },
            {
                "id": "c01-s02",
                "parent_id": "c01",
                "level": 2,
                "source_heading": "目标能力",
                "section_thesis": "建设目标形成可验证能力",
                "argument_role": "capability",
                "argument_weight": "core",
                "status": "planned",
                "evidence_refs": ["S001"],
                "actor_refs": ["中电联"],
                "primary_consumer": "p02",
                "allowed_merges": [],
            },
        ],
        "argument_relations": [
            {
                "id": "r01",
                "from": "c01-s01",
                "to": "c01",
                "relation": "supports",
                "weight_effect": "none",
                "explanation": "建设基础支撑章节使命",
                "evidence_refs": ["S001"],
            }
        ],
        "argument_weighting": {
            "definition": "core 是独立主张，supporting 是展开模块；关系不改变权重。",
            "core_node_ids": ["c01", "c01-s02"],
            "supporting_node_ids": ["c01-s01"],
            "detail_node_ids": [],
            "constraint_node_ids": [],
            "review_notes": [],
        },
        "mece_rules": {
            "partition_basis": "按源材料章节层级与论证功能划分",
            "exhaustive_scope": "覆盖全文一级、二级论点",
            "overlap_policy": "相同对象不同维度保留独立节点并声明关系",
            "groups": [
                {
                    "parent_id": "c01",
                    "partition_basis": "按建设依托与章节使命划分",
                    "exhaustive_scope": "第一章的两个示例节点",
                    "overlap_policy": "不同层级通过关系连接",
                    "node_ids": ["c01-s01", "c01-s02"],
                }
            ],
            "review_notes": [],
        },
        "source_gaps": [],
    }


def strict_model() -> tuple[dict[str, object], set[str], list[dict[str, object]]]:
    value = model()
    heading_unit = "SU-ABCDEF1234-HEADING-BBBBBBBBBBBB-01"
    evidence_unit = "SU-ABCDEF1234-PARAGRAPH-AAAAAAAAAAAA-01"
    value["interpretation_contract_mode"] = "strict"
    value["document_semantics"] = {
        "document_role": "业务方案",
        "subject_of_report": "目标业务事项",
        "primary_thesis": value["document_thesis"]["statement"],
        "decision_boundary": "部分事项待确认",
        "author_purpose": "推动相关方形成共同判断",
        "argument_method": [{"statement": "先提出主张再给出支撑", "source_refs": [heading_unit]}],
        "supporting_basis": [{"statement": "正文提供事实支撑", "source_refs": [evidence_unit]}],
        "business_objects": ["业务对象"],
        "scope": "约定范围",
        "decision_intent": "确认后续动作",
    }
    value["document_thesis"]["claim_origin"] = "source_explicit"
    value["document_thesis"]["evidence_refs"] = [evidence_unit]
    for node in value["section_nodes"] + value["subsection_nodes"]:
        node["claim_origin"] = "source_explicit"
        node["evidence_refs"] = [evidence_unit]
    for relation in value["argument_relations"]:
        relation["claim_origin"] = "source_explicit"
        relation["evidence_refs"] = [evidence_unit]
    value["heading_semantic_cards"] = [
        {
            "heading_id": "H-ABCDEF1234-BBBBBBBBBBBB-01",
            "source_unit_id": heading_unit,
            "source_heading": "第一章",
            "level": 1,
            "semantic_function": "提出章节主张",
            "author_claim": "交代本章需要成立的判断",
            "argument_role": "foundation",
            "argument_weight": "core",
            "claim_origin": "source_explicit",
            "evidence_refs": [heading_unit],
        }
    ]
    value["section_nodes"][0]["source_heading_id"] = "H-ABCDEF1234-BBBBBBBBBBBB-01"
    value["inference_register"] = []
    value["concept_occurrence_graph"] = {
        "concepts": [],
        "relations": [],
        "review_notes": [],
    }
    value["source_coverage"] = {
        "assignments": [
            {
                "source_unit_refs": [evidence_unit],
                "semantic_node_ids": ["c01"],
                "summary": "正文事实归入第一章语义节点",
            }
        ],
        "intentional_omissions": [],
        "review_notes": [],
    }
    headings = [
        {
            "heading_id": "H-ABCDEF1234-BBBBBBBBBBBB-01",
            "unit_id": heading_unit,
            "title": "第一章",
            "level": 1,
        }
    ]
    return value, {heading_unit, evidence_unit}, headings


class SourceArgumentModelTests(unittest.TestCase):
    def test_formal_semantic_outline_enables_disposition_by_default(self) -> None:
        outline = {
            "semantic_argument_model_mode": "required",
            "pages": [],
        }

        codes = {item["code"] for item in audit_outline_consumption(outline, model())}

        self.assertIn("OUTLINE_ARGUMENT_DISPOSITION_MODE_REQUIRED", codes)
        self.assertIn("OUTLINE_ARGUMENT_DISPOSITION_MISSING", codes)

    def test_required_disposition_blocks_silent_subsection_loss(self) -> None:
        outline = {
            "argument_node_disposition_mode": "required",
            "argument_node_dispositions": [{
                "node_id": "c01-s02",
                "disposition": "intentional_omission",
                "rationale": "Not used by the selected route.",
                "omission_reason": "Outside the approved communication goal.",
            }],
            "pages": [{
                "page_id": "p01",
                "page_type": "content",
                "primary_argument_node_id": "c01",
                "source_argument_node_ids": ["c01"],
                "source_argument_node_roles": {"c01": "foundation"},
                "source_argument_node_statuses": {"c01": "mixed"},
                "source_argument_node_weights": {"c01": "core"},
                "core_message_derivation": {"argument_node_ids": ["c01"]},
                "detail_refs": ["c01-s01"],
            }],
        }

        codes = {item["code"] for item in audit_outline_consumption(outline, model())}

        self.assertIn("OUTLINE_ARGUMENT_DISPOSITION_MISSING", codes)

    def test_merged_disposition_requires_formal_consumption_and_reason(self) -> None:
        outline = {
            "argument_node_disposition_mode": "required",
            "argument_node_dispositions": [
                {
                    "node_id": "c01-s01",
                    "disposition": "merged_page",
                    "page_id": "p01",
                    "rationale": "Merged into the chapter page.",
                },
                {
                    "node_id": "c01-s02",
                    "disposition": "intentional_omission",
                    "rationale": "Not used by the selected route.",
                    "omission_reason": "Outside the approved communication goal.",
                },
            ],
            "pages": [{
                "page_id": "p01",
                "page_type": "content",
                "primary_argument_node_id": "c01",
                "source_argument_node_ids": ["c01"],
                "source_argument_node_roles": {"c01": "foundation"},
                "source_argument_node_statuses": {"c01": "mixed"},
                "source_argument_node_weights": {"c01": "core"},
                "core_message_derivation": {"argument_node_ids": ["c01"]},
                "detail_refs": ["c01-s01"],
            }],
        }

        codes = {item["code"] for item in audit_outline_consumption(outline, model())}

        self.assertIn("OUTLINE_MERGED_ARGUMENT_NOT_CONSUMED", codes)
        self.assertIn("OUTLINE_ARGUMENT_MERGE_REASON_MISSING", codes)
        self.assertIn("OUTLINE_ARGUMENT_MERGE_TOPIC_MISSING", codes)

    def test_protected_argument_cannot_be_silently_omitted(self) -> None:
        candidate = model()
        candidate["subsection_nodes"][0]["evidence_refs"] = [
            f"S{index:03d}" for index in range(1, 7)
        ]
        outline = {
            "argument_node_disposition_mode": "required",
            "argument_node_dispositions": [
                {
                    "node_id": "c01-s01",
                    "disposition": "intentional_omission",
                    "rationale": "Compressed for length.",
                    "omission_reason": "Supporting material.",
                },
                {
                    "node_id": "c01-s02",
                    "disposition": "intentional_omission",
                    "rationale": "Compressed for length.",
                    "omission_reason": "Core material.",
                },
            ],
            "pages": [],
        }

        codes = {item["code"] for item in audit_outline_consumption(outline, candidate)}

        self.assertIn("OUTLINE_PROTECTED_ARGUMENT_OMITTED", codes)

    def test_user_authorized_omission_of_protected_argument_is_traceable(self) -> None:
        outline = {
            "argument_node_disposition_mode": "required",
            "argument_node_dispositions": [
                {
                    "node_id": "c01-s01",
                    "disposition": "intentional_omission",
                    "rationale": "User excluded this supporting topic.",
                    "omission_reason": "Outside the confirmed scope.",
                    "user_authorized_omission": True,
                    "user_decision_ref": "conversation:exclude-foundation",
                },
                {
                    "node_id": "c01-s02",
                    "disposition": "intentional_omission",
                    "rationale": "User excluded this core topic.",
                    "omission_reason": "Outside the confirmed scope.",
                    "user_authorized_omission": True,
                    "user_decision_ref": "conversation:exclude-capability",
                },
            ],
            "pages": [],
        }

        codes = {item["code"] for item in audit_outline_consumption(outline, model())}

        self.assertNotIn("OUTLINE_PROTECTED_ARGUMENT_OMITTED", codes)

    def test_marked_nested_json_is_extracted(self) -> None:
        parsed = extract_model("# 语义\n\n" + render_model_block(model()))
        self.assertEqual(SCHEMA, parsed["schema"])
        self.assertEqual("依托基础设施形成可验证运营合作", parsed["document_thesis"]["statement"])

    def test_validation_preserves_source_headings_and_relations(self) -> None:
        issues = validate_model(model(), required_headings=["第一章"])
        self.assertEqual([], issues)
        broken = model()
        broken["section_nodes"][0]["source_heading"] = "别的标题"
        self.assertIn(
            "SEMANTIC_SOURCE_HEADINGS_NOT_PRESERVED",
            {item["code"] for item in validate_model(broken, required_headings=["第一章"])},
        )

    def test_outline_must_consume_nodes_and_declare_primary(self) -> None:
        outline = {
            "pages": [
                {
                    "page_id": "p01",
                    "page_type": "content",
                    "primary_argument_node_id": "c01",
                    "source_argument_node_ids": ["c01", "c01-s01"],
                    "source_argument_node_roles": {"c01": "foundation", "c01-s01": "foundation"},
                    "source_argument_node_statuses": {"c01": "mixed", "c01-s01": "existing"},
                    "source_argument_node_weights": {"c01": "core", "c01-s01": "supporting"},
                    "core_message_derivation": {"argument_node_ids": ["c01", "c01-s01"]},
                }
            ]
        }
        self.assertEqual([], audit_outline_consumption(outline, model()))
        outline["pages"][0]["core_message_derivation"] = {"argument_node_ids": []}
        self.assertIn(
            "OUTLINE_DERIVATION_NODE_MISSING",
            {item["code"] for item in audit_outline_consumption(outline, model())},
        )

    def test_core_section_requires_primary_consumer_by_default(self) -> None:
        codes = {
            item["code"]
            for item in audit_outline_consumption({"pages": []}, model())
        }
        self.assertIn("ARGUMENT_NODE_WITHOUT_PRIMARY_CONSUMER", codes)

    def test_non_core_section_defaults_to_selective_consumption(self) -> None:
        candidate = model()
        candidate["section_nodes"][0]["argument_weight"] = "detail"
        codes = {
            item["code"]
            for item in audit_outline_consumption({"pages": []}, candidate)
        }
        self.assertNotIn("ARGUMENT_NODE_WITHOUT_PRIMARY_CONSUMER", codes)

    def test_non_core_section_can_explicitly_require_primary_consumer(self) -> None:
        candidate = model()
        candidate["section_nodes"][0]["argument_weight"] = "constraint"
        candidate["section_nodes"][0]["required_for_primary_consumer"] = True
        codes = {
            item["code"]
            for item in audit_outline_consumption({"pages": []}, candidate)
        }
        self.assertIn("ARGUMENT_NODE_WITHOUT_PRIMARY_CONSUMER", codes)

    def test_page_status_cannot_drift_from_semantic_node(self) -> None:
        outline = {
            "pages": [
                {
                    "page_id": "p01",
                    "page_type": "content",
                    "primary_argument_node_id": "c01",
                    "source_argument_node_ids": ["c01"],
                    "source_argument_node_roles": {"c01": "foundation"},
                    "source_argument_node_statuses": {"c01": "existing"},
                    "source_argument_node_weights": {"c01": "core"},
                    "core_message_derivation": {"argument_node_ids": ["c01"]},
                }
            ]
        }
        self.assertIn(
            "OUTLINE_ARGUMENT_STATUS_DRIFTED",
            {item["code"] for item in audit_outline_consumption(outline, model())},
        )

    def test_core_weight_is_not_inferred_from_support_relation(self) -> None:
        broken = model()
        broken["section_nodes"][0]["argument_weight"] = "supporting"
        codes = {item["code"] for item in validate_model(broken)}
        self.assertIn("SEMANTIC_ARGUMENT_WEIGHT_DRIFTED", codes)

    def test_flattened_heading3_is_rejected(self) -> None:
        broken = model()
        broken["subsection_nodes"][1]["parent_id"] = "c01-s01"
        codes = {item["code"] for item in validate_model(broken)}
        self.assertIn("SEMANTIC_NODE_LEVEL_INVALID", codes)

    def test_outline_must_copy_argument_weight(self) -> None:
        outline = {
            "pages": [
                {
                    "page_id": "p01",
                    "page_type": "content",
                    "primary_argument_node_id": "c01",
                    "source_argument_node_ids": ["c01"],
                    "source_argument_node_roles": {"c01": "foundation"},
                    "source_argument_node_statuses": {"c01": "mixed"},
                    "source_argument_node_weights": {"c01": "supporting"},
                    "core_message_derivation": {"argument_node_ids": ["c01"]},
                }
            ]
        }
        codes = {item["code"] for item in audit_outline_consumption(outline, model())}
        self.assertIn("OUTLINE_ARGUMENT_WEIGHT_DRIFTED", codes)

    def test_outline_cannot_downgrade_source_argument_role(self) -> None:
        outline = {
            "pages": [
                {
                    "page_id": "p01",
                    "page_type": "content",
                    "primary_argument_node_id": "c01-s02",
                    "source_argument_node_ids": ["c01-s02"],
                    "source_argument_node_roles": {"c01-s02": "foundation"},
                    "source_argument_node_statuses": {"c01-s02": "planned"},
                    "source_argument_node_weights": {"c01-s02": "core"},
                    "core_message_derivation": {"argument_node_ids": ["c01-s02"]},
                }
            ]
        }
        codes = {item["code"] for item in audit_outline_consumption(outline, model())}
        self.assertIn("OUTLINE_ARGUMENT_ROLE_DRIFTED", codes)

    def test_lossy_question_mark_text_is_rejected(self) -> None:
        broken = model()
        broken["document_thesis"]["statement"] = "????????????????"
        codes = {item["code"] for item in validate_model(broken)}
        self.assertIn("SEMANTIC_ARGUMENT_MODEL_TEXT_CORRUPTED", codes)

    def test_actor_refs_must_remain_an_array(self) -> None:
        broken = model()
        broken["section_nodes"][0]["actor_refs"] = "中电联"
        codes = {item["code"] for item in validate_model(broken)}
        self.assertIn("SEMANTIC_SECTION_ACTORS_INVALID", codes)

    def test_formal_model_owns_document_semantics(self) -> None:
        broken = model()
        codes = {item["code"] for item in validate_model(broken, require_document_context=True)}
        self.assertIn("SEMANTIC_DOCUMENT_CONTEXT_MISSING", codes)
        broken["document_semantics"] = {
            "document_role": "运营合作方案",
            "subject_of_report": "依托基础设施开展行业服务",
            "primary_thesis": "不同主论点",
            "decision_boundary": "待调研确认",
            "business_objects": ["数据服务"],
            "scope": "电力行业",
            "decision_intent": "启动调研",
        }
        codes = {item["code"] for item in validate_model(broken, require_document_context=True)}
        self.assertIn("SEMANTIC_DOCUMENT_CONTEXT_THESIS_DRIFTED", codes)

    def test_strict_model_binds_heading_cards_and_stable_source_units(self) -> None:
        value, unit_ids, headings = strict_model()

        issues = validate_model(
            value,
            required_headings=["第一章"],
            required_heading_records=headings,
            source_unit_ids=unit_ids,
            require_document_context=True,
        )

        self.assertEqual([], issues)

    def test_strict_model_requires_every_content_unit_disposition(self) -> None:
        value, unit_ids, headings = strict_model()
        extra = "SU-ABCDEF1234-PARAGRAPH-CCCCCCCCCCCC-01"
        codes = {
            item["code"]
            for item in validate_model(
                value,
                required_heading_records=headings,
                source_unit_ids=unit_ids | {extra},
                required_content_unit_ids={next(iter(value["document_thesis"]["evidence_refs"])), extra},
            )
        }
        self.assertIn("SEMANTIC_SOURCE_UNIT_UNDISPOSED", codes)

    def test_source_assignment_must_bind_target_node_evidence(self) -> None:
        value, unit_ids, headings = strict_model()
        evidence = next(iter(value["document_thesis"]["evidence_refs"]))
        value["section_nodes"][0]["evidence_refs"] = []
        codes = {
            item["code"]
            for item in validate_model(
                value,
                required_heading_records=headings,
                source_unit_ids=unit_ids,
                required_content_unit_ids={evidence},
            )
        }
        self.assertIn("SEMANTIC_SOURCE_ASSIGNMENT_EVIDENCE_DISCONNECTED", codes)

    def test_specific_intentional_omission_satisfies_disposition(self) -> None:
        value, unit_ids, headings = strict_model()
        extra = "SU-ABCDEF1234-PARAGRAPH-CCCCCCCCCCCC-01"
        value["source_coverage"]["intentional_omissions"] = [
            {
                "source_unit_refs": [extra],
                "reason": "该段仅重复附件字段定义，正文论点节点不再重复展开。",
            }
        ]
        issues = validate_model(
            value,
            required_heading_records=headings,
            source_unit_ids=unit_ids | {extra},
            required_content_unit_ids={
                next(iter(value["document_thesis"]["evidence_refs"])),
                extra,
            },
        )
        self.assertNotIn(
            "SEMANTIC_SOURCE_UNIT_UNDISPOSED",
            {item["code"] for item in issues},
        )

    def test_strict_model_rejects_legacy_evidence_and_missing_heading_card(self) -> None:
        value, unit_ids, headings = strict_model()
        value["document_thesis"]["evidence_refs"] = ["S001"]
        value["heading_semantic_cards"] = []

        codes = {
            item["code"]
            for item in validate_model(
                value,
                required_heading_records=headings,
                source_unit_ids=unit_ids,
            )
        }

        self.assertIn("SEMANTIC_STABLE_EVIDENCE_REQUIRED", codes)
        self.assertIn("SEMANTIC_SOURCE_HEADINGS_UNINTERPRETED", codes)

    def test_editorial_hypothesis_cannot_be_promoted_into_source_nodes(self) -> None:
        value, unit_ids, headings = strict_model()
        value["section_nodes"][0]["claim_origin"] = "editorial_hypothesis"
        value["section_nodes"][0]["inference_id"] = "I001"
        value["inference_register"] = [
            {
                "id": "I001",
                "statement": "候选编辑框架",
                "claim_origin": "editorial_hypothesis",
                "basis_refs": [next(iter(unit_ids))],
                "affected_node_ids": ["c01"],
                "handling": "仅供 Director 评估",
            }
        ]

        codes = {
            item["code"]
            for item in validate_model(
                value,
                required_heading_records=headings,
                source_unit_ids=unit_ids,
            )
        }

        self.assertIn("SEMANTIC_EDITORIAL_HYPOTHESIS_PROMOTED", codes)

    def test_source_implied_heading_interpretation_must_be_registered(self) -> None:
        value, unit_ids, headings = strict_model()
        heading_id = value["heading_semantic_cards"][0]["heading_id"]
        evidence_unit = value["heading_semantic_cards"][0]["source_unit_id"]
        value["heading_semantic_cards"][0]["claim_origin"] = "source_implied"
        value["heading_semantic_cards"][0]["inference_id"] = "I001"
        value["section_nodes"][0]["claim_origin"] = "source_implied"
        value["section_nodes"][0]["inference_id"] = "I001"
        value["inference_register"] = [
            {
                "id": "I001",
                "statement": "该标题隐含一个章节判断",
                "claim_origin": "source_implied",
                "basis_refs": [evidence_unit],
                "affected_node_ids": [heading_id, "c01"],
                "handling": "保留为有依据的隐含解释",
            }
        ]

        issues = validate_model(
            value,
            required_heading_records=headings,
            source_unit_ids=unit_ids,
        )

        self.assertEqual([], issues)

    def test_repeated_concept_can_be_preserved_as_different_dimensions(self) -> None:
        value, unit_ids, headings = strict_model()
        value["concept_occurrence_graph"] = {
            "concepts": [
                {
                    "concept_id": "K001",
                    "canonical_label": "同一业务对象",
                    "occurrence_unit_ids": sorted(unit_ids),
                    "resolution": "different_dimension",
                    "rationale": "两处分别描述对象的构成和形成后的作用，不能因词语重复而合并。",
                }
            ],
            "relations": [],
            "review_notes": [],
        }

        issues = validate_model(
            value,
            required_heading_records=headings,
            source_unit_ids=unit_ids,
        )

        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
