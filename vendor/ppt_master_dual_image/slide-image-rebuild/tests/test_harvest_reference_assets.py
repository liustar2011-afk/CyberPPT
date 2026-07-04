from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harvest_reference_assets import harvest_assets
from layout_reference_to_svg_plan import build_markdown, build_plan


def _write_project(project: Path) -> None:
    image_dir = project / "images"
    image_dir.mkdir(parents=True)
    image = Image.new("RGB", (400, 240), (245, 247, 250))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 120, 100), fill=(20, 120, 180))
    draw.rectangle((180, 50, 340, 150), fill=(220, 240, 255), outline=(12, 60, 120), width=2)
    image.save(image_dir / "reference_layout.png")

    (project / "layout_reference.json").write_text(
        json.dumps({
            "version": "2.0",
            "workflow": "layout-reference-rebuild-2",
            "page_id": "P01",
            "source_reference": {"path": "images/reference_layout.png"},
            "canvas": {"width_px": 400, "height_px": 240},
            "structure_contract": {
                "required_primitives": ["card", "connector"],
                "forbidden_substitutes": ["card", "connector", "text"],
            },
            "crop_candidates": [
                {
                    "id": "logo_mark",
                    "bbox_px": [40, 40, 80, 60],
                    "editability_intent": "asset",
                    "crop_role": "logo",
                    "needs_review": False,
                },
                {
                    "id": "main_card",
                    "bbox_px": [180, 50, 160, 100],
                    "editability_intent": "asset",
                    "crop_role": "card",
                    "needs_review": False,
                },
                {
                    "id": "uncertain_icon",
                    "bbox_px": [10, 10, 20, 20],
                    "editability_intent": "asset",
                    "crop_role": "complex_small_icon",
                    "needs_review": True,
                },
            ],
        }),
        encoding="utf-8",
    )
    (project / "content_mapping.json").write_text(
        json.dumps({"renderable_content": {"modules": []}}),
        encoding="utf-8",
    )


def test_harvest_reference_assets_only_materializes_allowed_crop_assets(tmp_path: Path) -> None:
    _write_project(tmp_path)

    manifest = harvest_assets(tmp_path)

    assert manifest["valid"], manifest["errors"]
    assert manifest["summary"]["assets_written"] == 1
    assert manifest["assets"][0]["id"] == "P01_logo_mark"
    assert manifest["assets"][0]["treatment"] == "logo_crop"
    assert (tmp_path / manifest["assets"][0]["path"]).is_file()
    skipped_ids = {item["id"] for item in manifest["skipped"]}
    assert {"main_card", "uncertain_icon"}.issubset(skipped_ids)


def test_svg_build_plan_lists_harvested_assets(tmp_path: Path) -> None:
    _write_project(tmp_path)
    asset_manifest = harvest_assets(tmp_path)
    layout = json.loads((tmp_path / "layout_reference.json").read_text(encoding="utf-8"))
    mapping = json.loads((tmp_path / "content_mapping.json").read_text(encoding="utf-8"))

    plan = build_plan(layout, mapping, asset_manifest=asset_manifest)
    markdown = build_markdown(plan)

    assert plan["harvested_asset_plan"]["assets"][0]["id"] == "P01_logo_mark"
    assert "## Harvested Image Assets" in markdown
    assert "P01_logo_mark" in markdown
    assert "Prefer harvested_asset_plan local crops" in plan["executor_checks"][0]
