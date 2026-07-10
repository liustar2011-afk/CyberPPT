from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_alignment_rules import inspect


def _write_svg(path: Path, body: str) -> Path:
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="240" viewBox="0 0 600 240">{body}</svg>',
        encoding="utf-8",
    )
    return path


def test_top_band_centered_icon_and_text_pass(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "ok.svg",
        """
        <rect x="20" y="20" width="540" height="60" fill="#FFFDF9" stroke="#8FA0B3"/>
        <g data-icon-id="cube" data-icon-bbox="80 32 36 36"><circle cx="98" cy="50" r="18"/></g>
        <text x="150" y="56" font-size="24" fill="#111827">总体架构</text>
        """,
    )

    result = inspect(svg)

    assert result["valid"], result["errors"]


def test_top_band_low_text_fails_centerline_rule(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "low-text.svg",
        """
        <rect x="20" y="20" width="540" height="60" fill="#FFFDF9" stroke="#8FA0B3"/>
        <text x="150" y="70" font-size="24" fill="#111827">总体架构</text>
        """,
    )

    result = inspect(svg)

    assert not result["valid"]
    assert any("visual center" in error for error in result["errors"])


def test_top_band_member_centerline_spread_fails(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "spread.svg",
        """
        <rect x="20" y="20" width="540" height="60" fill="#FFFDF9" stroke="#8FA0B3"/>
        <g data-icon-id="high-icon" data-icon-bbox="80 24 28 28"><circle cx="94" cy="38" r="14"/></g>
        <text x="150" y="62" font-size="22" fill="#111827">总体架构</text>
        """,
    )

    result = inspect(svg)

    assert not result["valid"]
    assert any("member centerlines differ" in error for error in result["errors"])


def test_top_band_rich_title_baseline_too_low_fails(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "rich-low.svg",
        """
        <rect x="20" y="20" width="540" height="60" fill="#FFFDF9" stroke="#8FA0B3"/>
        <text x="150" y="59" font-size="22" fill="#111827">以<tspan font-size="36">1</tspan>个底座构建总体架构</text>
        """,
    )

    result = inspect(svg)

    assert not result["valid"]
    assert any("rich title baseline" in error for error in result["errors"])
