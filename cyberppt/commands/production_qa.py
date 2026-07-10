"""Validation helpers for project-scoped image-PPT assembly."""

from __future__ import annotations

import json
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

from scripts.dual_image_overlay.qa_render_page import render_to_png


VISUAL_DIFF_THRESHOLD = 12.0


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _body_crop_box(region: dict[str, Any], canvas: dict[str, Any], render_size: tuple[int, int]) -> tuple[int, int, int, int]:
    canvas_width = float(canvas.get("width") or 1280)
    canvas_height = float(canvas.get("height") or 720)
    scale_x = render_size[0] / canvas_width
    scale_y = render_size[1] / canvas_height
    left = int(round(float(region.get("x", 0)) * scale_x))
    top = int(round(float(region.get("y", 0)) * scale_y))
    right = int(round((float(region.get("x", 0)) + float(region.get("width", canvas_width))) * scale_x))
    bottom = int(round((float(region.get("y", 0)) + float(region.get("height", canvas_height))) * scale_y))
    return (
        max(0, min(left, render_size[0])),
        max(0, min(top, render_size[1])),
        max(0, min(right, render_size[0])),
        max(0, min(bottom, render_size[1])),
    )


def validate_assembly_bundle(bundle: dict[str, Any], expected_pages: list[int]) -> dict[str, Any]:
    """Check that a successful exporter process actually produced a usable bundle."""

    project = Path(str(bundle["project"])).expanduser().resolve()
    pptx = Path(str(bundle["exported_pptx"])).expanduser().resolve()
    manifest_path = Path(str(bundle["template_image_manifest"])).expanduser().resolve()
    failures: list[str] = []
    checks = {
        "output_inside_project": _inside(pptx, project) and _inside(manifest_path, project),
        "pptx_exists": pptx.is_file() and pptx.stat().st_size > 0,
        "manifest_exists": manifest_path.is_file() and manifest_path.stat().st_size > 0,
        "pptx_readable": False,
        "page_set_matches": False,
        "notes_complete": False,
        "approved_images_match": False,
    }
    if not checks["output_inside_project"]:
        failures.append("output_outside_project")
    if not checks["pptx_exists"]:
        failures.append("exported_pptx_missing")
    if not checks["manifest_exists"]:
        failures.append("template_image_manifest_missing")

    manifest: dict[str, Any] = {}
    if checks["manifest_exists"]:
        try:
            manifest = _read_json(manifest_path)
        except (OSError, ValueError, json.JSONDecodeError):
            failures.append("template_image_manifest_invalid")

    tasks = [item for item in manifest.get("tasks", []) if isinstance(item, dict)]
    task_pages = {int(item["page_number"]) for item in tasks if "page_number" in item}
    checks["page_set_matches"] = task_pages == set(expected_pages)
    if not checks["page_set_matches"]:
        failures.append("page_set_mismatch")
    checks["notes_complete"] = len(tasks) == len(expected_pages) and all(
        bool(str(item.get("notes_text") or "").strip()) for item in tasks
    )
    if not checks["notes_complete"]:
        failures.append("speaker_notes_missing")

    approved_images = {int(page): Path(path).expanduser().resolve() for page, path in bundle.get("approved_images", {}).items()}
    checks["approved_images_match"] = all(
        page in approved_images
        and Path(str(item.get("image_path", ""))).expanduser().resolve() == approved_images[page]
        and approved_images[page].is_file()
        for page, item in ((int(item["page_number"]), item) for item in tasks if "page_number" in item)
    )
    if not checks["approved_images_match"]:
        failures.append("approved_images_mismatch")

    if checks["pptx_exists"]:
        try:
            with zipfile.ZipFile(pptx) as archive:
                names = set(archive.namelist())
                slide_count = sum(name.startswith("ppt/slides/slide") and name.endswith(".xml") for name in names)
                notes_count = sum(name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml") for name in names)
                checks["pptx_readable"] = "[Content_Types].xml" in names and slide_count == len(expected_pages) and notes_count >= len(expected_pages)
        except (OSError, zipfile.BadZipFile):
            checks["pptx_readable"] = False
    if not checks["pptx_readable"]:
        failures.append("pptx_invalid_or_incomplete")

    return {
        "schema": "cyberppt.assembly_report.v1",
        "valid": not failures,
        "checks": checks,
        "artifacts": {"exported_pptx": str(pptx), "template_image_manifest": str(manifest_path)},
        "approved_images": {str(page): str(path) for page, path in approved_images.items()},
        "artifacts_sha256": {
            "exported_pptx": _sha256(pptx) if checks["pptx_exists"] else None,
            "template_image_manifest": _sha256(manifest_path) if checks["manifest_exists"] else None,
        },
        "failures": failures,
    }


def render_and_compare(
    pptx: Path,
    template_image_manifest: Path,
    approved_images: dict[int, Path],
    expected_pages: list[int],
    output_dir: Path,
    *,
    threshold: float = VISUAL_DIFF_THRESHOLD,
) -> dict[str, Any]:
    """Render the assembled PPTX and compare each body region against approved full images."""

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = _read_json(template_image_manifest)
    rendered = render_to_png(pptx, output_dir / "renders")
    if not rendered:
        raise RuntimeError("render_tool_unavailable: no rendered pages were produced")

    tasks = {
        int(item["page_number"]): item
        for item in manifest.get("tasks", [])
        if isinstance(item, dict) and isinstance(item.get("page_number"), int)
    }
    canvas = manifest.get("canvas") if isinstance(manifest.get("canvas"), dict) else {"width": 1280, "height": 720}
    body_region = manifest.get("body_region") if isinstance(manifest.get("body_region"), dict) else {"x": 0, "y": 0, "width": 1280, "height": 720}
    slides: list[dict[str, Any]] = []
    failures: list[str] = []
    for index, page in enumerate(expected_pages):
        if page not in tasks:
            failures.append(f"missing_manifest_task:{page}")
            continue
        if page not in approved_images:
            failures.append(f"missing_approved_image:{page}")
            continue
        if index >= len(rendered):
            failures.append(f"missing_render:{page}")
            continue
        render_path = rendered[index]
        approved_path = approved_images[page]
        with Image.open(render_path).convert("RGB") as rendered_image:
            box = _body_crop_box(body_region, canvas, rendered_image.size)
            crop = rendered_image.crop(box)
        with Image.open(approved_path).convert("RGB") as approved_image:
            resized = approved_image.resize(crop.size)
        diff = ImageChops.difference(crop, resized)
        mean_abs_diff = round(sum(ImageStat.Stat(diff).mean) / 3.0, 4)
        passed = mean_abs_diff <= threshold
        if not passed:
            failures.append(f"visual_diff_exceeds_threshold:{page}")
        crop_path = output_dir / f"page_{page:03d}_body_crop.png"
        crop.save(crop_path)
        slides.append(
            {
                "page": page,
                "rendered_page": str(render_path),
                "approved_image": str(approved_path),
                "body_crop": str(crop_path),
                "mean_abs_diff": mean_abs_diff,
                "threshold": threshold,
                "passed": passed,
                "rendered_sha256": _sha256(render_path),
                "approved_image_sha256": _sha256(approved_path),
            }
        )

    report = {
        "schema": "cyberppt.production_visual_report.v1",
        "pptx": str(pptx),
        "template_image_manifest": str(template_image_manifest),
        "threshold": threshold,
        "passed": not failures and len(slides) == len(expected_pages),
        "slides": slides,
        "failures": failures,
    }
    (output_dir / "production_visual_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
