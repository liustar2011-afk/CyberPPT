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


def test_style_ten_is_not_a_separate_executable_registry_entry() -> None:
    library = load_style_library()
    assert [style["id"] for style in library["styles"]] == list(range(1, 10))
    assert library["default_style_id"] == 9


def test_legacy_style_ten_resolves_to_canonical_style_nine() -> None:
    style9 = resolve_default_style(style_id=9)
    style10 = resolve_default_style(style_id=10)

    assert style10["id"] == 9
    assert style10["prompt_contract"] == style9["prompt_contract"]
    assert style10["prompt_contract_sha256"] == style9["prompt_contract_sha256"]
    assert style10["legacy_alias_from_style_id"] == 10


def test_legacy_style_ten_lock_records_alias_and_canonical_snapshot() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=10)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    assert payload["selection"] == {
        "requested_style_id": 10,
        "requested_style_name": None,
        "canonical_style_id": 9,
        "legacy_alias": True,
    }
    assert payload["style"]["id"] == 9
    assert payload["style"]["legacy_alias_from_style_id"] == 10
    assert payload["policy"]["legacy_alias_resolves_to_canonical_snapshot"] is True
    assert payload["reference_image"]["path"].endswith("palette-09.png")


def test_style_ten_alias_is_not_advertised_and_has_no_separate_palette() -> None:
    choices = default_style_choices()
    assert choices.count("\n") == 7
    assert "9." not in choices
    assert "10." not in choices
    assert not (ROOT / "assets" / "palette-samples" / "palette-10.png").exists()
