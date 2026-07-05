#!/usr/bin/env python3
"""
PPT Master - Layout Reference Validator

Validate layout_reference.json for the layout-reference-rebuild workflow.

Usage:
    python3 scripts/validate_layout_reference.py <layout_reference.json>
    python3 scripts/validate_layout_reference.py <layout_reference.draft.json> --allow-draft

Examples:
    python3 scripts/validate_layout_reference.py projects/demo/layout_reference.json

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from geometry_locks_lib import validate_geometry_locks_list
except ImportError:  # pragma: no cover
    from scripts.geometry_locks_lib import validate_geometry_locks_list  # type: ignore

try:
    from layout_reference_rebuild2_lib import ALLOWED_PAGE_TYPE_HINTS, is_rebuild2, validate_structure_contract
except ImportError:  # pragma: no cover
    from scripts.layout_reference_rebuild2_lib import ALLOWED_PAGE_TYPE_HINTS, is_rebuild2, validate_structure_contract  # type: ignore

REQUIRED_TOP_LEVEL = [
    "version",
    "source_reference",
    "canvas",
    "page_role",
    "layout_type",
    "visual_structure",
    "main_chain",
    "zones",
    "style_reference",
    "editability_policy",
]

ALLOWED_PAGE_ROLES = {
    "overall_architecture",
    "process_flow",
    "closed_loop_mechanism",
    "capability_matrix",
    "supply_landscape",
    "product_system",
    "roadmap",
    "comparison",
    "problem_solution",
    "data_flow",
    "stakeholder_map",
    "custom",
}

ALLOWED_CONTENT_TRUST = {
    "untrusted_for_final_text",
    "trusted_for_final_text_by_user",
}

ALLOWED_ICON_POLICIES = {
    "semantic_vector_first",
    "repo_library_first",
    "source_image_crop_allowed",
    "custom_vector_allowed",
}

ALLOWED_ICON_LEVELS = {
    "intro",
    "card_section",
    "title_aligned_icon",
    "body_column_icon",
    "consensus",
    "action",
    "footer_action_icon",
    "custom",
}

ALLOWED_ANCHOR_TYPES = {
    "band",
    "center",
    "horizontal_edge",
    "vertical_edge",
    "baseline",
    "point",
}

ALLOWED_VISUAL_LAYERS = {
    "content_layer",
    "structure_layer",
    "semantic_icon_layer",
    "decorative_layer",
    "noise_layer",
}

ALLOWED_NOISE_TREATMENTS = {
    "ignore",
    "ignore_or_simplified_vector",
    "simplified_vector",
    "local_clean_crop",
    "preserve_as_low_opacity_vector",
}

ALLOWED_EDITABILITY_INTENTS = {
    "editable",
    "asset",
    "fallback",
}

FORBIDDEN_CROP_TOKENS = (
    "card_body",
    "card_border",
    "connector",
    "process_arrow",
    "chevron",
    "center_node",
    "text_region",
    "main_diagram",
    "arrowhead",
)

ALLOWED_SEMANTIC_WEIGHTS = {
    "none",
    "ambient",
    "supporting",
    "structural",
}


def _validate_bbox(
    errors: list[str],
    value: Any,
    *,
    label: str,
    ratio: bool = False,
) -> None:
    if not isinstance(value, list) or len(value) != 4:
        errors.append(f"{label} must be a 4-item list")
        return
    for index, item in enumerate(value):
        if not isinstance(item, (int, float)):
            errors.append(f"{label}[{index}] must be numeric")
            continue
        if ratio and not 0 <= float(item) <= 1:
            errors.append(f"{label}[{index}] must be between 0 and 1")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def _number_between(value: Any, low: float, high: float) -> bool:
    return isinstance(value, (int, float)) and low <= float(value) <= high


def _crop_candidate_blob(candidate: dict[str, Any]) -> str:
    return " ".join(
        str(candidate.get(key, "")).lower()
        for key in ["id", "type", "reason", "recommended_treatment"]
    )


def _validate_crop_candidates_extended(
    crop_candidates: list[Any],
    *,
    rebuild2: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for index, candidate in enumerate(crop_candidates):
        if not isinstance(candidate, dict):
            continue
        intent = candidate.get("editability_intent")
        if intent is not None and intent not in ALLOWED_EDITABILITY_INTENTS:
            errors.append(
                f"crop_candidates[{index}].editability_intent must be editable, asset, or fallback"
            )
        if "needs_review" in candidate and not isinstance(candidate.get("needs_review"), bool):
            errors.append(f"crop_candidates[{index}].needs_review must be boolean")
        precrop = candidate.get("precrop")
        if precrop is not None:
            if not isinstance(precrop, dict):
                errors.append(f"crop_candidates[{index}].precrop must be an object")
            else:
                if "enabled" in precrop and not isinstance(precrop.get("enabled"), bool):
                    errors.append(f"crop_candidates[{index}].precrop.enabled must be boolean")
                for key in ["file", "source_image"]:
                    if key in precrop and not isinstance(precrop.get(key), str):
                        errors.append(f"crop_candidates[{index}].precrop.{key} must be a string")
                if precrop.get("enabled") is True and not str(precrop.get("file", "")).strip():
                    warnings.append(f"crop_candidates[{index}]: precrop_enabled_without_file")
        blob = _crop_candidate_blob(candidate)
        if any(token in blob for token in FORBIDDEN_CROP_TOKENS):
            errors.append(
                f"crop_candidates[{index}] describes a forbidden structural crop "
                f"(cards/connectors/arrows/text must be vector-rebuilt, not cropped)"
            )
        elif rebuild2 and intent == "asset" and any(
            token in blob for token in ("connector", "card", "arrow", "chevron")
        ):
            errors.append(
                f"crop_candidates[{index}].editability_intent=asset conflicts with a structural element"
            )
    return errors, warnings


def validate(
    data: dict[str, Any],
    *,
    allow_draft: bool = False,
    rebuild2: bool = False,
    mapping: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Missing top-level field: {field}")

    page_role = data.get("page_role")
    if page_role not in ALLOWED_PAGE_ROLES:
        errors.append(f"Unsupported page_role: {page_role}")

    source = data.get("source_reference", {})
    if not isinstance(source, dict):
        errors.append("source_reference must be an object")
    else:
        if source.get("purpose") != "layout_only":
            errors.append("source_reference.purpose must be layout_only")
        content_trust = source.get("content_trust")
        if content_trust not in ALLOWED_CONTENT_TRUST:
            errors.append("source_reference.content_trust must be untrusted_for_final_text or trusted_for_final_text_by_user")
        if source.get("copy_text_from_reference") is True and content_trust != "trusted_for_final_text_by_user":
            errors.append("source_reference.copy_text_from_reference requires trusted_for_final_text_by_user")

    canvas = data.get("canvas", {})
    if not isinstance(canvas, dict):
        errors.append("canvas must be an object")
    elif canvas.get("aspect") != "16:9":
        errors.append("canvas.aspect should be 16:9 for the standard PPT pipeline")

    zones = data.get("zones")
    zone_ids: set[str] = set()
    if allow_draft and zones == []:
        pass
    elif not isinstance(zones, list) or not zones:
        errors.append("zones must be a non-empty list")
    else:
        seen_ids: set[str] = set()
        for index, zone in enumerate(zones):
            if not isinstance(zone, dict):
                errors.append(f"zones[{index}] must be an object")
                continue
            for key in ["id", "role", "position_hint", "editable"]:
                if key not in zone:
                    errors.append(f"zones[{index}] missing field: {key}")
            zone_id = zone.get("id")
            if isinstance(zone_id, str):
                if zone_id in seen_ids:
                    errors.append(f"Duplicate zone id: {zone_id}")
                seen_ids.add(zone_id)
                zone_ids.add(zone_id)
            for key in ["x_ratio", "y_ratio", "w_ratio", "h_ratio"]:
                if key in zone and not _number_between(zone[key], 0, 1):
                    errors.append(f"zones[{index}].{key} must be between 0 and 1")
            if zone.get("editable") is not True:
                # A zone may be deliberately non-editable (e.g. the raster snapshot
                # underlay in text-editable-snapshot mode) only when it records why --
                # mirrors the "requires a recorded reason" pattern used for snapshot
                # crops elsewhere (image_crops_manifest / verify_text_bearing_images).
                has_reason = zone.get("editable") is False and bool(
                    str(zone.get("non_editable_reason", "")).strip()
                )
                if not has_reason:
                    errors.append(f"zones[{index}].editable should be true")

    policy = data.get("editability_policy", {})
    if not isinstance(policy, dict):
        errors.append("editability_policy must be an object")
    elif policy.get("never_flatten_full_slide") is not True:
        errors.append("editability_policy.never_flatten_full_slide must be true")

    dense_mode = data.get("dense_rebuild_mode")
    if dense_mode is not None:
        if not isinstance(dense_mode, dict):
            errors.append("dense_rebuild_mode must be an object when present")
        else:
            if "enabled" in dense_mode and not isinstance(dense_mode.get("enabled"), bool):
                errors.append("dense_rebuild_mode.enabled must be boolean when present")
            signals = dense_mode.get("signals", {})
            if signals and not isinstance(signals, dict):
                errors.append("dense_rebuild_mode.signals must be an object when present")
            elif isinstance(signals, dict):
                for key in ["zone_count", "module_item_count", "renderable_text_chars", "svg_text_elements"]:
                    if key in signals and not isinstance(signals[key], (int, float)):
                        errors.append(f"dense_rebuild_mode.signals.{key} must be numeric")

    visual_layering = data.get("visual_layering")
    if visual_layering is not None:
        if not isinstance(visual_layering, dict):
            errors.append("visual_layering must be an object when present")
        else:
            for layer, items in visual_layering.items():
                if layer not in ALLOWED_VISUAL_LAYERS:
                    errors.append(
                        "visual_layering keys must be one of: "
                        + ", ".join(sorted(ALLOWED_VISUAL_LAYERS))
                    )
                    continue
                if not isinstance(items, list):
                    errors.append(f"visual_layering.{layer} must be a list")
                    continue
                for index, item in enumerate(items):
                    if not isinstance(item, str) or not item.strip():
                        errors.append(f"visual_layering.{layer}[{index}] must be a non-empty string")

    decorative_noise = data.get("decorative_noise")
    if decorative_noise is not None:
        if not isinstance(decorative_noise, list):
            errors.append("decorative_noise must be a list when present")
        else:
            seen_noise_ids: set[str] = set()
            for index, item in enumerate(decorative_noise):
                if not isinstance(item, dict):
                    errors.append(f"decorative_noise[{index}] must be an object")
                    continue
                noise_id = item.get("id")
                if not isinstance(noise_id, str) or not noise_id.strip():
                    errors.append(f"decorative_noise[{index}].id must be a non-empty string")
                elif noise_id in seen_noise_ids:
                    errors.append(f"Duplicate decorative_noise id: {noise_id}")
                else:
                    seen_noise_ids.add(noise_id)
                layer = item.get("layer")
                if layer is not None and layer not in ALLOWED_VISUAL_LAYERS:
                    errors.append(f"decorative_noise[{index}].layer must be one of: {', '.join(sorted(ALLOWED_VISUAL_LAYERS))}")
                treatment = item.get("treatment")
                if treatment not in ALLOWED_NOISE_TREATMENTS:
                    errors.append(f"decorative_noise[{index}].treatment must be one of: {', '.join(sorted(ALLOWED_NOISE_TREATMENTS))}")
                semantic_weight = item.get("semantic_weight", "none")
                if semantic_weight not in ALLOWED_SEMANTIC_WEIGHTS:
                    errors.append(f"decorative_noise[{index}].semantic_weight must be one of: {', '.join(sorted(ALLOWED_SEMANTIC_WEIGHTS))}")
                if "bbox_px" in item:
                    _validate_bbox(errors, item.get("bbox_px"), label=f"decorative_noise[{index}].bbox_px")
                if "bbox_ratio" in item:
                    _validate_bbox(errors, item.get("bbox_ratio"), label=f"decorative_noise[{index}].bbox_ratio", ratio=True)
                if not isinstance(item.get("type"), str) or not item.get("type"):
                    errors.append(f"decorative_noise[{index}].type must be a non-empty string")
                if not isinstance(item.get("reason"), str) or not item.get("reason"):
                    errors.append(f"decorative_noise[{index}].reason must be a non-empty string")

    layout_grammar = data.get("layout_grammar")
    if layout_grammar is not None:
        if not isinstance(layout_grammar, dict):
            errors.append("layout_grammar must be an object when present")
        else:
            page_type_hint = layout_grammar.get("page_type_hint")
            if page_type_hint is not None and page_type_hint not in ALLOWED_PAGE_TYPE_HINTS:
                errors.append(
                    "layout_grammar.page_type_hint must be one of: "
                    + ", ".join(sorted(ALLOWED_PAGE_TYPE_HINTS))
                )
            reading_order = layout_grammar.get("reading_order", [])
            if reading_order and not isinstance(reading_order, list):
                errors.append("layout_grammar.reading_order must be a list when present")
            elif isinstance(reading_order, list):
                for index, item in enumerate(reading_order):
                    if not isinstance(item, str) or not item.strip():
                        errors.append(f"layout_grammar.reading_order[{index}] must be a non-empty string")

    page_type_classifier = data.get("page_type_classifier")
    if page_type_classifier is not None:
        if not isinstance(page_type_classifier, dict):
            errors.append("page_type_classifier must be an object when present")
        else:
            hint = page_type_classifier.get("page_type_hint")
            if hint not in ALLOWED_PAGE_TYPE_HINTS:
                errors.append(
                    "page_type_classifier.page_type_hint must be one of: "
                    + ", ".join(sorted(ALLOWED_PAGE_TYPE_HINTS))
                )
            if "confidence" in page_type_classifier and not _number_between(page_type_classifier["confidence"], 0, 1):
                errors.append("page_type_classifier.confidence must be between 0 and 1")
            signals = page_type_classifier.get("signals", {})
            if signals and not isinstance(signals, dict):
                errors.append("page_type_classifier.signals must be an object when present")
            review = page_type_classifier.get("needs_review", [])
            if review and not isinstance(review, list):
                errors.append("page_type_classifier.needs_review must be a list when present")
            elif isinstance(review, list):
                for index, item in enumerate(review):
                    if not isinstance(item, str) or not item.strip():
                        errors.append(f"page_type_classifier.needs_review[{index}] must be a non-empty string")

    visual_anchors = data.get("visual_anchors")
    if visual_anchors is not None:
        if not isinstance(visual_anchors, list):
            errors.append("visual_anchors must be a list when present")
        else:
            seen_anchor_ids: set[str] = set()
            for index, anchor in enumerate(visual_anchors):
                if not isinstance(anchor, dict):
                    errors.append(f"visual_anchors[{index}] must be an object")
                    continue
                anchor_id = anchor.get("id")
                if not isinstance(anchor_id, str) or not anchor_id.strip():
                    errors.append(f"visual_anchors[{index}].id must be a non-empty string")
                elif anchor_id in seen_anchor_ids:
                    errors.append(f"Duplicate visual anchor id: {anchor_id}")
                else:
                    seen_anchor_ids.add(anchor_id)
                anchor_type = anchor.get("type")
                if anchor_type not in ALLOWED_ANCHOR_TYPES:
                    errors.append(f"visual_anchors[{index}].type must be one of: {', '.join(sorted(ALLOWED_ANCHOR_TYPES))}")
                if "bbox_px" in anchor:
                    _validate_bbox(errors, anchor.get("bbox_px"), label=f"visual_anchors[{index}].bbox_px")
                if "bbox_ratio" in anchor:
                    _validate_bbox(errors, anchor.get("bbox_ratio"), label=f"visual_anchors[{index}].bbox_ratio", ratio=True)
                for key in ["x", "y", "confidence"]:
                    if key in anchor and not isinstance(anchor[key], (int, float)):
                        errors.append(f"visual_anchors[{index}].{key} must be numeric")

    crop_candidates = data.get("crop_candidates")
    if crop_candidates is not None:
        if not isinstance(crop_candidates, list):
            errors.append("crop_candidates must be a list when present")
        else:
            seen_crop_ids: set[str] = set()
            for index, candidate in enumerate(crop_candidates):
                if not isinstance(candidate, dict):
                    errors.append(f"crop_candidates[{index}] must be an object")
                    continue
                crop_id = candidate.get("id")
                if not isinstance(crop_id, str) or not crop_id.strip():
                    errors.append(f"crop_candidates[{index}].id must be a non-empty string")
                elif crop_id in seen_crop_ids:
                    errors.append(f"Duplicate crop candidate id: {crop_id}")
                else:
                    seen_crop_ids.add(crop_id)
                if "bbox_px" in candidate:
                    _validate_bbox(errors, candidate.get("bbox_px"), label=f"crop_candidates[{index}].bbox_px")
                if "bbox_ratio" in candidate:
                    _validate_bbox(errors, candidate.get("bbox_ratio"), label=f"crop_candidates[{index}].bbox_ratio", ratio=True)
                if "recommended_treatment" in candidate and not isinstance(candidate.get("recommended_treatment"), str):
                    errors.append(f"crop_candidates[{index}].recommended_treatment must be a string")
            crop_errors, crop_warnings = _validate_crop_candidates_extended(
                crop_candidates,
                rebuild2=rebuild2 or is_rebuild2(data),
            )
            errors.extend(crop_errors)
            warnings.extend(crop_warnings)

    text_background_relation = data.get("text_background_relation")
    if text_background_relation is not None:
        if not isinstance(text_background_relation, list):
            errors.append("text_background_relation must be a list when present")
        else:
            for index, relation in enumerate(text_background_relation):
                if not isinstance(relation, dict):
                    errors.append(f"text_background_relation[{index}] must be an object")
                    continue
                if not isinstance(relation.get("text_region_id"), str) or not relation.get("text_region_id"):
                    errors.append(f"text_background_relation[{index}].text_region_id must be a non-empty string")
                if "requires_text_underlay_removal" in relation and not isinstance(relation.get("requires_text_underlay_removal"), bool):
                    errors.append(f"text_background_relation[{index}].requires_text_underlay_removal must be boolean")

    confidence = data.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, dict):
            errors.append("confidence must be an object when present")
        else:
            for key, value in confidence.items():
                if not _number_between(value, 0, 1):
                    errors.append(f"confidence.{key} must be between 0 and 1")

    needs_review = data.get("needs_review")
    if needs_review is not None:
        if not isinstance(needs_review, list):
            errors.append("needs_review must be a list when present")
        else:
            for index, item in enumerate(needs_review):
                if not isinstance(item, str) or not item.strip():
                    errors.append(f"needs_review[{index}] must be a non-empty string")

    icon_reconstruction = data.get("icon_reconstruction")
    if icon_reconstruction is not None:
        if not isinstance(icon_reconstruction, dict):
            errors.append("icon_reconstruction must be an object when present")
        else:
            if icon_reconstruction.get("policy") not in ALLOWED_ICON_POLICIES:
                errors.append("icon_reconstruction.policy must be semantic_vector_first, repo_library_first, source_image_crop_allowed, or custom_vector_allowed")
            level_rules = icon_reconstruction.get("level_rules", {})
            if level_rules and not isinstance(level_rules, dict):
                errors.append("icon_reconstruction.level_rules must be an object when present")
            elif isinstance(level_rules, dict):
                for level_name, rule in level_rules.items():
                    if not isinstance(rule, dict):
                        errors.append(f"icon_reconstruction.level_rules.{level_name} must be an object")
                        continue
                    for key in ["circle_r_px", "icon_size_px", "text_gap_px", "min_clearance_px"]:
                        if key in rule and not isinstance(rule[key], (int, float)):
                            errors.append(f"icon_reconstruction.level_rules.{level_name}.{key} must be numeric")
                    alignment_model = rule.get("alignment_model")
                    circle_r = rule.get("circle_r_px")
                    icon_size = rule.get("icon_size_px")
                    bare_linear_icon = (
                        isinstance(circle_r, (int, float))
                        and float(circle_r) == 0
                        and alignment_model in {"title_aligned_icon", "body_column_icon", "footer_action_icon", "custom"}
                    )
                    if (
                        isinstance(icon_size, (int, float))
                        and isinstance(circle_r, (int, float))
                        and not bare_linear_icon
                        and float(icon_size) > float(circle_r) * 2
                    ):
                        errors.append(f"icon_reconstruction.level_rules.{level_name}.icon_size_px should fit inside the icon circle")
            icons = icon_reconstruction.get("icons", [])
            if allow_draft and icons == []:
                pass
            elif icons and not isinstance(icons, list):
                errors.append("icon_reconstruction.icons must be a list")
            elif isinstance(icons, list):
                seen_icon_ids: set[str] = set()
                for index, icon in enumerate(icons):
                    if not isinstance(icon, dict):
                        errors.append(f"icon_reconstruction.icons[{index}] must be an object")
                        continue
                    for key in ["id", "semantic_intent", "parent_zone_id", "slot"]:
                        if key not in icon:
                            errors.append(f"icon_reconstruction.icons[{index}] missing field: {key}")
                    level = icon.get("level")
                    if level is not None and level not in ALLOWED_ICON_LEVELS:
                        errors.append(f"icon_reconstruction.icons[{index}].level must be one of: {', '.join(sorted(ALLOWED_ICON_LEVELS))}")
                    parent_zone_id = icon.get("parent_zone_id")
                    if isinstance(parent_zone_id, str) and zone_ids and parent_zone_id not in zone_ids:
                        errors.append(f"icon_reconstruction.icons[{index}].parent_zone_id does not match a zone id: {parent_zone_id}")
                    icon_id = icon.get("id")
                    if isinstance(icon_id, str):
                        if icon_id in seen_icon_ids:
                            errors.append(f"Duplicate icon id: {icon_id}")
                        seen_icon_ids.add(icon_id)
                    source = icon.get("source", {})
                    if source and not isinstance(source, dict):
                        errors.append(f"icon_reconstruction.icons[{index}].source must be an object")
                    elif isinstance(source, dict):
                        library = source.get("library", "")
                        name = source.get("name", "")
                        if library and "/" in str(library):
                            errors.append(f"icon_reconstruction.icons[{index}].source.library should not include a slash")
                        if name and "/" in str(name):
                            errors.append(f"icon_reconstruction.icons[{index}].source.name should not include a slash")
                    slot = icon.get("slot", {})
                    if not isinstance(slot, dict):
                        errors.append(f"icon_reconstruction.icons[{index}].slot must be an object")
                    else:
                        for key in ["cx_ratio", "cy_ratio", "size_ratio"]:
                            if key in slot and not _number_between(slot[key], 0, 1):
                                errors.append(f"icon_reconstruction.icons[{index}].slot.{key} must be between 0 and 1")
                        fit = slot.get("fit", "contain")
                        if fit not in {"contain", "cover", "badge", "composite"}:
                            errors.append(f"icon_reconstruction.icons[{index}].slot.fit must be contain, cover, badge, or composite")
                    text_anchor = icon.get("text_anchor", {})
                    if text_anchor and not isinstance(text_anchor, dict):
                        errors.append(f"icon_reconstruction.icons[{index}].text_anchor must be an object")
                    elif isinstance(text_anchor, dict):
                        for key in ["text_left_px", "text_top_px", "text_height_px"]:
                            if key in text_anchor and not isinstance(text_anchor[key], (int, float)):
                                errors.append(f"icon_reconstruction.icons[{index}].text_anchor.{key} must be numeric")

    if rebuild2 or is_rebuild2(data):
        errors.extend(validate_structure_contract(data, mapping))
        if "geometry_locks" in data:
            errors.extend(validate_geometry_locks_list(data.get("geometry_locks")))

    return errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate layout_reference.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Path to layout_reference.json")
    parser.add_argument("--allow-draft", action="store_true", help="Allow intake drafts with empty zones")
    parser.add_argument(
        "--rebuild2",
        action="store_true",
        help="Apply 复刻流程2 / layout-reference-rebuild-2 structure_contract rules",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        help="Optional content_mapping.json for icon-count cross-checks",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data = load_json(args.path)
    mapping = load_json(args.mapping) if args.mapping else None
    errors, warnings = validate(
        data,
        allow_draft=args.allow_draft,
        rebuild2=args.rebuild2 or is_rebuild2(data),
        mapping=mapping,
    )
    payload = {"valid": not errors, "errors": errors, "warnings": warnings}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
