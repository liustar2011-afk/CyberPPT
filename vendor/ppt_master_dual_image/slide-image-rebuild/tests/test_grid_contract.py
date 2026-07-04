from __future__ import annotations

import json
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_grid_contract import inspect


def _write_contract(path: Path, grid: dict) -> Path:
    path.write_text(
        json.dumps(
            {
                "workflow": "slide-image-rebuild",
                "version": "1.0",
                "pages": [{"page_id": "P01", "grids": [grid]}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def test_missing_grid_contract_is_skipped(tmp_path: Path) -> None:
    result = inspect(tmp_path)

    assert result["valid"]
    assert result["skipped"]


def test_square_n_by_n_grid_with_centered_items_passes(tmp_path: Path) -> None:
    items = []
    for row in range(3):
        for col in range(3):
            cell_x = 90 + col * 100
            cell_y = 60 + row * 100
            items.append({"id": f"icon_{row}_{col}", "cell": [row, col], "bbox_px": [cell_x + 20, cell_y + 20, 60, 60]})
    _write_contract(
        tmp_path / "grid_contract.json",
        {"id": "icon_matrix", "rows": 3, "columns": 3, "bbox_px": [90, 60, 300, 300], "items": items},
    )

    result = inspect(tmp_path)

    assert result["valid"], result["errors"]
    assert not result["skipped"]


def test_n_by_n_grid_rejects_non_square_bbox(tmp_path: Path) -> None:
    _write_contract(
        tmp_path / "grid_contract.json",
        {
            "id": "bad_matrix",
            "rows": 3,
            "columns": 3,
            "bbox_px": [90, 60, 330, 300],
            "items": [{"id": "icon", "cell": [0, 0], "bbox_px": [110, 80, 60, 60]}],
        },
    )

    result = inspect(tmp_path)

    assert not result["valid"]
    assert any("must use a square bbox" in error for error in result["errors"])


def test_grid_rejects_off_center_item_and_edge_padding(tmp_path: Path) -> None:
    _write_contract(
        tmp_path / "grid_contract.json",
        {
            "id": "bad_icons",
            "rows": 2,
            "columns": 3,
            "bbox_px": [0, 0, 300, 200],
            "items": [{"id": "clipped", "cell": [0, 0], "bbox_px": [0, 8, 80, 80]}],
        },
    )

    result = inspect(tmp_path)

    assert not result["valid"]
    assert any("center offset" in error for error in result["errors"])
    assert any("padding ratio" in error for error in result["errors"])
