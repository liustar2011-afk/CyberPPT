from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_visual_contact_sheet import inspect


def _write_project(tmp_path: Path, *, with_reference: bool = True) -> Path:
    project = tmp_path / "project"
    preview_dir = project / "exports" / "preview_qa"
    preview_dir.mkdir(parents=True)
    image = Image.new("RGB", (400, 225), (251, 250, 246))
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 30, 376, 72), fill=(255, 255, 255), outline=(143, 160, 179))
    draw.rectangle((40, 120, 160, 190), fill=(255, 255, 255), outline=(170, 183, 198))
    image.save(preview_dir / "P01.preview.png")

    if with_reference:
        ref_dir = project / "images"
        ref_dir.mkdir(parents=True)
        image.save(ref_dir / "reference_layout.png")

    (project / "slide_image_rebuild_manifest.json").write_text(
        json.dumps(
            {
                "workflow": "slide-image-rebuild",
                "pages": [{"page_id": "P01", "reference_image": "images/reference_layout.png"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project / "layout_reference.json").write_text(
        json.dumps(
            {
                "source_reference": {"path": "images/reference_layout.png"},
                "zones": [
                    {"id": "zone_header", "bbox_px": [24, 30, 352, 42]},
                    {"id": "zone_card", "bbox_px": [40, 120, 120, 70]},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project / "text_region_map.json").write_text(
        json.dumps(
            {
                "pages": [
                    {
                        "page_id": "P01",
                        "regions": [{"id": "title", "bbox": [40, 38, 200, 26]}],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project / "icon_manifest.json").write_text(
        json.dumps(
            {
                "pages": [
                    {
                        "page_id": "P01",
                        "icons": [{"id": "icon_demo", "bbox_px": [58, 138, 32, 32]}],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return project


def test_visual_contact_sheet_builds_png(tmp_path: Path) -> None:
    project = _write_project(tmp_path)

    result = inspect(project)

    assert result["valid"], result["errors"]
    sheet = Path(result["results"][0]["contact_sheet"])
    assert sheet.is_file()
    with Image.open(sheet) as image:
        assert image.width > 400
        assert image.height > 225
    labels = {region["label"] for region in result["results"][0]["regions"]}
    assert "full_page" in labels
    assert "zone_header" in labels
    assert "text_regions" in labels
    assert "icon_regions" in labels


def test_visual_contact_sheet_degrades_without_reference(tmp_path: Path) -> None:
    project = _write_project(tmp_path, with_reference=False)

    result = inspect(project)

    assert result["valid"], result["errors"]
    assert any("reference image not found" in warning for warning in result["warnings"])
    assert Path(result["results"][0]["contact_sheet"]).is_file()
