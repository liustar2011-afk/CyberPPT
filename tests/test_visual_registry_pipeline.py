from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image

from scripts.visual_registry_from_source_capture import build_registries, write_registries


ROOT = Path(__file__).resolve().parents[1]


def test_builds_draft_visual_registry_from_source_capture_inventory(tmp_path: Path) -> None:
    source_capture = {
        "schema": "cyberppt.dual_image.source_capture.v1",
        "project": str(tmp_path),
        "pages": [
            {
                "page_number": 3,
                "source_images": {"full": {"path": "/tmp/blueprint.png"}},
                "image_regions": {"canvas": {"width": 1280, "height": 720}},
                "visual_element_inventory": [
                    {
                        "element_id": "background_visual_001",
                        "element_type": "line",
                        "priority": "P0",
                        "blueprint_bbox_px": {"x": 100, "y": 200, "w": 300, "h": 6},
                        "tolerance_px": 6,
                        "measurement_mode": "individual_bbox",
                        "source": {"kind": "background_visual_component"},
                    },
                    {
                        "element_id": "text_001",
                        "element_type": "text",
                        "blueprint_bbox_px": {"x": 0, "y": 0, "w": 10, "h": 10},
                    },
                ],
            }
        ],
    }

    registries = build_registries(source_capture)
    written = write_registries(registries, tmp_path / "visual_registry")

    assert len(registries) == 1
    registry = registries[0]
    assert registry["registry_status"] == "draft_from_source_capture"
    assert registry["element_count"] == 1
    assert registry["elements"][0]["element_id"] == "background_visual_001"
    assert registry["elements"][0]["ppt_target_bbox_in"]["x"] == 1.0416
    assert (tmp_path / "visual_registry/slide-03-visual-element-registry.json") in written
    assert (tmp_path / "visual_registry/page_003_visual_element_registry.json") in written


def test_compare_render_can_write_measured_registry(tmp_path: Path) -> None:
    blueprint = tmp_path / "blueprint.png"
    render = tmp_path / "render.png"
    Image.new("RGB", (100, 100), "white").save(blueprint)
    Image.new("RGB", (100, 100), "white").save(render)
    registry = tmp_path / "visual_element_registry.json"
    registry.write_text(
        json.dumps(
            {
                "schema": "cyberppt.visual_element_registry.v1",
                "elements": [
                    {
                        "element_id": "shape_1",
                        "priority": "P0",
                        "element_type": "shape",
                        "blueprint_bbox_px": {"x": 10, "y": 10, "w": 20, "h": 20},
                        "tolerance_px": 3,
                        "measurement_mode": "individual_bbox",
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    report = tmp_path / "render_compare.json"
    measured = tmp_path / "measured_registry.json"

    result = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts/compare_render.py"),
            "--blueprint",
            str(blueprint),
            "--render",
            str(render),
            "--registry",
            str(registry),
            "--out",
            str(report),
            "--measured-registry-out",
            str(measured),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(measured.read_text(encoding="utf-8"))
    element = payload["elements"][0]
    assert payload["measurement_status"] == "passed"
    assert element["registration_status"] == "passed"
    assert element["render_bbox_px"] == {"x": 10, "y": 10, "w": 20, "h": 20}
    assert element["delta_px"] == {"x": 0, "y": 0, "w": 0, "h": 0}
