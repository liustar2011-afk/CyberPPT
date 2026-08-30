from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.imagegen_pipeline import style_library


def _contract_sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest().upper()


def test_load_style09_lock_uses_frozen_snapshot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    frozen = "frozen Style 09 contract"
    lock = tmp_path / "visual_style_lock.json"
    lock.write_text(
        json.dumps(
            {
                "schema": "cyberppt.visual_style_lock.v1",
                "style": {
                    "id": 9,
                    "prompt_contract": frozen,
                    "prompt_contract_sha256": _contract_sha(frozen),
                },
                "resolution": {
                    "mode": "frozen_snapshot",
                    "resolved_contract_sha256": _contract_sha(frozen),
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    changed_source = tmp_path / "visual-system.md"
    changed_source.write_text("## 扩展风格9：\nnew runtime text\n", encoding="utf-8")
    monkeypatch.setattr(style_library, "VISUAL_SYSTEM_PATH", changed_source)

    payload = style_library.load_style_lock(lock)

    assert payload["style"]["prompt_contract"] == frozen
    assert payload["style"]["prompt_contract_sha256"] == _contract_sha(frozen)


def test_load_style09_lock_rejects_legacy_live_lock(tmp_path: Path) -> None:
    lock = tmp_path / "legacy_style_lock.json"
    lock.write_text(
        json.dumps(
            {
                "schema": "cyberppt.visual_style_lock.v1",
                "style": {"id": 9},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="legacy live lock"):
        style_library.load_style_lock(lock)


def test_load_style09_lock_rejects_tampered_snapshot(tmp_path: Path) -> None:
    lock = tmp_path / "tampered_style_lock.json"
    lock.write_text(
        json.dumps(
            {
                "schema": "cyberppt.visual_style_lock.v1",
                "style": {
                    "id": 9,
                    "prompt_contract": "changed",
                    "prompt_contract_sha256": _contract_sha("original"),
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="frozen contract hash mismatch"):
        style_library.load_style_lock(lock)


def test_write_project_style_lock_snapshots_live_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    visual_system = tmp_path / "visual-system.md"
    visual_system.write_text(
        "## 扩展风格9：纯白深蓝\n\nFrozen rule A.\nFrozen rule B.\n\n## 其他\nignored\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(style_library, "VISUAL_SYSTEM_PATH", visual_system)

    style_registry = tmp_path / "registry" / "a" / "b" / "cyberppt_default_styles.json"
    style_registry.parent.mkdir(parents=True)
    style_registry.write_text(
        json.dumps(
            {
                "default_style_id": 9,
                "source_reference": "visual-system.md",
                "styles": [
                    {
                        "id": 9,
                        "slug": "style09",
                        "name": "Style 09",
                        "scenario": "test",
                        "extension_only": True,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    project = tmp_path / "project"
    lock_path = style_library.write_project_style_lock(
        project=project,
        style_id=9,
        path=style_registry,
    )
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    contract = payload["style"]["prompt_contract"]

    assert payload["resolution"]["mode"] == "frozen_snapshot"
    assert payload["resolution"]["resolved_contract_sha256"] == _contract_sha(contract)
    assert payload["policy"]["runtime_contract_refresh_forbidden"] is True
