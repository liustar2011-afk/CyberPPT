from pathlib import Path


# Clarify production comments/docstrings to match the live-contract behavior already implemented.
p = Path("scripts/imagegen_pipeline/style_library.py")
text = p.read_text(encoding="utf-8")
old = '''    # Resolve the executable registry exactly once when the lock is created.\n    # Production consumers then use the stored snapshot verbatim.\n'''
new = '''    # Store the resolved contract for traceability when the lock is created.\n    # Live styles remain refreshable unless the lock policy is explicitly immutable.\n'''
if text.count(old) != 1:
    raise SystemExit("write_project_style_lock comment block not found uniquely")
text = text.replace(old, new, 1)
old = '    """Load a style lock and refresh its editable extension contract."""\n'
new = '    """Load a style lock; refresh live styles unless explicitly immutable."""\n'
if text.count(old) != 1:
    raise SystemExit("load_style_lock docstring not found uniquely")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8", newline="\n")


test = r'''from __future__ import annotations

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


def _set_live_source(monkeypatch, path: Path, contract: str) -> Path:
    live = path / "visual-system.md"
    live.write_text(contract, encoding="utf-8")
    monkeypatch.setitem(style_library.VISUAL_SYSTEM_PATHS, 9, live)
    return live


def test_style09_lock_refreshes_with_live_contract_by_default(tmp_path: Path, monkeypatch) -> None:
    preset = tmp_path / "styles.json"
    _write_preset(preset, "registry placeholder")
    live = _set_live_source(monkeypatch, tmp_path, "live contract A")

    lock = style_library.write_project_style_lock(
        project=tmp_path / "project",
        style_id=9,
        path=preset,
    )
    first = style_library.load_style_lock(lock)
    first_hash = first["resolved_contract"]["sha256"]

    assert first["style"]["prompt_contract"] == "live contract A"
    assert first["policy"]["resolved_contract_is_immutable"] is False
    assert first["policy"]["executable_style_authority"] == str(live)

    live.write_text("live contract B", encoding="utf-8")
    second = style_library.load_style_lock(lock)

    assert second["style"]["prompt_contract"] == "live contract B"
    assert second["resolved_contract"]["sha256"] != first_hash
    assert second["resolved_contract"]["source"] == str(live)
    assert second["policy"]["resolved_contract_is_immutable"] is False


def test_new_style09_lock_picks_up_current_live_revision(tmp_path: Path, monkeypatch) -> None:
    preset = tmp_path / "styles.json"
    _write_preset(preset, "registry placeholder")
    live = _set_live_source(monkeypatch, tmp_path, "版本 A")

    lock_a = style_library.write_project_style_lock(
        project=tmp_path / "a",
        style_id=9,
        path=preset,
    )
    payload_a = style_library.load_style_lock(lock_a)

    live.write_text("版本 B", encoding="utf-8")
    lock_b = style_library.write_project_style_lock(
        project=tmp_path / "b",
        style_id=9,
        path=preset,
    )
    payload_b = style_library.load_style_lock(lock_b)

    assert payload_a["style"]["prompt_contract"] == "版本 A"
    assert payload_b["style"]["prompt_contract"] == "版本 B"
    assert payload_a["resolved_contract"]["sha256"] != payload_b["resolved_contract"]["sha256"]


def test_explicit_immutable_style09_lock_does_not_refresh(tmp_path: Path, monkeypatch) -> None:
    preset = tmp_path / "styles.json"
    _write_preset(preset, "registry placeholder")
    live = _set_live_source(monkeypatch, tmp_path, "frozen A")

    lock = style_library.write_project_style_lock(
        project=tmp_path / "project",
        style_id=9,
        path=preset,
    )
    payload = json.loads(lock.read_text(encoding="utf-8"))
    frozen_hash = payload["resolved_contract"]["sha256"]
    payload["policy"]["resolved_contract_is_immutable"] = True
    payload["policy"]["executable_style_authority"] = "style_registry_snapshot"
    lock.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    live.write_text("live B", encoding="utf-8")
    loaded = style_library.load_style_lock(lock)

    assert loaded["style"]["prompt_contract"] == "frozen A"
    assert loaded["resolved_contract"]["sha256"] == frozen_hash
    assert loaded["policy"]["resolved_contract_is_immutable"] is True
    assert loaded["policy"]["executable_style_authority"] == "style_registry_snapshot"


def test_legacy_style09_lock_continues_to_follow_live_contract(tmp_path: Path, monkeypatch) -> None:
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

    first = style_library.load_style_lock(lock)
    assert first["style"]["prompt_contract"] == "迁移合同 A"
    assert first.get("policy") is None
    assert "migration" not in first

    again = style_library.load_style_lock(lock)
    assert again["style"]["prompt_contract"] == "迁移合同 B"
    assert "migration" not in again
'''
Path("tests/test_style_lock_snapshot.py").write_text(test, encoding="utf-8", newline="\n")

print("Track A3 snapshot patch applied")
