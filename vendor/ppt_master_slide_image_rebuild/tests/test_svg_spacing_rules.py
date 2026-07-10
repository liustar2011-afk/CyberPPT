from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_svg_spacing import inspect


def _write_svg(path: Path, body: str) -> Path:
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">{body}</svg>',
        encoding="utf-8",
    )
    return path


def test_named_paint_is_rejected_for_pptx_export(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "named.svg",
        '<rect x="0" y="0" width="100" height="50" fill="white"/>',
    )

    result = inspect(svg)

    assert not result["valid"]
    assert any("named paint" in item and "fill=white" in item for item in result["errors"])


def test_top_band_icon_bottom_padding_is_enforced(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "top-band.svg",
        """
        <rect x="20" y="20" width="500" height="60" fill="#FFFDF9" stroke="#8FA0B3"/>
        <g data-icon-id="low-icon" data-icon-bbox="40 38 36 40">
          <circle cx="58" cy="58" r="18" fill="#0B3B73"/>
        </g>
        <text x="100" y="58" font-size="20" fill="#111827">安全文字</text>
        """,
    )

    result = inspect(svg)

    assert not result["valid"]
    assert any("low-icon" in item and "too close" in item for item in result["errors"])


def test_top_band_with_hex_colors_and_padding_passes(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "ok.svg",
        """
        <rect x="20" y="20" width="500" height="60" fill="#FFFDF9" stroke="#8FA0B3"/>
        <g data-icon-id="ok-icon" data-icon-bbox="40 30 36 36">
          <circle cx="58" cy="48" r="18" fill="#0B3B73"/>
        </g>
        <text x="100" y="54" font-size="20" fill="#111827">安全文字</text>
        """,
    )

    result = inspect(svg)

    assert result["valid"], result["errors"]
