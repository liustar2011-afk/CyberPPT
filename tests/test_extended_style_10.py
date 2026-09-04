from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.imagegen_pipeline.style_library import (
    default_style_choices,
    load_style_library,
    resolve_default_style,
    write_project_style_lock,
)


ROOT = Path(__file__).resolve().parents[1]


def test_style_ten_is_a_separate_executable_registry_entry() -> None:
    library = load_style_library()
    assert [style["id"] for style in library["styles"]] == list(range(1, 11))
    assert library["default_style_id"] == 9


def test_style_ten_resolves_to_its_copied_live_contract() -> None:
    style10 = resolve_default_style(style_id=10)

    assert style10["id"] == 10
    assert style10["prompt_contract_source"].endswith("references/visual-system-10.md")
    assert "Prefer a scene-supported executive-report language." in style10["prompt_contract"]
    assert "Keep all locked Chinese text complete." not in style10["prompt_contract"]


def test_style_ten_lock_records_its_own_snapshot() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=10)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    assert payload["selection"] == {
        "requested_style_id": 10,
        "requested_style_name": None,
        "canonical_style_id": 10,
        "legacy_alias": False,
    }
    assert payload["style"]["id"] == 10
    assert payload["policy"]["legacy_alias_resolves_to_canonical_snapshot"] is False
    assert payload["reference_image"]["path"].endswith("palette-09.png")


def test_style_ten_is_not_advertised_and_reuses_style_nine_palette() -> None:
    choices = default_style_choices()
    assert choices.count("\n") == 7
    assert "9." not in choices
    assert "10." not in choices
    assert not (ROOT / "assets" / "palette-samples" / "palette-10.png").exists()
