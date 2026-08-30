from __future__ import annotations

import json
from pathlib import Path

from scripts.imagegen_pipeline import style_library


def _write_live_source(path: Path, contract: str) -> None:
    path.write_text(f"## 扩展风格9：测试\n\n{contract}\n", encoding="utf-8")


def _write_preset(path: Path) -> None:
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
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_style09_lock_is_an_immutable_contract_snapshot(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "visual-system.md"
    _write_live_source(source, "测试合同 A")
    monkeypatch.setattr(style_library, "VISUAL_SYSTEM_PATH", source)
    preset = tmp_path / "styles.json"
    _write_preset(preset)

    project = tmp_path / "project"
    lock = style_library.write_project_style_lock(project=project, style_id=9, path=preset)
    first = style_library.load_style_lock(lock)
    first_contract = first["style"]["prompt_contract"]
    first_hash = first["resolved_contract"]["sha256"]

    _write_live_source(source, "测试合同 B")
    second = style_library.load_style_lock(lock)

    assert second["style"]["prompt_contract"] == first_contract
    assert second["resolved_contract"]["sha256"] == first_hash
    assert second["policy"]["resolved_contract_is_immutable"] is True


def test_new_style09_lock_picks_up_new_contract_revision(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "visual-system.md"
    _write_live_source(source, "版本 A")
    monkeypatch.setattr(style_library, "VISUAL_SYSTEM_PATH", source)
    preset = tmp_path / "styles.json"
    _write_preset(preset)

    lock_a = style_library.write_project_style_lock(project=tmp_path / "a", style_id=9, path=preset)
    hash_a = style_library.load_style_lock(lock_a)["resolved_contract"]["sha256"]

    _write_live_source(source, "版本 B")
    lock_b = style_library.write_project_style_lock(project=tmp_path / "b", style_id=9, path=preset)
    hash_b = style_library.load_style_lock(lock_b)["resolved_contract"]["sha256"]

    assert hash_a != hash_b


def test_legacy_style09_lock_migrates_once_then_freezes(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "visual-system.md"
    _write_live_source(source, "迁移合同 A")
    monkeypatch.setattr(style_library, "VISUAL_SYSTEM_PATH", source)
    lock = tmp_path / "legacy.json"
    lock.write_text(
        json.dumps({"schema": "cyberppt.visual_style_lock.v1", "style": {"id": 9, "prompt_contract": "stale"}}),
        encoding="utf-8",
    )

    migrated = style_library.load_style_lock(lock)
    assert migrated["style"]["prompt_contract"] == "迁移合同 A"
    assert migrated["migration"]["from"] == "legacy_live_refresh"

    _write_live_source(source, "迁移合同 B")
    again = style_library.load_style_lock(lock)
    assert again["style"]["prompt_contract"] == "迁移合同 A"
