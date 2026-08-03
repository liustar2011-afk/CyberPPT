from __future__ import annotations

import unittest

from cyberppt.semantic_cross_audit import semantic_evidence_cross_issues
from test_source_argument_model import model, strict_model


class SemanticEvidenceCrossAuditTests(unittest.TestCase):
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
