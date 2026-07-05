#!/usr/bin/env python3
"""
PPT Master - Layout Reference SVG Plan Bridge

Convert layout_reference.json and content_mapping.json into an Executor-facing
svg_build_plan.json plus a compact Markdown companion. The plan is an execution
aid only; it does not generate SVG files.

Usage:
    python3 scripts/layout_reference_to_svg_plan.py <project_path>

Examples:
    python3 scripts/layout_reference_to_svg_plan.py projects/demo

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from layout_reference_rebuild2_lib import (
        build_crop_plan,
        build_executor_obligations,
        build_zone_components,
        is_rebuild2,
    )
except ImportError:  # pragma: no cover
    from scripts.layout_reference_rebuild2_lib import (  # type: ignore
        build_crop_plan,
        build_executor_obligations,
        build_zone_components,
        is_rebuild2,
    )

try:
    from layout_family_lib import build_detected_layout_family
except ImportError:  # pragma: no cover
    from scripts.layout_family_lib import build_detected_layout_family  # type: ignore

try:
    from harvest_reference_assets import harvest_assets
except ImportError:  # pragma: no cover
    from scripts.harvest_reference_assets import harvest_assets  # type: ignore


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def _ratio_box_to_px(zone: dict[str, Any], canvas: dict[str, Any]) -> dict[str, int] | None:
    width = int(canvas.get("width_px") or 1280)
    height = int(canvas.get("height_px") or 720)
    keys = ["x_ratio", "y_ratio", "w_ratio", "h_ratio"]
    if not all(isinstance(zone.get(key), (int, float)) for key in keys):
        return None
    return {
        "x": round(float(zone["x_ratio"]) * width),
        "y": round(float(zone["y_ratio"]) * height),
        "w": round(float(zone["w_ratio"]) * width),
        "h": round(float(zone["h_ratio"]) * height),
    }


def _icon_slot_to_px(icon: dict[str, Any], canvas: dict[str, Any]) -> dict[str, int] | None:
    width = int(canvas.get("width_px") or 1280)
    height = int(canvas.get("height_px") or 720)
    slot = icon.get("slot", {})
    if not isinstance(slot, dict):
        return None
    keys = ["cx_ratio", "cy_ratio", "size_ratio"]
    if not all(isinstance(slot.get(key), (int, float)) for key in keys):
        return None
    size = round(float(slot["size_ratio"]) * min(width, height))
    return {
        "cx": round(float(slot["cx_ratio"]) * width),
        "cy": round(float(slot["cy_ratio"]) * height),
        "size": size,
    }


def _body_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_string_values(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(_string_values(item))
        return out
    return []


def _dense_rebuild_mode(layout: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    renderable = mapping.get("renderable_content", {})
    modules = renderable.get("modules", [])
    item_count = 0
    if isinstance(modules, list):
        for module in modules:
            if not isinstance(module, dict):
                continue
            for key in ["items", "body", "result"]:
                value = module.get(key)
                if isinstance(value, list):
                    item_count += len(value)
                elif isinstance(value, str) and value.strip():
                    item_count += 1
    text_chars = sum(len(text) for text in _string_values(renderable))
    zone_count = len([zone for zone in layout.get("zones", []) if isinstance(zone, dict)])
    explicit = layout.get("dense_rebuild_mode", {})
    enabled = bool(explicit.get("enabled")) if isinstance(explicit, dict) else False
    triggered = enabled or zone_count >= 8 or item_count >= 20 or text_chars >= 900
    return {
        "enabled": triggered,
        "reason": explicit.get("reason", "") if isinstance(explicit, dict) else "",
        "signals": {
            "zone_count": zone_count,
            "module_item_count": item_count,
            "renderable_text_chars": text_chars,
        },
        "rules": [
            "Prioritize readable/editable text over exact micro-icon reproduction.",
            "Use lightweight semantic line icons; omit low-value repeated icons when space is tight.",
            "Shorten visible line breaks before reducing line height.",
            "Run verify_text_fit.py and verify_svg_spacing.py after every dense layout adjustment.",
        ] if triggered else [],
    }


def _visual_layer_summary(layout: dict[str, Any]) -> dict[str, Any]:
    layering = layout.get("visual_layering", {})
    decorative_noise = layout.get("decorative_noise", [])
    if not isinstance(layering, dict):
        layering = {}
    if not isinstance(decorative_noise, list):
        decorative_noise = []

    treatment_counts: dict[str, int] = {}
    items: list[dict[str, Any]] = []
    for item in decorative_noise:
        if not isinstance(item, dict):
            continue
        treatment = str(item.get("treatment", "")).strip() or "unspecified"
        treatment_counts[treatment] = treatment_counts.get(treatment, 0) + 1
        items.append({
            "id": item.get("id", ""),
            "type": item.get("type", ""),
            "layer": item.get("layer", ""),
            "treatment": treatment,
            "semantic_weight": item.get("semantic_weight", "none"),
            "bbox_px": item.get("bbox_px"),
            "reason": item.get("reason", ""),
        })

    return {
        "layers": {
            key: value
            for key, value in layering.items()
            if isinstance(key, str) and isinstance(value, list)
        },
        "decorative_noise": items,
        "treatment_counts": treatment_counts,
        "rules": [
            "Build content_layer, structure_layer, and semantic_icon_layer first.",
            "Render decorative_layer only after content is stable.",
            "Never convert decorative_noise into semantic icons, hard anchors, or data-chain connectors.",
            "For faint data streams, place data-chain-connector only on the functional arrowhead, not on the ambient stream group.",
        ],
    }


def _connector_plan(layout: dict[str, Any], zones: list[dict[str, Any]]) -> dict[str, Any]:
    chain = layout.get("main_chain", {})
    contract = layout.get("structure_contract", {})
    primitives = contract.get("required_primitives", []) if isinstance(contract, dict) else []
    connectors = chain.get("connectors", []) if isinstance(chain, dict) else []
    relationship_style = str(chain.get("relationship_style", "")) if isinstance(chain, dict) else ""
    layout_type = str(layout.get("layout_type", ""))
    signals = " ".join([
        relationship_style,
        layout_type,
        " ".join(str(item) for item in primitives if isinstance(item, str)),
    ]).lower()
    needs_connector_plan = bool(connectors) or any(
        token in signals
        for token in ["arrow", "connector", "chain", "flow", "center", "node"]
    )
    zone_boxes = {
        str(zone.get("zone_id")): zone.get("px_box")
        for zone in zones
        if zone.get("zone_id") and zone.get("px_box")
    }
    return {
        "enabled": needs_connector_plan,
        "selection_policy": "arrow_library_first",
        "shared_arrow_indexes": {
            "connector_index": "../skills/ppt-master/templates/arrows/connector_index.json",
            "arrows_index": "../skills/ppt-master/templates/arrows/arrows_index.json",
        },
        "preferred_template_families": [
            "pptpack7_orthogonal_connector_*",
            "pptpack7_hub_exchange_topology_*",
            "pptpack7_cycle_feedback_*",
            "pptpack6_right_angle_route_connector_*",
            "pptpack5_node_link_connector_*",
            "pptpack4_connector_route_*",
            "dashed_orthogonal_dependency_bus",
            "data_flow_swimlanes",
            "dashed_bus_up_taps",
            "side_rail_arrow_frame",
        ],
        "library": "scripts/layout_reference_components.py",
        "geometry_helper": "scripts/arrow_geometry.py",
        "main_chain_connectors": connectors if isinstance(connectors, list) else [],
        "zone_boxes": zone_boxes,
        "recipes": [
            {
                "use": "layout_reference_components.svg_box_connector_arrow",
                "for": "card-to-card, column-to-column, or box-to-box curved connectors",
                "output": "<path> plus <polygon> arrowhead with data-chain-connector",
            },
            {
                "use": "layout_reference_components.svg_center_node_arrow",
                "for": "short chunky arrows pointing from a card/box into a central circle or node",
                "output": "<polygon> block arrow with data-chain-connector and center_node_block_arrow primitive",
            },
            {
                "use": "layout_reference_components.svg_block_arrow_between",
                "for": "explicit point-to-point straight block arrows in flow diagrams",
                "output": "<polygon> block arrow with data-chain-connector",
            },
        ],
        "rules": [
            "Before drawing any arrow/connector, search shared connector_index.json first and arrows_index.json second; adapt a matching template when the semantic role fits.",
            "Use connector_plan recipes and arrow_geometry.py only as a fallback when no indexed arrow template matches the reference relationship.",
            "If custom geometry is used, record why no arrow-library template matched.",
            "Use connector_plan recipes before hand-calculating arrow coordinates.",
            "Keep data-chain-connector on the functional arrow element or group, not on decorative streams.",
            "Use svg_center_node_arrow for center-node inbound arrows so the arrow is short, chunky, and tangent to the node.",
            "Use svg_box_connector_arrow for card/column connectors so start/end points land on rectangle edges.",
            "Do not run a post-processing auto-rewrite over existing lines; revise the authored SVG when connector QA fails.",
        ],
    }


def _page_id(layout: dict[str, Any]) -> str:
    raw = layout.get("page_id")
    page_block = layout.get("page")
    if not raw and isinstance(page_block, dict):
        raw = page_block.get("page_id")
    return str(raw or "P01")


def _assets_for_page(asset_manifest: dict[str, Any] | None, page_id: str) -> list[dict[str, Any]]:
    if not isinstance(asset_manifest, dict):
        return []
    assets = asset_manifest.get("assets")
    if not isinstance(assets, list):
        return []
    return [
        asset for asset in assets
        if isinstance(asset, dict) and str(asset.get("page_id", page_id)) == page_id
    ]


def build_plan(
    layout: dict[str, Any],
    mapping: dict[str, Any],
    *,
    asset_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    canvas = layout.get("canvas", {})
    page_id = _page_id(layout)
    renderable = mapping.get("renderable_content", {})
    modules = renderable.get("modules", [])
    module_by_zone = {
        module.get("zone_id"): module
        for module in modules
        if isinstance(module, dict) and isinstance(module.get("zone_id"), str)
    }

    zones: list[dict[str, Any]] = []
    for zone in layout.get("zones", []):
        if not isinstance(zone, dict):
            continue
        zone_id = zone.get("id")
        module = module_by_zone.get(zone_id, {})
        body = _body_lines(module.get("body", []))
        if not body and zone.get("role") == "main_carrier" and renderable.get("core_judgment"):
            body = _body_lines(renderable.get("core_judgment", ""))
        zones.append({
            "zone_id": zone_id,
            "role": zone.get("role", ""),
            "position_hint": zone.get("position_hint", ""),
            "visual_weight": zone.get("visual_weight", ""),
            "ratio_box": {
                key: zone.get(key)
                for key in ["x_ratio", "y_ratio", "w_ratio", "h_ratio"]
                if key in zone
            },
            "px_box": _ratio_box_to_px(zone, canvas),
            "contains": zone.get("contains", []),
            "renderable": {
                "index": module.get("index", ""),
                "title": module.get("title", ""),
                "body": body,
                "result_title": module.get("result_title", ""),
                "result": _body_lines(module.get("result", [])),
            },
            "editable": zone.get("editable", True),
        })

    icon_reference = layout.get("icon_reconstruction", {})
    icon_plan: dict[str, Any] = {
        "policy": "repo_library_first",
        "preferred_libraries": ["tabler-outline", "tabler-filled", "chunk-filled", "phosphor-duotone"],
        "fallback": "hand_vector_only_when_no_repository_match",
        "slot_model": "centered_square_with_optical_adjustment",
        "level_rules": {
            "intro": {"circle_r_px": 40, "icon_size_px": 55, "text_gap_px": 29, "min_clearance_px": 18},
            "card_section": {"circle_r_px": 22, "icon_size_px": 26, "text_gap_px": 18, "min_clearance_px": 14},
            "consensus": {"circle_r_px": 34, "icon_size_px": 45, "text_gap_px": 14, "min_clearance_px": 20},
            "action": {"circle_r_px": 32, "icon_size_px": 42, "text_gap_px": 41, "min_clearance_px": 18},
        },
        "alignment_rules": [
            "Compute icon_cy from the paired text block center, not from a fixed baseline.",
            "Treat text_gap_px as icon circle right edge to text left clearance.",
            "Compute icon_cx from text_left - text_gap_px - circle_r_px.",
            "Same-level icons share circle radius and visual icon size; use optical_adjustment only for glyph-specific correction.",
            "Keep icon circles clear of card borders, text dividers, and body copy by min_clearance_px.",
        ],
        "icons": [],
        "quality_rules": [
            "Use <use data-icon=\"library/name\"> placeholders from one repository icon library by default.",
            "Use hand-drawn semantic vectors only when no repository icon can carry the semantic role.",
            "Preserve icon aspect ratio; fit by the shorter side inside the slot.",
            "Normalize icon visual weight with explicit size/offset rules.",
            "Keep badges and composite marks inside the parent icon circle/card slot.",
            "Verify final icons from svg_final or exported PPTX.",
        ],
    }
    if isinstance(icon_reference, dict):
        icon_plan.update({
            "policy": icon_reference.get("policy", icon_plan["policy"]),
            "preferred_libraries": icon_reference.get("preferred_libraries", icon_plan["preferred_libraries"]),
            "fallback": icon_reference.get("fallback", icon_plan["fallback"]),
            "slot_model": icon_reference.get("slot_model", icon_plan["slot_model"]),
            "level_rules": icon_reference.get("level_rules", icon_plan["level_rules"]),
            "alignment_rules": icon_reference.get("alignment_rules", icon_plan["alignment_rules"]),
        })
        icons = icon_reference.get("icons", [])
        if isinstance(icons, list):
            for icon in icons:
                if not isinstance(icon, dict):
                    continue
                source = icon.get("source", {})
                slot = icon.get("slot", {})
                icon_plan["icons"].append({
                    "id": icon.get("id", ""),
                    "semantic_intent": icon.get("semantic_intent", ""),
                    "parent_zone_id": icon.get("parent_zone_id", ""),
                    "source": source if isinstance(source, dict) else {},
                    "level": icon.get("level", ""),
                    "text_anchor": icon.get("text_anchor", {}),
                    "slot": slot if isinstance(slot, dict) else {},
                    "px_slot": _icon_slot_to_px(icon, canvas),
                    "optical_adjustment": icon.get("optical_adjustment", {}),
                    "composite": icon.get("composite", []),
                    "notes": icon.get("notes", ""),
                })

    source = layout.get("source_reference", {})
    family_block = layout.get("detected_layout_family", {})
    if not isinstance(family_block, dict) or not isinstance(family_block.get("archetype"), dict):
        family_block = build_detected_layout_family(layout)
    archetype_block = family_block.get("archetype", {}) if isinstance(family_block, dict) else {}
    dense_mode = _dense_rebuild_mode(layout, mapping)
    rebuild2 = is_rebuild2(layout)
    if rebuild2:
        dense_mode = {
            **dense_mode,
            "enabled": dense_mode.get("enabled", False),
            "fidelity_mode": "reference",
            "rules": [
                "Preserve structure_contract.required_primitives before omitting icons.",
                "Use layout_reference_components recipes from components[].recipe.",
                "Emit data-zone-id, data-icon-id, data-primitive, and data-chain-connector markers.",
            ],
        }
    plan = {
        "version": "2.0" if rebuild2 else "1.0",
        "purpose": "executor_svg_build_plan",
        "workflow": layout.get("workflow", ""),
        "source_policy": {
            "reference_image": source.get("path", ""),
            "content_trust": source.get("content_trust", ""),
            "copy_text_from_reference": source.get("copy_text_from_reference", False),
            "full_slide_raster_allowed": False,
        },
        "canvas": {
            "aspect": canvas.get("aspect", "16:9"),
            "width_px": canvas.get("width_px", 1280),
            "height_px": canvas.get("height_px", 720),
            "safe_margin_px": canvas.get("safe_margin_px", 48),
        },
        "page": {
            "page_id": page_id,
            "page_role": layout.get("page_role", ""),
            "layout_type": layout.get("layout_type", ""),
            "page_rhythm_recommendation": "dense",
            "title": renderable.get("title", ""),
            "subtitle": renderable.get("subtitle", ""),
            "intro": renderable.get("intro", ""),
            "core_judgment": renderable.get("core_judgment", ""),
            "takeaway": renderable.get("takeaway", ""),
        },
        "main_chain": {
            "direction": layout.get("main_chain", {}).get("direction", ""),
            "relationship_style": layout.get("main_chain", {}).get("relationship_style", ""),
            "node_labels": renderable.get("main_chain_labels", []),
            "nodes": layout.get("main_chain", {}).get("nodes", []),
        },
        "layout_archetype": archetype_block if isinstance(archetype_block, dict) else {},
        "harvested_asset_plan": {
            "policy": "Use only for declared decorative/photo/logo/complex-small-icon assets; prefer vector/library icons for functional icons.",
            "manifest": "image_asset_manifest.json",
            "assets": _assets_for_page(asset_manifest, page_id),
        },
        "style_cues": layout.get("style_reference", {}),
        "visual_layer_policy": _visual_layer_summary(layout),
        "dense_rebuild_mode": dense_mode,
        "icon_plan": icon_plan,
        "connector_plan": _connector_plan(layout, zones),
        "zones": zones,
        "executor_checks": [
            "Use only values locked in spec_lock.md for colors and fonts.",
            "Render final text from renderable fields only.",
            "Do not place the reference image as a full-slide background.",
            "Keep text, cards, arrows, bands, and simple icons editable.",
            "Use connector_plan recipes for card/center-node arrows before hand-calculating connector coordinates.",
            "Apply visual_layer_policy before drawing: ignore or weaken decorative_noise, and keep data-chain connectors reserved for functional flow arrows.",
            "Use semantic hand-drawn icons first unless a repository icon is an immediate match; verify icon proportions and positions visually.",
            "If dense_rebuild_mode.enabled is true, reduce icon complexity and protect text readability before pursuing exact icon count.",
            "Run verify_svg_spacing.py for dense cards, bottom chains, and repeated labels.",
            "Run svg_quality_checker.py before post-processing.",
        ],
    }
    if rebuild2:
        plan["structure_contract"] = layout.get("structure_contract", {})
        plan["components"] = build_zone_components(layout, mapping)
        plan["crop_plan"] = build_crop_plan(layout)
        plan["executor_obligations"] = build_executor_obligations(layout, plan["icon_plan"].get("icons", []))
        plan["executor_checks"] = [
            *plan["executor_obligations"],
            "Use connector_plan recipes for required chain/arrow primitives.",
            "Apply visual_layer_policy: decorative_noise must not become functional icons, hard anchors, or flow arrows.",
            "Run verify_layout_executor_contract.py before export.",
            "Run verify_icon_text_fit.py --strict against svg_final.",
        ]
    if plan["layout_archetype"]:
        plan["executor_checks"].insert(
            0,
            "Use layout_archetype as an advisory object inventory; do not force the page into a template when confidence is low.",
        )
    if plan["harvested_asset_plan"]["assets"]:
        plan["executor_checks"].insert(
            0,
            "Prefer harvested_asset_plan local crops only for their declared roles; do not use them as text/card/connector/main-structure substitutes.",
        )
    return plan


def _row(values: list[Any]) -> str:
    cells: list[str] = []
    for value in values:
        if isinstance(value, (dict, list)):
            text_value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            text_value = str(value)
        cells.append(text_value.replace("\n", " ").strip())
    return "| " + " | ".join(cells) + " |"


def build_markdown(plan: dict[str, Any]) -> str:
    page = plan["page"]
    lines = [
        "# SVG Build Plan",
        "",
        "> Generated by `layout_reference_to_svg_plan.py`. This is an Executor aid, not generated SVG.",
        "",
        "## Page",
        "",
        _row(["Field", "Value"]),
        _row(["---", "---"]),
        _row(["Role", page.get("page_role", "")]),
        _row(["Layout type", page.get("layout_type", "")]),
        _row(["Rhythm", page.get("page_rhythm_recommendation", "")]),
        _row(["Title", page.get("title", "")]),
        _row(["Core judgment", page.get("core_judgment", "")]),
        "",
        "## Layout Archetype",
        "",
        _row(["Field", "Value"]),
        _row(["---", "---"]),
    ]
    archetype = plan.get("layout_archetype", {})
    if isinstance(archetype, dict) and archetype:
        lines.extend([
            _row(["Name", archetype.get("name", "")]),
            _row(["Label", archetype.get("label", "")]),
            _row(["Confidence", archetype.get("confidence", "")]),
            _row(["Required objects", "；".join(str(item) for item in archetype.get("required_objects", []))]),
            _row(["Signals", "；".join(str(item) for item in archetype.get("signals", []))]),
        ])
    else:
        lines.append(_row(["Name", "custom / unavailable"]))
    lines.extend([
        "",
        "## Zones",
        "",
        _row(["Zone", "Px box", "Title", "Body", "Result"]),
        _row(["---", "---", "---", "---", "---"]),
    ])
    for zone in plan.get("zones", []):
        renderable = zone.get("renderable", {})
        px_box = zone.get("px_box") or {}
        px = ",".join(str(px_box.get(key, "")) for key in ["x", "y", "w", "h"])
        lines.append(_row([
            zone.get("zone_id", ""),
            px,
            renderable.get("title", ""),
            "；".join(renderable.get("body", [])),
            "；".join(renderable.get("result", [])),
        ]))
    icon_plan = plan.get("icon_plan", {})
    lines.extend([
        "",
        "## Icon Reconstruction",
        "",
        _row(["Field", "Value"]),
        _row(["---", "---"]),
        _row(["Policy", icon_plan.get("policy", "")]),
        _row(["Preferred libraries", ", ".join(icon_plan.get("preferred_libraries", []))]),
        _row(["Slot model", icon_plan.get("slot_model", "")]),
        _row(["Level rules", icon_plan.get("level_rules", {})]),
        "",
        "### Alignment Rules",
        "",
    ])
    lines.extend(f"- {item}" for item in icon_plan.get("alignment_rules", []))
    lines.extend([
        "",
        _row(["Icon", "Level", "Intent", "Source", "Px slot", "Text anchor", "Adjustment"]),
        _row(["---", "---", "---", "---", "---", "---", "---"]),
    ])
    for icon in icon_plan.get("icons", []):
        source = icon.get("source", {})
        source_label = str(source.get("kind", "")).strip()
        repo_label = "/".join(str(source.get(key, "")).strip() for key in ["library", "name"]).strip("/")
        if repo_label:
            source_label = f"{source_label}:{repo_label}" if source_label else repo_label
        px_slot = icon.get("px_slot") or {}
        px = ",".join(str(px_slot.get(key, "")) for key in ["cx", "cy", "size"])
        lines.append(_row([
            icon.get("id", ""),
            icon.get("level", ""),
            icon.get("semantic_intent", ""),
            source_label,
            px,
            icon.get("text_anchor", {}),
            icon.get("optical_adjustment", ""),
        ]))
    visual_policy = plan.get("visual_layer_policy", {})
    if isinstance(visual_policy, dict):
        lines.extend([
            "",
            "## Visual Layer Policy",
            "",
            _row(["Layer", "Items"]),
            _row(["---", "---"]),
        ])
        layers = visual_policy.get("layers", {})
        if isinstance(layers, dict):
            for layer, items in layers.items():
                if isinstance(items, list):
                    lines.append(_row([layer, "；".join(str(item) for item in items)]))
        lines.extend([
            "",
            _row(["Noise", "Layer", "Treatment", "Semantic weight", "Reason"]),
            _row(["---", "---", "---", "---", "---"]),
        ])
        noise_items = visual_policy.get("decorative_noise", [])
        if isinstance(noise_items, list):
            for item in noise_items:
                if isinstance(item, dict):
                    lines.append(_row([
                        item.get("id", ""),
                        item.get("layer", ""),
                        item.get("treatment", ""),
                        item.get("semantic_weight", ""),
                        item.get("reason", ""),
                    ]))
        lines.extend(["", "### Visual Layer Rules", ""])
        rules = visual_policy.get("rules", [])
        if isinstance(rules, list):
            lines.extend(f"- {item}" for item in rules)
    harvested = plan.get("harvested_asset_plan", {})
    if isinstance(harvested, dict):
        assets = harvested.get("assets", [])
        lines.extend([
            "",
            "## Harvested Image Assets",
            "",
            _row(["Policy", harvested.get("policy", "")]),
            _row(["Manifest", harvested.get("manifest", "")]),
            "",
            _row(["Asset", "Treatment", "Role", "Path", "Source bbox"]),
            _row(["---", "---", "---", "---", "---"]),
        ])
        if isinstance(assets, list) and assets:
            for asset in assets:
                if isinstance(asset, dict):
                    lines.append(_row([
                        asset.get("id", ""),
                        asset.get("treatment", ""),
                        asset.get("crop_role", ""),
                        asset.get("path", ""),
                        asset.get("bbox_px", ""),
                    ]))
        else:
            lines.append(_row(["none", "", "", "", ""]))
    connector_plan = plan.get("connector_plan", {})
    if isinstance(connector_plan, dict) and connector_plan.get("enabled"):
        lines.extend([
            "",
            "## Connector Plan",
            "",
            _row(["Selection policy", connector_plan.get("selection_policy", "")]),
            "",
            _row(["Shared arrow index", "Path"]),
            _row(["---", "---"]),
        ])
        indexes = connector_plan.get("shared_arrow_indexes", {})
        if isinstance(indexes, dict):
            for name, path in indexes.items():
                lines.append(_row([name, path]))
        families = connector_plan.get("preferred_template_families", [])
        if isinstance(families, list) and families:
            lines.extend(["", "### Preferred Arrow Template Families", ""])
            lines.extend(f"- `{item}`" for item in families)
        lines.extend([
            "",
            _row(["Helper", "Path"]),
            _row(["---", "---"]),
            _row(["Component helpers", connector_plan.get("library", "")]),
            _row(["Geometry helper", connector_plan.get("geometry_helper", "")]),
            "",
            _row(["Recipe", "Use", "Output"]),
            _row(["---", "---", "---"]),
        ])
        for recipe in connector_plan.get("recipes", []):
            if isinstance(recipe, dict):
                lines.append(_row([
                    recipe.get("use", ""),
                    recipe.get("for", ""),
                    recipe.get("output", ""),
                ]))
        connectors = connector_plan.get("main_chain_connectors", [])
        if isinstance(connectors, list) and connectors:
            lines.extend(["", "### Main Chain Connectors", ""])
            lines.extend(f"- {item}" for item in connectors)
        lines.extend(["", "### Connector Rules", ""])
        rules = connector_plan.get("rules", [])
        if isinstance(rules, list):
            lines.extend(f"- {item}" for item in rules)
    lines.extend([
        "",
        "## Executor Checks",
        "",
    ])
    lines.extend(f"- {item}" for item in plan.get("executor_checks", []))
    if plan.get("components"):
        lines.extend([
            "",
            "## Components (复刻流程2)",
            "",
            _row(["Zone", "Component", "Recipe"]),
            _row(["---", "---", "---"]),
        ])
        for component in plan.get("components", []):
            if isinstance(component, dict):
                lines.append(_row([
                    component.get("zone_id", ""),
                    component.get("component", ""),
                    component.get("recipe", ""),
                ]))
    if plan.get("executor_obligations"):
        lines.extend(["", "## Executor Obligations", ""])
        lines.extend(f"- {item}" for item in plan["executor_obligations"])
    crop_plan = plan.get("crop_plan", [])
    if crop_plan:
        lines.extend([
            "",
            "## Crop plan (复刻流程2)",
            "",
            _row(["ID", "Intent", "Review", "Precrop", "Hint"]),
            _row(["---", "---", "---", "---", "---"]),
        ])
        for item in crop_plan:
            if isinstance(item, dict):
                precrop = item.get("precrop", {}) if isinstance(item.get("precrop"), dict) else {}
                precrop_label = "enabled" if precrop.get("enabled") else "disabled"
                lines.append(_row([
                    item.get("id", ""),
                    item.get("editability_intent", ""),
                    "yes" if item.get("needs_review") else "no",
                    precrop_label,
                    item.get("executor_hint", ""),
                ]))
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate svg_build_plan.json/md from layout reference artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_path = args.project_path
    layout = load_json(project_path / "layout_reference.json")
    mapping = load_json(project_path / "content_mapping.json")
    asset_manifest = harvest_assets(project_path, write_report=True)
    plan = build_plan(layout, mapping, asset_manifest=asset_manifest)
    json_path = project_path / "svg_build_plan.json"
    md_path = project_path / "svg_build_plan.md"
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(plan), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
