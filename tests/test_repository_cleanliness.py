from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_generated_metadata_and_root_scratch_are_ignored() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "*.egg-info/" in text
    assert "/out.txt" in text
    assert "/tmp_*" in text
    assert ".pytest_cache/" in text
    assert "*.whl" in text
