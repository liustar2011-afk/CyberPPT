from __future__ import annotations

import json
from pathlib import Path

from scripts.imagegen_pipeline import style_library


def test_style09_lock_is_an_immutable_contract_snapshot(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "visual-system.md"
    source.write_text("## 扩展风格9：测试合同 A\n", encoding="utf-8")
    monkeypatch.setattr(style_library, "VISUAL_SYSTEM_PATH", source)

    preset = tmp_path / "styles.json"
    preset.write_text(
        json.dumps(
            {
                "default_style_id": 9,
                "source_reference": str(source),
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

    project = tmp_path / "project"
    lock = style_library.write_project_style_lock(project=project, style_id=9, path=preset)
    first = style_library.load_style_lock(lock)
    first_contract = first["style"]["prompt_contract"]
    first_hash = first["resolved_contract"]["sha256"]

    source.write_text("## 扩展风格9：测试合同 B\n", encoding="utf-8")
    second = style_library.load_style_lock(lock)

    assert second["style"]["prompt_contract"] == first_contract
    assert second["resolved_contract"]["sha256"] == first_hash
    assert second["policy"]["resolved_contract_is_immutable"] is True


def test_new_style09_lock_picks_up_new_contract_revision(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "visual-system.md"
    source.write_text("## 扩展风格9：版本 A\n", encoding="utf-8")
    monkeypatch.setattr(style_library, "VISUAL_SYSTEM_PATH", source)
    preset = tmp_path / "styles.json"
    preset.write_text(
        json.dumps(
            {
                "default_style_id": 9,
                "source_reference": str(source),
                "styles": [{"id": 9, "slug": "test", "name": "test", "scenario": "test", "extension_only": True}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lock_a = style_library.write_project_style_lock(project=tmp_path / "a", style_id=9, path=preset)
    hash_a = style_library.load_style_lock(lock_a)["resolved_contract"]["sha256"]

    source.write_text("## 扩展风格9：版本 B\n", encoding="utf-8")
    lock_b = style_library.write_project_style_lock(project=tmp_path / "b", style_id=9, path=preset)
    hash_b = style_library.load_style_lock(lock_b)["resolved_contract"]["sha256"]

    assert hash_a != hash_b
