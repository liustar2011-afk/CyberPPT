"""Contract checks for reviewable OCR forensic golden fixtures.

Fixtures may be synthetic while the approved GPT page-image set is being
curated.  Synthetic records are still required to carry the same audit shape
as a production fixture and must never contain credentials or service URLs.
"""

import json
from pathlib import Path


GOLDEN_DIR = Path(__file__).parent / "fixtures" / "ocr_golden"


def test_golden_forensics_has_required_audit_fields():
    paths = sorted(GOLDEN_DIR.glob("*.json"))
    assert paths, "at least one golden fixture contract is required"
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"]
        assert data.get("fixture_id")
        assert data.get("fixture_status") in {"approved", "synthetic"}
        assert isinstance(data.get("lines"), list) and data["lines"]
        for line in data["lines"]:
            assert "observed_text" in line and "final_text" in line
            assert "correction" in line
            assert isinstance(line["correction"], dict)
            assert "reversible" in line["correction"]


def test_golden_fixture_contract_has_no_external_credentials_or_services():
    for path in GOLDEN_DIR.glob("*.json"):
        raw = path.read_text(encoding="utf-8").lower()
        assert "api_key" not in raw
        assert "authorization" not in raw
        assert "http://" not in raw
        assert "https://" not in raw
