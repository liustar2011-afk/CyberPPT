from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageDraw

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_layer_order import inspect as inspect_layer_order
from verify_transparent_assets import inspect as inspect_transparent_assets


def _write_svg(path: Path, body: str) -> Path:
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240" viewBox="0 0 400 240">{body}</svg>',
        encoding="utf-8",
    )
    return path


def test_transparent_asset_with_padding_passes(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 48, 48), fill=(11, 59, 115, 255))
    image.save(asset_dir / "safe_icon.png")

    result = inspect_transparent_assets(tmp_path)

    assert result["valid"], result["errors"]
    assert result["count"] == 1


def test_transparent_asset_touching_edge_fails(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 8, 24, 24), fill=(11, 59, 115, 255))
    image.save(asset_dir / "clipped_icon.png")

    result = inspect_transparent_assets(tmp_path)

    assert not result["valid"]
    assert any("unsafe transparent padding" in error for error in result["errors"])


def test_layer_order_allows_container_before_text_and_icon(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "ok.svg",
        """
        <rect x="40" y="40" width="200" height="100" fill="#FFFFFF" stroke="#AAB7C6"/>
        <g data-icon-id="safe-icon" data-icon-bbox="60 70 32 32"><circle cx="76" cy="86" r="16" fill="#0B3B73"/></g>
        <text x="110" y="92" font-size="20" fill="#111827">安全文字</text>
        """,
    )

    result = inspect_layer_order(svg)

    assert result["valid"], result["errors"]


def test_layer_order_rejects_late_cover_over_text(tmp_path: Path) -> None:
    svg = _write_svg(
        tmp_path / "bad.svg",
        """
        <text x="80" y="92" font-size="20" fill="#111827">会被遮挡</text>
        <rect x="40" y="50" width="200" height="80" fill="#FFFFFF" stroke="#AAB7C6"/>
        """,
    )

    result = inspect_layer_order(svg)

    assert not result["valid"]
    assert any("is after text" in error for error in result["errors"])
