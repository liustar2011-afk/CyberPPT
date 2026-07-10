from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_architecture_inventory import inspect as inspect_architecture
from verify_asset_classification import inspect as inspect_assets


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_svg_with_icon(project: Path) -> None:
    svg_dir = project / "svg_output"
    svg_dir.mkdir()
    (svg_dir / "P01.svg").write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="240">
          <g data-icon-id="icon-a" data-icon-bbox="20 20 32 32"><circle cx="36" cy="36" r="16"/></g>
        </svg>
        """,
        encoding="utf-8",
    )


def test_missing_architecture_inventory_is_advisory(tmp_path: Path) -> None:
    result = inspect_architecture(tmp_path)

    assert result["valid"]
    assert result["warnings"]


def test_architecture_inventory_validates_roles_and_relationships(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "architecture_inventory.json",
        {
            "pages": [
                {
                    "page_id": "P01",
                    "architecture": {
                        "primary_axis": "left_to_right",
                        "reading_order": ["card_1", "card_2"],
                    },
                    "zones": [
                        {"id": "card_1", "semantic_role": "card", "bbox": [20, 40, 120, 100]},
                        {"id": "card_2", "semantic_role": "card", "bbox": [180, 40, 120, 100]},
                    ],
                    "relationships": [
                        {"id": "flow_1", "kind": "connects", "from": "card_1", "to": "card_2"}
                    ],
                }
            ]
        },
    )

    result = inspect_architecture(tmp_path)

    assert result["valid"], result["errors"]


def test_architecture_inventory_rejects_broken_connector(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "architecture_inventory.json",
        {
            "pages": [
                {
                    "page_id": "P01",
                    "architecture": {"primary_axis": "left_to_right"},
                    "zones": [{"id": "card_1", "semantic_role": "card", "bbox": [20, 40, 120, 100]}],
                    "relationships": [
                        {"id": "flow_1", "kind": "connects", "from": "card_1", "to": "missing"}
                    ],
                }
            ]
        },
    )

    result = inspect_architecture(tmp_path)

    assert not result["valid"]
    assert any("must connect declared" in error for error in result["errors"])


def test_asset_classification_accepts_shared_icon_library_asset(tmp_path: Path) -> None:
    _write_svg_with_icon(tmp_path)
    _write_json(
        tmp_path / "asset_classification.json",
        {
            "pages": [
                {
                    "page_id": "P01",
                    "assets": [
                        {
                            "id": "icon-a",
                            "kind": "icon",
                            "source": "shared_icon_library",
                            "treatment": "editable_svg",
                            "semantic_role": "icon_slot",
                            "parent_id": "card_1",
                            "bbox": [20, 20, 32, 32],
                        }
                    ],
                }
            ]
        },
    )

    result = inspect_assets(tmp_path)

    assert result["valid"], result["errors"]


def test_asset_classification_rejects_icon_without_parent(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "asset_classification.json",
        {
            "pages": [
                {
                    "page_id": "P01",
                    "assets": [
                        {
                            "id": "icon-a",
                            "kind": "icon",
                            "source": "generated_svg",
                            "treatment": "editable_svg",
                            "bbox": [20, 20, 32, 32],
                        }
                    ],
                }
            ]
        },
    )

    result = inspect_assets(tmp_path)

    assert not result["valid"]
    assert any("requires parent_id" in error for error in result["errors"])


def test_asset_classification_requires_existing_transparent_png(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "asset_classification.json",
        {
            "pages": [
                {
                    "page_id": "P01",
                    "assets": [
                        {
                            "id": "complex-flow",
                            "kind": "complex_visual",
                            "source": "imagegen_asset",
                            "treatment": "transparent_png",
                            "bbox": [20, 20, 160, 80],
                            "path": "assets/missing.png",
                        }
                    ],
                }
            ]
        },
    )

    result = inspect_assets(tmp_path)

    assert not result["valid"]
    assert any("does not exist" in error for error in result["errors"])


def test_asset_classification_accepts_existing_transparent_png(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 20, 48, 44), fill=(11, 59, 115, 255))
    image.save(asset_dir / "flow.png")
    _write_json(
        tmp_path / "asset_classification.json",
        {
            "pages": [
                {
                    "page_id": "P01",
                    "assets": [
                        {
                            "id": "complex-flow",
                            "kind": "complex_visual",
                            "source": "imagegen_asset",
                            "treatment": "transparent_png",
                            "bbox": [20, 20, 160, 80],
                            "path": "assets/flow.png",
                        }
                    ],
                }
            ]
        },
    )

    result = inspect_assets(tmp_path)

    assert result["valid"], result["errors"]
