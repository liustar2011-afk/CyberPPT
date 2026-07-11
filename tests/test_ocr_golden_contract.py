"""Contract checks for reviewable OCR forensic golden fixtures.

Fixtures may be synthetic while the approved GPT page-image set is being
curated.  Synthetic records are still required to carry the same audit shape
as a production fixture and must never contain credentials or service URLs.
"""

import json
import re
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
        image = data["image"]
        assert isinstance(image, dict)
        assert image.get("source")
        assert isinstance(image.get("width"), int) and image["width"] > 0
        assert isinstance(image.get("height"), int) and image["height"] > 0
        model = data["model"]
        assert model.get("backend") == "paddleocr-local"
        assert model.get("runtime") == "offline"
        assert model.get("model_manifest_sha256")
        assert isinstance(data.get("lines"), list) and data["lines"]
        for line in data["lines"]:
            assert "observed_text" in line and "final_text" in line
            bbox = line.get("bbox")
            assert isinstance(bbox, list) and len(bbox) == 4
            assert bbox[2] > bbox[0] and bbox[3] > bbox[1]
            polygon = line.get("polygon")
            assert isinstance(polygon, list) and len(polygon) >= 4
            assert all(isinstance(point, list) and len(point) >= 2 for point in polygon)
            assert "correction" in line
            assert isinstance(line["correction"], dict)
            audit = line["correction"]
            assert {"applied", "changes", "reason", "confidence", "reversible"} <= audit.keys()
            assert audit["reversible"] is True

        if data["fixture_status"] == "synthetic":
            assert data["approved_image"] is False
            assert image.get("path") is None
            assert data["artifacts"].get("render_check") == "not_run_synthetic_fixture"
        else:
            assert data["approved_image"] is True
            assert image.get("path")
            assert re.fullmatch(r"[0-9a-f]{64}", str(image.get("sha256", "")))
            assert image.get("provenance")


def test_golden_fixture_contract_has_no_external_credentials_or_services():
    for path in GOLDEN_DIR.glob("*.json"):
        raw = path.read_text(encoding="utf-8").lower()
        assert "api_key" not in raw
        assert "authorization" not in raw
        assert "http://" not in raw
        assert "https://" not in raw
