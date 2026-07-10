"""Validation helpers for project-scoped image-PPT assembly."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any


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
        "failures": failures,
    }
