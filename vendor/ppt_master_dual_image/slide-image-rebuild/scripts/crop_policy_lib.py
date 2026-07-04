#!/usr/bin/env python3
"""
PPT Master - Crop Policy Library

Shared rules for layout_reference crop_candidates and intake precrop scripts.
"""

from __future__ import annotations

from typing import Any

try:
    from validate_layout_reference import FORBIDDEN_CROP_TOKENS, _crop_candidate_blob
except ImportError:  # pragma: no cover
    from scripts.validate_layout_reference import FORBIDDEN_CROP_TOKENS, _crop_candidate_blob  # type: ignore

MAX_PRECROP_AREA_RATIO = 0.35
FULL_SLIDE_AREA_RATIO = 0.85

STRUCTURAL_INTENT_CONFLICT_TOKENS = (
    "connector",
    "card",
    "arrow",
    "chevron",
    "center_node",
    "text_region",
    "main_chain",
)


def crop_bbox_px(candidate: dict[str, Any]) -> tuple[int, int, int, int] | None:
    bbox = candidate.get("bbox_px")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    try:
        x, y, w, h = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def crop_area_ratio(candidate: dict[str, Any], canvas: dict[str, Any]) -> float:
    bbox = crop_bbox_px(candidate)
    if bbox is None:
        return 0.0
    _x, _y, w, h = bbox
    width = int(canvas.get("width_px") or 1280)
    height = int(canvas.get("height_px") or 720)
    slide_area = max(width * height, 1)
    return (w * h) / slide_area


def is_forbidden_structural_crop(candidate: dict[str, Any], *, rebuild2: bool = False) -> bool:
    blob = _crop_candidate_blob(candidate)
    if any(token in blob for token in FORBIDDEN_CROP_TOKENS):
        return True
    intent = str(candidate.get("editability_intent", ""))
    if rebuild2 and intent == "asset" and any(token in blob for token in STRUCTURAL_INTENT_CONFLICT_TOKENS):
        return True
    return False


def conflicts_with_structure_contract(candidate: dict[str, Any], layout: dict[str, Any]) -> list[str]:
    contract = layout.get("structure_contract")
    if not isinstance(contract, dict):
        return []
    errors: list[str] = []
    blob = _crop_candidate_blob(candidate)
    candidate_id = str(candidate.get("id", ""))
    for forbidden in contract.get("forbidden_substitutes", []):
        if not isinstance(forbidden, str) or not forbidden.strip():
            continue
        token = forbidden.strip().lower()
        if token in blob or token in candidate_id.lower():
            errors.append(
                f"crop candidate `{candidate_id}` conflicts with structure_contract.forbidden_substitutes `{forbidden}`"
            )
    required = contract.get("required_primitives", [])
    if isinstance(required, list):
        for primitive in required:
            if not isinstance(primitive, str):
                continue
            token = primitive.lower()
            if token in blob and str(candidate.get("editability_intent", "")) == "asset":
                errors.append(
                    f"crop candidate `{candidate_id}` cannot use asset intent on required primitive `{primitive}`"
                )
    return errors


def validate_precrop_eligible(
    candidate: dict[str, Any],
    layout: dict[str, Any],
    *,
    rebuild2: bool,
    index: int | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    label = f"crop_candidates[{index}]" if index is not None else f"crop_candidates `{candidate.get('id', '')}`"
    precrop = candidate.get("precrop")
    if not isinstance(precrop, dict) or precrop.get("enabled") is not True:
        return errors, warnings

    if candidate.get("needs_review") is True:
        errors.append(f"{label}: needs_review=true blocks precrop until human confirmation")

    if is_forbidden_structural_crop(candidate, rebuild2=rebuild2):
        errors.append(
            f"{label}: forbidden structural crop (cards/connectors/arrows/text must be vector-rebuilt)"
        )

    errors.extend(conflicts_with_structure_contract(candidate, layout))

    canvas = layout.get("canvas", {}) if isinstance(layout.get("canvas"), dict) else {}
    area_ratio = crop_area_ratio(candidate, canvas)
    if area_ratio >= FULL_SLIDE_AREA_RATIO:
        errors.append(f"{label}: bbox covers {area_ratio:.0%} of slide; full-slide precrop is forbidden")
    elif area_ratio >= MAX_PRECROP_AREA_RATIO:
        warnings.append(
            f"{label}: bbox covers {area_ratio:.0%} of slide; confirm this is decorative-only before precrop"
        )

    if crop_bbox_px(candidate) is None:
        errors.append(f"{label}: bbox_px must be a valid [x, y, w, h] list")

    intent = candidate.get("editability_intent")
    if intent is not None and intent not in {"editable", "asset", "fallback"}:
        errors.append(f"{label}: editability_intent must be editable, asset, or fallback")

    return errors, warnings


def precrop_enabled_candidates(layout: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    raw = layout.get("crop_candidates", [])
    if not isinstance(raw, list):
        return []
    enabled: list[tuple[int, dict[str, Any]]] = []
    for index, candidate in enumerate(raw):
        if not isinstance(candidate, dict):
            continue
        precrop = candidate.get("precrop")
        if isinstance(precrop, dict) and precrop.get("enabled") is True:
            enabled.append((index, candidate))
    return enabled
