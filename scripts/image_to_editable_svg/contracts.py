"""Closed, JSON-safe evidence contracts for image reconstruction.

The contracts intentionally encode a page gate rather than treating a raster
image as an acceptable fallback.  An unresolved visible region is evidence for
manual work, never permission to flatten the page.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping


INVENTORY_SCHEMA = "cyberppt.image_to_editable_svg.inventory.v1"
PAGE_GATE_SCHEMA = "cyberppt.image_to_editable_svg.page_gate.v1"
LAYER_SCHEMA = "cyberppt.image_to_editable_svg.layer.v1"
VALID_FAMILIES = frozenset({"text", "simple_geometry", "source_graphic", "data_graphic", "scene", "unknown"})
VALID_REALIZATIONS = frozenset({"native_text", "native_geometry", "exact_asset", "registered_layer", "shared_plate", "manual_required"})


@dataclass(frozen=True)
class NormalizedFrame:
    page_number: int
    source_path: str
    source_sha256: str
    normalized_path: str
    pixel_size: tuple[int, int]

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be positive")
        try:
            pixels = tuple(int(value) for value in self.pixel_size)
        except (TypeError, ValueError) as exc:
            raise ValueError("pixel_size must contain width and height") from exc
        if len(pixels) != 2 or min(pixels) <= 0:
            raise ValueError("pixel_size must contain two positive values")
        object.__setattr__(self, "pixel_size", pixels)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["pixel_size"] = list(self.pixel_size)
        return payload


@dataclass(frozen=True)
class ReconstructionInventory:
    frame: NormalizedFrame
    regions: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return build_inventory(self.frame, list(self.regions))


def _bbox(value: Any) -> list[float] | None:
    if isinstance(value, Mapping):
        try:
            return [float(value[key]) for key in ("x", "y", "width", "height")]
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    return None


def normalize_region(region: Mapping[str, Any], *, index: int = 0) -> dict[str, Any]:
    """Return a validated, JSON-safe region record without silently guessing."""
    result = dict(region)
    result.setdefault("id", f"region-{index:03d}")
    result.setdefault("family", "unknown")
    result.setdefault("z_index", index)
    result.setdefault("status", "pending")
    result.setdefault("identity_verified", False)
    result.setdefault("data_verified", False)
    if result["family"] not in VALID_FAMILIES:
        raise ValueError(f"unsupported reconstruction region family: {result['family']}")
    bbox = _bbox(result.get("bbox"))
    if bbox is not None:
        result["bbox"] = bbox
    elif result["family"] != "unknown":
        raise ValueError(f"region {result['id']} requires a four-value bbox")
    return result


def build_inventory(frame: NormalizedFrame, regions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    if frame.page_number < 1:
        raise ValueError("page_number must be positive")
    normalized = [normalize_region(region, index=index) for index, region in enumerate(regions)]
    return {"schema": INVENTORY_SCHEMA, "frame": frame.to_dict(), "regions": normalized}


def layer_record(layer: Mapping[str, Any], *, frame: NormalizedFrame, index: int = 0) -> dict[str, Any]:
    """Validate the evidence every delivered layer must retain."""
    result = normalize_region(layer, index=index)
    result.setdefault("canvas", list(frame.pixel_size))
    result.setdefault("source_hash", frame.source_sha256)
    result.setdefault("registration_group", f"page-{frame.page_number:03d}")
    result.setdefault("realization", "manual_required" if result["family"] == "unknown" else "registered_layer")
    if result["realization"] not in VALID_REALIZATIONS:
        raise ValueError(f"unsupported layer realization: {result['realization']}")
    result["canvas"] = [int(item) for item in result["canvas"]]
    if tuple(result["canvas"]) != frame.pixel_size:
        result["registration_valid"] = False
    else:
        result.setdefault("registration_valid", True)
    return {"schema": LAYER_SCHEMA, **result}


def page_gate(items: Iterable[Mapping[str, Any]], *, frame: NormalizedFrame | None = None) -> dict[str, Any]:
    """Build a fail-closed page gate from region or layer records."""
    errors: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        item = dict(raw)
        identifier = str(item.get("id") or f"region-{index:03d}")
        realization = item.get("realization")
        status = item.get("status")
        if realization == "manual_required" or status == "manual_required":
            errors.append({"code": "manual_required", "region_id": identifier, "message": "visible region requires manual reconstruction"})
        if item.get("family") in {"data_graphic", "source_graphic"}:
            verified = bool(item.get("data_verified") or item.get("identity_verified") or item.get("verified"))
            if not verified:
                errors.append({"code": "unverified_identity_or_data", "region_id": identifier, "message": "source/data graphic is not verified"})
        if frame is not None and item.get("canvas") is not None and tuple(item["canvas"]) != frame.pixel_size:
            errors.append({"code": "registration_drift", "region_id": identifier, "message": "layer canvas differs from canonical frame"})
        if item.get("registration_valid") is False:
            errors.append({"code": "registration_invalid", "region_id": identifier, "message": "layer registration check failed"})
    return {"schema": PAGE_GATE_SCHEMA, "valid": not errors, "blocking_errors": errors, "blocking_count": len(errors)}
