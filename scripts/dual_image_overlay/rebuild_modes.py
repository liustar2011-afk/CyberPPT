from __future__ import annotations

from pathlib import Path
from typing import Any


VALID_REBUILD_MODES = {"full_slide", "template_body_region"}


def resolve_rebuild_mode(manifest: dict[str, Any]) -> str:
    contract = manifest.get("generation_contract")
    raw = manifest.get("rebuild_mode")
    if not raw and isinstance(contract, dict):
        raw = contract.get("rebuild_mode")
    mode = str(raw or "template_body_region")
    if mode not in VALID_REBUILD_MODES:
        raise ValueError(f"Unsupported rebuild_mode: {mode}")
    return mode


def first_full_image(manifest: dict[str, Any], *, manifest_path: Path | None = None) -> str | None:
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs or not isinstance(pairs[0], dict):
        return None
    full = pairs[0].get("full")
    if not isinstance(full, dict):
        return None
    path = full.get("path")
    if not isinstance(path, str) or not path:
        return None
    full_path = Path(path).expanduser()
    if not full_path.is_absolute() and manifest_path is not None:
        full_path = manifest_path.parent / full_path
    return str(full_path.resolve())


def visual_reference_for_mode(
    project_path: Path,
    manifest: dict[str, Any],
    rebuild_mode: str,
    *,
    manifest_path: Path | None = None,
) -> tuple[str, str | None]:
    if rebuild_mode == "full_slide":
        return "raw_full_image", first_full_image(manifest, manifest_path=manifest_path)
    reference = project_path / "qa" / "visual-reference" / "template-normalized-reference.png"
    return "template_normalized_reference", str(reference)
