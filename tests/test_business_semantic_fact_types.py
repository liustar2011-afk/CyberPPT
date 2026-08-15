from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "business-semantic-understanding"
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))

from business_semantic_understanding.validate import FACT_TYPES, _validate_normalized


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


if __name__ == "__main__":
    unittest.main()
