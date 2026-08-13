from __future__ import annotations

import unittest

from cyberppt.semantic_cross_audit import (
    semantic_evidence_cross_issues,
    source_chapter_placement_suggestions,
)
from test_source_argument_model import model, strict_model


class SemanticEvidenceCrossAuditTests(unittest.TestCase):
    def test_placement_suggests_rehome_from_semantic_binding_and_outline_consumer(self) -> None:
        model = {
            "subsection_nodes": [{
                "id": "node-mechanism",
                "source_heading": "运行机制",
                "argument_role": "operation",
            }],
        }
        truth = {"records": [{
            "id": "S001",
            "semantic_node_ids": ["node-mechanism"],
            "source_unit_refs": ["SU-A"],
        }]}
        outline = {"pages": [{
            "page_type": "content",
            "chapter_id": "mechanism",
            "source_argument_node_ids": ["node-mechanism"],
        }]}

        suggestions = source_chapter_placement_suggestions(
            model,
            truth,
            source_units=[{"unit_id": "SU-A", "heading_path": ["实施保障"]}],
            outline=outline,
        )

        self.assertEqual("suggest_reporting_rehome", suggestions[0]["outcome"])
        self.assertEqual(["mechanism"], suggestions[0]["suggested_chapter_ids"])
        self.assertEqual(["semantic_node_scope_match", "source_heading_context_mismatch"], suggestions[0]["reason_codes"])

    def test_placement_suggests_cross_chapter_reference_for_multiple_consumers(self) -> None:
        model = {"subsection_nodes": [{"id": "node-a", "source_heading": "运行机制"}]}
        truth = {"records": [{"id": "S001", "semantic_node_ids": ["node-a"], "source_unit_refs": ["SU-A"]}]}
        outline = {"pages": [
            {"page_type": "content", "chapter_id": "mechanism", "source_argument_node_ids": ["node-a"]},
            {"page_type": "content", "chapter_id": "implementation", "source_argument_node_ids": ["node-a"]},
        ]}

        suggestions = source_chapter_placement_suggestions(
            model, truth, source_units=[{"unit_id": "SU-A", "heading_path": ["实施保障"]}], outline=outline,
        )

        self.assertEqual("suggest_cross_chapter_reference", suggestions[0]["outcome"])
        self.assertEqual(["implementation", "mechanism"], suggestions[0]["suggested_chapter_ids"])

    def test_placement_skips_heading_only_difference_without_semantic_binding(self) -> None:
        suggestions = source_chapter_placement_suggestions(
            {"subsection_nodes": []},
            {"records": []},
            source_units=[{"unit_id": "SU-A", "heading_path": ["实施保障"]}],
            outline={"pages": []},
        )

        self.assertEqual([], suggestions)

    def test_placement_does_not_invent_target_chapter_without_outline(self) -> None:
        suggestions = source_chapter_placement_suggestions(
            {"subsection_nodes": [{"id": "node-a", "source_heading": "运行机制"}]},
            {"records": [{"id": "S001", "semantic_node_ids": ["node-a"], "source_unit_refs": ["SU-A"]}]},
            source_units=[{"unit_id": "SU-A", "heading_path": ["实施保障"]}],
        )

        self.assertEqual([], suggestions)

    def test_protected_semantic_node_requires_all_source_units_in_truth(self) -> None:
        model = {
            "interpretation_contract_mode": "strict",
            "section_nodes": [],
            "subsection_nodes": [{
                "id": "sub-01-01",
                "source_heading": "建设基础",
                "argument_weight": "core",
                "evidence_refs": ["SU-A", "SU-B", "SU-C"],
            }],
        }
        truth = {
            "records": [{
                "id": "ST001",
                "priority": "P1",
                "claim_origin": "source_explicit",
                "semantic_node_ids": ["sub-01-01"],
                "source_unit_refs": ["SU-A"],
            }],
        }

        codes = {
            item["code"] for item in semantic_evidence_cross_issues(
                model,
                truth,
                source_unit_ids={"SU-A", "SU-B", "SU-C"},
            )
        }

        self.assertIn("SOURCE_TRUTH_PROTECTED_EVIDENCE_GAP", codes)

    def test_protected_semantic_node_cannot_be_silently_omitted(self) -> None:
        model = {
            "interpretation_contract_mode": "strict",
            "section_nodes": [],
            "subsection_nodes": [{
                "id": "sub-01-01",
                "source_heading": "建设基础",
                "argument_weight": "core",
                "evidence_refs": ["SU-A", "SU-B"],
            }],
        }
        truth = {
            "intentional_source_unit_omissions": [{
                "source_unit_refs": ["SU-B"],
                "reason": "自动压缩篇幅。",
            }],
            "records": [{
                "id": "ST001",
                "priority": "P1",
                "claim_origin": "source_explicit",
                "semantic_node_ids": ["sub-01-01"],
                "source_unit_refs": ["SU-A"],
            }],
        }

        codes = {
            item["code"] for item in semantic_evidence_cross_issues(
                model,
                truth,
                source_unit_ids={"SU-A", "SU-B"},
            )
        }

        self.assertIn("SOURCE_TRUTH_PROTECTED_OMISSION_UNAUTHORIZED", codes)
    def test_strict_p0_record_forms_bidirectional_binding(self) -> None:
        semantic, unit_ids, _headings = strict_model()
        evidence_unit = next(
            ref
            for ref in semantic["section_nodes"][0]["evidence_refs"]
            if "PARAGRAPH" in ref
        )
        truth = {
            "records": [
                {
                    "id": "S001",
                    "priority": "P0",
                    "claim_role": "fact",
                    "claim_origin": "source_explicit",
                    "source_unit_refs": [evidence_unit],
                    "semantic_node_ids": ["c01"],
                }
            ] + [
                {
                    "id": f"S-{node['id']}",
                    "priority": "P1",
                    "claim_role": "fact",
                    "claim_origin": "source_explicit",
                    "source_unit_refs": list(node.get("evidence_refs", [])),
                    "semantic_node_ids": [node["id"]],
                }
                for node in semantic.get("subsection_nodes", [])
                if node.get("argument_weight") in {"core", "constraint"}
            ]
        }

        self.assertEqual(
            [],
            semantic_evidence_cross_issues(
                semantic,
                truth,
                source_unit_ids=unit_ids,
            ),
        )

    def test_legacy_semantic_refs_must_exist_in_source_truth(self) -> None:
        semantic = model()

        codes = {
            item["code"]
            for item in semantic_evidence_cross_issues(
                semantic,
                {"records": [{"id": "S999"}]},
                source_unit_ids=set(),
            )
        }

        self.assertIn("SEMANTIC_LEGACY_EVIDENCE_UNKNOWN", codes)
        self.assertIn("SEMANTIC_CORE_CLAIM_UNRESOLVED", codes)

    def test_strict_p0_record_cannot_bypass_semantic_mapping(self) -> None:
        semantic, unit_ids, _headings = strict_model()
        truth = {
            "records": [
                {
                    "id": "S001",
                    "priority": "P0",
                    "claim_role": "fact",
                    "claim_origin": "source_explicit",
                }
            ]
        }

        codes = {
            item["code"]
            for item in semantic_evidence_cross_issues(
                semantic,
                truth,
                source_unit_ids=unit_ids,
            )
        }

        self.assertIn("SOURCE_TRUTH_P0_SEMANTIC_MAPPING_MISSING", codes)
        self.assertIn("SOURCE_TRUTH_P0_SOURCE_UNIT_MISSING", codes)

    def test_editorial_hypothesis_cannot_become_p0_fact(self) -> None:
        semantic, unit_ids, _headings = strict_model()
        evidence_unit = next(iter(unit_ids))
        truth = {
            "records": [
                {
                    "id": "S001",
                    "priority": "P0",
                    "claim_role": "fact",
                    "claim_origin": "editorial_hypothesis",
                    "source_unit_refs": [evidence_unit],
                    "semantic_node_ids": ["c01"],
                }
            ]
        }

        codes = {
            item["code"]
            for item in semantic_evidence_cross_issues(
                semantic,
                truth,
                source_unit_ids=unit_ids,
            )
        }

        self.assertIn("SOURCE_TRUTH_EDITORIAL_HYPOTHESIS_PROMOTED", codes)


if __name__ == "__main__":
    unittest.main()
