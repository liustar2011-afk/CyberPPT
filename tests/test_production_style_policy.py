from __future__ import annotations

import json
from pathlib import Path

from scripts.imagegen_pipeline.style_library import PRODUCTION_STYLE_ID, write_project_style_lock


def test_production_style_id_is_explicit() -> None:
    assert PRODUCTION_STYLE_ID == 9


def test_style09_lock_does_not_require_separate_user_style_confirmation(tmp_path: Path) -> None:
    lock = write_project_style_lock(project=tmp_path, style_id=PRODUCTION_STYLE_ID)
    payload = json.loads(lock.read_text(encoding="utf-8"))

    assert payload["policy"]["production_style"] is True
    assert payload["policy"]["production_style_id"] == 9
    assert payload["policy"]["samples_are_required_for_user_confirmation"] is False
    assert payload["policy"]["runtime_contract_refresh_forbidden"] is True


def test_policy_document_distinguishes_reference_catalogue_from_production() -> None:
    text = (
        Path(__file__).resolve().parents[1] / "docs" / "PRODUCTION_STYLE_POLICY.md"
    ).read_text(encoding="utf-8")

    assert "当前唯一正式生产视觉风格为 `Style 09`" in text
    assert "它们不构成当前 Stage 02 正式生产路由" in text
