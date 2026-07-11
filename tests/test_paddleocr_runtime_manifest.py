import json
from pathlib import Path


MANIFEST = Path(__file__).parents[1] / "tools" / "paddleocr_runtime" / "runtime_manifest.json"


def test_runtime_manifest_has_pinned_versions_and_model_hashes():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["python_version"] == "3.12"
    assert data["paddleocr_version"]
    assert data["paddle_version"]
    assert data["models"]
    assert all(item["sha256"] for item in data["models"])
