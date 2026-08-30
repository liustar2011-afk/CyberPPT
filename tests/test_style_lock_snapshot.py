from __future__ import annotations

import json
from pathlib import Path

from scripts.imagegen_pipeline import style_library


def _write_preset(path: Path, contract: str) -> None:
    path.write_text(
        json.dumps(
            {
                "default_style_id": 9,
                "source_reference": "visual-system.md",
                "styles": [
                    {
                        "id": 9,
                        "slug": "test",
                        "name": "test",
                        "scenario": "test",
                        "extension_only": True,
                        "prompt_contract": contract,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_style09_lock_is_an_immutable_registry_snapshot(tmp_path: Path) -> None:
    preset = tmp_path / "styles.json"
    _write_preset(preset, "测试合同 A")

    lock = style_library.write_project_style_lock(
        project=tmp_path / "project",
        style_id=9,
        path=preset,
    )
    first = style_library.load_style_lock(lock)
    first_contract = first["style"]["prompt_contract"]
    first_hash = first["resolved_contract"]["sha256"]

    _write_preset(preset, "测试合同 B")
    second = style_library.load_style_lock(lock)

    assert first_contract == "测试合同 A"
    assert second["style"]["prompt_contract"] == "测试合同 A"
    assert second["resolved_contract"]["sha256"] == first_hash
    assert second["resolved_contract"]["source"] == str(preset)
    assert second["policy"]["resolved_contract_is_immutable"] is True
    assert second["policy"]["executable_style_authority"] == "style_registry_snapshot"


def test_new_style09_lock_picks_up_new_registry_revision(tmp_path: Path) -> None:
    preset = tmp_path / "styles.json"
    _write_preset(preset, "版本 A")
    lock_a = style_library.write_project_style_lock(
        project=tmp_path / "a",
        style_id=9,
        path=preset,
    )
    payload_a = style_library.load_style_lock(lock_a)

    _write_preset(preset, "版本 B")
    lock_b = style_library.write_project_style_lock(
        project=tmp_path / "b",
        style_id=9,
        path=preset,
    )
    payload_b = style_library.load_style_lock(lock_b)

    assert payload_a["style"]["prompt_contract"] == "版本 A"
    assert payload_b["style"]["prompt_contract"] == "版本 B"
    assert payload_a["resolved_contract"]["sha256"] != payload_b["resolved_contract"]["sha256"]


def test_documentation_revision_does_not_change_registry_lock(tmp_path: Path, monkeypatch) -> None:
    preset = tmp_path / "styles.json"
    _write_preset(preset, "registry contract")
    documentation = tmp_path / "visual-system.md"
    documentation.write_text("## 扩展风格9：测试\n\ndoc A\n", encoding="utf-8")
    monkeypatch.setattr(style_library, "VISUAL_SYSTEM_PATH", documentation)

    lock_a = style_library.write_project_style_lock(
        project=tmp_path / "a",
        style_id=9,
        path=preset,
    )
    documentation.write_text("## 扩展风格9：测试\n\ndoc B\n", encoding="utf-8")
    lock_b = style_library.write_project_style_lock(
        project=tmp_path / "b",
        style_id=9,
        path=preset,
    )

    payload_a = style_library.load_style_lock(lock_a)
    payload_b = style_library.load_style_lock(lock_b)
    assert payload_a["resolved_contract"]["sha256"] == payload_b["resolved_contract"]["sha256"]
    assert payload_a["style"]["prompt_contract"] == "registry contract"
    assert payload_b["style"]["prompt_contract"] == "registry contract"


def test_legacy_style09_lock_migrates_once_then_freezes(tmp_path: Path, monkeypatch) -> None:
    revisions = iter(("迁移合同 A", "迁移合同 B"))

    def fake_resolve_default_style(*, style_id=None, style_name=None, path=style_library.STYLE_LIBRARY_PATH):
        contract = next(revisions)
        return {
            "id": 9,
            "slug": "test",
            "name": "test",
            "scenario": "test",
            "extension_only": True,
            "prompt_contract": contract,
            "prompt_contract_source": str(path),
        }

    monkeypatch.setattr(style_library, "resolve_default_style", fake_resolve_default_style)
    lock = tmp_path / "legacy.json"
    lock.write_text(
        json.dumps(
            {
                "schema": "cyberppt.visual_style_lock.v1",
                "style": {"id": 9, "prompt_contract": "stale"},
            }
        ),
        encoding="utf-8",
    )

    migrated = style_library.load_style_lock(lock)
    assert migrated["style"]["prompt_contract"] == "迁移合同 A"
    assert migrated["migration"]["from"] == "legacy_live_refresh"
    assert migrated["migration"]["to"] == "style_registry_snapshot"

    again = style_library.load_style_lock(lock)
    assert again["style"]["prompt_contract"] == "迁移合同 A"
