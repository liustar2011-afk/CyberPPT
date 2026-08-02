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
                "source_heading": "建设基础",
                "section_thesis": "已有平台和组织基础构成建设依托",
                "argument_role": "foundation",
                "status": "existing",
                "evidence_refs": ["S001"],
                "actor_refs": ["中电联"],
                "primary_consumer": "p01",
                "allowed_merges": [],
            },
            {
                "id": "c01-s02",
                "parent_id": "c01",
                "source_heading": "目标能力",
                "section_thesis": "建设目标形成可验证能力",
                "argument_role": "capability",
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
                "explanation": "建设基础支撑章节使命",
                "evidence_refs": ["S001"],
            }
        ],
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


class SourceArgumentModelTests(unittest.TestCase):
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
                    "source_argument_node_statuses": {"c01": "mixed", "c01-s01": "existing"},
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

    def test_page_status_cannot_drift_from_semantic_node(self) -> None:
        outline = {
            "pages": [
                {
                    "page_id": "p01",
                    "page_type": "content",
                    "primary_argument_node_id": "c01",
                    "source_argument_node_ids": ["c01"],
                    "source_argument_node_statuses": {"c01": "existing"},
                    "core_message_derivation": {"argument_node_ids": ["c01"]},
                }
            ]
        }
        self.assertIn(
            "OUTLINE_ARGUMENT_STATUS_DRIFTED",
            {item["code"] for item in audit_outline_consumption(outline, model())},
        )

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


if __name__ == "__main__":
    unittest.main()
