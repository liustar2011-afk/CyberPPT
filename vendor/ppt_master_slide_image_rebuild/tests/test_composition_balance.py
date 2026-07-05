from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_composition_balance import inspect


def _write_svg(path: Path, cards: list[tuple[int, int, int, int]]) -> Path:
    body = []
    for index, (x, y, w, h) in enumerate(cards, start=1):
        body.append(
            f'<g data-zone-id="card_{index}" data-primitive="target_goal_card">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#FFFFFF" stroke="#AAB7C6"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="32" fill="#0B3B73"/>'
            "</g>"
        )
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
        + "\n".join(body)
        + "</svg>",
        encoding="utf-8",
    )
    return path


def test_goal_cards_with_reasonable_bottom_margin_pass(tmp_path: Path) -> None:
    svg = _write_svg(tmp_path / "ok.svg", [(24, 286, 366, 390), (448, 286, 365, 390), (863, 286, 373, 390)])

    result = inspect(svg)

    assert result["valid"], result["errors"]
    assert result["metrics"]["bottom_margin_px"] == 44


def test_goal_cards_that_end_too_high_fail(tmp_path: Path) -> None:
    svg = _write_svg(tmp_path / "too-high.svg", [(24, 268, 366, 390), (448, 268, 365, 390), (863, 268, 373, 390)])

    result = inspect(svg)

    assert not result["valid"]
    assert any("ends too high" in error for error in result["errors"])


def test_goal_card_top_edge_misalignment_fails(tmp_path: Path) -> None:
    svg = _write_svg(tmp_path / "ragged.svg", [(24, 286, 366, 390), (448, 294, 365, 390), (863, 286, 373, 390)])

    result = inspect(svg)

    assert not result["valid"]
    assert any("top edges differ" in error for error in result["errors"])
