from __future__ import annotations

from pathlib import Path

import pytest

from scripts.imagegen_pipeline.style_library import (
    default_style_choices,
    load_style_library,
    resolve_default_style,
    write_project_style_lock,
)


ROOT = Path(__file__).resolve().parents[1]


def test_style_ten_is_retired_from_the_executable_registry() -> None:
    library = load_style_library()
    assert [style["id"] for style in library["styles"]] == list(range(1, 10))
    assert library["default_style_id"] == 9
    assert resolve_default_style()["id"] == 9


def test_style_ten_cannot_be_resolved_or_locked() -> None:
    with pytest.raises(ValueError, match="unknown CyberPPT style selection"):
        resolve_default_style(style_id=10)

    with pytest.raises(ValueError, match="unknown CyberPPT style selection"):
        write_project_style_lock(project=ROOT / ".pytest-style10-retired", style_id=10)


def test_retired_style_ten_is_not_advertised_as_a_default_choice() -> None:
    choices = default_style_choices()
    assert choices.count("\n") == 7
    assert "9." not in choices
    assert "10." not in choices


def test_retired_style_ten_has_no_palette_asset() -> None:
    assert not (ROOT / "assets" / "palette-samples" / "palette-10.png").exists()
