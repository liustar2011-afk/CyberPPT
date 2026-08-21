"""Validation for the mandatory text-free base in editable Stage 02 pages."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

from PIL import Image


SCHEMA = "cyberppt.stage02.clean_base.v1"


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: object, *, parent: Path) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    return (candidate if candidate.is_absolute() else parent / candidate).resolve()


def _image_hrefs(svg_path: Path) -> list[str]:
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    return [
        href
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "image"
        for href in [node.attrib.get("href") or node.attrib.get("{http://www.w3.org/1999/xlink}href")]
        if href
    ]


def validate_clean_base(
    clean_base: Mapping[str, Any] | None,
    *,
    full_image: Path | str,
    authored_svg: Path | str,
    graphic_text_policy: Mapping[str, Any] | None,
    page_number: int,
) -> dict[str, Any]:
    """Require a distinct text-free base and native reconstruction of its text."""

    full_path = Path(full_image).expanduser().resolve()
    svg_path = Path(authored_svg).expanduser().resolve()
    value = dict(clean_base) if isinstance(clean_base, Mapping) else {}
    errors: list[dict[str, str]] = []
    if value.get("schema") != SCHEMA:
        errors.append({"code": "invalid_clean_base_schema", "message": f"expected {SCHEMA}"})
    if value.get("status") != "complete":
        errors.append({"code": "clean_base_not_complete", "message": "text-free base preparation is incomplete"})
    base_path = _path(value.get("path"), parent=svg_path.parent)
    if base_path is None or not base_path.is_file():
        errors.append({"code": "clean_base_missing", "message": "clean-base asset is missing"})
    if not full_path.is_file():
        errors.append({"code": "full_image_missing", "message": "audited full image is missing"})

    if full_path.is_file() and value.get("source_sha256") != _sha256(full_path):
        errors.append({"code": "clean_base_source_mismatch", "message": "clean base is not bound to the audited full image"})
    if base_path is not None and base_path.is_file():
        base_hash = _sha256(base_path)
        if value.get("sha256") != base_hash:
            errors.append({"code": "clean_base_hash_mismatch", "message": "clean-base hash does not match the asset"})
        if full_path.is_file() and (base_path == full_path or base_hash == _sha256(full_path)):
            errors.append({"code": "full_image_as_clean_base", "message": "audited full image cannot be the delivered base layer"})
        try:
            if full_path.is_file() and Image.open(base_path).size != Image.open(full_path).size:
                errors.append({"code": "clean_base_canvas_mismatch", "message": "clean base must retain the full-image canvas"})
        except OSError as exc:
            errors.append({"code": "clean_base_unreadable", "message": str(exc)})

    visual = value.get("visual_diff_report")
    if not isinstance(visual, Mapping) or visual.get("status") != "passed":
        errors.append({"code": "clean_base_visual_review_failed", "message": "clean-base visual-difference review must pass"})
    raw_regions = value.get("cleaned_text_regions")
    if not isinstance(raw_regions, list):
        errors.append({"code": "invalid_cleaned_text_regions", "message": "cleaned_text_regions must be a list"})
        raw_regions = []
    cleaned = {_text(item.get("text")) for item in raw_regions if isinstance(item, Mapping) and _text(item.get("text"))}
    policy = dict(graphic_text_policy) if isinstance(graphic_text_policy, Mapping) else {}
    items = [dict(item) for item in policy.get("items", []) if isinstance(item, Mapping)]
    native = {_text(item.get("text")) for item in items if _text(item.get("treatment")) == "native_text" and _text(item.get("text"))}
    missing = sorted(native - cleaned)
    if missing:
        errors.append({"code": "native_text_not_cleaned", "message": "native text absent from cleaned_text_regions: " + ", ".join(missing)})
    for item in items:
        if _text(item.get("treatment")) != "preserved_in_image":
            continue
        if item.get("identity_integral") is not True:
            errors.append({"code": "preserved_text_not_identity_integral", "message": f"{_text(item.get('id')) or _text(item.get('text'))}: preserved image text requires identity_integral=true"})
        asset = _path(item.get("asset_ref"), parent=svg_path.parent)
        if asset is not None and (asset == full_path or asset == base_path):
            errors.append({"code": "preserved_text_uses_page_layer", "message": "preserved image text cannot use the full image or clean base"})

    try:
        hrefs = _image_hrefs(svg_path)
    except (OSError, ET.ParseError) as exc:
        errors.append({"code": "invalid_authored_svg", "message": str(exc)})
        hrefs = []
    if base_path is not None and base_path.is_file() and not any(
        not href.startswith(("data:", "http:", "https:")) and _path(href, parent=svg_path.parent) == base_path
        for href in hrefs
    ):
        errors.append({"code": "clean_base_not_referenced", "message": "authored SVG does not reference the declared clean base"})
    return {"schema": SCHEMA, "page_number": page_number, "valid": not errors, "errors": errors, "cleaned_text": sorted(cleaned), "native_text": sorted(native)}
