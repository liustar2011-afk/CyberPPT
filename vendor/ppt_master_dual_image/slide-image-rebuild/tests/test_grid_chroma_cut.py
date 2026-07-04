from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageDraw

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from grid_chroma_cut import cut_sheet


def test_grid_chroma_cut_uses_detected_centers_not_origin_hard_slice(tmp_path: Path) -> None:
    sheet = Image.new("RGB", (260, 230), (238, 244, 250))
    draw = ImageDraw.Draw(sheet)
    centers = [(70, 62), (190, 62), (70, 172), (190, 172)]
    for i, (cx, cy) in enumerate(centers):
        fill = [(10, 92, 173), (36, 140, 88), (172, 80, 54), (92, 70, 160)][i]
        draw.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=fill)
    image_path = tmp_path / "sheet.png"
    sheet.save(image_path)

    manifest = cut_sheet(image_path, rows=2, columns=2, out_dir=tmp_path / "out", prefix="asset")

    assert manifest["column_centers"] == [70.0, 190.0]
    assert manifest["row_centers"] == [62.0, 172.0]
    assert manifest["x_edges"] != [0, 130, 260]
    assert len(manifest["assets"]) == 4

    first = Image.open(tmp_path / "out" / "asset_01_01.png").convert("RGBA")
    alpha = first.getchannel("A")
    assert alpha.getbbox() is not None
    assert alpha.getpixel((0, 0)) == 0


def test_grid_chroma_cut_rejects_invalid_dimensions(tmp_path: Path) -> None:
    image_path = tmp_path / "sheet.png"
    Image.new("RGB", (20, 20), "white").save(image_path)

    try:
        cut_sheet(image_path, rows=0, columns=2, out_dir=tmp_path / "out")
    except ValueError as exc:
        assert "rows and columns" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")
