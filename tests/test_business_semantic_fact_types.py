from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "business-semantic-understanding"
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))

from business_semantic_understanding.validate import (
    FACT_TYPES,
    _validate_argument,
    _validate_normalized,
    _validate_semantic_issues,
    _validate_source_coverage,
)


class MetadataFactTypeTests(unittest.TestCase):
    def test_metadata_is_a_supported_normalized_fact_type(self) -> None:
        self.assertIn("metadata", FACT_TYPES)

    def _fact(self, fact_type: str) -> dict[str, object]:
        return {
            "normalized_fact_id": "NF-0001",
            "statement": "依托电力领域数据基础设施开展",
            "fact_type": fact_type,
            "normalization": "verbatim",
            "verification_status": "unverified",
            "confidence": "high",
            "source_assertion_ids": ["fact-0001"],
        }

    def test_preamble_fact_normalized_as_metadata_passes_validation(self) -> None:
        errors: list[dict[str, object]] = []
        warnings: list[dict[str, object]] = []
        _validate_normalized(
            {"facts": [self._fact("metadata")]},
            {"fact-0001": {}},
            errors,
            warnings,
        )
        self.assertEqual(
            [],
            [item for item in errors if item["code"] == "invalid_fact_type"],
        )

    def test_unsupported_fact_type_still_rejected(self) -> None:
        errors: list[dict[str, object]] = []
        warnings: list[dict[str, object]] = []
        _validate_normalized(
            {"facts": [self._fact("front_matter")]},
            {"fact-0001": {}},
            errors,
            warnings,
        )
        self.assertIn(
            "invalid_fact_type",
            {item["code"] for item in errors},
        )

    def test_table_parent_and_composite_statement_emit_atomicity_diagnostics(self) -> None:
        fact = self._fact("metric")
        fact["statement"] = "| 市场 | 0.5亿元 |；完成试点；研究投入"
        errors: list[dict[str, object]] = []
        warnings: list[dict[str, object]] = []
        _validate_normalized(
            {"facts": [fact]},
            {
                "fact-0001": {"fact_type": "table_record"},
                "fact-0001-c02-s01": {"parent_fact_id": "fact-0001"},
            },
            errors,
            warnings,
        )
        codes = {item["code"] for item in warnings}
        self.assertIn("normalized_fact_table_row_residue", codes)
        self.assertIn("normalized_fact_composite_statement", codes)
        self.assertIn("normalized_fact_uses_table_parent", codes)

    def test_argument_diagnostic_requires_resolution(self) -> None:
        errors: list[dict[str, object]] = []
        _validate_argument(
            {
                "diagnostic_resolution_mode": "required",
                "source_chain": [],
                "reconstructed_chain": [],
                "diagnostics": [{
                    "diagnostic_id": "D-001",
                    "type": "mixed_level",
                    "normalized_fact_ids": [],
                    "section_ids": [],
                }],
            },
            set(),
            set(),
            errors,
            [],
        )
        self.assertIn("diagnostic_resolution_missing", {item["code"] for item in errors})

    def test_missing_atomic_source_assertion_is_rejected(self) -> None:
        errors: list[dict[str, object]] = []
        counts = _validate_source_coverage(
            {"facts": [self._fact("metadata")]},
            {"fact-0001": {}, "fact-0002": {}},
            set(),
            errors,
        )
        self.assertEqual(1, counts["unrepresented_source_assertions"])
        self.assertIn("unrepresented_source_assertion", {item["code"] for item in errors})

    def test_atomic_table_children_replace_trace_parent_for_coverage(self) -> None:
        errors: list[dict[str, object]] = []
        fact = self._fact("metric")
        fact["source_assertion_ids"] = ["fact-0001-c02-s01"]
        counts = _validate_source_coverage(
            {"facts": [fact]},
            {
                "fact-0001": {"fact_type": "table_record"},
                "fact-0001-c02-s01": {"parent_fact_id": "fact-0001"},
            },
            set(),
            errors,
        )
        self.assertEqual(0, counts["unrepresented_source_assertions"])
        self.assertEqual([], errors)

    def test_documented_exclusion_covers_source_assertion(self) -> None:
        errors: list[dict[str, object]] = []
        warnings: list[dict[str, object]] = []
        payload = {
            "facts": [],
            "exclusions": [{
                "exclusion_id": "EX-001",
                "statement": "附件登记字段不参与当前语义论证。",
                "reason": "仅用于材料追溯。",
                "source_assertion_ids": ["fact-0001"],
            }],
        }
        issue_source_ids = _validate_semantic_issues(payload, set(), {"fact-0001": {}}, errors, warnings)
        counts = _validate_source_coverage(payload, {"fact-0001": {}}, issue_source_ids, errors)
        self.assertEqual(0, counts["unrepresented_source_assertions"])
        self.assertEqual([], errors)

    def test_issue_structure_and_references_are_validated(self) -> None:
        errors: list[dict[str, object]] = []
        _validate_semantic_issues(
            {
                "ambiguities": [{
                    "ambiguity_id": "AMB-001",
                    "statement": "测算口径待确认。",
                    "normalized_fact_ids": ["NF-UNKNOWN"],
                    "source_assertion_ids": ["fact-unknown"],
                }],
            },
            {"NF-0001"},
            {"fact-0001": {}},
            errors,
            [],
        )
        codes = {item["code"] for item in errors}
        self.assertIn("missing_issue_resolution", codes)
        self.assertIn("unknown_normalized_fact", codes)
        self.assertIn("unknown_source_assertion", codes)

    def test_source_assertion_cannot_bind_to_multiple_normalized_facts(self) -> None:
        errors: list[dict[str, object]] = []
        second = dict(self._fact("metadata"))
        second["normalized_fact_id"] = "NF-0002"
        _validate_source_coverage(
            {"facts": [self._fact("metadata"), second]},
            {"fact-0001": {}},
            set(),
            errors,
        )
        self.assertIn("duplicate_source_assertion_binding", {item["code"] for item in errors})

    def test_repeated_first_column_label_requires_documented_exclusion(self) -> None:
        label = self._fact("other")
        label["statement"] = "近期策略"
        label["source_assertion_ids"] = ["fact-row-c01-s01"]
        errors: list[dict[str, object]] = []
        _validate_normalized(
            {"facts": [label]},
            {
                "fact-row-c01-s01": {
                    "text": "近期策略",
                    "parent_fact_id": "fact-row",
                    "table_cell": {
                        "row_index": 1,
                        "cell_index": 1,
                        "row_label": "近期策略",
                        "source_text": "近期策略",
                    },
                },
                "fact-row-c02-s01": {
                    "text": "近期策略：先形成1门标准课程",
                    "parent_fact_id": "fact-row",
                    "table_cell": {
                        "row_index": 1,
                        "cell_index": 2,
                        "row_label": "近期策略",
                        "source_text": "先形成1门标准课程",
                    },
                },
            },
            errors,
            [],
        )

        self.assertIn(
            "normalized_fact_redundant_table_row_label",
            {item["code"] for item in errors},
        )

    def test_first_column_business_fact_without_sibling_prefix_is_retained(self) -> None:
        label = self._fact("deliverable")
        label["statement"] = "课程A"
        label["source_assertion_ids"] = ["fact-row-c01-s01"]
        errors: list[dict[str, object]] = []
        _validate_normalized(
            {"facts": [label]},
            {
                "fact-row-c01-s01": {
                    "text": "课程A",
                    "parent_fact_id": "fact-row",
                    "table_cell": {
                        "row_index": 1,
                        "cell_index": 1,
                        "row_label": "课程A",
                        "source_text": "课程A",
                    },
                },
            },
            errors,
            [],
        )

        self.assertNotIn(
            "normalized_fact_redundant_table_row_label",
            {item["code"] for item in errors},
        )


if __name__ == "__main__":
    unittest.main()
