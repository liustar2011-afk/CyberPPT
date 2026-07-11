"""CyberPPT adapter contract for the vendored three-image-to-PPT pipeline."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


FULL_IMAGE_MODE = "full_image_ppt"
EDITABLE_TEXT_MODE = "editable_text_three_image"
_SUPPORTED_MODES = {FULL_IMAGE_MODE, EDITABLE_TEXT_MODE}


def _read_project_manifest(project: Path) -> str:
    path = project.expanduser().resolve() / "manifest.yml"
    if not path.is_file():
        raise ValueError(f"project manifest is missing: {path}")
    return path.read_text(encoding="utf-8")


def get_production_mode(project: Path) -> str:
    """Return the explicit project mode, preserving legacy defaults."""

    match = re.search(r"^production_mode:\s*([^\s#]+)\s*$", _read_project_manifest(project), re.MULTILINE)
    mode = match.group(1) if match else FULL_IMAGE_MODE
    if mode not in _SUPPORTED_MODES:
        supported = ", ".join(sorted(_SUPPORTED_MODES))
        raise ValueError(f"unsupported production_mode: {mode}; expected one of {supported}")
    return mode


def _parse_pages(pages_raw: str) -> list[int]:
    pages: set[int] = set()
    for raw in pages_raw.split(","):
        item = raw.strip()
        if not item:
            continue
        if "-" in item:
            start, end = (int(value.strip()) for value in item.split("-", 1))
            if start > end:
                raise ValueError(f"invalid page range: {item}")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(item))
    if not pages:
        raise ValueError("at least one page is required")
    return sorted(pages)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _path_from_role(role: dict[str, Any] | None, base: Path) -> Path | None:
    if not isinstance(role, dict):
        return None
    raw = role.get("path") or role.get("filename")
    if not raw:
        return None
    path = Path(str(raw)).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_image_set(paths: dict[str, Path]) -> tuple[int, int]:
    sizes: dict[str, tuple[int, int]] = {}
    for role, path in paths.items():
        if not path.is_file():
            raise ValueError(f"{role} image is not readable: {path}")
        try:
            with Image.open(path) as image:
                image.load()
                sizes[role] = image.size
        except (OSError, UnidentifiedImageError) as exc:
            raise ValueError(f"{role} image is not readable: {path}") from exc
    if len(set(sizes.values())) != 1:
        raise ValueError("FULL, BACKGROUND, and TEXT image dimensions must be identical")
    width, height = next(iter(sizes.values()))
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    return width, height


def _three_image_job(project: Path, page: dict[str, Any], manifest_dir: Path) -> dict[str, Any]:
    page_number = int(page.get("page_number", 0))
    if page_number <= 0:
        raise ValueError("three-image pair is missing a positive page_number")
    paths = {
        "full": _path_from_role(page.get("full"), manifest_dir),
        "background": _path_from_role(page.get("background"), manifest_dir),
        "text": _path_from_role(page.get("text"), manifest_dir),
    }
    missing = [role.upper() for role, path in paths.items() if path is None]
    if missing:
        raise ValueError(f"three-image page {page_number} requires: {', '.join(missing)}")
    resolved = {role: path for role, path in paths.items() if path is not None}
    width, height = _validate_image_set(resolved)
    output_dir = (
        project.expanduser().resolve()
        / "workbench/stages/02-blueprint-dual-image"
        / "editable_text"
        / f"page_{page_number:03d}"
    )
    return {
        "page_id": f"page-{page_number:03d}",
        "page_number": page_number,
        "input_mode": "three-image",
        "full": {"path": str(resolved["full"]), "sha256": _sha256(resolved["full"])},
        "background": {"path": str(resolved["background"]), "sha256": _sha256(resolved["background"])},
        "text": {"path": str(resolved["text"]), "sha256": _sha256(resolved["text"])},
        "canvas": {"width_px": width, "height_px": height},
        "ocr": page.get("ocr"),
        "registration": page.get("registration"),
        "output_dir": str(output_dir),
    }


def build_three_image_batch(project: Path, pages_raw: str, pairs_path: Path) -> dict[str, Any]:
    """Build a deterministic vendor batch manifest from approved page pairs."""

    manifest_path = pairs_path.expanduser().resolve()
    payload = _read_json(manifest_path)
    pairs = payload.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError(f"page image manifest must contain pairs[]: {manifest_path}")
    wanted = set(_parse_pages(pages_raw))
    selected = [pair for pair in pairs if isinstance(pair, dict) and int(pair.get("page_number", 0)) in wanted]
    if {int(pair["page_number"]) for pair in selected} != wanted:
        raise ValueError("page image manifest does not contain every requested page")
    jobs = [_three_image_job(project, pair, manifest_path.parent) for pair in sorted(selected, key=lambda item: int(item["page_number"]))]
    return {
        "schema": "cyberppt.editable_text_batch.v1",
        "input_mode": "three-image",
        "pages": jobs,
    }
