"""Image crop and same-source reuse contract for Page SVG IR."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping


IMAGE_ASSET_SCHEMA = "cyberppt.image_asset_contract.v1"


def _canonical_source(source: str) -> str:
    if source.startswith(("data:", "http://", "https://")):
        return source
    return str(Path(source).expanduser().resolve()).replace("\\", "/")


def asset_id_for_source(source: str) -> str:
    digest = hashlib.sha256(_canonical_source(str(source)).encode("utf-8")).hexdigest()[:16]
    return f"asset_{digest}"


def _crop_payload(crop: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not crop:
        return None
    keys = ("x", "y", "width", "height")
    if all(key in crop for key in keys):
        return {key: float(crop[key]) for key in keys}
    if all(key in crop for key in ("x1", "y1", "x2", "y2")):
        return {"x": float(crop["x1"]), "y": float(crop["y1"]), "width": float(crop["x2"]) - float(crop["x1"]), "height": float(crop["y2"]) - float(crop["y1"])}
    raise ValueError("crop must use x/y/width/height or x1/y1/x2/y2")


def register_image_asset(
    registry: dict[str, dict[str, Any]],
    *,
    source: str,
    role: str,
    crop: Mapping[str, Any] | None = None,
    text_bearing: bool = False,
    editable: bool = False,
) -> str:
    """Register one source once; repeated uses share its asset ID."""
    canonical = _canonical_source(source)
    asset_id = asset_id_for_source(canonical)
    record = registry.setdefault(
        asset_id,
        {
            "asset_id": asset_id,
            "source": canonical,
            "roles": [],
            "uses": 0,
            "crop_variants": [],
            "text_bearing": False,
            "editable": False,
        },
    )
    if role not in record["roles"]:
        record["roles"].append(role)
    record["uses"] += 1
    record["text_bearing"] = bool(record["text_bearing"] or text_bearing)
    record["editable"] = bool(record["editable"] or editable)
    normalized_crop = _crop_payload(crop)
    if normalized_crop and normalized_crop not in record["crop_variants"]:
        record["crop_variants"].append(normalized_crop)
    return asset_id


def validate_image_asset_contract(registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for asset_id, record in registry.items():
        if str(record.get("asset_id")) != str(asset_id):
            issues.append({"code": "asset_id_mismatch", "asset_id": asset_id, "blocking": True})
        if not record.get("source"):
            issues.append({"code": "asset_source_missing", "asset_id": asset_id, "blocking": True})
        if "complex_visual_background" in (record.get("roles") or []) and record.get("text_bearing"):
            issues.append({"code": "background_text_bearing_forbidden", "asset_id": asset_id, "blocking": True})
        if int(record.get("uses") or 0) < 1:
            issues.append({"code": "asset_use_count_invalid", "asset_id": asset_id, "blocking": True})
    return {"schema": "cyberppt.image_asset_contract_gate.v1", "valid": not issues, "blocking_count": len(issues), "issues": issues}


def image_asset_manifest(registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    gate = validate_image_asset_contract(registry)
    return {"schema": IMAGE_ASSET_SCHEMA, "assets": list(registry.values()), "gate": gate, "reuse_policy": "same_canonical_source_shares_asset_id"}

