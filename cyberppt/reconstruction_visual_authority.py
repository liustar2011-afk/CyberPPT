"""Validate the immutable audited-full-image authority used for editable reconstruction."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping


RECONSTRUCTION_AUTHORITY_SCHEMA = "cyberppt.reconstruction_visual_authority.v1"


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def validate_reconstruction_visual_authority(
    manifest: Mapping[str, object],
    *,
    require_clean_base: bool = False,
) -> dict[str, Any]:
    """Require every editable page to remain bound to its audited full image.

    This guard does not judge visual quality or redesign a page. It only proves
    that reconstruction inputs still derive from the exact full-image authority
    that Stage 02 froze after image and deck-rhythm QA.
    """

    truth = manifest.get("visual_truth_policy")
    truth = truth if isinstance(truth, Mapping) else {}
    if truth.get("authority") != "audited_full_image" or truth.get("scope") != "editable_reconstruction":
        raise ValueError("editable reconstruction requires audited_full_image visual_truth_policy")

    pairs = manifest.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("editable reconstruction authority requires manifest pairs")

    pages: list[dict[str, Any]] = []
    for raw_pair in pairs:
        if not isinstance(raw_pair, Mapping):
            continue
        page_number = int(raw_pair.get("page_number") or 0)
        if page_number <= 0:
            raise ValueError("editable reconstruction authority requires positive page numbers")
        full = raw_pair.get("full")
        full = full if isinstance(full, Mapping) else {}
        full_path = Path(str(full.get("path") or "")).expanduser().resolve()
        if not full_path.is_file():
            raise FileNotFoundError(f"page {page_number} audited full-image authority is missing: {full_path}")
        binding = full.get("reconstruction_visual_source")
        binding = binding if isinstance(binding, Mapping) else {}
        if binding.get("authority") != "audited_full_image":
            raise ValueError(f"page {page_number} reconstruction authority is not audited_full_image")
        if binding.get("immutable_visual_composition") is not True:
            raise ValueError(f"page {page_number} reconstruction authority must lock immutable visual composition")
        bound_path = Path(str(binding.get("path") or "")).expanduser().resolve()
        if bound_path != full_path:
            raise ValueError(f"page {page_number} reconstruction authority path drifted from full image")
        actual_sha = _file_sha256(full_path)
        if str(binding.get("sha256") or "") != actual_sha:
            raise ValueError(f"page {page_number} reconstruction authority sha256 drifted from full image")

        page_record: dict[str, Any] = {
            "page_number": page_number,
            "authority_path": str(full_path),
            "authority_sha256": actual_sha,
            "immutable_visual_composition": True,
        }
        if require_clean_base:
            clean = raw_pair.get("clean_base")
            clean = clean if isinstance(clean, Mapping) else {}
            clean_path = Path(str(clean.get("path") or "")).expanduser().resolve()
            if clean.get("status") != "complete" or not clean_path.is_file():
                raise ValueError(f"page {page_number} requires a complete clean base derived from the visual authority")
            if str(clean.get("source_sha256") or "") != actual_sha:
                raise ValueError(f"page {page_number} clean base source_sha256 drifted from visual authority")
            page_record["clean_base_path"] = str(clean_path)
            page_record["clean_base_sha256"] = _file_sha256(clean_path)

        pages.append(page_record)

    if not pages:
        raise ValueError("editable reconstruction authority requires at least one bound page")
    return {
        "schema": RECONSTRUCTION_AUTHORITY_SCHEMA,
        "authority": "audited_full_image",
        "immutable_visual_composition": True,
        "page_count": len(pages),
        "pages": pages,
    }


__all__ = ["RECONSTRUCTION_AUTHORITY_SCHEMA", "validate_reconstruction_visual_authority"]
