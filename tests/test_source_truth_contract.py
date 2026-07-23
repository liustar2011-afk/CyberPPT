from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberppt.source_truth_contract import (
    audit_source_truth,
    load_source_truth,
    source_truth_retry_directive,
)


def valid_payload() -> dict[str, object]:
    return {
        "schema": "cyberppt.source_truth.v1",
        "argument_contract_mode": "strict",
        "project": {"title": "测试项目", "material_type": "前期研究方案", "audience": "内部讨论"},
        "sources": [
            {
                "id": "DOC01",
                "file": "source.docx",
                "role": "primary",
                "non_empty_paragraphs": 10,
                "headings": 2,
                "tables": 0,
            }
        ],
        "coverage_targets": [
            {
                "id": "T001",
                "kind": "section",
                "label": "第一章",
                "priority": "P0",
                "required": True,
                "record_refs": ["S001"],
            }
        ],
        "records": [
            {
                "id": "S001",
                "type": "F",
                "priority": "P0",
                "statement": "现有系统已形成月度统计基础。",
                "source_locator": {
                    "source_id": "DOC01",
                    "file": "source.docx",
                    "section": "第一章",
                    "paragraph": 3,
                },
                "status": "现状",
                "claim_role": "fact",
                "semantic_units": [
                    {"text": "已形成月度统计基础。", "claim_role": "fact"}
                ],
                "allowed_page_roles": ["foundation", "necessity"],
                "forbidden_page_roles": ["solution"],
                "depends_on": [],
                "conditions": ["仅说明统计基础"],
                "supports": ["C001"],
                "page_refs": ["p04"],
                "quote": "已形成月度统计基础",
                "fingerprint": "sha256:test",
            }
        ],
        "conclusions": [
            {
                "id": "C001",
                "statement": "具备开展首期研究的基础。",
                "source_refs": ["S001"],
            }
        ],
        "pages": [{"id": "p04", "source_refs": ["S001"]}],
        "retry": {"attempt": 1, "max_attempts": 3, "strategy": "section_sweep"},
    }


class SourceTruthContractTests(unittest.TestCase):
    def _write(self, payload: dict[str, object]) -> Path:
        root = Path(tempfile.mkdtemp())
        path = root / "source-truth.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_loads_valid_contract(self) -> None:
        payload = load_source_truth(self._write(valid_payload()))
        self.assertEqual("cyberppt.source_truth.v1", payload["schema"])

    def test_rejects_unknown_schema(self) -> None:
        payload = valid_payload()
        payload["schema"] = "wrong"
        with self.assertRaisesRegex(ValueError, "cyberppt.source_truth.v1"):
            load_source_truth(self._write(payload))

    def test_flags_composite_record_and_imprecise_locator(self) -> None:
        payload = valid_payload()
        record = payload["records"][0]
        record["type"] = ["F", "R"]
        record["source_locator"] = {"source_id": "DOC01", "file": "source.docx", "section": "第一章"}
        codes = {item.code for item in audit_source_truth(payload)}
        self.assertIn("SOURCE_RECORD_COMPOSITE", codes)
        self.assertIn("SOURCE_LOCATOR_IMPRECISE", codes)

    def test_flags_missing_quote(self) -> None:
        payload = valid_payload()
        payload["records"][0]["quote"] = ""
        codes = {item.code for item in audit_source_truth(payload)}
        self.assertIn("SOURCE_QUOTE_MISSING", codes)

    def test_flags_numeric_table_boundary_priority_and_traceability_gaps(self) -> None:
        payload = valid_payload()
        payload["coverage_targets"] = [
            {
                "id": "T1",
                "kind": "table",
                "label": "附件表1",
                "priority": "P0",
                "required": True,
                "record_refs": [],
            },
            {
                "id": "T2",
                "kind": "boundary",
                "label": "待确认事项",
                "priority": "P1",
                "required": True,
                "record_refs": [],
            },
        ]
        record = payload["records"][0]
        record["numeric"] = {"raw_value": "100"}
        record["supports"] = ["C404"]
        record["page_refs"] = ["p404"]
        codes = {item.code for item in audit_source_truth(payload)}
        expected = {
            "SOURCE_NUMERIC_FIELDS_MISSING",
            "SOURCE_TABLE_COVERAGE_MISSING",
            "SOURCE_BOUNDARY_COVERAGE_MISSING",
            "SOURCE_PRIORITY_COVERAGE_MISSING",
            "SOURCE_TRACEABILITY_BROKEN",
        }
        self.assertTrue(expected.issubset(codes), expected - codes)

    def test_flags_type_status_conflict(self) -> None:
        payload = valid_payload()
        payload["records"][0]["type"] = "F"
        payload["records"][0]["status"] = "待核"
        codes = {item.code for item in audit_source_truth(payload)}
        self.assertIn("SOURCE_TYPE_STATUS_CONFLICT", codes)

    def test_unknown_record_accepts_pending_inventory_status(self) -> None:
        payload = valid_payload()
        payload["records"][0]["type"] = "U"
        payload["records"][0]["status"] = "待摸底"
        codes = {item.code for item in audit_source_truth(payload)}
        self.assertNotIn("SOURCE_TYPE_STATUS_CONFLICT", codes)

    def test_flags_mixed_semantic_claims(self) -> None:
        payload = valid_payload()
        payload["records"][0]["semantic_units"] = [
            {"text": "已经形成统计基础。", "claim_role": "fact"},
            {"text": "首期建议从全国总盘入手。", "claim_role": "recommendation"},
        ]
        codes = {item.code for item in audit_source_truth(payload)}
        self.assertIn("SOURCE_RECORD_MIXED_CLAIMS", codes)

    def test_fact_record_cannot_carry_recommendation_unit(self) -> None:
        payload = valid_payload()
        payload["records"][0]["semantic_units"] = [
            {"text": "首期建议从全国总盘入手。", "claim_role": "recommendation"}
        ]
        codes = {item.code for item in audit_source_truth(payload)}
        self.assertIn("SOURCE_FACT_CONTAINS_RECOMMENDATION", codes)

    def test_recommendation_requires_resolvable_dependency(self) -> None:
        payload = valid_payload()
        record = payload["records"][0]
        record["type"] = "R"
        record["claim_role"] = "recommendation"
        record["semantic_units"] = [
            {"text": "建议从全国总盘入手。", "claim_role": "recommendation"}
        ]
        record["depends_on"] = ["S404"]
        codes = {item.code for item in audit_source_truth(payload)}
        self.assertIn("SOURCE_DEPENDENCY_MISSING", codes)

    def test_valid_contract_has_no_issues(self) -> None:
        self.assertEqual([], audit_source_truth(valid_payload()))

    def test_retry_changes_direction_for_repeated_strategy(self) -> None:
        payload = valid_payload()
        payload["records"][0]["quote"] = ""
        issues = audit_source_truth(payload)
        directive = source_truth_retry_directive(issues, "section_sweep")
        self.assertTrue(directive["required"])
        self.assertEqual("structured_fact_sweep", directive["strategy"])


if __name__ == "__main__":
    unittest.main()
